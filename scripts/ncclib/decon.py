"""拆书库的脚本支撑：章节索引、进度与覆盖率、对标基线统计、本书与对标书的对照。只往下依赖 core。"""

import hashlib
import re
import statistics
import sys
from collections import Counter
from pathlib import Path
from .core import (DECON_CFG, DECON_LIB, HAN, PROMISES, book_root, die, ledger, load, mood_of, now, parse_window, read_json, read_jsonl, save, sha16, write_json)


DIGIT = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


UNIT = {"十": 10, "百": 100, "千": 1000, "万": 10000}


HEAD = re.compile(DECON_CFG["chapter_heading"])


def cn2int(s: str) -> int:
    if s.isdigit():
        return int(s)
    total = section = num = 0
    for ch in s:
        if ch in DIGIT:
            num = DIGIT[ch]
        elif ch in UNIT:
            if UNIT[ch] == 10000:
                total += (section + num) * 10000
                section = 0
            else:
                section += (num or 1) * UNIT[ch]
            num = 0
    return total + section + num


def lib_path(p) -> Path:
    p = Path(p)
    if not p.is_dir():
        die(f"拆书库目录不存在：{p}（应是 {{书库}}/{DECON_LIB}/<书名>/）")
    return p


def source_file(lib: Path, given=None) -> Path:
    if given:
        p = lib / given if not Path(given).is_absolute() else Path(given)
        if not p.is_file():
            die(f"找不到原文：{given}")
        return p
    files = sorted(x for x in (lib / "原文").glob("*") if x.suffix in (".txt", ".md"))
    if not files:
        die(f"{lib}/原文/ 里没有 .txt 或 .md（先把作者合法持有的原文放进去，或用 --source 指定）")
    return files[0]


def build_index(text: str):
    lines = text.splitlines()
    heads = [(i, HEAD.match(line)) for i, line in enumerate(lines)]
    heads = [(i, m) for i, m in heads if m]
    chapters, problems = [], []
    for k, (i, m) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
        body = "\n".join(lines[i + 1:end])
        no = cn2int(re.search(r"第([〇零一二两三四五六七八九十百千万0-9]+)", m.group(0)).group(1))
        han = len(HAN.findall(body))
        chapters.append({"seq": k + 1, "no": no, "title": lines[i].strip(), "start": i + 1, "end": end, "han": han,
                         "hash": hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]})
    if not chapters:
        problems.append("一个章标题都没认出来（标题应形如「第十二章 ……」）")
    seen = Counter(c["no"] for c in chapters)
    problems += [f"重号：第 {n} 章出现 {k} 次" for n, k in seen.items() if k > 1]
    for x, y in zip(chapters, chapters[1:]):
        if y["no"] not in (x["no"] + 1, x["no"]):
            problems.append(f"跳号：第 {x['no']} 章之后是第 {y['no']} 章")
    problems += [f"疑似空章：序号 {c['seq']}（{c['title']}，{c['han']} 字）" for c in chapters if c["han"] < 100]
    return chapters, problems


def progress(lib: Path) -> dict:
    p = read_json(lib / DECON_CFG["progress"], {})
    return {"done": sorted(set(p.get("done", []))), "skipped": p.get("skipped", {})}


def coverage(lib: Path, window=None):
    idx = read_json(lib / DECON_CFG["index"], None)
    if not idx:
        return None, ["还没有章节索引（decon index）"]
    pr = progress(lib)
    covered = set(pr["done"]) | {int(k) for k in pr["skipped"]}
    seqs = {c["seq"] for c in idx["chapters"]}
    selected = set(range(window[0], window[1] + 1)) if window else seqs
    missing = sorted((seqs & selected) - covered)
    problems = []
    if window and (window[0] > window[1] or not selected or not selected <= seqs):
        problems.append("统计范围不在章节索引内")
    src = lib / idx["source"]
    if not src.is_file():
        problems.append("索引对应的原文不存在：恢复原文后重建索引")
    elif sha16(src) != idx.get("sha"):
        problems.append("原文在建索引之后变过：先重建索引（decon index），章号一律以索引为准")
    if missing:
        head = "、".join(map(str, missing[:20])) + ("……" if len(missing) > 20 else "")
        problems.append(f"索引 {len(idx['chapters'])} 章，已拆 {len(pr['done'])}、显式跳过 {len(pr['skipped'])}，还差 {len(missing)} 章：{head}")
    return idx, problems


def records(lib: Path, kind: str, lo: int, hi: int) -> list:
    rows = read_jsonl(lib / DECON_CFG["ledgers"][kind])
    return [r for r in rows if lo <= (r.get("chapter") or r.get("start") or 0) <= hi]


def runs(seq) -> dict:
    """连续段长度：{值: [每段长度]}。"""
    out, prev, n = {}, None, 0
    for x in seq + [None]:
        if x == prev:
            n += 1
            continue
        if prev is not None:
            out.setdefault(prev, []).append(n)
        prev, n = x, 1
    return out


def avg(xs):
    return round(statistics.mean(xs), 1) if xs else None


def baseline(lib: Path, lo: int, hi: int) -> dict:
    n = hi - lo + 1
    fs = records(lib, "伏笔", lo, hi)
    plant, resolve, touch, last = {}, {}, Counter(), {}
    for r in sorted(fs, key=lambda r: r["chapter"]):
        fid, op, ch = r.get("id"), r.get("op"), r["chapter"]
        last[fid] = ch
        if op == "埋":
            plant.setdefault(fid, ch)
        elif op == "回收":
            resolve[fid] = ch
        elif op == "强化":
            touch[fid] += 1
    waits = [resolve[f] - plant[f] for f in plant if f in resolve]
    open_ = [f for f in plant if f not in resolve]
    forgotten = [f for f in open_ if hi - last.get(f, plant[f]) > DECON_CFG["forgotten_after"]]
    sp = records(lib, "爽点", lo, hi)
    gaps = [r["chapter"] - r["setup"] for r in sp if isinstance(r.get("setup"), int)]
    parts = DECON_CFG["payoff_parts"]
    full = [r for r in sp if set(parts) <= set(r.get("parts", []))]
    emo = {}
    for r in sorted(records(lib, "情绪", lo, hi), key=lambda r: r["chapter"]):
        emo[r["chapter"]] = r.get("tension")
    rr = runs([emo[k] for k in sorted(emo)])
    hooks = Counter(r.get("type") for r in records(lib, "钩子", lo, hi) if r.get("type"))
    units = [r["end"] - r["start"] + 1 for r in records(lib, "单元", lo, hi) if r.get("end")]
    ents = Counter((r.get("category") or "未归类") for r in read_jsonl(lib / DECON_CFG["ledgers"]["实体"])
                   if lo <= (r.get("first_ch") or r.get("chapter") or lo) <= hi)
    return {"range": [lo, hi], "chapters": n, "at": now(),
            "伏笔": {"埋": len(plant), "回收": len(waits), "平均等待章数": avg(waits),
                   "最长等待章数": max(waits) if waits else None, "平均强化次数": avg([touch[f] for f in plant]),
                   "未回收": len(open_), "疑似遗忘": len(forgotten)},
            "爽点": {"数量": len(sp), "每10章": round(len(sp) / n * 10, 1) if n else None, "平均铺垫章数": avg(gaps),
                   "四件齐全占比": round(len(full) / len(sp), 2) if sp else None},
            "情绪": {"最长连续压抑": max(rr.get("压", [0])), "压抑段平均章数": avg(rr.get("压", [])),
                   "释放段平均章数": avg(rr.get("放", [])), "已标章数": len(emo)},
            "钩子": dict(hooks.most_common()),
            "单元": {"个数": len(units), "平均章数": avg(units)},
            "实体": dict(ents.most_common())}


def baseline_md(name: str, b: dict) -> str:
    lines = [f"# 对标基线：《{name}》第{b['range'][0]}–{b['range'][1]}章", "",
             "> 由 `ncc_state.py decon stats --write` 从拆书台账算出，勿手改。只作参照，不作判据。", ""]
    for k in ("伏笔", "爽点", "情绪", "钩子", "单元", "实体"):
        v = b.get(k) or {}
        lines += [f"## {k}", ""] + ([f"- {x}：{y if y is not None else '—'}" for x, y in v.items()] or ["- （无数据）"]) + [""]
    return "\n".join(lines)


def book_metrics(book_dir: Path, d: dict, lo: int, hi: int) -> dict:
    """本书同口径的数：伏笔等待、爽点密度（兑现的爽点欠账与名场面）、最长连续压抑。"""
    items = ledger(book_dir, PROMISES)["items"]
    fs = [p for p in items if p.get("type") == "伏笔" and lo <= (p.get("created_ch") or 0) <= hi]
    waits = [p["resolved_ch"] - p["created_ch"] for p in fs if p.get("resolved_ch") and p.get("status") == "已兑现"]
    paid = [p for p in items if p.get("type") in ("爽点欠账", "名场面") and lo <= (p.get("resolved_ch") or -1) <= hi]
    moods = [mood_of(c)["tension"] for c in sorted(d.get("chapters", []), key=lambda c: c["seq"])
             if lo <= c["seq"] <= hi and c.get("mood")]
    rr = runs(moods)
    n = max(hi - lo + 1, 1)
    return {"伏笔平均等待章数": avg(waits), "爽点每10章": round(len(paid) / n * 10, 1), "最长连续压抑": max(rr.get("压", [0]))}


def compare_lines(book_dir: Path, d: dict, lo: int, hi: int) -> list:
    names = d.get("benchmarks") or []
    if not names:
        return ["- 本书没有链接对标书（decon link <书目录> <对标书名>）"]
    mine = book_metrics(book_dir, d, lo, hi)
    out = [f"- 本书第{lo}–{hi}章：伏笔平均等待 {mine['伏笔平均等待章数'] or '—'} 章；爽点每 10 章 {mine['爽点每10章']} 个；最长连续压抑 {mine['最长连续压抑']} 章"]
    root = book_root(book_dir)
    for name in names:
        b = read_json(root / DECON_LIB / name / DECON_CFG["baseline"], None)
        if not b:
            out.append(f"- 《{name}》还没有基线（拆完后 decon stats --write）")
            continue
        out.append(f"- 《{name}》第{b['range'][0]}–{b['range'][1]}章：伏笔平均等待 {b['伏笔']['平均等待章数'] or '—'} 章；"
                   f"爽点每 10 章 {b['爽点']['每10章']} 个；最长连续压抑 {b['情绪']['最长连续压抑']} 章")
    out.append("- 只作参照，不作判据：差得多的地方，复盘时问一句\"是有意为之吗\"")
    return out


def cmd_decon(a):
    if a.action == "link":
        book_dir = Path(a.book_dir)
        d = load(book_dir)
        lib = book_root(book_dir) / DECON_LIB / a.name
        if not lib.is_dir():
            die(f"拆书库里没有《{a.name}》：{lib}")
        d["benchmarks"] = list(dict.fromkeys((d.get("benchmarks") or []) + [a.name]))
        save(book_dir, d)
        print(f"OK 对标书：{'、'.join(d['benchmarks'])}（单元复盘底稿会拿它们的基线作参照）")
        return
    lib = lib_path(a.lib)
    if a.action == "index":
        src = source_file(lib, a.source)
        chapters, problems = build_index(src.read_text("utf-8", errors="ignore"))
        if problems:
            print("INDEX 有问题（不带病进抽取）：")
            print("\n".join(f"  - {p}" for p in problems))
            if not a.force:
                print("核对原文后重跑；确认无误（如原书本来就缺章）加 --force")
                sys.exit(1)
        write_json(lib / DECON_CFG["index"], {"source": str(src.relative_to(lib)) if lib in src.parents else str(src),
                                              "sha": sha16(src), "at": now(), "chapters": chapters})
        print(f"OK 章节索引 {DECON_CFG['index']}：{len(chapters)} 章（第 {chapters[0]['no']}–{chapters[-1]['no']} 章），"
              f"共 {sum(c['han'] for c in chapters)} 字。一切章号引用这份索引的序号（seq）")
        return
    if a.action == "mark":
        pr = progress(lib)
        if a.done:
            lo, hi = parse_window(a.done) if re.search(r"[-~～至]", a.done) else (int(a.done),) * 2
            pr["done"] = sorted(set(pr["done"]) | set(range(lo, hi + 1)))
            msg = f"OK 已拆 第{lo}–{hi}（序号）"
        elif a.skip is not None:
            if not a.why:
                die("跳过要写 --why（覆盖率闸门会核对）")
            pr["skipped"][str(a.skip)] = a.why
            msg = f"OK 跳过序号 {a.skip}：{a.why}"
        else:
            die("给 --done A-B 或 --skip N --why …")
        write_json(lib / DECON_CFG["progress"], pr)
        print(msg)
        return
    if a.action == "coverage":
        idx, problems = coverage(lib)
        if problems:
            print("COVERAGE FAIL")
            print("\n".join(f"  - {p}" for p in problems))
            sys.exit(1)
        print(f"COVERAGE OK  索引 {len(idx['chapters'])} 章 = 已拆 + 显式跳过")
        return
    # stats
    window = parse_window(a.range) if a.range else None
    idx, problems = coverage(lib, window)
    if problems:
        die("统计要先过覆盖率闸门：" + "；".join(problems) + "（只统计一段用 --range A-B）")
    lo, hi = window or (1, len(idx["chapters"]))
    b = baseline(lib, lo, hi)
    md = baseline_md(lib.name, b)
    if a.write:
        write_json(lib / DECON_CFG["baseline"], b)
        p = lib / DECON_CFG["baseline_view"]
        p.write_text(md + "\n", "utf-8")
        print(f"OK 基线写进 {DECON_CFG['baseline']} 与 {DECON_CFG['baseline_view']}")
    print(md)
