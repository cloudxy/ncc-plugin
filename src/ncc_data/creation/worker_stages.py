"""Creation task submission, explicit stage transitions, candidate assembly, and acceptance."""

from sqlalchemy import select

from ncc_data.application.security import authorize
from ncc_data.creation.model_route import ensure_job_route, purpose_slot
from ncc_data.domain.contracts import ChangeInput, CreationInput
from ncc_data.domain.creation import creation_scheme
from ncc_data.domain.studio_catalog import ordered_book_chapters, producer_guidance
from ncc_data.persistence.models import (
    Assessment,
    Audit,
    Calibration,
    Delegation,
    Job,
    Revision,
    uid,
    utcnow,
)
from ncc_shared.errors import require
from ncc_shared.quality.policy import POLICY_HASH
from ncc_shared.serialization import digest


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


def validate_stage_order(stages, *, has_outline, has_current):
    """Reject an explicit pipeline that cannot be executed in the given order."""
    require(isinstance(stages, list) and stages, "stages", "创作工序不能为空")
    require(len(stages) == len(set(stages)), "stages", "创作工序不能重复")
    allowed = {"plan", "judge_plan", "write", "judge", "revise"}
    require(set(stages) <= allowed, "stages", "存在未知创作工序")
    index = {name: pos for pos, name in enumerate(stages)}
    if "plan" in index and "judge_plan" in index:
        require(index["plan"] < index["judge_plan"], "stages", "结构审校必须排在细纲推演之后")
    if "plan" in index and "write" in index:
        require(index["plan"] < index["write"], "stages", "正文起草必须排在细纲推演之后")
    if "plan" in index and "revise" in index:
        require(index["plan"] < index["revise"], "stages", "定向返修必须排在细纲推演之后")
    if "judge_plan" in index and "write" in index:
        require(index["judge_plan"] < index["write"], "stages", "正文起草必须排在结构审校之后")
    if "judge_plan" in index and "revise" in index:
        require(index["judge_plan"] < index["revise"], "stages", "定向返修必须排在结构审校之后")
    if "write" in index and "judge" in index:
        require(index["write"] < index["judge"], "stages", "品质审评必须排在正文起草之后")
    if "write" in index and "revise" in index:
        require(index["write"] < index["revise"], "stages", "定向返修必须排在正文起草之后")
        require("judge" in index, "stages", "起草后自动返修需要先勾选质量审评，以依据审评意见返修")
    if "judge" in index and "revise" in index:
        if "write" in index:
            require(index["judge"] < index["revise"], "stages", "自动返修必须排在品质审评之后")
        else:
            require(index["revise"] < index["judge"], "stages", "复评必须排在定向返修之后")
    if "judge" in index and stages != ["judge"]:
        require("write" in stages or "revise" in stages, "stages", "品质审评需要排在起草或返修之后")
    if "judge_plan" in index and "plan" not in index:
        require(has_outline or has_current, "stages", "结构审校需要已有细纲或当前文本")
    if stages == ["judge"]:
        require(has_current, "assessment_target", "单独评分需要已有内容对象")
    if "revise" in index and "write" not in index:
        require(has_current, "revision_target", "不经过正文起草的定向返修需要已有正文对象")


def explicit_transition(stages, stage, *, qualified, revisions, max_revisions):
    """Next step for an explicit pipeline. Default jobs never call this."""
    position = stages.index(stage)
    nxt = stages[position + 1] if position + 1 < len(stages) else None
    if stage == "plan":
        if nxt == "judge_plan":
            return {"next_stage": "judge_plan"}
        if "write" in stages:
            return {"next_stage": "write"}
        if "revise" in stages:
            return {"next_stage": "revise", "prepare_revise_from_plan": True}
        return {"terminal": "waiting", "attach_plan": True}
    if stage == "judge_plan":
        if not qualified and "plan" in stages and revisions < max_revisions:
            return {"next_stage": "plan", "retry_plan": True}
        if "write" in stages:
            if qualified:
                return {"next_stage": "write"}
            return {"terminal": "waiting", "attach_plan": True}
        if "revise" in stages:
            if qualified:
                return {"next_stage": "revise", "prepare_revise_from_plan": True}
            return {"terminal": "waiting", "attach_plan": True}
        return {"terminal": "qualified" if qualified else "waiting", "attach_plan": True}
    if stage in {"write", "revise"}:
        if nxt == "judge" or (stage == "revise" and "judge" in stages):
            return {"next_stage": "judge"}
        if nxt == "revise":
            return {"next_stage": "revise", "attach_draft": True}
        return {"terminal": "waiting", "attach_draft": True}
    if stage == "judge":
        if stages == ["judge"]:
            return {"terminal": "succeeded", "attach_judged": True}
        later = stages[position + 1 :]
        if not qualified and "revise" in later and revisions < max_revisions:
            return {"next_stage": "revise", "attach_judged": True, "count_revision": True}
        return {"terminal": "qualified" if qualified else "waiting", "attach_judged": True}
    return {"terminal": "waiting"}


def begin_explicit_stage(payload, result, packet):
    """Enter the first requested stage. Plan-only and write-only do not invent the other half."""
    first = payload["stages"][0]
    outline = (payload.get("beat_outline") or "").strip() or str(
        (packet.get("current_data") or {}).get("beat_outline") or ""
    )
    if first == "write":
        if outline:
            packet["scene_plan"] = outline
            result["packet"] = {**result["packet"], "scene_plan": outline}
        return "write"
    if first == "judge":
        result["draft"] = {"text": packet.get("current") or "", "data": {}, "claims": []}
        return "judge"
    if first == "judge_plan":
        result["plan"] = {"text": outline or packet.get("current") or "", "data": {}, "claims": []}
        return "judge_plan"
    if first == "revise":
        notes = [item for item in (payload.get("guidance"), payload.get("objective")) if item]
        packet["revision_notes"] = notes
        result["packet"] = {**result["packet"], "revision_notes": notes}
        return "revise"
    return "plan"


def _append_plan_candidate(result, assessment_id=None):
    plan = result.get("plan") or {}
    text = plan.get("text") or ""
    candidate = {
        "text": text,
        "data": plan.get("data") or {},
        "claims": plan.get("claims") or [],
        "artifact": "plan",
        "hash": digest(text),
    }
    if result.get("plan_evaluation"):
        candidate["evaluation"] = result["plan_evaluation"]
        pinned = assessment_id or result.get("plan_assessment_id")
        if pinned:
            candidate["assessment_id"] = pinned
    result.setdefault("candidates", []).append(candidate)
    result["selected"] = len(result["candidates"]) - 1


def _append_draft_candidate(result):
    draft = result.get("draft") or {}
    text = draft.get("text") or ""
    result.setdefault("candidates", []).append({**draft, "artifact": "draft", "hash": digest(text)})
    result["selected"] = len(result["candidates"]) - 1


def _append_judged_candidate(result, assessment_id, evaluation, scheme, content):
    result.setdefault("candidates", []).append(
        {
            **result.get("draft", {}),
            "assessment_id": assessment_id,
            "evaluation": evaluation,
            "hash": digest(content),
            "scheme": scheme,
        }
    )
    result["selected"] = len(result["candidates"]) - 1


def _apply_explicit(row, progress, result, decision, *, assessment_id=None, evaluation=None, scheme=None, content=""):
    if decision.get("retry_plan"):
        progress["revisions"] = progress.get("revisions", 0) + 1
        progress["stage"] = "plan"
        feedback = (result.get("plan_evaluation") or {}).get("report", {}).get("suggestions", [])
        result["packet"] = {**result["packet"], "plan_feedback": feedback}
        return
    if decision.get("prepare_revise_from_plan"):
        notes = [item for item in (row.payload.get("guidance"), row.payload.get("objective")) if item]
        plan_text = (result.get("plan") or {}).get("text") or ""
        result["packet"] = {
            **result["packet"],
            "scene_plan": plan_text,
            "revision_notes": result["packet"].get("revision_notes") or notes,
        }
    if decision.get("attach_plan"):
        _append_plan_candidate(result, assessment_id)
    elif decision.get("attach_draft"):
        _append_draft_candidate(result)
    elif decision.get("attach_judged") and assessment_id is not None:
        _append_judged_candidate(result, assessment_id, evaluation, scheme, content)
    if decision.get("count_revision"):
        progress["revisions"] = progress.get("revisions", 0) + 1
    if decision.get("next_stage"):
        progress["stage"] = decision["next_stage"]
        return
    row.state = decision.get("terminal") or "waiting"


async def _scope_volumes_and_chapters(service, scope):
    stmt = (await service.revision_query(scope)).where(
        Revision.body["deleted"].as_boolean().is_(False),
        Revision.body["kind"].astext.in_(["volume", "卷", "chapter", "章节"]),
    )
    rows = (await service.db.scalars(stmt.order_by(Revision.entity_id))).all()
    volumes, chapters = [], []
    for r in rows:
        body = r.body or {}
        entry = {
            "id": r.entity_id,
            "revision": r.id,
            "version": f"{r.scope_id}:{r.version}",
            "kind": body.get("kind") or "",
            "name": body.get("name") or "",
            "text": body.get("text") or "",
            "data": body.get("data") or {},
            "secret": bool(body.get("secret")),
        }
        if entry["kind"] in {"volume", "卷"}:
            volumes.append(entry)
        else:
            chapters.append(entry)
    return volumes, ordered_book_chapters(volumes, chapters)


def _needs_revision_judge(row, progress):
    stages = row.payload.get("stages") or []
    if row.payload.get("mode") == "assess" or stages == ["judge"]:
        return False
    return bool(
        row.payload.get("scheme") == "P5"
        or progress.get("revised_prose")
        or progress.get("revisions", 0) > 0
    )


def _studio_inputs(payload):
    return bool(
        payload.get("stages")
        or payload.get("commons_refs")
        or payload.get("builtin_commons_ids")
        or payload.get("market_playbook_id")
        or (payload.get("guidance") or "").strip()
        or (payload.get("beat_outline") or "").strip()
    )


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
        require(
            not value.stages,
            "delegation_stages",
            "自动定稿托管须执行完整标准审评流程，不能与显式拆分工序同时传入",
        )
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
    if value.stages:
        stored_outline = ""
        if target:
            stored_outline = str((target.get("data") or {}).get("beat_outline") or "")
        has_outline = bool(
            value.beat_outline.strip()
            or stored_outline.strip()
            or (target and str(target.get("text") or "").strip())
        )
        validate_stage_order(value.stages, has_outline=has_outline, has_current=target is not None)
    if value.stages or value.builtin_commons_ids or value.market_playbook_id:
        producer_guidance(payload, scope.config)
    requires_secret = "secret" in actions
    for source in value.source_ids:
        source_entity = await service.entity(scope_id, source)
        requires_secret |= bool(source_entity.get("secret"))
    for ref in value.commons_refs:
        # Read permission, including secret, is enforced by the same entity gate as this book.
        commons_entity = await service.entity(ref.scope_id, ref.entity_id)
        requires_secret |= bool(commons_entity.get("secret"))
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
    return await service.serialize_job(row)


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
    assessment = (
        await service.db.get(Assessment, candidate["assessment_id"]) if candidate.get("assessment_id") else None
    )
    scope, actions = await authorize(service.db, service.actor, scope_id, "adopt")
    require(
        scope.version == row.payload["base_version"],
        "version_conflict",
        "作者或其他任务已修改资料，需重新比较/复评",
        409,
    )
    stages = row.payload.get("stages") or []
    route_snap = ensure_job_route(row.result.get("model_route"))
    requires_second = bool(
        candidate.get("artifact") != "plan"
        and purpose_slot(route_snap, "judge_secondary").get("model_key")
    )
    requires_revision_p5 = bool(
        candidate.get("artifact") != "plan"
        and (
            row.payload.get("scheme") == "P5"
            or candidate.get("revised_prose")
            or ("revise" in stages and "judge" in stages and "write" not in stages)
        )
    )
    if assessment is None:
        # An explicit plan or unjudged draft can be accepted manually by the author, never when judge was requested or auto-adopting.
        require(
            not automatic
            and (
                candidate.get("artifact") == "plan"
                or (bool(stages) and "judge" not in stages)
            ),
            "hard_gate",
            "硬伤未通过或评分不完整，不能采用",
            409,
        )
    else:
        require(
            assessment.policy_hash == POLICY_HASH
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
        if candidate.get("artifact") != "plan":
            if requires_second:
                second_row = (
                    await service.db.get(Assessment, candidate["second_assessment_id"])
                    if candidate.get("second_assessment_id")
                    else None
                )
                require(
                    second_row is not None
                    and second_row.policy_hash == POLICY_HASH
                    and second_row.content_hash == digest(candidate["text"])
                    and second_row.verdict not in {"blocked", "incomplete"}
                    and not candidate.get("disputed"),
                    "hard_gate",
                    "缺少必需的第二评价或存在评价分歧，不能采用",
                    409,
                )
            if requires_revision_p5:
                rev_row = (
                    await service.db.get(Assessment, candidate["revision_assessment_id"])
                    if candidate.get("revision_assessment_id")
                    else None
                )
                require(
                    rev_row is not None
                    and rev_row.scheme == "P5"
                    and rev_row.policy_hash == POLICY_HASH
                    and rev_row.content_hash == digest(candidate["text"])
                    and rev_row.verdict not in {"blocked", "incomplete"},
                    "hard_gate",
                    "缺少必需的 P5 修订质量评价或存在硬伤，不能采用",
                    409,
                )
    require(
        not row.payload.get("requires_secret") or "secret" in actions, "forbidden", "秘密内容权限已变化", 403
    )
    if row.payload["scheme"] == "P1" and not stages:
        require(row.result.get("plan_valid"), "story_gate", "场景计划尚未通过故事审", 409)
    elif row.payload["scheme"] == "P1" and "judge_plan" in stages and assessment is not None:
        require(row.result.get("plan_valid"), "story_gate", "场景计划尚未通过故事审", 409)
    auto_decision = None
    if automatic:
        require(
            not stages and candidate.get("artifact") != "plan",
            "delegation_stages",
            "显式拆分工序或纯细纲候选不能自动采用",
            409,
        )
        require(assessment is not None and assessment.verdict == "qualified", "quality", "未达自动采用质量线")
        delegation, mode = await checked_delegation(
            service,
            scope,
            row.payload.get("delegation_id"),
            row.payload.get("entity_id"),
            {assessment.scheme, row.payload["scheme"]},
        )
        extra_reports = []
        if requires_second or candidate.get("second_evaluation") or candidate.get("second_assessment_id"):
            # Secondary identity is recorded on its immutable assessment, not inferred from UI configuration.
            second = (
                await service.db.get(Assessment, candidate.get("second_assessment_id"))
                if candidate.get("second_assessment_id")
                else None
            )
            require(
                second is not None
                and second.policy_hash == POLICY_HASH
                and second.content_hash == digest(candidate["text"])
                and second.verdict == "qualified"
                and not candidate.get("disputed"),
                "quality",
                "第二评价尚未达到自动采用质量线",
                409,
            )
            extra_reports.append((second.scheme, second.evaluator))
        if requires_revision_p5 or candidate.get("revision_assessment_id"):
            revision_report = (
                await service.db.get(Assessment, candidate["revision_assessment_id"])
                if candidate.get("revision_assessment_id")
                else None
            )
            require(
                revision_report is not None
                and revision_report.scheme == "P5"
                and revision_report.policy_hash == POLICY_HASH
                and revision_report.content_hash == digest(candidate["text"])
                and revision_report.verdict == "qualified",
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
        chapter_book_order = 99
        if target.get("kind") in {"chapter", "章节"}:
            _, ordered_chapters = await _scope_volumes_and_chapters(service, scope)
            matched = next((c for c in ordered_chapters if c["id"] == target["id"]), None)
            chapter_book_order = matched["book_order"] if matched else 99
        require(
            not target.get("data", {}).get("key_chapter") and chapter_book_order > 3,
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
    target_body = (
        await service.entity(scope_id, row.payload["entity_id"]) if row.payload.get("entity_id") else None
    )
    effective_kind = (target_body or {}).get("kind") or row.payload.get("kind")
    plan_into_chapter = candidate.get("artifact") == "plan" and effective_kind in {"chapter", "章节"}
    plan_into_outline = candidate.get("artifact") == "plan" and effective_kind in {
        "outline",
        "大纲",
        "细纲",
        "主线",
        "支线",
        "剧情",
    }
    if plan_into_chapter:
        if row.payload.get("entity_id"):
            # Keep the chapter prose. The adopted outline lives in beat_outline.
            operations.append(
                {
                    "op": "update",
                    "entity_id": entity_id,
                    "expected": row.payload["expected"],
                    "data": {"beat_outline": candidate["text"]},
                }
            )
        else:
            _, ordered_chapters = await _scope_volumes_and_chapters(service, scope)
            loose_positions = [
                int((c.get("data") or {}).get("position", 0))
                for c in ordered_chapters
                if not (c.get("data") or {}).get("parent_id")
                and isinstance((c.get("data") or {}).get("position", 0), int)
                and not isinstance((c.get("data") or {}).get("position", 0), bool)
            ]
            next_pos = (max(loose_positions) + 1) if loose_positions else 0
            operations.append(
                {
                    "op": "create",
                    "entity_id": entity_id,
                    "kind": row.payload["kind"],
                    "name": row.payload["name"],
                    "text": "",
                    "data": {
                        **candidate.get("data", {}),
                        "status": (candidate.get("data") or {}).get("status") or "draft",
                        "position": next_pos,
                        "beat_outline": candidate["text"],
                    },
                }
            )
    elif row.payload.get("entity_id"):
        extra_data = dict(candidate.get("data", {}))
        if plan_into_outline:
            extra_data.setdefault("beat_outline", candidate["text"])
        operations.append(
            {
                "op": "update",
                "entity_id": entity_id,
                "expected": row.payload["expected"],
                "text": candidate["text"],
                "data": extra_data,
            }
        )
    else:
        extra_data = dict(candidate.get("data", {}))
        if plan_into_outline:
            extra_data.setdefault("beat_outline", candidate["text"])
        operations.append(
            {
                "op": "create",
                "entity_id": entity_id,
                "kind": row.payload["kind"],
                "name": row.payload["name"],
                "text": candidate["text"],
                "data": extra_data,
            }
        )
    allowed = set(row.result.get("packet", {}).get("entity_ids", [])) | {entity_id}
    pending = []
    claim_rows = [] if plan_into_chapter else candidate.get("claims", [])[:100]
    for claim in claim_rows:
        quote = claim.get("quote", "")
        if not quote or quote not in candidate["text"] or claim.get("object_id") not in allowed | {None}:
            pending.append({"claim": claim, "reason": "证据不足或身份尚未解析"})
            continue
        category = claim.get("category", "fact")
        if row.payload["scheme"] == "P2" or candidate.get("artifact") == "plan":
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
    result = await service.adopt(
        scope_id,
        change["id"],
        key,
        receipt_extra={"entity_id": entity_id},
    )
    if assessment is not None:
        service.db.add(
            Assessment(
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
        )
    row.state = "applied"
    row.updated_at = utcnow()
    row.result = {
        **row.result,
        "new_entity_id": entity_id,
        "receipt": result,
        "pending_claims": pending,
        "author_plan_adopted": candidate.get("artifact") == "plan" and assessment is None,
        "author_quality_override": False if assessment is None else assessment.verdict != "qualified",
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
