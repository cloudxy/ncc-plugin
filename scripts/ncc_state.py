#!/usr/bin/env python3
"""ncc_state.py — book.json 单一状态源的确定性读写工具。

子命令:
  init <book_dir> --title T [--genre a,b] [--chapters N]   初始化书目录与 book.json
  status <book_dir>                                          打印状态摘要（退出码恒 0）
  next <book_dir>                                            第一个非 done 章（无则退出 1）
  gate <book_dir> settings|outline|golden [--action check|pass|reject] [--quote Q]
                                        机械检查（默认）/记录作者通过/记录作者打回
  complete <book_dir> <seq> --words N [--score S] [--coverage C] [--report P]  章落盘回写
  sha <file>                                                 打印文件 sha256（前 16 位）

只依赖标准库。状态只从这里（和经理派单回收）写入。
"""
import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

DIRS = [
    "00-策划", "01-设定/人物卡", "02-大纲/卷纲", "02-大纲/章纲",
    "03-文风", "04-正文/_packs", "05-审稿", "06-台账", "07-导出", "memory",
]
GATE_FILES = {
    "settings": ["01-设定/世界观圣经.md", "01-设定/力量体系.md", "01-设定/设定词典.md"],
    "outline": ["02-大纲/总纲.md", "02-大纲/卷纲/卷1.md"],
    "golden": ["04-正文/第0001章-雨夜.md"],  # 实际以 book.json 章节记录为准
}
GATE_NEXT_STAGE = {"settings": "outline", "outline": "golden", "golden": "serial"}


def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def die(msg, code=1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def load(book_dir: Path) -> dict:
    p = book_dir / "book.json"
    if not p.exists():
        die(f"book.json 不存在: {p}（先 init，或按 references/book-state.md 重建）")
    try:
        return json.loads(p.read_text("utf-8"))
    except json.JSONDecodeError as e:
        die(f"book.json 损坏: {e}（按文件存在性+check_chapter.py 重建后 diff 给作者）")


def save(book_dir: Path, data: dict):
    data["updated_at"] = now()
    (book_dir / "book.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8")


def foreshadow_summary(book_dir: Path) -> dict:
    p = book_dir / "06-台账" / "伏笔台账.json"
    if not p.exists():
        return {"total": 0, "resolved": 0, "overdue": 0, "note": "无台账文件"}
    try:
        items = json.loads(p.read_text("utf-8"))
        rows = items if isinstance(items, list) else items.get("items", [])
        resolved = sum(1 for r in rows if r.get("status") == "已回收")
        overdue = sum(1 for r in rows if r.get("status") == "超期未收")
        return {"total": len(rows), "resolved": resolved, "overdue": overdue}
    except (json.JSONDecodeError, AttributeError):
        return {"total": 0, "resolved": 0, "overdue": 0, "note": "台账解析失败"}


def cmd_init(args):
    book_dir = Path(args.book_dir)
    if (book_dir / "book.json").exists():
        die(f"已存在: {book_dir/'book.json'}（不覆盖）")
    for d in DIRS:
        (book_dir / d).mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": 1,
        "title": args.title,
        "genre_tags": [g.strip() for g in (args.genre or "").split(",") if g.strip()],
        "premise": "",
        "target": {"chapters": args.chapters, "words_per_chapter": [3000, 5000]},
        "stage": "ideation",
        "writing_mode": "serial",
        "gates": {k: {"status": "waiting"} for k in
                 ("settings_frozen", "outline_frozen", "golden_accepted")},
        "chapters": [],
        "foreshadows": foreshadow_summary(book_dir),
        "host_spawn": False,
        "updated_at": now(),
    }
    save(book_dir, data)
    print(f"OK init {book_dir} stage=ideation")


def cmd_status(args):
    book_dir = Path(args.book_dir)
    d = load(book_dir)
    chs = d.get("chapters", [])
    done = [c for c in chs if c["status"] == "done"]
    print(f"书: {d.get('title')}  标签: {','.join(d.get('genre_tags', []))}")
    print(f"阶段: {d.get('stage')}  模式: {d.get('writing_mode')}")
    for g, v in d.get("gates", {}).items():
        print(f"闸门 {g}: {v.get('status')}"
              + (f" @ {v.get('at')} 「{v.get('quote')}」" if v.get("status") != "waiting" else ""))
    print(f"章节: {len(done)}/{len(chs)} done")
    for c in chs:
        if c["status"] != "done":
            print(f"  断点: ch{c.get('seq')} status={c['status']} retry={c.get('retry', 0)}")
            break
    fs = foreshadow_summary(book_dir)
    live = dict(d.get("foreshadows", {}))
    live.update(fs)
    print(f"伏笔: 总{live.get('total', 0)} 已收{live.get('resolved', 0)} "
          f"超期{live.get('overdue', 0)} {live.get('note', '')}")
    # SHA 新鲜度
    stale = []
    for c in done:
        rev = c.get("review") or {}
        if rev.get("sha") and c.get("sha") and rev["sha"] != c["sha"]:
            stale.append(c["seq"])
    if stale:
        print(f"警告: 以下章正文已变更但未复评（评审作废）: {stale}")
    print(f"更新于: {d.get('updated_at')}")


def cmd_next(args):
    d = load(Path(args.book_dir))
    for c in d.get("chapters", []):
        if c["status"] != "done":
            print(c["seq"])
            return
    print("NONE")
    sys.exit(1)


def lexicon_count(book_dir: Path) -> int:
    p = book_dir / "01-设定" / "设定词典.md"
    if not p.exists():
        return 0
    rows = 0
    for line in p.read_text("utf-8").splitlines():
        s = line.strip()
        if s.startswith("|") and not set(s) <= {"|", "-", " ", ":"}:
            if "首现章计划" not in s:  # 只排除表头行
                rows += 1
    return rows


def gate_check(book_dir: Path, name: str) -> list:
    problems = []
    if name == "settings":
        for f in GATE_FILES["settings"]:
            p = book_dir / f
            if not p.exists() or not p.read_text("utf-8").strip():
                problems.append(f"缺设定文件或为空: {f}")
        n = lexicon_count(book_dir)
        if n < 30:
            problems.append(f"设定词典条目 {n} < 30")
        hb = book_dir / "01-设定" / "力量体系.md"
        if hb.exists() and "量纲" not in hb.read_text("utf-8"):
            problems.append("力量体系未含量纲定义")
    elif name == "outline":
        for f in GATE_FILES["outline"]:
            p = book_dir / f
            if not p.exists() or not p.read_text("utf-8").strip():
                problems.append(f"缺大纲文件或为空: {f}")
        zs = sorted((book_dir / "02-大纲" / "章纲").glob("ch-*.md"))
        if len(zs) < 3:
            problems.append(f"章纲 {len(zs)} 份 < 3（黄金三章细纲不齐）")
    elif name == "golden":
        d = load(book_dir)
        chs = {c["seq"]: c for c in d.get("chapters", [])}
        for seq in (1, 2, 3):
            c = chs.get(seq)
            if not c or c.get("status") != "done":
                problems.append(f"第 {seq} 章未 done")
                continue
            rev = c.get("review") or {}
            if (rev.get("score") or 0) < 70:
                problems.append(f"第 {seq} 章审稿分 {rev.get('score')} < 70")
            if rev.get("sha") and c.get("sha") and rev["sha"] != c["sha"]:
                problems.append(f"第 {seq} 章正文变更后未复评")
        if not (book_dir / "05-审稿").glob("blind-*"):
            problems.append("缺读者盲评报告（05-审稿/blind-*.md）")
    else:
        problems.append(f"未知闸门: {name}")
    return problems


def cmd_gate(args):
    book_dir = Path(args.book_dir)
    key = {"settings": "settings_frozen", "outline": "outline_frozen",
           "golden": "golden_accepted"}[args.name]
    d = load(book_dir)
    if args.action == "check":
        problems = gate_check(book_dir, args.name)
        if problems:
            print(f"GATE {args.name}: FAIL")
            for p in problems:
                print(f"  - {p}")
            sys.exit(1)
        print(f"GATE {args.name}: 机械条件满足，等待作者确认")
    else:
        d.setdefault("gates", {})[key] = {
            "status": "passed" if args.action == "pass" else "rejected",
            "at": now(), "quote": args.quote or ""}
        if args.action == "pass":
            d["stage"] = GATE_NEXT_STAGE[args.name]
        save(book_dir, d)
        print(f"GATE {args.name}: {args.action} 记录已写入，stage={d['stage']}")


def cmd_complete(args):
    book_dir = Path(args.book_dir)
    d = load(book_dir)
    for c in d.get("chapters", []):
        if c["seq"] == args.seq:
            c["status"] = "done"
            c["word_count"] = args.words
            p = book_dir / c.get("file", "")
            c["sha"] = (hashlib.sha256(p.read_bytes()).hexdigest()[:16]
                        if p.exists() else "")
            if args.score is not None:
                c.setdefault("review", {})
                c["review"].update({
                    "score": args.score,
                    "coverage": args.coverage,
                    "report": args.report or c["review"].get("report", ""),
                    "sha": c["sha"],
                })
            save(book_dir, d)
            print(f"OK complete ch{args.seq} words={args.words} sha={c['sha']}")
            return
    die(f"book.json 中没有 seq={args.seq} 的章")


def cmd_sha(args):
    p = Path(args.file)
    print(hashlib.sha256(p.read_bytes()).hexdigest()[:16])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init")
    p.add_argument("book_dir")
    p.add_argument("--title", required=True)
    p.add_argument("--genre", default="")
    p.add_argument("--chapters", type=int, default=300)
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("status")
    p.add_argument("book_dir")
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("next")
    p.add_argument("book_dir")
    p.set_defaults(fn=cmd_next)

    p = sub.add_parser("gate")
    p.add_argument("book_dir")
    p.add_argument("name", choices=["settings", "outline", "golden"])
    p.add_argument("--action", choices=["check", "pass", "reject"], default="check")
    p.add_argument("--quote", default="")
    p.set_defaults(fn=cmd_gate)

    p = sub.add_parser("complete")
    p.add_argument("book_dir")
    p.add_argument("seq", type=int)
    p.add_argument("--words", type=int, required=True)
    p.add_argument("--score", type=float)
    p.add_argument("--coverage", type=float)
    p.add_argument("--report", default="")
    p.set_defaults(fn=cmd_complete)

    p = sub.add_parser("sha")
    p.add_argument("file")
    p.set_defaults(fn=cmd_sha)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
