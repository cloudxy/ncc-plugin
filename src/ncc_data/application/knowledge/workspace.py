"""Version-bound working copies. Originals and semantic studio projections commit and export together."""

import base64
import json
from pathlib import PurePosixPath
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select

from ncc_data.application.knowledge.workspace_sync import (
    CATEGORIES_DIR,
    CATEGORY_ALIASES,
    CHAPTER_OUTLINE_DIR,
    CHARACTERS_DIR,
    CORE_SETTING_PATH_KINDS,
    EXCLUDED_SETTING_KINDS,
    MASTER_OUTLINE_PATH,
    PROMISES_PATH,
    PROSE_DIR,
    SCENE_DIR,
    SETTINGS_DIR,
    STRUCTURAL_KINDS,
    STYLE_ANCHOR_PATH,
    WORKSPACE_BOUNDARIES,
    _cli_chapter_status_from_studio,
    _cli_status_from_studio,
    _extract_founding_from_files,
    _has_nonempty_founding,
    _infer_setting_kind,
    _is_setting_md_path,
    _next_promise_id,
    _parse_setting_markdown,
    _promise_code_from_note,
    _render_setting_markdown,
    _safe_segment,
    _studio_chapter_status_from_cli,
    _studio_status_from_cli,
    apply_founding_to_state,
    collect_promise_operations,
    collect_setting_operations,
    project_foreshadows_to_promises,
    project_settings_to_files,
    safe_path,
)
from ncc_data.application.security import authorize
from ncc_data.domain.contracts import ChangeInput, Query
from ncc_data.domain.studio_catalog import count_han_chars, ordered_book_chapters
from ncc_data.persistence.models import Receipt
from ncc_shared.errors import DomainError, require
from ncc_shared.serialization import digest

__all__ = [
    "CATEGORIES_DIR",
    "CATEGORY_ALIASES",
    "CHAPTER_OUTLINE_DIR",
    "CHARACTERS_DIR",
    "CORE_SETTING_PATH_KINDS",
    "EXCLUDED_SETTING_KINDS",
    "MASTER_OUTLINE_PATH",
    "PROMISES_PATH",
    "PROSE_DIR",
    "SCENE_DIR",
    "SETTINGS_DIR",
    "STRUCTURAL_KINDS",
    "STYLE_ANCHOR_PATH",
    "WORKSPACE_BOUNDARIES",
    "WorkspaceMixin",
    "_cli_chapter_status_from_studio",
    "_cli_status_from_studio",
    "_extract_founding_from_files",
    "_has_nonempty_founding",
    "_infer_setting_kind",
    "_is_setting_md_path",
    "_next_promise_id",
    "_parse_setting_markdown",
    "_promise_code_from_note",
    "_render_setting_markdown",
    "_safe_segment",
    "_studio_chapter_status_from_cli",
    "_studio_status_from_cli",
    "safe_path",
]


class WorkspaceMixin:
    async def workspace_snapshot(self, scope_id):
        scope, actions = await authorize(self.db, self.actor, scope_id, "export")
        require("secret" in actions, "workspace_permission", "完整CLI工作副本需要秘密内容与导出权限", 403)
        files, offset = {}, 0
        volumes, chapters, outlines, foreshadows, settings_entities = [], [], [], [], []
        while True:
            page = await self.entities(scope_id, Query(limit=200, offset=offset))
            for item in page["items"]:
                full = await self.entity(scope_id, item["id"])
                kind = full["kind"]
                if kind == "legacy-file":
                    path = full["data"]["legacy_path"]
                    if full["data"].get("attachment_id"):
                        attachment = await self.attachment(scope_id, full["data"]["attachment_id"])
                        raw = attachment.data
                    else:
                        raw = full["text"].encode("utf-8")
                    files[path] = raw
                elif kind in {"volume", "卷"}:
                    volumes.append(full)
                elif kind in {"chapter", "章节"}:
                    chapters.append(full)
                elif kind in {"outline", "大纲"}:
                    outlines.append(full)
                elif kind in {"foreshadow", "伏笔", "暗线", "悬念"}:
                    foreshadows.append(full)
                elif kind not in EXCLUDED_SETTING_KINDS:
                    settings_entities.append(full)
            if page["next_offset"] is None:
                break
            offset = page["next_offset"]

        ordered = ordered_book_chapters(volumes, chapters)
        used_paths = set()
        chapter_paths = {}
        for idx, chapter in enumerate(ordered, 1):
            preferred = (chapter.get("data") or {}).get("legacy_path")
            if preferred and preferred not in used_paths:
                chosen = safe_path(preferred)
            else:
                base = f"{PROSE_DIR}/第{idx:04d}章.md"
                chosen = base if base not in used_paths else f"{PROSE_DIR}/第{idx:04d}章-{chapter['id'][:6]}.md"
            used_paths.add(chosen)
            chapter_paths[chapter["id"]] = chosen
            text = chapter.get("text") or ""
            files[chosen] = text.encode("utf-8")

        project_settings_to_files(files, settings_entities, scope.config, actions)

        founding = (scope.config or {}).get("founding") or {}
        has_founding = _has_nonempty_founding(founding)

        if "book.json" in files or ordered or has_founding:
            state = (
                json.loads(files["book.json"].decode("utf-8"))
                if "book.json" in files
                else {
                    "schema_version": 4,
                    "title": scope.name,
                    "mode": "混合",
                    "writing_mode": "serial",
                    "stage": "serial",
                    "soul": {
                        "question": "",
                        "answer": "",
                        "injustice": "",
                        "ending": "",
                        "status": "未填",
                        "deadline": "",
                        "arc": "",
                    },
                    "contract": {"main": "", "extras": [], "poison": [], "signing": {}, "audience": ""},
                    "chapters": [],
                    "units": [],
                    "volumes": [{"n": 1, "start": 1, "end": None, "status": "open"}],
                    "published_upto": 0,
                }
            )
            mapped = scope.config.get("legacy_chapters", {})
            old_by_id = {}
            old_by_path = {}
            for old in state.get("chapters", []):
                sid = old.get("studio_id") or mapped.get(str(old.get("seq")))
                if sid:
                    old_by_id[sid] = old
                if old.get("file"):
                    old_by_path[old["file"]] = old

            synced_chapters = []
            for seq, obj in enumerate(ordered, 1):
                path = chapter_paths[obj["id"]]
                old = dict(old_by_id.get(obj["id"]) or old_by_path.get(path) or {})
                text = obj.get("text") or ""
                text_sha = digest(text.encode("utf-8"))[:16] if text.strip() else ""
                data = obj.get("data") or {}
                studio_status = str(data.get("status") or "")
                ch_status = _cli_chapter_status_from_studio(studio_status, text, old)
                word_cnt = (
                    count_han_chars(text)
                    if text.strip()
                    else int(old.get("words") or old.get("word_count") or 0)
                )
                entry = {
                    "origin": old.get("origin") or "author",
                    **old,
                    "seq": seq,
                    "title": obj["name"],
                    "file": path,
                    "studio_id": obj["id"],
                    "key": (
                        bool(data.get("key_chapter"))
                        if "key_chapter" in data
                        else bool(old.get("key", seq <= 3))
                    ),
                    "status": ch_status,
                    "sha": text_sha,
                    "words": word_cnt,
                    "word_count": word_cnt,
                }
                hook_val = str(data.get("hook") or "").strip()
                if hook_val:
                    prev_hook = dict(old.get("hook") or {})
                    if prev_hook.get("type") and prev_hook.get("line") == hook_val:
                        entry["hook"] = prev_hook
                    elif prev_hook.get("type") == hook_val and not prev_hook.get("line"):
                        entry["hook"] = prev_hook
                    else:
                        entry["hook"] = {
                            "type": prev_hook.get("type") or "悬念",
                            "intensity": int(prev_hook.get("intensity") or 3),
                            "line": hook_val,
                        }
                synced_chapters.append(entry)

                beat = str(data.get("beat_outline") or "").strip()
                scene_rel = f"{SCENE_DIR}/ch-{seq:04d}.md"
                outline_rel = f"{CHAPTER_OUTLINE_DIR}/ch-{seq:04d}.md"
                old_scene_txt = files[scene_rel].decode("utf-8").strip() if scene_rel in files else ""
                if beat:
                    if "## 场景" in beat:
                        files[scene_rel] = (beat + "\n").encode("utf-8")
                    elif beat != old_scene_txt:
                        header = f"# 第 {seq} 章 章纲：{obj['name']}\n\n"
                        body = beat if beat.startswith("#") else (header + beat)
                        files[outline_rel] = (body.rstrip() + "\n").encode("utf-8")

            if ordered or "chapters" in state:
                state["chapters"] = synced_chapters
            if volumes:
                sorted_vols = sorted(
                    volumes, key=lambda v: (int((v.get("data") or {}).get("position", 0)), v["id"])
                )
                vol_entries = []
                for v_idx, vol in enumerate(sorted_vols, 1):
                    v_chs = [
                        idx
                        for idx, ch in enumerate(ordered, 1)
                        if (ch.get("data") or {}).get("parent_id") == vol["id"]
                    ]
                    v_start = (
                        min(v_chs)
                        if v_chs
                        else (
                            vol_entries[-1]["end"] + 1
                            if vol_entries and vol_entries[-1].get("end")
                            else 1
                        )
                    )
                    v_end = max(v_chs) if v_chs and v_idx < len(sorted_vols) else None
                    vol_entries.append(
                        {
                            "n": v_idx,
                            "title": vol["name"],
                            "studio_id": vol["id"],
                            "start": v_start,
                            "end": v_end,
                            "status": "open" if v_idx == len(sorted_vols) else "closed",
                        }
                    )
                state["volumes"] = vol_entries

            if has_founding:
                apply_founding_to_state(state, files, founding)

            files["book.json"] = (json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

        if outlines:
            primary = next(
                (o for o in outlines if (o.get("data") or {}).get("legacy_path") == MASTER_OUTLINE_PATH),
                outlines[0],
            )
            outline_body = str(
                (primary.get("data") or {}).get("beat_outline") or primary.get("text") or ""
            ).strip()
            if outline_body:
                files[MASTER_OUTLINE_PATH] = (outline_body + "\n").encode("utf-8")

        if PROMISES_PATH in files or foreshadows:
            project_foreshadows_to_promises(files, foreshadows, scope.config, len(ordered) or 1)

        return {
            "format": "ncc.workspace/1",
            "version": scope.version,
            "boundaries": WORKSPACE_BOUNDARIES,
            "files": [
                {"path": p, "base64": base64.b64encode(raw).decode(), "sha256": digest(raw)}
                for p, raw in sorted(files.items())
            ],
        }

    async def workspace_commit(self, scope_id, value):
        scope, actions = await authorize(self.db, self.actor, scope_id, "adopt", lock=True)
        require("secret" in actions, "workspace_permission", "CLI接入需要完整范围权限", 403)
        require(value.get("format") == "ncc.workspace/1", "workspace_format", "工作副本格式不受支持")
        key = "workspace:" + value["request_id"]
        request_hash = digest(value)
        receipt = await self.db.scalar(
            select(Receipt).where(
                Receipt.scope_id == scope_id, Receipt.actor_id == self.actor.id, Receipt.key == key
            )
        )
        if receipt:
            require(
                receipt.request_hash == request_hash, "idempotency_reuse", "工作副本幂等键已用于不同内容", 409
            )
            return receipt.result
        require(
            value.get("base_version") == scope.version,
            "version_conflict",
            "数据库已有新变化，工作副本须三方比较",
            409,
        )
        require(
            isinstance(value.get("files"), list) and 0 < len(value["files"]) <= 200,
            "workspace_size",
            "每批1至200个文件",
        )
        current = await self.workspace_snapshot(scope_id)
        old_files = {x["path"]: base64.b64decode(x["base64"]) for x in current["files"]}
        raw_files, operations = dict(old_files), []
        changed_paths: set[str] = set()
        deleted_paths: set[str] = set()

        for item in value["files"]:
            path = safe_path(item.get("path", ""))
            if item.get("deleted"):
                was_present = path in old_files
                raw_files.pop(path, None)
                deleted_paths.add(path)
                if was_present:
                    changed_paths.add(path)
            else:
                try:
                    raw = base64.b64decode(item["base64"], validate=True)
                except (ValueError, KeyError):
                    raise DomainError("workspace_encoding", "文件编码无效") from None
                require(
                    len(raw) <= 16 * 1024 * 1024,
                    "workspace_size",
                    "单个工作副本文件超过16MiB，请通过受管附件导入",
                )
                require(digest(raw) == item.get("sha256"), "workspace_digest", "工作副本内容摘要不符")
                raw_files[path] = raw
                if old_files.get(path) != raw:
                    changed_paths.add(path)

            identity = str(uuid5(NAMESPACE_URL, scope.id + ":file:" + path))
            previous = None
            try:
                previous = await self.entity(scope_id, identity, Query(include_deleted=True))
            except DomainError as exc:
                if exc.status != 404:
                    raise
            if item.get("deleted"):
                if previous and not previous.get("deleted"):
                    operations.append(
                        {"op": "retire", "entity_id": identity, "expected": previous["version"]}
                    )
                continue
            # If the submitted bytes match the current workspace_snapshot, skip redundant legacy-file churn
            if path not in changed_paths and (
                previous is None
                or (
                    not previous.get("deleted")
                    and (previous.get("data") or {}).get("content_hash") == digest(raw)
                )
            ):
                continue
            try:
                content = raw.decode("utf-8")
                binary = len(content) > 2_000_000
            except UnicodeError:
                content, binary = "", True
            data = {
                "legacy_path": path,
                "encoding": "binary" if binary else "utf-8",
                "content_hash": digest(raw),
            }
            if binary:
                saved = await self.upload(scope_id, PurePosixPath(path).name, "application/octet-stream", raw)
                data["attachment_id"] = saved["id"]
                content = ""
            operation = {
                "op": "update" if previous else "create",
                "entity_id": identity,
                "kind": "legacy-file",
                "name": path,
                "data": data,
                "text": content,
            }
            if previous:
                operation["expected"] = previous["version"]
                operation["reactivate"] = bool(previous.get("deleted"))
            operations.append(operation)

        if not changed_paths and not operations:
            return {"version": scope.version, "unchanged": True, "boundaries": WORKSPACE_BOUNDARIES}

        all_existing = await self.all_entities(scope_id, include_deleted=True)
        existing_by_id = {e["id"]: e for e in all_existing}
        existing_chapters_by_path = {
            c["data"]["legacy_path"]: c
            for c in all_existing
            if c["kind"] in {"chapter", "章节"} and c["data"].get("legacy_path")
        }
        existing_settings_by_path = {
            s["data"]["legacy_path"]: s
            for s in all_existing
            if s["kind"] not in EXCLUDED_SETTING_KINDS and (s.get("data") or {}).get("legacy_path")
        }
        defined_keys = {
            d["key"]
            for d in await self.definitions(scope_id)
            if not (d.get("spec") or {}).get("relation")
        }

        legacy = json.loads(raw_files.get("book.json", b"{}"))
        mapping = dict(scope.config.get("legacy_chapters", {}))
        promise_mapping = dict(scope.config.get("legacy_promises", {}))
        setting_mapping = dict(scope.config.get("legacy_settings", {}))
        for p_key, s_row in existing_settings_by_path.items():
            if not s_row.get("deleted") and _is_setting_md_path(p_key):
                setting_mapping.setdefault(p_key, s_row["id"])

        metadata_changed = "book.json" in changed_paths
        active_declared_paths = set()
        active_declared_studio_ids = set()
        for c in legacy.get("chapters", []):
            c_path = (
                safe_path(c["file"])
                if c.get("file")
                else f"{PROSE_DIR}/第{int(c['seq']):04d}章.md"
            )
            if c_path in deleted_paths:
                continue
            active_declared_paths.add(c_path)
            if c.get("studio_id"):
                active_declared_studio_ids.add(c["studio_id"])

        if not metadata_changed:
            book_file_id = str(uuid5(NAMESPACE_URL, scope.id + ":file:book.json"))
            book_file_row = existing_by_id.get(book_file_id)
            if book_file_row and not book_file_row.get("deleted") and book_file_row.get("text"):
                try:
                    stored_book = json.loads(book_file_row["text"])
                except ValueError:
                    stored_book = {}
                for stored_ch in stored_book.get("chapters") or []:
                    s_path = safe_path(stored_ch["file"]) if stored_ch.get("file") else ""
                    if (
                        s_path
                        and s_path in changed_paths
                        and s_path in raw_files
                        and s_path not in deleted_paths
                        and s_path not in active_declared_paths
                    ):
                        legacy.setdefault("chapters", []).append(stored_ch)
                        active_declared_paths.add(s_path)
                        if stored_ch.get("studio_id"):
                            active_declared_studio_ids.add(stored_ch["studio_id"])

        for path, old in existing_chapters_by_path.items():
            explicitly_deleted = path in deleted_paths
            if (
                not old.get("deleted")
                and old["id"] not in active_declared_studio_ids
                and (explicitly_deleted or (metadata_changed and path not in active_declared_paths))
            ):
                operations.append({"op": "retire", "entity_id": old["id"], "expected": old["version"]})

        if metadata_changed:
            mapping = {}

        # Project volumes when book.json has multiple/named volumes
        volume_id_for_seq = {}
        raw_volumes = legacy.get("volumes") or []
        if len(raw_volumes) > 1 or any(v.get("title") or v.get("studio_id") for v in raw_volumes):
            for v_idx, vol in enumerate(raw_volumes):
                vid = vol.get("studio_id") or str(
                    uuid5(NAMESPACE_URL, f"{scope.id}:volume:{vol.get('n', v_idx + 1)}")
                )
                old_vol = existing_by_id.get(vid)
                v_name = vol.get("title") or f"第{vol.get('n', v_idx + 1)}卷"
                v_data = {
                    **(old_vol["data"] if old_vol else {}),
                    "position": v_idx,
                    "status": vol.get("status") or "open",
                }
                if not old_vol or old_vol.get("deleted") or old_vol["name"] != v_name or old_vol["data"] != v_data:
                    v_op = {
                        "op": "update" if old_vol else "create",
                        "entity_id": vid,
                        "kind": old_vol["kind"] if old_vol else "volume",
                        "name": v_name,
                        "data": v_data,
                        "text": old_vol["text"] if old_vol else "",
                    }
                    if old_vol:
                        v_op["expected"] = old_vol["version"]
                        v_op["reactivate"] = bool(old_vol.get("deleted"))
                    operations.append(v_op)
                v_start = int(vol.get("start") or 1)
                v_end = int(vol["end"]) if vol.get("end") is not None else 10**9
                volume_id_for_seq[(v_start, v_end)] = vid

        for chapter in legacy.get("chapters", []):
            seq = int(chapter["seq"])
            path = safe_path(chapter.get("file", "")) if chapter.get("file") else f"{PROSE_DIR}/第{seq:04d}章.md"
            if path in deleted_paths:
                continue
            scene_rel = f"{SCENE_DIR}/ch-{seq:04d}.md"
            outline_rel = f"{CHAPTER_OUTLINE_DIR}/ch-{seq:04d}.md"
            relevant_changed = bool(metadata_changed or {path, scene_rel, outline_rel} & changed_paths)
            old_by_path = existing_chapters_by_path.get(path)
            eid = (
                chapter.get("studio_id")
                or (old_by_path["id"] if old_by_path else None)
                or mapping.get(str(seq))
                or str(uuid5(NAMESPACE_URL, scope.id + ":chapter-path:" + path))
            )
            mapping[str(seq)] = eid
            if not relevant_changed and eid in existing_by_id and not existing_by_id[eid].get("deleted"):
                continue
            old = existing_by_id.get(eid)
            if path in raw_files:
                try:
                    text = raw_files[path].decode("utf-8-sig")
                except UnicodeError:
                    raise DomainError("chapter_encoding", "章节正文必须是UTF-8文本") from None
            else:
                text = old["text"] if old and not metadata_changed else ""

            scene_txt = raw_files[scene_rel].decode("utf-8-sig").strip() if scene_rel in raw_files else ""
            outline_txt = (
                raw_files[outline_rel].decode("utf-8-sig").strip() if outline_rel in raw_files else ""
            )
            prev_data = dict(old["data"]) if old else {}
            mapped_status = _studio_chapter_status_from_cli(chapter.get("status", "draft"))
            data = {
                **prev_data,
                "position": seq if not volume_id_for_seq else prev_data.get("position", seq - 1),
                "legacy_path": path,
                "status": mapped_status,
                "key_chapter": bool(chapter.get("key", seq <= 3)),
            }
            for (v_lo, v_hi), vid in volume_id_for_seq.items():
                if v_lo <= seq <= v_hi:
                    data["parent_id"] = vid
                    data["position"] = seq - v_lo
                    break
            if scene_rel in changed_paths and scene_txt:
                data["beat_outline"] = scene_txt
            elif outline_rel in changed_paths and outline_txt:
                data["beat_outline"] = outline_txt
            elif not data.get("beat_outline"):
                if scene_txt:
                    data["beat_outline"] = scene_txt
                elif outline_txt:
                    data["beat_outline"] = outline_txt
            hk = chapter.get("hook") or {}
            hook_str = str(hk.get("line") or hk.get("type") or "").strip()
            if hook_str:
                data["hook"] = hook_str
            name = chapter.get("title") or f"第{seq}章"
            if (
                old
                and not old.get("deleted")
                and old["name"] == name
                and old["text"] == text
                and old["data"] == data
            ):
                continue
            operation = {
                "op": "update" if old else "create",
                "entity_id": eid,
                "kind": old["kind"] if old else "chapter",
                "name": name,
                "data": data,
                "text": text,
            }
            if old:
                operation["expected"] = old["version"]
                operation["reactivate"] = bool(old.get("deleted"))
            operations.append(operation)

        operations.extend(
            collect_setting_operations(
                scope_id=scope.id,
                changed_paths=changed_paths,
                deleted_paths=deleted_paths,
                raw_files=raw_files,
                old_files=old_files,
                existing_by_id=existing_by_id,
                existing_settings_by_path=existing_settings_by_path,
                setting_mapping=setting_mapping,
                defined_keys=defined_keys,
            )
        )

        # Project master outline 02-大纲/总纲.md -> Studio outline entity
        if MASTER_OUTLINE_PATH in changed_paths and MASTER_OUTLINE_PATH in raw_files:
            out_raw = raw_files[MASTER_OUTLINE_PATH].decode("utf-8-sig").strip()
            if out_raw:
                oid = next(
                    (
                        e["id"]
                        for e in all_existing
                        if e["kind"] in {"outline", "大纲"}
                        and (e.get("data") or {}).get("legacy_path") == MASTER_OUTLINE_PATH
                    ),
                    str(uuid5(NAMESPACE_URL, scope.id + ":outline-file:" + MASTER_OUTLINE_PATH)),
                )
                old_out = existing_by_id.get(oid)
                out_data = {
                    **(old_out["data"] if old_out else {}),
                    "legacy_path": MASTER_OUTLINE_PATH,
                    "beat_outline": out_raw,
                    "position": (old_out["data"].get("position", 0) if old_out else 0),
                }
                out_name = old_out["name"] if old_out else "全书总纲"
                if (
                    not old_out
                    or old_out.get("deleted")
                    or old_out["text"] != out_raw
                    or old_out["data"] != out_data
                ):
                    out_op = {
                        "op": "update" if old_out else "create",
                        "entity_id": oid,
                        "kind": old_out["kind"] if old_out else "outline",
                        "name": out_name,
                        "data": out_data,
                        "text": out_raw,
                    }
                    if old_out:
                        out_op["expected"] = old_out["version"]
                        out_op["reactivate"] = bool(old_out.get("deleted"))
                    operations.append(out_op)

        promise_ops, typed_foreshadows = collect_promise_operations(
            scope_id=scope.id,
            raw_files=raw_files,
            changed_paths=changed_paths,
            existing_by_id=existing_by_id,
            promise_mapping=promise_mapping,
        )
        operations.extend(promise_ops)

        next_config = {
            **scope.config,
            "legacy_chapters": mapping,
            "legacy_promises": promise_mapping,
            "legacy_settings": setting_mapping,
        }
        if (
            metadata_changed
            or STYLE_ANCHOR_PATH in changed_paths
            or "founding" not in (scope.config or {})
        ) and ("book.json" in raw_files or STYLE_ANCHOR_PATH in raw_files):
            extracted_founding = _extract_founding_from_files(
                legacy, raw_files, (scope.config or {}).get("founding")
            )
            if _has_nonempty_founding(extracted_founding) or "founding" in next_config:
                next_config["founding"] = extracted_founding

        scope.config = next_config
        require(len(operations) <= 500, "workspace_size", "语义变化超过单批预算，请拆分文件批次")
        if not operations:
            return {"version": scope.version, "unchanged": True, "boundaries": WORKSPACE_BOUNDARIES}
        change = await self.create_change(
            scope_id,
            ChangeInput(
                title=value.get("title", "CLI工作副本受控回写")[:256],
                base_version=scope.version,
                operations=operations,
            ),
        )
        result = await self.adopt(scope_id, change["id"], value.get("request_id") or change["id"])
        response = {
            **result,
            "coverage": {
                "raw_files": len(raw_files),
                "typed_chapters": len(mapping),
                "typed_settings": len(setting_mapping),
                "typed_foreshadows": typed_foreshadows,
                "boundaries": WORKSPACE_BOUNDARIES,
                "other_semantics": "章节、状态、立书档案、01-设定、场景卡/章纲、总纲与承诺伏笔已双向结构化映射；其余台账原件完整保留",
            },
        }
        self.db.add(
            Receipt(
                scope_id=scope_id, actor_id=self.actor.id, key=key, request_hash=request_hash, result=response
            )
        )
        return response
