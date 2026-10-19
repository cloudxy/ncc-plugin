import copy

from sqlalchemy import func, select

from .contracts import ChangeInput, DefinitionInput, FactInput
from .errors import DomainError, require
from .models import Attachment, Audit, ChangeSet, Definition, Entity, Fact, Job, Receipt, Revision, uid
from .policy import POLICY_HASH
from .queries import QueryService
from .security import authorize
from .utils import digest, search_tokens
from .validation import validate_definition, validate_values


class ChangeService(QueryService):
    async def change(self, scope_id, change_id, action="read", lock=False):
        scope, actions = await authorize(self.db, self.actor, scope_id, action, lock=lock)
        row = await self.db.get(ChangeSet, change_id)
        require(row is not None and row.scope_id == scope_id, "not_found", "变更不存在", 404)
        require(row.actor_id == self.actor.id or "secret" in actions, "not_found", "变更不可访问", 404)
        require(
            not row.validation.get("requires_secret", True) or "secret" in actions,
            "not_found",
            "变更不可访问",
            404,
        )
        return scope, actions, row

    def change_json(self, row):
        return {
            "id": row.id,
            "title": row.title,
            "base_version": row.base_version,
            "draft_version": row.draft_version,
            "operations": row.operations,
            "state": row.state,
            "validation": row.validation,
            "applied_version": row.applied_version,
            "created_at": row.created_at.isoformat(),
        }

    async def create_change(self, scope_id, value: ChangeInput):
        scope, actions = await authorize(self.db, self.actor, scope_id, "edit")
        require(
            value.base_version == scope.version,
            "version_conflict",
            "内容范围已变化，请刷新后比较",
            409,
            current_version=scope.version,
        )
        operations = [op.model_dump(mode="json", exclude_none=True) for op in value.operations]
        for op in operations:
            if op["op"] == "create":
                op["entity_id"] = op.get("entity_id") or uid()
        row = ChangeSet(
            scope_id=scope_id,
            actor_id=self.actor.id,
            title=value.title,
            base_version=value.base_version,
            operations=operations,
            validation={"requires_secret": "secret" in actions},
        )
        self.db.add(row)
        await self.db.flush()
        return self.change_json(row)

    async def edit_change(self, scope_id, change_id, value):
        scope, _, row = await self.change(scope_id, change_id, "edit", lock=True)
        require(row.state not in {"applied", "withdrawn"}, "change_state", "已采用/撤销的变更不可编辑", 409)
        require(row.draft_version == value.draft_version, "precondition", "草稿版本已变化", 412)
        require(value.base_version == scope.version, "version_conflict", "范围版本已变化", 409)
        operations = [op.model_dump(mode="json", exclude_none=True) for op in value.operations]
        for op in operations:
            if op["op"] == "create":
                op["entity_id"] = op.get("entity_id") or uid()
        row.title, row.operations, row.base_version = value.title, operations, value.base_version
        row.draft_version += 1
        row.state, row.validation, row.approved_hash, row.approver_id = (
            "draft",
            {"requires_secret": row.validation.get("requires_secret", True)},
            None,
            None,
        )
        return self.change_json(row)

    def approval_digest(self, row):
        return digest(
            {
                "operations": row.operations,
                "base": row.base_version,
                "draft": row.draft_version,
                "policy": POLICY_HASH,
                "contract": 1,
            }
        )

    async def validate_change(self, scope_id, change_id):
        scope, _, row = await self.change(scope_id, change_id, "edit", lock=True)
        require(row.state != "applied", "change_state", "已采用变更无需重复预检", 409)
        report = {"valid": False, "errors": [], "impacts": []}
        if row.base_version != scope.version:
            report["errors"] = [
                {"code": "version_conflict", "detail": "范围版本已变化", "current_version": scope.version}
            ]
        else:
            nested = await self.db.begin_nested()
            try:
                report["impacts"] = await self._operations(scope, row)
                await self.db.flush()
                report["valid"] = True
            except DomainError as exc:
                report["errors"] = [{"code": exc.code, "detail": exc.detail, **exc.extra}]
            finally:
                await nested.rollback()
            await self.db.refresh(scope)
            await self.db.refresh(row)
        row.validation = {
            "requires_secret": row.validation.get("requires_secret", True),
            **report,
            "fingerprint": self.approval_digest(row),
            "checked_version": scope.version,
        }
        row.state = "validated" if report["valid"] else "draft"
        return self.change_json(row)

    async def approve_change(self, scope_id, change_id):
        scope, _, row = await self.change(scope_id, change_id, "adopt", lock=True)
        require(
            row.state == "validated" and row.validation.get("valid"), "not_validated", "请先完成预检", 409
        )
        require(row.base_version == scope.version, "version_conflict", "批准依据已过期", 409)
        require(
            row.validation.get("fingerprint") == self.approval_digest(row),
            "stale_validation",
            "草稿或规则已变化",
            409,
        )
        if scope.config.get("separate_approval"):
            require(row.actor_id != self.actor.id, "separate_approval", "此范围要求另一位批准者", 403)
        row.approved_hash, row.approver_id, row.state = self.approval_digest(row), self.actor.id, "approved"
        return self.change_json(row)

    async def apply_change(self, scope_id, change_id, key):
        require(isinstance(key, str) and 1 <= len(key) <= 128, "idempotency", "采用操作必须提供幂等键")
        scope, _, row = await self.change(scope_id, change_id, "adopt", lock=True)
        request_hash = digest({"change": row.id, "draft": row.draft_version, "ops": row.operations})
        receipt = await self.db.scalar(
            select(Receipt).where(
                Receipt.scope_id == scope_id, Receipt.actor_id == self.actor.id, Receipt.key == key
            )
        )
        if receipt:
            require(
                receipt.request_hash == request_hash, "idempotency_reuse", "同一幂等键不能用于不同内容", 409
            )
            return receipt.result
        if row.state == "applied":
            return {"change_id": row.id, "version": row.applied_version, "already_applied": True}
        require(
            row.state == "approved" and row.approved_hash == self.approval_digest(row),
            "approval_required",
            "采用需要有效批准",
            409,
        )
        require(
            row.base_version == scope.version,
            "version_conflict",
            "范围已变化，请重新比较与预检",
            409,
            current_version=scope.version,
        )
        # Recheck the approver's current privileges, even when a different actor applies it.
        from .models import User

        approver = await self.db.get(User, row.approver_id)
        require(approver is not None and approver.active, "approval_revoked", "批准者已不可用", 403)
        await authorize(self.db, approver, scope_id, "adopt")
        impacts = await self._operations(scope, row)
        row.state, row.applied_version = "applied", scope.version
        result = {"change_id": row.id, "version": scope.version, "impacts": impacts}
        self.db.add(
            Receipt(
                scope_id=scope_id, actor_id=self.actor.id, key=key, request_hash=request_hash, result=result
            )
        )
        self.db.add(
            Audit(
                scope_id=scope_id,
                actor_id=self.actor.id,
                action="change.apply",
                version=scope.version,
                detail={"change_id": row.id, "title": row.title, "operations_hash": digest(row.operations)},
            )
        )
        self.db.add(
            Job(scope_id=scope_id, actor_id=self.actor.id, kind="index", payload={"version": scope.version})
        )
        await self.db.flush()
        return result

    async def adopt(self, scope_id, change_id, key):
        """A single author action; not an alternative business write path."""
        _, _, row = await self.change(scope_id, change_id, "adopt")
        if row.state == "applied":
            return await self.apply_change(scope_id, change_id, key)
        result = await self.validate_change(scope_id, change_id)
        require(
            result["validation"]["valid"],
            "validation_failed",
            "变更预检未通过",
            409,
            errors=result["validation"]["errors"],
        )
        await self.approve_change(scope_id, change_id)
        return await self.apply_change(scope_id, change_id, key)

    async def _save_body(self, scope, identity, body, change_id):
        content_hash = digest(body)
        row = await self.db.scalar(
            select(Revision).where(
                Revision.scope_id == scope.id,
                Revision.entity_id == identity.id,
                Revision.version == scope.version,
            )
        )
        if row is None:
            self.db.add(
                Revision(
                    scope_id=scope.id,
                    entity_id=identity.id,
                    version=scope.version,
                    body=body,
                    content_hash=content_hash,
                    change_id=change_id,
                )
            )
        else:
            # Coalesce multiple operations before the transaction commits; never edit a committed revision.
            row.body, row.content_hash = body, content_hash
        if identity.scope_id == scope.id:
            identity.name, identity.data, identity.text = body["name"], body["data"], body["text"]
            identity.current_version, identity.secret, identity.deleted = (
                scope.version,
                body["secret"],
                body["deleted"],
            )
            identity.search_vector = func.to_tsvector(
                "simple", search_tokens(body["name"] + " " + body["text"])
            )
        await self.db.flush()

    async def _validate_refs(self, scope, spec, data, actions, previous_data=None):
        for key, value in data.items():
            rule = spec["properties"][key]
            if rule.get("secret") and "secret" not in actions:
                require(
                    previous_data is not None and key in previous_data and previous_data[key] == value,
                    "secret_field",
                    "无权编辑秘密属性",
                    403,
                    field=key,
                )
                continue
            if rule["type"] in {"reference", "references"}:
                refs = value if rule["type"] == "references" else [value]
                for ref in refs:
                    obj = await self.reference(scope, ref, secret="secret" in actions)
                    require(
                        not rule.get("kinds") or obj["kind"] in rule["kinds"],
                        "reference_type",
                        "引用对象类型不符",
                        field=key,
                    )
            if rule["type"] == "attachment":
                attachment = await self.db.get(Attachment, value)
                require(
                    attachment is not None and attachment.scope_id == scope.id,
                    "attachment",
                    "附件不属于当前范围",
                )

    async def _operations(self, scope, change):
        _, actions = await authorize(self.db, self.actor, scope.id, "edit")
        scope.version += 1
        await self.db.flush()
        impacts = []
        # Publish definitions first, then stage all identities/revisions so cyclic and forward
        # references are validated against the complete transaction, never against row order.
        ordered = sorted(change.operations, key=lambda op: 0 if op["op"] in {"definition", "adopt"} else 1)
        staged = {}
        for op in ordered:
            if op["op"] != "create":
                continue
            entity_id = op["entity_id"]
            require(
                entity_id not in staged and await self.db.get(Entity, entity_id) is None,
                "identity_exists",
                "对象身份已存在或在同批重复",
                409,
            )
            # Definitions in this same change are resolved below before staging creates.
            staged[entity_id] = op
        for op in ordered:
            action = op["op"]
            if action == "definition":
                require("admin" in actions, "definition_permission", "发布定义需要范围管理权限", 403)
                require("secret" in actions, "definition_permission", "发布定义需要完整范围权限", 403)
                value = DefinitionInput.model_validate(op.get("definition"))
                validate_definition(value.spec)
                exists = await self.db.scalar(
                    select(Definition).where(
                        Definition.scope_id == scope.id,
                        Definition.key == value.key,
                        Definition.version == value.version,
                    )
                )
                require(exists is None, "definition_version", "定义版本已存在，不得覆盖", 409)
                definition = Definition(
                    scope_id=scope.id, key=value.key, version=value.version, spec=value.spec
                )
                self.db.add(definition)
                await self.db.flush()
                config = copy.deepcopy(scope.config)
                config.setdefault("definitions", {})[value.key] = definition.id
                scope.config = config
                impacts.append({"kind": "definition", "key": value.key, "version": value.version})
                continue
            if action == "adopt":
                target, target_actions = await authorize(self.db, self.actor, op.get("target_scope"), "read")
                require(
                    "export" in target_actions and "secret" in target_actions,
                    "share_permission",
                    "完整范围采用需要来源导出与秘密内容权限",
                    403,
                )
                require(target.id != scope.id, "adoption", "不能采用自身")
                pin = op.get("target_version")
                require(isinstance(pin, int) and 0 <= pin <= target.version, "adoption", "采用版本无效")
                config = copy.deepcopy(scope.config)
                config.setdefault("adoptions", {})[target.id] = pin
                scope.config = config
                impacts.append({"kind": "adoption", "scope_id": target.id, "version": pin})
                continue
            entity_id = op.get("entity_id")
            require(entity_id, "entity_id", "操作必须指定对象")
            if action == "create":
                if staged:
                    for pending_id, pending in list(staged.items()):
                        require(
                            pending.get("kind") and pending.get("name"), "entity", "创建必须指定类型和名称"
                        )
                        pending_def = await self.definition(scope, pending["kind"])
                        require(not pending_def.spec.get("relation"), "kind", "关系类型不能直接作为对象类型")
                        pending_body = {
                            "kind": pending["kind"],
                            "name": pending["name"],
                            "data": copy.deepcopy(pending.get("data", {})),
                            "text": pending.get("text", ""),
                            "secret": pending.get("secret", False),
                            "deleted": False,
                            "definition_id": pending_def.id,
                        }
                        if pending["kind"] in {"chapter", "章节"} and "position" not in pending_body["data"]:
                            from .contracts import Query

                            latest = await self.entities(
                                scope.id,
                                Query(kind=pending["kind"], sort="position", descending=True, limit=1),
                            )
                            pending_body["data"]["position"] = (
                                max([int(i["data"].get("position", 0)) for i in latest["items"]] + [0]) + 1
                            )
                        validate_values(pending_def.spec, pending_body["data"])
                        pending_entity = Entity(
                            id=pending_id,
                            scope_id=scope.id,
                            kind=pending["kind"],
                            current_version=scope.version,
                            name=pending_body["name"],
                            data=pending_body["data"],
                            text=pending_body["text"],
                            secret=pending_body["secret"],
                        )
                        self.db.add(pending_entity)
                        await self.db.flush()
                        await self._save_body(scope, pending_entity, pending_body, change.id)
                    staged.clear()
                require(op.get("kind") and op.get("name"), "entity", "创建必须指定类型和名称")
                definition = await self.definition(scope, op["kind"])
                require(not definition.spec.get("relation"), "kind", "关系类型不能直接作为对象类型")
                staged_body = await self.raw_entity(scope, entity_id)
                body = {
                    k: staged_body[k]
                    for k in ("kind", "name", "data", "text", "secret", "deleted", "definition_id")
                }
                identity = await self.db.get(Entity, entity_id)
            else:
                previous = await self.raw_entity(scope, entity_id)
                require(not previous.get("secret") or "secret" in actions, "not_found", "对象不可访问", 404)
                identity = await self.db.get(Entity, entity_id)
                body = {
                    k: copy.deepcopy(previous[k])
                    for k in ("kind", "name", "data", "text", "secret", "deleted", "definition_id")
                }
                if action in {"update", "retire", "restore"}:
                    require(op.get("expected"), "precondition_required", "修改必须携带读取时的版本", 428)
                    require(
                        op["expected"] == previous["version"],
                        "precondition",
                        "对象版本已变化，请三方比较",
                        412,
                        current_version=previous["version"],
                    )
                definition = await self.db.get(Definition, body["definition_id"])
                if op.get("definition_id"):
                    require("secret" in actions, "definition_upgrade", "定义升级需要完整属性权限", 403)
                    adopted = await self.definition(scope, body["kind"])
                    require(
                        adopted.id == op["definition_id"],
                        "definition_upgrade",
                        "只能显式升级到当前采用的同类型定义",
                    )
                    body["definition_id"], definition = adopted.id, adopted
            if action in {"create", "update", "retire", "restore"}:
                if action == "restore":
                    require("secret" in actions, "restore_permission", "历史恢复需要完整范围权限", 403)
                    old = await self.revision(scope.id, entity_id, op.get("revision_id"))
                    body = {
                        k: copy.deepcopy(old[k])
                        for k in ("kind", "name", "data", "text", "secret", "deleted", "definition_id")
                    }
                    definition = await self.db.get(Definition, body["definition_id"])
                if action == "update":
                    if op.get("reactivate"):
                        body["deleted"] = False
                    for field in ("name", "text", "secret"):
                        if field in op:
                            body[field] = op[field]
                    body["data"].update(op.get("data", {}))
                    for key in op.get("unset", []):
                        require(
                            not definition.spec["properties"].get(key, {}).get("secret")
                            or "secret" in actions,
                            "secret_field",
                            "无权删除秘密属性",
                            403,
                            field=key,
                        )
                        body["data"].pop(key, None)
                if action == "retire":
                    body["deleted"] = True
                require(
                    not body["secret"] or "secret" in actions, "secret_field", "无权创建或修改秘密内容", 403
                )
                validate_values(definition.spec, body["data"])
                await self._validate_refs(
                    scope,
                    definition.spec,
                    body["data"],
                    actions,
                    previous.get("data") if action != "create" else None,
                )
                parent_id = body["data"].get("parent_id")
                visited = {entity_id}
                while parent_id:
                    require(
                        parent_id not in visited and len(visited) < 100, "hierarchy_cycle", "层级关系形成循环"
                    )
                    visited.add(parent_id)
                    parent = await self.reference(scope, parent_id)
                    parent_id = parent.get("data", {}).get("parent_id")
                await self._save_body(scope, identity, body, change.id)
                if action == "create" or body["name"] != previous["name"]:
                    self.db.add(
                        Fact(
                            scope_id=scope.id,
                            subject_id=entity_id,
                            predicate="name",
                            category="name",
                            value={"label": body["name"], "language": "zh", "context": "default"},
                            recorded_from=scope.version,
                            source={"kind": "author", "change_id": change.id},
                            change_id=change.id,
                        )
                    )
                impacts.append(
                    {
                        "kind": action,
                        "entity_id": entity_id,
                        "name": body["name"],
                        "review_stale": action == "update" and "text" in op,
                    }
                )
            elif action in {"fact", "name"}:
                value = FactInput.model_validate(op.get("fact"))
                if action == "name":
                    require(value.category == "name", "name", "名称记录必须使用name类别")
                await self._assert_fact(scope, entity_id, value, change.id, actions)
                impacts.append({"kind": value.category, "entity_id": entity_id, "predicate": value.predicate})
            elif action == "retract":
                old = await self.db.get(Fact, op.get("fact_id"))
                require(not old or not old.secret or "secret" in actions, "not_found", "事实不可访问", 404)
                active_ids = {f.id for f in await self.raw_facts(scope)}
                require(
                    old is not None and old.id in active_ids and old.subject_id == entity_id,
                    "fact",
                    "事实不存在或已撤回",
                )
                if old.scope_id == scope.id:
                    old.recorded_to = scope.version
                else:
                    self.db.add(
                        Fact(
                            scope_id=scope.id,
                            subject_id=entity_id,
                            predicate=old.predicate,
                            category="retraction",
                            value={},
                            recorded_from=scope.version,
                            supersedes=old.id,
                            source={"kind": "author", "change_id": change.id},
                            change_id=change.id,
                        )
                    )
                impacts.append({"kind": "retraction", "fact_id": old.id})
            else:
                raise DomainError("operation", "未知变更操作")
            await self.db.flush()
        return impacts

    async def _assert_fact(self, scope, subject_id, value, change_id, actions):
        subject = await self.reference(scope, subject_id, secret="secret" in actions)
        value.secret |= bool(subject.get("secret"))
        require(not value.secret or "secret" in actions, "secret_field", "无权编辑秘密关系", 403)
        require(
            value.source.get("kind") in {"author", "text", "reference", "ai", "inference"},
            "source",
            "事实必须说明来源类型",
        )
        if value.category == "relation":
            require(value.object_id, "relation", "已确认关系必须有已解析目标")
        if value.object_id:
            target = await self.reference(scope, value.object_id, secret="secret" in actions)
            value.secret |= bool(target.get("secret"))
        if value.chapter_id:
            chapter = await self.reference(scope, value.chapter_id, secret="secret" in actions)
            value.secret |= bool(chapter.get("secret"))
            require(
                chapter["kind"] in {"chapter", "章节", "scene", "场景"}, "chapter", "叙述锚点必须是章节或场景"
            )
        if value.world_from is not None or value.world_to is not None:
            require(
                value.calendar
                and (value.world_to is None or value.world_from is None or value.world_to > value.world_from),
                "world_interval",
                "时间区间必须有历法，终点大于起点（半开区间）",
            )
        if value.category == "belief":
            require(
                value.value.get("stance") in {"knows", "suspects", "misbelieves", "unaware", "denies"},
                "belief",
                "角色认知必须有信念状态",
            )
            require(value.value.get("proposition"), "belief", "认知必须针对明确命题")
        if value.source.get("entity_id"):
            source = await self.reference(scope, value.source["entity_id"], secret="secret" in actions)
            value.secret |= bool(source.get("secret"))
            if value.source.get("revision") == "$change":
                revision = await self.db.get(Revision, source["revision"])
                require(revision.change_id == change_id, "source_revision", "当前变更未产生该来源修订")
                value.source = {**value.source, "revision": source["revision"]}
            else:
                require(
                    value.source.get("revision") == source["revision"], "source_revision", "来源修订已过期"
                )
            quote = value.source.get("quote")
            require(quote and quote in source["text"], "source_quote", "来源证据不可定位")
        active = await self.raw_facts(scope)
        if value.supersedes:
            old = next((f for f in active if f.id == value.supersedes), None)
            require(not old or not old.secret or "secret" in actions, "not_found", "事实不可访问", 404)
            require(
                old is not None and old.subject_id == subject_id and old.predicate == value.predicate,
                "supersedes",
                "修正必须绑定同一对象及命题的有效事实",
            )
            if old.scope_id == scope.id:
                old.recorded_to = scope.version
            active = [f for f in active if f.id != old.id]
        if value.category == "relation":
            definition = await self.definition(scope, "rel:" + value.predicate)
            spec = definition.spec
            subject = await self.reference(scope, subject_id)
            require(
                not spec.get("source_kinds") or subject["kind"] in spec["source_kinds"],
                "relation_type",
                "关系起点类型不符",
            )
            require(
                not spec.get("target_kinds") or target["kind"] in spec["target_kinds"],
                "relation_type",
                "关系终点类型不符",
            )
            others = [f for f in active if f.category == "relation" and f.predicate == value.predicate]
            if spec.get("exclusive_target"):
                for f in others:
                    if f.object_id != value.object_id:
                        continue
                    same_calendar = f.calendar == value.calendar
                    overlap = (
                        f.world_to is None or value.world_from is None or f.world_to > value.world_from
                    ) and (value.world_to is None or f.world_from is None or value.world_to > f.world_from)
                    require(
                        same_calendar and not overlap,
                        "exclusive_relation",
                        "排他关系时间重叠或历法无法比较",
                        409,
                        fact_id=f.id,
                    )
            if spec.get("acyclic"):
                edges = {}
                for f in others:
                    edges.setdefault(f.subject_id, []).append(f.object_id)
                todo, seen = [value.object_id], set()
                while todo:
                    node = todo.pop()
                    require(node != subject_id, "relation_cycle", "关系形成循环")
                    if node not in seen:
                        seen.add(node)
                        todo.extend(edges.get(node, []))
        self.db.add(
            Fact(
                scope_id=scope.id,
                subject_id=subject_id,
                change_id=change_id,
                recorded_from=scope.version,
                **value.model_dump(exclude={"predicate"}),
                predicate=value.predicate,
            )
        )
