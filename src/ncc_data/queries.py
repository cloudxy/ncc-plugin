import copy
from decimal import Decimal

from sqlalchemy import Integer, Numeric, and_, cast, func, literal, or_, select, union_all

from .contracts import Query, ScopeInput, StateQuery
from .errors import DomainError, require
from .models import ChangeSet, Definition, Entity, Fact, Membership, Revision, Scope
from .policy import SYSTEM_SCOPE
from .security import authorize
from .utils import jsonable


class QueryService:
    def __init__(self, db, actor):
        self.db, self.actor = db, actor

    async def scopes(self):
        members = select(Membership.scope_id).where(Membership.user_id == self.actor.id)
        statement = select(Scope).where(or_(Scope.owner_id == self.actor.id, Scope.id.in_(members)))
        if hasattr(self.actor, "_access_scope"):
            statement = statement.where(Scope.id == self.actor._access_scope)
        rows = (await self.db.scalars(statement.order_by(Scope.created_at))).all()
        result = []
        for row in rows:
            try:
                result.append(await self.scope_info(row.id))
            except DomainError as exc:
                if exc.status not in {403, 404}:
                    raise
        return result

    async def scope_info(self, scope_id):
        row, actions = await authorize(self.db, self.actor, scope_id)
        config = {k: v for k, v in row.config.items() if k != "views"} if "admin" in actions else {}
        config["views"] = row.config.get("views", {}).get(self.actor.id, {})
        return {
            "id": row.id,
            "name": row.name,
            "kind": row.kind,
            "version": row.version,
            "parent_id": row.parent_id,
            "base_id": row.base_id,
            "base_version": row.base_version,
            "actions": sorted(actions),
            "config": config,
        }

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
        return await self.scope_info(row.id)

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
        pins = scope.config.get("definitions", {})
        for key, definition_id in pins.items():
            d = await self.db.get(Definition, definition_id)
            if d:
                picked[key] = d
        result = []
        for d in sorted(picked.values(), key=lambda d: (d.spec.get("domain", ""), d.key)):
            spec = copy.deepcopy(d.spec)
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
        return row

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

    async def redact(self, scope, actions, body, query):
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
                cutoff = await self.raw_entity(scope, query.chapter_id, query.as_of)
                require(
                    body.get("data", {}).get("position", 10**12)
                    <= cutoff.get("data", {}).get("position", -1),
                    "not_found",
                    "当前视角不可访问",
                    404,
                )
        definition = await self.db.get(Definition, body["definition_id"])
        properties = definition.spec.get("properties", {}) if definition else {}
        can_secret = "secret" in actions and query.role == "author"
        data = {
            k: v
            for k, v in body.get("data", {}).items()
            if can_secret or not properties.get(k, {}).get("secret")
        }
        spec = copy.deepcopy(definition.spec) if definition else {}
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
        if query.q:
            # Literal substring semantics support CJK names without assuming an English parser segments Chinese.
            q = query.q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            statement = statement.where(
                or_(
                    body["name"].astext.ilike(f"%{q}%", escape="\\"),
                    body["text"].astext.ilike(f"%{q}%", escape="\\"),
                )
            )
        for condition in query.filters:
            require(set(condition) <= {"field", "op", "value"}, "filter", "筛选含未知字段")
            field, op, value = condition.get("field"), condition.get("op"), condition.get("value")
            require(isinstance(field, str) and 0 < len(field) <= 128, "filter", "无效筛选属性")
            # Secret fields must not become an oracle through matching counts.
            defs = await self.definitions(scope_id)
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
        if query.role != "author":
            statement = statement.where(
                body["kind"].astext.not_in(["outline", "大纲", "细纲", "主线", "暗线"])
            )
            require(query.chapter_id is not None, "view_context", "受限查询必须指定叙述截止章节")
            cutoff = await self.raw_entity(scope, query.chapter_id, query.as_of)
            position = int(cutoff.get("data", {}).get("position", -1))
            narrative = body["kind"].astext.in_(["chapter", "章节", "scene", "场景"])
            statement = statement.where(
                or_(~narrative, cast(body["data"]["position"].astext, Integer) <= position)
            )
        ordering = (
            body["name"].astext if query.sort == "name" else cast(body["data"]["position"].astext, Integer)
        )
        statement = statement.order_by(ordering.desc() if query.descending else ordering, Revision.entity_id)
        rows = (await self.db.scalars(statement.offset(query.offset).limit(query.limit + 1))).all()
        items = []
        for row in rows[: query.limit]:
            obj = {
                **row.body,
                "id": row.entity_id,
                "revision": row.id,
                "version": f"{row.scope_id}:{row.version}",
                "content_hash": row.content_hash,
            }
            obj = await self.redact(scope, actions, obj, query)
            obj["text_preview"] = obj.pop("text", "")[:200]
            obj.pop("definition_spec", None)
            items.append(obj)
        return {
            "items": items,
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
        if query.chapter_id:
            chapter = await self.raw_entity(scope, query.chapter_id, query.as_of)
            cutoff = chapter.get("data", {}).get("position")
        require(query.role == "author" or cutoff is not None, "view_context", "受限事实查询需要叙述截止点")
        items, uncertain = [], 0
        for row in rows:
            if row.secret and ("secret" not in actions or query.role != "author"):
                continue
            try:
                await self.entity(
                    scope_id,
                    row.subject_id,
                    Query(
                        as_of=query.as_of,
                        role=query.role,
                        chapter_id=query.chapter_id,
                        include_deleted=query.include_deleted,
                    ),
                )
                if row.object_id:
                    await self.reference(
                        scope,
                        row.object_id,
                        secret="secret" in actions and query.role == "author",
                        as_of=query.as_of,
                        include_deleted=query.include_deleted,
                    )
                if row.source.get("entity_id"):
                    await self.entity(
                        scope_id,
                        row.source["entity_id"],
                        Query(
                            as_of=query.as_of,
                            role=query.role,
                            chapter_id=query.chapter_id,
                            include_deleted=True,
                        ),
                    )
            except DomainError:
                continue
            if query.subject_id and row.subject_id != query.subject_id:
                continue
            if query.predicate and row.predicate != query.predicate:
                continue
            if query.category and row.category != query.category:
                continue
            if query.role != "author" and (row.category == "plan" or not row.chapter_id):
                continue
            if cutoff is not None and row.chapter_id:
                chapter = await self.raw_entity(scope, row.chapter_id, query.as_of)
                if chapter.get("data", {}).get("position", 10**12) > cutoff:
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
