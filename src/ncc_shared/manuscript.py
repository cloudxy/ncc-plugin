"""Pure-stdlib manuscript rendering: clean paragraphs, Markdown, TXT, and EPUB 3."""

from __future__ import annotations

import datetime
import html
import io
import re
import uuid
import zipfile
from collections.abc import Sequence
from pathlib import Path

_CHAPTER_HEADING_RE = re.compile(r"^\s*第[一二三四五六七八九十百千零〇0-9]+章(?:\s*$|[\s：:·\-—_].*)$")
_REV_NOTE_RE = re.compile(r"^rev\s*\d+\s*[:：]", re.IGNORECASE)
_HR_RE = re.compile(r"^[-*_]{3,}$")
_LEAD_MARK_RE = re.compile(r"^(?:#+|>+)\s*")
_UTC = datetime.timezone(datetime.timedelta(0))


def parse_chapter_paragraphs(raw_text: str, fallback_title: str = "") -> tuple[str, list[str]]:
    """Extract clean chapter title and body paragraphs without revision notes or dividers."""
    lines = (raw_text or "").lstrip("\ufeff").splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    fallback = (fallback_title or "").strip()
    extracted = ""
    if lines:
        first = lines[0].strip()
        if first.startswith("#"):
            extracted = first.lstrip("#").strip()
            lines.pop(0)
        elif len(first) <= 120 and _CHAPTER_HEADING_RE.match(first):
            extracted = first
            lines.pop(0)
        elif fallback and first == fallback:
            extracted = first
            lines.pop(0)

    if fallback and lines and lines[0].strip().lstrip("#").strip() == fallback:
        lines.pop(0)

    title = fallback or extracted
    paragraphs: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or _REV_NOTE_RE.match(stripped) or _HR_RE.fullmatch(stripped):
            continue
        cleaned = _LEAD_MARK_RE.sub("", stripped).strip()
        if cleaned:
            paragraphs.append(cleaned)
    return title, paragraphs


def _chapter_parts(item: dict) -> tuple[str, list[str], str]:
    vol_title = str(item.get("volume_title") or "").strip()
    raw_title = str(item.get("title") or "").strip()
    if "paragraphs" in item and item["paragraphs"] is not None:
        paras = [str(p).strip() for p in item["paragraphs"] if str(p).strip()]
        title = raw_title or "未命名章节"
        return title, paras, vol_title
    title, paras = parse_chapter_paragraphs(str(item.get("text") or ""), fallback_title=raw_title)
    return (title or "未命名章节"), paras, vol_title


def render_manuscript_md(book_title: str, chapters: Sequence[dict]) -> bytes:
    """Render clean UTF-8 manuscript Markdown with optional volume headers and zero JSON metadata."""
    heading = (book_title or "").strip() or "未命名作品"
    blocks = [f"# {heading}"]
    current_volume = ""
    for item in chapters:
        ch_title, paras, vol_title = _chapter_parts(item)
        if vol_title:
            if vol_title != current_volume:
                blocks.append(f"## {vol_title}")
                current_volume = vol_title
            blocks.append(f"### {ch_title}")
        else:
            current_volume = ""
            blocks.append(f"## {ch_title}")
        for para in paras:
            blocks.append(para)
    return ("\n\n".join(blocks) + "\n").encode("utf-8")


def render_manuscript_txt(book_title: str, chapters: Sequence[dict]) -> bytes:
    """Render clean UTF-8 plain text with two full-width spaces indenting every paragraph."""
    heading = (book_title or "").strip() or "未命名作品"
    sections = [heading]
    current_volume = ""
    for item in chapters:
        ch_title, paras, vol_title = _chapter_parts(item)
        if vol_title:
            if vol_title != current_volume:
                sections.append(vol_title)
                current_volume = vol_title
        else:
            current_volume = ""
        if paras:
            indented = "\n".join("　　" + p.lstrip("　 \t") for p in paras)
            sections.append(f"{ch_title}\n\n{indented}")
        else:
            sections.append(ch_title)
    return ("\n\n".join(sections) + "\n").encode("utf-8")


def build_epub_bytes(
    title: str,
    author: str,
    chapters: Sequence[tuple[str, Sequence[str]]],
) -> bytes:
    """Build valid EPUB 3 archive bytes in memory using only standard library modules."""
    e = html.escape
    clean_title = (title or "").strip() or "未命名作品"
    clean_author = (author or "").strip()
    book_uid = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, 'ncc-workflow:' + clean_title)}"
    modified = datetime.datetime.now(_UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    xhtml_tpl = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<!DOCTYPE html>\n"
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="zh-CN" lang="zh-CN">\n'
        '<head><meta charset="utf-8"/><title>{t}</title>'
        '<link rel="stylesheet" type="text/css" href="style.css"/></head>\n'
        "<body>\n{b}\n</body>\n</html>\n"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        mt = zipfile.ZipInfo("mimetype")
        mt.compress_type = zipfile.ZIP_STORED
        mt.extra = b""
        zf.writestr(mt, b"application/epub+zip")
        zf.writestr(
            "META-INF/container.xml",
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
            '<rootfiles><rootfile full-path="OEBPS/content.opf" '
            'media-type="application/oebps-package+xml"/></rootfiles>\n'
            "</container>\n",
        )
        zf.writestr(
            "OEBPS/style.css",
            "body { line-height: 1.8; }\n"
            "p { text-indent: 2em; margin: 0 0 0.4em; }\n"
            "h2 { text-align: center; margin: 1.5em 0 1em; }\n",
        )
        items: list[str] = []
        refs: list[str] = []
        lis: list[str] = []
        points: list[str] = []
        for idx, (ch_title, paras) in enumerate(chapters, 1):
            safe_ch_title = (ch_title or "").strip() or f"第{idx}章"
            name = f"ch{idx:04d}.xhtml"
            body = f"<h2>{e(safe_ch_title)}</h2>\n" + "\n".join(f"<p>{e(str(p))}</p>" for p in paras)
            zf.writestr(f"OEBPS/{name}", xhtml_tpl.format(t=e(safe_ch_title), b=body))
            items.append(f'<item id="c{idx}" href="{name}" media-type="application/xhtml+xml"/>')
            refs.append(f'<itemref idref="c{idx}"/>')
            lis.append(f'<li><a href="{name}">{e(safe_ch_title)}</a></li>')
            points.append(
                f'<navPoint id="np{idx}" playOrder="{idx}">'
                f"<navLabel><text>{e(safe_ch_title)}</text></navLabel>"
                f'<content src="{name}"/></navPoint>'
            )
        zf.writestr(
            "OEBPS/nav.xhtml",
            xhtml_tpl.format(
                t="目录",
                b=f'<nav epub:type="toc" id="toc"><h1>目录</h1><ol>{"".join(lis)}</ol></nav>',
            ),
        )
        zf.writestr(
            "OEBPS/toc.ncx",
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">\n'
            f'<head><meta name="dtb:uid" content="{e(book_uid)}"/><meta name="dtb:depth" content="1"/>'
            '<meta name="dtb:totalPageCount" content="0"/><meta name="dtb:maxPageNumber" content="0"/></head>\n'
            f"<docTitle><text>{e(clean_title)}</text></docTitle>\n"
            f'<navMap>{"".join(points)}</navMap>\n'
            "</ncx>\n",
        )
        creator = f"<dc:creator>{e(clean_author)}</dc:creator>" if clean_author else ""
        zf.writestr(
            "OEBPS/content.opf",
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<package xmlns="http://www.idpf.org/2007/opf" '
            'version="3.0" unique-identifier="bookid" xml:lang="zh-CN">\n'
            '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
            f'<dc:identifier id="bookid">{e(book_uid)}</dc:identifier>'
            f"<dc:title>{e(clean_title)}</dc:title>"
            "<dc:language>zh-CN</dc:language>"
            f"{creator}"
            f'<meta property="dcterms:modified">{modified}</meta></metadata>\n'
            "<manifest>"
            '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
            '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
            f'<item id="css" href="style.css" media-type="text/css"/>{"".join(items)}</manifest>\n'
            f'<spine toc="ncx">{"".join(refs)}</spine>\n'
            "</package>\n",
        )
    return buf.getvalue()


def write_epub(
    dest: Path,
    title: str,
    author: str,
    chapters: Sequence[tuple[str, Sequence[str]]],
) -> None:
    """Write valid EPUB 3 file to disk."""
    target = Path(dest)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(build_epub_bytes(title, author, chapters))
