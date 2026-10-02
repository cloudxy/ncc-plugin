"""视图只生成（七律二）：author-intent、续写状态卡、台账视图、生成区块、render 与 check、布局迁移。"""

import re
import sys
from pathlib import Path
from .core import (FACTS, FOCUS_VIEW, INTENT_VIEW, KNOWLEDGE, L, LEDGER_VIEWS, MEMORY_DIR, view_head, OLD_BOOK_PATHS, OLD_PACKS, OLD_ROOT_PATHS, OPEN_STATES, PACK_DIR, PROMISES, PROMISE_TYPES, SIGNING_POINTS, current_chapter, ledger, load, next_seq, read_json)
from .ledgers import focus_core, history_problem, promise_overdue, promise_summary, reader_now_lines
from .learning import pref_file, pref_load
from .memory import memory_roles, memory_view


GEN_BEGIN = "<!-- ncc:生成区块 开始（render 与 report --write 会整块重写；判断写在区块外） -->"


GEN_END = "<!-- ncc:生成区块 结束 -->"


GEN_RE = re.compile(re.escape(GEN_BEGIN) + r".*?" + re.escape(GEN_END), re.S)


def outside_block(text: str) -> str:
    return GEN_RE.sub("", text)


def write_block(path: Path, body: str, skeleton: str = ""):
    """把生成内容写进文件里的生成区块；区块外作者与角色写的内容原样保留。"""
    block = f"{GEN_BEGIN}\n{body.rstrip()}\n{GEN_END}"
    if path.exists():
        old = path.read_text("utf-8")
        new = GEN_RE.sub(lambda m: block, old, count=1) if GEN_RE.search(old) else block + "\n\n" + old
    else:
        new = block + "\n\n" + skeleton
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new.rstrip() + "\n", "utf-8")


def intent_view(book_dir: Path, d: dict) -> str:
    soul, ct = d.get("soul", {}), d.get("contract", {})
    v = lambda x: x or "（未填）"
    st = soul.get("status") or "未填"
    when = f"，最晚 {soul['deadline']} 定下" if st == "暂定" and soul.get("deadline") else ""
    dislikes = pref_load(pref_file(book_dir)).get("dislikes", [])
    signing = ct.get("signing", {})
    lines = [f"# 创作意图：{d.get('title')}", "",
             view_head("`book.json` 与 `_作者/偏好.json`", "书魂用 soul，类型契约与目标读者用 contract，签约点用 sign，雷点用 pref dislike"), "",
             f"## 书魂（{st}{when}）", "",
             f"- 主题之问：{v(soul.get('question'))}", f"- 主角的答案：{v(soul.get('answer'))}",
             f"- 世界的不公：{v(soul.get('injustice'))}", f"- 终局的回答：{v(soul.get('ending'))}",
             f"- 主角弧光：{v(soul.get('arc'))}", "",
             "## 类型契约", "", f"- 主契约：{v(ct.get('main'))}", f"- 附加契约：{'、'.join(ct.get('extras', [])) or '（无）'}",
             f"- 毒点：{'、'.join(ct.get('poison', [])) or '（未填）'}", f"- 目标读者：{v(ct.get('audience'))}", "",
             "### 签约点（黄金三章内必须落地）", "", "| 签约点 | 落在 |", "|---|---|"]
    lines += [f"| {pt} | {'第' + str(signing[pt]) + '章' if pt in signing else '（未落地）'} |" for pt in SIGNING_POINTS]
    lines += ["", "## 作者雷点（来自偏好，硬约束）", ""] + ([f"- {x}" for x in dislikes] or ["- （无）"])
    return "\n".join(lines) + "\n"


def focus_view(book_dir: Path, d: dict) -> str:
    seq = next_seq(d)
    lines = [f"# 续写状态卡（写第 {seq} 章前）", "",
             view_head("`book.json`、场景卡与三本账", "结束时的时间地点与下一章要接的事用 chapter end，其余改场景卡和台账"), "",
             "## 当前位置", ""] + focus_core(book_dir, d, seq) + [""] + reader_now_lines(book_dir, d, seq, top=3)
    return "\n".join(lines) + "\n"


def ledger_view(book_dir: Path, d: dict, kind: str) -> str:
    if kind == "promise":
        items, cur = ledger(book_dir, PROMISES)["items"], current_chapter(d)
        s = promise_summary(book_dir, d)
        row = lambda p: (f"| {p['id']} | {p['type']} | {p['content']} | {p.get('strength')} | {p.get('created_ch')} | "
                         + (f"{p['window'][0]}–{p['window'][1]}" if p.get("window") else (p.get("deadline") or "—"))
                         + f" | {p['status']}{'（逾期）' if promise_overdue(p, cur) else ''} |")
        head = ["| 编号 | 类型 | 内容 | 强度 | 建立 | 兑现窗口／最晚 | 状态 |", "|---|---|---|---|---|---|---|"]
        order = {t: i for i, t in enumerate(PROMISE_TYPES)}
        open_ = sorted((p for p in items if p.get("status") in OPEN_STATES),
                       key=lambda p: (order.get(p["type"], 99), -(p.get("strength") or 0)))
        lines = ["# 承诺台账", "", view_head("`06-台账/承诺台账.json`", "promise add/touch/resolve/reschedule/drop"), "",
                 f"开放 {s['open']}、已兑现 {s['resolved']}、作废 {s['dropped']}、逾期 {s['overdue']}；"
                 f"期权 {s['options']}、母题 {s['motifs']}、暂定决策 {s['pending_decisions']}", "",
                 "## 开放中", ""] + (head + [row(p) for p in open_] if open_ else ["（无）"])
        for title, t in (("名场面清单", "名场面"), ("核心意象（母题）", "母题")):
            ps = [p for p in items if p.get("type") == t]
            lines += ["", f"## {title}", ""] + (head + [row(p) for p in ps] if ps else ["（无）"])
        closed = [p for p in items if p.get("status") not in OPEN_STATES]
        lines += ["", "## 已兑现与作废", ""] + (head + [row(p) for p in closed] if closed else ["（无）"])
    elif kind == "know":
        items = ledger(book_dir, KNOWLEDGE)["items"]
        lines = ["# 知情台账", "", view_head("`06-台账/知情台账.json`", "know add/learn"), "",
                 "| 编号 | 事实 | 自第几章 | 知道 | 还不知道 |", "|---|---|---|---|---|"]
        lines += [f"| {k['id']} | {k['fact']} | {k.get('since_ch')} | {'、'.join(k.get('known_by', [])) or '—'} | "
                  f"{'、'.join(k.get('unknown_to', [])) or '—'} |" for k in items] or ["| — | （无） | | | |"]
    else:
        facts = read_json(book_dir / FACTS, {"facts": {}}).get("facts", {})
        lines = ["# 知识台账", "", view_head("`06-台账/知识台账.json`", "fact set"), "",
                 "| 键 | 值 | 类别 | 第几章 | 来源 |", "|---|---|---|---|---|"]
        lines += [f"| {k} | {f['value']} | {f.get('category') or '—'} | {f.get('ch')} | {f.get('source') or '未注'} |"
                  for k, f in facts.items()] or ["| — | （无） | | | |"]
    return "\n".join(lines) + "\n"


def views(book_dir: Path, d: dict) -> dict:
    out = {INTENT_VIEW: intent_view(book_dir, d), FOCUS_VIEW: focus_view(book_dir, d)}
    out.update({rel: ledger_view(book_dir, d, kind) for rel, kind in LEDGER_VIEWS.items()})
    out.update({f"{MEMORY_DIR}/{role}.md": memory_view(book_dir, role) for role in memory_roles(book_dir)})
    return out


def render(book_dir: Path) -> list:
    d = read_json(book_dir / "book.json", {})
    changed = []
    for rel, text in views(book_dir, d).items():
        p = book_dir / rel
        if not p.exists() or p.read_text("utf-8") != text:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, "utf-8")
            changed.append(rel)
    return changed


def cmd_render(a):
    book_dir = Path(a.book_dir)
    load(book_dir)
    changed = render(book_dir)
    print("OK 视图已是最新" if not changed else "OK 重新生成：" + "、".join(changed))


DATA_IN_PROSE = re.compile(r"\d+(?:\.\d+)?\s*(?:里|公里|千米|日|天|时辰|两|文|贯|钱|斤|丈|尺|米|元|块)")


def cmd_check(a):
    """七律自查：视图与源头逐字一致、历史只追加、没有旧布局残留、数据不散在设定正文里。"""
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    problems, warns = [], []
    for rel, text in views(book_dir, d).items():
        p = book_dir / rel
        if not p.exists():
            problems.append(f"缺视图：{rel}（render 生成）")
        elif p.read_text("utf-8") != text:
            problems.append(f"视图与源头不一致：{rel}（被手改了，或源头改了还没 render；手改的内容先改到源头，再 render）")
    bad = history_problem(book_dir, d)
    if bad:
        problems.append(bad)
    for old, new in OLD_BOOK_PATHS:
        if (book_dir / old).exists() and old not in (INTENT_VIEW, FOCUS_VIEW):
            problems.append(f"旧布局残留：{old}（应在 {new}；运行 migrate）")
    for old, new in OLD_ROOT_PATHS:
        if (book_dir.parent / old).exists():
            problems.append(f"书库根目录有旧布局残留：{old}（应在 {new}；运行 migrate）")
    bible = book_dir / L("bible")
    if bible.exists():
        hits = DATA_IN_PROSE.findall(bible.read_text("utf-8"))
        if hits:
            warns.append(f"世界观圣经里有具体数据（{'、'.join(dict.fromkeys(hits[:5]))}）：数据只放知识台账（fact set），圣经里写台账的键")
    for line in problems:
        print(f"CHECK FAIL  {line}")
    for line in warns:
        print(f"CHECK WARN  {line}")
    if not problems and not warns:
        print("CHECK OK  视图都是最新的，历史没被改写，没有旧布局残留")
    sys.exit(1 if problems else 0)


def migrate_layout(book_dir: Path, d: dict) -> list:
    """schema 2 → 3：机器工作件进 .ncc/，读者反馈进 05-审稿/，作者资产进书库根目录 _作者/，派生数据移出 book.json。"""
    import shutil
    moved = []
    for base, pairs in ((book_dir, OLD_BOOK_PATHS), (book_dir.parent, OLD_ROOT_PATHS)):
        for old, new in pairs:
            src, dst = base / old, base / new
            if not src.exists():
                continue
            if src.is_dir() and dst.is_dir():          # 目标目录已建好（init 会建）：逐个搬进去，不覆盖
                for child in sorted(src.iterdir()):
                    if not (dst / child.name).exists():
                        shutil.move(str(child), str(dst / child.name))
                if not any(src.iterdir()):
                    src.rmdir()
                moved.append(f"{old} → {new}")
            elif not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                moved.append(f"{old} → {new}")
    d.pop("promises", None)
    d.setdefault("contract", {}).setdefault("audience", "")
    for c in d.get("chapters", []):
        pack = str(c.get("pack") or "")
        if pack.startswith(OLD_PACKS + "/") and pack.endswith(".md"):
            c["pack"] = pack.replace(OLD_PACKS + "/", f"{PACK_DIR}/")
        elif pack.endswith(".json"):
            c["pack"] = None
    return moved
