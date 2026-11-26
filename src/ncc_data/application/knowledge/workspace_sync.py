"""Pure deterministic bidirectional mapping helpers for working copies, settings, founding, and promises."""

import json
import re
from pathlib import PurePosixPath
from uuid import NAMESPACE_URL, uuid5

from ncc_shared.errors import require
from ncc_shared.serialization import digest

PROMISES_PATH = "06-台账/承诺台账.json"
MASTER_OUTLINE_PATH = "02-大纲/总纲.md"
SCENE_DIR = "02-大纲/场景卡"
CHAPTER_OUTLINE_DIR = "02-大纲/章纲"
PROSE_DIR = "04-正文"
SETTINGS_DIR = "01-设定"
CHARACTERS_DIR = "01-设定/人物卡"
CATEGORIES_DIR = "01-设定/类目"
STYLE_ANCHOR_PATH = "03-文风/文风基准.md"

STRUCTURAL_KINDS = frozenset(
    {
        "chapter",
        "章节",
        "volume",
        "卷",
        "outline",
        "大纲",
        "细纲",
        "scene",
        "场景",
        "主线",
        "支线",
        "剧情",
        "foreshadow",
        "伏笔",
        "暗线",
        "悬念",
    }
)
EXCLUDED_SETTING_KINDS = STRUCTURAL_KINDS | {"legacy-file", "公共母本", "市场风向"}
CORE_SETTING_PATH_KINDS = {
    "01-设定/世界观圣经.md": "法则",
    "01-设定/力量体系.md": "境界",
    "01-设定/规则表.md": "制度",
}
CATEGORY_ALIASES = {
    "门派": "宗门",
    "帮派": "势力",
    "法器": "法宝",
    "兵器": "武器",
    "地域": "地点",
    "城邦": "城池",
}

WORKSPACE_BOUNDARIES = {
    "bidirectional": [
        "章节身份、全书顺序（含多卷与调序）、标题、正文、关键章标记、章尾钩文本与章节定稿状态（planned / draft / review / done）",
        "章节细纲（CLI 场景卡/章纲 <-> 工作台 beat_outline；后台新增或非场景卡细纲输出至 02-大纲/章纲/ch-NNNN.md）",
        "总纲（02-大纲/总纲.md <-> 工作台 outline 实体）",
        "立书档案（书魂四问与弧光、类型主副契约与毒点、写作模式 <-> book.json；文风基准 <-> 03-文风/文风基准.md）",
        "作品设定与资料卡（01-设定/人物卡、01-设定/类目/* 与核心设定文档 <-> /materials 实体，角色采访原件独立保留）",
        "伏笔与明暗灰线（06-台账/承诺台账.json <-> 工作台 伏笔 实体，里层真义入私有字段 secret_note）",
    ],
    "cli_file_only": [
        "book.json 中的 plight 四维处境历史、units 倒计时与复盘门禁、chapter.length/mood/end 硬检细节",
        "06-台账/知情台账.json、知识台账.json、状态事件.json 原件保留但不在看板投影为伏笔",
        "06-台账/承诺台账.json 中的暂定决策（内部流程项，不投影为读者向伏笔）",
    ],
    "studio_only": [
        "跨范围公共陈列卡挂载（commons_refs）、在线 AI 拆合工序候选与校准授权（Delegation/Calibration）",
    ],
}

_STUDIO_META_RE = re.compile(r"^\s*<!--\s*ncc-studio:\s*(\{[^\n]*?\})\s*-->\s*\n?")
_SECRET_SECTION_RE = re.compile(r"(?:^|\n)##\s*作者秘密\s*\n(.*)$", re.DOTALL)


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


def _safe_segment(value: str, fallback: str = "未命名") -> str:
    cleaned = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", (value or "").strip()).strip(" ._")
    if not cleaned or cleaned in {".", ".."}:
        return fallback
    if cleaned.endswith("-采访"):
        cleaned = f"{cleaned}_卡"
    return cleaned[:80]


def _is_setting_md_path(path: str) -> bool:
    return (
        isinstance(path, str)
        and path.startswith(SETTINGS_DIR + "/")
        and path.endswith(".md")
        and not path.endswith("-采访.md")
    )


def _has_nonempty_founding(founding: dict | None) -> bool:
    if not isinstance(founding, dict):
        return False
    return any(bool(v) for v in founding.values())


_KNOWN_CHAPTER_STATUSES = frozenset(
    {
        "",
        "done",
        "已定稿",
        "review",
        "reviewing",
        "checking",
        "revising",
        "待审",
        "planned",
        "pending",
        "规划中",
        "draft",
        "drafted",
        "drafting",
        "草稿",
    }
)


def _cli_chapter_status_from_studio(studio_status: str, text: str, old: dict) -> str:
    raw = (studio_status or "").strip()
    s = raw.lower()
    if raw and s not in _KNOWN_CHAPTER_STATUSES:
        return raw
    has_text = bool((text or "").strip())
    old_status = str(old.get("status") or "").strip()
    text_sha = digest((text or "").encode("utf-8"))[:16] if has_text else ""
    same_sha = old.get("sha", "") == text_sha
    if s in {"done", "已定稿"}:
        return "done"
    if s in {"review", "reviewing", "checking", "revising", "待审"}:
        if old_status in {"reviewing", "checking", "revising"} and same_sha:
            return old_status
        return "reviewing"
    if s in {"planned", "pending", "规划中"} and not has_text:
        if old_status in {"planned", "pending"} and same_sha:
            return old_status
        return "planned"
    if has_text:
        if old_status in {"drafted", "drafting"} and same_sha:
            return old_status
        return "drafted"
    if s in {"draft", "drafted", "drafting", "草稿"}:
        return "drafted"
    return old_status if old_status in {"planned", "pending"} else "planned"


def _studio_chapter_status_from_cli(cli_status: str) -> str:
    s = (cli_status or "").strip().lower()
    if s in {"done", "已定稿"}:
        return "done"
    if s in {"reviewing", "checking", "revising", "review", "待审"}:
        return "review"
    if s in {"planned", "pending", "规划中"}:
        return "planned"
    if s in {"drafted", "drafting", "draft", "草稿", ""}:
        return "draft"
    return str(cli_status or "draft")


def _parse_setting_markdown(raw_text: str, path: str) -> dict:
    text = (raw_text or "").lstrip("\ufeff")
    meta_id: str | None = None
    meta_kind: str | None = None
    m_meta = _STUDIO_META_RE.match(text)
    if m_meta:
        try:
            meta = json.loads(m_meta.group(1))
            if isinstance(meta, dict):
                if isinstance(meta.get("id"), str) and meta["id"].strip():
                    meta_id = meta["id"].strip()
                if isinstance(meta.get("kind"), str) and meta["kind"].strip():
                    meta_kind = meta["kind"].strip()
        except ValueError:
            pass
        rest = text[m_meta.end() :]
    else:
        rest = text

    secret_note = ""
    m_sec = _SECRET_SECTION_RE.search(rest)
    if m_sec:
        secret_note = m_sec.group(1).strip()
        rest = rest[: m_sec.start()]

    lines = rest.splitlines()
    idx = 0
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    stem = PurePosixPath(path).stem
    if idx < len(lines) and lines[idx].strip().startswith("# "):
        raw_heading = lines[idx].strip()[2:].strip()
        parts = PurePosixPath(path).parts
        if meta_id is None and len(parts) >= 4 and parts[0] == SETTINGS_DIR and parts[1] == "类目":
            cat = parts[2]
            if raw_heading.startswith(f"{cat}："):
                raw_heading = raw_heading[len(cat) + 1 :].strip() or stem
        name = (raw_heading or stem)[:512]
        body_text = "\n".join(lines[idx + 1 :]).strip()
    else:
        name = stem[:512]
        body_text = rest.strip()
    return {
        "meta_id": meta_id,
        "meta_kind": meta_kind,
        "name": name,
        "text": body_text,
        "secret_note": secret_note,
    }


def _render_setting_markdown(
    entity_id: str,
    kind: str,
    name: str,
    text: str,
    secret_note: str = "",
) -> bytes:
    meta = json.dumps({"id": entity_id, "kind": kind}, ensure_ascii=False, separators=(",", ":"))
    parts = [f"<!-- ncc-studio: {meta} -->", f"# {name}"]
    clean_body = (text or "").strip()
    if clean_body:
        parts.extend(["", clean_body])
    clean_secret = (secret_note or "").strip()
    if clean_secret:
        parts.extend(["", "## 作者秘密", "", clean_secret])
    return ("\n".join(parts) + "\n").encode("utf-8")


def _infer_setting_kind(path: str, meta_kind: str | None, defined_keys: set[str]) -> tuple[str, str | None]:
    if meta_kind and meta_kind in defined_keys and meta_kind not in EXCLUDED_SETTING_KINDS:
        return meta_kind, None
    if path in CORE_SETTING_PATH_KINDS:
        mapped_core = CORE_SETTING_PATH_KINDS[path]
        return (mapped_core if mapped_core in defined_keys else "source"), None
    if path.startswith(CHARACTERS_DIR + "/"):
        return ("人物" if "人物" in defined_keys else "character"), None
    if path.startswith(CATEGORIES_DIR + "/"):
        parts = PurePosixPath(path).parts
        if len(parts) >= 4:
            cat = parts[2]
            if cat in defined_keys and cat not in EXCLUDED_SETTING_KINDS:
                return cat, None
            aliased = CATEGORY_ALIASES.get(cat)
            if aliased and aliased in defined_keys:
                return aliased, None
            return "source", f"原设定类目：{cat}"
    return "source", None


def _extract_founding_from_files(legacy: dict, raw_files: dict[str, bytes], existing_founding: dict | None) -> dict:
    prev = existing_founding if isinstance(existing_founding, dict) else {}
    soul = legacy.get("soul") if isinstance(legacy.get("soul"), dict) else {}
    contract = legacy.get("contract") if isinstance(legacy.get("contract"), dict) else {}
    raw_arc = str(soul.get("arc") or "").strip()
    soul_arc = raw_arc if raw_arc in {"正向", "负向", "平弧"} else ""
    raw_status = str(soul.get("status") or "").strip()
    soul_status = raw_status if raw_status in {"暂定", "确定"} else ""
    raw_mode = str(legacy.get("mode") or "").strip()
    writing_mode = raw_mode if raw_mode in {"建筑师", "混合", "园丁"} else ""
    extras = [
        str(x).strip()[:120]
        for x in (contract.get("extras") if isinstance(contract.get("extras"), list) else [])
        if str(x).strip()
    ][:12]
    poisons = [
        str(x).strip()[:400]
        for x in (contract.get("poison") if isinstance(contract.get("poison"), list) else [])
        if str(x).strip()
    ][:30]
    if STYLE_ANCHOR_PATH in raw_files:
        try:
            style_anchor = raw_files[STYLE_ANCHOR_PATH].decode("utf-8-sig").strip()[:4000]
        except UnicodeError:
            style_anchor = str(prev.get("style_anchor") or "")[:4000]
    else:
        style_anchor = str(prev.get("style_anchor") or "")[:4000]
    return {
        "soul_question": str(soul.get("question") or "")[:1000],
        "soul_answer": str(soul.get("answer") or "")[:1000],
        "soul_injustice": str(soul.get("injustice") or "")[:1000],
        "soul_ending": str(soul.get("ending") or "")[:1000],
        "soul_arc": soul_arc,
        "soul_status": soul_status,
        "contract_main": str(contract.get("main") or "")[:500],
        "contract_extras": extras,
        "contract_audience": str(contract.get("audience") or "")[:500],
        "poison_lines": poisons,
        "writing_mode": writing_mode,
        "style_anchor": style_anchor,
    }


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


def project_settings_to_files(
    files: dict[str, bytes],
    settings_entities: list[dict],
    scope_config: dict | None,
    actions: set[str] | frozenset[str],
) -> None:
    active_setting_ids = {s["id"] for s in settings_entities}
    saved_legacy_settings = (scope_config or {}).get("legacy_settings") or {}
    for mapped_path, mapped_eid in saved_legacy_settings.items():
        if mapped_eid not in active_setting_ids and _is_setting_md_path(mapped_path):
            files.pop(mapped_path, None)

    used_setting_paths: set[str] = set()
    sorted_settings = sorted(
        settings_entities,
        key=lambda s: (int((s.get("data") or {}).get("position", 0) or 0), s.get("name") or "", s["id"]),
    )
    for s in sorted_settings:
        sdata = s.get("data") or {}
        preferred_setting = sdata.get("legacy_path")
        chosen_setting: str | None = None
        if (
            isinstance(preferred_setting, str)
            and _is_setting_md_path(preferred_setting)
            and preferred_setting not in used_setting_paths
        ):
            chosen_setting = safe_path(preferred_setting)
        if not chosen_setting:
            safe_name = _safe_segment(s.get("name") or "", "设定")
            if s["kind"] in {"人物", "character"}:
                base_p = f"{CHARACTERS_DIR}/{safe_name}.md"
                chosen_setting = (
                    base_p
                    if base_p not in used_setting_paths
                    else f"{CHARACTERS_DIR}/{safe_name}-{s['id'][:6]}.md"
                )
            else:
                safe_kind = _safe_segment(s["kind"], "其他")
                base_p = f"{CATEGORIES_DIR}/{safe_kind}/{safe_name}.md"
                chosen_setting = (
                    base_p
                    if base_p not in used_setting_paths
                    else f"{CATEGORIES_DIR}/{safe_kind}/{safe_name}-{s['id'][:6]}.md"
                )
        used_setting_paths.add(chosen_setting)
        s_secret = str(sdata.get("secret_note") or "").strip() if "secret" in actions else ""
        s_text = (s.get("text") or "").strip()
        keep_existing = False
        if chosen_setting in files:
            try:
                parsed_cur = _parse_setting_markdown(files[chosen_setting].decode("utf-8"), chosen_setting)
                if (
                    parsed_cur["name"] == s["name"]
                    and parsed_cur["text"] == s_text
                    and parsed_cur["secret_note"] == s_secret
                    and (parsed_cur["meta_id"] in {None, s["id"]})
                    and (parsed_cur["meta_kind"] in {None, s["kind"]})
                ):
                    keep_existing = True
            except UnicodeError:
                keep_existing = False
        if not keep_existing:
            files[chosen_setting] = _render_setting_markdown(
                s["id"], s["kind"], s["name"], s_text, s_secret
            )


def apply_founding_to_state(state: dict, files: dict[str, bytes], founding: dict) -> None:
    soul = dict(state.get("soul") or {})
    soul["question"] = founding.get("soul_question", soul.get("question", ""))
    soul["answer"] = founding.get("soul_answer", soul.get("answer", ""))
    soul["injustice"] = founding.get("soul_injustice", soul.get("injustice", ""))
    soul["ending"] = founding.get("soul_ending", soul.get("ending", ""))
    if founding.get("soul_arc"):
        soul["arc"] = founding["soul_arc"]
    else:
        soul.setdefault("arc", "")
    if founding.get("soul_status"):
        soul["status"] = founding["soul_status"]
    else:
        soul.setdefault("status", "未填")
    soul.setdefault("deadline", "")
    state["soul"] = soul

    contract = dict(state.get("contract") or {})
    contract["main"] = founding.get("contract_main", contract.get("main", ""))
    contract["extras"] = list(founding.get("contract_extras") or [])
    contract["audience"] = founding.get("contract_audience", contract.get("audience", ""))
    contract["poison"] = list(founding.get("poison_lines") or [])
    contract.setdefault("signing", {})
    state["contract"] = contract

    if founding.get("writing_mode"):
        state["mode"] = founding["writing_mode"]

    style_anchor = str(founding.get("style_anchor") or "").strip()
    if style_anchor:
        existing_style = ""
        if STYLE_ANCHOR_PATH in files:
            try:
                existing_style = files[STYLE_ANCHOR_PATH].decode("utf-8").strip()
            except UnicodeError:
                existing_style = ""
        if existing_style != style_anchor:
            files[STYLE_ANCHOR_PATH] = (style_anchor + "\n").encode("utf-8")


def project_foreshadows_to_promises(
    files: dict[str, bytes],
    foreshadows: list[dict],
    scope_config: dict | None,
    max_seq: int,
) -> None:
    p_doc = (
        json.loads(files[PROMISES_PATH].decode("utf-8"))
        if PROMISES_PATH in files
        else {"items": []}
    )
    p_items = list(p_doc.get("items") or [])
    by_pid = {str(it.get("id")): it for it in p_items if it.get("id")}
    by_studio_id = {str(it.get("studio_id")): it for it in p_items if it.get("studio_id")}
    mapped_promises = (scope_config or {}).get("legacy_promises") or {}
    inv_promises = {v: k for k, v in mapped_promises.items()}

    for fs in sorted(foreshadows, key=lambda x: (int((x.get("data") or {}).get("position", 0)), x["id"])):
        fdata = fs.get("data") or {}
        pid = (
            inv_promises.get(fs["id"])
            or _promise_code_from_note(fdata)
            or (by_studio_id[fs["id"]]["id"] if fs["id"] in by_studio_id else None)
        )
        target = by_pid.get(pid) if pid else by_studio_id.get(fs["id"])
        line_type = fdata.get("line_type") or (
            "暗线" if fs["kind"] in {"暗线", "伏笔", "foreshadow"} else "明线"
        )
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
                low = (
                    int(target["window"][0])
                    if isinstance(target.get("window"), list) and target["window"]
                    else (planted or 1)
                )
                target["window"] = [min(low, expected), expected]
            if secret_truth:
                target["true_meaning"] = secret_truth
            if new_status == "已兑现" and not target.get("resolved_ch"):
                target["resolved_ch"] = expected or max_seq
        else:
            prefix = (
                "FS"
                if line_type in {"暗线", "灰线"} or fs["kind"] in {"伏笔", "暗线", "foreshadow"}
                else "P"
            )
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
                "strength": (
                    int(fdata["strength"])
                    if isinstance(fdata.get("strength"), int) and 1 <= fdata["strength"] <= 5
                    else 3
                ),
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


def collect_setting_operations(
    *,
    scope_id: str,
    changed_paths: set[str],
    deleted_paths: set[str],
    raw_files: dict[str, bytes],
    old_files: dict[str, bytes],
    existing_by_id: dict[str, dict],
    existing_settings_by_path: dict[str, dict],
    setting_mapping: dict[str, str],
    defined_keys: set[str],
) -> list[dict]:
    ops: list[dict] = []
    for path in sorted(changed_paths):
        if not _is_setting_md_path(path):
            continue
        if path in deleted_paths or path not in raw_files:
            old_meta_id = None
            if path in old_files:
                old_meta_id = _parse_setting_markdown(
                    old_files[path].decode("utf-8", errors="ignore"), path
                )["meta_id"]
            target_eid = (
                setting_mapping.pop(path, None)
                or old_meta_id
                or (existing_settings_by_path[path]["id"] if path in existing_settings_by_path else None)
            )
            if (
                target_eid
                and target_eid in existing_by_id
                and existing_by_id[target_eid]["kind"] not in EXCLUDED_SETTING_KINDS
                and not existing_by_id[target_eid].get("deleted")
            ):
                old_set = existing_by_id[target_eid]
                ops.append({"op": "retire", "entity_id": target_eid, "expected": old_set["version"]})
            continue
        try:
            raw_md = raw_files[path].decode("utf-8-sig")
        except UnicodeError:
            continue
        parsed = _parse_setting_markdown(raw_md, path)
        inferred_kind, note_hint = _infer_setting_kind(path, parsed["meta_kind"], defined_keys)
        sid_cand = parsed["meta_id"]
        if sid_cand and sid_cand in existing_by_id and existing_by_id[sid_cand]["kind"] in EXCLUDED_SETTING_KINDS:
            sid_cand = None
        seid = (
            sid_cand
            or setting_mapping.get(path)
            or (existing_settings_by_path[path]["id"] if path in existing_settings_by_path else None)
            or str(uuid5(NAMESPACE_URL, f"{scope_id}:setting:{path}"))
        )
        setting_mapping[path] = seid
        old_set = existing_by_id.get(seid)
        effective_kind = old_set["kind"] if old_set else inferred_kind
        sdata = dict(old_set["data"]) if old_set else {}
        sdata["legacy_path"] = path
        if note_hint and not sdata.get("note"):
            sdata["note"] = note_hint
        unset_keys: list[str] = []
        if parsed["secret_note"]:
            sdata["secret_note"] = parsed["secret_note"]
        elif "secret_note" in sdata:
            sdata.pop("secret_note", None)
            unset_keys.append("secret_note")
        if (
            old_set
            and not old_set.get("deleted")
            and old_set["name"] == parsed["name"]
            and old_set["text"] == parsed["text"]
            and old_set["data"] == sdata
            and not unset_keys
        ):
            continue
        s_op = {
            "op": "update" if old_set else "create",
            "entity_id": seid,
            "kind": effective_kind,
            "name": parsed["name"],
            "data": sdata,
            "text": parsed["text"],
        }
        if unset_keys and old_set:
            s_op["unset"] = unset_keys
        if old_set:
            s_op["expected"] = old_set["version"]
            s_op["reactivate"] = bool(old_set.get("deleted"))
        ops.append(s_op)
    return ops


def collect_promise_operations(
    *,
    scope_id: str,
    raw_files: dict[str, bytes],
    changed_paths: set[str],
    existing_by_id: dict[str, dict],
    promise_mapping: dict[str, str],
) -> tuple[list[dict], int]:
    ops: list[dict] = []
    typed_foreshadows = 0
    if PROMISES_PATH in raw_files and (PROMISES_PATH in changed_paths or not promise_mapping):
        p_doc = json.loads(raw_files[PROMISES_PATH].decode("utf-8-sig"))
        for idx, p in enumerate(p_doc.get("items") or []):
            pid = str(p.get("id") or "").strip()
            if not pid or p.get("type") == "暂定决策":
                continue
            fid = (
                p.get("studio_id")
                or promise_mapping.get(pid)
                or str(uuid5(NAMESPACE_URL, scope_id + ":promise:" + pid))
            )
            promise_mapping[pid] = fid
            typed_foreshadows += 1
            old_fs = existing_by_id.get(fid)
            line = p.get("line") or (
                "灰线"
                if p.get("type") in {"期权", "母题"}
                else "暗线"
                if p.get("type") == "伏笔"
                else "明线"
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
                "kind": old_fs["kind"] if old_fs else "伏笔",
                "name": fname,
                "data": fdata,
                "text": ftext,
            }
            if old_fs:
                fs_op["expected"] = old_fs["version"]
                fs_op["reactivate"] = bool(old_fs.get("deleted"))
            ops.append(fs_op)
    else:
        typed_foreshadows = len(promise_mapping)
    return ops, typed_foreshadows
