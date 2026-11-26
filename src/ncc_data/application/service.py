"""Management use cases shared by HTTP, CLI and workers."""

import copy
from datetime import datetime, timedelta

from sqlalchemy import and_, func, or_, select, update

from ncc_data.application.calibration import CalibrationMixin
from ncc_data.application.knowledge.changes import ChangeService
from ncc_data.application.knowledge.exchange import ExchangeMixin
from ncc_data.application.knowledge.maintenance import MaintenanceMixin
from ncc_data.application.knowledge.workspace import WorkspaceMixin
from ncc_data.application.security import authorize, password_hash
from ncc_data.domain.contracts import DelegationInput, Query, StateQuery, UserUpdateInput
from ncc_data.domain.definitions import SYSTEM_SCOPE
from ncc_data.persistence.models import (
    Assessment,
    Audit,
    ChangeSet,
    Definition,
    Delegation,
    Feedback,
    ImportRun,
    Job,
    Membership,
    Revision,
    Scope,
    Session,
    User,
    utcnow,
)
from ncc_shared.errors import DomainError, require
from ncc_shared.quality.policy import POLICY_HASH
from ncc_shared.serialization import jsonable


class Service(CalibrationMixin, MaintenanceMixin, WorkspaceMixin, ExchangeMixin, ChangeService):
    async def clear_author_draft(self, scope_id, key, version):
        await authorize(self.db, self.actor, scope_id, "edit", lock=True)
        row = await self.db.scalar(
            select(Job).where(
                Job.scope_id == scope_id,
                Job.actor_id == self.actor.id,
                Job.kind == "author-draft",
                Job.payload["key"].astext == key,
            )
        )
        if not row:
            return {"cleared": True}
        await self.job(scope_id, row.id, "edit")
        require(
            row.progress.get("version", 0) == version,
            "draft_conflict",
            "另一个窗口产生了新草稿，已保留供比较",
            409,
        )
        row.result = {}
        row.progress = {"version": version + 1}
        row.updated_at = utcnow()
        return {"cleared": True, "version": version + 1}

    async def author_draft(self, scope_id, key, value=None):
        _, actions = await authorize(self.db, self.actor, scope_id, "edit", lock=value is not None)
        require(0 < len(key) <= 128, "draft_key", "草稿标识无效")
        row = await self.db.scalar(
            select(Job).where(
                Job.scope_id == scope_id,
                Job.actor_id == self.actor.id,
                Job.kind == "author-draft",
                Job.payload["key"].astext == key,
            )
        )
        if row:
            require(
                not row.payload.get("requires_secret") or "secret" in actions,
                "not_found",
                "草稿不可访问",
                404,
            )
        if value is None:
            return {"version": row.progress.get("version", 0), **row.result} if row else {"version": 0}
        if value.entity_id:
            await self.entity(scope_id, value.entity_id)
        require(
            value.version == (row.progress.get("version", 0) if row else 0),
            "draft_conflict",
            "另一编辑窗口已更新草稿；当前输入保留，请比较",
            409,
        )
        if not row:
            row = Job(
                scope_id=scope_id,
                actor_id=self.actor.id,
                kind="author-draft",
                state="draft",
                payload={"key": key, "requires_secret": "secret" in actions},
            )
            self.db.add(row)
        row.result = value.model_dump(exclude={"version"})
        row.progress = {"version": value.version + 1}
        row.updated_at = utcnow()
        # A human edit invalidates in-flight work even before a formal content adoption.
        running = (
            await self.db.scalars(
                select(Job).where(
                    Job.scope_id == scope_id,
                    Job.actor_id == self.actor.id,
                    Job.kind == "creation",
                    Job.state.in_(["queued", "running", "qualified"]),
                )
            )
        ).all()
        for task in running:
            if task.payload.get("entity_id") == value.entity_id:
                task.state = "paused"
                task.cancel_requested = True
                task.lease_token = None
                task.lease_until = None
                task.updated_at = utcnow()
        await self.db.flush()
        return {"version": row.progress["version"], **row.result}

    async def members(self, scope_id):
        await authorize(self.db, self.actor, scope_id, "admin")
        rows = (
            await self.db.execute(
                select(Membership, User.username)
                .join(User, Membership.user_id == User.id)
                .where(Membership.scope_id == scope_id)
            )
        ).all()
        return [
            {"id": m.id, "user_id": m.user_id, "username": name, "actions": m.actions} for m, name in rows
        ]

    async def set_member(self, scope_id, value):
        scope, _ = await authorize(self.db, self.actor, scope_id, "admin", lock=True)
        require(scope.owner_id == self.actor.id, "owner_only", "只有范围所有者可调整成员权限", 403)
        require(
            not hasattr(self.actor, "_access_scope"), "scoped_credential", "范围凭据不能调整成员权限", 403
        )
        target = None
        if value.user_id and value.user_id.strip():
            target = await self.db.get(User, value.user_id.strip())
        elif value.username and value.username.strip():
            target = await self.db.scalar(select(User).where(User.username == value.username.strip()))
        require(target is not None, "member", "用户不存在")
        require(
            target.id != scope.owner_id,
            "owner_membership",
            "空间所有者默认拥有全部权限，无需单独调整成员记录",
            409,
        )
        sorted_actions = sorted(set(value.actions))
        row = await self.db.scalar(
            select(Membership).where(Membership.scope_id == scope_id, Membership.user_id == target.id)
        )
        if row:
            row.actions = sorted_actions
        else:
            self.db.add(Membership(scope_id=scope_id, user_id=target.id, actions=sorted_actions))
        self.db.add(
            Audit(
                scope_id=scope_id,
                actor_id=self.actor.id,
                action="member.set",
                version=scope.version,
                detail={"user_id": target.id, "username": target.username, "actions": sorted_actions},
            )
        )
        await self.db.flush()
        return await self.members(scope_id)

    async def remove_member(self, scope_id: str, user_id: str):
        scope, _ = await authorize(self.db, self.actor, scope_id, "admin", lock=True)
        require(scope.owner_id == self.actor.id, "owner_only", "只有范围所有者可移除成员", 403)
        require(
            not hasattr(self.actor, "_access_scope"), "scoped_credential", "范围凭据不能移除成员", 403
        )
        require(
            user_id != scope.owner_id,
            "owner_membership",
            "空间所有者默认拥有全部权限，不能移除自身",
            409,
        )
        row = await self.db.scalar(
            select(Membership).where(Membership.scope_id == scope_id, Membership.user_id == user_id)
        )
        require(row is not None, "not_found", "成员不存在", 404)
        target = await self.db.get(User, user_id)
        target_name = target.username if target is not None else ""
        await self.db.delete(row)
        await self.db.execute(
            update(Session)
            .where(Session.scope_id == scope_id, Session.user_id == user_id, Session.kind == "cli")
            .values(revoked=True)
        )
        self.db.add(
            Audit(
                scope_id=scope_id,
                actor_id=self.actor.id,
                action="member.remove",
                version=scope.version,
                detail={"user_id": user_id, "username": target_name},
            )
        )
        await self.db.flush()
        return await self.members(scope_id)

    async def list_users(self):
        require(self.actor.admin, "administrator", "查看系统账号需要系统管理员权限", 403)
        require(
            not hasattr(self.actor, "_access_scope"), "scoped_credential", "范围凭据不能执行全局账号管理", 403
        )
        rows = (await self.db.scalars(select(User).order_by(User.created_at.asc(), User.username.asc()))).all()
        return jsonable(
            [
                {
                    "id": u.id,
                    "username": u.username,
                    "active": bool(u.active),
                    "admin": bool(u.admin),
                    "must_change_credentials": bool(u.must_change_credentials),
                    "created_at": u.created_at,
                }
                for u in rows
            ]
        )

    async def user_directory(self, q: str = ""):
        require(
            not hasattr(self.actor, "_access_scope"), "scoped_credential", "范围凭据不能读取账号目录", 403
        )
        stmt = select(User).where(User.active.is_(True))
        if q and q.strip():
            escaped = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            stmt = stmt.where(User.username.ilike(f"%{escaped}%", escape="\\"))
        rows = (await self.db.scalars(stmt.order_by(User.username.asc()).limit(50))).all()
        return [{"id": u.id, "username": u.username} for u in rows]

    async def update_user(self, user_id: str, value: UserUpdateInput):
        require(self.actor.admin, "administrator", "账号管理需要系统管理员权限", 403)
        require(
            not hasattr(self.actor, "_access_scope"), "scoped_credential", "范围凭据不能执行全局账号管理", 403
        )
        target = await self.db.scalar(
            select(User).where(User.id == user_id).with_for_update().execution_options(populate_existing=True)
        )
        require(target is not None, "not_found", "账号不存在", 404)
        require(
            not (value.active is False and target.id == self.actor.id),
            "self_disable",
            "不能停用当前登录账号",
            409,
        )
        next_active = target.active if value.active is None else bool(value.active)
        next_admin = target.admin if value.admin is None else bool(value.admin)
        if (target.active and target.admin) and not (next_active and next_admin):
            other_admins = int(
                (
                    await self.db.scalar(
                        select(func.count())
                        .select_from(User)
                        .where(User.active.is_(True), User.admin.is_(True), User.id != target.id)
                    )
                )
                or 0
            )
            require(other_admins >= 1, "last_admin", "至少需要保留一名活跃系统管理员", 409)
        fields: list[str] = []
        revoke_sessions = False
        if value.active is not None:
            target.active = bool(value.active)
            fields.append("active")
            if not target.active:
                revoke_sessions = True
        if value.admin is not None:
            target.admin = bool(value.admin)
            fields.append("admin")
        if value.reset_password is not None:
            target.password_hash = password_hash(value.reset_password)
            target.must_change_credentials = True
            fields.append("reset_password")
            revoke_sessions = True
        if revoke_sessions:
            await self.db.execute(update(Session).where(Session.user_id == target.id).values(revoked=True))
        self.db.add(
            Audit(
                scope_id=SYSTEM_SCOPE,
                actor_id=self.actor.id,
                action="user.update",
                version=0,
                detail={
                    "target_user_id": target.id,
                    "target_username": target.username,
                    "fields": fields,
                },
            )
        )
        await self.db.flush()
        return jsonable(
            {
                "id": target.id,
                "username": target.username,
                "active": bool(target.active),
                "admin": bool(target.admin),
                "must_change_credentials": bool(target.must_change_credentials),
                "created_at": target.created_at,
            }
        )

    async def create_user(self, username, password):
        require(self.actor.admin, "administrator", "创建账号需要系统管理员权限", 403)
        require(
            not hasattr(self.actor, "_access_scope"), "scoped_credential", "范围凭据不能执行全局账号管理", 403
        )
        require(
            await self.db.scalar(select(User.id).where(User.username == username)) is None,
            "username",
            "用户名已存在",
            409,
        )
        user = User(username=username, password_hash=password_hash(password))
        self.db.add(user)
        await self.db.flush()
        self.db.add(
            Audit(
                scope_id=SYSTEM_SCOPE,
                actor_id=self.actor.id,
                action="user.create",
                version=0,
                detail={"user_id": user.id, "username": user.username},
            )
        )
        await self.db.flush()
        return {"id": user.id, "username": user.username}

    async def changes(self, scope_id):
        _, actions = await authorize(self.db, self.actor, scope_id)
        query = select(ChangeSet).where(ChangeSet.scope_id == scope_id)
        if "secret" not in actions:
            query = query.where(ChangeSet.actor_id == self.actor.id)
        rows = (await self.db.scalars(query.order_by(ChangeSet.created_at.desc()).limit(100))).all()
        return [
            self.change_json(r)
            for r in rows
            if not r.validation.get("requires_secret", True) or "secret" in actions
        ]

    async def save_view(self, scope_id, name, value):
        scope, _ = await authorize(self.db, self.actor, scope_id, "read", lock=True)
        require(isinstance(name, str) and 0 < len(name) <= 100, "view", "视图名称无效")
        # Views are actor-specific, never shared accidentally through a global browser cache.
        config = dict(scope.config)
        views = dict(config.get("views", {}))
        personal = dict(views.get(self.actor.id, {}))
        require(name in personal or len(personal) < 50, "view_limit", "个人视图上限50")
        personal[name] = Query.model_validate(value).model_dump(mode="json")
        views[self.actor.id] = personal
        config["views"] = views
        scope.config = config
        return personal

    async def graph(self, scope_id, center, hops=2):
        require(1 <= hops <= 2, "graph_limit", "图谱最多展开两跳")
        scope, actions = await authorize(self.db, self.actor, scope_id)
        center_raw = await self.raw_entity(scope, center)
        await self.redact(scope, actions, center_raw, Query())
        relations = (await self.facts(scope_id, StateQuery(category="relation", limit=200)))["items"]
        nodes, edges, frontier = {center}, [], {center}
        for _ in range(hops):
            chosen = [f for f in relations if f["subject_id"] in frontier or f["object_id"] in frontier]
            frontier = {v for f in chosen for v in (f["subject_id"], f["object_id"]) if v} - nodes
            nodes.update(frontier)
            edges += [f for f in chosen if f["id"] not in {e["id"] for e in edges}]
        node_list = list(nodes)[:500]
        raw_by_id: dict[str, dict] = {}
        defs_by_id: dict[str, Definition] = {}
        if node_list:
            rev_stmt = (await self.revision_query(scope)).where(Revision.entity_id.in_(node_list))
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
        default_query = Query()
        items = []
        for eid in node_list:
            raw_obj = raw_by_id.get(eid)
            if raw_obj is None:
                continue
            try:
                item = await self.redact_with_definitions(
                    scope, actions, raw_obj, default_query, defs_by_id
                )
                items.append({"id": eid, "name": item["name"], "kind": item["kind"]})
            except DomainError:
                # Foreign endpoints are deliberately omitted unless requested through their authorized scope.
                continue
        allowed = {n["id"] for n in items}
        return {
            "nodes": items,
            "edges": [e for e in edges[:1000] if e["subject_id"] in allowed and e["object_id"] in allowed],
            "truncated": len(relations) >= 200 or len(nodes) > 500 or len(edges) > 1000,
        }

    async def quality(self, scope_id):
        await authorize(self.db, self.actor, scope_id, "read")
        found, offset = [], 0
        names = {}
        while offset < 2000:
            page = await self.entities(scope_id, Query(offset=offset, limit=200))
            for item in page["items"]:
                if item["name"] in names:
                    found.append(
                        {
                            "kind": "duplicate_candidate",
                            "entity_id": item["id"],
                            "other_id": names[item["name"]],
                            "detail": f"同名候选：{item['name']}，不会自动合并",
                        }
                    )
                names[item["name"]] = item["id"]
                if item["kind"] in {"foreshadow", "伏笔"}:
                    data = item["data"]
                    if data.get("status") in {"resolved", "已回收", "完全兑现"} and not data.get(
                        "payoff_chapters"
                    ):
                        found.append(
                            {
                                "kind": "payoff_evidence",
                                "entity_id": item["id"],
                                "detail": "已兑现状态缺少实际回收章节",
                            }
                        )
                    if data.get("expected_chapter") and not data.get("observed_chapters"):
                        found.append(
                            {
                                "kind": "insufficient_coverage",
                                "entity_id": item["id"],
                                "detail": "观察覆盖不足，不能判断伏笔断线",
                            }
                        )
                if item["kind"] in {"语录", "佛家语录", "道家语录", "法家语录", "墨家语录"} and not item[
                    "data"
                ].get("source_id"):
                    found.append(
                        {"kind": "unverified_attribution", "entity_id": item["id"], "detail": "出处尚未核实"}
                    )
            if page["next_offset"] is None:
                break
            offset = page["next_offset"]
        return {"items": found, "coverage": "bounded", "scanned": min(offset + 200, 2000)}

    async def job(self, scope_id, job_id, action="read", lock=False):
        _, actions = await authorize(self.db, self.actor, scope_id, action, lock=lock)
        row = await self.db.get(Job, job_id)
        require(row is not None and row.scope_id == scope_id, "not_found", "任务不存在", 404)
        require(
            row.actor_id == self.actor.id or ("admin" in actions and "secret" in actions),
            "not_found",
            "任务不可访问",
            404,
        )
        require(
            not row.payload.get("requires_secret") or "secret" in actions, "not_found", "任务不可访问", 404
        )
        return row

    def job_json(self, row, details=True):
        result = copy.deepcopy(row.result) if details and isinstance(row.result, dict) else {}
        packet = result.get("packet")
        if isinstance(packet, dict) and isinstance(packet.get("sources"), list):
            sanitized = []
            for item in packet["sources"]:
                if isinstance(item, dict) and item.get("scope_id") and item.get("scope_id") != row.scope_id:
                    sanitized.append(
                        {
                            "id": item.get("id"),
                            "scope_id": item.get("scope_id"),
                            "revision": item.get("revision"),
                            "version": item.get("version"),
                            "content_hash": item.get("content_hash"),
                            "readonly": True,
                            "redacted": True,
                        }
                    )
                else:
                    sanitized.append(item)
            packet["sources"] = sanitized
        return jsonable(
            {
                "id": row.id,
                "kind": row.kind,
                "state": row.state,
                "progress": row.progress,
                "payload": row.payload if details else {},
                "result": result if details else {},
                "attempts": row.attempts,
                "cancel_requested": row.cancel_requested,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
        )

    async def serialize_job(self, row, details=True):
        data = self.job_json(row, details=details)
        if not details:
            return data
        raw_sources = ((row.result or {}).get("packet") or {}).get("sources")
        if not isinstance(raw_sources, list):
            return data
        projected = []
        for item in raw_sources:
            if not (isinstance(item, dict) and item.get("scope_id") and item.get("scope_id") != row.scope_id):
                projected.append(jsonable(item))
                continue
            ref_entry = {
                "id": item.get("id"),
                "scope_id": item.get("scope_id"),
                "revision": item.get("revision"),
                "version": item.get("version"),
                "content_hash": item.get("content_hash"),
                "readonly": True,
            }
            if hasattr(self.actor, "_access_scope") and self.actor._access_scope != item.get("scope_id"):
                projected.append({**ref_entry, "redacted": True})
                continue
            viewer = copy.copy(self.actor)
            for attr in ("_access_scope", "_access_actions"):
                if hasattr(viewer, attr):
                    delattr(viewer, attr)
            reader_svc = Service(self.db, viewer)
            try:
                if item.get("revision"):
                    obj = await reader_svc.revision(item["scope_id"], item["id"], item["revision"])
                    if obj.get("deleted"):
                        raise DomainError("not_found", "对象已停用", 404)
                    # Enforce live entity/field secret visibility for non-deleted check as well
                    live = await reader_svc.entity(item["scope_id"], item["id"])
                    if live.get("deleted"):
                        raise DomainError("not_found", "对象已停用", 404)
                else:
                    obj = await reader_svc.entity(item["scope_id"], item["id"])
                projected.append(
                    jsonable(
                        {
                            **ref_entry,
                            "name": obj.get("name") or "",
                            "kind": obj.get("kind") or "",
                            "data": obj.get("data") or {},
                            "text": (obj.get("text") or "")[:16000],
                            "redacted": False,
                        }
                    )
                )
            except DomainError:
                projected.append({**ref_entry, "redacted": True})
        data["result"]["packet"]["sources"] = projected
        return data

    def job_summary_json(self, row, details=True):
        progress = dict(row.progress) if isinstance(row.progress, dict) else {}
        raw_payload = row.payload if isinstance(row.payload, dict) else {}
        raw_result = row.result if isinstance(row.result, dict) else {}
        stage = progress.get("stage")
        error = raw_result.get("error") if details else None
        payload = {}
        result = {}
        if details:
            omit_payload = {"beat_outline", "guidance"}
            payload = {
                k: (v[:500] if k == "objective" and isinstance(v, str) else v)
                for k, v in raw_payload.items()
                if k not in omit_payload
            }
            candidates = raw_result.get("candidates")
            cand = {}
            if isinstance(candidates, list) and candidates:
                idx = raw_result.get("selected", len(candidates) - 1)
                if isinstance(idx, int) and 0 <= idx < len(candidates) and isinstance(candidates[idx], dict):
                    cand = candidates[idx]
                elif isinstance(candidates[-1], dict):
                    cand = candidates[-1]
            ev = cand.get("evaluation") or raw_result.get("plan_evaluation") or {}
            ev = ev if isinstance(ev, dict) else {}
            report = ev.get("report") if isinstance(ev.get("report"), dict) else {}
            attachment_id = raw_result.get("attachment_id") or (
                raw_result.get("id") if row.kind == "export" else None
            )
            target_id = (
                raw_result.get("target_id")
                or raw_payload.get("entity_id")
                or raw_result.get("new_entity_id")
            )
            target_name = raw_result.get("target_name") or raw_payload.get("name")
            result = {
                "summary": raw_result.get("summary") or report.get("summary"),
                "score": raw_result.get("score") if raw_result.get("score") is not None else ev.get("score"),
                "verdict": raw_result.get("verdict") or ev.get("verdict"),
                "attachment_id": attachment_id,
                "target_id": target_id,
                "target_name": target_name,
                "stage": stage,
                "rounds": progress.get("revisions", 0),
            }
            if error is not None:
                result["error"] = error
            if row.kind == "export":
                for key in ("id", "name", "size", "digest", "format", "chapter_count", "words"):
                    if key in raw_result:
                        result[key] = raw_result[key]
            for key in ("selected", "new_entity_id", "auto_hold", "receipt", "last_receipt"):
                if key in raw_result:
                    result[key] = raw_result[key]
        return jsonable(
            {
                "id": row.id,
                "kind": row.kind,
                "state": row.state,
                "stage": stage,
                "progress": progress,
                "payload": payload,
                "result": result,
                "error": error,
                "attempts": row.attempts,
                "cancel_requested": row.cancel_requested,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
        )

    async def jobs(
        self,
        scope_id,
        *,
        kind: str | None = None,
        state: str | None = None,
        entity_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
        summary: bool = False,
    ):
        require(1 <= limit <= 100, "limit", "每页任务条数须在 1 至 100 之间")
        require(0 <= offset <= 100_000, "offset", "分页偏移超出范围")
        _, actions = await authorize(self.db, self.actor, scope_id)
        statement = select(Job).where(
            Job.scope_id == scope_id,
            Job.kind.not_in(["author-draft", "index"]),
        )
        if not {"admin", "secret"} <= set(actions):
            statement = statement.where(Job.actor_id == self.actor.id)
        if "secret" not in actions:
            statement = statement.where(
                or_(
                    Job.payload["requires_secret"].is_(None),
                    Job.payload["requires_secret"].as_boolean().is_(False),
                )
            )
        if kind:
            statement = statement.where(Job.kind == kind)
        if state:
            statement = statement.where(Job.state == state)
        if entity_id:
            statement = statement.where(Job.payload["entity_id"].astext == entity_id)
        rows = (
            await self.db.scalars(statement.order_by(Job.created_at.desc()).offset(offset).limit(limit))
        ).all()
        base_details = bool({"edit", "assess"} & set(actions))
        out = []
        for r in rows:
            if r.payload.get("requires_secret") and "secret" not in actions:
                continue
            row_details = base_details or (r.kind == "export" and "export" in actions)
            if summary:
                out.append(self.job_summary_json(r, details=row_details))
            else:
                out.append(await self.serialize_job(r, details=row_details))
        return out

    async def _authorize_job_control(self, scope_id, job_id):
        _, actions = await authorize(self.db, self.actor, scope_id, "read", lock=True)
        row = await self.db.scalar(
            select(Job).where(Job.id == job_id).with_for_update().execution_options(populate_existing=True)
        )
        require(
            row is not None and row.scope_id == scope_id and row.kind not in {"author-draft", "index"},
            "not_found",
            "任务不存在",
            404,
        )
        require(
            row.actor_id == self.actor.id or ("admin" in actions and "secret" in actions),
            "not_found",
            "任务不可访问",
            404,
        )
        require(
            not row.payload.get("requires_secret") or "secret" in actions,
            "not_found",
            "任务不可访问",
            404,
        )
        if row.kind == "export":
            await authorize(self.db, self.actor, scope_id, "export")
        elif row.kind == "creation" and row.payload.get("mode") == "assess":
            if "edit" not in actions:
                await authorize(self.db, self.actor, scope_id, "assess")
        else:
            await authorize(self.db, self.actor, scope_id, "edit")
        details = bool({"edit", "assess"} & set(actions)) or (row.kind == "export" and "export" in actions)
        return row, details

    async def cancel_job(self, scope_id, job_id):
        row, details = await self._authorize_job_control(scope_id, job_id)
        require(
            row.state not in {"applied", "succeeded", "cancelled"},
            "job_terminal",
            "任务已结束，不能取消",
            409,
        )
        row.cancel_requested = True
        row.state = "cancelled"
        row.lease_token = None
        row.lease_until = None
        row.updated_at = utcnow()
        if row.kind == "import" and row.payload.get("import_id"):
            imported = await self.db.get(ImportRun, row.payload["import_id"])
            if imported is not None and imported.state != "succeeded":
                imported.state = "cancelled"
        return await self.serialize_job(row, details=details)

    async def retry_job(self, scope_id, job_id):
        row, details = await self._authorize_job_control(scope_id, job_id)
        require(row.kind in {"export", "import", "creation"}, "job_kind", "此类型任务不支持重试", 409)
        require(
            row.state in {"failed", "waiting", "cancelled", "paused"},
            "job_state",
            "当前任务状态不支持重试",
            409,
        )
        res = dict(row.result or {})
        res.pop("error", None)
        row.result = res
        row.state = "queued"
        row.cancel_requested = False
        row.attempts = 0
        row.lease_token = None
        row.lease_until = None
        row.updated_at = utcnow()
        if row.kind == "import" and row.payload.get("import_id"):
            imported = await self.db.get(ImportRun, row.payload["import_id"])
            if imported is not None:
                imported.state = "queued"
        return await self.serialize_job(row, details=details)

    async def intervene(self, scope_id, job_id, value):
        row = await self.job(scope_id, job_id, "read", lock=True)
        await authorize(
            self.db, self.actor, scope_id, "assess" if row.payload.get("mode") == "assess" else "edit"
        )
        require(row.kind == "creation", "job_kind", "此操作仅适用于创作任务")
        require(row.state not in {"applied", "cancelled"}, "job_state", "任务已结束", 409)
        if value.action in {"pause", "cancel"}:
            row.cancel_requested = True
            row.state = "paused" if value.action == "pause" else "cancelled"
        elif value.action == "resume":
            require(row.state in {"paused", "failed", "waiting"}, "job_state", "当前任务不能恢复", 409)
            row.cancel_requested, row.state = False, "queued"
            row.attempts = 0
        elif value.action == "change_objective":
            require(value.objective, "objective", "需要新的创作目标")
            row.cancel_requested = False
            row.payload = {
                **row.payload,
                "objective": value.objective,
                "generation": row.payload.get("generation", 0) + 1,
            }
            row.state = "queued"
            row.progress, row.result, row.attempts = {}, {}, 0
        else:
            candidates = row.result.get("candidates", [])
            require(
                value.candidate is not None and value.candidate < len(candidates), "candidate", "候选不存在"
            )
            row.result = {**row.result, "selected": value.candidate}
        # Fencing invalidates an in-flight worker, including its late model response.
        row.lease_token, row.lease_until, row.updated_at = None, None, utcnow()
        return await self.serialize_job(row)

    async def assessments(self, scope_id):
        scope, actions = await authorize(self.db, self.actor, scope_id)
        statement = select(Assessment).where(Assessment.scope_id == scope_id)
        if "secret" not in actions:
            statement = statement.where(Assessment.actor_id == self.actor.id)
        rows = (await self.db.scalars(statement.order_by(Assessment.created_at.desc()).limit(100))).all()
        visible_rows = [
            r for r in rows if not r.report.get("requires_secret", True) or "secret" in actions
        ]
        entity_meta: dict[str, tuple[str | None, str | None]] = {}
        entity_ids = {r.entity_id for r in visible_rows if r.entity_id}
        if entity_ids:
            rev_stmt = (await self.revision_query(scope)).where(Revision.entity_id.in_(entity_ids))
            if "secret" not in actions:
                rev_stmt = rev_stmt.where(Revision.body["secret"].as_boolean().is_(False))
            rev_rows = (await self.db.scalars(rev_stmt)).all()
            for rev in rev_rows:
                body = rev.body if isinstance(rev.body, dict) else {}
                entity_meta[rev.entity_id] = (body.get("name"), body.get("kind"))
        return [
            {
                "id": r.id,
                "entity_id": r.entity_id,
                "entity_name": entity_meta.get(r.entity_id, (None, None))[0],
                "entity_kind": entity_meta.get(r.entity_id, (None, None))[1],
                "score": str(r.score) if r.score is not None else None,
                "verdict": r.verdict,
                "scheme": r.scheme,
                "report": r.report,
                "fresh": r.dependency_version == scope.version and r.policy_hash == POLICY_HASH,
                "evaluator": r.evaluator,
                "content_hash": r.content_hash,
                "created_at": r.created_at.isoformat(),
            }
            for r in visible_rows
        ]

    async def feedback(self, scope_id, assessment_id, choice, note):
        await authorize(self.db, self.actor, scope_id, "read")
        row = await self.db.get(Assessment, assessment_id)
        require(row and row.scope_id == scope_id, "not_found", "评分不存在", 404)
        require(choice in {"satisfied", "usable", "dislike", "prefer_other"}, "feedback", "未知反馈选项")
        self.db.add(
            Feedback(
                scope_id=scope_id,
                actor_id=self.actor.id,
                assessment_id=row.id,
                choice=choice,
                note=note[:4000],
            )
        )
        return {"saved": True}

    async def delegation(self, scope_id, value: DelegationInput):
        scope, _ = await authorize(self.db, self.actor, scope_id, "adopt", lock=True)
        if value.mode == "author_trial":
            require(scope.owner_id == self.actor.id, "owner_only", "未经校准的试运行须由作品所有者启用", 403)
            require(value.note.strip(), "trial_note", "试运行须记录作者授权依据；不会标记为已校准")
        for eid in value.target_ids:
            await self.entity(scope_id, eid)
        row = Delegation(
            scope_id=scope_id,
            actor_id=self.actor.id,
            target_ids=value.target_ids,
            schemes=value.schemes,
            expires_at=utcnow() + timedelta(hours=value.hours),
            remaining=value.count,
            authorization={"mode": value.mode, "policy_hash": POLICY_HASH, "note": value.note.strip()},
        )
        self.db.add(row)
        await self.db.flush()
        self.db.add(
            Audit(
                scope_id=scope_id,
                actor_id=self.actor.id,
                action="delegation.create",
                version=scope.version,
                detail={
                    "delegation_id": row.id,
                    "target_ids": row.target_ids,
                    "schemes": row.schemes,
                    "hours": value.hours,
                    "count": row.remaining,
                    "authorization": row.authorization,
                },
            )
        )
        return {
            "id": row.id,
            "target_ids": row.target_ids,
            "schemes": row.schemes,
            "expires_at": row.expires_at.isoformat(),
            "remaining": row.remaining,
            "authorization": row.authorization,
        }

    async def audit(
        self,
        scope_id,
        *,
        action: str | None = None,
        actor_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ):
        require(1 <= limit <= 200, "limit", "审计每页条数须在 1 至 200 之间")
        require(0 <= offset <= 100_000, "offset", "分页偏移超出范围")
        _, actions = await authorize(self.db, self.actor, scope_id, "admin")
        require("secret" in actions, "audit", "完整审计需要秘密内容权限", 403)
        stmt = select(Audit).where(
            or_(
                Audit.scope_id == scope_id,
                and_(
                    Audit.scope_id == SYSTEM_SCOPE,
                    Audit.action == "scope.create",
                    Audit.detail["scope_id"].astext == scope_id,
                ),
            )
        )
        if action and action.strip():
            stmt = stmt.where(Audit.action == action.strip())
        if actor_id and actor_id.strip():
            stmt = stmt.where(Audit.actor_id == actor_id.strip())
        rows = (await self.db.scalars(stmt.order_by(Audit.created_at.desc()).offset(offset).limit(limit))).all()
        actor_ids = {r.actor_id for r in rows if r.actor_id}
        usernames: dict[str, str] = {}
        if actor_ids:
            user_rows = (
                await self.db.execute(select(User.id, User.username).where(User.id.in_(actor_ids)))
            ).all()
            usernames = {uid_val: uname for uid_val, uname in user_rows if uname}
        return jsonable(
            [
                {
                    "id": r.id,
                    "actor_id": r.actor_id,
                    "actor_username": usernames.get(r.actor_id) or (r.actor_id[:8] if r.actor_id else ""),
                    "action": r.action,
                    "version": r.version,
                    "detail": r.detail,
                    "created_at": r.created_at,
                }
                for r in rows
            ]
        )

    async def operations_status(self, scope_id):
        _, actions = await authorize(self.db, self.actor, scope_id, "read")
        require(
            bool({"operate", "edit", "assess", "export"} & set(actions)),
            "forbidden",
            "当前范围未授予此操作",
            403,
        )
        counts = (
            await self.db.execute(
                select(Job.state, func.count())
                .where(
                    Job.scope_id == scope_id,
                    Job.kind.not_in(["author-draft", "index"]),
                )
                .group_by(Job.state)
            )
        ).all()
        worker = {"online": False, "last_seen_at": None, "stale_seconds": None}
        sys_scope = await self.db.get(Scope, SYSTEM_SCOPE)
        heartbeat = (sys_scope.config or {}).get("worker_heartbeat") if sys_scope else None
        if isinstance(heartbeat, dict) and isinstance(heartbeat.get("updated_at"), str):
            try:
                parsed = datetime.fromisoformat(heartbeat["updated_at"].replace("Z", "+00:00"))
                if parsed.tzinfo is not None:
                    stale = max(0, int((utcnow() - parsed).total_seconds()))
                    worker = {
                        "online": stale <= 45,
                        "last_seen_at": parsed.isoformat(),
                        "stale_seconds": stale,
                    }
            except ValueError:
                pass
        return {
            "jobs": dict(counts),
            "worker": worker,
            "policy_hash": POLICY_HASH,
            "version": "4.0.0",
            "database": "PostgreSQL",
            "backup": "CLI维护命令管理；恢复演练结果以实际报告为准",
        }
