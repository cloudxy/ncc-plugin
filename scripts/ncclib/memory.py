"""角色记忆与会话交接：本书记忆、跨书记忆、记忆日志、交接卡、全文检索。只往下依赖 core。"""

import json
import re
import sys
from pathlib import Path
from .core import (EVENTS, FACTS, HANDOFF, HANDOFF_CFG, HANDOFF_KINDS, HANDOFF_LAYERS, HAN, KNOWLEDGE, MEMORY_CFG, MEMORY_DIR, MEMORY_KINDS, MEMORY_LOG, MEMORY_ROLES, PROMISES, REVIEW_DIR, SCENE_DIR, SHARED_MEMORY, WRITER_GUARD, L, append_jsonl, bigrams, book_root, chars, current_chapter, die, ledger, load, next_id, next_seq, now, read_json, read_jsonl, similarity, soul_leaks, split_names, view_head, write_json)
from .core import capped, writer_input_problems


STATE_ZH = {"candidate": "候选", "active": "生效", "archived": "归档", "superseded": "已合并"}


PREF_LIKE = re.compile(r"作者(?:很|更|比较|特别|一向)?(?:喜欢|不喜欢|偏好|讨厌|不要|想要|爱看|不爱看)")


CAPS = MEMORY_CFG["caps"]


# ---------- 记忆 ----------

def memory_file(book_dir: Path, role: str, shared: bool = False) -> Path:
    base = book_root(book_dir) / SHARED_MEMORY if shared else book_dir / MEMORY_DIR
    return base / f"{role}.json"


def memory_items(book_dir: Path, role: str, shared: bool = False) -> list:
    return read_json(memory_file(book_dir, role, shared), {"items": []}).get("items", [])


def memory_save(book_dir: Path, role: str, items: list, shared: bool = False):
    """存源头，同时重写它的视图（七律二：视图只由源头生成）。"""
    p = memory_file(book_dir, role, shared)
    write_json(p, {"role": role, "items": items})
    p.with_suffix(".md").write_text(memory_view(book_dir, role, shared), "utf-8")


def memory_view(book_dir: Path, role: str, shared: bool = False) -> str:
    items = memory_items(book_dir, role, shared)
    src = f"`{SHARED_MEMORY if shared else MEMORY_DIR}/{role}.json`"
    lines = [f"# {role} 的{'跨书' if shared else '本书'}记忆", "",
             view_head(src, "memory add/reinforce/merge/archive/restore/promote"), ""]
    for st in ("active", "candidate", "archived", "superseded"):
        xs = [i for i in items if i.get("status") == st]
        if xs:
            lines += [f"## {STATE_ZH[st]}", ""]
            lines += [f"- {i['id']} [{i['kind']}] {i['text']}（命中 {i.get('hits', 1)}"
                      + (f"，第 {i.get('since')}–{i.get('last')} 章" if i.get("since") is not None else "")
                      + (f"；并入 {i['by']}" if i.get("by") else "") + (f"；已进跨书记忆 {i['promoted_to']}" if i.get("promoted_to") else "")
                      + f"；证据：{'；'.join(i.get('evidence', [])) or '—'}）" for i in xs]
            lines.append("")
    if not items:
        lines.append("（还没有记忆）")
    return "\n".join(lines).rstrip() + "\n"


def memory_roles(book_dir: Path, shared: bool = False) -> list:
    base = book_root(book_dir) / SHARED_MEMORY if shared else book_dir / MEMORY_DIR
    return [r for r in MEMORY_ROLES if (base / f"{r}.json").exists()]


def mem_log(book_dir: Path, op: str, role: str, mid: str, **kw):
    append_jsonl(book_dir / MEMORY_LOG, {"at": now(), "op": op, "role": role, "id": mid, **kw})


def role_cfg(role: str) -> dict:
    if role not in MEMORY_ROLES:
        die(f"--role 只能是 {'/'.join(MEMORY_ROLES)}")
    return MEMORY_CFG["roles"].get(role, {"kinds": list(MEMORY_KINDS)})


def guard(d: dict, role: str, kind: str, text: str):
    """写入前的可见范围检查：种类、作者偏好、写手与 editor 的判据词和书魂原文（铁律 9）。"""
    cfg = role_cfg(role)
    if kind not in MEMORY_KINDS:
        die(f"--kind 只能是 {'/'.join(MEMORY_KINDS)}")
    if kind not in cfg["kinds"]:
        die(f"{role} 的记忆只记 {'、'.join(cfg['kinds'])}（{cfg.get('keeps', '')}）")
    if PREF_LIKE.search(text):
        die("这像是作者偏好：偏好只记在偏好文件（pref like/reject/dislike），记忆不另存一份")
    if cfg.get("guard"):
        problems = writer_input_problems(d, text)
        if problems:
            die(f"{role} 的记忆要写成怎么写，不放" + "；".join(problems))


def evidence_of(a) -> list:
    ev = []
    for x in a.evidence or []:
        ev += [s.strip() for s in re.split(r"[；;]", x) if s.strip()]
    return list(dict.fromkeys(ev))


def active_items(items: list, kinds=None) -> list:
    out = [i for i in items if i.get("status") == "active" and (not kinds or i["kind"] in kinds)]
    return sorted(out, key=lambda i: (i["kind"] != "约定", -i.get("hits", 1), -(i.get("last") or 0)))


def evidence_count(item: dict) -> int:
    return len(set(item.get("evidence", [])))


def genre_fits(item: dict, d: dict) -> bool:
    want = (item.get("applies") or {}).get("题材") or []
    return not want or bool(set(want) & set(d.get("genre_tags", [])))


def memory_slice(book_dir: Path, d: dict, role: str, plain: bool = False, kinds=None, persona: str = None):
    """派单用的记忆切片：本书记忆（上限 book_chars）＋适用的跨书记忆（上限 shared_chars）。plain=True 给写手：只留"写成什么"。"""
    def fmt(i):
        return f"- {i['text']}" if plain else f"- [{i['kind']}] {i['text']}（{i['id']}）"
    own = active_items(memory_items(book_dir, role), kinds)
    if persona:
        own = [i for i in own if persona in i["text"] or (i.get("applies") or {}).get("画像") == persona]
    shared = [i for i in active_items(memory_items(book_dir, role, shared=True), kinds) if genre_fits(i, d)]
    if persona:
        shared = [i for i in shared if persona in i["text"] or (i.get("applies") or {}).get("画像") == persona]
    limit = CAPS["book_items"]
    a, cut_a = capped([fmt(i) for i in own[:limit]], CAPS["book_chars"])
    cut_a += max(0, len(own) - limit)
    b, cut_b = capped([fmt(i) for i in shared], CAPS["shared_chars"])
    return a, b, cut_a + cut_b


def stale_before(d: dict):
    """连续 stale_units 个单元没再出现的界线：倒数第 stale_units 个已关单元的起点。"""
    closed = [u for u in d.get("units", []) if u.get("status") == "closed"]
    n = MEMORY_CFG["stale_units"]
    return closed[-n]["start"] if len(closed) >= n else None


def consolidate_lines(book_dir: Path, d: dict, apply: bool = False, roles=None, shared: bool = False) -> list:
    """单元整理底稿：候选、可合并、久未出现、超上限、够格进跨书记忆；--apply 只自动归档久未出现的。"""
    out, line = [], None if shared else stale_before(d)
    cap = CAPS["shared_chars"] if shared else CAPS["book_chars"]
    for role in roles or memory_roles(book_dir, shared):
        items = memory_items(book_dir, role, shared)
        act = [i for i in items if i.get("status") == "active"]
        cand = [i for i in items if i.get("status") == "candidate"]
        live = act + cand
        pairs = [(x["id"], y["id"]) for k, x in enumerate(live) for y in live[k + 1:]
                 if x["kind"] == y["kind"] and similarity(x["text"], y["text"]) >= MEMORY_CFG["similar"]]
        stale = [i for i in act if line is not None and i["kind"] not in MEMORY_CFG["once_ok"] and (i.get("last") or 0) < line]
        size = chars(i["text"] for i in act)
        promo = [i for i in act if not shared and i["kind"] not in MEMORY_CFG["once_ok"] and evidence_count(i) >= MEMORY_CFG["promote_hits"]
                 and not i.get("promoted_to")]
        if not (cand or pairs or stale or promo or size > cap or len(act) > CAPS["book_items"]):
            continue
        out.append(f"- {role}{'（跨书）' if shared else ''}：生效 {len(act)} 条（{size} 字，上限 {cap} 字、{CAPS['book_items']} 条）")
        out += [f"  - 候选（再出现一次才生效）：{i['id']} {i['text']}" for i in cand]
        out += [f"  - 相似候选：{a} 与 {b}（先确认同义，再 memory merge；相反意见不要合并）" for a, b in pairs]
        if size > cap or len(act) > CAPS["book_items"]:
            out.append("  - 超上限：合并相近的，或归档用不上的")
        for i in stale:
            if apply:
                i.update(status="archived", prev="active", note="连续两个单元没再出现，自动归档")
                mem_log(book_dir, "auto-archive", role, i["id"])
            out.append(f"  - {'已自动归档' if apply else '久未出现'}：{i['id']} {i['text']}（最后一次第 {i.get('last')} 章）")
        out += [f"  - 够格进跨书记忆：{i['id']} {i['text']}（命中 {i.get('hits')} 次；完本时默认晋升，memory promote）" for i in promo]
        if apply and stale:
            memory_save(book_dir, role, items, shared)
    return out


def cmd_memory(a):
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    act = a.action
    scope_shared = getattr(a, "shared", False)
    if act == "list":
        roles = [a.role] if a.role else memory_roles(book_dir, a.shared)
        if not roles:
            print("（还没有记忆）")
        for role in roles:
            items = memory_items(book_dir, role, a.shared)
            shown = items if a.all else [i for i in items if i.get("status") in ("active", "candidate")]
            print(f"## {role}{'（跨书）' if a.shared else ''}：{len(shown)} 条")
            for i in shown:
                print(f"- {i['id']} [{i['kind']}·{STATE_ZH.get(i['status'], i['status'])}] {i['text']}"
                      f"（命中 {i.get('hits', 1)}，第 {i.get('since')}–{i.get('last')} 章；证据：{'；'.join(i.get('evidence', [])) or '—'}）")
        return
    if act == "consolidate":
        lines = consolidate_lines(book_dir, d, apply=a.apply, roles=[a.role] if a.role else None, shared=scope_shared)
        print("\n".join(lines) if lines else "记忆不用整理：没有候选、重复、久未出现或超上限的条目")
        ho = [e for e in handoff_open(book_dir) if e["kind"] == "决定"] if not scope_shared else []
        if ho:
            print("还没落进源头的决定（写进台账、场景卡、偏好或记忆后 handoff close）：")
            print("\n".join(f"- {e['id']} {e['text']}" for e in ho))
        return
    role = a.role
    role_cfg(role)
    items = memory_items(book_dir, role, scope_shared)
    def persist():
        memory_save(book_dir, role, items, scope_shared)

    def log(op, mid, **kw):
        mem_log(book_dir, op, role, mid, scope="shared" if scope_shared else "book", **kw)

    find = lambda mid: next((i for i in items if i["id"] == mid), None) or die(f"{role} 的记忆里没有 {mid}")
    ch = a.ch if getattr(a, "ch", None) is not None else current_chapter(d)
    if act == "add":
        guard(d, role, a.kind, a.text)
        ev = evidence_of(a)
        live = [i for i in items if i["kind"] == a.kind and i.get("status") in ("active", "candidate")]
        exact = next((i for i in live if i["text"].strip() == a.text.strip()), None)
        if exact:
            i = exact
            reinforce(book_dir, role, i, ev or [f"第 {ch} 章"], ch)
            memory_save(book_dir, role, items)
            print(f"OK 和 {i['id']} 正文相同，合并独立证据：{i['id']} 命中 {i['hits']} 次（{STATE_ZH[i['status']]}）")
            return
        best = max(((similarity(a.text, i["text"]), i) for i in live), default=(0, None), key=lambda x: x[0])
        ev = ev or [f"第 {ch} 章"]
        once = a.kind in MEMORY_CFG["once_ok"]
        item = {"id": next_id(items, "MEM"), "kind": a.kind, "text": a.text.strip(), "evidence": ev, "since": ch, "last": ch,
                "hits": len(ev), "recordings": 1, "status": "active" if once or len(ev) >= MEMORY_CFG["min_evidence"] else "candidate", "at": now()}
        items.append(item)
        memory_save(book_dir, role, items)
        mem_log(book_dir, "add", role, item["id"], text=item["text"], status=item["status"])
        print(f"OK {role} {item['id']} [{a.kind}] {STATE_ZH[item['status']]}"
              + ("（同类证据再出现一次才生效：一次侥幸不成经验）" if item["status"] == "candidate" else ""))
        if best[0] >= MEMORY_CFG["similar"]:
            print(f"  与 {best[1]['id']} 相似，已独立保存；确认同义后 memory merge，纠正旧意见则 edit 或 archive")
        size = chars(i["text"] for i in items if i.get("status") == "active")
        if size > CAPS["book_chars"]:
            print(f"  提醒：{role} 的生效记忆 {size} 字，超过上限 {CAPS['book_chars']}；派单跳过放不下的整条，单元整理时压缩或归档")
        return
    if act == "reinforce":
        i = find(a.id)
        ev = evidence_of(a) or [f"第 {ch} 章"]
        if scope_shared:
            ev = [f"{book_dir.resolve()}::{e}" for e in ev]
        reinforce(book_dir, role, i, ev, ch, shared=scope_shared)
        persist()
        print(f"OK {i['id']} 命中 {i['hits']} 次（{STATE_ZH[i['status']]}）")
    elif act == "edit":
        i = find(a.id)
        guard(d, role, i["kind"], a.text)
        old = i["text"]
        i["text"] = a.text.strip()
        persist()
        log("edit", i["id"], before=old, text=i["text"], note=a.note or "")
        print(f"OK {i['id']} 已修改（{'跨书' if scope_shared else '本书'}记忆；证据与来源保留）")
    elif act == "archive":
        i = find(a.id)
        if i["status"] == "archived":
            die(f"{a.id} 已归档")
        i.update(prev=i["status"], status="archived", note=a.note or "")
        persist()
        log("archive", i["id"], note=a.note or "")
        print(f"OK {i['id']} 已归档（memory restore 可撤回）")
    elif act == "restore":
        i = find(a.id)
        if i["status"] not in ("archived", "superseded"):
            die(f"{a.id} 不是已归档或已合并的条目")
        i["status"] = i.pop("prev", "candidate")
        i.pop("by", None)
        persist()
        log("restore", i["id"])
        print(f"OK {i['id']} 已恢复（{STATE_ZH[i['status']]}）")
    elif act == "merge":
        into = find(a.into)
        if a.into in a.ids:
            die("不能把记忆合并到自己")
        if any(find(mid)["kind"] != into["kind"] for mid in a.ids):
            die("只能合并同一种类的记忆")
        if a.text:
            guard(d, role, into["kind"], a.text)
            into["text"] = a.text.strip()
        for mid in a.ids:
            x = find(mid)
            into["evidence"] = list(dict.fromkeys(into.get("evidence", []) + x.get("evidence", [])))
            into["since"] = min(into.get("since") or ch, x.get("since") or ch)
            into["last"] = max(into.get("last") or 0, x.get("last") or 0)
            x.update(prev=x["status"], status="superseded", by=into["id"])
        into["hits"] = len(into["evidence"])
        if into["status"] == "candidate" and len(into["evidence"]) >= MEMORY_CFG["min_evidence"]:
            into["status"] = "active"
        persist()
        log("merge", into["id"], merged=a.ids)
        print(f"OK {'、'.join(a.ids)} 并入 {into['id']}（命中 {into['hits']} 次）")
    elif act == "promote":
        ids = a.ids or [i["id"] for i in items if i.get("status") == "active" and i["kind"] not in MEMORY_CFG["once_ok"]
                        and evidence_count(i) >= MEMORY_CFG["promote_hits"] and not i.get("promoted_to")]
        if not ids:
            print(f"{role} 没有够格进跨书记忆的条目（命中 ≥ {MEMORY_CFG['promote_hits']} 次、不是本书约定）")
            return
        shared = memory_items(book_dir, role, shared=True)
        applies = {"题材": split_names(a.genre)} if a.genre else {"题材": d.get("genre_tags", [])}
        for mid in ids:
            i = find(mid)
            if i["kind"] in MEMORY_CFG["once_ok"]:
                die(f"{mid} 是本书约定，不进跨书记忆")
            if i.get("status") != "active" or evidence_count(i) < MEMORY_CFG["promote_hits"]:
                die(f"{mid} 晋升需要生效且至少 {MEMORY_CFG['promote_hits']} 处独立证据")
            if i.get("promoted_to"):
                continue
            new = {"id": next_id(shared, "MX"), "kind": i["kind"], "text": i["text"], "hits": evidence_count(i),
                   "evidence": [f"{book_dir.resolve()}::{e}" for e in dict.fromkeys(i["evidence"])],
                   "applies": {**(i.get("applies") or {}), **applies}, "status": "active", "at": now(),
                   "origin": {"book": d.get("title"), "id": mid}}
            shared.append(new)
            i["promoted_to"] = new["id"]
            mem_log(book_dir, "promote", role, mid, to=new["id"])
            print(f"OK {mid} → 跨书记忆 {new['id']}（适用题材：{'、'.join(applies['题材']) or '不限'}）")
        memory_save(book_dir, role, shared, shared=True)
        memory_save(book_dir, role, items)


def reinforce(book_dir: Path, role: str, i: dict, ev: list, ch: int, shared: bool = False):
    i["evidence"] = list(dict.fromkeys(i.get("evidence", []) + ev))
    i["hits"] = len(i["evidence"])
    i["recordings"] = i.get("recordings", 1) + 1
    i["last"] = max(i.get("last") or 0, ch)
    if i["status"] == "candidate" and len(i["evidence"]) >= MEMORY_CFG["min_evidence"]:
        i["status"] = "active"
    mem_log(book_dir, "reinforce", role, i["id"], scope="shared" if shared else "book", evidence=ev, status=i["status"])


# ---------- 会话交接卡 ----------

def handoff_entries(book_dir: Path) -> list:
    """把只追加的记录折叠成条目：add 建条，close 关掉。"""
    by = {}
    for r in read_jsonl(book_dir / HANDOFF):
        if r.get("op") == "add":
            by[r["id"]] = {**r, "closed": None}
        elif r.get("op") == "close" and r.get("id") in by:
            by[r["id"]]["closed"] = {"to": r.get("to"), "note": r.get("note", ""), "at": r.get("at")}
    return list(by.values())


def handoff_open(book_dir: Path) -> list:
    return [e for e in handoff_entries(book_dir) if not e["closed"]]


def handoff_visible(e: dict, role: str, seq=None) -> bool:
    vis = HANDOFF_CFG["visibility"].get(role, None)
    if not vis:
        return False
    if vis["kinds"] != "*" and e["kind"] not in vis["kinds"]:
        return False
    if vis["layers"] != "*" and e.get("layer") not in vis["layers"]:
        return False
    rng = e.get("chapters")
    if rng and seq is not None and seq > rng[1]:
        return False                      # 过了作用范围，不再进派单
    if vis.get("chapter") and rng and seq is not None and not rng[0] <= seq <= rng[1]:
        return False
    return True


def handoff_slice(book_dir: Path, d: dict, role: str, seq=None, plain: bool = False, cap: int = None) -> list:
    seq = seq if seq is not None else next_seq(d)
    es = [e for e in handoff_open(book_dir) if handoff_visible(e, role, seq)]
    es.sort(key=lambda e: e["at"], reverse=True)

    def fmt(e):
        if plain:
            return f"- {e['text']}"
        where = f"·第{e['chapters'][0]}–{e['chapters'][1]}章" if e.get("chapters") else ""
        return f"- [{e['kind']}{'·' + e['layer'] if e.get('layer') else ''}{where}] {e['text']}（{e['id']}）"
    limit = cap if cap is not None else (HANDOFF_CFG["writer_chars"] if plain else HANDOFF_CFG["brief_chars"])
    lines, cut = capped([fmt(e) for e in es], limit)
    if cut:
        print(f"提醒：{role} 的交接省略 {cut} 条（超过字数预算，请压缩原条目）", file=sys.stderr)
    return lines


def parse_chapters(s):
    if not s:
        return None
    m = re.fullmatch(r"\s*(\d+)\s*(?:[-~～至]\s*(\d+))?\s*", str(s))
    if not m:
        die(f"--ch 写章号或范围（如 12 或 12-15），收到: {s}")
    a, b = int(m.group(1)), int(m.group(2) or m.group(1))
    return [min(a, b), max(a, b)]


def cmd_handoff(a):
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    entries = handoff_entries(book_dir)
    if a.action == "add":
        if a.kind not in HANDOFF_KINDS:
            die(f"--kind 只能是 {'/'.join(HANDOFF_KINDS)}")
        if a.kind in ("原话", "决定") and not a.layer:
            die(f"原话与决定要写 --layer（{'/'.join(HANDOFF_LAYERS)}），派单按它切给各角色")
        if a.layer and a.layer not in HANDOFF_LAYERS:
            die(f"--layer 只能是 {'/'.join(HANDOFF_LAYERS)}")
        if a.layer in ("L3", "L4") and soul_leaks(d, a.text):
            die("这条会进写手包，书魂原文不能进：改记到 L0，或换成本章要发生的事")
        rec = {"op": "add", "id": next_id(entries, "H"), "at": now(), "kind": a.kind, "text": a.text.strip(),
               "layer": a.layer or "", "chapters": parse_chapters(a.ch)}
        append_jsonl(book_dir / HANDOFF, rec)
        who = [r for r in HANDOFF_CFG["visibility"] if handoff_visible(rec, r, None)]
        print(f"OK {rec['id']} [{a.kind}] 会切给：{'、'.join(who)}")
        return
    if a.action == "close":
        e = next((x for x in entries if x["id"] == a.id), None) or die(f"没有交接条目 {a.id}")
        if e["closed"]:
            die(f"{a.id} 已经关过（落到 {e['closed']['to']}）")
        append_jsonl(book_dir / HANDOFF, {"op": "close", "id": a.id, "at": now(), "to": a.to, "note": a.note or ""})
        print(f"OK {a.id} 已落到「{a.to}」并关闭")
        return
    if a.role:
        lines = handoff_slice(book_dir, d, a.role, a.ch, plain=a.role in ("writer", "editor"))
        print("\n".join(lines) if lines else f"（没有要切给 {a.role} 的交接）")
        return
    for e in entries:
        if a.open and e["closed"]:
            continue
        st = f"已落到「{e['closed']['to']}」" if e["closed"] else "开放"
        where = f" 第{e['chapters'][0]}–{e['chapters'][1]}章" if e.get("chapters") else ""
        print(f"{e['id']} [{e['kind']}{'·' + e['layer'] if e.get('layer') else ''}{where}] {st}：{e['text']}")
    if not entries:
        print("（还没有交接条目）")


# ---------- 全文检索 ----------

def recall_units(book_dir: Path, role: str):
    """(来源, 章号或 None, 文本)；按角色的可见范围过滤来源。"""
    cfg = MEMORY_CFG["recall"]
    allowed = cfg.get(role or "*", cfg["*"])
    if "memory" in allowed:
        for r in [role] if role else memory_roles(book_dir):
            for i in memory_items(book_dir, r):
                yield f"记忆·{r}", i.get("last"), f"[{i['kind']}·{STATE_ZH.get(i['status'])}] {i['text']}（{i['id']}；{'；'.join(i.get('evidence', []))}）"
    if "memory_log" in allowed:
        for r in read_jsonl(book_dir / MEMORY_LOG):
            yield "记忆日志", None, json.dumps(r, ensure_ascii=False)
    if "handoff" in allowed:
        for e in handoff_entries(book_dir):
            if role and not handoff_visible({**e, "chapters": None}, role):
                continue
            yield "交接", (e.get("chapters") or [None])[0], f"{e['id']} [{e['kind']}] {e['text']}" + (f"（已落到 {e['closed']['to']}）" if e["closed"] else "")
    if "scenes" in allowed:
        for p in sorted((book_dir / SCENE_DIR).glob("ch-*.md")):
            seq = int(re.search(r"(\d+)", p.stem).group(1))
            for line in p.read_text("utf-8").splitlines():
                if HAN.search(line):
                    yield "场景卡", seq, line.strip()
    if "reviews" in allowed:
        for p in sorted((book_dir / L("reviews")).glob("*.md")) + sorted((book_dir / REVIEW_DIR).glob("*.md")):
            m = re.search(r"ch-(\d+)", p.stem)
            for line in p.read_text("utf-8").splitlines():
                if HAN.search(line):
                    yield f"审稿·{p.stem}", int(m.group(1)) if m else None, line.strip()
    if "ledgers" in allowed:
        for p in ledger(book_dir, PROMISES)["items"]:
            yield "承诺台账", p.get("created_ch"), f"{p['id']} [{p['type']}] {p['content']} {p['status']}"
        for k in ledger(book_dir, KNOWLEDGE)["items"]:
            yield "知情台账", k.get("since_ch"), f"{k['id']} {k['fact']}"
        for key, f in read_json(book_dir / FACTS, {"facts": {}}).get("facts", {}).items():
            yield "知识台账", f.get("ch"), f"{key} = {f.get('value')}"
        for e in read_json(book_dir / EVENTS, {"events": []}).get("events", []):
            yield "状态事件", e.get("chapter"), f"{e.get('entity')} {e.get('attribute')}：{e.get('old')} → {e.get('new')} {e.get('reason') or ''}"


def cmd_recall(a):
    book_dir = Path(a.book_dir)
    load(book_dir)
    if a.role and a.role not in MEMORY_ROLES:
        die(f"--role 只能是 {'/'.join(MEMORY_ROLES)}")
    words = [w for w in a.words if w.strip()]
    qb = bigrams("".join(words))
    hits = []
    for src, ch, text in recall_units(book_dir, a.role):
        if ch is not None and ((a.from_ch and ch < a.from_ch) or (a.to_ch and ch > a.to_ch)):
            continue
        exact = sum(text.count(w) for w in words)
        overlap = len(qb & bigrams(text))
        if not exact and overlap < 2:
            continue
        hits.append((exact * 3 + overlap, src, ch, text))
    hits.sort(key=lambda x: -x[0])
    for score, src, ch, text in hits[:a.top]:
        pos = min([text.find(w) for w in words if w in text] or [0])
        snip = text[max(0, pos - 30):pos + 50]
        print(f"[{src}{'·第' + str(ch) + '章' if ch is not None else ''}] {snip}")
    if not hits:
        print("（没有找到）")
