"""Studio catalog, chapter overview, reorder and market guidance. No new tables."""

import re

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select

from ncc_data.application.security import authorize
from ncc_data.application.service import Service
from ncc_data.domain.contracts import (
    ChangeInput,
    Query,
    StudioMarketConfigInput,
    StudioReorderInput,
)
from ncc_data.domain.studio_catalog import (
    CODEX_GROUPS,
    catalog_payload,
    count_han_chars,
    foreshadow_lifecycle,
    market_playbook,
    ordered_book_chapters,
)
from ncc_data.persistence.models import Audit, Definition, Receipt, Revision
from ncc_shared.errors import DomainError, require
from ncc_shared.serialization import digest, jsonable

CHAPTER_KINDS = {"chapter", "章节"}
VOLUME_KINDS = {"volume", "卷"}
OUTLINE_KINDS = {"outline", "大纲", "细纲", "scene", "场景", "主线", "支线", "剧情"}
FORESHADOW_KINDS = {"foreshadow", "伏笔", "暗线", "悬念"}
STRUCTURAL_KINDS = CHAPTER_KINDS | VOLUME_KINDS | OUTLINE_KINDS | FORESHADOW_KINDS
_WHITESPACE = re.compile(r"\s+")
DEFAULT_OVERVIEW_LIMIT = 5000


def build_router(service):
    router = APIRouter()

    @router.get("/api/v1/studio/catalog")
    async def catalog(svc: Service = Depends(service, scope="function")):
        return catalog_payload()

    @router.get("/api/v1/scopes/{sid}/studio/overview")
    async def overview(
        sid: str,
        role: str = "author",
        chapter_id: str | None = None,
        offset: int = 0,
        limit: int = DEFAULT_OVERVIEW_LIMIT,
        svc: Service = Depends(service, scope="function"),
    ):
        require(0 <= offset <= 100_000 and 1 <= limit <= 10_000, "pagination", "分页参数超出允许范围")
        require(role in {"author", "writer", "reader"}, "role", "未知阅读视角")
        scope, actions = await authorize(svc.db, svc.actor, sid, "read")
        return await _overview(svc, scope, actions, role=role, chapter_id=chapter_id, offset=offset, limit=limit)

    @router.post("/api/v1/scopes/{sid}/studio/reorder")
    async def reorder(
        sid: str,
        value: StudioReorderInput,
        request: Request,
        svc: Service = Depends(service, scope="function"),
    ):
        await authorize(svc.db, svc.actor, sid, "edit", lock=True)
        await authorize(svc.db, svc.actor, sid, "adopt")
        payload_json = value.model_dump(mode="json")
        payload_digest = digest(payload_json)
        header_key = (request.headers.get("idempotency-key") or "").strip()
        key = header_key[:128] if header_key else ("studio-reorder:" + payload_digest[:64])
        existing_receipt = await svc.db.scalar(
            select(Receipt).where(
                Receipt.scope_id == sid,
                Receipt.actor_id == svc.actor.id,
                Receipt.key == key,
            )
        )
        if existing_receipt is not None:
            if header_key:
                expected_payload_hash = (existing_receipt.result or {}).get("reorder_digest")
                require(
                    expected_payload_hash == payload_digest,
                    "idempotency_reuse",
                    "同一幂等键不能用于不同内容",
                    409,
                )
            return existing_receipt.result
        operations = []
        for item in value.items:
            current = await svc.entity(sid, item.entity_id)
            data = {"position": item.position}
            unset = []
            if item.include_parent:
                if item.parent_id:
                    data["parent_id"] = item.parent_id
                else:
                    unset.append("parent_id")
            operation = {
                "op": "update",
                "entity_id": item.entity_id,
                "expected": current["version"],
                "data": data,
            }
            if unset:
                operation["unset"] = unset
            operations.append(operation)
        change = await svc.create_change(
            sid,
            ChangeInput(title="调整卷章顺序", base_version=value.base_version, operations=operations),
        )
        return await svc.adopt(
            sid,
            change["id"],
            key,
            receipt_extra={"reorder_digest": payload_digest} if header_key else None,
        )

    @router.put("/api/v1/scopes/{sid}/studio/market-config")
    async def market_config(
        sid: str, value: StudioMarketConfigInput, svc: Service = Depends(service, scope="function")
    ):
        scope, actions = await authorize(svc.db, svc.actor, sid, "edit", lock=True)
        if value.playbook_id:
            require(market_playbook(value.playbook_id) is not None, "market_playbook", "未知的赛道母本")
        saved = value.model_dump(mode="json")
        config = dict(scope.config or {})
        config["studio_market"] = saved
        scope.config = config
        svc.db.add(
            Audit(
                scope_id=scope.id,
                actor_id=svc.actor.id,
                action="studio.market_config",
                version=scope.version,
                detail={"playbook_id": saved["playbook_id"], "custom_track": saved["custom_track"]},
            )
        )
        await svc.db.flush()
        view = await _overview(svc, scope, actions)
        return {"market_config": saved, "diagnostics": view["diagnostics"]}

    return router


def _position(data):
    value = (data or {}).get("position", 0)
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return value


def _chars(text):
    return count_han_chars(text)


def _non_ws_chars(text):
    return len(_WHITESPACE.sub("", text or ""))


async def _overview(svc, scope, actions, *, role="author", chapter_id=None, offset=0, limit=DEFAULT_OVERVIEW_LIMIT):
    query = Query(role=role, chapter_id=chapter_id)
    if role != "author":
        require(chapter_id is not None, "view_context", "受限查询必须指定叙述截止章节")
        await svc.raw_entity(scope, chapter_id)

    base = await svc.revision_query(scope)
    visible = base.where(Revision.body["deleted"].as_boolean().is_(False))
    if "secret" not in actions or role != "author":
        visible = visible.where(Revision.body["secret"].as_boolean().is_(False))

    non_structural = visible.where(Revision.body["kind"].astext.not_in(sorted(STRUCTURAL_KINDS)))
    kind_sub = non_structural.with_only_columns(Revision.body["kind"].astext.label("kind")).subquery("visible_kinds")
    count_rows = (
        await svc.db.execute(select(kind_sub.c.kind, func.count()).group_by(kind_sub.c.kind))
    ).all()
    kind_counts = {str(kind or ""): int(cnt) for kind, cnt in count_rows}

    structural_stmt = visible.where(Revision.body["kind"].astext.in_(sorted(STRUCTURAL_KINDS))).order_by(
        Revision.entity_id
    )
    all_structural_rows = (await svc.db.scalars(structural_stmt)).all()

    book_orders = None
    if role != "author":
        raw_vols, raw_chs = [], []
        for r in all_structural_rows:
            b = r.body or {}
            entry = {"id": r.entity_id, "data": b.get("data") or {}}
            if b.get("kind") in VOLUME_KINDS:
                raw_vols.append(entry)
            elif b.get("kind") in CHAPTER_KINDS:
                raw_chs.append(entry)
        book_orders = {c["id"]: c["book_order"] for c in ordered_book_chapters(raw_vols, raw_chs)}

    def_ids = {
        (r.body or {}).get("definition_id")
        for r in all_structural_rows
        if isinstance(r.body, dict) and (r.body or {}).get("definition_id")
    }
    defs_by_id = {}
    if def_ids:
        loaded_defs = (await svc.db.scalars(select(Definition).where(Definition.id.in_(def_ids)))).all()
        defs_by_id = {d.id: d for d in loaded_defs}

    all_items = []
    for row in all_structural_rows:
        raw_obj = {
            **(row.body or {}),
            "id": row.entity_id,
            "revision": row.id,
            "version": f"{row.scope_id}:{row.version}",
            "content_hash": row.content_hash,
        }
        try:
            projected = await svc.redact_with_definitions(
                scope, actions, raw_obj, query, defs_by_id, book_orders=book_orders
            )
        except DomainError:
            continue
        kind_str = str(projected.get("kind") or "")
        kind_counts[kind_str] = kind_counts.get(kind_str, 0) + 1
        all_items.append(
            {
                "id": projected["id"],
                "version": projected["version"],
                "kind": kind_str,
                "name": projected.get("name") or "",
                "text": projected.get("text") or "",
                "data": projected.get("data") or {},
            }
        )

    total_structural = len(all_items)
    total_entities = sum(kind_counts.values())
    page_items = all_items[offset : offset + limit]
    page_ids = {item["id"] for item in page_items}
    truncated = offset > 0 or total_structural > offset + limit
    next_offset = offset + limit if offset + limit < total_structural else None

    all_volumes = [_volume(item) for item in all_items if item["kind"] in VOLUME_KINDS]
    all_volumes.sort(key=lambda item: (item["position"], item["id"]))
    raw_all_chapters = [_chapter(item) for item in all_items if item["kind"] in CHAPTER_KINDS]
    all_chapters = ordered_book_chapters(all_volumes, raw_all_chapters)
    written_orders = [item["book_order"] for item in all_chapters if item["char_count"] > 0]
    max_written = max(written_orders) if written_orders else 0
    all_outlines = [_outline(item) for item in all_items if item["kind"] in OUTLINE_KINDS]
    all_outlines.sort(key=lambda item: (item["position"], item["id"]))
    all_foreshadows = []
    for item in all_items:
        if item["kind"] not in FORESHADOW_KINDS:
            continue
        data = item["data"]
        life = foreshadow_lifecycle(data, max_written)
        all_foreshadows.append(
            {
                "id": item["id"],
                "name": item["name"],
                "version": item["version"],
                "kind": item["kind"],
                "position": _position(data),
                "status": data.get("status") or "",
                "line_type": data.get("line_type") or "",
                "planted_chapter": data.get("planted_chapter"),
                "expected_chapter": data.get("expected_chapter"),
                "planted": life["planted"],
                "due_state": life["due_state"],
                "alert_state": life["alert_state"],
            }
        )
    all_foreshadows.sort(key=lambda item: (item["position"], item["id"]))

    volumes = [v for v in all_volumes if v["id"] in page_ids]
    chapters = [c for c in all_chapters if c["id"] in page_ids]
    outlines = [o for o in all_outlines if o["id"] in page_ids]
    foreshadows = [f for f in all_foreshadows if f["id"] in page_ids]

    groups = [
        {
            "id": group["id"],
            "label": group["label"],
            "count": sum(kind_counts.get(kind, 0) for kind in group["kinds"]),
        }
        for group in CODEX_GROUPS
    ]
    hidden_rows = [
        item for item in all_foreshadows if item["kind"] == "暗线" or item["line_type"] == "暗线"
    ]
    active_hidden = sum(1 for item in hidden_rows if item["planted"])
    planned_hidden = sum(
        1 for item in hidden_rows if not item["planted"] and item["alert_state"] not in {"resolved", "dropped"}
    )
    resolved_hidden = sum(1 for item in hidden_rows if item["alert_state"] == "resolved")
    dropped_hidden = sum(1 for item in hidden_rows if item["alert_state"] == "dropped")
    overdue = sum(1 for item in all_foreshadows if item["due_state"] == "overdue")
    due_soon = sum(1 for item in all_foreshadows if item["due_state"] == "due_soon")
    planted_overdue = sum(1 for item in all_foreshadows if item["planted"] and item["due_state"] == "overdue")
    planted_due_soon = sum(1 for item in all_foreshadows if item["planted"] and item["due_state"] == "due_soon")
    unplanted_due = sum(
        1 for item in all_foreshadows if not item["planted"] and item["due_state"] in {"due_soon", "overdue"}
    )
    resolved_count = sum(1 for item in all_foreshadows if item["alert_state"] == "resolved")
    dropped_count = sum(1 for item in all_foreshadows if item["alert_state"] == "dropped")
    total_chars = sum(item["char_count"] for item in all_chapters)
    total_non_ws = sum(item["non_whitespace_chars"] for item in all_chapters)
    chapter_count = len(all_chapters)
    scopes = await svc.scopes()
    return jsonable(
        {
            "volumes": volumes,
            "chapters": chapters,
            "outlines": outlines,
            "foreshadows": foreshadows,
            "codex_counts": {"groups": groups, "kinds": kind_counts},
            "market_config": (scope.config or {}).get("studio_market") or {},
            "pagination": {
                "total_entities": total_entities,
                "structural_count": total_structural,
                "returned_structural": len(page_items),
                "offset": offset,
                "limit": limit,
                "truncated": bool(truncated),
                "next_offset": next_offset,
            },
            "diagnostics": {
                "chapter_count": chapter_count,
                "total_chars": total_chars,
                "avg_chars": round(total_chars / chapter_count) if chapter_count else 0,
                "total_non_whitespace_chars": total_non_ws,
                "char_metric": "han",
                "key_chapter_count": sum(1 for item in all_chapters if item["key_chapter"] is True),
                "active_hidden_lines": active_hidden,
                "planned_hidden_lines": planned_hidden,
                "resolved_hidden_lines": resolved_hidden,
                "dropped_hidden_lines": dropped_hidden,
                "hidden_line_cap_exceeded": active_hidden > 5,
                "overdue_foreshadow_count": overdue,
                "due_soon_foreshadow_count": due_soon,
                "planted_overdue_foreshadow_count": planted_overdue,
                "planted_due_soon_foreshadow_count": planted_due_soon,
                "unplanted_due_foreshadow_count": unplanted_due,
                "resolved_foreshadow_count": resolved_count,
                "dropped_foreshadow_count": dropped_count,
            },
            "commons_scopes": [
                {"id": item["id"], "name": item["name"], "kind": item["kind"], "version": item["version"]}
                for item in scopes
                if item.get("kind") in {"author", "universe", "research"}
            ],
        }
    )


def _volume(item):
    data = item["data"]
    return {
        "id": item["id"],
        "name": item["name"],
        "version": item["version"],
        "position": _position(data),
        "status": data.get("status") or "",
    }


def _chapter(item):
    data = item["data"]
    return {
        "id": item["id"],
        "name": item["name"],
        "version": item["version"],
        "position": _position(data),
        "parent_id": data.get("parent_id"),
        "status": data.get("status") or "",
        "key_chapter": data.get("key_chapter") is True,
        "pov": data.get("pov") or "",
        "plotline": data.get("plotline") or "",
        "hook": data.get("hook") or "",
        "beat_outline": data.get("beat_outline") or "",
        "target_words": data.get("target_words"),
        "char_count": _chars(item["text"]),
        "non_whitespace_chars": _non_ws_chars(item["text"]),
    }


def _outline(item):
    data = item["data"]
    return {
        "id": item["id"],
        "name": item["name"],
        "version": item["version"],
        "kind": item["kind"],
        "position": _position(data),
        "parent_id": data.get("parent_id"),
        "status": data.get("status") or "",
        "plotline": data.get("plotline") or "",
        "beat_outline": data.get("beat_outline") or "",
    }
