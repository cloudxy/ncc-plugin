"""书与闸门：建书、迁移、状态、闸门、书魂与契约、章节登记与定稿。"""

import re
import sys
from pathlib import Path
from .core import (ARCS, CHAPTER_STATES, CHARACTER_REQUIRED, COLORS, CRAFT_EXCERPT, CRAFT_LIBRARY, DIRS, EVENTS, FACTS, FINALE_LIST, FINALE_REQUIRED, GATES, HAN, KNOWLEDGE, L, LEGACY_MOOD, LEVELS, MODES, NON_READER_TYPES, OLD_FORESHADOW, OPEN_STATES, PLANNED_GATES, PROMISES, READER_DATA, REVIEW_DIR, SCENE_DIR, SCHEMA, SEEDS, SIGNING_POINTS, STYLE_ANCHOR, STYLE_FP, TENSION, VOLUME_REVIEW_REQUIRED, as_int, chapter_file, copy_template, current_chapter, die, ensure_m3_fields, find_ch, han_words, ledger, length_band, load, load_cfg, next_id, now, open_unit, open_volume, parse_window, read_json, save, section, sha16, split_names, write_json)
from .ledgers import chapter_touches, promise_due_soon, promise_overdue, promise_summary
from .materials import material_cards, material_usage
from .scenes import knowledge_ready, knowledge_rows, scene_ready
from .learning import craft_entries, craft_pending, pref_note_book
from .views import migrate_layout
from .loops import has_sections, sustain_lines


def new_book(title, genre, chapters, level, mode):
    return {
        "schema_version": SCHEMA,
        "title": title,
        "genre_tags": genre,
        "premise": "",
        "target": {"chapters": chapters, "words_per_chapter": [3000, 5000]},
        "stage": "founding",
        "mode": mode,
        "era": "",
        "study": [],
        "writing_mode": "serial",
        "experience_level": level,
        "soul": {"question": "", "answer": "", "injustice": "", "ending": "",
                 "status": "未填", "deadline": "", "arc": ""},
        "contract": {"main": "", "extras": [], "poison": [], "signing": {}, "audience": ""},
        "gates": {k: {"status": "waiting"} for k in
                  ("soul", "settings_frozen", "outline_frozen", "opening_accepted")},
        "chapters": [],
        "units": [],
        "volumes": [{"n": 1, "start": 1, "end": None, "status": "open"}],
        "published_upto": 0,
        "team": {},
        "host_spawn": False,
        "updated_at": now(),
    }


def init_ledgers(book_dir: Path):
    for rel, empty in ((PROMISES, {"items": []}), (KNOWLEDGE, {"items": []}),
                       (FACTS, {"facts": {}}), (EVENTS, {"events": []}), (READER_DATA, {"items": []})):
        p = book_dir / rel
        if not p.exists():
            write_json(p, empty)
    (book_dir / SCENE_DIR).mkdir(parents=True, exist_ok=True)
    (book_dir / REVIEW_DIR).mkdir(parents=True, exist_ok=True)
    copy_template("author-seeds.md", book_dir / SEEDS)


def cmd_init(a):
    book_dir = Path(a.book_dir)
    if (book_dir / "book.json").exists():
        die(f"已存在: {book_dir / 'book.json'}（不覆盖）")
    if a.level not in LEVELS:
        die(f"--level 只能是 {'/'.join(LEVELS)}")
    if a.mode not in MODES:
        die(f"--mode 只能是 {'/'.join(MODES)}")
    for sub in DIRS:
        (book_dir / sub).mkdir(parents=True, exist_ok=True)
    genre = [g.strip() for g in (a.genre or "").split(",") if g.strip()]
    save(book_dir, new_book(a.title, genre, a.chapters, a.level, a.mode))
    init_ledgers(book_dir)
    pref_note_book(book_dir, a.title, genre)
    print(f"OK init {book_dir} stage=founding level={a.level} mode={a.mode}")


def cmd_migrate(a):
    book_dir = Path(a.book_dir)
    p = book_dir / "book.json"
    if not p.exists():
        die(f"book.json 不存在: {p}")
    d = read_json(p, {})
    ver = d.get("schema_version", 1)
    if ver >= SCHEMA:
        print(f"已是 schema {SCHEMA}，无需迁移")
        return
    if ver >= 2:
        moved = migrate_layout(book_dir, d)
        d["schema_version"] = SCHEMA
        ensure_m3_fields(d)
        save(book_dir, d)
        init_ledgers(book_dir)
        print(f"OK migrate schema {ver} → {SCHEMA}；按七律归位 {len(moved)} 处" + ("：" + "；".join(moved) if moved else "")
              + "。旧的 author-intent.md、current-focus.md 若是手写的，已移到 .ncc/迁移备份/，现在由 render 生成")
        return
    stage_map = {"ideation": "founding", "golden": "opening"}
    d["stage"] = stage_map.get(d.get("stage"), d.get("stage"))
    gates = d.get("gates", {})
    if "golden_accepted" in gates:
        gates["opening_accepted"] = gates.pop("golden_accepted")
    gates.setdefault("opening_accepted", {"status": "waiting"})
    gates.setdefault("soul", {"status": "waiting", "note": "v0.1 迁移：开书时无书魂闸，需补填书魂与类型契约"})
    d["gates"] = gates
    d.pop("foreshadows", None)
    fresh = new_book("", [], 0, "熟手", "建筑师")
    d.setdefault("experience_level", "熟手")
    d.setdefault("mode", "建筑师")           # v0.1 的流程就是建筑师模式
    d.setdefault("soul", fresh["soul"])
    d.setdefault("contract", fresh["contract"])
    moved = migrate_layout(book_dir, d)
    d["schema_version"] = SCHEMA
    ensure_m3_fields(d)
    save(book_dir, d)

    migrated = 0
    old = book_dir / OLD_FORESHADOW
    if old.exists() and not (book_dir / PROMISES).exists():
        raw = read_json(old, [])
        rows = raw if isinstance(raw, list) else raw.get("items", [])
        status_map = {"planned": "开放", "已回收": "已兑现", "超期未收": "开放"}
        items = []
        for r in rows:
            win = str(r.get("预计回收窗口", ""))
            items.append({
                "id": r.get("id") or next_id(items, "FS"),
                "type": "伏笔", "content": r.get("content", ""), "strength": 3,
                "created_ch": as_int(r.get("预计埋设章")),
                "window": parse_window(win) if re.search(r"\d+\s*[-~～至]\s*\d+", win) else None,
                "deadline": None, "status": status_map.get(r.get("status"), "开放"),
                "progress": [], "resolved_ch": None, "note": "v0.1 伏笔台账迁移",
            })
        write_json(book_dir / PROMISES, {"items": items})
        migrated = len(items)
    init_ledgers(book_dir)
    print(f"OK migrate → schema {SCHEMA}；stage={d['stage']}；mode={d['mode']}；伏笔迁入承诺台账 {migrated} 条"
          + ("（原伏笔台账.json 保留未删）" if migrated else "") + (f"；按七律归位 {len(moved)} 处" if moved else ""))


def cmd_status(a):
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    chs = d.get("chapters", [])
    done = [c for c in chs if c["status"] == "done"]
    soul, ct = d.get("soul", {}), d.get("contract", {})
    print(f"书: {d.get('title')}  标签: {','.join(d.get('genre_tags', []))}  "
          f"引导档位: {d.get('experience_level')}  写作模式: {d.get('mode')}")
    print(f"阶段: {d.get('stage')}  更新方式: {d.get('writing_mode')}")
    print(f"书魂: {soul.get('status')}" + (f"（最晚 {soul.get('deadline')} 定下）" if soul.get("status") == "暂定" else "")
          + f"  主角弧光: {soul.get('arc') or '未定'}  主契约: {ct.get('main') or '未填'}"
          + f"  签约点: {len(ct.get('signing', {}))}/{len(SIGNING_POINTS)}")
    for g, v in d.get("gates", {}).items():
        extra = f" @ {v.get('at')} 「{v.get('quote')}」" if v.get("status") not in ("waiting", None) else ""
        print(f"闸门 {g}: {v.get('status')}{extra}" + (f"  ({v['note']})" if v.get("note") else ""))
    print(f"章节: {len(done)}/{len(chs)} done")
    for c in chs:
        if c["status"] != "done":
            why = scene_ready(book_dir, c)
            print(f"  断点: ch{c['seq']} status={c['status']} retry={c.get('retry', 0)}"
                  + ("（关键章）" if c.get("key") else "") + (f"  场景卡: {why}" if why else "  场景卡: 已过故事审"))
            break
    s = promise_summary(book_dir, d)
    print(f"承诺: 开放{s['open']} 已兑现{s['resolved']} 作废{s['dropped']} 逾期{s['overdue']} "
          f"期权{s['options']} 母题{s['motifs']} 暂定决策{s['pending_decisions']}")
    items = ledger(book_dir, PROMISES)["items"]
    cur = current_chapter(d)
    for p in items:
        if promise_overdue(p, cur):
            print(f"  逾期: {p['id']} [{p['type']}] {p['content']}")
        elif promise_due_soon(p, cur):
            print(f"  将到期: {p['id']} 暂定决策「{p['content']}」最晚第 {p['deadline']} 章")
        elif p.get("type") == "暂定决策" and p.get("status") in OPEN_STATES and as_int(p.get("deadline")) is None:
            print(f"  暂定: {p['id']}「{p['content']}」最晚 {p['deadline']}")
    stale = [c["seq"] for c in done
             if (c.get("review") or {}).get("sha") and c.get("sha") and c["review"]["sha"] != c["sha"]]
    if stale:
        print(f"警告: 以下章正文已变更但未复评（评审作废）: {stale}")
    water = [c["seq"] for c in done if not chapter_touches(items, c["seq"])]
    if water:
        print(f"警告: 以下已完成章未建立、推进或兑现任何承诺（水章）: {water}")
    ensure_m3_fields(d)
    u, v = open_unit(d), open_volume(d)
    print(f"卷: 第{v['n']}卷（{v['status']}，自第{v['start']}章）" if v else "卷: 无进行中的卷",
          f"  单元: {u['id']}（自第{u['start']}章）" if u else "  单元: 无进行中的单元")
    for line in sustain_lines(book_dir, d):
        print(line)
    if d.get("team"):
        print("团队: " + "，".join(f"{k}={v}" for k, v in d["team"].items()))
    pending_k = 0
    for c in chs:
        rows = knowledge_rows(book_dir, c["seq"]) or []
        pending_k += sum(1 for r in rows if len(r) >= 5 and r[4] == "待核")
    print(f"底蕴: 时代背景 {d.get('era') or '未设'}  一书一深学 {'、'.join(d.get('study', [])) or '未选'}  待核知识点 {pending_k}")
    st = d.get("style") or {}
    print(f"文风指纹: {st.get('source')}（{st.get('han')} 字）" if st else "文风指纹: 未生成（style --sample 旧文，或第 1 章定稿后 --from-chapters 1）")
    mats = material_cards(book_dir)
    if mats:
        own = sum(1 for k in mats if k.startswith("M-"))
        print(f"素材: {len(mats)} 张（本书 {own}、跨书 {len(mats) - own}），场景卡已引用 "
              f"{len([k for k in mats if k in material_usage(book_dir)])} 张")
    print(f"更新于: {d.get('updated_at')}")


def cmd_next(a):
    d = load(Path(a.book_dir))
    for c in d.get("chapters", []):
        if c["status"] != "done":
            print(c["seq"])
            return
    print("NONE")
    sys.exit(1)


def lexicon_count(book_dir: Path) -> int:
    p = book_dir / L("lexicon")
    if not p.exists():
        return 0
    rows = 0
    for line in p.read_text("utf-8").splitlines():
        s = line.strip()
        if s.startswith("|") and not set(s) <= {"|", "-", " ", ":"} and "首现章计划" not in s:
            rows += 1
    return rows


def nonempty(book_dir: Path, rel: str) -> bool:
    p = book_dir / rel
    return p.exists() and bool(p.read_text("utf-8").strip())


def hard_passed(c: dict) -> bool:
    rev = c.get("review") or {}
    if "hard" in rev:
        return rev["hard"] == "pass"
    return (rev.get("score") or 0) >= 70     # v0.1 旧评审兼容


def gate_check(book_dir: Path, name: str, d: dict) -> list:
    problems = []
    mode = d.get("mode", "混合")
    if name == "soul":
        soul, ct = d.get("soul", {}), d.get("contract", {})
        labels = {"question": "主题之问", "answer": "主角的答案", "injustice": "世界的不公", "ending": "终局的回答"}
        for k, label in labels.items():
            if not soul.get(k, "").strip():
                problems.append(f"书魂缺「{label}」（可写候选并标暂定，见 guidance.md）")
        if soul.get("status") not in ("暂定", "确定"):
            problems.append("书魂状态未标暂定或确定")
        elif soul.get("status") == "暂定" and not soul.get("deadline"):
            problems.append("书魂为暂定，但没写最晚决定点（D7：最晚第一卷卷复盘）")
        if not ct.get("main"):
            problems.append("类型契约缺主契约")
        if not ct.get("poison"):
            problems.append("类型契约缺毒点清单")
        if d.get("experience_level") not in LEVELS:
            problems.append("未设引导档位（新手/熟手/老手）")
        n = craft_pending(book_dir, d)
        if n and not (book_dir / CRAFT_EXCERPT).exists():
            problems.append(f"技艺库里有别的书的 {n} 条经验，开书前先读（ncc_state.py craft read，M6-4）")
    elif name == "settings":
        for rel in (L("bible"), L("power"), L("lexicon")):
            if not nonempty(book_dir, rel):
                problems.append(f"缺设定文件或为空: {rel}")
        n = lexicon_count(book_dir)
        if n < 30:
            problems.append(f"设定词典条目 {n} < 30")
        hb = book_dir / L("power")
        if hb.exists() and "量纲" not in hb.read_text("utf-8"):
            problems.append("力量体系未含量纲定义")
        bible = book_dir / L("bible")
        if bible.exists() and not section(bible.read_text("utf-8"), "社会洞察"):
            problems.append("世界观圣经缺「社会洞察」一节或为空（看似不合理却存在的规矩：谁受益、谁受害、主角在哪，"
                            "对应书魂里世界的不公哪一面，见 worldbuilding.md；确实用不上就写一行理由）")
        cards = [p for p in (book_dir / L("characters")).glob("*.md")
                 if all(f in p.read_text("utf-8") for f in CHARACTER_REQUIRED)]
        if not cards:
            problems.append(f"没有一张完整的人物卡（须含 {'、'.join(CHARACTER_REQUIRED)}，见 character.md）")
        if d.get("soul", {}).get("arc") not in ARCS:
            problems.append("未选主角弧光类型（正向/负向/平弧，soul --arc）")
    elif name == "outline":
        if not nonempty(book_dir, L("master_outline")):
            problems.append(f"缺大纲文件或为空: {L('master_outline')}")
        if mode in ("建筑师", "混合") and not nonempty(book_dir, f"{L('volume_outlines')}/卷1.md"):
            problems.append("缺大纲文件或为空: 02-大纲/卷纲/卷1.md"
                            + ("（混合模式只需写到当前单元）" if mode == "混合" else ""))
        if mode == "建筑师":
            zs = sorted((book_dir / L("chapter_outlines")).glob("ch-*.md"))
            if len(zs) < 3:
                problems.append(f"章纲 {len(zs)} 份 < 3（黄金三章细纲不齐）")
        items = ledger(book_dir, PROMISES)["items"]
        if mode != "园丁" and not [p for p in items if p.get("type") not in NON_READER_TYPES]:
            problems.append("承诺台账为空（大纲层的伏笔、悬念、卷目标应先登记）")
    elif name == "opening":
        chs = {c["seq"]: c for c in d.get("chapters", [])}
        for seq in (1, 2, 3):
            c = chs.get(seq)
            if not c or c.get("status") != "done":
                problems.append(f"第 {seq} 章未 done")
                continue
            if not hard_passed(c):
                problems.append(f"第 {seq} 章硬伤层未通过")
            rev = c.get("review") or {}
            if rev.get("sha") and c.get("sha") and rev["sha"] != c["sha"]:
                problems.append(f"第 {seq} 章正文变更后未复评")
            if c.get("key") and not c.get("selection"):
                problems.append(f"第 {seq} 章是关键章，缺作者的版本选定（chapter pick）")
        blinds = list((book_dir / L("reviews")).glob("blind-*"))
        tested = [p for p in blinds if "记忆测试" in p.read_text("utf-8")]
        if not blinds:
            problems.append("缺读者盲评报告（05-审稿/blind-*.md）")
        elif not tested:
            problems.append("盲评报告缺「记忆测试」一节")
        elif len(tested) < 2:
            problems.append("开篇盲评只有 1 个读者画像，至少 2 个（目标读者＋老白或懂行读者，各一份 "
                            "05-审稿/blind-ch-0001-0003-<画像>.md，见 reader-personas.md）")
        anchor = book_dir / STYLE_ANCHOR
        calib = section(anchor.read_text("utf-8"), "本书校准段") if anchor.exists() else ""
        if len(HAN.findall(re.sub(r"^\s*<.*>\s*$", "", calib, flags=re.M))) < 100:
            problems.append("文风基准.md 的「本书校准段」还没填（从第 1 章定稿里摘 200–400 字，见 golden-three.md）")
        if not (book_dir / STYLE_FP).exists():
            problems.append("缺文风指纹（有旧文样本用 style --sample；没有就 style --from-chapters 1）")
        signing = d.get("contract", {}).get("signing", {})
        for pt in SIGNING_POINTS:
            ch = signing.get(pt)
            if ch is None:
                problems.append(f"签约点未落地: {pt}")
            elif ch > 3:
                problems.append(f"签约点「{pt}」落在第 {ch} 章，晚于黄金三章")
    elif name == "volume":
        v = open_volume(d)
        if d.get("stage") != "volume" or not v or v.get("status") != "reviewing":
            problems.append("当前不在卷复盘阶段（先 volume end）")
        else:
            problems += has_sections(book_dir / REVIEW_DIR / f"卷{v['n']}.md", VOLUME_REVIEW_REQUIRED)
            items = ledger(book_dir, PROMISES)["items"]
            late = [p["id"] for p in items if promise_overdue(p, v["end"])]
            if late:
                problems.append(f"逾期承诺未处置（兑现、带补偿作废，或带强化延期）：{late}")
            if open_unit(d):
                problems.append(f"单元 {open_unit(d)['id']} 还没关（先做单元复盘并 unit close）")
            soul = d.get("soul", {})
            if v["n"] == 1 and soul.get("status") == "暂定":
                problems.append("书魂仍是暂定——D7 要求最晚在第一卷卷复盘时定下（soul --status 确定）")
    elif name == "finale":
        if d.get("stage") != "finale":
            problems.append("当前不在收束阶段（先 finale begin）")
        items = ledger(book_dir, PROMISES)["items"]
        left = [p["id"] for p in items if p.get("type") not in ("期权", "母题") and p.get("status") in OPEN_STATES]
        if left:
            problems.append(f"还有未清算的承诺（含暂定决策）：{left}")
        if d.get("soul", {}).get("status") != "确定":
            problems.append("书魂还没定下")
        problems += has_sections(book_dir / FINALE_LIST, FINALE_REQUIRED)
        problems += [x.replace("缺文件或为空", "缺书复盘") for x in has_sections(book_dir / REVIEW_DIR / "全书.md", ())]
        lib = book_dir.parent / CRAFT_LIBRARY / f"{d.get('title')}.md"
        if not lib.exists():
            problems.append(f"技艺库还没有这本书的条目：{CRAFT_LIBRARY}/{d.get('title')}.md（craft init 生成模板，见 loops.md 书循环）")
        elif not craft_entries(lib):
            problems.append(f"技艺库条目表是空的：{CRAFT_LIBRARY}/{d.get('title')}.md（每条一句话＋证据＋适用条件＋标签）")
    return problems


def cmd_gate(a):
    book_dir = Path(a.book_dir)
    if a.name in PLANNED_GATES:
        print(f"GATE {a.name}: 尚未实现（计划于 {PLANNED_GATES[a.name]}）")
        sys.exit(3)
    key, next_stage = GATES[a.name]
    d = ensure_m3_fields(load(book_dir))
    if a.action == "check":
        problems = gate_check(book_dir, a.name, d)
        if problems:
            print(f"GATE {a.name}: FAIL")
            for p in problems:
                print(f"  - {p}")
            sys.exit(1)
        print(f"GATE {a.name}: 机械条件满足，等待作者确认")
        return
    forced = []
    if a.action == "pass":
        problems = gate_check(book_dir, a.name, d)
        if problems and not a.force:
            print(f"GATE {a.name}: 机械条件未满足，不能记录通过（作者坚持放行请加 --force 并附 --quote 原话）")
            for p in problems:
                print(f"  - {p}")
            sys.exit(1)
        if problems and not a.quote:
            die("--force 放行必须附 --quote（作者原话）")
        forced = problems
    d.setdefault("gates", {})[key] = {
        "status": "passed" if a.action == "pass" else "rejected", "at": now(), "quote": a.quote or ""}
    if forced:
        d["gates"][key]["forced_over"] = forced
    if a.action == "pass" and a.name == "volume":
        v = open_volume(d)
        v.update({"status": "closed", "closed_at": now()})
        d["volumes"].append({"n": v["n"] + 1, "start": (v.get("end") or 0) + 1, "end": None, "status": "open"})
    if a.action == "pass" and next_stage:
        d["stage"] = next_stage
    save(book_dir, d)
    print(f"GATE {a.name}: {a.action} 记录已写入，stage={d['stage']}")


def cmd_level(a):
    if a.level not in LEVELS:
        die(f"档位只能是 {'/'.join(LEVELS)}")
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    d["experience_level"] = a.level
    save(book_dir, d)
    print(f"OK 引导档位={a.level}")


def cmd_mode(a):
    if a.mode not in MODES:
        die(f"写作模式只能是 {'/'.join(MODES)}")
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    d["mode"] = a.mode
    save(book_dir, d)
    print(f"OK 写作模式={a.mode}")


def cmd_soul(a):
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    soul = d.setdefault("soul", {})
    for k in ("question", "answer", "injustice", "ending", "deadline"):
        v = getattr(a, k)
        if v is not None:
            soul[k] = v
    if a.arc is not None:
        if a.arc not in ARCS:
            die(f"--arc 只能是 {'/'.join(ARCS)}")
        soul["arc"] = a.arc
    if a.status:
        if a.status not in ("暂定", "确定"):
            die("--status 只能是 暂定 或 确定")
        soul["status"] = a.status
        if a.status == "确定":
            soul["deadline"] = ""
    save(book_dir, d)
    print(f"OK 书魂 status={soul.get('status')}" + (f" deadline={soul.get('deadline')}" if soul.get("deadline") else "")
          + (f" arc={soul.get('arc')}" if soul.get("arc") else ""))


def cmd_contract(a):
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    ct = d.setdefault("contract", {"main": "", "extras": [], "poison": [], "signing": {}})
    if a.main is not None:
        ct["main"] = a.main
    if a.extra:
        ct["extras"] = list(dict.fromkeys(ct.get("extras", []) + a.extra))
    if a.poison is not None:
        ct["poison"] = split_names(a.poison)
    if a.audience is not None:
        ct["audience"] = a.audience
    save(book_dir, d)
    print(f"OK 主契约={ct['main'] or '未填'} 附加={len(ct['extras'])} 毒点={len(ct['poison'])}"
          + f" 目标读者={ct.get('audience') or '未填'}")


def cmd_sign(a):
    if a.point not in SIGNING_POINTS:
        die(f"签约点只能是: {'、'.join(SIGNING_POINTS)}")
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    d.setdefault("contract", {}).setdefault("signing", {})[a.point] = a.ch
    save(book_dir, d)
    print(f"OK 签约点「{a.point}」落在第 {a.ch} 章")


def cmd_chapter(a):
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    if a.action == "publish":
        d["published_upto"] = max(d.get("published_upto", 0), a.upto)
        save(book_dir, d)
        print(f"OK 已发布到第 {d['published_upto']} 章")
        return
    if a.action == "add":
        if any(c["seq"] == a.seq for c in d.get("chapters", [])):
            die(f"第 {a.seq} 章已登记")
        key = a.key or a.seq <= 3
        d.setdefault("chapters", []).append({
            "seq": a.seq, "file": a.file, "status": "pending", "key": key, "word_count": 0,
            "hook": None, "mood": None, "retry": 0, "sha": "", "review": None,
            "scenes": {"count": 0, "review": "pending"}, "selection": None,
            "pack": None})
        d["chapters"].sort(key=lambda c: c["seq"])
        msg = f"OK chapter add ch{a.seq} → {a.file}" + ("（关键章）" if key else "")
    else:
        c = find_ch(d, a.seq)
        if a.action == "key":
            c["key"] = not a.off
            msg = f"OK ch{a.seq} key={c['key']}"
        elif a.action == "hook":
            if not 1 <= a.intensity <= 5:
                die("--intensity 取 1–5（1 顺带 … 5 全书名场面）")
            c["hook"] = {"type": a.type, "intensity": a.intensity, "line": a.line or ""}
            msg = f"OK ch{a.seq} hook={a.type}/{a.intensity}"
        elif a.action == "mark":
            if a.status not in CHAPTER_STATES:
                die(f"status 只能是 {'/'.join(CHAPTER_STATES)}（done 只能经 complete）")
            if a.status == "drafting":
                why = scene_ready(book_dir, c)
                if why:
                    die(f"第 {a.seq} 章不能开写：{why}。先审故事，后写文字。")
            c["status"] = a.status
            if a.status == "drafting" and not c.get("drafting_at"):
                c["drafting_at"] = now()
            msg = f"OK ch{a.seq} status={a.status}"
        elif a.action == "mood":
            t = LEGACY_MOOD.get(a.tension, a.tension)
            if t not in TENSION:
                die(f"张弛只能是 {'/'.join(TENSION)}")
            colors = split_names(a.colors)
            bad = [x for x in colors if x not in COLORS]
            if bad:
                die(f"情绪色只能取 {'、'.join(COLORS)}，收到: {'、'.join(bad)}")
            c["mood"] = {"tension": t, "colors": colors}
            msg = f"OK ch{a.seq} mood={t}" + (f" {'、'.join(colors)}" if colors else "")
        elif a.action == "pick":
            if not c.get("key"):
                die(f"第 {a.seq} 章不是关键章；常规章不走比选")
            c["selection"] = {"version": a.version, "note": a.note or "", "by": "author", "at": now()}
            msg = f"OK ch{a.seq} 作者选定版本 {a.version}"
        elif a.action == "end":
            c["end"] = {k: v for k, v in (("time", a.time), ("place", a.place), ("next", a.next)) if v}
            msg = f"OK ch{a.seq} 结束于：" + "，".join(c["end"].values())
        elif a.action == "length":
            p = chapter_file(book_dir, c)
            n = han_words(p.read_text("utf-8"))
            lo, hi, _ = length_band(book_dir, a.seq)
            rec = c.setdefault("length", {})
            if a.compressed:
                rec.update({"compressed": True, "compressed_at": now()})
                msg = f"OK ch{a.seq} 已做过一次只删不加的压缩（现在 {n} 字）"
            elif a.accept:
                if n < lo / 2 and (a.tentative or not a.force):
                    if a.tentative:
                        die(f"第 {a.seq} 章只有 {n} 字，不到下限 {lo} 的一半：不能按推荐先收，要当场问作者")
                    die(f"第 {a.seq} 章只有 {n} 字，不到下限 {lo} 的一半：作者明确要收下时加 --force，并把原话写进 --note")
                if n > hi and not rec.get("compressed") and not a.force:
                    die(f"第 {a.seq} 章 {n} 字，超出上限 {hi}：先让 editor 做一次只删不加的压缩（chapter length --compressed），仍超再收下")
                rec.update({"accepted": n, "band": [lo, hi], "sha": sha16(p), "at": now(), "note": a.note or "",
                            "by": "recommendation" if a.tentative else "author"})
                msg = (f"OK ch{a.seq} 按推荐先收下 {n} 字（区间 {lo}–{hi}），单元复盘时请作者确认" if a.tentative
                       else f"OK ch{a.seq} 作者收下当前长度 {n} 字（区间 {lo}–{hi}）")
            else:
                die("chapter length 要给 --accept（作者收下当前长度）或 --compressed（已做过一次只删不加的压缩）")
        elif a.action == "retry":
            c["retry"] = c.get("retry", 0) + 1
            if c["retry"] >= load_cfg(book_dir)["max_retry"]:
                c["status"] = "failed"
            msg = f"OK ch{a.seq} retry={c['retry']} status={c['status']}"
    save(book_dir, d)
    print(msg)


def cmd_complete(a):
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    c = find_ch(d, a.seq)
    why = scene_ready(book_dir, c)
    if why:
        die(f"章定稿闸：{why}")
    kp = knowledge_ready(book_dir, a.seq)
    if kp:
        die("章定稿闸：场景卡标了知识点，但知识点清单不合格——" + "；".join(kp))
    if a.hard != "pass":
        die("章定稿闸：硬伤层未通过（先派 editor 修订并复审）")
    if c.get("key") and not c.get("selection"):
        die(f"章定稿闸：第 {a.seq} 章是关键章，须作者从 2–3 版中选定（chapter pick）")
    c["status"] = "done"
    c["done_at"] = now()
    c["word_count"] = a.words
    c["sha"] = sha16(book_dir / c.get("file", ""))
    c["review"] = {"hard": a.hard, "decidable": a.decidable,
                   "report": a.report or (c.get("review") or {}).get("report", ""), "sha": c["sha"]}
    save(book_dir, d)
    print(f"OK complete ch{a.seq} words={a.words} sha={c['sha']}")
