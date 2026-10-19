"""Durable orchestration: external calls outside transactions, every continuation fenced."""

import asyncio
import copy
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import and_, or_, select

from .contracts import ChangeInput, CreationInput, Query
from .errors import DomainError, require
from .models import Assessment, Audit, Calibration, Delegation, ImportRun, Job, User, uid, utcnow
from .policy import POLICY, POLICY_HASH
from .provider import ChatProvider
from .scoring import disagreement, evaluate
from .security import authorize
from .service import Service
from .utils import digest


async def checked_delegation(service, scope, delegation_id, entity_id, schemes):
    row = await service.db.get(Delegation, delegation_id) if delegation_id else None
    require(
        row
        and row.scope_id == scope.id
        and row.actor_id == service.actor.id
        and not row.revoked
        and row.expires_at > utcnow()
        and row.remaining > 0
        and entity_id in row.target_ids
        and set(schemes) <= set(row.schemes),
        "delegation",
        "没有覆盖此对象及方案的有效托管授权",
        403,
    )
    authorization = row.authorization or {}
    mode = authorization.get("mode", "calibrated")
    require(mode in {"calibrated", "author_trial"}, "delegation", "未知授权模式", 403)
    require(
        authorization.get("policy_hash") == POLICY_HASH,
        "delegation_policy",
        "评分策略已变化，须重新授权",
        409,
    )
    if mode == "author_trial":
        require(
            scope.owner_id == service.actor.id and authorization.get("note", "").strip(),
            "owner_only",
            "试运行授权须保留作品所有者的明确依据",
            403,
        )
    return row, mode


def creation_scheme(payload):
    if payload["scheme"] != "P5":
        return payload["scheme"]
    return payload.get("content_scheme") or {
        "chapter": "P1",
        "章节": "P1",
        "outline": "P2",
        "scene": "P2",
        "volume": "P2",
        "source": "P4",
        "legacy-file": "P4",
    }.get(payload["kind"], "P3")


async def create_task(service, scope_id, value: CreationInput):
    scope, actions = await authorize(service.db, service.actor, scope_id, "assess", lock=True)
    if value.mode != "assess":
        await authorize(service.db, service.actor, scope_id, "edit")
    target = await service.entity(scope_id, value.entity_id) if value.entity_id else None
    payload = value.model_dump(mode="json")
    payload["kind"] = target["kind"] if target else value.kind
    if value.scheme == "P5":
        payload["content_scheme"] = creation_scheme(payload)
    require(value.mode != "assess" or target, "assessment_target", "单独评分需要已有内容对象")
    if value.delegation_id:
        await authorize(service.db, service.actor, scope_id, "adopt")
        require(
            value.mode == "create" and target,
            "delegation_target",
            "自动定稿须选择已有对象，单独评分不采用正文",
        )
        schemes = {value.scheme, creation_scheme(payload)}
        await checked_delegation(service, scope, value.delegation_id, value.entity_id, schemes)
    if value.selection_start is not None or value.selection_end is not None:
        require(
            target
            and value.selection_start is not None
            and value.selection_end is not None
            and 0 <= value.selection_start < value.selection_end <= len(target["text"]),
            "selection",
            "选段边界超出当前正文",
        )
    requires_secret = "secret" in actions
    for source in value.source_ids:
        source_entity = await service.entity(scope_id, source)
        requires_secret |= bool(source_entity.get("secret"))
    payload.update(
        base_version=scope.version,
        policy_hash=POLICY_HASH,
        expected=target["version"] if target else None,
        requires_secret=requires_secret,
        allowed_actions=sorted(actions),
        credential_id=getattr(service.actor, "_credential_id", None),
    )
    row = Job(
        scope_id=scope_id,
        actor_id=service.actor.id,
        kind="creation",
        payload=payload,
        progress={"stage": "prepare", "revisions": 0, "tokens": 0},
    )
    service.db.add(row)
    await service.db.flush()
    return service.job_json(row)


async def accept_task(service, scope_id, job_id, key, automatic=False):
    row = await service.job(scope_id, job_id, "adopt", lock=True)
    require(row.kind == "creation", "job_kind", "不是创作任务")
    require(row.payload.get("mode") != "assess", "assessment_only", "单独评分任务不产生待采用文本")
    if row.state == "applied":
        return row.result["receipt"]
    require(row.state in {"waiting", "qualified"}, "job_state", "任务尚未达到可选择状态", 409)
    candidates = row.result.get("candidates", [])
    index = row.result.get("selected", len(candidates) - 1)
    require(candidates and 0 <= index < len(candidates), "candidate", "没有可采用候选")
    candidate = candidates[index]
    require(
        candidate.get("second_evaluation", {}).get("verdict") not in {"blocked", "incomplete"},
        "hard_gate",
        "附加评价存在严重问题或缺证据，不能采用",
        409,
    )
    assessment = await service.db.get(Assessment, candidate["assessment_id"])
    scope, actions = await authorize(service.db, service.actor, scope_id, "adopt")
    require(
        scope.version == row.payload["base_version"],
        "version_conflict",
        "作者或其他任务已修改资料，需重新比较/复评",
        409,
    )
    require(
        assessment
        and assessment.policy_hash == POLICY_HASH
        and assessment.verdict not in {"blocked", "incomplete"}
        and not candidate.get("disputed")
        and candidate.get("revision_evaluation", {}).get("verdict") not in {"blocked", "incomplete"},
        "hard_gate",
        "硬伤未通过或评分不完整，不能采用",
        409,
    )
    require(
        assessment.content_hash == digest(candidate["text"]), "stale_assessment", "候选与评分版本不一致", 409
    )
    require(
        not row.payload.get("requires_secret") or "secret" in actions, "forbidden", "秘密内容权限已变化", 403
    )
    if row.payload["scheme"] == "P1":
        require(row.result.get("plan_valid"), "story_gate", "场景计划尚未通过故事审", 409)
    auto_decision = None
    if automatic:
        require(assessment.verdict == "qualified", "quality", "未达自动采用质量线")
        delegation, mode = await checked_delegation(
            service,
            scope,
            row.payload.get("delegation_id"),
            row.payload.get("entity_id"),
            {assessment.scheme, row.payload["scheme"]},
        )
        extra_reports = []
        if candidate.get("second_evaluation"):
            # Secondary identity is recorded on its immutable assessment, not inferred from UI configuration.
            second = await service.db.get(Assessment, candidate.get("second_assessment_id"))
            require(
                second is not None and second.verdict == "qualified",
                "quality",
                "第二评价尚未达到自动采用质量线",
                409,
            )
            extra_reports.append((second.scheme, second.evaluator))
        if candidate.get("revision_assessment_id"):
            revision_report = await service.db.get(Assessment, candidate["revision_assessment_id"])
            require(
                revision_report and revision_report.verdict == "qualified",
                "calibration",
                "修订执行质量尚未达标",
                409,
            )
            extra_reports.append((revision_report.scheme, revision_report.evaluator))
        if mode == "calibrated":
            for checked_scheme, evaluator in [(assessment.scheme, assessment.evaluator), *extra_reports]:
                trusted = await service.db.scalar(
                    select(Calibration.id).where(
                        Calibration.scope_id == scope_id,
                        Calibration.policy_hash == POLICY_HASH,
                        Calibration.scheme == checked_scheme,
                        Calibration.evaluator == evaluator,
                        Calibration.active.is_(True),
                    )
                )
                require(trusted, "calibration", "当前方案或附加评价器尚未校准，保留作者审核", 409)
        target = await service.entity(scope_id, row.payload["entity_id"])
        require(
            not target.get("data", {}).get("key_chapter") and target.get("data", {}).get("position", 99) > 3,
            "key_chapter",
            "关键章保留作者版本选择",
            409,
        )
        delegation.remaining -= 1
        auto_decision = {
            "delegation_id": delegation.id,
            "mode": mode,
            "calibration": "verified" if mode == "calibrated" else "unverified",
            "policy_hash": POLICY_HASH,
            "note": delegation.authorization.get("note", ""),
        }
    operations = []
    entity_id = row.payload.get("entity_id") or row.result.setdefault("new_entity_id", uid())
    if row.payload.get("entity_id"):
        operations.append(
            {
                "op": "update",
                "entity_id": entity_id,
                "expected": row.payload["expected"],
                "text": candidate["text"],
                "data": candidate.get("data", {}),
            }
        )
    else:
        operations.append(
            {
                "op": "create",
                "entity_id": entity_id,
                "kind": row.payload["kind"],
                "name": row.payload["name"],
                "text": candidate["text"],
                "data": candidate.get("data", {}),
            }
        )
    allowed = set(row.result.get("packet", {}).get("entity_ids", [])) | {entity_id}
    pending = []
    for claim in candidate.get("claims", [])[:100]:
        quote = claim.get("quote", "")
        if not quote or quote not in candidate["text"] or claim.get("object_id") not in allowed | {None}:
            pending.append({"claim": claim, "reason": "证据不足或身份尚未解析"})
            continue
        category = claim.get("category", "fact")
        if row.payload["scheme"] == "P2":
            category = "plan"
        if category not in {"fact", "relation", "belief", "plan", "reveal"}:
            pending.append({"claim": claim, "reason": "类别需要确认"})
            continue
        operations.append(
            {
                "op": "fact",
                "entity_id": entity_id,
                "fact": {
                    "predicate": claim.get("predicate", "mentioned"),
                    "category": category,
                    "value": claim.get("value", {}),
                    "object_id": claim.get("object_id"),
                    "chapter_id": entity_id if row.payload["kind"] in {"chapter", "章节"} else None,
                    "source": {"kind": "text", "entity_id": entity_id, "revision": "$change", "quote": quote},
                },
            }
        )
    change = await service.create_change(
        scope_id,
        ChangeInput(
            title="采用创作成果：" + row.payload["name"], base_version=scope.version, operations=operations
        ),
    )
    result = await service.adopt(scope_id, change["id"], key)
    adopted_assessment = Assessment(
        scope_id=scope_id,
        actor_id=service.actor.id,
        entity_id=entity_id,
        content_hash=assessment.content_hash,
        dependency_version=result["version"],
        scheme=assessment.scheme,
        policy_hash=assessment.policy_hash,
        evaluator=assessment.evaluator,
        report={**assessment.report, "applied_from": assessment.id},
        score=assessment.score,
        verdict=assessment.verdict,
    )
    service.db.add(adopted_assessment)
    row.state = "applied"
    row.result = {
        **row.result,
        "new_entity_id": entity_id,
        "receipt": result,
        "pending_claims": pending,
        "author_quality_override": assessment.verdict != "qualified",
        "automatic_adoption": auto_decision,
    }
    if auto_decision:
        service.db.add(
            Audit(
                scope_id=scope_id,
                actor_id=service.actor.id,
                action="creation.auto_adopt",
                version=result["version"],
                detail={"job_id": row.id, **auto_decision},
            )
        )
    return result


class Worker:
    def __init__(self, factory, settings, provider=None):
        self.factory, self.settings = factory, settings
        self.provider = provider or ChatProvider(settings)

    async def claim(self):
        async with self.factory() as db, db.begin():
            now = utcnow()
            row = await db.scalar(
                select(Job)
                .where(
                    Job.cancel_requested.is_(False),
                    Job.attempts < 3,
                    or_(Job.state == "queued", and_(Job.state == "running", Job.lease_until < now)),
                )
                .order_by(Job.created_at)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
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
            from .models import Session

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

    async def run_once(self):
        claimed = await self.claim()
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
                elif kind == "export":
                    data, media_type, ext = await service.export_bytes(
                        row.scope_id, row.payload["version"], row.payload["format"]
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
        return True

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
        row.lease_token, row.lease_until = None, None
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
        # Only previous chapters enter the default writing packet; never send the whole database.
        position = target["data"].get("position") if target else None
        chapters = (
            await service.entities(
                row.scope_id, Query(kind="chapter", limit=1, sort="position", descending=True)
            )
        )["items"]
        next_position = position or max([x["data"].get("position", 0) for x in chapters] + [0]) + 1
        previous = (
            await service.entities(
                row.scope_id,
                Query(
                    kind="chapter",
                    limit=3,
                    sort="position",
                    descending=True,
                    filters=[{"field": "position", "op": "lte", "value": next_position - 1}],
                ),
            )
        )["items"][::-1]
        for obj in previous:
            full = await service.entity(row.scope_id, obj["id"])
            sources.append(
                {
                    "id": obj["id"],
                    "revision": full["revision"],
                    "name": full["name"],
                    "text": full["text"][-8000:],
                }
            )
            ids.append(obj["id"])
        definition = await service.definition(scope, payload["kind"])
        return {
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
                if "packet" not in result:
                    result["packet"] = await self.packet(service, row)
                stage = progress.get("stage", "prepare")
                packet = copy.deepcopy(result["packet"])
                sources = [s["text"] for s in packet["sources"]]
                scheme = row.payload["scheme"]
                budget = row.payload["token_budget"] - progress.get("tokens", 0)
                if stage == "prepare":
                    if row.payload.get("mode") == "assess":
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
                        packet["current"] = result["candidates"][-1]["text"]
                        packet["revision_notes"] = (
                            result["candidates"][-1]["evaluation"].get("report", {}).get("suggestions", [])
                        )
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
                            before=result["packet"]["current"],
                            requested_scope=row.payload.get("selection_start"),
                            prior_issues=result.get("candidates", [{}])[-1].get("evaluation"),
                        )
                row.result = result
                row.progress = {**progress, "stage": stage}
            # No database session/lock is kept across model I/O.
            require(budget >= 256, "token_budget", "任务预算不足，已有用量和成果保留，请明确新任务预算", 409)
            response, usage = await self.provider.call(purpose, packet, budget)
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
                        result["draft"] = response
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
                        evaluator=("chat:" + self.settings.second_judge_model)
                        if stage == "judge_second"
                        else self.provider.identity,
                        report={**evaluation, "requires_secret": row.payload.get("requires_secret", False)},
                        score=Decimal(evaluation["score"]) if evaluation.get("score") is not None else None,
                        verdict=evaluation["verdict"],
                    )
                    db.add(assessment)
                    await db.flush()
                    qualified = evaluation["verdict"] == "qualified"
                    if stage == "judge_plan":
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
                        elif row.payload.get("scheme") == "P5" or progress.get("revisions", 0):
                            progress["stage"] = "judge_revision"
                        else:
                            self.route_candidate(row, progress, result)
                    elif stage == "judge_revision":
                        candidate = result["candidates"][-1]
                        candidate["revision_evaluation"] = evaluation
                        candidate["revision_assessment_id"] = assessment.id
                        if evaluation["verdict"] != "qualified":
                            candidate["revision_hold"] = True
                            row.state = "waiting"
                        else:
                            self.route_candidate(row, progress, result)
                    else:
                        candidate = {
                            **result["draft"],
                            "assessment_id": assessment.id,
                            "evaluation": evaluation,
                            "hash": digest(content),
                            "scheme": scheme,
                        }
                        result.setdefault("candidates", []).append(candidate)
                        result["selected"] = len(result["candidates"]) - 1
                        if row.payload.get("mode") == "assess":
                            row.state = "succeeded"
                        elif self.settings.second_judge_model:
                            progress["stage"] = "judge_second"
                        elif qualified and (row.payload["scheme"] == "P5" or progress.get("revisions", 0)):
                            progress["stage"] = "judge_revision"
                        else:
                            self.route_candidate(row, progress, result)
                row.progress, row.result = progress, result
                if row.state != "running":
                    if row.state == "qualified" and row.payload.get("delegation_id"):
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
                    return

    def route_candidate(self, row, progress, result):
        candidate = result["candidates"][-1]
        if candidate["evaluation"]["verdict"] == "qualified" and not candidate.get("revision_hold"):
            row.state = "qualified"
        elif progress.get("revisions", 0) < row.payload["max_revisions"]:
            progress["revisions"] = progress.get("revisions", 0) + 1
            progress["stage"] = "revise"
        else:
            row.state = "waiting"

    async def run(self, once=False):
        while True:
            worked = await self.run_once()
            if once:
                return worked
            if not worked:
                await asyncio.sleep(1)
