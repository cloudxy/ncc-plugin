"""交付：多书仪表盘与导出。"""

import datetime
import html
import re
import uuid
import zipfile
from pathlib import Path
from .core import (HAN, L, PROMISES, PROMISE_TYPES, SCHEMA, current_chapter, die, ensure_m3_fields, ledger, load, now, open_unit, read_json)
from .ledgers import promise_overdue, promise_summary
from .views import views


SHADES = "·░▒▓█"


def shade(n: int) -> str:
    return SHADES[0 if n <= 0 else 1 if n == 1 else 2 if n == 2 else 3 if n <= 4 else 4]


def promise_events(items) -> list:
    """读者向承诺的事件：(章, 类型, 动作)。期权、暂定决策不算。"""
    ev = []
    for p in items:
        if p.get("type") in ("期权", "暂定决策"):
            continue
        if p.get("created_ch") is not None:
            ev.append((p["created_ch"], p["type"], "建立"))
        ev += [(e["ch"], p["type"], "推进") for e in p.get("progress", []) if e.get("ch") is not None]
        if p.get("resolved_ch") is not None:
            ev.append((p["resolved_ch"], p["type"], "兑现" if p.get("status") == "已兑现" else "作废"))
    return ev


def book_overview(b: Path, bucket: int) -> dict:
    d = ensure_m3_fields(read_json(b / "book.json", {}))
    if d.get("schema_version", 1) < SCHEMA:
        return {"title": d.get("title") or b.name, "legacy": True}
    chs = d.get("chapters", [])
    done = [c for c in chs if c.get("status") == "done"]
    items = ledger(b, PROMISES)["items"]
    cur = current_chapter(d)
    pub = d.get("published_upto", 0)
    ev = promise_events(items)
    last = max([c["seq"] for c in chs] + [e[0] for e in ev] + [1])
    nb = -(-last // bucket)
    grid = {}
    for ch, t, _ in ev:
        grid.setdefault(t, [0] * nb)[min(max(ch - 1, 0) // bucket, nb - 1)] += 1
    return {"title": d.get("title") or b.name, "stage": d.get("stage"), "done": len(done), "total": len(chs),
            "words": sum(c.get("word_count") or 0 for c in done), "buffer": sum(1 for c in done if c["seq"] > pub) if pub else None,
            "promises": promise_summary(b, d), "soul": d.get("soul", {}).get("status"), "updated": (d.get("updated_at") or "")[:10],
            "unit": (open_unit(d) or {}).get("id"), "nb": nb, "grid": {t: grid[t] for t in PROMISE_TYPES if t in grid},
            "overdue": [f"{p['id']}（{p['type']}）{p['content']}" for p in items if promise_overdue(p, cur)]}


def cmd_dashboard(a):
    root = Path(a.book_root)
    books = [p.parent for p in sorted(root.glob("*/book.json")) if not p.parent.name.startswith("_")]
    if not books:
        die(f"{root} 下没有书（每本书一个目录，含 book.json）")
    views = [book_overview(b, a.bucket) for b in books]
    out = [f"# 书库仪表盘（{len(views)} 本）", "",
           "| 书 | 阶段 | 章（定稿／登记） | 字数 | 存稿 | 承诺 开放／逾期 | 暂定决策 | 书魂 | 更新 |", "|---|---|---|---|---|---|---|---|---|"]
    for v in views:
        if v.get("legacy"):
            out.append(f"| {v['title']} | v0.1 旧书，先 migrate | | | | | | | |")
            continue
        s = v["promises"]
        out.append(f"| {v['title']} | {v['stage']}{'·' + v['unit'] if v['unit'] else ''} | {v['done']}／{v['total']} | {v['words']} | "
                   f"{'—' if v['buffer'] is None else v['buffer']} | {s['open']}／{s['overdue']}{' ⚠' if s['overdue'] else ''} | "
                   f"{s['pending_decisions']} | {v['soul']} | {v['updated']} |")
    for v in views:
        if v.get("legacy") or not v["grid"]:
            continue
        out += ["", f"## 承诺热力：《{v['title']}》（每格 {a.bucket} 章；{SHADES[1]}1 {SHADES[2]}2 {SHADES[3]}3–4 {SHADES[4]}5+ 次建立、推进或兑现）", ""]
        width = max([len(t) for t in v["grid"]] + [3])
        out.append(f"第几格{'　' * (width - 3)}：" + " ".join(str(i % 10) for i in range(1, v["nb"] + 1)) + f"（第 1 格＝第 1–{a.bucket} 章）")
        out += [f"{t}{'　' * (width - len(t))}：" + " ".join(shade(n) for n in cells) for t, cells in v["grid"].items()]
        if v["overdue"]:
            out.append("逾期：" + "；".join(v["overdue"]))
    print("\n".join(out))
    if a.html:
        dest = Path(a.html)
        dest.write_text(dashboard_html(views, a.bucket), "utf-8")
        print(f"\nOK 网页版：{dest}")


def dashboard_html(views, bucket) -> str:
    e = html.escape
    rows = []
    for v in views:
        if v.get("legacy"):
            rows.append(f"<tr><td>{e(v['title'])}</td><td colspan='8'>v0.1 旧书，先 migrate</td></tr>")
            continue
        s = v["promises"]
        rows.append("<tr>" + "".join(f"<td>{e(str(x))}</td>" for x in (
            v["title"], v["stage"], f"{v['done']}／{v['total']}", v["words"], "—" if v["buffer"] is None else v["buffer"],
            f"{s['open']}／{s['overdue']}", s["pending_decisions"], v["soul"], v["updated"])) + "</tr>")
    heat = []
    for v in views:
        if v.get("legacy") or not v["grid"]:
            continue
        head = "".join(f"<th>{i * bucket + 1}</th>" for i in range(v["nb"]))
        body = "".join(f"<tr><th>{e(t)}</th>" + "".join(
            f"<td style='background:rgba(214,96,42,{min(n / 5, 1):.2f})' title='第{i * bucket + 1}–{(i + 1) * bucket}章：{n} 次'>{n or ''}</td>"
            for i, n in enumerate(cells)) + "</tr>" for t, cells in v["grid"].items())
        over = f"<p class='warn'>逾期：{e('；'.join(v['overdue']))}</p>" if v["overdue"] else ""
        heat.append(f"<h2>承诺热力：《{e(v['title'])}》</h2><p class='note'>每格 {bucket} 章，数字是这几章里建立、推进、兑现的次数；表头是每格的起始章。</p>"
                    f"<div class='scroll'><table class='heat'><tr><th></th>{head}</tr>{body}</table></div>{over}")
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>书库仪表盘</title>
<style>
:root {{ --bg:#fbfaf7; --fg:#22201c; --line:#ddd8cf; --muted:#6b665d; --warn:#b3261e; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#1b1a18; --fg:#ece8e1; --line:#3a3732; --muted:#a39d92; --warn:#f2b8b5; }} }}
body {{ background:var(--bg); color:var(--fg); font:15px/1.6 -apple-system, "PingFang SC", "Noto Sans CJK SC", sans-serif; margin:0; padding:24px 16px; }}
main {{ max-width:1100px; margin:0 auto; }}
table {{ border-collapse:collapse; margin:8px 0 20px; }}
th, td {{ border:1px solid var(--line); padding:4px 8px; text-align:center; white-space:nowrap; }}
.heat td {{ min-width:28px; }}
.scroll {{ overflow-x:auto; }}
.note {{ color:var(--muted); font-size:13px; }}
.warn {{ color:var(--warn); }}
</style></head><body><main>
<h1>书库仪表盘（{len(views)} 本）</h1>
<p class="note">由 ncc_state.py dashboard 生成于 {now()}</p>
<div class="scroll"><table><tr><th>书</th><th>阶段</th><th>章（定稿／登记）</th><th>字数</th><th>存稿</th><th>承诺 开放／逾期</th><th>暂定决策</th><th>书魂</th><th>更新</th></tr>
{''.join(rows)}</table></div>
{''.join(heat)}
</main></body></html>
"""


def chapter_text(book_dir: Path, c: dict):
    raw = (book_dir / c["file"]).read_text("utf-8")
    lines = raw.splitlines()
    title = ""
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and (lines[0].lstrip().startswith("#") or re.match(r"\s*第[一二三四五六七八九十百千零〇0-9]+章", lines[0])):
        title = lines.pop(0).lstrip("# ").strip()
    if not title:
        m = re.match(r"第0*(\d+)章[-_ ]?(.*)", Path(c["file"]).stem)
        title = f"第{m.group(1)}章 {m.group(2)}".strip() if m else Path(c["file"]).stem
    paras = []
    for l in lines:
        t = l.strip()
        if not t or re.match(r"rev\s*\d+\s*[:：]", t) or re.fullmatch(r"[-*_]{3,}", t):
            continue
        paras.append(re.sub(r"^(#+|>)\s*", "", t))
    return title, paras


def write_epub(dest: Path, title: str, author: str, chapters):
    e = html.escape
    uid = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, 'ncc-workflow:' + title)}"
    modified = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    xhtml = ('<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n<html xmlns="http://www.w3.org/1999/xhtml" '
             'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="zh-CN" lang="zh-CN">\n<head><meta charset="utf-8"/>'
             '<title>{t}</title><link rel="stylesheet" type="text/css" href="style.css"/></head>\n<body>\n{b}\n</body>\n</html>\n')
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        mt = zipfile.ZipInfo("mimetype")
        mt.compress_type = zipfile.ZIP_STORED
        z.writestr(mt, "application/epub+zip")
        z.writestr("META-INF/container.xml", '<?xml version="1.0" encoding="utf-8"?>\n<container version="1.0" '
                   'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n<rootfiles><rootfile full-path="OEBPS/content.opf" '
                   'media-type="application/oebps-package+xml"/></rootfiles>\n</container>\n')
        z.writestr("OEBPS/style.css", "body { line-height: 1.8; }\np { text-indent: 2em; margin: 0 0 0.4em; }\n"
                   "h2 { text-align: center; margin: 1.5em 0 1em; }\n")
        items, refs, lis, points = [], [], [], []
        for i, (t, paras) in enumerate(chapters, 1):
            name = f"ch{i:04d}.xhtml"
            body = f"<h2>{e(t)}</h2>\n" + "\n".join(f"<p>{e(p)}</p>" for p in paras)
            z.writestr(f"OEBPS/{name}", xhtml.format(t=e(t), b=body))
            items.append(f'<item id="c{i}" href="{name}" media-type="application/xhtml+xml"/>')
            refs.append(f'<itemref idref="c{i}"/>')
            lis.append(f'<li><a href="{name}">{e(t)}</a></li>')
            points.append(f'<navPoint id="np{i}" playOrder="{i}"><navLabel><text>{e(t)}</text></navLabel><content src="{name}"/></navPoint>')
        z.writestr("OEBPS/nav.xhtml", xhtml.format(t="目录", b=f'<nav epub:type="toc" id="toc"><h1>目录</h1><ol>{"".join(lis)}</ol></nav>'))
        z.writestr("OEBPS/toc.ncx", f'<?xml version="1.0" encoding="utf-8"?>\n<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">\n'
                   f'<head><meta name="dtb:uid" content="{uid}"/><meta name="dtb:depth" content="1"/>'
                   f'<meta name="dtb:totalPageCount" content="0"/><meta name="dtb:maxPageNumber" content="0"/></head>\n'
                   f'<docTitle><text>{e(title)}</text></docTitle>\n<navMap>{"".join(points)}</navMap>\n</ncx>\n')
        creator = f"<dc:creator>{e(author)}</dc:creator>" if author else ""
        z.writestr("OEBPS/content.opf", f'<?xml version="1.0" encoding="utf-8"?>\n<package xmlns="http://www.idpf.org/2007/opf" '
                   f'version="3.0" unique-identifier="bookid" xml:lang="zh-CN">\n<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
                   f'<dc:identifier id="bookid">{uid}</dc:identifier><dc:title>{e(title)}</dc:title><dc:language>zh-CN</dc:language>'
                   f'{creator}<meta property="dcterms:modified">{modified}</meta></metadata>\n<manifest>'
                   '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
                   '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
                   f'<item id="css" href="style.css" media-type="text/css"/>{"".join(items)}</manifest>\n'
                   f'<spine toc="ncx">{"".join(refs)}</spine>\n</package>\n')


def cmd_export(a):
    book_dir = Path(a.book_dir)
    d = ensure_m3_fields(load(book_dir))
    chs = [c for c in d.get("chapters", []) if (a.from_ch or 1) <= c["seq"] <= (a.to_ch or 10 ** 9)]
    done = [c for c in chs if c.get("status") == "done" and (book_dir / c.get("file", "")).is_file()]
    if not done:
        die("范围内没有已定稿的章（只导出 complete 过的章）")
    skipped = [c["seq"] for c in chs if c not in done]
    chapters = [chapter_text(book_dir, c) for c in done]
    title = d.get("title") or book_dir.name
    lo, hi = done[0]["seq"], done[-1]["seq"]
    dest = book_dir / L("export_dir") / f"{title}-第{lo}-{hi}章.{a.format}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if a.format == "md":
        dest.write_text(f"# {title}\n\n" + "\n\n".join(f"## {t}\n\n" + "\n\n".join(ps) for t, ps in chapters) + "\n", "utf-8")
    elif a.format == "txt":
        dest.write_text(f"{title}\n\n" + "\n\n".join(f"{t}\n\n" + "\n".join("　　" + p for p in ps) for t, ps in chapters) + "\n", "utf-8")
    else:
        write_epub(dest, title, a.author if a.author is not None else d.get("team", {}).get("主编", ""), chapters)
    words = sum(len(HAN.findall("".join(ps))) for _, ps in chapters)
    print(f"OK 导出 {len(done)} 章（{words} 字）→ {dest.relative_to(book_dir)}"
          + (f"；未定稿未导出：第 {'、'.join(map(str, skipped))} 章" if skipped else ""))
