"""场景卡与故事审、知识点清单、写手包与派单头、字数检查点、审稿快照。"""

import re
import sys
from pathlib import Path
from .core import (BRIEF_DIR, HANDOFF_CFG, ROLES, TECH_CFG, WRITER_GUARD, book_root, chars, ENTRY, ERAS, FACTS, KNOW_DIR, L, MATERIAL_HINT, PACK_BUDGET, PACK_DIR, PROMISES, SCENE_BATCH, SCENE_DIR, SCENE_KEY_REQUIRED, SCENE_REQUIRED, SEEDS, SNAPSHOT_DIR, STYLE_ANCHOR, WRITER_SEEDS, chapter_file, die, ensure_m3_fields, find_ch, han_words, knowledge_path, ledger, length_band, load, normalize_domain, now, plain, read_json, save, scene_path, section, sha16)
from .ledgers import focus_core, reader_now_lines
from .materials import material_cards, material_refs
from .memory import handoff_slice, memory_slice
from .techniques import brief_lines, technique_cards, technique_refs, writer_lines


def scene_problems(book_dir: Path, seq: int, key: bool):
    p = scene_path(book_dir, seq)
    if not p.exists():
        return [f"缺场景卡: {SCENE_DIR}/ch-{seq:04d}.md（模板见 skills/ncc-write/references/scene-card.md）"], 0
    text = p.read_text("utf-8")
    blocks = re.split(r"^##\s*场景", text, flags=re.M)[1:]
    if not blocks:
        return ["场景卡里没有「## 场景」段"], 0
    problems = []
    if len(blocks) > 3:
        problems.append(f"一章 {len(blocks)} 场，超过 3 场（考虑拆章）")
    need = SCENE_REQUIRED + (SCENE_KEY_REQUIRED if key else ())
    for i, b in enumerate(blocks, 1):
        missing = [f for f in need if f not in b]
        if missing:
            problems.append(f"场景 {i} 缺: {'、'.join(missing)}" + ("（关键章用完整版）" if key else ""))
    refs = material_refs(text)
    if refs:
        lost = [r for r in refs if r not in material_cards(book_dir)]
        if lost:
            problems.append(f"引用的素材卡不存在: {'、'.join(lost)}（material list 查编号）")
    trefs = technique_refs(text)
    if trefs:
        lost = [r for r in trefs if r not in technique_cards(book_root(book_dir))]
        if lost:
            problems.append(f"引用的技法卡不存在: {'、'.join(lost)}（technique list 查编号）")
    return problems, len(blocks)


def scene_ready(book_dir: Path, c: dict):
    """返回 None 表示场景卡已过故事审且之后未改动，否则返回原因。"""
    sc = c.get("scenes") or {}
    if sc.get("review") != "passed":
        return "场景卡未过故事审（scene review --result pass）"
    if sc.get("sha") != sha16(scene_path(book_dir, c["seq"])):
        return "场景卡在故事审之后被改动，需要重审"
    return None


def cmd_scene(a):
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    if a.action == "next":
        size = SCENE_BATCH.get(d.get("mode", "混合"), 3)
        chs = d.get("chapters", [])
        pending = [c["seq"] for c in chs if c.get("status") != "done" and (c.get("scenes") or {}).get("review") != "passed"]
        start = pending[0] if pending else max([c["seq"] for c in chs] or [0]) + 1
        batch = list(range(start, start + size))
        print(f"下一批场景卡：第 {batch[0]}–{batch[-1]} 章（{d.get('mode', '混合')}模式一批 {size} 章）")
        missing = [n for n in batch if n not in {c["seq"] for c in chs}]
        if missing:
            print(f"  先登记：{missing}（chapter add）")
        keys = [c["seq"] for c in chs if c["seq"] in batch and c.get("key")]
        if keys:
            print(f"  其中关键章 {keys}：场景卡须写完整版，由作者过目")
        return
    seqs = a.seq if isinstance(a.seq, list) else [a.seq]
    if a.action == "check":
        bad = False
        for seq in seqs:
            c = find_ch(d, seq)
            problems, n = scene_problems(book_dir, seq, c.get("key", False))
            if problems:
                bad = True
                print(f"SCENE ch{seq}: FAIL")
                for p in problems:
                    print(f"  - {p}")
            else:
                print(f"SCENE ch{seq}: {n} 场，格式完整")
        sys.exit(1 if bad else 0)
    # review（整批校验通过才写入）
    if a.by not in ("story-editor", "author"):
        die("--by 只能是 story-editor 或 author")
    results, errors = [], []
    for seq in seqs:
        c = find_ch(d, seq)
        problems, n = scene_problems(book_dir, seq, c.get("key", False))
        if a.result == "pass":
            if problems:
                errors += [f"ch{seq}: {p}" for p in problems]
            if c.get("key") and a.by != "author":
                errors.append(f"ch{seq} 是关键章，场景卡须由作者过目（--by author）")
        results.append((c, n))
    if errors:
        print("SCENE: 整批未写入")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    for c, n in results:
        c["scenes"] = {"count": n, "review": "passed" if a.result == "pass" else "revise", "by": a.by,
                       "at": now(), "note": a.note or "", "sha": sha16(scene_path(book_dir, c["seq"]))}
    save(book_dir, d)
    done_list = "、".join("ch" + str(c[0]["seq"]) for c in results)
    print(f"OK 场景卡故事审: {done_list} → "
          f"{'passed' if a.result == 'pass' else 'revise'}（{a.by}）")


BRIEF_TAIL = ("两难里的两个选项都不完全对。把人物的选择演出来，不要替他解释，也不要让任何人（包括叙述者）说出这场的意义。"
              "从视角人物能感知到的写起；他不知道的事，叙述也不知道。"
              "情绪落在选择、台词、物件和后果上；身体反应只写有后果的（手一抖摔了杯子、信封被攥皱），"
              "不用指尖、指节、喉结、呼吸、心跳这类小动作去标注情绪。写完删掉解释情绪、复述前情、结尾点题的句子。")


def knowledge_points(card: str):
    pts = []
    for m in re.finditer(r"知识[：:]\s*([^\n]+)", card):
        pts += [x.strip() for x in re.split(r"[；;、,，]", m.group(1)) if x.strip() and x.strip() not in ("无", "——", "-")]
    return pts


def knowledge_rows(book_dir: Path, seq: int):
    p = knowledge_path(book_dir, seq)
    if not p.exists():
        return None
    rows = []
    for line in p.read_text("utf-8").splitlines():
        t = line.strip()
        if not t.startswith("|") or set(t) <= {"|", "-", " ", ":"}:
            continue
        cells = [c.strip() for c in t.strip("|").split("|")]
        if cells and cells[0] == "知识点":
            continue
        rows.append(cells)
    return rows


def knowledge_problems(book_dir: Path, seq: int):
    rows = knowledge_rows(book_dir, seq)
    if rows is None:
        return [f"缺知识点清单: {KNOW_DIR}/ch-{seq:04d}.md（格式见 skills/ncc/references/domains/README.md 的「本章知识点清单格式」）"]
    if not rows:
        return ["知识点清单是空表"]
    problems = []
    for i, r in enumerate(rows, 1):
        if len(r) < 5:
            problems.append(f"第 {i} 行不足五栏（知识点｜学科｜写成什么｜来源｜状态）")
            continue
        point, dom, how, src, state = r[:5]
        if not normalize_domain(dom):
            problems.append(f"第 {i} 行「{point}」的学科「{dom}」不是 24 张卡之一")
        if state not in ("已核", "待核"):
            problems.append(f"第 {i} 行「{point}」的状态应为 已核 或 待核")
        elif state == "已核" and src in ("", "——", "-", "—"):
            problems.append(f"第 {i} 行「{point}」标了已核却没有来源")
        if not how:
            problems.append(f"第 {i} 行「{point}」缺\"写成什么\"")
        elif state == "待核" and re.search(r"\d|[一二两三四五六七八九十百千万半]+\s*(?:里|斤|两|年|月|天|日|夜|丈|尺|寸|度|公里|米|钱|文|贯|石|刻|时辰|人|兵|骑)", how):
            problems.append(f"第 {i} 行「{point}」是待核，写法里却有具体数字（宁缺律：改成可感的现象，如\"走到脚底起泡\"）")
    return problems


def knowledge_ready(book_dir: Path, seq: int):
    """场景卡标了知识点时，返回清单的问题；没标则返回空。"""
    card = scene_path(book_dir, seq)
    if not card.exists() or not knowledge_points(card.read_text("utf-8")):
        return []
    return knowledge_problems(book_dir, seq)


def cmd_knowledge(a):
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    if a.action == "plan":
        need = []
        for seq in a.seq:
            find_ch(d, seq)
            card = scene_path(book_dir, seq)
            pts = knowledge_points(card.read_text("utf-8")) if card.exists() else []
            if pts:
                need.append(seq)
                print(f"第 {seq} 章：{'；'.join(pts)}")
            else:
                print(f"第 {seq} 章：场景卡没有标知识点")
        print(f"→ 派 scholar（一次）做第 {'、'.join(map(str, need))} 章的知识点清单" if need else "→ 这一批不派 scholar")
        return
    bad = False
    for seq in a.seq:
        problems = knowledge_problems(book_dir, seq)
        if problems:
            bad = True
            print(f"KNOWLEDGE ch{seq}: FAIL")
            for p in problems:
                print(f"  - {p}")
        else:
            rows = knowledge_rows(book_dir, seq)
            print(f"KNOWLEDGE ch{seq}: {len(rows)} 条，待核 {sum(1 for r in rows if r[4] == '待核')} 条")
    sys.exit(1 if bad else 0)


def cmd_era(a):
    if a.era not in ERAS:
        die(f"时代背景只能是 {'/'.join(ERAS)}")
    book_dir = Path(a.book_dir)
    d = ensure_m3_fields(load(book_dir))
    d["era"] = a.era
    save(book_dir, d)
    print(f"OK 时代背景={a.era}")


def cmd_study(a):
    book_dir = Path(a.book_dir)
    d = ensure_m3_fields(load(book_dir))
    if a.add:
        dom = normalize_domain(a.add)
        if not dom:
            die(f"「{a.add}」不是 24 张卡之一（见 skills/ncc/references/domains/README.md）")
        if dom not in d["study"]:
            d["study"].append(dom)
        save(book_dir, d)
    print("一书一深学：" + ("、".join(d["study"]) or "（未选）"))


def cmd_pack(a):
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    c = find_ch(d, a.seq)
    why = scene_ready(book_dir, c)
    if why:
        die(f"不能组装写手包：{why}")
    card = scene_path(book_dir, a.seq).read_text("utf-8")
    blocks = re.split(r"^##\s*场景", card, flags=re.M)[1:]
    out = [f"# 第 {a.seq} 章 写手包", "", "> 由 ncc_state.py pack 组装。阅读顺序：写作简报 → 本书经验 → 作者刚说的 → 读者此刻 → 人物声音 → 可用材料 → 前情 → 前一章结尾 → 文风基准。", ""]

    out += ["## 写作简报", ""]
    for i, b in enumerate(blocks, 1):
        body = b.split("\n", 1)[1] if "\n" in b else ""
        out += [f"### 场景 {i}", body.strip()]
        if "默认写法" in body:
            out.append("- 上面\"默认写法\"列的是这场最容易想到的走法：不要这样写。")
        if c.get("key") and "关键节拍" in body:
            out.append(f"- 关键节拍写 2–3 个版本，彼此走法不同，存到 {L('versions')}/，不要自己挑。")
        out += [f"- {BRIEF_TAIL}", ""]
    lo, hi, _ = length_band(book_dir, a.seq)
    out += ["### 篇幅", f"- 本章 {lo}–{hi} 字。分两段写：先把前半段（写到一个自然转场处）写进正文文件，"
            f"跑一次 `python3 {ENTRY} words {book_dir.resolve()} {a.seq}`，它会告诉你后半段大约还要多少字；"
            "再接着写后半段。只量这一次，不回头改前半段去追字数。",
            "- 简报里的事写完就停：不为凑字数加情节、加人物、加设定。写短了照实交回，由作者决定收不收。", ""]
    if a.note:
        out += ["### 经理的特别提醒（只写意图与材料）", a.note, ""]

    mem, shared, _ = memory_slice(book_dir, d, "writer", plain=True)
    said = handoff_slice(book_dir, d, "writer", seq=a.seq, plain=True)
    bad = [w for w in WRITER_GUARD if any(w in x for x in mem + shared + said)]
    if bad:
        die(f"写手的记忆或交接里出现了审稿判据词（{'、'.join(bad)}）：改成\"怎么写\"（memory merge --text，或 handoff close 后重记）")
    if mem or shared:
        out += ["## 本书经验（写成什么）", ""] + mem + shared + [""]
    if said:
        out += ["## 作者刚说的", ""] + said + [""]

    out += reader_now_lines(book_dir, d, a.seq) + [""]

    rows = knowledge_rows(book_dir, a.seq)
    if rows:
        out += ["## 本章知识点（scholar 已查；写成什么就照这个方向写）", ""]
        for r in rows:
            if len(r) >= 5:
                tail = "（待核：不写具体数字和术语，写可感的现象）" if r[4] == "待核" else ""
                out.append(f"- {r[0]}：{r[2]}{tail}")
        out.append("")

    out += ["## 人物声音", ""]
    names = []
    for p in sorted((book_dir / L("characters")).glob("*.md")):
        if p.stem.endswith("-采访") or p.stem not in card:
            continue
        names.append(p.stem)
        t = p.read_text("utf-8")
        out.append(f"### {p.stem}")
        for sec in ("欲望", "恐惧", "声音"):
            v = section(t, sec)
            if v:
                out.append(f"- {sec}：{v}")
        out.append("")
    if not names:
        out += ["（场景卡里没有出现已建卡的人物名）", ""]

    out += ["## 可用材料", ""]
    seeds = book_dir / SEEDS
    if seeds.exists():
        for line in seeds.read_text("utf-8").splitlines():
            m = re.match(r"^\|\s*(\d+)\s*\|[^|]*\|\s*([^|]+?)\s*\|", line)
            if m and m.group(1) in WRITER_SEEDS and m.group(2).strip():
                out.append(f"- 作者种子 #{m.group(1)}：{m.group(2).strip()}")
    mats = material_cards(book_dir)
    for r in material_refs(card):
        if r in mats:
            m = mats[r]
            out.append(f"- 素材 {r}：{m['内容']}（可用在：{m['可用处']}）{MATERIAL_HINT.get(m.get('可信级'), '')}")
    out += writer_lines(book_dir, card)
    facts = read_json(book_dir / FACTS, {"facts": {}}).get("facts", {})
    for k, f in facts.items():
        if k in card:
            out.append(f"- {k} = {f['value']}（知识台账）")
    lex = book_dir / L("lexicon")
    if lex.exists():
        rows = [[x.strip() for x in line.strip().strip("|").split("|")] for line in lex.read_text("utf-8").splitlines()
                if line.strip().startswith("|") and not set(line.strip()) <= {"|", "-", " ", ":"}]
        head = rows[0] if rows else []
        col = head.index("读者已知") if "读者已知" in head else None
        for r in rows[1:]:
            if r and r[0] and r[0] in card:
                known = r[col] if col is not None and col < len(r) else ""
                out.append(f"- {r[0]}：读者目前知道「{known or '（未登记）'}」（设定词典；完整真相不进写手包）")
    out.append("")

    out += ["## 前情", ""] + focus_core(book_dir, d, a.seq) + [""]
    prev = next((x for x in d.get("chapters", []) if x["seq"] == a.seq - 1), None)
    if prev and (book_dir / prev.get("file", "")).is_file():
        tail = plain((book_dir / prev["file"]).read_text("utf-8")).strip()[-800:]
        out += ["## 前一章结尾（原文）", "", tail, ""]
    style = book_dir / STYLE_ANCHOR
    if style.exists() and style.read_text("utf-8").strip():
        out += ["## 文风基准（最后读）", "", style.read_text("utf-8").strip(), ""]

    text = "\n".join(out)
    soul = d.get("soul", {})
    leaks = [v for v in (soul.get("question"), soul.get("answer"), soul.get("injustice"), soul.get("ending"))
             if v and len(v) >= 6 and v in text]
    if leaks:
        die("写手包里出现了书魂原文（多半写进了场景卡）：" + "；".join(leaks) + "。书魂不进写手提示，请改场景卡后重审。")
    size = len(re.findall(r"[\u4e00-\u9fff]", text))
    dest = book_dir / PACK_DIR / f"ch-{a.seq:04d}.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text + "\n", "utf-8")
    c["pack"] = str(dest.relative_to(book_dir))
    save(book_dir, d)
    print(f"OK 写手包 {c['pack']}（{size} 字" + (f"，超过预算 {PACK_BUDGET}，请删减材料" if size > PACK_BUDGET else "") + "）")


def cmd_brief(a):
    """其余角色的派单头：本角色记忆、作者刚说的（按可见范围切）、技法参考。写手用 pack。"""
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    role = a.role
    if role == "writer":
        die("写手用 pack：写手包里已经带了本书经验、作者刚说的和场景卡引用的文笔参考")
    if role not in ROLES:
        die(f"--role 只能是 {'/'.join(r for r in ROLES if r != 'writer')}")
    seqs = a.seq or []
    head = f"# 派单头：{role}" + (f"（第 {'、'.join(map(str, seqs))} 章）" if seqs else "") + (f"｜任务：{a.task}" if a.task else "")
    what = "这个画像的校准备注" if role == "reader" else "本角色的记忆、作者刚说的话、技法参考"
    out = [head, "", f"> 由 ncc_state.py brief 组装：{what}。任务材料按派单包的 inputs 读；角色定义见 agents/{role}.md。", ""]
    mem, shared, cut = memory_slice(book_dir, d, role, kinds=["校准"] if role == "reader" else None, persona=a.persona)
    out += ["## 本书记忆" if role != "reader" else "## 校准备注（来自真实读者数据）", ""] + (mem or ["- （无）"]) + [""]
    if shared:
        out += ["## 跨书经验", ""] + shared + [""]
    if cut:
        out += [f"> 还有 {cut} 条没放进来（超上限，单元整理时合并或归档）", ""]
    if HANDOFF_CFG["visibility"].get(role):
        said = handoff_slice(book_dir, d, role, seq=seqs[0] if seqs else None)
        out += ["## 作者刚说的（会话交接）", ""] + (said or ["- （无）"]) + [""]
    elif role != "reader":
        out += [f"> 不带会话交接：{HANDOFF_CFG['why_none']}", ""]
    if role in TECH_CFG["per_role"]:
        tl = brief_lines(book_dir, d, role, seqs)
        out += ["## 技法参考（借写法，不借事件链；推荐理由仍先从作者种子长出来）", ""] + (tl or ["- （技法库里没有合适的卡）"]) + [""]
    if a.note:
        out += ["## 经理的特别提醒", a.note, ""]
    name = role + (f"-ch-{seqs[0]:04d}" if seqs else "") + (f"-{a.persona}" if a.persona else "") + (f"-{a.task}" if a.task and not seqs else "")
    dest = book_dir / BRIEF_DIR / f"{name}.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(out)
    dest.write_text(text + "\n", "utf-8")
    print(f"OK 派单头 {dest.relative_to(book_dir)}（{chars([text])} 字）；派单包的 inputs 里放它的路径")


def cmd_words(a):
    """量字数。写前半段后量一次，给出后半段还剩多少（只量这一次，不据此回改前半段）。"""
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    c = find_ch(d, a.seq)
    p = Path(a.file) if a.file else chapter_file(book_dir, c)
    if not p.is_file():
        die(f"找不到文件：{p}")
    n = han_words(p.read_text("utf-8"))
    lo, hi, src = length_band(book_dir, a.seq)
    print(f"第 {a.seq} 章现在 {n} 字；本章区间 {lo}–{hi} 字（来自{src}）")
    if n < lo:
        print(f"后半段大约还要 {lo - n}–{hi - n} 字。照简报写完就停，不为凑字数加内容。")
    elif n <= hi:
        print(f"已在区间内；后半段最多还能写 {hi - n} 字，简报里的事写完就停。")
    else:
        print(f"已超出上限 {n - hi} 字：后半段只收尾，不再展开。")


def paragraphs(text: str):
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def cmd_review(a):
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    c = find_ch(d, a.seq)
    body = book_dir / c.get("file", "")
    if not body.is_file():
        die(f"找不到第 {a.seq} 章正文：{c.get('file')}")
    snap = book_dir / SNAPSHOT_DIR / f"ch-{a.seq:04d}.md"
    if a.action == "plan":
        items = ledger(book_dir, PROMISES)["items"]
        payoff = [p["id"] for p in items if p.get("resolved_ch") == a.seq and p.get("type") in ("爽点欠账", "名场面")]
        reasons = []
        if c.get("key"):
            reasons.append("关键章（另做成对比较）")
        if a.seq <= 3:
            reasons.append("开篇（查签约点）")
        if payoff:
            reasons.append(f"本章兑现 {payoff}（查欠·挣·超·证）")
        print(f"第 {a.seq} 章审稿计划：continuity 必派（硬伤层，含契约与毒点）")
        print("  pulse：" + ("派——" + "；".join(reasons) if reasons else "不派（常规章、无兑现）"))
        snap.parent.mkdir(parents=True, exist_ok=True)
        snap.write_text(body.read_text("utf-8"), "utf-8")
        print(f"  已存正文快照：{snap.relative_to(book_dir)}（修订后用 review delta 只看改动）")
        return
    # delta
    if not snap.exists():
        die("没有快照：先 review plan")
    old, new = paragraphs(snap.read_text("utf-8")), paragraphs(body.read_text("utf-8"))
    old_set = set(old)
    changed = [(i, p) for i, p in enumerate(new, 1) if p not in old_set]
    removed = len([p for p in old if p not in set(new)])
    if not changed and not removed:
        print(f"第 {a.seq} 章：快照之后没有改动")
    else:
        print(f"第 {a.seq} 章改动：{len(changed)} 段新增或修改，{removed} 段删除。复审只看这些段落与上次不通过的项：")
        for i, p in changed:
            print(f"\n[第 {i} 段]\n{p}")
    snap.write_text(body.read_text("utf-8"), "utf-8")
