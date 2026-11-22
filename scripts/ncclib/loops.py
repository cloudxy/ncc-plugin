"""循环与收束：单元、卷、收束、读者反馈、团队、作者可持续、复盘底稿（含记忆整理、技法结算、对标基线、进化提议）。"""

import datetime
import hashlib
import re
import sys
from pathlib import Path
from .core import (DARK_LINE_COOL, L, MEMORY_CFG, MEMORY_LOG, SANDBOX_DIR, TRACK_PLAYBOOK, as_int, book_root, next_seq, read_jsonl, scene_path, EVENTS, FEEDBACK_KINDS, FEEDBACK_SOURCES, FINALE_LIST, FINALE_REQUIRED, KNOWLEDGE, NON_READER_TYPES, OPEN_STATES, PROMISES, READER_DATA, REVIEW_DIR, TEAM_POSITIONS, UNIT_REVIEW_REQUIRED, VOLUME_REVIEW_REQUIRED, current_chapter, die, ensure_m3_fields, ledger, load, load_cfg, mood_of, normalize_domain, now, open_unit, open_volume, range_chapters, read_json, save, write_json)
from .ledgers import chapter_touches, dark_line_cooling, infer_line, plight_lines, promise_last_touch, promise_overdue
from . materials import material_cards, material_usage
from .scenes import knowledge_rows
from .views import GEN_BEGIN, GEN_RE, outside_block, write_block
from .memory import consolidate_lines, handoff_open, memory_items, memory_roles
from .techniques import settle, technique_refs
from .decon import compare_lines
from .evolve import proposals, scan


def _count(xs) -> dict:
    out = {}
    for x in xs:
        out[x] = out.get(x, 0) + 1
    return out


def has_sections(p: Path, needed) -> list:
    """复盘与收束文件：只看生成区块之外（作者与角色写的判断），区块里的数据不算回答。"""
    if not p.exists() or not p.read_text("utf-8").strip():
        return [f"缺文件或为空: {p.name}"]
    text = outside_block(p.read_text("utf-8"))
    problems = [f"{p.name} 缺「{x}」一节" for x in needed if x not in text]
    if "（待填）" in text:
        problems.append(f"{p.name} 还有「（待填）」没写")
    return problems


def cmd_unit(a):
    book_dir = Path(a.book_dir)
    d = ensure_m3_fields(load(book_dir))
    units = d["units"]
    if a.action == "list":
        for u in units:
            extra = "｜".join(x for x in (f"倒计时:{u['countdown']}" if u.get("countdown") else "",
                                          f"跃迁:{u['milestone']}" if u.get("milestone") else "",
                                          f"弧光章:ch{u['arc_ch']}" if u.get("arc_ch") else "") if x)
            print(f"{u['id']} 第{u['start']}–{u.get('end') or '…'}章 {u['status']}  {u.get('title', '')}" + (f"（{extra}）" if extra else ""))
        return
    if a.action == "open":
        if open_unit(d):
            die(f"单元 {open_unit(d)['id']} 还没关，先 unit close")
        uid = f"U{len(units) + 1}"
        rec = {"id": uid, "start": a.start, "end": None, "title": a.title or "", "status": "open", "opened_at": now()}
        if getattr(a, "countdown", None):
            rec["countdown"] = a.countdown
        if getattr(a, "milestone", None):
            rec["milestone"] = a.milestone
        if getattr(a, "arc_ch", None) is not None:
            if a.arc_ch < a.start:
                die("--arc-ch 不能早于单元起点 --start")
            rec["arc_ch"] = a.arc_ch
            for c in d.get("chapters", []):
                if c["seq"] == a.arc_ch:
                    c["key"] = True
        units.append(rec)
        msg = f"OK 单元 {uid} 从第 {a.start} 章开始"
    else:  # close
        u = open_unit(d)
        if not u:
            die("没有进行中的单元")
        if a.end < u["start"]:
            die("--end 早于单元起点")
        problems = has_sections(book_dir / REVIEW_DIR / f"单元-{u['id']}.md", UNIT_REVIEW_REQUIRED)
        if problems:
            print(f"UNIT {u['id']}: 不能关闭——先做单元复盘（ncc_state.py report {book_dir} unit 生成底稿）")
            for p in problems:
                print(f"  - {p}")
            sys.exit(1)
        u.update({"end": a.end, "status": "closed", "closed_at": now()})
        msg = f"OK 单元 {u['id']} 关闭（第{u['start']}–{a.end}章）"
        auto = [f"  技法结算：{x}" for x in settle(book_dir, d, u["start"], a.end)]
        auto += [f"  记忆{x[1:]}" for x in consolidate_lines(book_dir, d, apply=True) if "已自动归档" in x]
        left = [e for e in handoff_open(book_dir) if e["kind"] == "决定"]
        if auto:
            msg += "\n自动做了（可撤回）：\n" + "\n".join(auto)
        if left:
            msg += f"\n提醒：还有 {len(left)} 条作者的决定没落进源头（{'、'.join(e['id'] for e in left)}），写进台账、场景卡、偏好或记忆后 handoff close"
    save(book_dir, d)
    print(msg)


def cmd_volume(a):
    book_dir = Path(a.book_dir)
    d = ensure_m3_fields(load(book_dir))
    v = open_volume(d)
    if d.get("stage") != "serial" or not v or v.get("status") != "open":
        die(f"只能在连载阶段结束进行中的卷（当前 stage={d.get('stage')}）")
    v.update({"end": a.end, "status": "reviewing"})
    d["stage"] = "volume"
    save(book_dir, d)
    print(f"OK 第{v['n']}卷写到第 {a.end} 章，进入卷复盘；复盘写到 {REVIEW_DIR}/卷{v['n']}.md 后过 gate volume")


def cmd_finale(a):
    book_dir = Path(a.book_dir)
    d = ensure_m3_fields(load(book_dir))
    if d.get("stage") != "serial":
        die(f"只能从连载阶段进入收束（当前 stage={d.get('stage')}）")
    d["stage"] = "finale"
    save(book_dir, d)
    print(f"OK 进入收束；用 report {book_dir} finale 生成收束清单底稿，写到 {FINALE_LIST}")


def cmd_feedback(a):
    book_dir = Path(a.book_dir)
    load(book_dir)
    data = ledger(book_dir, READER_DATA)
    if a.action == "list":
        for f in data["items"]:
            if a.ch and f.get("ch") != a.ch:
                continue
            print(f"第{f['ch']}章 [{f['source']}{'·' + f['persona'] if f.get('persona') else ''}] "
                  f"{f['kind']}={f['value']}  {f.get('note', '')}")
        return
    if a.source not in FEEDBACK_SOURCES:
        die(f"--source 只能是 {'/'.join(FEEDBACK_SOURCES)}")
    if a.kind not in FEEDBACK_KINDS:
        die(f"--kind 只能是 {'/'.join(FEEDBACK_KINDS)}")
    item = {"ch": a.ch, "source": a.source, "kind": a.kind, "value": a.value, "note": a.note or "", "at": now()}
    if a.persona:
        item["persona"] = a.persona
    data["items"].append(item)
    write_json(book_dir / READER_DATA, data)
    print(f"OK 第{a.ch}章 {a.source}{'·' + a.persona if a.persona else ''} {a.kind}={a.value}")


def cmd_team(a):
    book_dir = Path(a.book_dir)
    d = ensure_m3_fields(load(book_dir))
    if a.action == "list":
        for pos in TEAM_POSITIONS:
            print(f"{pos}: {d['team'].get(pos) or '（未认领，个人模式下由作者兼任）'}")
        return
    if a.position not in TEAM_POSITIONS:
        die(f"位置只能是 {'/'.join(TEAM_POSITIONS)}")
    d["team"][a.position] = a.name
    save(book_dir, d)
    print(f"OK {a.position} 由 {a.name} 认领")


def sustain_lines(book_dir: Path, d: dict) -> list:
    """存稿线与倦怠信号（M3-7）。"""
    out = []
    done = [c for c in d.get("chapters", []) if c.get("status") == "done"]
    pub = d.get("published_upto", 0)
    if pub:
        buffer = sum(1 for c in done if c["seq"] > pub)
        cfg = load_cfg(book_dir)
        line = f"存稿: {buffer} 章（已发布到第 {pub} 章，存稿线 {cfg['buffer_min']}）"
        if buffer < cfg["buffer_min"]:
            line += "  ⚠ 低于存稿线，建议进入保更模式（见 sustain.md）"
        out.append(line)
    timed = [c for c in done if c.get("drafting_at") and c.get("done_at")]
    if len(timed) >= 6:
        def hours(c):
            t0 = datetime.datetime.fromisoformat(c["drafting_at"])
            t1 = datetime.datetime.fromisoformat(c["done_at"])
            return max((t1 - t0).total_seconds() / 3600, 0.0)
        recent, before = timed[-3:], timed[-6:-3]
        h_r, h_b = sum(map(hours, recent)) / 3, sum(map(hours, before)) / 3
        r_r = sum(c.get("retry", 0) for c in recent) / 3
        r_b = sum(c.get("retry", 0) for c in before) / 3
        if h_b > 0 and h_r > h_b * 1.5 and r_r >= r_b:
            out.append(f"⚠ 倦怠信号：近 3 章平均耗时 {h_r:.1f} 小时（此前 {h_b:.1f}），返工没有减少。建议调节奏（见 sustain.md）")
    return out


def cmd_report(a):
    book_dir = Path(a.book_dir)
    d = ensure_m3_fields(load(book_dir))
    items = ledger(book_dir, PROMISES)["items"]
    know = ledger(book_dir, KNOWLEDGE)["items"]
    events = read_json(book_dir / EVENTS, {"events": []}).get("events", [])
    fb = ledger(book_dir, READER_DATA)["items"]
    cur = current_chapter(d)
    if a.kind == "unit":
        u = open_unit(d)
        if not u:
            die("没有进行中的单元（unit open）")
        lo, hi, title = u["start"], cur, f"单元 {u['id']} 复盘（第{u['start']}–{cur}章）"
        target = f"{REVIEW_DIR}/单元-{u['id']}.md"
        human = ("暂定决策", "故事审", "下一单元")
    elif a.kind == "volume":
        v = open_volume(d)
        if not v:
            die("没有进行中的卷")
        lo, hi, title = v["start"], v.get("end") or cur, f"第{v['n']}卷 卷复盘（第{v['start']}–{v.get('end') or cur}章）"
        target = f"{REVIEW_DIR}/卷{v['n']}.md"
        human = VOLUME_REVIEW_REQUIRED
    else:
        lo, hi, title = 1, cur, "收束清单"
        target, human = FINALE_LIST, FINALE_REQUIRED
    chs = range_chapters(d, lo, hi)
    out = [f"# {title}", "", f"> 由 `ncc_state.py report {a.kind}` 从台账生成的数据与要回答的问题；"
           "回答与决定写在本区块外对应的小节里（区块会随数据刷新）。", ""]

    def plist(ps, empty="（无）"):
        return [f"- {p['id']} [{p['type']}] 强度{p.get('strength')} {p['status']}：{p['content']}" for p in ps] or [f"- {empty}"]

    open_reader = [p for p in items if p.get("type") not in ("期权", "暂定决策") and p.get("status") in OPEN_STATES]
    pending = [p for p in items if p.get("type") == "暂定决策" and p.get("status") in OPEN_STATES]
    overdue = [p for p in items if promise_overdue(p, cur)]

    if a.kind in ("unit", "volume"):
        out += ["## 本段章节", ""]
        for c in chs:
            sc = c.get("scenes") or {}
            m = mood_of(c) if c.get("mood") else None
            out.append(f"- 第{c['seq']}章 {c['status']}" + ("（关键章，作者选定 " + str((c.get("selection") or {}).get("version", "—")) + "）" if c.get("key") else "")
                       + f"｜故事审：{sc.get('review', '—')}（{sc.get('by', '—')}）"
                       + (f"｜{m['tension']}{'、'.join(m.get('colors', []))}" if m else "")
                       + (f"｜钩子 {c['hook']['type']}/{c['hook']['intensity']}" if c.get("hook") else ""))
        out += ["", "## 暂定决策（请作者逐条确认或推翻）", ""] + plist(pending)
        by_editor = [c["seq"] for c in chs if (c.get("scenes") or {}).get("by") == "story-editor"]
        out += ["", "## 故事审回顾", "", f"- 由发展编辑放行、待作者复看的章：{by_editor or '（无）'}",
                "- 发展编辑的单元问题（待填）：最打动人的是什么？主角的选择够不够难？哪个配角比主角更鲜活？哪条线该删？主角失去了什么？主题之问从哪个角度被考验？"]
        made = [p for p in items if lo <= (p.get("created_ch") or -1) <= hi]
        paid = [p for p in items if lo <= (p.get("resolved_ch") or -1) <= hi]
        water = [c["seq"] for c in chs if c.get("status") == "done" and not chapter_touches(items, c["seq"])]
        lost = [e for e in events if e.get("attribute") == "失去" and lo <= (e.get("chapter") or -1) <= hi]
        out += ["", "## 承诺", "", f"- 本段建立 {len(made)} 条，兑现或作废 {len(paid)} 条；水章：{water or '（无）'}", "- 逾期："] + plist(overdue)
        out += ["", "## 失去", ""] + ([f"- 第{e.get('chapter')}章 {e.get('entity')}：{e.get('old')} → {e.get('new')}" for e in lost] or ["- （本段主角没有失去任何东西——检查是否只有爽没有痛）"])
        seg_fb = [f for f in fb if lo <= f.get("ch", -1) <= hi]
        out += ["", "## 读者数据", ""] + ([f"- 第{f['ch']}章 [{f['source']}] {f['kind']}={f['value']} {f.get('note', '')}" for f in seg_fb] or ["- （无回流数据）"])
        sim = {}
        for f in seg_fb:
            if f["source"] == "模拟" and f["kind"] == "追读":
                v = f"{f['value']}（{f['persona']}）" if f.get("persona") else str(f["value"])
                sim[f["ch"]] = f"{sim[f['ch']]}／{v}" if f["ch"] in sim else v
        real = {f["ch"]: f["value"] for f in seg_fb if f["source"] == "真实" and f["kind"] == "追读"}
        both = sorted(set(sim) & set(real))
        if both:
            out += ["", "**模拟读者校准**（同一章的模拟追读 vs 真实追读）", ""]
            out += [f"- 第{ch}章：模拟 {sim[ch]}｜真实 {real[ch]}" for ch in both]
            out += ["- 偏差规律（待填）：模拟读者在哪类章节高估或低估？写进 reader 的校准备注"]
    if a.kind in ("unit", "volume"):
        pend_rows = [(c["seq"], r) for c in chs for r in (knowledge_rows(book_dir, c["seq"]) or []) if len(r) >= 5 and r[4] == "待核"]
        out += ["", "## 待核知识点（请作者核实，或维持宁缺写法）", ""]
        out += [f"- 第{seq}章 {r[0]}（{r[1]}）：{r[2]}" for seq, r in pend_rows] or ["- （无）"]
        odd = [c for c in chs if (c.get("length") or {}).get("accepted") is not None]
        out += ["", "## 篇幅（字数不在区间、已收下的章；按推荐先收的请作者确认）", ""]
        out += [f"- 第{c['seq']}章 {c['length']['accepted']} 字（区间 {c['length']['band'][0]}–{c['length']['band'][1]}）"
                + ("，按推荐先收，待你确认" if c["length"].get("by") == "recommendation" else "，你已收下")
                + (f"：{c['length']['note']}" if c["length"].get("note") else "") for c in odd] or ["- （无）"]
        mats, used = material_cards(book_dir), material_usage(book_dir)
        seg = {r: [s for s in seqs if lo <= s <= hi] for r, seqs in used.items()}
        seg = {r: s for r, s in seg.items() if s}
        idle = [r for r in mats if r not in used]
        out += ["", "## 素材", ""]
        out.append("- 本段用到：" + "；".join(f"{r}（第{'、'.join(map(str, s))}章）" for r, s in seg.items())
                   if seg else "- 本段场景卡没有引用素材")
        out.append(f"- 素材库共 {len(mats)} 张，从未用过 {len(idle)} 张" + (f"：{'、'.join(idle[:10])}" if idle else "")
                   + "（outliner 排下一单元时可以挑；作者这段时间新看到、新想到的，随时 material add）")
    if a.kind == "unit":
        mem = consolidate_lines(book_dir, d)
        since = u.get("opened_at", "")
        ops = [r for r in read_jsonl(book_dir / MEMORY_LOG) if r.get("at", "") >= since]
        out += ["", "## 记忆与交接（关单元时自动归档久未出现的；其余由经理按底稿合并、晋升）", ""]
        out.append(f"- 本单元记忆变动 {len(ops)} 次：" + ("、".join(f"{k} {v}" for k, v in _count(r['op'] for r in ops).items()) if ops else "（无）"))
        out += mem or ["- 记忆不用整理"]
        left = [e for e in handoff_open(book_dir) if e["kind"] == "决定"]
        out += [f"- 还没落进源头的决定：{e['id']} {e['text']}" for e in left] or ["- 作者的决定都已落进源头"]
        used = {}
        for c in chs:
            card = scene_path(book_dir, c["seq"])
            for t in technique_refs(card.read_text("utf-8")) if card.exists() else []:
                used.setdefault(t, []).append(c["seq"])
        out += ["", "## 技法（场景卡引用的技法卡；关单元时自动结算结果）", ""]
        out += [f"- {t}：第{'、'.join(map(str, v))}章" for t, v in used.items()] or ["- 本单元场景卡没有引用技法卡"]
        out += ["", "## 对标基线（只作参照，不作判据）", ""] + compare_lines(book_dir, d, lo, hi)
        out += ["", "## 下一单元", "", "- 候选走向 2–3 个（outliner 从承诺账、读者此刻、书魂推出；标推荐与理由，至少一个非主流）（待填）",
                "- 下一单元的关键章（系统先按规则推荐，作者确认）（待填）"]
    if a.kind == "volume":
        soul = d.get("soul", {})
        out += ["", "## 承诺盘点", "", "开放中的读者向承诺："] + plist(open_reader)
        out += ["", "## 书魂检验", "", f"- 书魂状态：{soul.get('status')}" + (f"（最晚 {soul.get('deadline')}）" if soul.get("status") == "暂定" else ""),
                "- 本卷从哪个角度考验了主题之问？主角的答案变了吗？（待填）"]
        out += ["", "## 数据归因", "", "- 追读与弃读的变化落在哪几章、对应哪类写法（scout 与 pulse 填）（待填）"]
        out += ["", "## 变更提议", "", "- 需要调整的骨架（L1）条目，按 architecture.md 的变更提议格式（待填）", "- 下一卷走向候选 2–3 个，标推荐（待填）"]
        root = book_root(book_dir)
        props = [p for p in proposals(root).values() if p["state"] not in ("已生效", "作者否决", "已撤回")]
        out += ["", "## 进化（规则级改动：先过锚定章回归，再由作者确认）", ""]
        out += [f"- {p['id']} [{p['tier']}] {p['state']}：{p['key']} ← {p['raw']}（{p['why']}）" for p in props] or ["- 没有待定的进化提议"]
        out += [f"- 苗头：{key} ← {raw}：{why}（evolve scan --propose 记为提议）" for key, raw, why, _ in scan(root)
                if not any(p["key"] == key and p["raw"] == raw for p in proposals(root).values())]
        by_dom, pend = {}, {}
        for c in chs:
            for r in knowledge_rows(book_dir, c["seq"]) or []:
                if len(r) >= 5:
                    dom = normalize_domain(r[1]) or r[1]
                    by_dom[dom] = by_dom.get(dom, 0) + 1
                    if r[4] == "待核":
                        pend[dom] = pend.get(dom, 0) + 1
        slips = {}
        for f in fb:
            if f.get("kind") == "出戏" and lo <= f.get("ch", -1) <= hi:
                slips.setdefault(normalize_domain(str(f["value"])) or str(f["value"]), []).append(f"第{f['ch']}章 {f.get('note', '')}".strip())
        out += ["", "## 底蕴", "", f"- 一书一深学：{'、'.join(d.get('study', [])) or '（未选）'}"]
        out += [f"- {k}：知识点 {v} 条，待核 {pend.get(k, 0)} 条" + (f"；出戏 {len(slips[k])} 处" if k in slips else "")
                for k, v in sorted(by_dom.items(), key=lambda x: -x[1])] or ["- （本卷没有知识点清单）"]
        out += [f"- {k}（无知识点清单）：出戏 {len(v)} 处——{'；'.join(v)}" for k, v in slips.items() if k not in by_dom]
        out += ["- 补学清单（待填）：按 domains/reading-list.md 的「补学清单」，挑知识点最多或出戏最多的学科"]
    if a.kind == "finale":
        gaps = [k for k in know if k.get("unknown_to")]
        scenes_left = [p for p in items if p.get("type") == "名场面" and p.get("status") in OPEN_STATES]
        motifs = [p for p in items if p.get("type") == "母题" and p.get("status") in OPEN_STATES]
        out += ["## 承诺清算", "", "终局前必须兑现或交代的读者向承诺（期权除外）："] + plist(open_reader)
        out += ["", "未定的暂定决策："] + plist(pending)
        out += ["", "## 暗线收拢", "", "知情账里仍有人不知道的事（哪些要在终局揭开）："]
        out += [f"- {k['id']} {k['fact']}——{'、'.join(k['unknown_to'])} 还不知道" for k in gaps] or ["- （无）"]
        out += ["", "未兑现的名场面："] + plist(scenes_left) + ["", "核心意象的最后一次变化："] + plist(motifs)
        promo = []
        for role in memory_roles(book_dir):
            promo += [f"- {role} {i['id']}：{i['text']}（命中 {i.get('hits', 1)} 次）" for i in memory_items(book_dir, role)
                      if i.get("status") == "active" and i["kind"] not in MEMORY_CFG["once_ok"]
                      and i.get("hits", 1) >= MEMORY_CFG["promote_hits"] and not i.get("promoted_to")]
        out += ["", "## 跨书记忆候选（默认晋升，作者可以划掉；memory promote --role 角色）", ""] + (promo or ["- （无）"])
        out += ["", "## 书魂回答", "", f"- 主题之问：{d.get('soul', {}).get('question') or '（未填）'}",
                "- 终局给出的回答：主角答案的胜利、修正，还是胜利的代价？（待填）",
                "- 收束方案候选 2–3 个，标推荐（outliner 填）（待填）"]
    if a.write:
        skeleton = "\n\n".join(f"## {h}\n\n（待填）" for h in human) + "\n"
        write_block(book_dir / target, "\n".join(out), skeleton)
        print(f"OK 底稿已写进 {target} 的生成区块；回答与决定写在区块外的「{'」「'.join(human)}」各节")
        return
    print("\n".join(out))


def _card_field(text: str, names) -> str:
    for name in names:
        vals = [m.strip() for m in re.findall(rf"{name}[：:]\s*([^\n]+)", text)]
        if vals:
            return "；".join(vals[:2])
    return ""


def _cell(val) -> str:
    return str(val).replace("|", "｜").replace("\n", " ").strip()


def _sandbox_digest(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:16]


SANDBOX_SHA_RE = re.compile(r"\n?<!-- ncc:sandbox-sha ([0-9a-f]{16}) -->\s*$")
SANDBOX_STALE_NOTE = re.compile(r"^> ⚠ 底层台账或场景卡已变更[^\n]*\n\n", re.M)


def sandbox_lines(book_dir: Path, d: dict, lo: int = None, hi: int = None):
    u = open_unit(d)
    if lo is None:
        lo = u["start"] if u else (1 if d.get("stage") == "opening" else next_seq(d))
    if hi is None:
        if d.get("stage") == "opening" and not u:
            hi = max(3, lo + 2)
        else:
            reg_max = max([c["seq"] for c in d.get("chapters", []) if c["seq"] >= lo] or [0])
            hi = max(reg_max, lo + 9)
    if hi < lo:
        die("--to 不能小于 --from")
    label = f"单元 {u['id']}{'《' + u['title'] + '》' if u.get('title') else ''}" if (u and lo == u["start"]) else f"第{lo}–{hi}章"
    target = f"{SANDBOX_DIR}/单元-{u['id']}.md" if (u and lo == u["start"]) else f"{SANDBOX_DIR}/ch-{lo:04d}-{hi:04d}.md"
    items = ledger(book_dir, PROMISES)["items"]
    soul = d.get("soul") or {}
    out = [f"# 战前剧情沙盘：{label}（第{lo}–{hi}章）", "",
           "> 每一个剧情展开前先看本沙盘：同屏核对处境枷锁、明暗灰三线交织与爽点断章排布，把剧情优化好再正式开火动笔。", ""]

    out += ["## 一、战局压迫与推进锁", ""]
    pb = book_dir / TRACK_PLAYBOOK
    if pb.is_file():
        pb_txt = pb.read_text("utf-8")
        pb_lever = _card_field(pb_txt, ("核心爽感杠杆", "核心杠杆"))
        pb_poison = _card_field(pb_txt, ("剧毒红线", "死穴红线", "红线"))
        pb_extra = "｜".join(x for x in (f"杠杆：{pb_lever}" if pb_lever else "", f"红线：{pb_poison}" if pb_poison else "") if x)
        out.append(f"- 赛道白金母本：已挂载专属 `{TRACK_PLAYBOOK}`" + (f"（{pb_extra}）" if pb_extra else ""))
    else:
        out.append(f"- 赛道白金母本：通用五大母本底盘（提出想写细分赛道时可深挖生成 `{TRACK_PLAYBOOK}`）")
    out.append(f"- 悬顶倒计时锁：{u.get('countdown') if u and u.get('countdown') else '⚠ 未设置（建议 unit open --countdown 挂上时间死锁，防慢热散步）'}")
    out.append(f"- 10章跃迁台阶：{u.get('milestone') if u and u.get('milestone') else '⚠ 未设置（建议明确本轮结束主角跨上的可见新台阶）'}")
    mid_ch = (lo + hi) // 2 if (hi - lo + 1) >= 6 else None
    if mid_ch is not None:
        out.append(f"- 单元五拍中点锚：第 {mid_ch} 章（前半受压拿牌 → 中点摸清底牌转入主动设局反猎杀 → 至暗封路 → 掀桌收网＋开箱余波）")
    arc_info = f"{soul.get('arc') or '未定'}" + (f" · 当前刻度「{soul['arc_stage']}」" if soul.get("arc_stage") else "")
    arc_ch_info = f"，本轮显影章：第 {u['arc_ch']} 章" if (u and u.get("arc_ch")) else ""
    out.append(f"- 主角弧光坐标：{arc_info}{arc_ch_info}")
    pl = plight_lines(d)
    if pl:
        out += ["- 主角四维高压处境："] + [f"  {x}" for x in pl]
    else:
        out.append("- 主角四维高压处境：⚠ 未登记（建议用 `plight` 填清头顶恶规、身边暗箭、兜里短板、唯一生门）")

    out += ["", "## 二、明·暗·灰三线交织进度表", ""]
    active = [p for p in items if p.get("status") in OPEN_STATES and p.get("type") != "暂定决策"]
    unplanned_cool = []
    if active:
        out += ["| 编号 | 叙事线 | 类型／强度 | 明面伪装或内容 | 里层真相（写手包隔离） | 距上次触碰 | 本轮排布 |",
                "|---|---|---|---|---|---|---|"]
        for p in sorted(active, key=lambda x: ({"明线": 0, "暗线": 1, "灰线": 2}[infer_line(x)], -(x.get("strength") or 0))):
            line = infer_line(p)
            gap = max(lo - promise_last_touch(p, before_seq=lo), 0)
            planned = [seq for seq in range(lo, hi + 1)
                       if p.get("created_ch") == seq or p.get("resolved_ch") == seq
                       or any(e.get("ch") == seq for e in p.get("progress", []))
                       or (scene_path(book_dir, seq).is_file() and p["id"] in scene_path(book_dir, seq).read_text("utf-8"))
                       or ((book_dir / L("chapter_outlines") / f"ch-{seq:04d}.md").is_file()
                           and p["id"] in (book_dir / L("chapter_outlines") / f"ch-{seq:04d}.md").read_text("utf-8"))]
            warn = " ⚠暗香断档" if line in ("暗线", "灰线") and gap >= DARK_LINE_COOL and not planned else ""
            if warn:
                unplanned_cool.append((p, line, gap))
            cover = f"伪装：{p['surface_cover']}（{p['content']}）" if p.get("surface_cover") else p["content"]
            truth = p.get("true_meaning") or "—"
            plan_txt = "第" + "、".join(map(str, planned)) + "章" if planned else ("待织入！" if warn else "待排")
            out.append(f"| {_cell(p['id'])} | {_cell(line)} | {_cell(p['type'])}·{p.get('strength')} | {_cell(cover)} | {_cell(truth)} | {gap}章{warn} | {_cell(plan_txt)} |")
    else:
        out.append("（承诺台账暂无开放中的明暗灰线索，开战前请先用 `promise add --line 明线|暗线|灰线` 布线）")

    out += ["", "## 三、逐章爽点·波折·断章钩排布预览", "",
            "| 章号 | 定位 | 翻转与第一手受挫 | 承诺／爽点动作 | 二阶后果（新隐患） | 张力／情绪 | 章尾断章钩 |",
            "|---|---|---|---|---|---|---|"]
    chs_by_seq = {c["seq"]: c for c in d.get("chapters", [])}
    blank_chs, tension_seq, hook_seq, desire_seq, weave_chs, resolved_old, converge_chs = [], [], [], [], [], [], []
    for seq in range(lo, hi + 1):
        c = chs_by_seq.get(seq, {})
        role_tags = []
        if c.get("key", seq <= 3):
            role_tags.append("关键章")
        if u and u.get("arc_ch") == seq:
            role_tags.append("弧光章")
        if mid_ch == seq:
            role_tags.append("中点反守为攻")
        card_p = scene_path(book_dir, seq)
        outline_p = book_dir / L("chapter_outlines") / f"ch-{seq:04d}.md"
        card_txt = card_p.read_text("utf-8") if card_p.is_file() else ""
        out_txt = outline_p.read_text("utf-8") if outline_p.is_file() else ""
        turn = _card_field(card_txt, ("翻转",)) or _card_field(out_txt, ("功能", "must-keep")) or "（待排场景卡）"
        setback = _card_field(card_txt, ("第一手受挫", "受挫"))
        if setback:
            turn = f"{turn}｜受挫：{setback}"
        aftermath = _card_field(card_txt, ("二阶后果", "新隐患", "新麻烦")) or "—"
        touches = chapter_touches(items, seq)
        rev_mark = set(re.findall(r"\b[A-Z]{1,4}-\d{4}\b", " ".join(re.findall(r"(?:伏笔回收|回收伏笔|揭晓伏笔|兑现承诺|本场兑现)[：:][^\n]*", card_txt + "\n" + out_txt))))
        for p in items:
            if (p.get("resolved_ch") == seq or p["id"] in rev_mark) and p.get("type") in ("伏笔", "悬念") and (as_int(p.get("created_ch")) or seq) < seq:
                resolved_old.append((seq, p["id"]))
        ref_ids = [p["id"] for p in active if (p["id"] in card_txt or p["id"] in out_txt) and p["id"] not in {i for i, _ in touches}]
        paid_ids = {p["id"] for p in items if p.get("resolved_ch") == seq} | rev_mark
        if len(paid_ids) >= 2:
            converge_chs.append(seq)
        touch_parts = [f"{i}:{'回收' if i in rev_mark else k}" for i, k in touches] + [f"{i}:{'计划回收' if i in rev_mark else '计划'}" for i in ref_ids]
        lines_hit = {infer_line(p) for p in items if p["id"] in {i for i, _ in touches} | set(ref_ids)}
        if "明线" in lines_hit and (lines_hit & {"暗线", "灰线"}):
            weave_chs.append(seq)
        for p in items:
            if p.get("resolved_ch") == seq and p.get("desire"):
                desire_seq.append(str(p["desire"]))
        m = mood_of(c) if c.get("mood") else None
        mood_txt = (f"{m['tension']}" + (f"（{'、'.join(m['colors'])}）" if m.get("colors") else "")) if m else (_card_field(card_txt or out_txt, ("情感", "情绪点")) or "—")
        if m:
            tension_seq.append((seq, m["tension"]))
        elif "压" in mood_txt and "放" not in mood_txt and "爽" not in mood_txt and "燃" not in mood_txt:
            tension_seq.append((seq, "压"))
        else:
            tension_seq.append((seq, ""))
        hk = c.get("hook") or {}
        hook_txt = f"{hk['type']}/{hk['intensity']}" if hk.get("type") else (_card_field(card_txt or out_txt, ("章尾断章", "钩子")) or "—")
        if hk.get("type"):
            hook_seq.append(hk["type"])
        else:
            hm = re.match(r"([^，,：:｜|/（(\s—\-]+)", hook_txt)
            if hm and hm.group(1) != "—":
                hook_seq.append(hm.group(1))
        if turn == "（待排场景卡）" and not touch_parts:
            blank_chs.append(seq)
        out.append(f"| 第{seq}章 | {'+'.join(role_tags) or '常规'} | {_cell(turn)} | {_cell('、'.join(touch_parts) or '—')} | {_cell(aftermath)} | {_cell(mood_txt)} | {_cell(hook_txt)} |")

    out += ["", "## 四、白金战前体检（细节后台自修，主线冲突给 A/B 选项呈出品人）", ""]
    findings = []
    if blank_chs:
        findings.append(f"- **[后台补齐项] 推进排布待补**：第 {'、'.join(map(str, blank_chs))} 章尚未排入场景翻转与承诺动作，按 3·10·30 三级火箭与九紧一松（收尾排 1 章开箱余波章）补齐。")
    max_press, cur_run = [], []
    for seq, t in tension_seq:
        if t == "压":
            cur_run.append(seq)
            if len(cur_run) > len(max_press):
                max_press = list(cur_run)
        else:
            cur_run = []
    if len(max_press) >= 3:
        findings.append(f"- **[呈出品人 A/B 拍板项] 连压憋屈预警**：第 {max_press[0]}–{max_press[-1]} 章连续 {len(max_press)} 章纯蓄压，触碰「受挫不受辱、大死局每 2 章必赢一手局部筹码」红线，请给 A/B 两个插爽方案供出品人二选一！")
    open_dark_only = [p for p in active if infer_line(p) == "暗线"]
    if len(open_dark_only) > 5:
        findings.append(f"- **[后台锁池项] 暗线池超载预警**：当前同时活跃暗线 {len(open_dark_only)} 条 > 封顶 5 条（1全书终极＋2本卷黑手＋2短线惊雷），暂停新挖暗坑，优先回收旧伏笔。")
    if hi - lo + 1 >= 8 and not resolved_old and [p for p in active if p.get("type") in ("伏笔", "悬念") and (as_int(p.get("created_ch")) or hi) < hi]:
        findings.append("- **[呈出品人 A/B 拍板项] 十章一响提醒**：本轮 8–12 章单元尚未安排旧伏笔炸响回收，建议挑 1 条中短线惊雷在本轮揭晓兑现以拉满头皮发麻正反馈。")
    dark_open = [p for p in active if infer_line(p) in ("暗线", "灰线")]
    if dark_open and not weave_chs:
        findings.append(f"- **[后台自修项] 明暗零交织预警**：当前有 {len(dark_open)} 条开放暗线/灰线（如 {dark_open[0]['id']}），`outliner` 先行挑 1–2 章用明面伪装一石二鸟自然带出。")
    elif weave_chs:
        findings.append(f"- **明暗交织达标**：第 {'、'.join(map(str, weave_chs))} 章已实现明线与暗/灰线同章交织。")
    if converge_chs:
        findings.append(f"- **多线雪崩合拢达标**：第 {'、'.join(map(str, converge_chs))} 章同场引爆兑现 ≥2 条线索（Sanderlanche 合拢）。")
    if unplanned_cool:
        findings.append("- **[后台自修项] 暗香断档报警**：" + "；".join(f"{p['id']}（已沉底 {gap} 章，本轮尚未排入）" for p, _, gap in unplanned_cool[:3]) + "，由 `outliner` 顺手织入明面痕迹后再呈沙盘。")
    dup_hooks = [h for h in dict.fromkeys(hook_seq) if hook_seq.count(h) >= 3]
    if dup_hooks:
        findings.append(f"- **[后台自修项] 断章钩撞车预警**：钩型「{'、'.join(dup_hooks)}」在本轮出现 ≥3 次，`outliner` 先行在五类白金钩型间轮换。")
    dup_desires = [x for x in dict.fromkeys(desire_seq) if desire_seq.count(x) >= 3]
    if dup_desires:
        findings.append(f"- **[后台自修项] 同型爽点疲劳预警**：爽感谱系第 {'、'.join(dup_desires)} 型本轮兑现 ≥3 次，建议换谱系交叉调剂。")
    if not pl or not (u and u.get("countdown")):
        findings.append("- **[战前引导项] 高压处境锁待加固**：开战前建议补全 `plight` 四维挤压账与单元 `--countdown` 悬顶倒计时（旧书不阻断续写）。")
    out += findings or ["- 战前体检全部绿灯：三线交织、十章一响、节奏呼吸与处境枷锁均已就绪，可呈出品人一键开战！"]
    return out, target


def cmd_sandbox(a):
    """每个剧情展开前的战前沙盘预览：明暗线交织进度与爽点排布。"""
    book_dir = Path(a.book_dir)
    d = ensure_m3_fields(load(book_dir))
    lines, target = sandbox_lines(book_dir, d, getattr(a, "from_ch", None), getattr(a, "to_ch", None))
    if a.write:
        dest = book_dir / target
        pure_body = "\n".join(lines).rstrip()
        new_sha = _sandbox_digest(pure_body)
        stale_prefix = ""
        skeleton = "## 出品人战前调优拍板\n\n- 战前结论：确认开战／调整后开战（待填）\n- 剧情优化指令：（待填：如哪章提前兑现小爽、哪条暗线换个伪装道具；经理回写台账或场景卡后再重刷本沙盘核验）\n"
        if dest.exists():
            old_raw = dest.read_text("utf-8")
            if GEN_BEGIN not in old_raw or not GEN_RE.search(old_raw):
                if not getattr(a, "force", False):
                    die(f"{target} 为无生成区块标记的手写文件，防丢稿拒绝覆盖；请先备份移走或加 --force")
            else:
                inner = GEN_RE.search(old_raw).group(0)
                inner = re.sub(r"^.*?\n", "", inner, count=1)
                inner = re.sub(r"\n[^\n]*$", "", inner, count=1)
                sm = SANDBOX_SHA_RE.search(inner)
                old_sha = sm.group(1) if sm else None
                clean_old = SANDBOX_STALE_NOTE.sub("", SANDBOX_SHA_RE.sub("", inner)).rstrip()
                if old_sha and _sandbox_digest(clean_old) != old_sha and not getattr(a, "force", False):
                    die(f"{target} 的生成区块被手工修改过，防丢稿拒绝覆盖；请将修改移入区块外「出品人战前调优拍板」后加 --force 重刷")
                outside = outside_block(old_raw).strip()
                if old_sha and old_sha != new_sha and outside and outside != skeleton.strip():
                    stale_prefix = f"> ⚠ 底层台账或场景卡已变更（快照 {old_sha} → {new_sha}），请复核下方「出品人战前调优拍板」是否仍适用。\n\n"
        stamped = f"{stale_prefix}{pure_body}\n<!-- ncc:sandbox-sha {new_sha} -->"
        write_block(dest, stamped, skeleton)
        print(f"OK 战前沙盘已写入 {target}（快照 {new_sha}）；请呈出品人预览优化后再正式开战写章")
        return
    print("\n".join(lines))
