"""素材卡：作者的生活素材（本书与跨书）。"""

import re
import sys
from pathlib import Path
from .core import (MATERIAL_DIR, MATERIAL_FIELDS, MATERIAL_REQUIRED, MATERIAL_TRUST, REGIONS, SCENE_DIR, SHARED_MATERIALS, die, load, next_id, normalize_domain, now)


def region_of(dom: str) -> str:
    return next((r for r, doms in REGIONS.items() if dom in doms), "未分")


def material_dirs(book_dir: Path):
    return [(book_dir / MATERIAL_DIR, "M"), (book_dir.parent / SHARED_MATERIALS, "MS")]


def material_cards(book_dir: Path) -> dict:
    """本书 素材/ 与书库根目录 _素材/ 里的全部素材卡：{编号: {path, title, 各字段}}。"""
    cards = {}
    for base, prefix in material_dirs(book_dir):
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*.md")):
            m = re.match(rf"({prefix}-\d{{4}})", p.stem)
            if not m:
                continue
            text = p.read_text("utf-8")
            head = re.search(r"^#\s*\S+\s*(.*)$", text, flags=re.M)
            card = {"path": p, "title": head.group(1).strip() if head else ""}
            for f in MATERIAL_FIELDS:
                mm = re.search(rf"^[-*]\s*{f}[：:][ \t]*(.*)$", text, flags=re.M)
                card[f] = mm.group(1).strip() if mm else ""
            cards[m.group(1)] = card
    return cards


def material_problems(card: dict) -> list:
    problems = [f"缺「{f}」" for f in MATERIAL_REQUIRED if card.get(f, "") in ("", "——", "-", "—")]
    if card.get("可信级") and card["可信级"] not in MATERIAL_TRUST:
        problems.append(f"可信级「{card['可信级']}」应为 {'/'.join(MATERIAL_TRUST)}")
    if card.get("域") and not normalize_domain(card["域"]):
        problems.append(f"域「{card['域']}」不是 24 张底蕴卡之一")
    return problems


def material_refs(text: str) -> list:
    refs = []
    for m in re.finditer(r"素材[：:]\s*([^\n]+)", text):
        refs += re.findall(r"MS?-\d{4}", m.group(1))
    return list(dict.fromkeys(refs))


def material_usage(book_dir: Path) -> dict:
    used = {}
    for p in sorted((book_dir / SCENE_DIR).glob("ch-*.md")):
        seq = int(re.search(r"(\d+)", p.stem).group(1))
        for r in material_refs(p.read_text("utf-8")):
            used.setdefault(r, []).append(seq)
    return used


def cmd_material(a):
    book_dir = Path(a.book_dir)
    load(book_dir)
    cards = material_cards(book_dir)
    if a.action == "add":
        dom = ""
        if a.domain:
            dom = normalize_domain(a.domain)
            if not dom:
                die(f"「{a.domain}」不是 24 张底蕴卡之一（见 skills/ncc/references/domains/README.md）")
        if a.trust and a.trust not in MATERIAL_TRUST:
            die(f"--trust 只能是 {'/'.join(MATERIAL_TRUST)}")
        base, prefix = material_dirs(book_dir)[1 if a.shared else 0]
        mid = next_id([{"id": k} for k in cards], prefix)
        first = a.title or re.split(r"[，。、！？；：,.!?;:\s]", a.content.strip())[0]
        title = re.sub(r"[\\/:*?\"<>|\s，。、！？；：]+", "", first)[:16] or "素材"
        dest = base / region_of(dom) / f"{mid}-{title}.md"
        lines = [f"# {mid} {title}", "", f"- 来源：{a.source}", f"- 内容：{a.content}", f"- 可用处：{a.use}"]
        lines += [f"- {k}：{v}" for k, v in (("可信级", a.trust), ("域", dom), ("题材", a.genre)) if v]
        lines.append(f"- 记录于：{now()[:10]}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("\n".join(lines) + "\n", "utf-8")
        print(f"OK {mid} → {dest.relative_to(base.parent)}")
        return
    used = material_usage(book_dir)
    if a.action == "list":
        for mid, c in cards.items():
            if a.domain and normalize_domain(c.get("域", "")) != normalize_domain(a.domain):
                continue
            if a.unused and mid in used:
                continue
            where = f"  已用：第{'、'.join(map(str, used[mid]))}章" if mid in used else ""
            print(f"{mid} [{c.get('域') or '未分'}] 可用处：{c.get('可用处')}｜{c.get('内容', '')[:30]}"
                  + (f"（{c['可信级']}）" if c.get("可信级") else "") + where)
        if not cards:
            print("（还没有素材卡：material add，或从作者种子 #3、#6 起头）")
        elif a.unused and all(k in used for k in cards):
            print("（素材卡都用过了）")
        return
    bad = 0
    for mid, c in cards.items():
        problems = material_problems(c)
        if problems:
            bad += 1
            print(f"MATERIAL {mid}: FAIL（{c['path'].name}）")
            for p in problems:
                print(f"  - {p}")
    ok = len(cards) - bad
    print(f"素材卡 {len(cards)} 张，合格 {ok} 张，场景卡已引用 {len([k for k in cards if k in used])} 张"
          + ("；开写前建议至少 10 张（作者种子 #3、#6 和生活里的观察都可以记）" if ok < 10 else ""))
    sys.exit(1 if bad else 0)
