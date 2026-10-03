#!/usr/bin/env python3
"""创作前准备：独立工作区、资料索引、六类成果、缺项与有版本依据的交接。"""

import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile


ROOT = Path(__file__).resolve().parent.parent
SPEC = json.loads((ROOT / "workflow/registry.json").read_text("utf-8"))["preparation"]
TASKS = SPEC["tasks"]


def fail(message):
    raise ValueError(message)


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")


def read_json(path):
    return json.loads(path.read_text("utf-8"))


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        temp = Path(f.name)
        f.write(data)
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def nonempty(value, name):
    if not value or not value.strip():
        fail(f"{name} 不能为空")
    return value.strip()


def safe_local(work, relative):
    p = work / relative
    if not p.resolve().is_relative_to(work.resolve()):
        fail(f"工作文件越出准备目录：{relative}")
    return p


def load(work):
    p = work / SPEC["state"]
    if not p.is_file():
        fail(f"没有准备工作区：{p}；先运行 init（无需 book.json）")
    d = read_json(p)
    if d.get("schema") != SPEC["schema"]:
        fail("不支持的准备工作区版本")
    return d


def save(work, d, action):
    d["updated_at"] = now()
    atomic(safe_local(work, SPEC["state"]), encoded(d) + b"\n")
    log = safe_local(work, f"{SPEC['work']}/events.jsonl")
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"at": d["updated_at"], "action": action}, ensure_ascii=False) + "\n")


@contextmanager
def lock(work):
    p = safe_local(work, f"{SPEC['work']}/write.lock")
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        fail(f"准备目录有另一个写操作；若上次异常退出，确认进程结束后清理 {p}")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(str(os.getpid()))
        yield
    finally:
        p.unlink(missing_ok=True)


def next_id(rows, prefix):
    n = max([int(x["id"].split("-")[-1]) for x in rows] or [0]) + 1
    return f"{prefix}-{n:04d}"


def find(rows, ident):
    for r in rows:
        if r["id"] == ident:
            return r
    fail(f"没有编号 {ident}")


def read_stable(path):
    before = path.stat()
    if before.st_size > SPEC["max_file_bytes"]:
        fail(f"文件超过 {SPEC['max_file_bytes']} 字节，请先分段或转换")
    data = path.read_bytes()
    after = path.stat()
    if (before.st_mtime_ns, before.st_size, before.st_ino) != (after.st_mtime_ns, after.st_size, after.st_ino):
        fail("读取期间文件发生变化，请重试")
    return data


def index_path(work):
    return safe_local(work, f"{SPEC['work']}/index.json")


def index(work):
    p = index_path(work)
    return read_json(p) if p.exists() else {"files": [], "errors": [], "scanned_at": None}


def source_path(d, rec):
    base = Path(find(d["sources"], rec["root"])["path"])
    p = base if rec["relative"] == "." else base / rec["relative"]
    if base.is_symlink() or p.is_symlink() or (base.is_dir() and not p.resolve().is_relative_to(base.resolve())):
        fail(f"来源变成了链接或越出资料根：{rec['id']}")
    return p


def source_text(d, rec):
    if rec["status"] != "readable":
        fail(f"来源不可读取：{rec['id']} [{rec['status']}]")
    data = read_stable(source_path(d, rec))
    if digest(data) != rec["sha"]:
        fail(f"来源已改变：{rec['id']}；重新 scan 并复核引用")
    return data.decode("utf-8-sig")


def cmd_init(a):
    work = a.work
    if (work / SPEC["state"]).exists():
        fail("准备工作区已存在，不覆盖；status 查看，继续使用原目录")
    d = {"schema": SPEC["schema"], "title": nonempty(a.title, "标题"),
         "purpose": nonempty(a.purpose, "目标"), "scope": nonempty(a.scope, "范围"),
         "tasks": list(dict.fromkeys(a.task or TASKS)), "sources": [], "items": [], "issues": [], "reviews": {}}
    save(work, d, "init")
    print(f"OK 准备工作区：{work}（无需建书；可从空白创建资料或设定）")


def cmd_source(a):
    d = load(a.work)
    p = a.path.expanduser().resolve(strict=True)
    if not p.is_file() and not p.is_dir():
        fail("来源必须是文件或目录")
    if any(s["path"] == str(p) for s in d["sources"]):
        fail("来源已登记，不重复添加")
    sid = next_id(d["sources"], "R")
    d["sources"].append({"id": sid, "path": str(p), "label": a.label or p.name, "kind": a.kind})
    save(a.work, d, f"source {sid}")
    print(f"OK {sid} {p}；运行 scan 读取索引")


def scan(work, d):
    previous = {r["id"]: r for r in index(work)["files"]}
    rows, errors = [], []
    excluded = {safe_local(work, x).resolve() for x in (SPEC["state"], SPEC["work"], SPEC["output"])}

    def visit(base, p, sid):
        rel = "." if p == base else p.relative_to(base).as_posix()
        ident = "S-" + digest(f"{sid}/{rel}".encode())[:16]
        rec = {"id": ident, "root": sid, "relative": rel, "status": "unread", "sha": None}
        try:
            if p.is_symlink():
                rec.update(status="link", target=os.readlink(p), exists=p.exists())
            elif p.suffix.lower() not in SPEC["text_extensions"]:
                rec.update(status="unsupported", bytes=p.stat().st_size)
            else:
                data = read_stable(p)
                rec.update(sha=digest(data), bytes=len(data))
                text = data.decode("utf-8-sig")
                rec.update(status="readable", lines=len(text.splitlines()),
                           headings=[{"line": i, "title": l.lstrip("#").strip()}
                                     for i, l in enumerate(text.splitlines(), 1) if re.match(r"^#{1,6} ", l)])
        except (OSError, UnicodeError, ValueError) as e:
            rec.update(status="unreadable", error=str(e))
        old = previous.get(ident)
        rec["change"] = "new" if not old else ("unchanged" if all(old.get(k) == rec.get(k) for k in
                             ("status", "sha", "target", "exists", "bytes")) else "changed")
        rows.append(rec)

    for s in d["sources"]:
        base = Path(s["path"])
        if base.is_symlink():
            errors.append(f"{s['id']} 来源根已变成符号链接，需重新确认真实来源：{base}")
        elif base.is_file():
            visit(base, base, s["id"])
        elif base.is_dir():
            def walk_error(e):
                errors.append(f"{s['id']}: {e}")
            for cur, dirs, files in os.walk(base, followlinks=False, onerror=walk_error):
                cur = Path(cur)
                keep = []
                for name in sorted(dirs):
                    p = cur / name
                    if name.startswith(".") or p.resolve() in excluded:
                        continue
                    if p.is_symlink():
                        visit(base, p, s["id"])
                    else:
                        keep.append(name)
                dirs[:] = keep
                for name in sorted(files):
                    p = cur / name
                    if not name.startswith(".") and p.resolve() not in excluded:
                        visit(base, p, s["id"])
        else:
            errors.append(f"{s['id']} 来源根不存在：{base}")
    current = {r["id"] for r in rows}
    rows += [{**r, "status": "missing", "change": "missing"} for sid, r in previous.items() if sid not in current]
    result = {"scanned_at": now(), "files": rows, "errors": errors}
    atomic(index_path(work), encoded(result) + b"\n")
    return result


def cmd_scan(a):
    d = load(a.work)
    result = scan(a.work, d)
    counts = Counter(r["status"] for r in result["files"])
    groups = defaultdict(list)
    for r in result["files"]:
        if r["status"] == "readable":
            groups[r["sha"]].append(r["id"])
    print(json.dumps({"coverage": counts, "duplicate_groups": [v for v in groups.values() if len(v) > 1],
                      "changes": Counter(r["change"] for r in result["files"]), "errors": result["errors"]},
                     ensure_ascii=False, indent=2))


def cmd_search(a):
    d = load(a.work)
    if a.limit < 1:
        fail("--limit 必须大于 0")
    words = [w.casefold() for w in a.words if w.strip()]
    if not words:
        fail("搜索词不能为空")
    results, skipped = [], []
    for rec in index(a.work)["files"]:
        if rec["status"] != "readable":
            continue
        try:
            text = source_text(d, rec)
        except (OSError, ValueError, UnicodeError) as e:
            skipped.append(str(e))
            continue
        path_match = all(w in rec["relative"].casefold() for w in words)
        for n, line in enumerate(text.splitlines(), 1):
            if all(w in line.casefold() for w in words) or (path_match and n == 1):
                results.append((rec, n, line))
    for rec, n, line in results[:a.limit]:
        print(f"{rec['id']}:{n} [{rec['root']}/{rec['relative']}] {line[:300]}")
    print(f"匹配 {len(results)} 处，展示 {min(len(results), a.limit)} 处；show 可读完整行段")
    for e in skipped:
        print(f"未检索：{e}", file=sys.stderr)


def cmd_show(a):
    d = load(a.work)
    r = find(index(a.work)["files"], a.id)
    text = source_text(d, r).splitlines()
    end = a.end if a.end is not None else min(a.start + 79, len(text))
    if a.start < 1 or end < a.start or end > len(text):
        fail(f"行号范围无效；来源共 {len(text)} 行")
    print(f"{r['id']} [{r['root']}/{r['relative']}] SHA {r['sha']}")
    for n in range(a.start, end + 1):
        print(f"{n}: {text[n-1]}")


def references(work, d, args):
    refs = []
    for raw in args:
        m = re.fullmatch(r"(S-[0-9a-f]{16}):(\d+)-(\d+)", raw)
        if not m:
            fail("来源格式应为 S-编号:起始行-结束行（search / show 查编号）")
        rec = find(index(work)["files"], m[1])
        lines = source_text(d, rec).splitlines()
        start, end = int(m[2]), int(m[3])
        if not 1 <= start <= end <= len(lines):
            fail(f"来源行范围无效：{raw}")
        refs.append({"source": rec["id"], "root": rec["root"], "relative": rec["relative"],
                     "sha": rec["sha"], "start": start, "end": end})
    return refs


def cmd_item(a):
    d = load(a.work)
    data = read_stable(a.file)
    nonempty(data.decode("utf-8-sig"), "成果正文")
    refs = references(a.work, d, a.ref)
    citations = [nonempty(x, "外部出处") for x in a.citation]
    if a.nature == "fact" and not refs and not citations:
        fail("事实资料必须带来源；原创虚构用 fiction，未核推演用 inference")
    basis = nonempty(a.basis, "整理或创建依据")
    depends = list(dict.fromkeys(a.depends))
    for ident in depends:
        find(d["items"], ident)
    ident = a.id or next_id(d["items"], "P")
    if ident in depends:
        fail("成果不能依赖自身")
    old = find(d["items"], ident) if a.id else None
    path = old["path"] if old else f"{SPEC['output']}/{ident}.md"
    dest = safe_local(a.work, path)
    if dest.exists():
        old_data = dest.read_bytes()
        atomic(safe_local(a.work, f"{SPEC['work']}/history/{ident}-{digest(old_data)}.md"), old_data)
    row = {"id": ident, "title": nonempty(a.title, "成果名"), "task": a.task,
           "nature": a.nature, "scope": nonempty(a.scope or d["scope"], "范围"), "path": path,
           "sha": digest(data), "refs": refs, "citations": citations, "basis": basis,
           "depends": depends, "state": "candidate", "decision": "", "updated_at": now()}
    if old:
        d["items"][d["items"].index(old)] = row
    else:
        d["items"].append(row)
    atomic(safe_local(a.work, f"{SPEC['work']}/history/{ident}-{digest(data)}.md"), data)
    atomic(dest, data)
    save(a.work, d, f"item {ident} {a.task}")
    print(f"OK {ident} {TASKS[a.task]} → {dest}；候选，需记录采用或处置决定")


def item_problems(work, d, item):
    problems = []
    try:
        if digest(read_stable(safe_local(work, item["path"]))) != item["sha"]:
            problems.append(f"{item['id']} 成果已修改，重新 item --id 登记并复核")
    except (OSError, ValueError) as e:
        problems.append(f"{item['id']} 成果不可读：{e}")
    for ref in item["refs"]:
        try:
            if digest(read_stable(source_path(d, ref))) != ref["sha"]:
                problems.append(f"{item['id']} 来源 {ref['source']} 已变化，需复核")
        except (OSError, ValueError) as e:
            problems.append(f"{item['id']} 来源 {ref['source']} 失效：{e}")
    return problems


def cmd_decide(a):
    d = load(a.work)
    r = find(d["items"], a.id)
    reason = nonempty(a.reason, "决定依据")
    if a.state == "accepted":
        problems = item_problems(a.work, d, r)
        if problems:
            fail("；".join(problems))
        if r["nature"] == "inference":
            fail("推演仍未核实：转为有来源的 fact 或明确虚构的 fiction 后再采用")
    r.update(state=a.state, decision=reason)
    save(a.work, d, f"decide {a.id} {a.state}")
    print(f"OK {a.id} {a.state}；仅对范围「{r['scope']}」有效")


def closure(d, scope):
    selected = [i for i in d["items"] if i["scope"] in (scope, "*") and i["state"] not in ("rejected", "shelved")]
    seen = {i["id"] for i in selected}
    for r in selected:
        for ident in r["depends"]:
            if ident not in seen:
                selected.append(find(d["items"], ident))
                seen.add(ident)
    return selected


def affected(d, scope, items):
    ids = {i["id"] for i in items}
    return [i for i in d["issues"] if i["scope"] in (scope, "*") or ids.intersection(i["items"])]


def live_stamp(work, d, items):
    values = []
    for item in items:
        values.append({"item": item, "problems": item_problems(work, d, item)})
    return digest(encoded(values))


def cmd_issue(a):
    d = load(a.work)
    ids = list(dict.fromkeys(a.item))
    for ident in ids:
        find(d["items"], ident)
    ident = next_id(d["issues"], "Q")
    row = {"id": ident, "kind": a.kind, "text": nonempty(a.text, "问题"),
           "scope": nonempty(a.scope or d["scope"], "范围"), "items": ids, "blocking": a.blocking,
           "evidence": nonempty(a.evidence, "证据"), "next": nonempty(a.next, "补全动作"),
           "state": "open", "resolution": "", "until": "", "stamp": None}
    d["issues"].append(row)
    save(a.work, d, f"issue {ident}")
    print(f"OK {ident} {'阻塞' if a.blocking else '待办'}")


def cmd_resolve(a):
    d = load(a.work)
    r = find(d["issues"], a.id)
    if a.state == "deferred":
        nonempty(a.until, "延期触发点 --until")
    reason = nonempty(a.reason, "处理依据")
    ids = list(dict.fromkeys(r["items"] + a.item))
    items = [find(d["items"], i) for i in ids]
    if a.state == "resolved":
        problems = [p for i in items for p in item_problems(a.work, d, i)]
        if problems:
            fail("；".join(problems))
    r.update(state=a.state, resolution=reason, until=a.until or "", items=ids, stamp=live_stamp(a.work, d, items))
    save(a.work, d, f"resolve {a.id} {a.state}")
    print(f"OK {a.id} {a.state}（阻塞项延期不会让当前范围通过）")


def readiness(work, d, scope):
    items = closure(d, scope)
    problems = []
    if not items:
        problems.append("范围内没有成果，不能以空目录视为完成")
    for r in items:
        if r["state"] != "accepted":
            problems.append(f"{r['id']} 尚未采用（{r['state']}）")
        problems += item_problems(work, d, r)
    issues = affected(d, scope, items)
    for r in issues:
        related = [find(d["items"], i) for i in r["items"]]
        stale = r["state"] == "resolved" and r["stamp"] != live_stamp(work, d, related)
        if stale:
            problems.append(f"{r['id']} 关闭依据已变，需要重新复核")
        if r["blocking"] and r["state"] != "resolved":
            problems.append(f"{r['id']} 阻塞尚未解决：{r['text']}")
    payload = {"purpose": d["purpose"], "scope": scope, "items": live_stamp(work, d, items), "issues": issues}
    return problems, digest(encoded(payload)), items


def cmd_review(a):
    d = load(a.work)
    scope = a.scope or d["scope"]
    problems, stamp, _ = readiness(a.work, d, scope)
    if a.result == "pass" and problems:
        fail("不能登记通过：\n" + "\n".join(problems))
    data = read_stable(a.file)
    nonempty(data.decode("utf-8-sig"), "语义检查报告")
    sha = digest(data)
    rel = f"{SPEC['work']}/reviews/{sha}.md"
    atomic(safe_local(a.work, rel), data)
    d["reviews"][scope] = {"result": a.result, "stamp": stamp, "report": rel,
                            "sha": sha, "by": nonempty(a.by, "检查人"), "at": now()}
    save(a.work, d, f"review {scope} {a.result}")
    print(f"OK {scope} {a.result}；脚本保存检查记录，不代替语义判断")


def check(work, d, scope):
    problems, stamp, items = readiness(work, d, scope)
    review = d["reviews"].get(scope)
    if not review or review["result"] != "pass":
        problems.append("缺少该范围的语义检查通过记录（review）")
    elif review["stamp"] != stamp:
        problems.append("内容、来源、采用决定或问题变化，语义检查已过期")
    else:
        try:
            if digest(read_stable(safe_local(work, review["report"]))) != review["sha"]:
                problems.append("语义检查报告被修改，重新登记")
        except (OSError, ValueError):
            problems.append("语义检查报告丢失或不可读")
    return problems, items


def cmd_check(a):
    d = load(a.work)
    scope = a.scope or d["scope"]
    problems, items = check(a.work, d, scope)
    print(f"{'FAIL' if problems else 'PASS'} 范围：{scope}；成果 {len(items)} 份")
    for p in problems:
        print(f"- {p}")
    if problems:
        return 1
    print("仅表示该范围的已登记成果及检查仍有效；不等于整库处理完毕或通过写作闸门")
    return 0


def cmd_status(a):
    d = load(a.work)
    if a.json:
        print(json.dumps(d, ensure_ascii=False, indent=2))
        return
    print(f"{d['title']}｜目标：{d['purpose']}｜默认范围：{d['scope']}")
    print("任务：" + "、".join(TASKS[t] for t in d["tasks"]))
    for s in d["sources"]:
        print(f"来源 {s['id']} [{s['kind']}] {s['path']}")
    idx = index(a.work)
    print(f"索引：{idx['scanned_at'] or '尚未扫描'}；{dict(Counter(r['status'] for r in idx['files']))}")
    for e in idx["errors"]:
        print(f"读取缺口：{e}")
    for i in d["items"]:
        print(f"{i['id']} [{TASKS[i['task']]} / {i['nature']} / {i['state']}] {i['title']}｜{i['scope']}｜{i['path']}")
    for i in d["issues"]:
        print(f"{i['id']} [{i['state']}{' / 阻塞' if i['blocking'] else ''}] {i['text']} → {i['next']}")


def cmd_export(a):
    d = load(a.work)
    scope = a.scope or d["scope"]
    problems, items = check(a.work, d, scope)
    if problems:
        fail("暂不能交接：\n" + "\n".join(problems))
    lines = [f"# 创作前准备交接：{d['title']}", "", f"范围：{scope}", f"目标：{d['purpose']}", "",
             "> 给作者、规划与设定工作使用；含完整设定，不是写手包。具体章节经现有场景与知情流程取用。", ""]
    for i in items:
        lines += [f"## {i['id']} {i['title']}", f"任务：{TASKS[i['task']]}；性质：{i['nature']}；范围：{i['scope']}",
                  f"采用依据：{i['decision']}", f"整理/创建依据：{i['basis']}", f"依赖：{', '.join(i['depends']) or '无'}"]
        for ref in i["refs"]:
            s = find(d["sources"], ref["root"])
            lines.append(f"来源：{s['path']} / {ref['relative']}:{ref['start']}-{ref['end']} SHA {ref['sha']}")
        lines += [f"外部出处：{c}" for c in i["citations"]]
        lines += ["", safe_local(a.work, i["path"]).read_text("utf-8-sig"), ""]
    lines += ["## 保留的待办", ""]
    for q in affected(d, scope, items):
        if q["state"] != "resolved":
            lines.append(f"- {q['id']} {q['text']}；下一步：{q['next']}；触发点：{q['until'] or '未指定'}")
    data = "\n".join(lines).encode("utf-8")
    out = safe_local(a.work, f"{SPEC['work']}/exports/{digest(data)}.md")
    atomic(out, data)
    print(out)


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    def command(name, fn, help_text):
        s = sub.add_parser(name, help=help_text)
        s.add_argument("work", type=Path, help="准备工作目录，不是必须存在的书目录")
        s.set_defaults(fn=fn)
        return s

    s = command("init", cmd_init, "建立工作区，可零资料开始")
    s.add_argument("--title", required=True); s.add_argument("--purpose", required=True)
    s.add_argument("--scope", default="本轮准备"); s.add_argument("--task", action="append", choices=TASKS)
    s = command("source", cmd_source, "登记只读资料根或单文件")
    s.add_argument("path", type=Path); s.add_argument("--label"); s.add_argument("--kind", choices=SPEC["source_kinds"], default="mixed")
    command("scan", cmd_scan, "增量扫描、重复组、覆盖缺口")
    s = command("search", cmd_search, "在已扫描来源中查词，词间 AND")
    s.add_argument("words", nargs="+"); s.add_argument("--limit", type=int, default=20)
    s = command("show", cmd_show, "按完整行查看来源，保留表格")
    s.add_argument("id"); s.add_argument("--start", type=int, default=1); s.add_argument("--end", type=int)
    s = command("item", cmd_item, "登记模型产出的实际成果或更新成果；更新会回到候选")
    s.add_argument("--file", type=Path, required=True); s.add_argument("--title", required=True)
    s.add_argument("--task", choices=TASKS, required=True); s.add_argument("--nature", choices=SPEC["natures"], required=True)
    s.add_argument("--basis", required=True); s.add_argument("--scope"); s.add_argument("--id")
    s.add_argument("--ref", action="append", default=[]); s.add_argument("--citation", action="append", default=[])
    s.add_argument("--depends", action="append", default=[])
    s = command("decide", cmd_decide, "按用户授权或已有决定记录成果处置")
    s.add_argument("id"); s.add_argument("--state", choices=SPEC["item_states"], required=True); s.add_argument("--reason", required=True)
    s = command("issue", cmd_issue, "记录待补、冲突或待创建内容")
    s.add_argument("--kind", choices=["gap", "conflict", "research", "creation"], required=True)
    for arg in ("text", "evidence", "next"):
        s.add_argument(f"--{arg}", required=True)
    s.add_argument("--scope"); s.add_argument("--item", action="append", default=[]); s.add_argument("--blocking", action="store_true")
    s = command("resolve", cmd_resolve, "解决、延期或重开问题")
    s.add_argument("id"); s.add_argument("--state", choices=["resolved", "deferred", "open"], required=True)
    s.add_argument("--reason", required=True); s.add_argument("--until")
    s.add_argument("--item", action="append", default=[])
    s = command("review", cmd_review, "保存有内容版本依据的语义检查报告")
    s.add_argument("--file", type=Path, required=True); s.add_argument("--scope")
    s.add_argument("--result", choices=["pass", "needs_work"], required=True); s.add_argument("--by", required=True)
    s = command("check", cmd_check, "检查指定范围能否交接")
    s.add_argument("--scope")
    s = command("status", cmd_status, "恢复任务、列出成果和待办")
    s.add_argument("--json", action="store_true")
    s = command("export", cmd_export, "输出已通过检查的交接文档，不改现有工程")
    s.add_argument("--scope")
    return p


def main(argv=None):
    a = parser().parse_args(argv)
    a.work = a.work.expanduser().resolve()
    try:
        if a.command in ("search", "show", "check", "status"):
            return a.fn(a) or 0
        if a.command != "init":
            load(a.work)
        with lock(a.work):
            return a.fn(a) or 0
    except (OSError, ValueError, KeyError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
