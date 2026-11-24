"""Version-bound working copies. Originals and semantic studio projections commit and export together."""

import base64
import json
import re
from pathlib import PurePosixPath
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select

from ncc_data.application.security import authorize
from ncc_data.domain.contracts import ChangeInput, Query
from ncc_data.domain.studio_catalog import count_han_chars, ordered_book_chapters
from ncc_data.persistence.models import Receipt
from ncc_shared.errors import DomainError, require
from ncc_shared.serialization import digest

PROMISES_PATH = "06-台账/承诺台账.json"
MASTER_OUTLINE_PATH = "02-大纲/总纲.md"
SCENE_DIR = "02-大纲/场景卡"
CHAPTER_OUTLINE_DIR = "02-大纲/章纲"
PROSE_DIR = "04-正文"

WORKSPACE_BOUNDARIES = {
    "bidirectional": [
        "章节身份、全书顺序（含多卷与调序）、标题、正文、关键章标记、章尾钩文本",
        "章节细纲（CLI 场景卡/章纲 <-> 工作台 beat_outline；后台新增或非场景卡细纲输出至 02-大纲/章纲/ch-NNNN.md）",
        "总纲（02-大纲/总纲.md <-> 工作台 outline 实体）",
        "伏笔与明暗灰线（06-台账/承诺台账.json <-> 工作台 伏笔 实体，里层真义入私有字段 secret_note）",
    ],
    "cli_file_only": [
        "book.json 中的 soul 书魂四问、plight 四维处境历史、units 倒计时与复盘门禁、chapter.length/mood/end 硬检细节",
        "06-台账/知情台账.json、知识台账.json、状态事件.json 原件保留但不在看板投影为伏笔",
        "06-台账/承诺台账.json 中的暂定决策（内部流程项，不投影为读者向伏笔）",
    ],
    "studio_only": [
        "跨范围公共陈列卡挂载（commons_refs）、在线 AI 拆合工序候选与校准授权（Delegation/Calibration）",
    ],
}


def safe_path(value):
    p = PurePosixPath(value)
    require(
        value
        and not p.is_absolute()
        and ".." not in p.parts
        and "\\" not in value
        and not any(
            part in {".git", ".env", ".ncc-database.json", ".ncc-database-state.json"} for part in p.parts
        ),
        "workspace_path",
        "工作副本路径无效",
    )
    return p.as_posix()


def _promise_code_from_note(data: dict) -> str | None:
    note = str((data or {}).get("note") or "").strip()
    m = re.match(r"^((?:P|FS)-\d{4,})\b", note)
    return m.group(1) if m else None


def _next_promise_id(items: list[dict], prefix: str = "FS") -> str:
    hi = 0
    for it in items:
        m = re.fullmatch(rf"{prefix}-(\d+)", str(it.get("id") or ""))
        if m:
            hi = max(hi, int(m.group(1)))
    return f"{prefix}-{hi + 1:04d}"


def _cli_status_from_studio(studio_status: str, existing_status: str = "悬置") -> str:
    s = (studio_status or "").strip()
    if s in {"resolved", "已兑现", "兑现", "已回收", "完全兑现"}:
        return "已兑现"
    if s in {"dropped", "abandoned", "作废", "已作废", "放弃"}:
        return "作废"
    if existing_status in {"悬置", "推进中"}:
        return existing_status
    if s in {"推进中", "active"}:
        return "推进中"
    return "悬置"


def _studio_status_from_cli(cli_status: str, has_progress: bool = False) -> str:
    s = (cli_status or "").strip()
    if s == "已兑现":
        return "已兑现"
    if s == "作废":
        return "作废"
    if s == "推进中" or has_progress:
        return "推进中"
    return "已埋设"


class WorkspaceMixin:
    async def workspace_snapshot(self, scope_id):
        scope, actions = await authorize(self.db, self.actor, scope_id, "export")
        require("secret" in actions, "workspace_permission", "完整CLI工作副本需要秘密内容与导出权限", 403)
        files, offset = {}, 0
        volumes, chapters, outlines, foreshadows = [], [], [], []
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
            # Only write prose file if it existed before or has prose or is registered in book.json/studio
            files[chosen] = text.encode("utf-8")

        if "book.json" in files or ordered:
            state = (
                json.loads(files["book.json"].decode("utf-8"))
                if "book.json" in files
                else {
                    "schema_version": 3,
                    "title": scope.name,
                    "mode": "serial",
                    "stage": "serial",
                    "soul": {},
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
                if studio_status == "done":
                    ch_status = "done"
                elif old.get("status") in {"planned", "drafted", "done"} and old.get("sha", "") == text_sha:
                    ch_status = old["status"]
                else:
                    ch_status = "drafted" if text.strip() else (old.get("status") or "planned")
                entry = {
                    "origin": old.get("origin") or "author",
                    **old,
                    "seq": seq,
                    "title": obj["name"],
                    "file": path,
                    "studio_id": obj["id"],
                    "key": bool(data.get("key_chapter")) if "key_chapter" in data else bool(old.get("key", seq <= 3)),
                    "status": ch_status,
                    "sha": text_sha,
                    "words": count_han_chars(text) if text.strip() else int(old.get("words") or 0),
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

            state["chapters"] = synced_chapters
            if volumes:
                sorted_vols = sorted(volumes, key=lambda v: (int((v.get("data") or {}).get("position", 0)), v["id"]))
                vol_entries = []
                for v_idx, vol in enumerate(sorted_vols, 1):
                    v_chs = [
                        idx
                        for idx, ch in enumerate(ordered, 1)
                        if (ch.get("data") or {}).get("parent_id") == vol["id"]
                    ]
                    v_start = min(v_chs) if v_chs else (vol_entries[-1]["end"] + 1 if vol_entries and vol_entries[-1].get("end") else 1)
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
            files["book.json"] = (json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

        if outlines:
            primary = next(
                (o for o in outlines if (o.get("data") or {}).get("legacy_path") == MASTER_OUTLINE_PATH),
                outlines[0],
            )
            outline_body = str((primary.get("data") or {}).get("beat_outline") or primary.get("text") or "").strip()
            if outline_body:
                files[MASTER_OUTLINE_PATH] = (outline_body + "\n").encode("utf-8")

        if PROMISES_PATH in files or foreshadows:
            p_doc = (
                json.loads(files[PROMISES_PATH].decode("utf-8"))
                if PROMISES_PATH in files
                else {"items": []}
            )
            p_items = list(p_doc.get("items") or [])
            by_pid = {str(it.get("id")): it for it in p_items if it.get("id")}
            by_studio_id = {str(it.get("studio_id")): it for it in p_items if it.get("studio_id")}
            mapped_promises = scope.config.get("legacy_promises", {})
            inv_promises = {v: k for k, v in mapped_promises.items()}
            max_seq = len(ordered) or 1

            for fs in sorted(foreshadows, key=lambda x: (int((x.get("data") or {}).get("position", 0)), x["id"])):
                fdata = fs.get("data") or {}
                pid = (
                    inv_promises.get(fs["id"])
                    or _promise_code_from_note(fdata)
                    or (by_studio_id[fs["id"]]["id"] if fs["id"] in by_studio_id else None)
                )
                target = by_pid.get(pid) if pid else by_studio_id.get(fs["id"])
                line_type = fdata.get("line_type") or ("暗线" if fs["kind"] in {"暗线", "伏笔", "foreshadow"} else "明线")
                planted = fdata.get("planted_chapter")
                expected = fdata.get("expected_chapter")
                secret_truth = str(fdata.get("secret_note") or "").strip()
                clean_title = re.sub(r"^(?:P|FS)-\d{4,}\s*·\s*", "", fs["name"]).strip() or fs["name"]
                public_desc = (fs.get("text") or "").strip() or clean_title
                if target is not None:
                    new_status = _cli_status_from_studio(fdata.get("status", ""), target.get("status", "悬置"))
                    target["status"] = new_status
                    target["studio_id"] = fs["id"]
                    if line_type in {"明线", "暗线", "灰线"}:
                        target["line"] = line_type
                    if isinstance(planted, int) and planted >= 1:
                        target["created_ch"] = planted
                    if isinstance(expected, int) and expected >= 1:
                        low = int(target["window"][0]) if isinstance(target.get("window"), list) and target["window"] else (planted or 1)
                        target["window"] = [min(low, expected), expected]
                    if secret_truth:
                        target["true_meaning"] = secret_truth
                    if new_status == "已兑现" and not target.get("resolved_ch"):
                        target["resolved_ch"] = expected or max_seq
                else:
                    prefix = "FS" if line_type in {"暗线", "灰线"} or fs["kind"] in {"伏笔", "暗线", "foreshadow"} else "P"
                    new_id = pid or _next_promise_id(p_items, prefix)
                    c_ch = planted if isinstance(planted, int) and planted >= 1 else 1
                    win = [c_ch, max(c_ch, expected)] if isinstance(expected, int) and expected >= 1 else None
                    new_status = _cli_status_from_studio(fdata.get("status", ""), "悬置")
                    rec = {
                        "id": new_id,
                        "studio_id": fs["id"],
                        "type": "伏笔" if prefix == "FS" else "悬念",
                        "line": line_type if line_type in {"明线", "暗线", "灰线"} else "暗线",
                        "content": clean_title,
                        "surface_cover": public_desc if public_desc != clean_title else "",
                        "true_meaning": secret_truth,
                        "strength": int(fdata["strength"]) if isinstance(fdata.get("strength"), int) and 1 <= fdata["strength"] <= 5 else 3,
                        "created_ch": c_ch,
                        "window": win,
                        "desire": None,
                        "status": new_status,
                        "progress": [],
                        "resolved_ch": (expected or max_seq) if new_status == "已兑现" else None,
                    }
                    p_items.append(rec)
                    by_pid[new_id] = rec
            p_doc["items"] = p_items
            files[PROMISES_PATH] = (json.dumps(p_doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

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
        for item in value["files"]:
            path = safe_path(item.get("path", ""))
            if item.get("deleted"):
                raw_files.pop(path, None)
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

        all_existing = await self.all_entities(scope_id, include_deleted=True)
        existing_by_id = {e["id"]: e for e in all_existing}
        existing_chapters_by_path = {
            c["data"]["legacy_path"]: c
            for c in all_existing
            if c["kind"] in {"chapter", "章节"} and c["data"].get("legacy_path")
        }

        legacy = json.loads(raw_files.get("book.json", b"{}"))
        mapping = dict(scope.config.get("legacy_chapters", {}))
        promise_mapping = dict(scope.config.get("legacy_promises", {}))
        declared = {c.get("file") for c in legacy.get("chapters", []) if c.get("file")}
        declared_studio_ids = {c.get("studio_id") for c in legacy.get("chapters", []) if c.get("studio_id")}
        changed_paths = {safe_path(i["path"]) for i in value["files"]}
        deleted_paths = {safe_path(i["path"]) for i in value["files"] if i.get("deleted")}
        metadata_changed = "book.json" in changed_paths

        for path, old in existing_chapters_by_path.items():
            explicitly_deleted = path in deleted_paths
            if (
                not old.get("deleted")
                and old["id"] not in declared_studio_ids
                and (explicitly_deleted or (metadata_changed and path not in declared))
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
                        "kind": "volume",
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
            scene_rel = f"{SCENE_DIR}/ch-{seq:04d}.md"
            outline_rel = f"{CHAPTER_OUTLINE_DIR}/ch-{seq:04d}.md"
            relevant_changed = bool(
                metadata_changed or {path, scene_rel, outline_rel} & changed_paths
            )
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
            outline_txt = raw_files[outline_rel].decode("utf-8-sig").strip() if outline_rel in raw_files else ""
            prev_data = dict(old["data"]) if old else {}
            data = {
                **prev_data,
                "position": seq if not volume_id_for_seq else prev_data.get("position", seq - 1),
                "legacy_path": path,
                "status": chapter.get("status", "draft"),
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
                "kind": "chapter",
                "name": name,
                "data": data,
                "text": text,
            }
            if old:
                operation["expected"] = old["version"]
                operation["reactivate"] = bool(old.get("deleted"))
            operations.append(operation)

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
                if not old_out or old_out.get("deleted") or old_out["text"] != out_raw or old_out["data"] != out_data:
                    out_op = {
                        "op": "update" if old_out else "create",
                        "entity_id": oid,
                        "kind": "outline",
                        "name": out_name,
                        "data": out_data,
                        "text": out_raw,
                    }
                    if old_out:
                        out_op["expected"] = old_out["version"]
                        out_op["reactivate"] = bool(old_out.get("deleted"))
                    operations.append(out_op)

        # Project CLI promise ledger 06-台账/承诺台账.json -> Studio 伏笔 entities
        typed_foreshadows = 0
        if PROMISES_PATH in raw_files and (PROMISES_PATH in changed_paths or not promise_mapping):
            p_doc = json.loads(raw_files[PROMISES_PATH].decode("utf-8-sig"))
            seen_promise_eids = set()
            for idx, p in enumerate(p_doc.get("items") or []):
                pid = str(p.get("id") or "").strip()
                if not pid or p.get("type") == "暂定决策":
                    continue
                fid = (
                    p.get("studio_id")
                    or promise_mapping.get(pid)
                    or str(uuid5(NAMESPACE_URL, scope.id + ":promise:" + pid))
                )
                promise_mapping[pid] = fid
                seen_promise_eids.add(fid)
                typed_foreshadows += 1
                old_fs = existing_by_id.get(fid)
                line = p.get("line") or (
                    "灰线" if p.get("type") in {"期权", "母题"} else "暗线" if p.get("type") == "伏笔" else "明线"
                )
                status = _studio_status_from_cli(p.get("status") or "悬置", bool(p.get("progress")))
                cover = str(p.get("surface_cover") or "").strip()
                content = str(p.get("content") or "").strip()
                comp = str(p.get("compensation") or "").strip()
                truth = str(p.get("true_meaning") or "").strip()
                fname = f"{pid} · {(cover or content)[:60]}" if (cover or content) else pid
                ftext = cover or content
                if status == "作废" and comp:
                    ftext = f"{ftext}\n补偿交代：{comp}".strip()
                fdata = {
                    **(old_fs["data"] if old_fs else {}),
                    "position": idx,
                    "status": status,
                    "line_type": line,
                    "note": pid,
                }
                if isinstance(p.get("created_ch"), int) and p["created_ch"] >= 0:
                    fdata["planted_chapter"] = p["created_ch"]
                if isinstance(p.get("window"), list) and len(p["window"]) >= 2 and isinstance(p["window"][1], int):
                    fdata["expected_chapter"] = p["window"][1]
                if isinstance(p.get("strength"), int) and 0 <= p["strength"] <= 5:
                    fdata["strength"] = p["strength"]
                if truth:
                    fdata["secret_note"] = truth
                if (
                    old_fs
                    and not old_fs.get("deleted")
                    and old_fs["name"] == fname
                    and old_fs["text"] == ftext
                    and old_fs["data"] == fdata
                ):
                    continue
                fs_op = {
                    "op": "update" if old_fs else "create",
                    "entity_id": fid,
                    "kind": "伏笔",
                    "name": fname,
                    "data": fdata,
                    "text": ftext,
                }
                if old_fs:
                    fs_op["expected"] = old_fs["version"]
                    fs_op["reactivate"] = bool(old_fs.get("deleted"))
                operations.append(fs_op)
        else:
            typed_foreshadows = len(promise_mapping)

        scope.config = {
            **scope.config,
            "legacy_chapters": mapping,
            "legacy_promises": promise_mapping,
        }
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
                "typed_foreshadows": typed_foreshadows,
                "boundaries": WORKSPACE_BOUNDARIES,
                "other_semantics": "章节、场景卡/章纲、总纲与承诺伏笔已双向结构化映射；其余台账原件完整保留，详见 boundaries",
            },
        }
        self.db.add(
            Receipt(
                scope_id=scope_id, actor_id=self.actor.id, key=key, request_hash=request_hash, result=response
            )
        )
        return response
