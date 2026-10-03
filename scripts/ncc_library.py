"""通用素材库治理：适配规范、覆盖计划、任务包、批次、检查与受控交付。"""

from collections import Counter, defaultdict
import fnmatch
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
from urllib.parse import unquote


def relative(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("库内路径不能为空")
    p = PurePosixPath(value)
    if p.is_absolute() or any(x in ("..", ".ncc-prepare", "prepare.json") or x.startswith(".") for x in p.parts):
        raise ValueError(f"库内路径不合法：{value}")
    if not p.parts or "\\" in value:
        raise ValueError(f"库内路径不合法：{value}")
    return p.as_posix()


def matches(path, pattern):
    return fnmatch.fnmatchcase(path, pattern) or (pattern.startswith("**/") and fnmatch.fnmatchcase(path, pattern[3:]))


def fields(text):
    """支持扁平 frontmatter；无 frontmatter 时读独立字段行与两列表。"""
    rows = text.splitlines()
    front = bool(rows and rows[0] == "---")
    stop = next((i for i in range(1, len(rows)) if rows[i] == "---"), None) if front else None
    if front and stop is None:
        raise ValueError("frontmatter 缺结束分隔符")
    out = defaultdict(list)
    fenced = False
    for i, row in enumerate(rows[:stop] if front else rows, 1):
        if re.match(r"^\s*(```|~~~)", row):
            fenced = not fenced
        if fenced:
            continue
        m = re.match(r"^\s*([^:#|\[\]{}]+?)\s*[:：]\s*(.*?)\s*$", row)
        cells = [x.strip().strip("*").strip() for x in row.strip().strip("|").split("|")]
        if not front and row.strip().startswith("|") and len(cells) == 2 and not re.fullmatch(r"[-: ]+", cells[0]):
            key, value = cells
        elif m:
            key, value = m[1].strip().strip("*").strip(), m[2].strip().strip("\"'")
        else:
            continue
        out[key].append({"value": value, "line": i})
    return dict(out)


def links(text):
    fenced = False
    for n, row in enumerate(text.splitlines(), 1):
        if re.match(r"^\s*(```|~~~)", row):
            fenced = not fenced
        if fenced:
            continue
        row = re.sub(r"`[^`]*`", "", row)
        for m in re.finditer(r"\[\[([^\]]+)\]\]|\]\((<[^>]+>|[^)]+)\)", row):
            wiki = m[1] is not None
            dest = m[1].split("|", 1)[0] if wiki else m[2]
            if dest.startswith("<"):
                dest = dest[1:dest.index(">")]
            elif not wiki:
                dest = re.sub(r'\s+[\"\'].*$', "", dest)
            dest = unquote(dest.strip())
            if re.match(r"^[a-zA-Z][\w+.-]*:", dest) and not re.match(r"^R-\d+::", dest):
                continue
            yield n, dest, wiki


def anchors(text):
    result = set()
    for row in text.splitlines():
        m = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", row)
        if m:
            h = m[1].strip()
            result.update((h, re.sub(r"[^\w\- ]", "", h.casefold()).replace(" ", "-")))
        for block in re.findall(r"(?:^|\s)(\^[\w-]+)\s*$", row):
            result.add(block)
    return result


def number(value):
    if not re.fullmatch(r"[-+]?\d+(?:\.\d+)?", value.strip()):
        raise ValueError(f"数值需为显式标量，单位另设字段：{value}")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("数值必须有限")
    return result


class Library:
    def __init__(self, prep):
        self.p = prep
        self.spec = prep.SPEC["library"]

    def data(self, work):
        d = self.p.load(work)
        lib = d.setdefault("library", {"schema": self.spec["schema"], "profile": None, "plans": [], "audits": []})
        if lib["schema"] != self.spec["schema"]:
            raise ValueError("不支持的库治理版本")
        return d, lib

    def base(self, work, plan):
        return self.p.safe_local(work, f"{self.p.SPEC['work']}/library/{plan['id']}")

    def profile_value(self, work, lib):
        rec = lib["profile"]
        if not rec:
            raise ValueError("先读取资料并用 library-profile 登记本库规范")
        data = self.p.read_stable(self.p.safe_local(work, rec["path"]))
        if self.p.digest(data) != rec["sha"]:
            raise ValueError("规范文件被修改；重新 library-profile 登记并复核计划")
        return json.loads(data)

    def profile(self, a):
        d, lib = self.data(a.work)
        value = json.loads(self.p.read_stable(a.file))
        if not isinstance(value, dict):
            raise ValueError("规范需为 JSON 对象")
        self.p.nonempty(value.get("name"), "规范名")
        self.p.nonempty(value.get("organization"), "分类、主归属、命名、版本和维护原则 organization")
        if not isinstance(value.get("types"), dict) or not value["types"]:
            raise ValueError("types 需要至少一种内容类型")
        for name, rule in value["types"].items():
            self.p.nonempty(name, "内容类型")
            if not isinstance(rule, dict) or not isinstance(rule.get("match"), list) or not rule["match"] or not all(isinstance(x, str) and x.strip() for x in rule["match"]):
                raise ValueError(f"{name} 需声明 match 路径模式")
            for key in ("required", "unique", "namespace"):
                if not isinstance(rule.get(key, []), list) or not all(isinstance(x, str) for x in rule.get(key, [])):
                    raise ValueError(f"{name}.{key} 需为字段名数组")
            if not isinstance(rule.get("enum", {}), dict):
                raise ValueError("enum 需为字段到允许值数组的映射")
            for allowed in rule.get("enum", {}).values():
                if not isinstance(allowed, list) or not allowed or not all(isinstance(x, str) for x in allowed):
                    raise ValueError("enum 的允许值需为非空字符串数组")
        for path in value.get("indexes", []):
            relative(path)
        for c in value.get("constraints", []):
            if c.get("op") not in ("eq", "le", "ge"):
                raise ValueError("constraints.op 支持 eq/le/ge")
            for side in ("left", "right"):
                relative(c[side]["path"])
                self.p.nonempty(c[side]["field"], "约束字段")
            for x in ("factor", "offset", "tolerance"):
                if x in c:
                    number(str(c[x]))
        payload = self.p.encoded(value)
        sha = self.p.digest(payload)
        path = f"{self.p.SPEC['work']}/library/profiles/{sha}.json"
        self.p.atomic(self.p.safe_local(a.work, path), payload)
        lib["profile"] = {"path": path, "sha": sha, "reason": self.p.nonempty(a.reason, "规范决定依据")}
        self.p.save(a.work, d, "library-profile")
        print(f"OK {value['name']}；既有计划的规范版本改变后需重新规划")

    def tree(self, root):
        if not root.is_dir() or root.is_symlink():
            raise ValueError(f"库根必须是实际目录：{root}")
        result = []
        def error(e):
            raise ValueError(f"库目录无法读取：{e}")
        for cur, dirs, files in os.walk(root, followlinks=False, onerror=error):
            dirs[:] = sorted(x for x in dirs if not x.startswith("."))
            for x in list(dirs):
                if (Path(cur) / x).is_symlink():
                    files.append(x)
                    dirs.remove(x)
            for name in sorted(files):
                if name.startswith("."):
                    continue
                path = Path(cur) / name
                rec = {"relative": path.relative_to(root).as_posix(), "root": "target", "id": path.relative_to(root).as_posix()}
                try:
                    if path.is_symlink():
                        rec.update(status="link", target=os.readlink(path))
                    else:
                        data = self.p.read_stable(path)
                        rec.update(sha=self.p.digest(data), status="unsupported")
                        if path.suffix.lower() in self.p.SPEC["text_extensions"]:
                            rec.update(status="readable", text=data.decode("utf-8-sig"))
                except (OSError, ValueError, UnicodeError) as e:
                    rec.update(status="unreadable", error=str(e))
                result.append(rec)
        return result

    def inputs(self, work, d):
        for source in d["sources"]:
            root = Path(source["path"])
            if root.is_symlink() or root.resolve() != root:
                raise ValueError("来源根或上级路径已被重定向；重新确认真实来源")
        idx = self.p.scan(work, d)
        if idx["errors"]:
            raise ValueError("来源扫描不完整：" + "；".join(idx["errors"]))
        rows = [r for r in idx["files"] if r["status"] != "missing"]
        for r in rows:
            if r["status"] not in ("readable", "link"):
                path = self.p.source_path(d, r)
                stat = path.stat()
                r["stat"] = [stat.st_size, stat.st_mtime_ns]
                try:
                    r["sha"] = self.p.digest(self.p.read_stable(path))
                except (OSError, ValueError):
                    pass  # The explicit read gap remains, even when metadata can be tracked.
        return rows

    def fingerprint(self, rows):
        return self.p.digest(self.p.encoded([{k: v for k, v in r.items() if k not in ("text", "change", "headings", "lines")} for r in rows]))

    def lint(self, rows, profile):
        findings, docs, meta = [], {}, {}
        def add(code, rec, message, line=1, level="error"):
            findings.append({"code": code, "source": rec["id"], "root": rec["root"], "path": rec["relative"],
                             "line": line, "level": level, "message": message})
        unique, duplicates = defaultdict(list), defaultdict(list)
        for r in rows:
            key = (r["root"], r["relative"])
            if r["status"] != "readable":
                add("unread", r, f"未做内容检查：{r['status']}", level="warning")
                continue
            docs[key] = r
            duplicates[(r["root"], r["sha"])].append(r)
            try:
                meta[key] = fields(r["text"])
            except ValueError as e:
                meta[key] = {}
                add("metadata", r, str(e))
            rules = [(name, rule) for name, rule in profile["types"].items() if any(matches(r["relative"], x) for x in rule["match"])]
            if len(rules) != 1:
                add("classification", r, "内容未匹配类型" if not rules else "同时匹配多个类型；收敛主归属")
                continue
            name, rule = rules[0]
            data = meta[key]
            for field in set(rule.get("required", [])) | set(rule.get("enum", {})) | set(rule.get("unique", [])) | set(rule.get("namespace", [])):
                vals = data.get(field, [])
                if field in rule.get("required", []) + rule.get("namespace", []) and (not vals or not vals[0]["value"]):
                    add("required", r, f"缺少必要字段：{field}")
                if len({x["value"] for x in vals}) > 1:
                    add("field-conflict", r, f"字段 {field} 有多个不同值", vals[-1]["line"])
                if vals and field in rule.get("enum", {}) and vals[0]["value"] not in rule["enum"][field]:
                    add("enum", r, f"{field} 不在本库允许值内：{vals[0]['value']}", vals[0]["line"])
                if vals and field in rule.get("unique", []):
                    ns = tuple(data.get(f, [{"value": ""}])[0]["value"] for f in rule.get("namespace", []))
                    unique[(r["root"], name, ns, field, vals[0]["value"])].append((r, vals[0]["line"]))
            for field, value in profile.get("terms", {}).items():
                for n, line in enumerate(r["text"].splitlines(), 1):
                    if field in line:
                        add("term-candidate", r, f"术语候选：{field} → {value}，需语义确认", n, "warning")
        for group in unique.values():
            if len(group) > 1:
                for r, n in group:
                    add("duplicate-id", r, "同一类型及命名空间内标识重复", n)
        for group in duplicates.values():
            if len(group) > 1:
                for r in group:
                    add("duplicate-content", r, "内容哈希相同；需确认是否保留或合并", level="warning")
        available = {(r["root"], r["relative"]): r for r in rows}
        edges = defaultdict(set)
        for key, r in docs.items():
            if profile.get("links", True):
                for n, dest, wiki in links(r["text"]):
                    target, _, fragment = dest.partition("#")
                    root = r["root"]
                    if "::" in target:
                        root, target = target.split("::", 1)
                    cand = []
                    if not target:
                        cand = [key]
                    else:
                        paths = [os.path.normpath(str(PurePosixPath(r["relative"]).parent / target)), target.lstrip("/")]
                        expanded = [v for x in paths for v in ([x, x + ".md"] if wiki and not PurePosixPath(x).suffix else [x])]
                        cand = list(dict.fromkeys((root, x) for x in expanded if (root, x) in available))
                        if not cand and wiki:
                            cand = [k for k in available if k[0] == root and PurePosixPath(k[1]).stem == target]
                        # Relative Markdown paths have precedence; wiki paths can be genuinely ambiguous.
                        if not wiki and cand:
                            cand = cand[:1]
                    if len(cand) != 1:
                        add("ambiguous-link" if cand else "broken-link", r, f"链接无法唯一定位：{dest}", n)
                    else:
                        edges[key].add(cand[0])
                        if fragment and cand[0] in docs and fragment not in anchors(docs[cand[0]]["text"]):
                            add("broken-anchor", r, f"标题/块引用不存在：{dest}", n)
            for field in profile.get("authority_fields", []):
                vals = meta[key].get(field, [])
                if vals and not vals[0]["value"]:
                    add("authority", r, f"权威来源字段 {field} 为空", vals[0]["line"])
        for root in {r["root"] for r in rows}:
            for path in profile.get("indexes", []):
                if (root, path) not in docs:
                    add("missing-index", {"id": root, "root": root, "relative": path}, "规范要求的导航文件缺失")
            if profile.get("indexes") and profile.get("navigation_coverage", True):
                visited = {(root, x) for x in profile["indexes"] if (root, x) in docs}
                pending = list(visited)
                for key in pending:
                    for dest in edges[key]:
                        if dest not in visited:
                            visited.add(dest)
                            pending.append(dest)
                for key, r in docs.items():
                    if key[0] == root and key not in visited:
                        add("orphan", r, "从已声明导航入口无法到达该内容")
            # Numeric checks are explicitly configured; no inference of genre-specific units or ranges.
            for c in profile.get("constraints", []):
                rec = {"id": root, "root": root, "relative": c["left"]["path"]}
                try:
                    values = [meta[(root, c[s]["path"])][c[s]["field"]][0] for s in ("left", "right")]
                    left, right = (number(v["value"]) for v in values)
                    right = right * float(c.get("factor", 1)) + float(c.get("offset", 0))
                    tol = float(c.get("tolerance", 0))
                    good = abs(left-right) <= tol if c["op"] == "eq" else (left <= right+tol if c["op"] == "le" else left >= right-tol)
                    if not good:
                        add("numeric-conflict", rec, f"约束不成立：{c.get('name', c['op'])}；{left} / {right}", values[0]["line"])
                except (KeyError, ValueError, IndexError) as e:
                    add("numeric-unchecked", rec, f"约束缺少可核标量：{e}")
        return findings

    def audit(self, a):
        d, lib = self.data(a.work)
        profile = self.profile_value(a.work, lib)
        if a.target:
            rows = self.tree(a.target.expanduser().resolve())
        else:
            rows = self.inputs(a.work, d)
            for r in rows:
                if r["status"] == "readable":
                    r["text"] = self.p.source_text(d, r)
        report = {"profile": lib["profile"]["sha"], "coverage": dict(Counter(r["status"] for r in rows)),
                  "stamp": self.fingerprint(rows), "findings": self.lint(rows, profile),
                  "boundary": "结构和显式规则检查；未证明信息保真、术语同义或设定合理性"}
        path = f"{self.p.SPEC['work']}/library/audits/{self.p.digest(self.p.encoded(report))}.json"
        self.p.atomic(self.p.safe_local(a.work, path), self.p.encoded(report))
        lib["audits"].append({"path": path, "at": self.p.now()})
        self.p.save(a.work, d, "library-audit")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"报告：{self.p.safe_local(a.work, path)}")

    def plan(self, a):
        d, lib = self.data(a.work)
        self.profile_value(a.work, lib)
        value = json.loads(self.p.read_stable(a.file))
        if not isinstance(value, dict):
            raise ValueError("治理计划需为 JSON 对象")
        self.p.nonempty(value.get("goal"), "治理目标")
        rows = self.inputs(a.work, d)
        if not rows:
            raise ValueError("治理计划没有来源；从空白创建使用六类准备任务")
        byid = {r["id"]: r for r in rows}
        entries = value.get("entries", [])
        if not isinstance(entries, list) or not all(isinstance(e, dict) for e in entries):
            raise ValueError("entries 需为来源处置对象数组")
        ids = [e["source"] for e in entries]
        if len(ids) != len(set(ids)) or set(ids) != set(byid):
            raise ValueError("entries 必须覆盖全部当前来源且每个来源恰好一次；未处理部分登记 deferred")
        for e in entries:
            if e.get("disposition") not in self.spec["dispositions"]:
                raise ValueError("无效来源处置")
            self.p.nonempty(e.get("reason"), "逐来源处置理由")
            outs = e.get("outputs", [])
            if not isinstance(outs, list) or not all(isinstance(x, str) for x in outs) or len(outs) != len(set(outs)):
                raise ValueError("outputs 需为无重复路径数组")
            if e["disposition"] in ("excluded", "deferred") and outs:
                raise ValueError("excluded/deferred 不能声明已整理输出")
            if e["disposition"] not in ("excluded", "deferred") and not outs:
                raise ValueError("保留、转换、拆分或合并来源需要实际输出")
            for x in outs:
                relative(x)
            if e["disposition"] == "retained" and len(outs) != 1:
                raise ValueError("retained 对应一个完整原文输出；改写使用 transformed")
            if e["disposition"] == "split" and len(outs) < 2:
                raise ValueError("split 需要至少两个输出")
            if outs and byid[e["source"]]["status"] != "readable":
                raise ValueError("未读取格式先转换并登记；不能声明已完成内容治理")
        batches, owned, seen = [], {}, set()
        if not isinstance(value.get("batches"), list):
            raise ValueError("batches 需为数组")
        for b in value.get("batches", []):
            if b.get("operation") not in self.spec["operations"]:
                raise ValueError("批次 operation 需为已注册库工程任务")
            self.p.nonempty(b.get("name"), "批次名")
            src = b.get("sources", [])
            if not isinstance(src, list) or not src or len(src) != len(set(src)) or set(src)-set(ids) or seen.intersection(src):
                raise ValueError("批次来源需有效、非空、无重复，且不得跨批次重复")
            seen.update(src)
            outputs = sorted({x for e in entries if e["source"] in src for x in e.get("outputs", [])})
            outputs += [relative(x) for x in b.get("new_outputs", [])]
            if len(set(outputs)) != len(outputs) or set(outputs).intersection(owned):
                raise ValueError("一个输出由一个批次维护；合并到同文件的来源放在同批次")
            ident = f"B-{len(batches)+1:04d}"
            owned.update({x: ident for x in outputs})
            batches.append({**b, "id": ident, "outputs": outputs, "state": "pending", "files": [], "report": None})
        if seen != set(ids):
            raise ValueError("批次必须覆盖全部来源处置")
        if not owned:
            raise ValueError("计划必须交付实际素材内容，不能只排除全部输入")
        for path in owned:
            if any(str(parent) in owned for parent in PurePosixPath(path).parents):
                raise ValueError("输出文件不能同时作为另一输出的目录")
        for e in entries:
            if e["disposition"] == "merged" and not any(set(e["outputs"]).intersection(x.get("outputs", [])) for x in entries if x is not e):
                raise ValueError("merged 的输出需对应其他来源，单来源改写用 transformed")
        for q in value.get("queries", []):
            if not isinstance(q.get("words"), list) or not q["words"] or not all(isinstance(x, str) and x.strip() for x in q["words"]) or not isinstance(q.get("expected"), list) or not q["expected"]:
                raise ValueError("写作取用用例需有 words 和 expected")
            if set(q["expected"])-set(owned):
                raise ValueError("取用用例的 expected 必须属于本轮输出")
        if not value.get("queries"):
            raise ValueError("至少登记一个代表性写作取用用例")
        mode = value.get("mode", "copy")
        if mode not in ("copy", "in-place"):
            raise ValueError("mode 支持 copy/in-place")
        target_raw = Path(value.get("target", str(a.work / "素材库"))).expanduser()
        if not target_raw.is_absolute() or target_raw.is_symlink():
            raise ValueError("target 需为绝对路径且不是符号链接")
        target = target_raw.resolve()
        for s in d["sources"]:
            root = Path(s["path"])
            if mode == "copy" and (target.is_relative_to(root) or root.is_relative_to(target)):
                raise ValueError("新库 target 与原资料根不得包含彼此")
        if mode == "in-place" and (len(d["sources"]) != 1 or target != Path(d["sources"][0]["path"]) or not target.is_dir()):
            raise ValueError("原地治理需对应唯一已登记目录根；多个库分别规划")
        if mode == "in-place":
            old_paths = {r["relative"] for r in rows}
            for path in owned:
                if any(str(parent) in old_paths for parent in PurePosixPath(path).parents) or any(path in map(str, PurePosixPath(old).parents) for old in old_paths):
                    raise ValueError("原地文件/目录类型互换需先交付到新库，避免无法恢复的路径冲突")
        if target == a.work or a.work.is_relative_to(target) or target.is_relative_to(a.work / self.p.SPEC["work"]):
            raise ValueError("target 不得覆盖状态工作区或位于内部记录目录")
        rec = {"id": self.p.next_id(lib["plans"], "L"), "goal": value["goal"], "mode": mode, "target": str(target),
               "reason": self.p.nonempty(a.reason, "计划与规范的决定依据"), "profile": lib["profile"]["sha"],
               "inputs": rows, "input_stamp": self.fingerprint(rows), "entries": entries, "batches": batches,
               "queries": value["queries"], "review": None, "applied": None, "transaction": None}
        lib["plans"].append(rec)
        (self.base(a.work, rec) / "staging").mkdir(parents=True)
        self.p.save(a.work, d, f"library-plan {rec['id']}")
        print(f"OK {rec['id']}；来源 {len(rows)}，批次 {len(batches)}，目标 {target}")

    def locate(self, a):
        d, lib = self.data(a.work)
        plan = self.p.find(lib["plans"], a.plan)
        profile = self.profile_value(a.work, lib)
        if plan["profile"] != lib["profile"]["sha"]:
            raise ValueError("计划的规范已变化；重新规划，不沿用旧批次")
        return d, lib, plan, profile

    def fresh(self, work, d, plan):
        rows = self.inputs(work, d)
        expected = plan["applied"]["input_stamp"] if plan["applied"] else plan["input_stamp"]
        if self.fingerprint(rows) != expected:
            raise ValueError("来源内容或全库范围已变化；重新诊断并规划")

    def packet(self, a):
        d, lib, plan, profile = self.locate(a)
        self.fresh(a.work, d, plan)
        batch = self.p.find(plan["batches"], a.batch)
        role = self.p.ROOT / "agents/curator.md"
        lines = [f"# {batch['name']}", f"role: curator\ntask: {batch['operation']}\nplugin_root: {self.p.ROOT}",
                 f"目标：{plan['goal']}\n授权依据：{plan['reason']}\n计划：{plan['id']} / {batch['id']}",
                 "必读方法：" + str(self.p.ROOT / "skills/ncc-prepare/references/library.md") + "\n命令接口：" + str(self.p.ROOT / "skills/ncc-prepare/references/library-tools.md"),
                 "产物只写草稿；经理通过 library-batch 登记。不得直接修改源库、状态、其他批次。",
                 "宿主与用户授权派子代理时优先 ncc-workflow:curator；fallback 仍加载以下角色协议。未授权派单时由当前助手执行。",
                 "## 角色协议", role.read_text("utf-8"), "## 本库规范", json.dumps(profile, ensure_ascii=False, indent=2),
                 "## 本任务方法", self.spec["operations"][batch["operation"]], "## 来源与处置"]
        for ident in batch["sources"]:
            r = self.p.find(plan["inputs"], ident)
            e = next(x for x in plan["entries"] if x["source"] == ident)
            base = Path(self.p.find(d["sources"], r["root"])["path"])
            lines += [json.dumps({"source": r, "disposition": e, "absolute": str(base if r["relative"] == "." else base / r["relative"])}, ensure_ascii=False)]
        lines += ["## 要交付的文件", *batch["outputs"], "## 回传", "实际内容草稿 + 逐来源保真/处置检查报告 + 未解决问题；注明执行方式与实际使用的角色。"]
        out = self.base(a.work, plan) / "packets" / f"{batch['id']}.md"
        self.p.atomic(out, "\n\n".join(lines).encode())
        batch["packet"] = {"path": str(out.relative_to(a.work)), "sha": self.p.digest(out.read_bytes()), "role_sha": self.p.digest(role.read_bytes())}
        self.p.save(a.work, d, f"library-packet {plan['id']} {batch['id']}")
        print(out)

    def batch(self, a):
        d, lib, plan, profile = self.locate(a)
        if plan["applied"] or plan["transaction"]:
            raise ValueError("已应用或恢复中的计划不能重写批次；建立新计划")
        self.fresh(a.work, d, plan)
        b = self.p.find(plan["batches"], a.batch)
        manifest = json.loads(self.p.read_stable(a.file))
        files = manifest.get("files", {})
        if set(files) != set(b["outputs"]):
            raise ValueError("批次必须交付恰好全部预定文件；调整范围需重新规划")
        report = self.p.read_stable(a.report)
        self.p.nonempty(report.decode("utf-8-sig"), "逐来源保真与处置报告")
        rows = []
        for path, file in files.items():
            relative(path)
            data = self.p.read_stable(Path(file).expanduser())
            self.p.nonempty(data.decode("utf-8-sig"), "实际素材内容")
            if Path(path).suffix.lower() not in self.p.SPEC["text_extensions"]:
                raise ValueError("本版内容交付支持 UTF-8 Markdown/文本，其他格式需转换")
            rows.append((path, data))
        hashes = {path: self.p.digest(data) for path, data in rows}
        for e in plan["entries"]:
            if e["source"] in b["sources"] and e["disposition"] == "retained":
                if hashes[e["outputs"][0]] != self.p.find(plan["inputs"], e["source"])["sha"]:
                    raise ValueError("retained 原文内容变化；保留原文或重新规划为 transformed")
        root = self.base(a.work, plan)
        for path, data in rows:
            self.p.atomic(self.p.safe_local(root / "staging", path), data)
        report_path = root / "reports" / f"{b['id']}-{self.p.digest(report)}.md"
        self.p.atomic(report_path, report)
        role_sha = self.p.digest((self.p.ROOT / "agents/curator.md").read_bytes())
        b.update(state="completed", files=[{"path": x, "sha": self.p.digest(data)} for x, data in rows],
                 report={"path": str(report_path.relative_to(a.work)), "sha": self.p.digest(report)},
                 execution=a.execution, by=self.p.nonempty(a.by, "执行者"), role="curator", role_sha=role_sha)
        plan["review"] = None
        self.p.save(a.work, d, f"library-batch {plan['id']} {b['id']}")
        print(f"OK {b['id']}；{len(rows)} 份内容；执行方式为执行者声明，待全库验收")

    def query(self, rows, words):
        return [r for r in rows if r["status"] == "readable" and all(w.casefold() in (r["relative"] + "\n" + r["text"]).casefold() for w in words)]

    def evaluate(self, a, d, plan, profile):
        self.fresh(a.work, d, plan)
        root = Path(plan["target"]) if plan["applied"] else self.base(a.work, plan) / "staging"
        rows = self.tree(root)
        problems = []
        expected = {f["path"]: f["sha"] for b in plan["batches"] for f in b["files"]}
        actual = {r["relative"]: r.get("sha") for r in rows}
        if actual != expected:
            problems.append("实际库文件与已登记批次不一致（缺失、额外或内容变化）")
        for b in plan["batches"]:
            if b["state"] != "completed":
                problems.append(f"{b['id']} 未完成")
            elif self.p.digest(self.p.read_stable(self.p.safe_local(a.work, b["report"]["path"]))) != b["report"]["sha"]:
                problems.append(f"{b['id']} 保真/处置报告已变化")
        problems += [f"未完成来源 {e['source']}：{e['reason']}" for e in plan["entries"] if e["disposition"] == "deferred"]
        findings = self.lint(rows, profile)
        problems += [f"{r['path']}:{r['line']} {r['message']}" for r in findings if r["level"] == "error"]
        for q in plan["queries"]:
            found = {r["relative"] for r in self.query(rows, q["words"])}
            if set(q["expected"])-found:
                problems.append(f"写作取用未命中：{q['words']} → {sorted(set(q['expected'])-found)}")
        payload = {"profile": plan["profile"], "input_stamp": plan["input_stamp"], "entries": plan["entries"],
                   "batches": plan["batches"], "queries": plan["queries"], "tree": self.fingerprint(rows)}
        return problems, self.p.digest(self.p.encoded(payload)), findings

    def review(self, a):
        d, lib, plan, profile = self.locate(a)
        problems, stamp, findings = self.evaluate(a, d, plan, profile)
        if a.result == "pass" and problems:
            raise ValueError("整库不能通过：\n" + "\n".join(problems))
        data = self.p.read_stable(a.file)
        self.p.nonempty(data.decode("utf-8-sig"), "全库语义与写作取用检查报告")
        out = self.base(a.work, plan) / "reviews" / f"{self.p.digest(data)}.md"
        self.p.atomic(out, data)
        plan["review"] = {"stamp": stamp, "result": a.result, "path": str(out.relative_to(a.work)), "sha": self.p.digest(data),
                          "by": self.p.nonempty(a.by, "复核者"), "findings": findings}
        self.p.save(a.work, d, f"library-review {plan['id']} {a.result}")
        print(f"OK {plan['id']} {a.result}；脚本保存语义报告，不证明其判断正确")

    def checked(self, a, d, plan, profile):
        if plan["transaction"]:
            raise ValueError("存在未结束的交付事务；先 library-restore")
        problems, stamp, findings = self.evaluate(a, d, plan, profile)
        r = plan["review"]
        if not r or r["result"] != "pass" or r["stamp"] != stamp:
            problems.append("缺少有效全库语义检查，或其依据已过期")
        elif self.p.digest(self.p.read_stable(self.p.safe_local(a.work, r["path"]))) != r["sha"]:
            problems.append("全库检查报告已被修改")
        return problems, findings

    def check(self, a):
        d, lib, plan, profile = self.locate(a)
        problems, findings = self.checked(a, d, plan, profile)
        print(f"{'FAIL' if problems else 'PASS'} {plan['id']}｜来源 {len(plan['inputs'])}｜批次 {len(plan['batches'])}")
        for x in problems:
            print("- " + x)
        print(f"语义检查由报告负责；专项检查警告 {sum(x['level']=='warning' for x in findings)}")
        return 1 if problems else 0

    def find(self, a):
        d, lib, plan, profile = self.locate(a)
        self.fresh(a.work, d, plan)
        if a.limit < 1:
            raise ValueError("--limit 必须大于 0")
        root = Path(plan["target"]) if plan["applied"] else self.base(a.work, plan) / "staging"
        rows = self.query(self.tree(root), a.words)
        for r in rows[:a.limit]:
            print(f"{r['relative']} SHA {r['sha']}")
            for n, row in enumerate(r["text"].splitlines(), 1):
                if any(w.casefold() in row.casefold() for w in a.words):
                    print(f"  {n}: {row[:250]}")
        print(f"匹配 {len(rows)} 份；按用途、条件和引用判断采用，完整内容位于 {root}")

    def apply(self, a):
        d, lib, plan, profile = self.locate(a)
        self.p.nonempty(a.authorization, "本次具体源库/成果库写入授权")
        problems, _ = self.checked(a, d, plan, profile)
        if problems:
            raise ValueError("不能交付：\n" + "\n".join(problems))
        if plan["applied"]:
            print("OK 已交付且仍有效；未重复写入")
            return
        target = Path(plan["target"])
        if target.is_symlink() or target.resolve() != target:
            raise ValueError("目标根或上级路径已被重定向；停止旧计划交付")
        staging = self.base(a.work, plan) / "staging"
        if plan["mode"] == "copy":
            if target.exists():
                raise ValueError("新库目标已存在；选择新的成果路径，不覆盖已有库")
            planned = {f["path"]: f["sha"] for b in plan["batches"] for f in b["files"]}
            plan["transaction"] = {"mode": "copy", "new": planned, "authorization": a.authorization}
            self.p.save(a.work, d, f"library-apply-start {plan['id']}")
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = Path(tempfile.mkdtemp(prefix=".ncc-library-", dir=target.parent))
            try:
                shutil.copytree(staging, tmp, dirs_exist_ok=True)
                if {r["relative"]: r.get("sha") for r in self.tree(tmp)} != planned:
                    raise ValueError("交付期间成果已变；恢复事务后重新登记和验收")
                self.fresh(a.work, d, plan)
                if target.exists():
                    raise ValueError("交付期间目标已被创建，停止覆盖")
                os.rename(tmp, target)
            finally:
                if tmp.exists():
                    shutil.rmtree(tmp)
        else:
            old = {r["relative"]: r for r in plan["inputs"]}
            new = {r["relative"]: r for r in self.tree(staging)}
            # No opaque or linked files can be moved by this text governance transaction.
            if any(r["status"] != "readable" for r in old.values()):
                raise ValueError("原地治理包含未读取/链接文件；转换后重规划，或交付到新库")
            backup = self.base(a.work, plan) / "backup"
            backup.mkdir(parents=True, exist_ok=True)
            for path in old:
                self.p.atomic(self.p.safe_local(backup, path), self.p.read_stable(self.p.safe_local(target, path)))
            plan["transaction"] = {"mode": "in-place", "old": {x: r["sha"] for x, r in old.items()}, "new": {x: r["sha"] for x, r in new.items()},
                                   "authorization": a.authorization}
            self.p.save(a.work, d, f"library-apply-start {plan['id']}")
            try:
                self.fresh(a.work, d, plan)
                for path in sorted(set(old) | set(new)):
                    dest = self.p.safe_local(target, path)
                    current = self.p.digest(self.p.read_stable(dest)) if dest.exists() else None
                    if current != old.get(path, {}).get("sha"):
                        raise ValueError(f"应用期间来源改变：{path}；保留事务，先恢复")
                    if path in new:
                        data = self.p.read_stable(staging / path)
                        if self.p.digest(data) != new[path]["sha"]:
                            raise ValueError("交付期间成果已变，停止使用旧验收")
                        self.p.atomic(dest, data)
                    else:
                        dest.unlink()  # Original bytes are retained in the versioned backup.
            except (OSError, ValueError):
                raise ValueError("原地交付中断；备份与事务已保存，运行 library-restore 后继续")
        expected = plan["transaction"]["new"]
        if {r["relative"]: r.get("sha") for r in self.tree(target)} != expected:
            raise ValueError("交付目标出现外部改动；事务已保留，先处理并恢复")
        if plan["mode"] == "copy":
            self.fresh(a.work, d, plan)
        applied_rows = self.inputs(a.work, d)
        plan["applied"] = {"at": self.p.now(), "authorization": a.authorization, "input_stamp": self.fingerprint(applied_rows)}
        plan["transaction"] = None
        self.p.save(a.work, d, f"library-apply {plan['id']}")
        print(f"OK 实际素材库：{target}；来源处置和检查依据保留在 {self.base(a.work, plan)}")

    def restore(self, a):
        d, lib = self.data(a.work)
        plan = self.p.find(lib["plans"], a.plan)
        tx = plan["transaction"]
        self.p.nonempty(a.authorization, "恢复授权")
        if not tx:
            raise ValueError("没有未完成的原地交付事务")
        root, backup = Path(plan["target"]), self.base(a.work, plan) / "backup"
        if root.is_symlink() or root.resolve() != root:
            raise ValueError("目标根或上级路径已被重定向；停止旧事务恢复")
        if tx.get("mode") == "copy":
            if root.exists():
                if {r["relative"]: r.get("sha") for r in self.tree(root)} != tx["new"]:
                    raise ValueError("交付目标有外部改动；停止恢复")
                archive = self.base(a.work, plan) / "interrupted-copy"
                if archive.exists():
                    raise ValueError("中断交付归档已存在；先人工检查，不覆盖")
                shutil.move(str(root), str(archive))
            plan["transaction"] = None
            self.p.save(a.work, d, f"library-restore {plan['id']}")
            print("OK 中断的新库交付已归档，目标恢复为空；重新验收后继续")
            return
        # Check all paths first; preserve external changes rather than partially restoring.
        for path in set(tx["old"]) | set(tx["new"]):
            p = self.p.safe_local(root, path)
            sha = self.p.digest(self.p.read_stable(p)) if p.exists() else None
            if sha not in (tx["old"].get(path), tx["new"].get(path), None):
                raise ValueError(f"恢复发现外部改动：{path}；先人工处理，未覆盖")
            if path in tx["old"] and self.p.digest(self.p.read_stable(backup / path)) != tx["old"][path]:
                raise ValueError("备份内容损坏；停止恢复")
        for path in sorted(set(tx["old"]) | set(tx["new"])):
            dest = self.p.safe_local(root, path)
            if path in tx["old"]:
                self.p.atomic(dest, self.p.read_stable(backup / path))
            elif dest.exists():
                dest.unlink()
        plan["transaction"] = None
        self.p.save(a.work, d, f"library-restore {plan['id']}")
        print("OK 原地交付已恢复；重新检查后可再应用")


def register(command, prep):
    lib = Library(prep)
    s = command("library-profile", lib.profile, "登记适配本库的组织规范")
    s.add_argument("--file", type=Path, required=True); s.add_argument("--reason", required=True)
    s = command("library-audit", lib.audit, "链接、字段、标识及显式数值约束体检")
    s.add_argument("--target", type=Path)
    s = command("library-plan", lib.plan, "全库覆盖、来源处置、批次及写作取用计划")
    s.add_argument("--file", type=Path, required=True); s.add_argument("--reason", required=True)
    for name, fn, text in (("library-packet", lib.packet, "生成自包含库工程任务包"),
                           ("library-batch", lib.batch, "登记一批实际内容和处置报告"),
                           ("library-review", lib.review, "登记全库语义及取用复核"),
                           ("library-check", lib.check, "验收全库覆盖、内容与检查有效性"),
                           ("library-find", lib.find, "按写作需求检索治理成果"),
                           ("library-apply", lib.apply, "交付新库或按授权应用原地治理"),
                           ("library-restore", lib.restore, "恢复中断的原地交付")):
        s = command(name, fn, text)
        s.add_argument("--plan", required=True)
        if name in ("library-packet", "library-batch"):
            s.add_argument("--batch", required=True)
        if name in ("library-batch", "library-review"):
            s.add_argument("--file", type=Path, required=True); s.add_argument("--by", required=True)
        if name == "library-batch":
            s.add_argument("--report", type=Path, required=True)
            s.add_argument("--execution", choices=("current", "native", "fallback"), required=True)
        if name == "library-review":
            s.add_argument("--result", choices=("pass", "needs_work"), required=True)
        if name == "library-find":
            s.add_argument("words", nargs="+"); s.add_argument("--limit", type=int, default=10)
        if name in ("library-apply", "library-restore"):
            s.add_argument("--authorization", required=True)
