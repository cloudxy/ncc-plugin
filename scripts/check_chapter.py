#!/usr/bin/env python3
"""check_chapter.py — 章节机械检查（确定性脚本，替代 LLM 自评）。

用法: check_chapter.py <书目录> <章号seq> [章文件路径]

检查项（退出码非 0 = 不及格）:
  1. 汉字字数在 [words_min, words_max]（默认 3000–5000；读 ncc.config.yaml）
  2. book.json 该章已登记章尾钩子（type + intensity）
  3. AI 味词表命中数（>阈值告警，计入退出码）
  4. 水章：本章未建立、推进或兑现任何承诺（读 06-台账/承诺台账.json；无台账则告警跳过）

只数汉字、剔除 Markdown 标记（做法源自 chinese-novelist-skill 的字数脚本思路）。
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ncc_state import PROMISES, chapter_touches  # noqa: E402

AI_FLAVOR = [
    "仿佛", "宛如", "不禁", "一丝", "一抹", "淡淡的", "微微", "轻轻",
    "瞬间", "刹那间", "顿时", "随即", "紧接着", "与此同时",
    "内心深处", "心中一动", "眼中闪过", "嘴角勾起", "勾起一抹",
    "空气仿佛凝固", "时间仿佛静止", "不言而喻", "毋庸置疑",
]
FLAVOR_LIMIT = 12


def load_config(book_dir: Path):
    words_min, words_max = 3000, 5000
    for cfg in (book_dir.parent / "ncc.config.yaml", book_dir / "ncc.config.yaml"):
        if cfg.exists():
            text = cfg.read_text("utf-8")
            m = re.search(r"words_min:\s*(\d+)", text)
            if m:
                words_min = int(m.group(1))
            m = re.search(r"words_max:\s*(\d+)", text)
            if m:
                words_max = int(m.group(1))
            break
    return words_min, words_max


def find_chapter(book_dir: Path, seq: int, explicit: str):
    if explicit:
        p = Path(explicit)
        return p if p.exists() else None
    for pat in (f"第{seq:04d}章-*.md", f"第{seq}章-*.md"):
        hits = sorted((book_dir / "04-正文").glob(pat))
        if hits:
            return hits[0]
    return None


def han_count(text: str) -> int:
    # 剔除 markdown 标记行/符号后数汉字
    text = re.sub(r"^[#>*\-|`\s]+", "", text, flags=re.M)
    return len(re.findall(r"[\u4e00-\u9fff]", text))


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    book_dir = Path(sys.argv[1])
    seq = int(sys.argv[2])
    explicit = sys.argv[3] if len(sys.argv) > 3 else ""

    problems, warns = [], []

    f = find_chapter(book_dir, seq, explicit)
    if not f:
        print(json.dumps({"seq": seq, "pass": False,
                          "problems": [f"找不到章节文件（04-正文/第{seq:04d}章-*.md）"]},
                         ensure_ascii=False))
        sys.exit(1)
    text = f.read_text("utf-8")
    words = han_count(text)
    words_min, words_max = load_config(book_dir)
    if words < words_min:
        problems.append(f"字数 {words} < {words_min}")
    elif words > words_max:
        warns.append(f"字数 {words} > {words_max}（超上限，确认是否拆章）")

    hook = None
    bj = book_dir / "book.json"
    if bj.exists():
        try:
            d = json.loads(bj.read_text("utf-8"))
            for c in d.get("chapters", []):
                if c.get("seq") == seq:
                    hook = c.get("hook")
                    break
        except json.JSONDecodeError:
            warns.append("book.json 解析失败，跳过钩子核对")
    if not hook or not hook.get("type") or not hook.get("intensity"):
        problems.append("book.json 未登记章尾钩子（type+intensity）")

    hits = {w: text.count(w) for w in AI_FLAVOR if text.count(w)}
    total_hits = sum(hits.values())
    if total_hits > FLAVOR_LIMIT:
        problems.append(f"AI 味词命中 {total_hits} > {FLAVOR_LIMIT}: "
                        + ", ".join(f"{k}x{v}" for k, v in
                                    sorted(hits.items(), key=lambda x: -x[1])[:6]))
    elif total_hits > FLAVOR_LIMIT // 2:
        warns.append(f"AI 味词命中 {total_hits}（接近阈值）")

    ledger = book_dir / PROMISES
    touches = []
    if ledger.exists():
        try:
            items = json.loads(ledger.read_text("utf-8")).get("items", [])
            touches = chapter_touches(items, seq)
            if not touches:
                problems.append("水章：本章未建立、推进或兑现任何承诺（先回写承诺台账，或补写推进）")
        except (json.JSONDecodeError, AttributeError):
            warns.append("承诺台账解析失败，跳过水章检测")
    else:
        warns.append("无承诺台账，跳过水章检测（v0.1 书先运行 ncc_state.py migrate）")

    result = {
        "seq": seq, "file": str(f), "han_words": words,
        "band": [words_min, words_max], "hook": hook,
        "ai_flavor_hits": total_hits, "promise_touches": [f"{i} {k}" for i, k in touches],
        "warnings": warns,
        "problems": problems, "pass": not problems,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if not problems else 1)


if __name__ == "__main__":
    main()
