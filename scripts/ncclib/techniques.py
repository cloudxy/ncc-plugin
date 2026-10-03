"""技法库：拆书学来的写法卡（跨书共用）、检查、匹配、使用结果与状态。依赖 core 与 learning（作者否决过的降权）。"""

import re
import sys
from pathlib import Path
from .core import (CONFIDENCE, DECON_LIB, HAN, SCENE_DIR, TECH_CFG, TECHNIQUE_LIB, TECHNIQUE_STAGES, TECHNIQUE_USAGE, append_jsonl, book_root, chars, die, load, next_id, now, read_jsonl, scene_path, split_names, technique_kinds)
from .core import capped, technique_catalog, writer_input_problems
from .learning import pref_file, pref_load


FIELDS = tuple(TECH_CFG["required"]) + tuple(TECH_CFG["optional"])


LOCATOR = re.compile(r"「([^」]+)」")


REF = re.compile(r"技法[：:]\s*([^\n]+)")


def lib_dir(root: Path) -> Path:
    return root / TECHNIQUE_LIB


def technique_cards(root: Path) -> dict:
    """{编号: {path, title, 各字段}}"""
    base = lib_dir(root)
    cards = {}
    if not base.is_dir():
        return cards
    for p in sorted(base.rglob("T-*.md")):
        m = re.match(r"(T-\d{4})", p.stem)
        if not m:
            continue
        text = p.read_text("utf-8")
        head = re.search(r"^#\s*\S+\s*(.*)$", text, flags=re.M)
        card = {"path": p, "title": head.group(1).strip() if head else ""}
        for f in FIELDS:
            mm = re.search(rf"^[-*]\s*{f}[：:][ \t]*(.*)$", text, flags=re.M)
            card[f] = mm.group(1).strip() if mm else ""
        cards[m.group(1)] = card
    return cards


def parse_applies(s: str) -> dict:
    out = {}
    for part in re.split(r"[；;]", s or ""):
        if "=" in part or "＝" in part:
            k, v = re.split(r"[=＝]", part, maxsplit=1)
            out[k.strip()] = split_names(v)
    return out


def sources_of(card: dict) -> list:
    books = re.findall(r"拆[:：]\s*《?([^\s》第]+)》?", card.get("证据", ""))
    return list(dict.fromkeys(books or ([card["来源书"]] if card.get("来源书") else [])))


def overlap_hits(root: Path, card: dict) -> list:
    """卡片正文与拆书库原文连续重合超过上限的片段（只用自己的话概括）。"""
    n = TECH_CFG["overlap_max"] + 1
    body = re.sub(r"\s", "", "".join(card.get(f, "") for f in ("手法", "怎么做", "代价与失效", "数据")))
    hits = []
    for book in sources_of(card):
        src = root / DECON_LIB / book / "原文"
        texts = [re.sub(r"\s", "", p.read_text("utf-8", errors="ignore")) for p in src.glob("*") if p.suffix in (".txt", ".md")] if src.is_dir() else []
        for t in texts:
            i = 0
            while i <= len(body) - n:
                seg = body[i:i + n]
                if len(HAN.findall(seg)) >= n // 2 and seg in t:
                    hits.append(seg)
                    i += n
                else:
                    i += 1
    return hits


def card_problems(root: Path, card: dict) -> list:
    problems = [f"缺「{f}」" for f in TECH_CFG["required"] if card.get(f, "") in ("", "——", "-", "—")]
    kinds = technique_kinds(root)
    if card.get("类别") and card["类别"] not in kinds:
        problems.append(f"类别「{card['类别']}」应为 {'/'.join(kinds)}（新类别走 evolve propose --key technique.kinds）")
    if card.get("置信级") and card["置信级"] not in CONFIDENCE:
        problems.append(f"置信级应为 {'/'.join(CONFIDENCE)}")
    if technique_catalog(root).get(card.get("类别")) == "文笔参考":
        problems += writer_input_problems({}, card.get("手法", "") + "\n" + card.get("怎么做", ""))
    locs = LOCATOR.findall(card.get("证据", ""))
    lo, hi = TECH_CFG["locator"]
    if card.get("证据") and not locs:
        problems.append("证据要写 拆:书名 第N章「5–15 字定位词」")
    problems += [f"定位词「{x}」{len(x)} 字，应在 {lo}–{hi} 字" for x in locs if not lo <= len(x) <= hi]
    stages = parse_applies(card.get("适用条件", "")).get("阶段", [])
    problems += [f"适用阶段「{s}」应为 {'/'.join(TECHNIQUE_STAGES)}" for s in stages if s not in TECHNIQUE_STAGES]
    hits = overlap_hits(root, card)
    if hits:
        problems.append(f"和原文连续重合超过 {TECH_CFG['overlap_max']} 字（只用自己的话概括）：{'；'.join(hits[:3])}")
    return problems


def usage(root: Path) -> list:
    return read_jsonl(root / TECHNIQUE_USAGE)


def card_state(card: dict, cid: str, uses: list):
    """状态由证据与使用结果推出：停用 > 已验证 > 手法 > 样本；另给"通用"（两本书以上都有）。"""
    mine = [u for u in uses if u.get("id") == cid]
    last_restore = max((k for k, u in enumerate(mine) if u.get("op") == "restore"), default=-1)
    after = mine[last_restore + 1:]
    general = len(sources_of(card)) >= TECH_CFG["general_books"]
    if any(u.get("op") == "retire" for u in after):
        return "停用", general, "作者停用"
    results = [u["outcome"] for u in after if u.get("op") == "result" and u.get("outcome") in ("good", "bad")]
    k = TECH_CFG["retire_after_bad"]
    if len(results) >= k and all(r == "bad" for r in results[-k:]):
        return "停用", general, f"连续 {k} 次结果差（technique restore 可恢复）"
    if "good" in results:
        return "已验证", general, f"用过 {len(results)} 次，好 {results.count('good')} 次"
    locs = LOCATOR.findall(card.get("证据", ""))
    return ("手法" if len(set(locs)) >= TECH_CFG["method_evidence"] else "样本"), general, ""


def technique_refs(text: str) -> list:
    refs = []
    for m in REF.finditer(text):
        refs += re.findall(r"T-\d{4}", m.group(1))
    return list(dict.fromkeys(refs))


def batch_text(book_dir: Path, seqs) -> str:
    return "\n".join(scene_path(book_dir, s).read_text("utf-8") for s in seqs or [] if scene_path(book_dir, s).exists())


def match(book_dir: Path, d: dict, role: str, seqs=None, card_text=None) -> list:
    """按题材、阶段、契约、本批场景卡涉及的承诺类型打分；状态加权；作者否决过的降权；同一本对标书限量。"""
    cfg = TECH_CFG["per_role"].get(role)
    if not cfg or role in TECH_CFG["never"]:
        return []
    root = book_root(book_dir)
    cards, uses = technique_cards(root), usage(root)
    text = batch_text(book_dir, seqs) if card_text is None else card_text
    if cfg.get("only_referenced"):
        refs = technique_refs(text)
        cards = {k: v for k, v in cards.items() if k in refs}
    genres = set(d.get("genre_tags", []))
    stage = TECH_CFG["stage_of"].get(d.get("stage"), "")
    ct = d.get("contract", {})
    contract = " ".join([ct.get("main", "")] + list(ct.get("extras", [])))
    rejected = {r["value"] for r in pref_load(pref_file(book_dir)).get("rejected", []) if r.get("key") == "技法"}
    scored = []
    catalog = technique_catalog(book_dir)
    for cid, c in cards.items():
        if catalog.get(c.get("类别")) not in cfg["kinds"]:
            continue
        status, general, _ = card_state(c, cid, uses)
        if status == "停用":
            continue
        ap = parse_applies(c.get("适用条件", ""))
        s = 1.0
        g = set(ap.get("题材", []))
        s += len(g & genres) if g else 0.5
        s *= 1 if not g or g & genres else 0.5
        s += 1 if stage and stage in ap.get("阶段", []) else 0
        s += 1 if any(x and x in contract for x in ap.get("契约", [])) else 0
        s += 0.5 * sum(1 for x in ap.get("承诺", []) if x in text)
        s += 0.3 if general else 0
        s *= TECH_CFG["status_weight"].get(status, 1)
        if cid in rejected:
            s *= 0.3
        scored.append((s, cid, c, status))
    scored.sort(key=lambda x: -x[0])
    out, per_book = [], {}
    for s, cid, c, status in scored:
        sources = sources_of(c) or ["?"]
        if any(per_book.get(src, 0) >= TECH_CFG["per_source_max"] for src in sources):
            continue
        for src in sources:
            per_book[src] = per_book.get(src, 0) + 1
        out.append((s, cid, c, status))
        if len(out) >= cfg["max"]:
            break
    return out


def brief_lines(book_dir: Path, d: dict, role: str, seqs=None) -> list:
    cfg = TECH_CFG["per_role"].get(role) or {}
    lines = [f"- {cid} [{c['类别']}·{st}] {c['手法']}：{c['怎么做']}｜适用：{c['适用条件']}｜代价：{c['代价与失效']}｜证据：{c['证据']}"
             for _, cid, c, st in match(book_dir, d, role, seqs)]
    out, cut = capped(lines, cfg.get("chars", 1500))
    if cut:
        print(f"提醒：{role} 的技法参考省略 {cut} 条（超过字数预算，请先压缩卡片）", file=sys.stderr)
    return out


def writer_lines(book_dir: Path, card_text: str) -> list:
    """写手只拿场景卡引用的文笔参考，转成"写成什么"一两句：不带证据、出处与代价。"""
    d = load(book_dir)
    cap = TECH_CFG["per_role"]["writer"]["chars"]
    lines = []
    for _, cid, c, _ in match(book_dir, d, "writer", card_text=card_text):
        text = f"- 文笔参考：{c['手法']}——{c['怎么做']}"
        problems = writer_input_problems(d, text)
        if problems:
            die(f"技法 {cid} 不能进写手包：" + "；".join(problems))
        lines.append(text)
    out, cut = capped(lines, cap)
    if cut:
        print(f"提醒：写手文笔参考省略 {cut} 条（超过字数预算，请先压缩卡片）", file=sys.stderr)
    return out


def settle(book_dir: Path, d: dict, lo: int, hi: int) -> list:
    """单元关闭时自动结算：用了技法的章，顺利定稿记好、返工两轮以上或失败记差；已结算过的不重复记。"""
    root = book_root(book_dir)
    done = {(u.get("id"), u.get("book"), u.get("ch")) for u in usage(root) if u.get("op") == "result"}
    out = []
    for c in d.get("chapters", []):
        if not lo <= c["seq"] <= hi or not scene_path(book_dir, c["seq"]).exists():
            continue
        refs = technique_refs(scene_path(book_dir, c["seq"]).read_text("utf-8"))
        if c.get("status") == "failed" or c.get("retry", 0) >= 2:
            outcome, why = "bad", f"返工 {c.get('retry', 0)} 轮" + ("，失败" if c.get("status") == "failed" else "")
        elif c.get("status") == "done" and c.get("retry", 0) == 0:
            outcome, why = "good", "一次定稿"
        else:
            continue
        for cid in refs:
            if (cid, d.get("title"), c["seq"]) in done:
                continue
            append_jsonl(root / TECHNIQUE_USAGE, {"op": "result", "id": cid, "book": d.get("title"), "ch": c["seq"],
                                                  "outcome": outcome, "why": why, "by": "auto", "at": now()})
            out.append(f"{cid} 第{c['seq']}章：{'好' if outcome == 'good' else '差'}（{why}）")
    return out


def cmd_technique(a):
    target = Path(a.path)
    root = book_root(target)
    cards = technique_cards(root)
    if a.action == "add":
        kinds = technique_kinds(root)
        if a.kind not in kinds:
            die(f"--kind 只能是 {'/'.join(kinds)}（新类别走 evolve propose --key technique.kinds）")
        if a.confidence not in CONFIDENCE:
            die(f"--confidence 只能是 {'/'.join(CONFIDENCE)}")
        card = {"类别": a.kind, "手法": a.method, "怎么做": a.how, "证据": "；".join(a.evidence), "适用条件": a.applies,
                "代价与失效": a.cost, "置信级": a.confidence, "来源书": a.source, "数据": a.data or ""}
        problems = card_problems(root, card)
        if problems:
            print("TECHNIQUE 未写入：")
            print("\n".join(f"  - {p}" for p in problems))
            sys.exit(1)
        cid = next_id([{"id": k} for k in cards], "T")
        title = re.sub(r"[\\/:*?\"<>|\s，。、！？；：]+", "", a.title or a.method)[:16] or "技法"
        dest = lib_dir(root) / a.kind / f"{cid}-{title}.md"
        lines = [f"# {cid} {title}", ""] + [f"- {f}：{card[f]}" for f in FIELDS if card.get(f)] + [f"- 记录于：{now()[:10]}"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("\n".join(lines) + "\n", "utf-8")
        print(f"OK {cid} → {dest.relative_to(root)}（{card_state(card, cid, [])[0]}）")
        return
    if a.action == "check":
        bad = 0
        for cid, c in cards.items():
            problems = card_problems(root, c)
            if problems:
                bad += 1
                print(f"TECHNIQUE {cid}: FAIL（{c['path'].name}）")
                print("\n".join(f"  - {p}" for p in problems))
        print(f"技法卡 {len(cards)} 张，合格 {len(cards) - bad} 张")
        sys.exit(1 if bad else 0)
    uses = usage(root)
    if a.action == "list":
        for cid, c in cards.items():
            if a.kind and c.get("类别") != a.kind:
                continue
            st, general, why = card_state(c, cid, uses)
            n = sum(1 for u in uses if u.get("id") == cid and u.get("op") == "result")
            print(f"{cid} [{c.get('类别')}·{st}{'·通用' if general else ''}] {c.get('手法')}｜来源：{'、'.join(sources_of(c))}"
                  + (f"｜用过 {n} 次" if n else "") + (f"（{why}）" if why else ""))
        if not cards:
            print("（技法库还是空的：拆书时 deconstructor 学法写卡，见 ncc-deconstruct）")
        return
    if a.action == "match":
        d = load(target)
        seqs = a.seq or []
        rows = match(target, d, a.role, seqs)
        for s, cid, c, st in rows:
            print(f"{s:.1f} {cid} [{c['类别']}·{st}] {c['手法']}（{'、'.join(sources_of(c))}）")
        if not rows:
            print(f"（没有适合 {a.role} 的技法卡）" if a.role not in TECH_CFG["never"] else f"{a.role} 不拿技法卡：{TECH_CFG['why_never']}")
        return
    cid = a.id
    if cid not in cards:
        die(f"技法库里没有 {cid}")
    if a.action == "result":
        if not a.note:
            die("手动登记结果要写 --note（好在哪、差在哪）")
        rec = {"op": "result", "id": cid, "book": a.book or "", "ch": a.ch, "outcome": a.outcome, "why": a.note, "by": "author", "at": now()}
    elif a.action == "retire":
        if not a.note:
            die("停用要写 --note（为什么不再用）")
        rec = {"op": "retire", "id": cid, "why": a.note, "at": now()}
    else:
        rec = {"op": "restore", "id": cid, "why": a.note or "", "at": now()}
    append_jsonl(root / TECHNIQUE_USAGE, rec)
    st = card_state(cards[cid], cid, usage(root))
    print(f"OK {cid} {a.action} → {st[0]}" + (f"（{st[2]}）" if st[2] else ""))
