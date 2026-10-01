"""三本账：承诺、知情、知识（数据）、状态事件（只追加）；读者此刻与前情。"""

import hashlib
import json
import re
import sys
from pathlib import Path
from .core import (EVENTS, FACTS, KNOWLEDGE, NON_READER_TYPES, OPEN_STATES, PROMISES, PROMISE_PREFIX, PROMISE_TYPES, as_int, current_chapter, die, ledger, load, mood_of, next_id, parse_window, read_json, save, scene_path, split_names, write_json)


def promise_overdue(p, cur: int) -> bool:
    if p.get("status") not in OPEN_STATES or p.get("type") in ("期权", "母题"):
        return False
    if p.get("type") == "暂定决策":
        dl = as_int(p.get("deadline"))
        return dl is not None and dl < cur
    w = p.get("window")
    return bool(w) and w[1] < cur


def promise_due_soon(p, cur: int, ahead: int = 3) -> bool:
    if p.get("type") != "暂定决策" or p.get("status") not in OPEN_STATES:
        return False
    dl = as_int(p.get("deadline"))
    return dl is not None and cur <= dl <= cur + ahead


def promise_summary(book_dir: Path, d: dict) -> dict:
    items = ledger(book_dir, PROMISES)["items"]
    cur = current_chapter(d)
    reader = [p for p in items if p.get("type") not in NON_READER_TYPES]
    live = lambda t: sum(1 for p in items if p.get("type") == t and p.get("status") in OPEN_STATES)
    return {
        "open": sum(1 for p in reader if p.get("status") in OPEN_STATES),
        "resolved": sum(1 for p in reader if p.get("status") == "已兑现"),
        "dropped": sum(1 for p in reader if p.get("status") == "作废"),
        "overdue": sum(1 for p in items if promise_overdue(p, cur)),
        "options": live("期权"),
        "motifs": live("母题"),
        "pending_decisions": live("暂定决策"),
    }


def chapter_touches(items, seq: int):
    """本章建立、推进、兑现（或作废补偿）的读者向承诺。"""
    hits = []
    for p in items:
        if p.get("type") in NON_READER_TYPES:
            continue
        if p.get("created_ch") == seq:
            hits.append((p["id"], "建立"))
        if any(e.get("ch") == seq for e in p.get("progress", [])):
            hits.append((p["id"], "推进"))
        if p.get("resolved_ch") == seq:
            hits.append((p["id"], "兑现" if p.get("status") == "已兑现" else "作废补偿"))
    return hits


def reader_now_lines(book_dir: Path, d: dict, seq: int, top: int = 5):
    items = ledger(book_dir, PROMISES)["items"]
    know = ledger(book_dir, KNOWLEDGE)["items"]
    events = read_json(book_dir / EVENTS, {"events": []}).get("events", [])
    before = [c for c in d.get("chapters", []) if c["seq"] < seq]
    out = [f"## 读者此刻（写第 {seq} 章前）", ""]
    out.append("**知道什么（读者知道、角色还不知道）**")
    gaps = [k for k in know if "读者" in k.get("known_by", []) and k.get("unknown_to")
            and (k.get("since_ch") or 0) < seq]
    out += [f"- {k['id']} {k['fact']}——{'、'.join(k['unknown_to'])} 还不知道" for k in gaps[:top]] or ["- （无登记的信息差）"]
    out += ["", "**在等什么（强度最高的开放承诺）**"]
    waiting = [p for p in items if p.get("type") not in NON_READER_TYPES
               and p.get("status") in OPEN_STATES and (p.get("created_ch") or 0) < seq]
    waiting.sort(key=lambda p: (-(p.get("strength") or 0), p.get("created_ch") or 0))
    lines = []
    for p in waiting[:top]:
        age = seq - (p.get("created_ch") or seq)
        w = p.get("window")
        tail = f"，计划第{w[0]}–{w[1]}章兑现" if w else ""
        lines.append(f"- {p['id']} [{p['type']}] 强度{p.get('strength')}：{p['content']}（已等 {age} 章{tail}）")
    out += lines or ["- （没有开放承诺——本章至少要建立一条）"]
    out += ["", "**情绪在哪**"]
    moods = [(c["seq"], mood_of(c)) for c in before if c.get("mood")][-5:]
    if moods:
        out.append("- 近几章：" + " → ".join(
            f"{s_}{m['tension']}" + (f"（{'、'.join(m['colors'])}）" if m.get("colors") else "") for s_, m in moods))
        last_release = max((s_ for s_, m in moods if m["tension"] == "放"), default=None)
        out.append(f"- 距上次释放：{seq - last_release} 章" if last_release else "- 近几章没有释放段")
    else:
        out.append("- （近几章未登记情绪，chapter mood 登记）")
    losses = [e for e in events if e.get("attribute") == "失去" and (e.get("chapter") or 0) < seq][-3:]
    if losses:
        out += ["", "**最近失去了什么**"]
        out += [f"- 第{e.get('chapter')}章 {e.get('entity')}：{e.get('old')} → {e.get('new')}" for e in losses]
    out += ["", "**可能腻了什么**"]
    hooks = [c["hook"]["type"] for c in before if c.get("hook")][-5:]
    tired = [f"章尾钩子「{t}」近 5 章用了 {hooks.count(t)} 次" for t in dict.fromkeys(hooks) if hooks.count(t) >= 3]
    colors = [x for _, m in moods for x in m.get("colors", [])]
    tired += [f"情绪「{x}」近 5 章出现 {colors.count(x)} 次" for x in dict.fromkeys(colors) if colors.count(x) >= 3]
    desires = [p.get("desire") for p in items if p.get("type") == "爽点欠账" and p.get("status") == "已兑现"
               and p.get("desire") and seq - 10 <= (p.get("resolved_ch") or -99) < seq]
    tired += [f"爽感谱系第 {x} 型近 10 章兑现了 {desires.count(x)} 次" for x in dict.fromkeys(desires) if desires.count(x) >= 3]
    out += [f"- {t}" for t in tired] or ["- （无明显重复）"]
    cur = current_chapter(d)
    alerts = [p for p in items if promise_overdue(p, cur) or promise_due_soon(p, cur)]
    if alerts:
        out += ["", "**到期提醒**"]
        out += [f"- {p['id']} [{p['type']}] {p['content']}" for p in alerts]
    return out


def focus_core(book_dir: Path, d: dict, seq: int) -> list:
    """前情：上一章结束在何时何地、下一章要接什么、近三章的翻转。全部取自源头（book.json、场景卡）。"""
    done = [c for c in d.get("chapters", []) if c["seq"] < seq and c.get("status") == "done"]
    out = []
    if done:
        last, end = done[-1], done[-1].get("end") or {}
        where = "，".join(x for x in (end.get("time"), f"在{end['place']}" if end.get("place") else "") if x)
        out.append(f"- 最近定稿：第{last['seq']}章" + (f"（结束时：{where}）" if where else "（结束时的时间地点还没登记）"))
        if end.get("next"):
            out.append(f"- 下一章要接：{end['next']}")
    else:
        out.append("- 还没有定稿的章")
    out += ["", "**近三章发生了什么**（取自场景卡的翻转）"]
    for c in done[-3:]:
        card = scene_path(book_dir, c["seq"])
        turns = [t.strip() for t in re.findall(r"翻转[：:]\s*([^\n]+)", card.read_text("utf-8"))] if card.exists() else []
        hook = c.get("hook") or {}
        out.append(f"- 第{c['seq']}章：" + ("；".join(turns) or "（场景卡缺失）") + (f"｜章尾钩子：{hook['type']}" if hook.get("type") else ""))
    if not done:
        out.append("- （无）")
    return out


def events_sha(events) -> str:
    return hashlib.sha256(json.dumps(events, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def history_problem(book_dir: Path, d: dict):
    mark = (d.get("history") or {}).get("events")
    if not mark:
        return None
    ev = read_json(book_dir / EVENTS, {"events": []}).get("events", [])
    if len(ev) < mark["count"] or events_sha(ev[:mark["count"]]) != mark["sha"]:
        return f"状态事件被改写或删除过（历史只允许追加）：登记时有 {mark['count']} 条，现在前 {mark['count']} 条对不上"
    return None


def cmd_event(a):
    """状态事件（世界账的历史）只经这里追加，不手改 JSON（七律三、六）。"""
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    data = read_json(book_dir / EVENTS, {"events": []})
    ev = data.setdefault("events", [])
    if a.action == "list":
        for e in ev:
            if a.entity and e.get("entity") != a.entity:
                continue
            print(f"第{e.get('chapter')}章 {e.get('entity')}·{e.get('attribute')}：{e.get('old')} → {e.get('new')}  {e.get('reason', '')}")
        return
    bad = history_problem(book_dir, d)
    if bad:
        die(bad + "；先用 check 查清楚，再决定怎么修")
    ev.append({"entity": a.entity, "chapter": a.ch, "attribute": a.attr, "old": a.old or "", "new": a.new or "",
               "reason": a.reason or "", "evidence": a.evidence or ""})
    write_json(book_dir / EVENTS, data)
    d.setdefault("history", {})["events"] = {"count": len(ev), "sha": events_sha(ev)}
    save(book_dir, d)
    print(f"OK 第{a.ch}章 {a.entity}·{a.attr}：{a.old or '—'} → {a.new or '—'}")


def cmd_water(a):
    book_dir = Path(a.book_dir)
    items = ledger(book_dir, PROMISES)["items"]
    hits = chapter_touches(items, a.seq)
    if hits:
        print(f"ch{a.seq}: " + "，".join(f"{i} {k}" for i, k in hits))
        return
    print(f"ch{a.seq}: 水章——未建立、推进或兑现任何读者向承诺")
    sys.exit(1)


def cmd_promise(a):
    book_dir = Path(a.book_dir)
    load(book_dir)
    data = ledger(book_dir, PROMISES)
    items = data["items"]
    if a.action == "list":
        d = load(book_dir)
        cur = current_chapter(d)
        for p in items:
            if a.open and p.get("status") not in OPEN_STATES:
                continue
            if a.type and p.get("type") != a.type:
                continue
            flag = " 逾期" if promise_overdue(p, cur) else (" 将到期" if promise_due_soon(p, cur) else "")
            w = p.get("window")
            when = f" 窗口{w[0]}-{w[1]}" if w else (f" 最晚{p['deadline']}" if p.get("deadline") else "")
            print(f"{p['id']} [{p['type']}] 强度{p.get('strength')} {p['status']} 第{p.get('created_ch')}章起{when}{flag}  {p['content']}")
        return
    if a.action == "add":
        if a.type not in PROMISE_TYPES:
            die(f"--type 只能是 {'/'.join(PROMISE_TYPES)}")
        if a.type == "暂定决策" and not a.deadline:
            die("暂定决策必须给 --deadline（章号或节点，如 22 或 第一卷卷复盘）")
        if not 1 <= a.strength <= 5:
            die("--strength 取 1–5")
        pid = next_id(items, PROMISE_PREFIX.get(a.type, PROMISE_PREFIX["*"]))
        items.append({
            "id": pid, "type": a.type, "content": a.content, "strength": a.strength,
            "created_ch": a.ch, "window": parse_window(a.window), "deadline": a.deadline,
            "desire": a.desire, "status": "开放", "progress": [], "resolved_ch": None})
        msg = f"OK {pid} [{a.type}] 第{a.ch}章建立"
    else:
        p = next((x for x in items if x["id"] == a.id), None)
        if not p:
            die(f"承诺台账中没有 {a.id}")
        if p.get("status") not in OPEN_STATES:
            die(f"{a.id} 状态为 {p.get('status')}，不能再 {a.action}")
        if a.action == "touch":
            p.setdefault("progress", []).append({"ch": a.ch, "note": a.note or ""})
            p["status"] = "推进中"
            msg = f"OK {a.id} 第{a.ch}章推进"
        elif a.action == "resolve":
            p["status"] = "已兑现"
            p["resolved_ch"] = a.ch
            if a.note:
                p["resolve_note"] = a.note
            msg = f"OK {a.id} 第{a.ch}章兑现"
        elif a.action == "reschedule":
            if not (a.note or "").strip():
                die("延期必须写 --note（用什么强化让读者继续等，如\"第 30 章再露一角\"）")
            old = p.get("window")
            p["window"] = parse_window(a.window)
            p.setdefault("progress", []).append({"ch": None, "note": f"延期 {old}→{p['window']}：{a.note}"})
            msg = f"OK {a.id} 延期到第 {p['window'][0]}–{p['window'][1]} 章"
        elif a.action == "drop":
            if not (a.compensation or "").strip():
                die("承诺作废必须写 --compensation（给读者的交代或替代兑现）")
            p["status"] = "作废"
            p["resolved_ch"] = a.ch
            p["compensation"] = a.compensation
            msg = f"OK {a.id} 第{a.ch}章作废，补偿：{a.compensation}"
    write_json(book_dir / PROMISES, data)
    print(msg)


def cmd_know(a):
    book_dir = Path(a.book_dir)
    load(book_dir)
    data = ledger(book_dir, KNOWLEDGE)
    items = data["items"]
    if a.action == "list":
        for k in items:
            if a.who and a.who not in k.get("known_by", []) and a.who not in k.get("unknown_to", []):
                continue
            print(f"{k['id']} 第{k.get('since_ch')}章 知道:{','.join(k.get('known_by', [])) or '无'} "
                  f"不知道:{','.join(k.get('unknown_to', [])) or '无'}  {k['fact']}")
        return
    if a.action == "add":
        kid = next_id(items, "K")
        items.append({"id": kid, "fact": a.fact, "since_ch": a.ch,
                      "known_by": split_names(a.known_by), "unknown_to": split_names(a.unknown_to),
                      "log": []})
        msg = f"OK {kid} 第{a.ch}章登记"
    else:  # learn
        k = next((x for x in items if x["id"] == a.id), None)
        if not k:
            die(f"知情台账中没有 {a.id}")
        if a.who in k.get("unknown_to", []):
            k["unknown_to"].remove(a.who)
        if a.who not in k.setdefault("known_by", []):
            k["known_by"].append(a.who)
        k.setdefault("log", []).append({"ch": a.ch, "who": a.who})
        msg = f"OK {a.id} 第{a.ch}章 {a.who} 得知"
    write_json(book_dir / KNOWLEDGE, data)
    print(msg)


def cmd_fact(a):
    book_dir = Path(a.book_dir)
    load(book_dir)
    data = read_json(book_dir / FACTS, {"facts": {}})
    facts = data.setdefault("facts", {})
    if a.action == "get":
        f = facts.get(a.key)
        if not f:
            die(f"知识台账中没有「{a.key}」", 1)
        print(f"{a.key} = {f['value']}（第{f.get('ch')}章，来源：{f.get('source') or '未注'}，类别：{f.get('category') or '未分'}）")
        return
    if a.action == "list":
        for k, f in facts.items():
            if a.category and f.get("category") != a.category:
                continue
            print(f"{k} = {f['value']}  [{f.get('category') or '未分'}] 第{f.get('ch')}章 来源：{f.get('source') or '未注'}")
        return
    old = facts.get(a.key)
    if old and old["value"] != a.value and not a.override:
        print(f"CONFLICT 「{a.key}」已记为 {old['value']}（第{old.get('ch')}章），本次为 {a.value}。"
              "若是剧情内的合理变化请加 --override 并在正文交代原因。", file=sys.stderr)
        sys.exit(1)
    entry = {"value": a.value, "ch": a.ch, "source": a.source or "", "category": a.category or ""}
    if old and old["value"] != a.value:
        entry["history"] = old.get("history", []) + [{k: old[k] for k in ("value", "ch", "source") if k in old}]
    facts[a.key] = entry
    write_json(book_dir / FACTS, data)
    print(f"OK {a.key} = {a.value}")


def cmd_reader_now(a):
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    print("\n".join(reader_now_lines(book_dir, d, a.seq, a.top)))
