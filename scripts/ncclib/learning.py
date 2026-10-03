"""学习与嗓音：文风指纹、读者画像热力、偏好演化、技艺库。"""

import datetime
import os
import re
import statistics
from pathlib import Path
from .core import (CRAFT_EXCERPT, CRAFT_LIBRARY, HAN, PLUGIN_ROOT, PREFS, PREF_HALF_LIFE, PREF_V1, READER_DATA, STYLE_ANCHOR, STYLE_FP, STYLE_MIN, copy_template, die, ensure_m3_fields, ledger, load, now, parse_window, range_chapters, read_json, save, write_json)
from .core import config_numbers


def style_metrics(text: str) -> dict:
    """可复算的文风指纹：句长、段长、对话占比、人称、标点习惯。只给审稿与脚本用。"""
    body = re.sub(r"^[#>*\-|`\s]+", "", text, flags=re.M)
    han = len(HAN.findall(body))
    lens = [len(HAN.findall(s)) for s in re.split(r"[。！？!?…\n]+", body) if HAN.search(s)]
    plens = [len(HAN.findall(p)) for p in body.splitlines() if HAN.search(p)]
    quoted = "".join(re.findall(r"[“「『\"]([^”」』\"]*)[”」』\"]", body))
    narr = re.sub(r"[“「『\"][^”」』\"]*[”」』\"]", "", body)
    mean = statistics.mean(lens) if lens else 0
    k = max(han / 1000, 1)
    return {
        "han": han,
        "sentence_mean": round(mean, 1),
        "sentence_cv": round(statistics.pstdev(lens) / mean, 2) if mean else 0,
        "short_share": round(sum(1 for n in lens if n <= 8) / len(lens), 2) if lens else 0,
        "long_share": round(sum(1 for n in lens if n >= 40) / len(lens), 2) if lens else 0,
        "paragraph_mean": round(statistics.mean(plens), 1) if plens else 0,
        "dialogue_share": round(len(HAN.findall(quoted)) / han, 2) if han else 0,
        "person": "第一人称" if narr.count("我") > narr.count("他") + narr.count("她") else "第三人称",
        "per_1000": {p: round(body.count(p) / k, 1) for p in ("——", "……", "！", "？")},
    }


def style_drift_lines(book_dir: Path, text: str) -> list:
    """本章与文风指纹的偏离（只作参考，交审稿判断是否"文风明显漂移"）。"""
    fp = read_json(book_dir / STYLE_FP, None)
    if not fp:
        return []
    m = style_metrics(text)
    tag = "" if fp.get("enough") else "（指纹样本不足 1 万字，只作参考）"
    out = []
    if fp.get("sentence_mean") and abs(m["sentence_mean"] - fp["sentence_mean"]) > fp["sentence_mean"] * 0.35:
        out.append(f"文风：平均句长 {m['sentence_mean']} 字，指纹 {fp['sentence_mean']} 字{tag}")
    if fp.get("paragraph_mean") and abs(m["paragraph_mean"] - fp["paragraph_mean"]) > fp["paragraph_mean"] * 0.6:
        out.append(f"文风：平均段长 {m['paragraph_mean']} 字，指纹 {fp['paragraph_mean']} 字{tag}")
    if abs(m["dialogue_share"] - fp.get("dialogue_share", 0)) > 0.2:
        out.append(f"文风：对话占比 {m['dialogue_share']}，指纹 {fp.get('dialogue_share')}{tag}")
    if fp.get("person") and m["person"] != fp["person"]:
        out.append(f"文风：人称像是{m['person']}，指纹是{fp['person']}{tag}")
    return out


def sample_files(paths) -> list:
    files = []
    for s in paths:
        p = Path(os.path.expanduser(s))
        if p.is_dir():
            files += sorted(x for x in p.rglob("*") if x.suffix in (".md", ".txt"))
        elif p.is_file():
            files.append(p)
        else:
            die(f"找不到样本：{s}")
    return files


def cmd_style(a):
    book_dir = Path(a.book_dir)
    d = ensure_m3_fields(load(book_dir))
    if a.from_chapters:
        lo, hi = parse_window(a.from_chapters) if re.search(r"[-~～至]", a.from_chapters) else (int(a.from_chapters),) * 2
        files = [book_dir / c["file"] for c in range_chapters(d, lo, hi) if c.get("status") == "done"]
        if not files:
            die(f"第 {lo}–{hi} 章还没有定稿的正文，不能反推")
        source = f"本书第{lo}–{hi}章" if lo != hi else f"本书第{lo}章"
    elif a.sample:
        files, source = sample_files(a.sample), "旧文样本"
    else:
        die("给 --sample <作者旧文的文件或目录>，或 --from-chapters 1（没有旧文时，第 1 章定稿后反推）")
    texts = [(f, f.read_text("utf-8", errors="ignore")) for f in files]
    m = style_metrics("\n".join(t for _, t in texts))
    enough = m["han"] >= STYLE_MIN or source != "旧文样本"
    fp = {"source": source, "files": [f.name for f in files], "enough": enough, "at": now(), **m}
    write_json(book_dir / STYLE_FP, fp)
    anchor = book_dir / STYLE_ANCHOR
    copy_template("style-anchor.md", anchor)
    d["style"] = {"source": source, "han": m["han"], "at": fp["at"]}
    save(book_dir, d)
    print(f"OK 文风指纹 {STYLE_FP}（{source}，{m['han']} 字"
          + ("" if enough else f"，不足 {STYLE_MIN} 字：指纹只作参考，第 1 章定稿后可再用 --from-chapters 1 补") + "）")
    print(f"  句长 {m['sentence_mean']} 字（起伏 {m['sentence_cv']}），段长 {m['paragraph_mean']} 字，"
          f"对话占比 {m['dialogue_share']}，{m['person']}")
    cands = []
    for f, t in texts:
        for i, para in enumerate((x.strip() for x in t.splitlines() if HAN.search(x)), 1):
            n = len(HAN.findall(para))
            if 150 <= n <= 400 and para[0] not in "“「『\"":
                sm = style_metrics(para)["sentence_mean"]
                cands.append((abs(sm - m["sentence_mean"]), f.name, i, para))
    cands.sort(key=lambda x: x[0])
    if cands:
        print("  校准段候选（句长最接近整体的叙述段，worldbuilder 从中挑 2–3 段、作者确认后写进 文风基准.md）：")
        for _, name, i, para in cands[:5]:
            print(f"  - {name} 第{i}段：{para[:30]}……")


def cmd_heat(a):
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    lo, hi = parse_window(a.ch) if a.ch else (1, max([c["seq"] for c in d.get("chapters", [])] or [1]))
    fb = [f for f in ledger(book_dir, READER_DATA)["items"] if lo <= f.get("ch", -1) <= hi]
    who = lambda f: f.get("persona") or ("真实读者" if f.get("source") == "真实" else "模拟（未标画像）")
    people = list(dict.fromkeys(who(f) for f in fb))
    out = [f"# 读者热力（第{lo}–{hi}章）", ""]
    follow = [f for f in fb if f["kind"] == "追读"]
    if follow:
        out += ["## 追读", "", "| 章 | " + " | ".join(people) + " |", "|---|" + "---|" * len(people)]
        for ch in sorted({f["ch"] for f in follow}):
            row = {who(f): str(f["value"]) for f in follow if f["ch"] == ch}
            out.append(f"| 第{ch}章 | " + " | ".join(row.get(p, "—") for p in people) + " |")
        out.append("")
    for kinds, title in ((("弃读", "略读"), "弃读与略读热点（越多画像在同一段失去耐心，越要先改）"), (("划线",), "划线")):
        spots = {}
        for f in fb:
            if f["kind"] in kinds:
                m = re.search(r"\d+", str(f["value"]))
                spots.setdefault((f["ch"], int(m.group()) if m else 0), []).append(f"{f['kind']}·{who(f)}")
        out += [f"## {title}", ""]
        for (ch, para), hits in sorted(spots.items(), key=lambda x: (-len(x[1]), x[0])):
            out.append(f"- 第{ch}章 " + (f"第{para}段" if para else "（未标段落）") + f"：{'█' * len(hits)} {len(hits)}（{'、'.join(hits)}）")
        if not spots:
            out.append("- （无）")
        out.append("")
    slips = [f for f in fb if f["kind"] == "出戏"]
    if slips:
        out += ["## 出戏（懂行读者）", ""] + [f"- 第{f['ch']}章 {f['value']}：{f.get('note', '')}（{who(f)}）" for f in slips]
    print("\n".join(out))


def pref_file(p: Path) -> Path:
    return (p.parent if (p / "book.json").exists() else p) / PREFS


def pref_load(path: Path) -> dict:
    raw = read_json(path, {})
    if raw.get("version") == 2:
        return raw
    data = {"version": 2, "items": [], "dislikes": list(raw.get("dislikes", [])), "rejected": [],
            "settings": {}, "creationHistory": raw.get("creationHistory", [])}
    for k, v in raw.items():
        if k in ("dislikes", "creationHistory", "version"):
            continue
        if k not in PREF_V1:
            data["settings"][k] = v
            continue
        for x in v if isinstance(v, list) else [v]:
            name, w = (x.get("name"), x.get("weight", 1)) if isinstance(x, dict) else (x, 1)
            data["items"].append({"key": PREF_V1[k], "value": name, "weight": w, "last": now()})
    return data


def pref_half_life(path: Path) -> int:
    for cfg in (path.parent.parent / "ncc.config.yaml", path.parent.parent.parent / "ncc.config.yaml"):
        values = config_numbers(cfg, ["half_life_days"])
        if "half_life_days" in values:
            return max(1, values["half_life_days"])
    return PREF_HALF_LIFE


def pref_effective(item: dict, half_life: int) -> float:
    age = (datetime.datetime.now() - datetime.datetime.fromisoformat(item.get("last") or now())).days
    return item["weight"] * 0.5 ** (max(age, 0) / half_life)


def cmd_pref(a):
    path = pref_file(Path(a.path))
    data = pref_load(path)
    hl = pref_half_life(path)
    if a.action == "show":
        rejected = {(r["key"], r["value"]): r for r in data["rejected"]}
        keys = [a.key] if a.key else list(dict.fromkeys(i["key"] for i in data["items"]))
        for key in keys:
            items = sorted((i for i in data["items"] if i["key"] == key), key=lambda i: -pref_effective(i, hl))
            line = []
            for i in items:
                eff = pref_effective(i, hl)
                flag = "（作者否决过，不首推）" if (key, i["value"]) in rejected else ("⭐" if eff >= 2 else "")
                line.append(f"{i['value']} {eff:.1f}{flag}")
            print(f"{key}：" + "；".join(line))
        if data["dislikes"]:
            print("雷点（硬约束，不衰减）：" + "、".join(data["dislikes"]))
        for r in data["rejected"]:
            if not a.key or r["key"] == a.key:
                print(f"否决记录：{r['key']}「{r['value']}」{r['at'][:10]} {r.get('note', '')}")
        print(f"（权重按半衰期 {hl} 天衰减；作者确认过的会重新计时）")
        return
    if a.action == "dislike":
        if a.value not in data["dislikes"]:
            data["dislikes"].append(a.value)
        write_json(path, data)
        print(f"OK 雷点「{a.value}」")
        return
    if not a.key:
        die("--key 必填（如 题材、主契约、主角、视角、基调、风格参考、写作模式、金手指、力量体系）")
    item = next((i for i in data["items"] if i["key"] == a.key and i["value"] == a.value), None)
    if not item:
        item = {"key": a.key, "value": a.value, "weight": 0, "last": now()}
        data["items"].append(item)
    if a.action == "reject":
        if not (a.note or "").strip():
            die("否决要写 --note（为什么不要，下次推荐时避开的就是这一点）")
        item["weight"] -= 2
        data["rejected"].append({"key": a.key, "value": a.value, "at": now(), "note": a.note})
    else:
        item["weight"] += 2 if a.action == "confirm" else 1
        if a.action == "confirm":
            item["confirmed"] = now()
        before = len(data["rejected"])
        data["rejected"] = [r for r in data["rejected"] if (r["key"], r["value"]) != (a.key, a.value)]
        if len(data["rejected"]) < before:
            print(f"  （作者改了主意：撤销对「{a.value}」的否决记录）")
    item["last"] = now()
    write_json(path, data)
    print(f"OK {a.action} {a.key}「{a.value}」权重 {item['weight']}")


def pref_note_book(book_dir: Path, title: str, genre: list):
    path = pref_file(book_dir)
    data = pref_load(path)
    data["creationHistory"] = (data["creationHistory"] + [{"title": title, "genre": "、".join(genre), "at": now()}])[-50:]
    write_json(path, data)


def craft_entries(p: Path):
    rows = []
    for line in p.read_text("utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.strip().startswith("|") else []
        if len(cells) >= 5 and re.fullmatch(r"\d+", cells[0]) and cells[1]:
            rows.append({"n": cells[0], "entry": cells[1], "evidence": cells[2], "when": cells[3], "tags": cells[4]})
    return rows


def book_terms(d: dict) -> list:
    ct = d.get("contract", {})
    raw = list(d.get("genre_tags", [])) + re.split(r"[＋+、,，/\s]", ct.get("main", "")) + list(ct.get("extras", []))
    raw += [d.get("soul", {}).get("arc", ""), d.get("mode", "")]
    return [t for t in dict.fromkeys(x.strip() for x in raw) if len(t) >= 2]


def cmd_craft(a):
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    lib = book_dir.parent / CRAFT_LIBRARY
    if a.action == "init":
        dest = lib / f"{d.get('title')}.md"
        if dest.exists():
            die(f"已存在：{dest}")
        tpl = (PLUGIN_ROOT / "skills/ncc/templates/craft-entry.md").read_text("utf-8")
        ct, soul = d.get("contract", {}), d.get("soul", {})
        tpl = (tpl.replace("{书名}", d.get("title", "")).replace("{题材}", "、".join(d.get("genre_tags", [])))
               .replace("{主契约}", ct.get("main", "")).replace("{弧光}", soul.get("arc", "")).replace("{写作模式}", d.get("mode", "")))
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(tpl, "utf-8")
        print(f"OK 技艺库条目模板 {CRAFT_LIBRARY}/{dest.name}（全书复盘后填，每条一句话＋证据＋适用条件＋标签）")
        return
    terms = book_terms(d)
    hits, others = [], {}
    for p in sorted(lib.glob("*.md")) if lib.is_dir() else []:
        if p.stem == d.get("title"):
            continue
        for r in craft_entries(p):
            generic = r["when"] in ("", "通用", "—", "——", "-")
            why = ["通用"] if generic else [t for t in terms if t in f"{r['when']} {r['tags']}"]
            if why:
                hits.append((len(why), p.stem, r, why))
            else:
                others[p.stem] = others.get(p.stem, 0) + 1
    if not hits and not others:
        print("技艺库里还没有别的书的条目（第一本书不需要这一步）")
        return
    hits.sort(key=lambda x: -x[0])
    out = ["# 技艺库摘录（开书时读，M6-4）", "",
           f"> 由 ncc_state.py craft read 生成。本书：{'、'.join(terms) or '（题材与契约未定）'}。"
           "推荐理由引用时写\"源自技艺库《书名》#n\"；排在作者种子之后、题材常规之前。", "",
           "## 相关条目", "", "| 来源 | # | 条目 | 证据 | 适用条件 | 为什么相关 |", "|---|---|---|---|---|---|"]
    out += [f"| 《{b}》 | {r['n']} | {r['entry']} | {r['evidence']} | {r['when']} | "
            + ("通用经验" if w == ["通用"] else f"本书也有 {'、'.join(w)}") + " |" for _, b, r, w in hits[:a.top]]
    if not hits:
        out.append("| —— | | （没有和本书题材、契约、弧光、写作模式相关的条目） | | | |")
    if others:
        out += ["", "## 其他条目（不一定适用）", ""] + [f"- 《{b}》{n} 条" for b, n in others.items()]
    dest = book_dir / CRAFT_EXCERPT
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(out) + "\n", "utf-8")
    print("\n".join(out))


def craft_pending(book_dir: Path, d: dict) -> int:
    """别的书在技艺库里的条目数（本书开书时要读）。"""
    lib = book_dir.parent / CRAFT_LIBRARY
    return sum(len(craft_entries(p)) for p in lib.glob("*.md") if p.stem != d.get("title")) if lib.is_dir() else 0
