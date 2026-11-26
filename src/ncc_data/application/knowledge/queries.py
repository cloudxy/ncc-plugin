import copy
import re
from decimal import Decimal

from sqlalchemy import Integer, Numeric, and_, case, cast, delete, func, literal, or_, select, union_all

from ncc_data.application.security import authorize
from ncc_data.domain.contracts import Query, ScopeInput, ScopeRename, StateQuery
from ncc_data.domain.definitions import SYSTEM_SCOPE, merge_system_properties
from ncc_data.persistence.models import (
    Assessment,
    Attachment,
    Audit,
    Calibration,
    ChangeSet,
    Definition,
    Delegation,
    Entity,
    Fact,
    Feedback,
    ImportRun,
    Job,
    Membership,
    Receipt,
    Revision,
    Scope,
    Session,
)
from ncc_shared.errors import DomainError, require
from ncc_shared.serialization import jsonable

_INT_POS_RE = re.compile(r"^-?[0-9]{1,9}$")


def safe_int_position(value, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str) and _INT_POS_RE.fullmatch(value.strip()):
        return int(value.strip())
    return default


def _sql_position(col, *, fallback: int = 2_147_483_647):
    return case((col.op("~")(r"^-?[0-9]{1,9}$"), cast(col, Integer)), else_=literal(fallback))


class ResolvedDefinition:
    """In-memory definition. Stored property keys win; missing system keys are filled without mutating ncc_definition."""

    def __init__(self, row):
        self.id = row.id
        self.key = row.key
        self.version = row.version
        self.scope_id = row.scope_id
        self.spec = view_spec(row)


def view_spec(row):
    spec = copy.deepcopy(row.spec if isinstance(getattr(row, "spec", None), dict) else {})
    if getattr(row, "scope_id", None) == SYSTEM_SCOPE and getattr(row, "version", None) == 1 and not spec.get("relation"):
        spec = merge_system_properties(spec)
    return spec


class QueryService:
    def __init__(self, db, actor):
        self.db, self.actor = db, actor

    async def scopes(self, *, include_archived: bool = False):
        members = select(Membership.scope_id).where(Membership.user_id == self.actor.id)
        statement = select(Scope).where(
            Scope.kind != "deleted",
            or_(Scope.owner_id == self.actor.id, Scope.id.in_(members)),
        )
        if hasattr(self.actor, "_access_scope"):
            statement = statement.where(Scope.id == self.actor._access_scope)
        rows = (await self.db.scalars(statement.order_by(Scope.created_at))).all()
        result = []
        for row in rows:
            if not include_archived and bool((row.config or {}).get("archived", False)):
                continue
            try:
                result.append(await self.scope_info(row.id))
            except DomainError as exc:
                if exc.status not in {403, 404}:
                    raise
        return result

    async def scope_info(self, scope_id):
        row, actions = await authorize(self.db, self.actor, scope_id)
        raw_config = row.config or {}
        config = {k: v for k, v in raw_config.items() if k != "views"} if "admin" in actions else {}
        config["views"] = raw_config.get("views", {}).get(self.actor.id, {})
        return {
            "id": row.id,
            "name": row.name,
            "kind": row.kind,
            "version": row.version,
            "parent_id": row.parent_id,
            "base_id": row.base_id,
            "base_version": row.base_version,
            "actions": sorted(actions),
            "owner": row.owner_id == self.actor.id,
            "archived": bool(raw_config.get("archived", False)),
            "config": config,
        }

    async def rename_scope(self, scope_id, value: ScopeRename):
        scope, _ = await authorize(self.db, self.actor, scope_id, "admin", lock=True)
        require(scope.owner_id == self.actor.id, "owner_only", "只有范围所有者可修改名称或归档状态", 403)
        require(not hasattr(self.actor, "_access_scope"), "scoped_credential", "范围凭据不能修改范围设置", 403)
        if value.name is not None:
            name = value.name.strip()
            require(name, "name", "名称不能为空")
            scope.name = name
            self.db.add(
                Audit(
                    scope_id=scope.id,
                    actor_id=self.actor.id,
                    action="scope.rename",
                    version=scope.version,
                    detail={"name": name},
                )
            )
        if value.archived is not None:
            archived = bool(value.archived)
            config = dict(scope.config or {})
            config["archived"] = archived
            scope.config = config
            self.db.add(
                Audit(
                    scope_id=scope.id,
                    actor_id=self.actor.id,
                    action="scope.archive",
                    version=scope.version,
                    detail={"archived": archived},
                )
            )
        await self.db.flush()
        return await self.scope_info(scope.id)

    async def create_scope(self, value: ScopeInput):
        if value.parent_id:
            await authorize(self.db, self.actor, value.parent_id, "edit")
        config = {"definitions": {}, "adoptions": {}}
        if value.base_id:
            base, _ = await authorize(self.db, self.actor, value.base_id, "adopt", lock=True)
            require(base.owner_id == self.actor.id, "branch_owner", "完整分支须由源范围所有者创建", 403)
            require(value.kind == "branch", "branch", "仅分支允许设置基线")
            pin = base.version if value.base_version is None else value.base_version
            require(0 <= pin <= base.version, "baseline", "无效分支基线")
            # Definition adoption is immutable per referenced ID; branch takes an explicit copy.
            config = await self.configuration_at(base, pin)
        else:
            require(value.kind != "branch", "branch", "分支必须指定基线")
            pin = None
        row = Scope(
            name=value.name,
            kind=value.kind,
            owner_id=self.actor.id,
            parent_id=value.parent_id,
            base_id=value.base_id,
            base_version=pin,
            config=config,
        )
        self.db.add(row)
        await self.db.flush()
        self.db.add(
            Audit(
                scope_id=SYSTEM_SCOPE,
                actor_id=self.actor.id,
                action="scope.create",
                version=row.version,
                detail={"scope_id": row.id, "name": row.name, "kind": row.kind},
            )
        )
        await self.db.flush()
        return await self.scope_info(row.id)

    async def delete_empty_scope(self, scope_id: str):
        scope, _ = await authorize(self.db, self.actor, scope_id, "admin", lock=True)
        require(scope.id != SYSTEM_SCOPE, "system_scope", "系统定义范围不可删除", 403)
        require(scope.owner_id == self.actor.id, "owner_only", "只有范围所有者可彻底删除空空间", 403)
        require(not hasattr(self.actor, "_access_scope"), "scoped_credential", "范围凭据不能删除空间", 403)
        child_id = await self.db.scalar(
            select(Scope.id)
            .where(
                Scope.kind != "deleted",
                or_(Scope.parent_id == scope_id, Scope.base_id == scope_id),
            )
            .limit(1)
        )
        has_entity = await self.db.scalar(select(Entity.id).where(Entity.scope_id == scope_id).limit(1))
        require(
            scope.version == 0 and child_id is None and has_entity is None,
            "scope_not_empty",
            "已有正式修订或子分支的空间不能彻底删除，请使用归档",
            409,
        )
        old_name = scope.name
        await self.db.execute(delete(ImportRun).where(ImportRun.scope_id == scope_id))
        await self.db.execute(delete(Attachment).where(Attachment.scope_id == scope_id))
        await self.db.execute(delete(Job).where(Job.scope_id == scope_id))
        await self.db.execute(delete(ChangeSet).where(ChangeSet.scope_id == scope_id))
        await self.db.execute(delete(Delegation).where(Delegation.scope_id == scope_id))
        await self.db.execute(delete(Calibration).where(Calibration.scope_id == scope_id))
        await self.db.execute(delete(Feedback).where(Feedback.scope_id == scope_id))
        await self.db.execute(delete(Session).where(Session.scope_id == scope_id))
        await self.db.execute(delete(Membership).where(Membership.scope_id == scope_id))
        has_immutable = bool(
            await self.db.scalar(
                union_all(
                    select(Audit.id).where(Audit.scope_id == scope_id).limit(1),
                    select(Receipt.id).where(Receipt.scope_id == scope_id).limit(1),
                    select(Assessment.id).where(Assessment.scope_id == scope_id).limit(1),
                    select(Definition.id).where(Definition.scope_id == scope_id).limit(1),
                ).limit(1)
            )
        )
        if has_immutable:
            # Committed ncc_audit/ncc_receipt/ncc_assessment/ncc_definition rows are protected by
            # PostgreSQL ncc_history_guard() triggers; detach ownership and mark deleted so no
            # principal can access or enumerate the retired empty scope.
            scope.owner_id = None
            scope.parent_id = None
            scope.base_id = None
            scope.kind = "deleted"
            scope.config = {"deleted": True}
        else:
            await self.db.delete(scope)
        self.db.add(
            Audit(
                scope_id=SYSTEM_SCOPE,
                actor_id=self.actor.id,
                action="scope.delete",
                version=0,
                detail={"scope_id": scope_id, "name": old_name},
            )
        )
        await self.db.flush()
        return {"deleted": True, "id": scope_id}

    async def lineage(self, scope, as_of=None):
        limit = scope.version if as_of is None else as_of
        require(0 <= limit <= scope.version, "version", "记录版本超出已提交范围")
        result, seen = [], set()
        while scope:
            require(scope.id not in seen and len(seen) < 16, "scope_cycle", "范围基线存在循环或过深")
            seen.add(scope.id)
            result.append((scope.id, limit))
            if not scope.base_id:
                break
            limit = scope.base_version
            scope = await self.db.get(Scope, scope.base_id)
        return result

    async def configuration_at(self, scope, version):
        if version is None or version == scope.version:
            return copy.deepcopy(scope.config)
        require(0 <= version <= scope.version, "version", "配置版本无效")
        config = {"definitions": {}, "adoptions": {}}
        if scope.base_id:
            base = await self.db.get(Scope, scope.base_id)
            config = await self.configuration_at(base, scope.base_version)
        changes = (
            await self.db.scalars(
                select(ChangeSet)
                .where(
                    ChangeSet.scope_id == scope.id,
                    ChangeSet.state == "applied",
                    ChangeSet.applied_version <= version,
                )
                .order_by(ChangeSet.applied_version)
            )
        ).all()
        for change in changes:
            for op in change.operations:
                if op["op"] == "definition":
                    value = op["definition"]
                    definition = await self.db.scalar(
                        select(Definition).where(
                            Definition.scope_id == scope.id,
                            Definition.key == value["key"],
                            Definition.version == value["version"],
                        )
                    )
                    if definition:
                        config.setdefault("definitions", {})[value["key"]] = definition.id
                elif op["op"] == "adopt":
                    config.setdefault("adoptions", {})[op["target_scope"]] = op["target_version"]
        return config

    async def definitions(self, scope_id):
        scope, actions = await authorize(self.db, self.actor, scope_id)
        rows = (
            await self.db.scalars(
                select(Definition).where(
                    or_(Definition.scope_id == SYSTEM_SCOPE, Definition.scope_id == scope_id)
                )
            )
        ).all()
        picked = {d.key: d for d in rows if d.scope_id == SYSTEM_SCOPE and d.version == 1}
        rows_by_id = {d.id: d for d in rows}
        pins = scope.config.get("definitions", {})
        missing_ids = {did for did in pins.values() if did and did not in rows_by_id}
        if missing_ids:
            extra = (
                await self.db.scalars(select(Definition).where(Definition.id.in_(missing_ids)))
            ).all()
            for d in extra:
                rows_by_id[d.id] = d
        for key, definition_id in pins.items():
            d = rows_by_id.get(definition_id)
            if d:
                picked[key] = d
        result = []
        for d in sorted(picked.values(), key=lambda d: (d.spec.get("domain", ""), d.key)):
            spec = view_spec(d)
            if "secret" not in actions:
                for rule in spec.get("properties", {}).values():
                    if rule.get("secret"):
                        rule.pop("default", None)
            result.append(
                {"id": d.id, "key": d.key, "version": d.version, "scope_id": d.scope_id, "spec": spec}
            )
        return result

    async def definition(self, scope, key):
        pin = scope.config.get("definitions", {}).get(key)
        row = (
            await self.db.get(Definition, pin)
            if pin
            else await self.db.scalar(
                select(Definition).where(
                    Definition.scope_id == SYSTEM_SCOPE, Definition.key == key, Definition.version == 1
                )
            )
        )
        require(row is not None, "unknown_kind", f"请先注册类型或关系：{key}")
        return ResolvedDefinition(row)

    async def revision_query(self, scope, as_of=None):
        chains = await self.lineage(scope, as_of)
        parts = [
            select(
                Revision.id.label("rid"),
                Revision.entity_id.label("eid"),
                Revision.version.label("v"),
                literal(rank).label("priority"),
            ).where(Revision.scope_id == sid, Revision.version <= version)
            for rank, (sid, version) in enumerate(chains)
        ]
        candidates = union_all(*parts).cte("revision_candidates")
        ranked = select(
            candidates.c.rid,
            func.row_number()
            .over(partition_by=candidates.c.eid, order_by=(candidates.c.priority, candidates.c.v.desc()))
            .label("r"),
        ).cte("latest_revisions")
        return select(Revision).join(ranked, Revision.id == ranked.c.rid).where(ranked.c.r == 1)

    async def raw_entity(self, scope, entity_id, as_of=None):
        statement = (await self.revision_query(scope, as_of)).where(Revision.entity_id == entity_id)
        row = await self.db.scalar(statement)
        require(row is not None, "not_found", "对象不存在或不属于当前视图", 404)
        return {
            **row.body,
            "id": entity_id,
            "revision": row.id,
            "version": f"{row.scope_id}:{row.version}",
            "content_hash": row.content_hash,
        }

    async def entity(self, scope_id, entity_id, query=None):
        query = query or Query()
        scope, actions = await authorize(self.db, self.actor, scope_id)
        body = await self.raw_entity(scope, entity_id, query.as_of)
        return await self.redact(scope, actions, body, query)

    async def _book_chapter_orders(self, scope, as_of=None):
        from ncc_data.domain.studio_catalog import ordered_book_chapters

        stmt = (await self.revision_query(scope, as_of)).where(
            Revision.body["deleted"].as_boolean().is_(False),
            Revision.body["kind"].astext.in_(["volume", "卷", "chapter", "章节"]),
        )
        rows = (await self.db.scalars(stmt.order_by(Revision.entity_id))).all()
        vols, chs = [], []
        for r in rows:
            b = r.body or {}
            entry = {"id": r.entity_id, "data": b.get("data") or {}}
            if b.get("kind") in {"volume", "卷"}:
                vols.append(entry)
            else:
                chs.append(entry)
        ordered = ordered_book_chapters(vols, chs)
        return {c["id"]: c["book_order"] for c in ordered}

    async def redact(self, scope, actions, body, query):
        definition = await self.db.get(Definition, body["definition_id"])
        return await self.redact_with_definitions(
            scope, actions, body, query, {body["definition_id"]: definition}
        )

    async def redact_with_definitions(
        self, scope, actions, body, query, definitions_by_id=None, book_orders=None, cutoff_obj=None
    ):
        require(
            not body.get("secret") or ("secret" in actions and query.role == "author"),
            "not_found",
            "对象不可访问",
            404,
        )
        require(not body.get("deleted") or query.include_deleted, "not_found", "对象已停用", 404)
        if query.role != "author":
            # A restricted view must never serialize an unpublished future chapter or outline.
            require(
                body["kind"] not in {"outline", "大纲", "细纲", "主线", "暗线"},
                "not_found",
                "当前视角不可访问",
                404,
            )
            if body["kind"] in {"chapter", "章节", "scene", "场景"}:
                require(query.chapter_id is not None, "view_context", "受限文本视图必须指定叙述截止章节")
                cutoff = (
                    cutoff_obj
                    if cutoff_obj is not None
                    else await self.raw_entity(scope, query.chapter_id, query.as_of)
                )
                orders = book_orders if book_orders is not None else await self._book_chapter_orders(scope, query.as_of)
                cutoff_order = orders.get(query.chapter_id)
                if body["kind"] in {"chapter", "章节"} and body.get("id") in orders and cutoff_order is not None:
                    allowed_pos = orders[body["id"]] <= cutoff_order
                elif (
                    body["kind"] in {"scene", "场景"}
                    and (body.get("data") or {}).get("chapter_id") in orders
                    and cutoff_order is not None
                ):
                    allowed_pos = orders[body["data"]["chapter_id"]] <= cutoff_order
                else:
                    allowed_pos = safe_int_position(
                        body.get("data", {}).get("position"), 2_147_483_647
                    ) <= safe_int_position(cutoff.get("data", {}).get("position"), -1)
                require(
                    allowed_pos,
                    "not_found",
                    "当前视角不可访问",
                    404,
                )
        def_id = body.get("definition_id")
        if definitions_by_id is not None and def_id in definitions_by_id:
            definition = definitions_by_id[def_id]
        else:
            definition = await self.db.get(Definition, def_id) if def_id else None
        properties = definition.spec.get("properties", {}) if definition else {}
        can_secret = "secret" in actions and query.role == "author"
        data = {
            k: v
            for k, v in body.get("data", {}).items()
            if can_secret or not properties.get(k, {}).get("secret")
        }
        spec = view_spec(definition) if definition else {}
        if not can_secret:
            for rule in spec.get("properties", {}).values():
                if rule.get("secret"):
                    rule.pop("default", None)
        # Definitions can contain secret defaults; only public field descriptors are returned elsewhere.
        return {**body, "data": data, "definition_spec": spec}

    async def entities(self, scope_id, query=None):
        query = query or Query()
        scope, actions = await authorize(self.db, self.actor, scope_id)
        statement = await self.revision_query(scope, query.as_of)
        body = Revision.body
        if not query.include_deleted:
            statement = statement.where(body["deleted"].as_boolean().is_(False))
        if "secret" not in actions or query.role != "author":
            statement = statement.where(body["secret"].as_boolean().is_(False))
        if query.kind:
            statement = statement.where(body["kind"].astext == query.kind)
        if query.kinds:
            statement = statement.where(body["kind"].astext.in_(query.kinds))
        if query.exclude_kinds:
            statement = statement.where(func.coalesce(body["kind"].astext, "").not_in(query.exclude_kinds))
        if query.q:
            # Literal substring semantics support CJK names without assuming an English parser segments Chinese.
            q = query.q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            statement = statement.where(
                or_(
                    body["name"].astext.ilike(f"%{q}%", escape="\\"),
                    body["text"].astext.ilike(f"%{q}%", escape="\\"),
                )
            )
        defs = await self.definitions(scope_id) if query.filters else []
        for condition in query.filters:
            require(set(condition) <= {"field", "op", "value"}, "filter", "筛选含未知字段")
            field, op, value = condition.get("field"), condition.get("op"), condition.get("value")
            require(isinstance(field, str) and 0 < len(field) <= 128, "filter", "无效筛选属性")
            # Secret fields must not become an oracle through matching counts.
            rules = [x["spec"].get("properties", {}).get(field) for x in defs]
            rules = [x for x in rules if x]
            require(
                rules and ("secret" in actions or not any(x.get("secret") for x in rules)),
                "filter",
                "属性不可筛选",
            )
            if "secret" not in actions:
                protected = select(Definition.id).where(
                    Definition.spec["properties"][field]["secret"].as_boolean().is_(True)
                )
                statement = statement.where(body["definition_id"].astext.not_in(protected))
            col = body["data"][field].astext
            if op == "eq":
                statement = statement.where(col == str(value))
            elif op == "in":
                require(
                    isinstance(value, list) and 1 <= len(value) <= 64,
                    "filter",
                    "集合条件需要1至64项列表",
                )
                statement = statement.where(col.in_([str(v) for v in value]))
            elif op == "contains":
                require(isinstance(value, str), "filter", "包含条件需要字符串")
                escaped = value.replace("%", "\\%").replace("_", "\\_")
                statement = statement.where(col.ilike(f"%{escaped}%", escape="\\"))
            elif op in {"gte", "lte"}:
                require(
                    all(x["type"] in {"integer", "decimal"} for x in rules),
                    "filter",
                    "仅数值属性支持范围查询",
                )
                try:
                    number = Decimal(str(value))
                    require(number.is_finite(), "filter", "无效数值")
                except Exception:
                    raise DomainError("filter", "无效数值") from None
                statement = statement.where(
                    cast(col, Numeric) >= number if op == "gte" else cast(col, Numeric) <= number
                )
            else:
                raise DomainError("filter", "不支持的筛选运算符")
        book_orders = None
        cutoff = None
        if query.role != "author":
            statement = statement.where(
                body["kind"].astext.not_in(["outline", "大纲", "细纲", "主线", "暗线"])
            )
            require(query.chapter_id is not None, "view_context", "受限查询必须指定叙述截止章节")
            cutoff = await self.raw_entity(scope, query.chapter_id, query.as_of)
            position = safe_int_position(cutoff.get("data", {}).get("position"), -1)
            book_orders = await self._book_chapter_orders(scope, query.as_of)
            cutoff_order = book_orders.get(query.chapter_id)
            if cutoff_order is not None:
                allowed_ch_ids = [cid for cid, ord_no in book_orders.items() if ord_no <= cutoff_order]
                is_ch = body["kind"].astext.in_(["chapter", "章节"])
                is_sc = body["kind"].astext.in_(["scene", "场景"])
                sc_ok = or_(
                    body["data"]["chapter_id"].astext.in_(allowed_ch_ids),
                    and_(
                        body["data"]["chapter_id"].astext.is_(None),
                        _sql_position(body["data"]["position"].astext) <= position,
                    ),
                )
                statement = statement.where(
                    or_(
                        and_(~is_ch, ~is_sc),
                        and_(is_ch, Revision.entity_id.in_(allowed_ch_ids)),
                        and_(is_sc, sc_ok),
                    )
                )
            else:
                narrative = body["kind"].astext.in_(["chapter", "章节", "scene", "场景"])
                statement = statement.where(
                    or_(~narrative, _sql_position(body["data"]["position"].astext) <= position)
                )
        total = int(
            (await self.db.scalar(select(func.count()).select_from(statement.subquery("filtered_entities"))))
            or 0
        )
        name_col = body["name"].astext
        if query.sort == "name":
            order_clauses = [name_col.desc() if query.descending else name_col.asc(), Revision.entity_id.asc()]
        elif query.sort == "position":
            fallback = -2_147_483_648 if query.descending else 2_147_483_647
            pos_expr = _sql_position(body["data"]["position"].astext, fallback=fallback)
            order_clauses = [
                pos_expr.desc() if query.descending else pos_expr.asc(),
                name_col.asc(),
                Revision.entity_id.asc(),
            ]
        elif query.sort == "created_at":
            order_clauses = [
                Revision.created_at.desc() if query.descending else Revision.created_at.asc(),
                name_col.asc(),
                Revision.entity_id.asc(),
            ]
        else:
            order_clauses = [
                Revision.version.desc(),
                Revision.created_at.desc(),
                name_col.asc(),
                Revision.entity_id.asc(),
            ]
        statement = statement.order_by(*order_clauses)
        rows = (await self.db.scalars(statement.offset(query.offset).limit(query.limit + 1))).all()
        page_rows = rows[: query.limit]
        def_ids = {r.body.get("definition_id") for r in page_rows if r.body.get("definition_id")}
        defs_by_id = {}
        if def_ids:
            def_rows = (await self.db.scalars(select(Definition).where(Definition.id.in_(def_ids)))).all()
            defs_by_id = {d.id: d for d in def_rows}
        items = []
        for row in page_rows:
            obj = {
                **row.body,
                "id": row.entity_id,
                "revision": row.id,
                "version": f"{row.scope_id}:{row.version}",
                "content_hash": row.content_hash,
            }
            obj = await self.redact_with_definitions(
                scope, actions, obj, query, defs_by_id, book_orders=book_orders, cutoff_obj=cutoff
            )
            obj["text_preview"] = obj.pop("text", "")[:200]
            obj.pop("definition_spec", None)
            items.append(obj)
        return {
            "items": items,
            "total": total,
            "offset": query.offset,
            "limit": query.limit,
            "next_offset": query.offset + query.limit if len(rows) > query.limit else None,
            "version": scope.version,
            "as_of": query.as_of,
            "count": len(items),
        }

    async def raw_facts(self, scope, as_of=None):
        chains = await self.lineage(scope, as_of)
        rows = []
        for sid, version in reversed(chains):
            found = (
                await self.db.scalars(
                    select(Fact).where(
                        Fact.scope_id == sid,
                        Fact.recorded_from <= version,
                        or_(Fact.recorded_to.is_(None), Fact.recorded_to > version),
                    )
                )
            ).all()
            superseded = {f.supersedes for f in found if f.supersedes}
            rows = [f for f in rows if f.id not in superseded]
            rows.extend(found)
        return [f for f in rows if f.category != "retraction"]

    async def facts(self, scope_id, query=None):
        query = query or StateQuery()
        scope, actions = await authorize(self.db, self.actor, scope_id)
        rows = await self.raw_facts(scope, query.as_of)
        cutoff = None
        cutoff_chapter = None
        if query.chapter_id:
            cutoff_chapter = await self.raw_entity(scope, query.chapter_id, query.as_of)
            cutoff = cutoff_chapter.get("data", {}).get("position")
        require(query.role == "author" or cutoff is not None, "view_context", "受限事实查询需要叙述截止点")
        can_secret = "secret" in actions and query.role == "author"
        prefiltered = []
        for row in rows:
            if row.secret and not can_secret:
                continue
            if query.subject_id and row.subject_id != query.subject_id:
                continue
            if query.predicate and row.predicate != query.predicate:
                continue
            if query.category and row.category != query.category:
                continue
            if query.role != "author" and (row.category == "plan" or not row.chapter_id):
                continue
            prefiltered.append(row)

        raw_by_id: dict[str, dict] = {}
        defs_by_id: dict[str, Definition] = {}
        book_orders = None
        if prefiltered:
            candidate_ids: set[str] = set()
            for row in prefiltered:
                candidate_ids.add(row.subject_id)
                if row.object_id:
                    candidate_ids.add(row.object_id)
                src_eid = (row.source or {}).get("entity_id")
                if src_eid:
                    candidate_ids.add(src_eid)
                if cutoff is not None and row.chapter_id:
                    candidate_ids.add(row.chapter_id)
            rev_stmt = (await self.revision_query(scope, query.as_of)).where(
                Revision.entity_id.in_(candidate_ids)
            )
            rev_rows = (await self.db.scalars(rev_stmt)).all()
            for r in rev_rows:
                raw_by_id[r.entity_id] = {
                    **r.body,
                    "id": r.entity_id,
                    "revision": r.id,
                    "version": f"{r.scope_id}:{r.version}",
                    "content_hash": r.content_hash,
                }
            def_ids = {
                obj.get("definition_id")
                for obj in raw_by_id.values()
                if obj.get("definition_id")
            }
            if def_ids:
                def_rows = (
                    await self.db.scalars(select(Definition).where(Definition.id.in_(def_ids)))
                ).all()
                defs_by_id = {d.id: d for d in def_rows}
            if query.role != "author" and any(
                obj.get("kind") in {"chapter", "章节", "scene", "场景"} for obj in raw_by_id.values()
            ):
                book_orders = await self._book_chapter_orders(scope, query.as_of)

        subj_query = Query(
            as_of=query.as_of,
            role=query.role,
            chapter_id=query.chapter_id,
            include_deleted=query.include_deleted,
        )
        src_query = Query(
            as_of=query.as_of,
            role=query.role,
            chapter_id=query.chapter_id,
            include_deleted=True,
        )
        entity_ok_cache: dict[tuple[str, bool], bool] = {}
        foreign_ref_cache: dict[str, bool] = {}

        async def _entity_visible(eid: str, inc_del: bool) -> bool:
            ck = (eid, inc_del)
            if ck in entity_ok_cache:
                return entity_ok_cache[ck]
            raw_obj = raw_by_id.get(eid)
            if raw_obj is None:
                entity_ok_cache[ck] = False
                return False
            try:
                await self.redact_with_definitions(
                    scope,
                    actions,
                    raw_obj,
                    src_query if inc_del else subj_query,
                    defs_by_id,
                    book_orders=book_orders,
                    cutoff_obj=cutoff_chapter,
                )
                entity_ok_cache[ck] = True
            except DomainError:
                entity_ok_cache[ck] = False
            return entity_ok_cache[ck]

        async def _object_visible(oid: str) -> bool:
            raw_obj = raw_by_id.get(oid)
            if raw_obj is not None:
                if raw_obj.get("deleted") and not query.include_deleted:
                    return False
                if raw_obj.get("secret") and not can_secret:
                    return False
                return True
            if oid in foreign_ref_cache:
                return foreign_ref_cache[oid]
            try:
                await self.reference(
                    scope,
                    oid,
                    secret=can_secret,
                    as_of=query.as_of,
                    include_deleted=query.include_deleted,
                )
                foreign_ref_cache[oid] = True
            except DomainError:
                foreign_ref_cache[oid] = False
            return foreign_ref_cache[oid]

        items, uncertain = [], 0
        for row in prefiltered:
            if not await _entity_visible(row.subject_id, query.include_deleted):
                continue
            if row.object_id and not await _object_visible(row.object_id):
                continue
            src_eid = (row.source or {}).get("entity_id")
            if src_eid and not await _entity_visible(src_eid, True):
                continue
            if cutoff is not None and row.chapter_id:
                chapter = raw_by_id.get(row.chapter_id)
                if chapter is None:
                    chapter = await self.raw_entity(scope, row.chapter_id, query.as_of)
                if safe_int_position(chapter.get("data", {}).get("position"), 2_147_483_647) > safe_int_position(
                    cutoff, -1
                ):
                    continue
            if query.world_at is not None:
                require(query.calendar is not None, "calendar", "世界时点查询必须指定历法")
                if row.calendar != query.calendar:
                    uncertain += 1
                    continue
                if row.world_from is not None and row.world_from > query.world_at:
                    continue
                if row.world_to is not None and row.world_to <= query.world_at:
                    continue
            items.append(
                jsonable(
                    {
                        "id": row.id,
                        "subject_id": row.subject_id,
                        "predicate": row.predicate,
                        "category": row.category,
                        "object_id": row.object_id,
                        "value": row.value,
                        "secret": row.secret,
                        "calendar": row.calendar,
                        "world_from": row.world_from,
                        "world_to": row.world_to,
                        "chapter_id": row.chapter_id,
                        "recorded_from": row.recorded_from,
                        "source": row.source,
                        "supersedes": row.supersedes,
                    }
                )
            )
        return {
            "items": items[query.offset : query.offset + query.limit],
            "total": len(items),
            "uncertain_time_count": uncertain,
            "version": scope.version,
            "as_of": query.as_of,
        }

    async def reference(self, scope, entity_id, secret=True, as_of=None, include_deleted=False):
        _, current_actions = await authorize(self.db, self.actor, scope.id)
        secret = secret and "secret" in current_actions
        row = await self.db.get(Entity, entity_id)
        require(row is not None, "reference", "引用对象尚未解析")
        chain = {sid for sid, _ in await self.lineage(scope, as_of)}
        if row.scope_id in chain:
            obj = await self.raw_entity(scope, entity_id, as_of)
        else:
            pin = (await self.configuration_at(scope, as_of)).get("adoptions", {}).get(row.scope_id)
            require(pin is not None, "cross_scope", "跨范围引用须先显式采用固定版本")
            target, actions = await authorize(self.db, self.actor, row.scope_id)
            secret = secret and "secret" in actions
            obj = await self.raw_entity(target, entity_id, pin)
        require(not obj.get("deleted") or include_deleted, "reference", "引用对象已停用")
        require(not obj.get("secret") or secret, "reference", "引用不可访问")
        return obj

    async def history(self, scope_id, entity_id):
        scope, _ = await authorize(self.db, self.actor, scope_id)
        await self.entity(scope_id, entity_id, Query(include_deleted=True))
        chains = await self.lineage(scope)
        rows = (
            await self.db.scalars(
                select(Revision)
                .where(
                    or_(*[and_(Revision.scope_id == sid, Revision.version <= pin) for sid, pin in chains]),
                    Revision.entity_id == entity_id,
                )
                .order_by(Revision.created_at.desc())
                .limit(200)
            )
        ).all()
        return [
            {
                "id": r.id,
                "scope_id": r.scope_id,
                "version": r.version,
                "created_at": r.created_at.isoformat(),
                "hash": r.content_hash,
                "change_id": r.change_id,
            }
            for r in rows
        ]

    async def revision(self, scope_id, entity_id, revision_id):
        scope, actions = await authorize(self.db, self.actor, scope_id)
        row = await self.db.get(Revision, revision_id)
        chains = dict(await self.lineage(scope))
        require(
            row
            and row.entity_id == entity_id
            and row.scope_id in chains
            and row.version <= chains[row.scope_id],
            "not_found",
            "修订不存在或不在此基线",
            404,
        )
        return await self.redact(
            scope,
            actions,
            {
                **row.body,
                "id": entity_id,
                "revision": row.id,
                "version": f"{row.scope_id}:{row.version}",
                "content_hash": row.content_hash,
            },
            Query(include_deleted=True),
        )
