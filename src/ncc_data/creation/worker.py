"""Durable orchestration: external calls outside transactions, every continuation fenced."""

import asyncio
import copy
import os
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import and_, or_, select

from ncc_data.application.model_settings import snapshot_model_route
from ncc_data.application.security import authorize
from ncc_data.application.service import Service
from ncc_data.creation.gateway import ChatProvider
from ncc_data.creation.model_route import ensure_job_route, materialize_one, purpose_slot
from ncc_data.creation.scoring import disagreement, evaluate
from ncc_data.creation.worker_stages import (
    _append_draft_candidate,
    _append_judged_candidate,
    _append_plan_candidate,
    _apply_explicit,
    _needs_revision_judge,
    _scope_volumes_and_chapters,
    _studio_inputs,
    accept_task,
    begin_explicit_stage,
    checked_delegation,
    create_task,
    explicit_transition,
    validate_stage_order,
)
from ncc_data.domain.contracts import ChangeInput, CreationInput
from ncc_data.domain.creation import creation_scheme
from ncc_data.domain.definitions import SYSTEM_SCOPE
from ncc_data.domain.studio_catalog import producer_guidance
from ncc_data.persistence.models import (
    Assessment,
    ImportRun,
    Job,
    Scope,
    User,
    uid,
    utcnow,
)
from ncc_shared.errors import DomainError, require
from ncc_shared.quality.policy import POLICY, POLICY_HASH
from ncc_shared.serialization import digest

__all__ = [
    "ChangeInput",
    "CreationInput",
    "Worker",
    "_append_draft_candidate",
    "_append_judged_candidate",
    "_append_plan_candidate",
    "_apply_explicit",
    "_needs_revision_judge",
    "_scope_volumes_and_chapters",
    "_studio_inputs",
    "accept_task",
    "begin_explicit_stage",
    "checked_delegation",
    "create_task",
    "explicit_transition",
    "validate_stage_order",
]


class Worker:
    def __init__(
        self, factory, settings, provider=None, *, actor_ids=None, scope_ids=None, job_ids=None
    ):
        self.factory, self.settings = factory, settings
        self.provider = provider or ChatProvider(settings)
        self.actor_ids = set(actor_ids) if actor_ids is not None else None
        self.scope_ids = set(scope_ids) if scope_ids is not None else None
        self.job_ids = set(job_ids) if job_ids is not None else None

    async def claim(self, *, job_id=None):
        async with self.factory() as db, db.begin():
            now = utcnow()
            allowed_actors = (
                self.actor_ids
                if self.actor_ids is not None
                else getattr(self.factory, "_test_actor_ids", None)
            )
            stmt = select(Job).where(
                Job.cancel_requested.is_(False),
                Job.attempts < 3,
                or_(Job.state == "queued", and_(Job.state == "running", Job.lease_until < now)),
            )
            if job_id is not None:
                stmt = stmt.where(Job.id == job_id)
            elif self.job_ids is not None:
                stmt = stmt.where(Job.id.in_(self.job_ids))
            if allowed_actors is not None:
                stmt = stmt.where(Job.actor_id.in_(allowed_actors))
            if self.scope_ids is not None:
                stmt = stmt.where(Job.scope_id.in_(self.scope_ids))
            row = await db.scalar(stmt.order_by(Job.created_at).with_for_update(skip_locked=True).limit(1))
            if not row:
                return None
            row.state, row.lease_token, row.lease_until = "running", uid(), now + timedelta(minutes=10)
            row.attempts += 1
            row.updated_at = now
            return row.id, row.lease_token

    async def fenced(self, db, job_id, token):
        row = await db.scalar(
            select(Job).where(Job.id == job_id).with_for_update().execution_options(populate_existing=True)
        )
        require(
            row
            and row.lease_token == token
            and row.state == "running"
            and not row.cancel_requested
            and row.lease_until > utcnow(),
            "lease_lost",
            "任务已暂停、撤销或由其他执行者接管",
            409,
        )
        actor = await db.get(User, row.actor_id)
        require(actor and actor.active, "actor_revoked", "任务操作者已失效", 403)
        if row.payload.get("allowed_actions") is not None:
            actor._access_scope, actor._access_actions = row.scope_id, set(row.payload["allowed_actions"])
        if row.payload.get("credential_id"):
            from ncc_data.persistence.models import Session

            credential = await db.get(Session, row.payload["credential_id"])
            require(
                credential and not credential.revoked and credential.expires_at > utcnow(),
                "credential_revoked",
                "任务凭据已撤销",
                403,
            )
        required_action = (
            "export"
            if row.kind == "export"
            else "assess"
            if row.kind == "creation" and row.payload.get("mode") == "assess"
            else "edit"
        )
        _, actions = await authorize(db, actor, row.scope_id, required_action)
        if row.kind == "creation":
            await authorize(db, actor, row.scope_id, "assess")
        require(
            not row.payload.get("requires_secret") or "secret" in actions,
            "permission_revoked",
            "任务所需秘密内容权限已撤销",
            403,
        )
        row.lease_until, row.updated_at = utcnow() + timedelta(minutes=10), utcnow()
        return row, Service(db, actor)

    async def run_once(self, *, job_id=None):
        claimed = await self.claim(job_id=job_id)
        if not claimed:
            return False
        job_id, token = claimed
        self.last_usage = None
        try:
            async with self.factory() as db, db.begin():
                row, service = await self.fenced(db, job_id, token)
                kind = row.kind
                if kind == "index":
                    row.result = {
                        "covered_version": row.payload["version"],
                        "note": "事务写入已维护当前检索投影",
                    }
                    row.state = "succeeded"
                    row.lease_token, row.lease_until, row.updated_at = None, None, utcnow()
                elif kind == "export":
                    fmt = row.payload["format"]
                    if fmt in {"manuscript_md", "txt", "epub"}:
                        data, media_type, _, filename, meta = await service.export_manuscript(
                            row.scope_id,
                            row.payload["version"],
                            fmt,
                            volume_id=row.payload.get("volume_id"),
                            only_done=bool(row.payload.get("only_done")),
                            author=row.payload.get("author") or "",
                        )
                        uploaded = await service.upload(
                            row.scope_id,
                            filename,
                            media_type,
                            data,
                            purpose="export",
                            limit=256 * 1024 * 1024,
                            requires_secret=False,
                        )
                        result = {**uploaded, **meta}
                    else:
                        data, media_type, ext = await service.export_bytes(
                            row.scope_id, row.payload["version"], fmt
                        )
                        result = await service.upload(
                            row.scope_id,
                            f"ncc-export-v{row.payload['version']}.{ext}",
                            media_type,
                            data,
                            purpose="export",
                            limit=256 * 1024 * 1024,
                        )
                    row.result, row.state = result, "succeeded"
                    row.lease_token, row.lease_until, row.updated_at = None, None, utcnow()
                elif kind == "import":
                    await self.import_batch(db, row, service)
                elif kind != "creation":
                    raise DomainError("job_kind", "未知任务类型")
            if kind == "creation":
                await self.creation(job_id, token)
        except DomainError as exc:
            async with self.factory() as db, db.begin():
                row = await db.get(Job, job_id)
                if row and row.lease_token == token and row.state == "running":
                    self.account_usage(row)
                    row.state = "waiting" if exc.status in {403, 409, 422} else "failed"
                    row.result = {**row.result, "error": {"code": exc.code, "detail": exc.detail}}
                    row.lease_token, row.lease_until = None, None
                    row.updated_at = utcnow()
        except Exception:
            async with self.factory() as db, db.begin():
                row = await db.get(Job, job_id)
                if row and row.lease_token == token and row.state == "running":
                    self.account_usage(row)
                    row.state = "failed"
                    row.result = {
                        **row.result,
                        "error": {
                            "code": "worker_failure",
                            "detail": "任务失败，原件和已提交回执保留；请检查受控运行日志",
                        },
                    }
                    row.lease_token, row.lease_until = None, None
                    row.updated_at = utcnow()
        return True

    async def run_job(self, job_id: str) -> bool:
        return await self.run_once(job_id=job_id)

    def account_usage(self, row):
        entry = getattr(self, "last_usage", None)
        if entry and entry[0] == row.id and row.progress.get("usage_id") != entry[1]:
            row.progress = {
                **row.progress,
                "tokens": row.progress.get("tokens", 0) + entry[2]["tokens"],
                "usage_id": entry[1],
                "usage_kind": entry[2]["kind"],
            }

    async def import_batch(self, db, row, service):
        imported = await db.get(ImportRun, row.payload["import_id"])
        info = await service.scope_info(row.scope_id)
        require(
            info["version"] == row.payload["expected_version"],
            "version_conflict",
            "批次间内容变化，暂停导入以重新对账",
            409,
        )
        start = row.progress["committed"]
        batch_index = row.progress.get("batch", 0)
        operations = imported.plan["batches"][batch_index]
        change = await service.create_change(
            row.scope_id,
            ChangeInput(
                title=f"导入{imported.id}/{start}", base_version=info["version"], operations=operations
            ),
        )
        receipt = await service.adopt(row.scope_id, change["id"], f"import:{imported.id}:{start}")
        end = start + len(operations)
        row.progress = {**row.progress, "committed": end, "batch": batch_index + 1}
        row.payload = {**row.payload, "expected_version": receipt["version"]}
        row.result = {**row.result, "last_receipt": receipt, "unmapped_retained": imported.plan["warnings"]}
        row.state = "succeeded" if end == len(imported.plan["rows"]) else "queued"
        if row.state == "queued":
            row.attempts = 0
        row.lease_token, row.lease_until, row.updated_at = None, None, utcnow()
        imported.state = row.state

    async def packet(self, service, row):
        payload = row.payload
        scope, _ = await authorize(
            service.db, service.actor, row.scope_id, "assess" if payload.get("mode") == "assess" else "edit"
        )
        require(
            scope.version == payload["base_version"],
            "version_conflict",
            "创作基线已变化，请比较后重新发起",
            409,
        )
        target = (
            await service.entity(row.scope_id, payload["entity_id"]) if payload.get("entity_id") else None
        )
        sources, ids = [], []
        for eid in payload.get("source_ids", []):
            obj = await service.entity(row.scope_id, eid)
            sources.append(
                {"id": eid, "revision": obj["revision"], "name": obj["name"], "text": obj["text"][:16000]}
            )
            ids.append(eid)
        for ref in payload.get("commons_refs") or []:
            # Cross-scope rows are read-only context. Persist only auditable reference & version;
            # live permissions and field redaction are re-evaluated on every model call and job view.
            obj = await self._read_cross_scope_source(
                service, payload, ref["scope_id"], ref["entity_id"], revision_id=None
            )
            sources.append(
                {
                    "id": ref["entity_id"],
                    "scope_id": ref["scope_id"],
                    "revision": obj["revision"],
                    "version": obj["version"],
                    "content_hash": obj.get("content_hash") or digest(obj.get("text") or ""),
                    "readonly": True,
                }
            )
        # Only strictly preceding chapters in canonical book-wide order enter the default writing packet.
        _, ordered_chapters = await _scope_volumes_and_chapters(service, scope)
        if target and target.get("kind") in {"chapter", "章节"}:
            target_index = next((idx for idx, c in enumerate(ordered_chapters) if c["id"] == target["id"]), None)
            prior_candidates = ordered_chapters[:target_index] if target_index is not None else []
            next_position = target.get("data", {}).get("position", 0)
        else:
            prior_candidates = ordered_chapters
            loose_positions = [
                int((c.get("data") or {}).get("position", 0))
                for c in ordered_chapters
                if not (c.get("data") or {}).get("parent_id")
                and isinstance((c.get("data") or {}).get("position", 0), int)
                and not isinstance((c.get("data") or {}).get("position", 0), bool)
            ]
            next_position = (max(loose_positions) + 1) if loose_positions else (0 if ordered_chapters else 1)
        previous = []
        for cand in reversed(prior_candidates):
            try:
                full = await service.entity(row.scope_id, cand["id"])
            except DomainError:
                continue
            previous.append(full)
            if len(previous) >= 3:
                break
        previous.reverse()
        for full in previous:
            sources.append(
                {
                    "id": full["id"],
                    "revision": full["revision"],
                    "name": full["name"],
                    "text": full["text"][-8000:],
                }
            )
            ids.append(full["id"])
        definition = await service.definition(scope, payload["kind"])
        built = {
            "objective": payload["objective"],
            "kind": payload["kind"],
            "name": payload["name"],
            "current": target["text"] if target else "",
            "current_data": target["data"] if target else {},
            "sources": sources,
            "entity_ids": ids,
            "properties": definition.spec.get("properties", {}),
            "next_position": next_position,
        }
        if _studio_inputs(payload):
            built["producer_guidance"] = producer_guidance(payload, scope.config)
        return built

    async def _read_cross_scope_source(self, service, payload, scope_id, entity_id, revision_id=None):
        if payload.get("credential_id"):
            reader_svc = service
        else:
            reader = copy.copy(service.actor)
            for attr in ("_access_scope", "_access_actions"):
                if hasattr(reader, attr):
                    delattr(reader, attr)
            reader_svc = Service(service.db, reader)
        live = await reader_svc.entity(scope_id, entity_id)
        if revision_id:
            pinned = await reader_svc.revision(scope_id, entity_id, revision_id)
            require(not pinned.get("deleted"), "not_found", "引用对象已停用", 404)
            return pinned
        return live

    async def _materialize_packet_sources(self, service, row, raw_sources):
        model_sources, clipped = [], []
        for entry in raw_sources or []:
            if not (isinstance(entry, dict) and entry.get("scope_id") and entry.get("scope_id") != row.scope_id):
                model_sources.append(copy.deepcopy(entry))
                continue
            try:
                obj = await self._read_cross_scope_source(
                    service,
                    row.payload,
                    entry["scope_id"],
                    entry["id"],
                    revision_id=entry.get("revision"),
                )
                model_sources.append(
                    {
                        "id": entry["id"],
                        "scope_id": entry["scope_id"],
                        "revision": obj["revision"],
                        "version": obj["version"],
                        "content_hash": entry.get("content_hash") or obj.get("content_hash"),
                        "name": obj["name"],
                        "kind": obj["kind"],
                        "data": obj["data"] or {},
                        "text": (obj.get("text") or "")[:16000],
                        "readonly": True,
                    }
                )
            except DomainError:
                clipped.append(entry["id"])
        return model_sources, clipped

    async def creation(self, job_id, token):
        while True:
            async with self.factory() as db, db.begin():
                row, service = await self.fenced(db, job_id, token)
                require(
                    row.payload["policy_hash"] == POLICY_HASH,
                    "policy_changed",
                    "评分策略已更新，请重新发起",
                    409,
                )
                scope, actions = await authorize(
                    db,
                    service.actor,
                    row.scope_id,
                    "assess" if row.payload.get("mode") == "assess" else "edit",
                )
                require(
                    scope.version == row.payload["base_version"],
                    "version_conflict",
                    "创作输入已被修改，保留候选并等待比较",
                    409,
                )
                require(
                    not row.payload.get("requires_secret") or "secret" in actions,
                    "forbidden",
                    "输入秘密权限已变化",
                    403,
                )
                progress, result = dict(row.progress), copy.deepcopy(row.result)
                if "model_route" not in result:
                    result["model_route"] = await snapshot_model_route(db, self.settings)
                result["model_route"] = ensure_job_route(result["model_route"])
                if "packet" not in result:
                    result["packet"] = await self.packet(service, row)
                stage = progress.get("stage", "prepare")
                packet = copy.deepcopy(result["packet"])
                model_sources, clipped_ids = await self._materialize_packet_sources(
                    service, row, packet.get("sources")
                )
                packet["sources"] = model_sources
                if clipped_ids:
                    result["clipped_source_ids"] = sorted(
                        set([*(result.get("clipped_source_ids") or []), *clipped_ids])
                    )
                sources = [s["text"] for s in model_sources]
                scheme = row.payload["scheme"]
                budget = row.payload["token_budget"] - progress.get("tokens", 0)
                if stage == "prepare":
                    if row.payload.get("stages"):
                        stored_sources = result["packet"].get("sources")
                        stage = begin_explicit_stage(row.payload, result, packet)
                        if "packet" in result and stored_sources is not None:
                            result["packet"] = {**result["packet"], "sources": stored_sources}
                        packet["sources"] = model_sources
                    elif row.payload.get("mode") == "assess":
                        result["draft"] = {"text": packet["current"], "data": {}, "claims": []}
                        stage = "judge"
                    else:
                        stage = "plan" if scheme == "P1" else "write"
                if scheme == "P5" and stage not in {"judge_plan", "judge_revision"}:
                    scheme = creation_scheme(row.payload)
                if stage in {"plan", "write", "revise"}:
                    purpose = stage
                    if result.get("plan") and purpose != "plan":
                        packet["scene_plan"] = result["plan"]["text"]
                    if purpose == "revise":
                        if result.get("candidates") and result["candidates"][-1].get("artifact") != "plan":
                            prev_cand = result["candidates"][-1]
                            packet["current"] = prev_cand["text"]
                            packet["revision_notes"] = (
                                prev_cand.get("evaluation", {}).get("report", {}).get("suggestions", [])
                                or packet.get("revision_notes")
                                or []
                            )
                            result["revision_before"] = prev_cand["text"]
                            result["revision_prior_evaluation"] = prev_cand.get("evaluation")
                        else:
                            result["revision_before"] = result["packet"].get("current") or ""
                            result["revision_prior_evaluation"] = None
                    if row.payload.get("selection_start") is not None:
                        start, end = row.payload["selection_start"], row.payload["selection_end"]
                        packet["current"] = result["packet"]["current"][start:end]
                        packet["scope"] = "仅返回选中段落的新文本；上下文只用于保持衔接"
                elif stage == "judge_plan":
                    purpose, scheme = "judge", "P2"
                    packet = {
                        "objective": packet["objective"],
                        "content": result["plan"]["text"],
                        "sources": sources,
                        "rubric": POLICY["profiles"][scheme],
                        "scale": "0无有效完成;3基本可用;4良好;5有锚定依据的突出表现",
                    }
                else:
                    purpose = "judge_secondary" if stage == "judge_second" else "judge"
                    if stage == "judge_revision":
                        scheme = "P5"
                    packet = {
                        "objective": packet["objective"],
                        "content": result["draft"]["text"],
                        "sources": sources,
                        "rubric": POLICY["profiles"][scheme],
                        "scale": "0无有效完成;3基本可用;4良好;5有锚定依据的突出表现",
                    }
                    if stage == "judge_revision":
                        packet.update(
                            before=result.get("revision_before", result["packet"]["current"]),
                            requested_scope=row.payload.get("selection_start"),
                            prior_issues=result.get("revision_prior_evaluation"),
                        )
                resolved = materialize_one(purpose_slot(result["model_route"], purpose), self.settings)
                row.result = result
                row.progress = {**progress, "stage": stage}
            # No database session/lock is kept across model I/O.
            require(budget >= 256, "token_budget", "任务预算不足，已有用量和成果保留，请明确新任务预算", 409)
            self.provider.route = resolved
            if isinstance(self.provider, ChatProvider):
                judge_key = purpose_slot(result["model_route"], "judge").get("model_key") or ""
                write_key = purpose_slot(result["model_route"], "write").get("model_key") or ""
                self.provider.identity = "chat:" + (judge_key or write_key)
            try:
                response, usage = await self.provider.call(purpose, packet, budget)
            finally:
                self.provider.route = None
            self.last_usage = (job_id, uid(), usage)
            async with self.factory() as db, db.begin():
                row, service = await self.fenced(db, job_id, token)
                progress, result = dict(row.progress), copy.deepcopy(row.result)
                progress["tokens"] = progress.get("tokens", 0) + usage["tokens"]
                progress["usage_kind"] = usage["kind"]
                progress["usage_id"] = self.last_usage[1]
                if progress["tokens"] > row.payload["token_budget"]:
                    row.progress = progress
                    row.result = {
                        **result,
                        "error": {"code": "token_budget", "detail": "预算已耗尽，保留已提交候选和实际用量"},
                    }
                    row.state, row.lease_token, row.lease_until = "waiting", None, None
                    return
                if purpose not in {"judge", "judge_secondary"}:
                    if not (
                        isinstance(response.get("text"), str)
                        and 0 < len(response["text"]) <= 2_000_000
                        and isinstance(response.get("data", {}), dict)
                        and isinstance(response.get("claims", []), list)
                    ):
                        row.progress = progress
                        row.result = {
                            **result,
                            "error": {
                                "code": "model_output",
                                "detail": "模型返回无效成果；本次用量已记录，原稿保留",
                            },
                        }
                        row.state, row.lease_token, row.lease_until = "waiting", None, None
                        return
                    if stage == "plan":
                        result["plan"] = response
                        if row.payload.get("stages"):
                            _apply_explicit(
                                row,
                                progress,
                                result,
                                explicit_transition(
                                    row.payload["stages"],
                                    stage,
                                    qualified=True,
                                    revisions=progress.get("revisions", 0),
                                    max_revisions=row.payload["max_revisions"],
                                ),
                            )
                        else:
                            progress["stage"] = "judge_plan"
                    else:
                        if row.payload.get("selection_start") is not None:
                            original = result["packet"]["current"]
                            response["text"] = (
                                original[: row.payload["selection_start"]]
                                + response["text"]
                                + original[row.payload["selection_end"] :]
                            )
                        if row.payload["kind"] in {"chapter", "章节"} and not row.payload.get("entity_id"):
                            response["data"] = {
                                **response.get("data", {}),
                                "position": result["packet"]["next_position"],
                            }
                        if stage == "revise":
                            progress["revised_prose"] = True
                        else:
                            progress["revised_prose"] = False
                        result["draft"] = response
                        if row.payload.get("stages"):
                            _apply_explicit(
                                row,
                                progress,
                                result,
                                explicit_transition(
                                    row.payload["stages"],
                                    stage,
                                    qualified=True,
                                    revisions=progress.get("revisions", 0),
                                    max_revisions=row.payload["max_revisions"],
                                ),
                            )
                        else:
                            progress["stage"] = "judge"
                else:
                    content = result["plan"]["text"] if stage == "judge_plan" else result["draft"]["text"]
                    evaluation = evaluate(scheme, content, response, sources)
                    assessment = Assessment(
                        scope_id=row.scope_id,
                        actor_id=row.actor_id,
                        entity_id=row.payload.get("entity_id"),
                        content_hash=digest(content),
                        dependency_version=row.payload["base_version"],
                        scheme=scheme,
                        policy_hash=POLICY_HASH,
                        evaluator=(
                            "chat:" + purpose_slot(result["model_route"], "judge_secondary").get("model_key", "")
                        )
                        if stage == "judge_second"
                        else self.provider.identity,
                        report={**evaluation, "requires_secret": row.payload.get("requires_secret", False)},
                        score=Decimal(evaluation["score"]) if evaluation.get("score") is not None else None,
                        verdict=evaluation["verdict"],
                    )
                    db.add(assessment)
                    await db.flush()
                    qualified = evaluation["verdict"] == "qualified"
                    if row.payload.get("stages") and stage == "judge_plan":
                        result["plan_evaluation"] = evaluation
                        result["plan_valid"] = qualified
                        result["plan_assessment_id"] = assessment.id
                        _apply_explicit(
                            row,
                            progress,
                            result,
                            explicit_transition(
                                row.payload["stages"],
                                stage,
                                qualified=qualified,
                                revisions=progress.get("revisions", 0),
                                max_revisions=row.payload["max_revisions"],
                            ),
                            assessment_id=assessment.id,
                            evaluation=evaluation,
                            scheme=scheme,
                            content=content,
                        )
                    elif stage == "judge_plan":
                        result["plan_evaluation"] = evaluation
                        result["plan_valid"] = qualified
                        if qualified:
                            progress["stage"] = "write"
                        elif progress.get("revisions", 0) < row.payload["max_revisions"]:
                            progress["revisions"] = progress.get("revisions", 0) + 1
                            progress["stage"] = "plan"
                            result["packet"] = {
                                **result["packet"],
                                "plan_feedback": evaluation.get("report", {}).get("suggestions", []),
                            }
                        else:
                            row.state = "waiting"
                    elif stage == "judge_second":
                        candidate = result["candidates"][-1]
                        candidate["second_evaluation"] = evaluation
                        candidate["second_assessment_id"] = assessment.id
                        candidate["disputed"] = disagreement(candidate["evaluation"], evaluation)
                        if candidate["disputed"]:
                            row.state = "waiting"
                            result["error"] = {
                                "code": "assessment_disagreement",
                                "detail": "评价分歧超阈值，需争议复核；没有平均放行",
                            }
                        elif _needs_revision_judge(row, progress):
                            progress["stage"] = "judge_revision"
                        else:
                            self.route_candidate(row, progress, result)
                    elif stage == "judge_revision":
                        candidate = result["candidates"][-1]
                        candidate["revision_evaluation"] = evaluation
                        candidate["revision_assessment_id"] = assessment.id
                        if evaluation["verdict"] != "qualified":
                            candidate["revision_hold"] = True
                        self.route_candidate(row, progress, result)
                    else:
                        candidate = {
                            **result["draft"],
                            "assessment_id": assessment.id,
                            "evaluation": evaluation,
                            "hash": digest(content),
                            "scheme": scheme,
                            "revised_prose": bool(progress.get("revised_prose")),
                        }
                        result.setdefault("candidates", []).append(candidate)
                        result["selected"] = len(result["candidates"]) - 1
                        if row.payload.get("mode") == "assess":
                            row.state = "succeeded"
                        elif purpose_slot(result["model_route"], "judge_secondary").get("model_key"):
                            progress["stage"] = "judge_second"
                        elif _needs_revision_judge(row, progress):
                            progress["stage"] = "judge_revision"
                        else:
                            self.route_candidate(row, progress, result)
                row.progress, row.result = progress, result
                row.updated_at = utcnow()
                if row.state != "running":
                    if (
                        row.state in {"qualified", "waiting"}
                        and row.payload.get("delegation_id")
                        and "auto_hold" not in row.result
                    ):
                        nested = await db.begin_nested()
                        try:
                            await accept_task(service, row.scope_id, row.id, "auto:" + row.id, automatic=True)
                        except DomainError as exc:
                            await nested.rollback()
                            await db.refresh(row)
                            row.result = {**row.result, "auto_hold": {"code": exc.code, "detail": exc.detail}}
                        else:
                            await nested.commit()
                    row.lease_token, row.lease_until = None, None
                    row.updated_at = utcnow()
                    return

    def route_candidate(self, row, progress, result):
        candidate = result["candidates"][-1]
        qualified = bool(
            candidate["evaluation"]["verdict"] == "qualified"
            and not candidate.get("revision_hold")
            and not candidate.get("disputed")
            and (
                not candidate.get("second_evaluation")
                or candidate["second_evaluation"].get("verdict") == "qualified"
            )
        )
        if row.payload.get("stages"):
            decision = explicit_transition(
                row.payload["stages"],
                "judge",
                qualified=qualified,
                revisions=progress.get("revisions", 0),
                max_revisions=row.payload["max_revisions"],
            )
            decision = {k: v for k, v in decision.items() if k != "attach_judged"}
            _apply_explicit(row, progress, result, decision)
            return
        if qualified:
            row.state = "qualified"
        elif progress.get("revisions", 0) < row.payload["max_revisions"]:
            progress["revisions"] = progress.get("revisions", 0) + 1
            progress["stage"] = "revise"
        else:
            row.state = "waiting"

    async def record_heartbeat(self) -> None:
        async with self.factory() as db, db.begin():
            scope = await db.scalar(
                select(Scope)
                .where(Scope.id == SYSTEM_SCOPE)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if scope is None:
                return
            config = dict(scope.config or {})
            config["worker_heartbeat"] = {
                "updated_at": utcnow().isoformat(),
                "pid": os.getpid(),
            }
            scope.config = config

    async def _heartbeat_loop(self, interval: float = 12.0) -> None:
        while True:
            await asyncio.sleep(interval)
            try:
                await self.record_heartbeat()
            except Exception:
                pass

    async def run(self, once=False):
        await self.record_heartbeat()
        if once:
            return await self.run_once()
        beat_task = asyncio.create_task(self._heartbeat_loop(12.0))
        try:
            while True:
                worked = await self.run_once()
                if not worked:
                    await asyncio.sleep(1)
        finally:
            beat_task.cancel()
            try:
                await beat_task
            except asyncio.CancelledError:
                pass
