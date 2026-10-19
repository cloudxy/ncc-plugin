"""Management use cases shared by HTTP, CLI and workers."""

from datetime import timedelta

from sqlalchemy import func, select

from .calibration import CalibrationMixin
from .changes import ChangeService
from .contracts import DelegationInput, Query, StateQuery
from .errors import DomainError, require
from .exchange import ExchangeMixin
from .maintenance import MaintenanceMixin
from .models import (
    Assessment,
    Audit,
    ChangeSet,
    Delegation,
    Feedback,
    Job,
    Membership,
    User,
    utcnow,
)
from .policy import POLICY_HASH
from .security import authorize, password_hash
from .utils import jsonable
from .workspace import WorkspaceMixin


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
                task.state, task.cancel_requested, task.lease_token = "paused", True, None
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
        require(await self.db.get(User, value.user_id), "member", "用户不存在")
        row = await self.db.scalar(
            select(Membership).where(Membership.scope_id == scope_id, Membership.user_id == value.user_id)
        )
        if row:
            row.actions = sorted(set(value.actions))
        else:
            self.db.add(
                Membership(scope_id=scope_id, user_id=value.user_id, actions=sorted(set(value.actions)))
            )
        self.db.add(
            Audit(
                scope_id=scope_id,
                actor_id=self.actor.id,
                action="member.set",
                version=scope.version,
                detail={"user_id": value.user_id, "actions": value.actions},
            )
        )
        await self.db.flush()
        return await self.members(scope_id)

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
        await self.entity(scope_id, center)
        relations = (await self.facts(scope_id, StateQuery(category="relation", limit=200)))["items"]
        nodes, edges, frontier = {center}, [], {center}
        for _ in range(hops):
            chosen = [f for f in relations if f["subject_id"] in frontier or f["object_id"] in frontier]
            frontier = {v for f in chosen for v in (f["subject_id"], f["object_id"]) if v} - nodes
            nodes.update(frontier)
            edges += [f for f in chosen if f["id"] not in {e["id"] for e in edges}]
        items = []
        for eid in list(nodes)[:500]:
            try:
                item = await self.entity(scope_id, eid)
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
        return jsonable(
            {
                "id": row.id,
                "kind": row.kind,
                "state": row.state,
                "progress": row.progress,
                "payload": row.payload if details else {},
                "result": row.result if details else {},
                "attempts": row.attempts,
                "cancel_requested": row.cancel_requested,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
        )

    async def jobs(self, scope_id):
        _, actions = await authorize(self.db, self.actor, scope_id)
        statement = select(Job).where(Job.scope_id == scope_id, Job.kind != "author-draft")
        if not {"admin", "secret"} <= set(actions):
            statement = statement.where(Job.actor_id == self.actor.id)
        rows = (await self.db.scalars(statement.order_by(Job.created_at.desc()).limit(100))).all()
        return [
            self.job_json(r, details=bool({"edit", "assess"} & set(actions)))
            for r in rows
            if not r.payload.get("requires_secret") or "secret" in actions
        ]

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
        return self.job_json(row)

    async def assessments(self, scope_id):
        scope, actions = await authorize(self.db, self.actor, scope_id)
        statement = select(Assessment).where(Assessment.scope_id == scope_id)
        if "secret" not in actions:
            statement = statement.where(Assessment.actor_id == self.actor.id)
        rows = (await self.db.scalars(statement.order_by(Assessment.created_at.desc()).limit(100))).all()
        return [
            {
                "id": r.id,
                "entity_id": r.entity_id,
                "score": str(r.score) if r.score is not None else None,
                "verdict": r.verdict,
                "scheme": r.scheme,
                "report": r.report,
                "fresh": r.dependency_version == scope.version and r.policy_hash == POLICY_HASH,
                "evaluator": r.evaluator,
                "content_hash": r.content_hash,
            }
            for r in rows
            if not r.report.get("requires_secret", True) or "secret" in actions
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

    async def audit(self, scope_id):
        _, actions = await authorize(self.db, self.actor, scope_id, "admin")
        require("secret" in actions, "audit", "完整审计需要秘密内容权限", 403)
        rows = (
            await self.db.scalars(
                select(Audit).where(Audit.scope_id == scope_id).order_by(Audit.created_at.desc()).limit(200)
            )
        ).all()
        return jsonable(
            [
                {
                    "id": r.id,
                    "actor_id": r.actor_id,
                    "action": r.action,
                    "version": r.version,
                    "detail": r.detail,
                    "created_at": r.created_at,
                }
                for r in rows
            ]
        )

    async def operations_status(self, scope_id):
        await authorize(self.db, self.actor, scope_id, "operate")
        counts = (
            await self.db.execute(
                select(Job.state, func.count()).where(Job.scope_id == scope_id).group_by(Job.state)
            )
        ).all()
        return {
            "jobs": dict(counts),
            "policy_hash": POLICY_HASH,
            "version": "4.0.0",
            "database": "PostgreSQL",
            "backup": "CLI维护命令管理；恢复演练结果以实际报告为准",
        }
