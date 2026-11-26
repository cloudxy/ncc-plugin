from __future__ import annotations

import io
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from ncc_shared.manuscript import (
    build_epub_bytes,
    parse_chapter_paragraphs,
    render_manuscript_md,
    render_manuscript_txt,
    write_epub,
)


def test_parse_chapter_paragraphs_strips_revision_notes_dividers_and_duplicate_headings():
    raw = (
        "\n\n# 第一章 风雪破庙\n\n"
        "rev 1: 删去多余环境描写\n"
        "---\n"
        "> 庙外风雪正紧。\n\n"
        "***\n"
        "rev 2：调整人物台词\n"
        "## 小节残留标记\n"
        "少年按剑而立。\n\n"
    )
    title, paras = parse_chapter_paragraphs(raw)
    assert title == "第一章 风雪破庙"
    assert paras == ["庙外风雪正紧。", "小节残留标记", "少年按剑而立。"]

    # When fallback_title matches or overrides heading, no duplicate title paragraph remains
    override_title, paras2 = parse_chapter_paragraphs(raw, fallback_title="第一章 夜雪归人")
    assert override_title == "第一章 夜雪归人"
    assert paras2 == ["庙外风雪正紧。", "小节残留标记", "少年按剑而立。"]

    dup_raw = "第二章 断桥\n\n江水如墨。\n"
    dup_title, dup_paras = parse_chapter_paragraphs(dup_raw, fallback_title="第二章 断桥")
    assert dup_title == "第二章 断桥"
    assert dup_paras == ["江水如墨。"]


def test_render_manuscript_md_and_txt_formatting_without_json_metadata():
    chapters = [
        {"title": "楔子 残剑", "paragraphs": ["寒铁无声。", "孤灯照影。"], "volume_title": ""},
        {"title": "第一章 入山", "paragraphs": ["　　山道湿滑。", "云雾初开。"], "volume_title": "第一卷 潜龙"},
        {"title": "第二章 试剑", "paragraphs": ["木剑裂石。"], "volume_title": "第一卷 潜龙"},
        {"title": "第三章 远行", "paragraphs": ["孤舟下江陵。"], "volume_title": "第二卷 出渊"},
    ]

    md_text = render_manuscript_md("剑起青萍", chapters).decode("utf-8")
    assert md_text.startswith("# 剑起青萍\n\n## 楔子 残剑\n\n寒铁无声。\n\n孤灯照影。\n\n")
    assert md_text.count("## 第一卷 潜龙") == 1
    assert "### 第一章 入山" in md_text
    assert "### 第二章 试剑" in md_text
    assert "## 第二卷 出渊\n\n### 第三章 远行" in md_text
    assert "```json" not in md_text
    assert "content_hash" not in md_text

    txt_text = render_manuscript_txt("剑起青萍", chapters).decode("utf-8")
    assert txt_text.startswith("剑起青萍\n\n楔子 残剑\n\n　　寒铁无声。\n　　孤灯照影。\n\n")
    assert "\n\n第一卷 潜龙\n\n第一章 入山\n\n　　山道湿滑。\n　　云雾初开。\n\n" in txt_text
    # Pre-indented paragraph must not become 4 full-width spaces
    assert "　　　　" not in txt_text


def test_build_and_write_epub3_structure_mimetype_stored_and_xml_escaping(tmp_path: Path):
    chapters = [
        ("第一章 <破庙> & \"夜雪\"", ["风雪 & 寒光 <一闪>。", "他说：'拔剑吧\"少年\"'。"]),
        ("第二章 渡口", ["孤舟横渡。"]),
    ]
    raw_epub = build_epub_bytes("剑道 <真解> & 卷一", "云山客 & <友>", chapters)
    with zipfile.ZipFile(io.BytesIO(raw_epub), "r") as zf:
        names = zf.namelist()
        assert names[0] == "mimetype"
        mt_info = zf.getinfo("mimetype")
        assert mt_info.compress_type == zipfile.ZIP_STORED
        assert zf.read("mimetype") == b"application/epub+zip"

        expected_members = {
            "META-INF/container.xml",
            "OEBPS/style.css",
            "OEBPS/ch0001.xhtml",
            "OEBPS/ch0002.xhtml",
            "OEBPS/nav.xhtml",
            "OEBPS/toc.ncx",
            "OEBPS/content.opf",
        }
        assert expected_members <= set(names)

        # Every XML/XHTML member must parse cleanly as well-formed XML
        for xml_member in (
            "META-INF/container.xml",
            "OEBPS/ch0001.xhtml",
            "OEBPS/ch0002.xhtml",
            "OEBPS/nav.xhtml",
            "OEBPS/toc.ncx",
            "OEBPS/content.opf",
        ):
            ET.fromstring(zf.read(xml_member).decode("utf-8"))

        opf_text = zf.read("OEBPS/content.opf").decode("utf-8")
        assert "云山客 &amp; &lt;友&gt;" in opf_text
        assert "剑道 &lt;真解&gt; &amp; 卷一" in opf_text

    dest = tmp_path / "out" / "book.epub"
    write_epub(dest, "测试书", "", chapters)
    assert dest.is_file()

    # Verify standalone CLI entry imports delivery.write_epub cleanly
    repo_root = Path(__file__).resolve().parents[3]
    proc = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "cli" / "ncc_state.py"), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "export" in proc.stdout
