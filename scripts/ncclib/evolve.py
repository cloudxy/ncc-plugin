"""自进化：进化提议、评测闸门、作者覆盖层、撤回、生效值、证据扫描。依赖 core 与 settings。

四档：自动（记忆、技法状态，脚本直接做）、作者确认、评测＋作者确认、永不自动——见注册表 evolution。
规则改动不改插件本体，写进作者覆盖层 {书库}/_作者/进化/覆盖.json：插件默认 < 作者覆盖 < 本书设置。
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from .core import (EVOLUTION, EVOLUTION_LOG, L, OVERLAY, PLUGIN_ROOT, REGISTRY, append_jsonl, book_root, category_catalog, die, next_id, now, read_json, read_jsonl, split_names, write_json)
from .core import resolved_config


KEYS = EVOLUTION["keys"]


def proposals(root: Path) -> dict:
    """把只追加的提议日志折叠成每条提议的现状。"""
    out = {}
    for r in read_jsonl(root / EVOLUTION_LOG):
        if r.get("op") == "propose":
            out[r["id"]] = {**r, "state": "待评测" if KEYS[r["key"]]["tier"] == "评测＋作者确认" else "待作者确认",
                            "eval": None, "applied": None}
        elif r.get("id") in out:
            p = out[r["id"]]
            if r["op"] == "eval":
                p["eval"] = r
                p["state"] = "评测通过，待作者确认" if r["result"] == "pass" else "评测变差，不能生效"
            elif r["op"] == "apply":
                p["applied"], p["state"] = r, "已生效"
            elif r["op"] == "reject":
                p["state"] = "作者否决"
            elif r["op"] == "revert":
                p["state"] = "已撤回"
    return out


def parse_value(key: str, raw: str):
    t = KEYS[key]["type"]
    if t == "int":
        if not re.fullmatch(r"\d+", raw.strip()):
            die(f"{key} 要一个整数")
        return int(raw)
    if t == "words":
        items = split_names(raw)
        if not items:
            die(f"{key} 写成 +词 或 -词，多个用逗号隔开")
        if key == "technique.kinds":
            for item in items:
                if item.startswith("-"):
                    continue
                name, _, parent = item.lstrip("+").partition(":")
                if not name or (parent and parent not in REGISTRY["vocab"]["technique_kinds"]["values"]):
                    die("新技法类别的父类必须是内置技法类别")
                if parent and name in REGISTRY["vocab"]["technique_kinds"]["values"] and name != parent:
                    die("不能通过新增类别改变内置类别的可见范围")
        return items
    m = re.fullmatch(r"\s*([^:：]+)[:：](.+)", raw)
    if not m:
        die(f"{key} 写成 类目名:必填字段1,字段2,字段3")
    fields = split_names(m.group(2))
    if len(fields) < 3:
        die("新类目至少三个必填字段")
    return {m.group(1).strip(): {"required": fields}}


def merged(values: dict, key: str, value) -> dict:
    out = json.loads(json.dumps(values))
    t = KEYS[key]["type"]
    if t == "int":
        out[key] = value
    elif t == "words":
        out[key] = list(out.get(key, [])) + list(value)
    else:
        out.setdefault(key, {}).update(value)
    return out


def overlay_file(root: Path) -> Path:
    return root / OVERLAY


def current(root: Path) -> dict:
    return read_json(overlay_file(root), {}).get("values", {})


def without_proposal(root: Path, pid: str, key: str) -> dict:
    """从该项首次应用前的值重放仍生效的提议；撤回旧项不覆盖后来的改动。"""
    ps = proposals(root)
    applications = [r for r in read_jsonl(root / EVOLUTION_LOG)
                    if r.get("op") == "apply" and ps.get(r.get("id"), {}).get("key") == key]
    values = current(root)
    initial = applications[0].get("prev")
    values.pop(key, None)
    if initial is not None:
        values[key] = initial
    # 同一提议撤回后再应用时，只有最后一次应用参与，顺序按日志而非时间戳。
    latest = {r["id"]: index for index, r in enumerate(applications)}
    for index, row in enumerate(applications):
        other = ps[row["id"]]
        if row["id"] != pid and latest[row["id"]] == index and other["state"] == "已生效":
            values = merged(values, key, other["value"])
    return values


def run_gate(base: dict, cand: dict):
    """锚定章回归：改动前后各跑一次，交给 ncc_eval.py gate 比较。"""
    with tempfile.TemporaryDirectory() as t:
        b, c = Path(t) / "baseline.json", Path(t) / "candidate.json"
        write_json(b, {"values": base})
        write_json(c, {"values": cand})
        env = {k: v for k, v in os.environ.items() if k != "NCC_OVERLAY"}
        r = subprocess.run([sys.executable, str(PLUGIN_ROOT / "scripts" / "ncc_eval.py"), "gate", "--baseline", str(b),
                            "--candidate", str(c)], capture_output=True, text=True, env=env)
        return r.returncode == 0, (r.stdout + r.stderr).strip()


def books(root: Path) -> list:
    return [p.parent for p in sorted(root.glob("*/book.json"))]


def scan(root: Path) -> list:
    """从各书的证据里找规则级改动的苗头：多本书都新提过的类目、多本书都放行过的一级词。"""
    cfg = EVOLUTION["scan"]
    found = []
    cats, catalog = {}, category_catalog(root)
    for b in books(root):
        d = read_json(b / "book.json", {})
        for name, spec in ((d.get("setting_categories") or {}).get("used") or {}).items():
            if spec.get("custom") and name not in catalog:
                cats.setdefault(name, {"books": [], "fields": []})
                cats[name]["books"].append(d.get("title") or b.name)
                cats[name]["fields"] += [f for f in spec.get("required", []) if f not in cats[name]["fields"]]
    for name, x in cats.items():
        if len(x["books"]) >= cfg["category_books"]:
            found.append(("setting.categories", f"{name}:{','.join(x['fields'])}",
                          f"新类目「{name}」在 {len(x['books'])} 本书里都用过（{'、'.join(x['books'])}）", x["books"]))
    level1 = REGISTRY["check_words"]["level1"]
    waived = {}
    for b in books(root):
        p = b / L("waivers")
        if not p.exists():
            continue
        snippets = re.findall(r"「([^」]+)」", p.read_text("utf-8"))
        for w in level1:
            n = sum(s.count(w) for s in snippets)
            if n:
                waived.setdefault(w, []).append((b.name, n))
    for w, rows in waived.items():
        if len(rows) >= cfg["waiver_books"] and sum(n for _, n in rows) >= cfg["waiver_hits"]:
            found.append(("check.level1_words", f"-{w}", f"一级词「{w}」在 {len(rows)} 本书里被作者放行 {sum(n for _, n in rows)} 次",
                          [f"{b} 放行清单 {n} 处" for b, n in rows]))
    return found


def cmd_evolve(a):
    root = book_root(Path(a.path))
    props = proposals(root)
    if a.action == "propose":
        if a.key not in KEYS:
            die(f"--key 只能是 {'、'.join(KEYS)}。永不自动的（{'、'.join(EVOLUTION['never'])}）只有作者主动要求，在开发会话里改插件本体")
        raw = a.value
        if getattr(a, "parent", None):
            if a.key != "technique.kinds":
                die("--parent 只用于新增技法类别")
            if any(x.startswith("-") or ":" in x for x in split_names(raw)):
                die("--parent 只用于 +类别名，不用于删除或重复指定父类")
            raw = ",".join(f"{x}:{a.parent}" for x in split_names(raw))
        value = parse_value(a.key, raw)
        if not a.evidence:
            die("提议要带证据（--evidence，可多次）：哪本书、哪几章、哪次审稿或放行")
        rec = {"op": "propose", "id": next_id(list(props.values()), "EP"), "key": a.key, "value": value, "raw": raw,
               "why": a.why, "evidence": a.evidence, "tier": KEYS[a.key]["tier"], "at": now()}
        append_jsonl(root / EVOLUTION_LOG, rec)
        nxt = "evolve eval 跑锚定章回归" if rec["tier"] == "评测＋作者确认" else "呈给作者，确认后 evolve apply --quote"
        print(f"OK {rec['id']}（{rec['tier']}）{a.key} ← {raw}；下一步：{nxt}")
        return
    if a.action == "list":
        for p in props.values():
            if a.open and p["state"] in ("已生效", "作者否决", "已撤回"):
                continue
            print(f"{p['id']} [{p['tier']}] {p['state']}：{p['key']} ← {p['raw']}｜{p['why']}｜证据：{'；'.join(p['evidence'])}")
        if not props:
            print("（还没有进化提议；evolve scan 从各书的证据里找苗头）")
        return
    if a.action == "rules":
        over = current(root)
        cfg, sources = resolved_config(Path(a.path))
        for key, spec in KEYS.items():
            if spec["type"] == "int":
                val, src = cfg[key[6:]], sources[key[6:]]
            elif key in over:
                val, src = "、".join(map(str, over[key])) if isinstance(over[key], list) else "、".join(over[key]), "作者覆盖"
            else:
                val, src = "（不改）", "插件默认"
            print(f"{key}（{spec['what']}）= {val}  ← {src}")
        print("优先级：插件默认 < 书库配置 < 作者覆盖 < 本书配置；传书目录时显示该书的实际值")
        return
    if a.action == "scan":
        found = scan(root)
        for key, raw, why, ev in found:
            dup = any(p["key"] == key and p["raw"] == raw for p in props.values())
            print(f"- {key} ← {raw}：{why}" + ("（已有提议）" if dup else ""))
            if a.propose and not dup:
                rec = {"op": "propose", "id": next_id(list(proposals(root).values()), "EP"), "key": key,
                       "value": parse_value(key, raw), "raw": raw, "why": why, "evidence": ev, "tier": KEYS[key]["tier"], "at": now()}
                append_jsonl(root / EVOLUTION_LOG, rec)
                print(f"  → 已记为 {rec['id']}")
        if not found:
            print("没有找到规则级改动的苗头")
        return
    p = props.get(a.id) or die(f"没有提议 {a.id}")
    if a.action in ("eval", "reject") and p["state"] == "已生效":
        die(f"{a.id} 已生效；要取消请 evolve revert，要变更请新建提议")
    if a.action == "eval":
        if p["tier"] != "评测＋作者确认":
            print(f"{a.id} 是「{p['tier']}」档，不用跑评测，呈给作者确认即可")
            return
        ok, out = run_gate(current(root), merged(current(root), p["key"], p["value"]))
        append_jsonl(root / EVOLUTION_LOG, {"op": "eval", "id": a.id, "result": "pass" if ok else "fail", "detail": out[-1500:], "at": now()})
        print(out)
        print(f"{'OK 评测通过' if ok else 'FAIL 评测变差'}：{a.id}" + ("，可以呈给作者确认（evolve apply --quote）" if ok else "，不能生效"))
        sys.exit(0 if ok else 1)
    if a.action == "apply":
        if p["state"] == "已生效":
            die(f"{a.id} 已经生效")
        if p["tier"] == "评测＋作者确认" and not (p["eval"] and p["eval"]["result"] == "pass"):
            die(f"{a.id} 要先过锚定章回归（evolve eval {a.id}），变差的改动不能生效")
        if not (a.quote or "").strip():
            die("生效要附作者原话（--quote）：规则改动由作者确认")
        values = current(root)
        if p["tier"] == "评测＋作者确认":
            ok, out = run_gate(values, merged(values, p["key"], p["value"]))
            if not ok:
                die("当前覆盖层下评测变差，不能生效；请重新 evolve eval\n" + out)
        prev = values.get(p["key"])
        write_json(overlay_file(root), {"values": merged(values, p["key"], p["value"]), "updated_at": now()})
        append_jsonl(root / EVOLUTION_LOG, {"op": "apply", "id": a.id, "prev": prev, "quote": a.quote, "at": now()})
        print(f"OK {a.id} 生效：{p['key']} ← {p['raw']}（evolve revert {a.id} 可撤回）")
        return
    if a.action == "reject":
        append_jsonl(root / EVOLUTION_LOG, {"op": "reject", "id": a.id, "note": a.note or "", "at": now()})
        print(f"OK {a.id} 作者否决")
        return
    # revert
    if p["state"] != "已生效":
        die(f"{a.id} 没有生效过（现在：{p['state']}）")
    values = without_proposal(root, a.id, p["key"])
    write_json(overlay_file(root), {"values": values, "updated_at": now()})
    append_jsonl(root / EVOLUTION_LOG, {"op": "revert", "id": a.id, "note": a.note or "", "at": now()})
    print(f"OK {a.id} 已撤回：{p['key']} = {values.get(p['key'], '插件默认')}（其余生效提议保留）")
