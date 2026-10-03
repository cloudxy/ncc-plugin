"""设定类目：类目表（注册表＋作者覆盖层）、本书的类目研判、类目卡。只往下依赖 core。"""

import re
import sys
from pathlib import Path
from .core import CATEGORY_DIR, L, REGISTRY, category_catalog, die, load, now, save, split_names


COMMON = tuple(REGISTRY["setting_categories"]["common"])


NUMBER = re.compile(r"\d+(?:\.\d+)?\s*(?:里|公里|千米|日|天|年|岁|两|文|贯|钱|斤|丈|尺|米|元|块|万|亿|人|个|名)")


EMPTY = ("", "——", "-", "—")


def book_cats(d: dict) -> dict:
    sc = d.setdefault("setting_categories", {})
    sc.setdefault("used", {})
    sc.setdefault("none", "")
    return sc


def resolve_cat(name: str, d: dict, catalog: dict):
    """类目名或别名 → 规范名；本书新提的类目也认。"""
    used = book_cats(d)["used"]
    if name in catalog or name in used:
        return name
    for k, spec in list(catalog.items()) + [(k, v) for k, v in used.items() if v.get("custom")]:
        if name in spec.get("alias", []):
            return k
    return None


def cat_fields(name: str, d: dict, catalog: dict):
    spec = book_cats(d)["used"].get(name, {})
    if not spec.get("custom"):
        spec = catalog.get(name, {})
    req = list(spec.get("required", []))
    req += [c for c in COMMON if c not in req]
    return req, list(spec.get("optional", []))


def card_fields(text: str) -> dict:
    return {m.group(1).strip(): m.group(2).strip() for m in re.finditer(r"^[-*]\s*([^：:\n]+)[：:][ \t]*(.*)$", text, flags=re.M)}


def category_cards(book_dir: Path) -> dict:
    """{类目: [(名字, 路径, 字段)]}"""
    base = book_dir / CATEGORY_DIR
    out = {}
    if base.is_dir():
        for cat_dir in sorted(p for p in base.iterdir() if p.is_dir()):
            for p in sorted(cat_dir.glob("*.md")):
                out.setdefault(cat_dir.name, []).append((p.stem, p, card_fields(p.read_text("utf-8"))))
    return out


def lexicon_names(book_dir: Path) -> set:
    p = book_dir / L("lexicon")
    if not p.exists():
        return set()
    names = set()
    for line in p.read_text("utf-8").splitlines():
        s = line.strip()
        if s.startswith("|") and not set(s) <= {"|", "-", " ", ":"}:
            first = s.strip("|").split("|")[0].strip()
            if first and first != "词条":
                names.add(first)
    return names


def setting_problems(book_dir: Path, d: dict):
    """类目研判做了没有、选用的类目有没有卡、卡的必填字段、名字进没进词典、数字有没有散在卡里。"""
    catalog = category_catalog(book_dir)
    sc = book_cats(d)
    problems, warns = [], []
    if not sc["used"] and not sc["none"]:
        problems.append("还没做设定类目研判：本书用哪些类目（setting use／setting new），或一个都不用（setting none --why）")
    cards = category_cards(book_dir)
    for cat in sc["used"]:
        if not cards.get(cat):
            problems.append(f"类目「{cat}」还没有卡（setting add {cat} <名字>）")
    lex = lexicon_names(book_dir)
    for cat, lst in cards.items():
        if cat not in sc["used"]:
            warns.append(f"{CATEGORY_DIR}/{cat}/ 不在本书选用的类目里（setting use 补选，或删掉）")
            continue
        req, _ = cat_fields(cat, d, catalog)
        for name, p, f in lst:
            missing = [x for x in req if f.get(x, "") in EMPTY]
            if missing:
                problems.append(f"{cat}/{name} 缺：{'、'.join(missing)}（没定的写「待定」）")
            if lex and name not in lex:
                warns.append(f"{cat}/{name} 还没进设定词典")
            nums = NUMBER.findall(p.read_text("utf-8"))
            if nums:
                warns.append(f"{cat}/{name} 里有具体数字（{'、'.join(dict.fromkeys(nums[:3]))}）：数字放知识台账（fact set），卡里写台账的键")
    return problems, warns


def cmd_setting(a):
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    catalog = category_catalog(book_dir)
    sc = book_cats(d)
    genres = set(d.get("genre_tags", []))
    if a.action == "catalog":
        for name, spec in catalog.items():
            fit = genres & set(spec.get("genres", []))
            mark = "✓ 已选用" if name in sc["used"] else ("★ 题材相关" if fit else "")
            print(f"{name}（{'、'.join(spec.get('alias', [])) or '—'}）{mark}\n  必填：{'、'.join(cat_fields(name, d, catalog)[0])}")
        print("表里装不下的，用 setting new 新提一类（给出字段和为什么现有类目装不下），作者在 G1 确认")
        return
    if a.action in ("use", "new", "none"):
        if a.action == "none":
            if sc["used"]:
                die(f"已经选用了 {'、'.join(sc['used'])}；一个都不用的话先把选用撤掉（setting drop）")
            sc["none"] = a.why
            msg = f"OK 本书不用设定类目：{a.why}"
        elif a.action == "use":
            got = []
            for raw in a.names:
                name = resolve_cat(raw, d, catalog)
                if not name:
                    die(f"类目表里没有「{raw}」：setting catalog 看现有类目；确实装不下就 setting new")
                spec = sc["used"].setdefault(name, {"custom": False})
                spec.update(why=a.why, at=now())
                got.append(name)
            sc["none"] = ""
            msg = f"OK 选用类目：{'、'.join(got)}（它会怎么进剧情：{a.why}）"
        else:
            if resolve_cat(a.name, d, catalog):
                die(f"已有类目「{resolve_cat(a.name, d, catalog)}」，用 setting use")
            req = split_names(a.required)
            if len(req) < 3:
                die("--required 至少三个字段（用逗号或顿号隔开）；只留会进剧情的")
            req += [c for c in COMMON if c not in req]
            sc["used"][a.name] = {"why": a.why, "custom": True, "required": req, "optional": split_names(a.optional),
                                  "gap": a.gap, "alias": split_names(a.alias), "at": now()}
            sc["none"] = ""
            msg = f"OK 本书新类目「{a.name}」：必填 {'、'.join(req)}（为什么现有类目装不下：{a.gap}）"
        save(book_dir, d)
        print(msg)
        return
    if a.action == "drop":
        name = resolve_cat(a.name, d, catalog)
        if name not in sc["used"]:
            die(f"本书没有选用「{a.name}」")
        if category_cards(book_dir).get(name):
            die(f"「{name}」下已经有卡；先把卡移走或删掉")
        sc["used"].pop(name)
        save(book_dir, d)
        print(f"OK 不再选用「{name}」")
        return
    if a.action == "add":
        cat = resolve_cat(a.cat, d, catalog)
        if not cat or cat not in sc["used"]:
            die(f"本书还没选用类目「{a.cat}」（setting use {a.cat} --why …）")
        dest = book_dir / CATEGORY_DIR / cat / f"{a.name}.md"
        if dest.exists():
            die(f"已存在：{dest.relative_to(book_dir)}")
        req, opt = cat_fields(cat, d, catalog)
        lines = [f"# {cat}：{a.name}", "", "> 没定的写「待定」；具体数字放知识台账（fact set），这里写台账的键。秘密写在这里，谁知道记知情台账。", ""]
        lines += [f"- {f}：" for f in req]
        if opt:
            lines += ["", "## 选填", ""] + [f"- {f}：" for f in opt]
        lines += ["", "## 备注", ""]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("\n".join(lines) + "\n", "utf-8")
        print(f"OK {dest.relative_to(book_dir)}（必填 {len(req)} 项）")
        return
    if a.action == "list":
        cards = category_cards(book_dir)
        if sc["none"]:
            print(f"本书不用设定类目：{sc['none']}")
        for cat, spec in sc["used"].items():
            lst = cards.get(cat, [])
            print(f"{cat}{'（本书新提）' if spec.get('custom') else ''}：{len(lst)} 张——{spec.get('why')}")
            for name, _, f in lst:
                pending = sum(1 for v in f.values() if v.startswith("待定"))
                print(f"  - {name}" + (f"（待定 {pending} 项）" if pending else ""))
        if not sc["used"] and not sc["none"]:
            print("还没做类目研判（setting catalog 看类目表）")
        return
    problems, warns = setting_problems(book_dir, d)
    for p in problems:
        print(f"SETTING FAIL  {p}")
    for w in warns:
        print(f"SETTING WARN  {w}")
    if not problems and not warns:
        print("SETTING OK  类目研判已做，卡的必填字段齐全")
    sys.exit(1 if problems else 0)
