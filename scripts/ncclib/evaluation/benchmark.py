#!/usr/bin/env python3
"""ncc_eval.py — 判据层回归评测与模型横评（M7）。只依赖标准库。

审稿判据写在文档里，靠模型执行；文档改一句，审稿的行为可能就变了。这个脚本用一组故意埋了错的
锚定章（eval/anchors/），量审稿的检出率、误报和稳定性；同一套锚定章每次改判据后重跑，就是回归测试。
脚本不调用任何模型：它生成派单包、读回审稿报告、对照答案打分；派单由宿主（经理）完成。

锚定章回归
  anchors                                列出锚定章与预期（不含答案细节）
  mech                                   机械层回归：check_chapter.py 的提醒是否命中锚定章里埋的错，干净章不误报（确定性）
  prepare <run_dir> [--suite 底蕴|连贯|承诺|对照] [--runs 3]
                                         生成 continuity 审稿派单包到 <run_dir>/packets/（不含答案），报告回收到 <run_dir>/reports/
  score <run_dir>                        对照答案算检出率、定级、结论准确率、干净章误报、多次之间的稳定性，写 <run_dir>/score.md
  gate --baseline B.json --candidate C.json
                                         规则改动的闸门（evolve eval 调用）：用两份覆盖层各跑一遍锚定章的机械层，
                                         候选不许漏掉原来报得出的错、不许在干净章上多报；变差退出 1
  anchor new <编号-名字> --suite 底蕴|连贯|承诺|对照 --era 时代 [--clean]
                                         漏检变锚定章：建一章锚定章的骨架（正文要原创复述，不摘真书）

模型横评（同一个写手包，换不同模型写同一章）
  bench init <book> <seq>                冻结本章写手包的 SHA，建 .ncc/横评/ch-NNNN/
  bench add <book> <seq> --model M --file F    登记一个模型写的草稿；写手包变过就拒绝（比的必须是同一个包）
  bench blind <book> <seq>               打乱成 A/B/C… 盲稿，列出成对比较与记忆测试的派单
  bench vote <book> <seq> --winner A --loser B [--tie]   登记一次成对比较结论（用盲标签）
  bench score <book> <seq>               揭盲：各模型的机械指标与成对比较胜率，写 score.md
"""
import argparse
import os
import itertools
import json
import random
import re
import shutil
import sys
import tempfile
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

from ..assets.learning import style_drift_lines
from ..foundation.core import PLUGIN_ROOT, WORK, die, find_ch, load, now, read_json, sha16, write_json
from ..quality import chapter_check as cc

ANCHORS = PLUGIN_ROOT / "eval" / "anchors"
SEVERE = ("critical", "major")


# ---------- 锚定章 ----------

def anchor_roots(dirs=None):
    out = []
    for p in (dirs or [ANCHORS]):
        cand = Path(p)
        if not cand.is_absolute() and (PLUGIN_ROOT / cand).exists():
            cand = PLUGIN_ROOT / cand
        out.append(cand.resolve())
    return out


def _portable_path(p: Path) -> str:
    rp = Path(p).resolve()
    root = PLUGIN_ROOT.resolve()
    return rp.relative_to(root).as_posix() if rp.is_relative_to(root) else str(rp)


def anchors(suite=None, dirs=None):
    out, seen = [], set()
    for root in anchor_roots(dirs):
        if not root.is_dir():
            die(f"锚定章目录不存在：{root}")
        for d in sorted(p for p in root.iterdir() if p.is_dir() and (p / "answers.json").is_file()):
            ans = json.loads((d / "answers.json").read_text("utf-8"))
            if ans["id"] in seen:
                die(f"锚定章编号重复：{ans['id']}")
            seen.add(ans["id"])
            if suite and ans["suite"] != suite:
                continue
            out.append((d, ans))
    if not out:
        die(f"没有锚定章（{', '.join(map(str, anchor_roots(dirs)))}）" + (f"属于「{suite}」" if suite else ""))
    return out


def mech_warnings(era: str, text: str, ans: dict = None) -> list:
    with tempfile.TemporaryDirectory() as t:
        book = Path(t)
        bj = {"era": era}
        seq = int((ans or {}).get("seq") or 2)
        prev_hook = (ans or {}).get("prev_hook")
        if isinstance(prev_hook, dict):
            bj["chapters"] = [
                {
                    "seq": seq - 1,
                    "hook": {
                        "type": prev_hook.get("type", "悬剑钩"),
                        "intensity": prev_hook.get("intensity", 5),
                        "line": prev_hook.get("line", ""),
                    },
                    "end": {"next": prev_hook.get("next", "")},
                }
            ]
        (book / "book.json").write_text(json.dumps(bj, ensure_ascii=False), "utf-8")
        warns, _ = cc.knowledge_warnings(book, text)
        warns += cc.avoidance_warnings(text, cc.load_config(book))
        if isinstance(prev_hook, dict):
            warns += cc.hook_handoff_warnings(book, seq, text)
        return warns


def cmd_anchors(a):
    for d, ans in anchors(a.suite, getattr(a, "anchors_dirs", None)):
        print(f"{ans['id']} [{ans['suite']}] 时代：{ans['era']}  预期结论：{'通过' if ans['verdict'] == 'pass' else '不通过'}  "
              f"埋错 {len(ans['expected'])} 处" + (f"  机械层应提醒：{'、'.join(ans['mech'])}" if ans.get("mech") else ""))


def cmd_mech(a):
    bad = 0
    for d, ans in anchors(a.suite, getattr(a, "anchors_dirs", None)):
        warns = mech_warnings(ans["era"], (d / "正文.md").read_text("utf-8"), ans)
        miss = [m for m in ans.get("mech", []) if not any(m in w for w in warns)]
        noise = [w for w in warns if w.startswith(("底蕴", "跨章断章承接"))] if ans.get("mech_clean") else []
        ok = not miss and not noise
        bad += not ok
        print(f"{'PASS' if ok else 'FAIL'} {ans['id']}" + (f"  漏报：{'、'.join(miss)}" if miss else "")
              + (f"  干净章误报：{'；'.join(noise)}" if noise else ""))
    sys.exit(1 if bad else 0)


PACKET_HEAD = """# 评测派单包：{code}

```yaml
role: continuity
task: audit（评测）
deliverable: {report}
```

这是一章评测用的锚定章。像审真书一样，按 `skills/ncc-review/references/review-domains.md` 的硬伤层审；只依据下面给的材料，不找别的文件。

**输出格式**（脚本按它打分，必须照写）：

- 第一行：`硬伤层: 通过` 或 `硬伤层: 不通过`
- 然后一张表：`| # | 类别 | 严重度 | 正文引用 | 问题 | 推荐处置与理由 |`。严重度只写 critical、major、minor；正文引用用「」括原句。没有问题就在表里写一行"无"。
"""


def _sanitize_section(text: str, aid: str) -> str:
    cleaned = []
    hint = aid.split("-", 1)[1] if "-" in aid else ""
    for line in text.strip().splitlines():
        if line.lstrip().startswith("#"):
            line = line.replace(aid, "").strip()
            if hint and len(hint) >= 2:
                line = line.replace(hint, "").strip()
            if re.fullmatch(r"#+\s*", line):
                continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def _assert_no_spoiler(head: str, packet_text: str, ans: dict):
    aid = ans["id"]
    headings = "\n".join(l for l in packet_text.splitlines() if l.lstrip().startswith("#"))
    envelope = head + "\n" + headings
    if aid in envelope or ("-" in aid and aid in packet_text):
        die(f"匿名化失败：派单包仍含题号 {aid}")
    if "干净对照" in packet_text:
        die(f"匿名化失败：派单包仍含对照提示词（{aid}）")
    if "-" in aid:
        hint = aid.split("-", 1)[1]
        if len(hint) >= 2 and hint in envelope:
            die(f"匿名化失败：派单包标题或包头仍含缺陷提示词「{hint}」（{aid}）")
    for exp in ans.get("expected", []):
        desc = (exp.get("desc") or "").strip()
        if len(desc) >= 6 and desc in packet_text:
            die(f"匿名化失败：派单包泄露答案说明（{aid} {exp.get('id')}）")


def cmd_prepare(a):
    if a.runs < 1:
        die("--runs 至少为 1")
    run = Path(a.run_dir)
    if (run / "manifest.json").exists():
        die(f"{run} 已有一次评测（换个目录，或删掉重来）")
    packets_dir = Path(a.packets_dir) if getattr(a, "packets_dir", None) else (run / "packets")
    if packets_dir.exists() and any(packets_dir.glob("*.md")):
        die(f"{packets_dir} 已有派单包（换个空目录）")
    run.mkdir(parents=True, exist_ok=True)
    packets_dir.mkdir(parents=True, exist_ok=True)
    (run / "reports").mkdir(exist_ok=True)
    dirs = getattr(a, "anchors_dirs", None)
    chosen = anchors(a.suite, dirs)
    assembled = {}
    for d, ans in chosen:
        aid = ans["id"]
        body = _sanitize_section((d / "正文.md").read_text("utf-8"), aid)
        parts = ["## 本书设定与台账摘录", "", _sanitize_section((d / "台账.md").read_text("utf-8"), aid), "",
                 "## 本章场景卡", "", _sanitize_section((d / "场景卡.md").read_text("utf-8"), aid), ""]
        if (d / "知识点.md").exists():
            parts += ["## 本章知识点清单", "", _sanitize_section((d / "知识点.md").read_text("utf-8"), aid), ""]
        warns = mech_warnings(ans["era"], body, ans)
        parts += ["## 脚本的机械提醒（check_chapter.py，只是提醒，是错是对由你判断）", ""]
        parts += [f"- {w}" for w in warns] or ["- （无）"]
        parts += ["", "## 正文", "", body, ""]
        assembled[aid] = (ans, "\n".join(parts))

    pairs = [(ans["id"], k) for _, ans in chosen for k in range(1, a.runs + 1)]
    seed = getattr(a, "seed", None) or f"{run.name}:{a.runs}:" + ",".join(ans["id"] for _, ans in chosen)
    random.Random(seed).shuffle(pairs)
    width = max(2, len(str(len(pairs))))
    blind = {}
    for idx, (aid, k) in enumerate(pairs, 1):
        code = f"M{idx:0{width}d}"
        ans, body_block = assembled[aid]
        head = PACKET_HEAD.format(code=code, report=f"reports/{code}.md")
        full_packet = head + "\n" + body_block
        _assert_no_spoiler(head, full_packet, ans)
        (packets_dir / f"{code}.md").write_text(full_packet, "utf-8")
        blind[code] = {"anchor": aid, "run": k}

    write_json(run / "manifest.json", {
        "anchors": [ans["id"] for _, ans in chosen],
        "anchor_dirs": [_portable_path(p) for p in anchor_roots(dirs)],
        "runs": a.runs,
        "suite": a.suite or "全部",
        "packets_dir": _portable_path(packets_dir),
        "blind": blind,
        "created": now(),
    })
    print(f"OK {len(chosen)} 章 × {a.runs} 次 = {len(pairs)} 个匿名派单包 → {packets_dir}")
    print("每个包派一次 continuity（fresh 上下文，互不看别的报告），报告按包里的 deliverable 存到 reports/，然后 score。")


def norm(s: str) -> str:
    return re.sub(r"[^一-鿿A-Za-z0-9]", "", s or "")


def parse_report(text: str):
    m = re.search(r"硬伤层[*`\s]*[:：][*`\s]*(不通过|通过)", text)
    verdict = {"通过": "pass", "不通过": "fail"}.get(m.group(1)) if m else None
    obs, cols = [], None
    for line in text.splitlines():
        t = line.strip()
        if not t.startswith("|"):
            cols = None
            continue
        cells = [c.replace(r"\|", "|").strip() for c in re.split(r"(?<!\\)\|", t.strip("|"))]
        if "正文引用" in cells and "严重度" in cells:
            cols = {name: i for i, name in enumerate(cells)}
            continue
        if cols is None or set(t) <= {"|", "-", " ", ":"}:
            continue
        get = lambda k: cells[cols[k]] if k in cols and cols[k] < len(cells) else ""
        if norm(get("问题") + get("正文引用")) in ("", "无"):
            continue
        sev = get("严重度").lower()
        obs.append({"severity": next((s for s in ("critical", "major", "minor") if s in sev), sev),
                    "category": get("类别"), "cite": get("正文引用"), "problem": get("问题")})
    return verdict, obs


def matches(exp: dict, ob: dict) -> bool:
    cite = norm(ob["cite"])
    for q in exp.get("quotes", []):
        nq = norm(q)
        if not nq or not cite:
            continue
        if nq in cite or (len(cite) >= 4 and cite in nq):
            return True
        if SequenceMatcher(None, nq, cite).find_longest_match(0, len(nq), 0, len(cite)).size >= min(6, len(nq)):
            return True
    kws = exp.get("keywords", [])
    return bool(kws) and all(k in ob["cite"] + ob["problem"] for k in kws)


def cmd_score(a):
    run = Path(a.run_dir)
    man = read_json(run / "manifest.json", None)
    if not man:
        die(f"{run} 不是评测目录（先 prepare）")
    dirs = getattr(a, "anchors_dirs", None) or man.get("anchor_dirs")
    keys = {ans["id"]: ans for _, ans in anchors(dirs=dirs)}
    blind_map = man.get("blind") or {}
    code_by_pair = {(v["anchor"], v["run"]): code for code, v in blind_map.items()}
    found = need = graded = verdict_ok = runs_done = false_alarm = 0
    r1_found = r1_need = r1_graded = r1_verdict_ok = r1_runs_done = r1_false_alarm = 0
    missing, unstable, extras, lines = [], [], [], []
    for aid in man["anchors"]:
        ans = keys[aid]
        verdicts, per_def = [], {e["id"]: [] for e in ans["expected"]}
        for k in range(1, man["runs"] + 1):
            code = code_by_pair.get((aid, k))
            cand_paths = ([run / "reports" / f"{code}.md"] if code else []) + [run / "reports" / f"{aid}-r{k}.md"]
            p = next((cp for cp in cand_paths if cp.exists()), None)
            if p is None:
                missing.append(f"{code}.md（{aid} r{k}）" if code else f"{aid}-r{k}.md")
                continue
            runs_done += 1
            verdict, obs = parse_report(p.read_text("utf-8"))
            verdicts.append(verdict)
            v_match = verdict == ans["verdict"]
            verdict_ok += v_match
            if k == 1:
                r1_runs_done += 1
                r1_verdict_ok += v_match
            used = set()
            for e in ans["expected"]:
                hit = [i for i, ob in enumerate(obs) if matches(e, ob)]
                used.update(hit)
                ok_sev = any(obs[i]["severity"] in SEVERE for i in hit)
                per_def[e["id"]].append(bool(hit))
                found += bool(hit)
                graded += ok_sev
                need += 1
                if k == 1:
                    r1_found += bool(hit)
                    r1_graded += ok_sev
                    r1_need += 1
            rest = [ob for i, ob in enumerate(obs) if i not in used]
            if ans["verdict"] == "pass":
                fa = sum(1 for ob in rest if ob["severity"] in SEVERE)
                false_alarm += fa
                if k == 1:
                    r1_false_alarm += fa
            tag = f"{aid} r{k}" + (f"（{code}）" if code else "")
            extras += [f"{tag}：[{ob['severity']}] {ob['cite'][:30]}——{ob['problem'][:40]}" for ob in rest]
        if not verdicts:
            lines.append(f"| {aid} | （无报告） | | |")
            continue
        top = max(set(verdicts), key=verdicts.count)
        consist = verdicts.count(top) / len(verdicts)
        det = "；".join(f"{d} {sum(v)}/{len(v)}" for d, v in per_def.items()) or "（干净章）"
        shaky = [d for d, v in per_def.items() if 0 < sum(v) < len(v)]
        if consist < 1 or shaky:
            unstable.append(f"{aid}" + (f"（结论 {consist:.0%} 一致）" if consist < 1 else "") + (f"（{'、'.join(shaky)} 时有时无）" if shaky else ""))
        lines.append(f"| {aid} | {'通过' if ans['verdict'] == 'pass' else '不通过'} | "
                     + "／".join({"pass": "通过", "fail": "不通过"}.get(v, "未写") for v in verdicts) + f" | {det} |")
    pct = lambda x, y: f"{x}/{y}（{x / y:.0%}）" if y else "—"
    out = [f"# 判据层评测：{run.name}", "", f"> {now()}｜锚定章 {len(man['anchors'])} 章 × {man['runs']} 次，收回报告 {runs_done} 份",
           "", "## 总览", "",
           f"- 检出率（埋的错被指出）：{pct(found, need)}",
           f"- 定级到位（指出时定为 critical 或 major）：{pct(graded, need)}",
           f"- 结论准确率（通过／不通过判对）：{pct(verdict_ok, runs_done)}",
           f"- 干净章误报（critical／major）：{false_alarm} 条",
           f"- 不稳定：{'；'.join(unstable) or '无'}"]
    if man["runs"] > 1:
        out.append(f"- 单轮基线（r1，收回 {r1_runs_done}/{len(man['anchors'])} 份）：检出 {pct(r1_found, r1_need)}，"
                   f"定级 {pct(r1_graded, r1_need)}，结论准确 {pct(r1_verdict_ok, r1_runs_done)}，干净章误报 {r1_false_alarm} 条")
    out += ["", "## 逐章", "", "| 锚定章 | 应为 | 各次结论 | 各处埋错的检出 |", "|---|---|---|---|"] + lines
    if extras:
        out += ["", "## 答案之外的发现（人工看：是真问题就补进答案，是误报就记进判据的改进项）", ""] + [f"- {x}" for x in extras]
    if missing:
        out += ["", f"## 缺报告（{len(missing)} 份）", "", "- " + "、".join(missing)]
    (run / "score.md").write_text("\n".join(out) + "\n", "utf-8")
    print("\n".join(out))


# ---------- 模型横评 ----------

def bench_dir(book: Path, seq: int) -> Path:
    return book / WORK / "横评" / f"ch-{seq:04d}"


def bench_manifest(book: Path, seq: int) -> dict:
    m = read_json(bench_dir(book, seq) / "manifest.json", None)
    if not m:
        die(f"第 {seq} 章还没有横评（先 bench init）")
    return m


def mech_metrics(book: Path, text: str) -> dict:
    cfg = cc.load_config(book)
    block = sum(len(re.findall(p, text)) for p in cc.BLOCK_PATTERNS.values())
    high = sum(len(re.findall(p, text)) for p in cc.HIGH_RISK_PATTERNS.values()) + sum(text.count(w) for w in cc.LEVEL1_WORDS)
    return {"han": cc.han_count(text), "ai_block": block, "ai_high": high,
            "avoid": len(cc.avoidance_warnings(text, cfg)), "drift": len(style_drift_lines(book, text))}


def cmd_bench(a):
    book = Path(a.book_dir)
    d = load(book)
    c = find_ch(d, a.seq)
    bd = bench_dir(book, a.seq)
    if a.action == "init":
        pack = book / (c.get("pack") or "")
        if not pack.is_file() or pack.suffix != ".md":
            die(f"第 {a.seq} 章还没有写手包（先 ncc_state.py pack）")
        if (bd / "manifest.json").exists():
            die(f"第 {a.seq} 章已有横评：{bd}")
        bd.mkdir(parents=True, exist_ok=True)
        write_json(bd / "manifest.json", {"seq": a.seq, "pack": c["pack"], "pack_sha": sha16(pack), "created": now(),
                                          "drafts": {}, "blind": {}, "votes": []})
        print(f"OK 横评第 {a.seq} 章，写手包 SHA {sha16(pack)}。每个模型用这同一个包写一版，bench add 登记")
        return
    m = bench_manifest(book, a.seq)
    if a.action == "add":
        if sha16(book / m["pack"]) != m["pack_sha"]:
            die("写手包在横评开始后变了——不同模型拿到的不是同一个包，比较作废。重新 pack 后另开一次横评")
        src = Path(a.file)
        if not src.is_file():
            die(f"找不到草稿：{src}")
        name = re.sub(r"[^\w.-]+", "_", a.model)
        dest = bd / "drafts" / f"{name}.md"
        dest.parent.mkdir(exist_ok=True)
        shutil.copyfile(src, dest)
        m["drafts"][a.model] = {"file": str(dest.relative_to(book)), "sha": sha16(dest), "at": now(),
                                **mech_metrics(book, dest.read_text("utf-8"))}
        if m["blind"]:
            m["blind"], m["votes"] = {}, []
            print("  （新加了一版，之前的盲稿与投票作废，重新 bench blind）")
        write_json(bd / "manifest.json", m)
        print(f"OK {a.model} 的草稿已登记（{m['drafts'][a.model]['han']} 字）")
        return
    if a.action == "blind":
        models = sorted(m["drafts"])
        if len(models) < 2:
            die("至少两个模型的草稿才能比")
        random.Random(m["pack_sha"] + "".join(models)).shuffle(models)
        labels = [chr(ord("A") + i) for i in range(len(models))]
        m["blind"] = dict(zip(labels, models))
        (bd / "blind").mkdir(exist_ok=True)
        for lab, model in m["blind"].items():
            shutil.copyfile(book / m["drafts"][model]["file"], bd / "blind" / f"{lab}.md")
        m["votes"] = []
        write_json(bd / "manifest.json", m)
        print(f"OK 盲稿 {', '.join(labels)} → {bd / 'blind'}（对照表存在 manifest 里，评完再看）")
        print("成对比较（派 pulse，每组交换顺序各比一次，两次不一致记 --tie）：")
        for x, y in itertools.combinations(labels, 2):
            print(f"  - {x} vs {y}")
        print("记忆测试（派 reader，目标读者画像，每份盲稿各一次）：" + "、".join(labels))
        return
    if a.action == "vote":
        if not m["blind"]:
            die("先 bench blind")
        for lab in (a.winner, a.loser):
            if lab not in m["blind"]:
                die(f"没有盲稿 {lab}（有：{'、'.join(m['blind'])}）")
        m["votes"].append({"a": a.winner, "b": a.loser, "result": "tie" if a.tie else "a", "at": now()})
        write_json(bd / "manifest.json", m)
        print(f"OK {a.winner} {'＝' if a.tie else '＞'} {a.loser}")
        return
    # score
    wins = {k: 0.0 for k in m["drafts"]}
    games = {k: 0 for k in m["drafts"]}
    for v in m["votes"]:
        x, y = m["blind"][v["a"]], m["blind"][v["b"]]
        games[x] += 1
        games[y] += 1
        if v["result"] == "tie":
            wins[x] += 0.5
            wins[y] += 0.5
        else:
            wins[x] += 1
    label = {model: lab for lab, model in m["blind"].items()}
    out = [f"# 模型横评：第 {a.seq} 章", "", f"> 写手包 {m['pack']}（SHA {m['pack_sha']}）｜成对比较 {len(m['votes'])} 次", "",
           "| 模型 | 盲标签 | 胜率 | 字数 | 五星句式 | 高危句式与一级词 | 规避点提醒 | 文风漂移提醒 |", "|---|---|---|---|---|---|---|---|"]
    for model in sorted(m["drafts"], key=lambda k: -(wins[k] / games[k] if games[k] else 0)):
        x = m["drafts"][model]
        rate = f"{wins[model] / games[model]:.0%}（{wins[model]:g}/{games[model]}）" if games[model] else "—"
        out.append(f"| {model} | {label.get(model, '—')} | {rate} | {x['han']} | {x['ai_block']} | {x['ai_high']} | {x['avoid']} | {x['drift']} |")
    out += ["", "胜率来自盲稿的成对比较（好不好看）；机械指标只说明\"有没有毛病\"，不决定好坏。样本只有一章时，结论只作参考。"]
    (bd / "score.md").write_text("\n".join(out) + "\n", "utf-8")
    print("\n".join(out))


# ---------- 规则改动的闸门 ----------

def anchor_findings(ans: dict, text: str) -> dict:
    """一章锚定章在当前覆盖层下的机械层结果：底蕴与规避点提醒、AI 味必须修与告警。"""
    with tempfile.TemporaryDirectory() as t:
        book = Path(t)
        (book / "book.json").write_text(json.dumps({"era": ans["era"]}), "utf-8")
        cfg = cc.load_config(book)
        warns, _ = cc.knowledge_warnings(book, text)
        warns += cc.avoidance_warnings(text, cfg)
        ai_p, ai_w, detail = cc.ai_findings(book, text, cc.han_count(text), cfg)
    # 用稳定类别和命中数比较，阈值数字变化不能伪装成新增/消失的问题。
    alerts, required = Counter(), Counter()
    for warning in warns:
        if warning.startswith("底蕴：时代错置词"):
            for word, count in re.findall(r"([^：，]+)×(\d+)", warning):
                alerts[f"时代错置词：{word}"] += int(count)
        else:
            m = re.match(r"规避点：(长段|长句) (\d+) 处", warning)
            if m:
                alerts[f"规避点：{m[1]}"] += int(m[2])
            else:
                alerts[warning] += 1
    required.update({f"AI 五星句式：{key}": count for key, count in detail["block"].items()})
    high = {**detail["high_risk"], **detail["level1"]}
    alerts.update({f"AI 高危命中：{key}": count for key, count in high.items()})
    if sum(high.values()) > cfg["ai_level1_max"]:
        required.update({f"AI 必须修：{key}": count for key, count in high.items()})
    alerts.update(w for w in ai_w if not w.startswith("A 级"))
    all_findings = warns + ai_w + ai_p
    miss = [m for m in ans.get("mech", []) if not any(m in w for w in all_findings)]
    return {"miss": miss, "alerts": alerts, "required": required, "problems": ai_p, "warns": warns + ai_w}


def gate_cases():
    for directory, answer in anchors():
        yield answer, (directory / "正文.md").read_text("utf-8")
    # 专用于脚本阈值/词表的样例，不混入模型审稿派单与打分。
    for case in read_json(PLUGIN_ROOT / "eval/mechanical.json", []):
        yield case, case["text"]


def cmd_gate(a):
    rows, worse = [], []
    for ans, text in gate_cases():
        res = {}
        previous = os.environ.get("NCC_OVERLAY")
        try:
            for tag, path in (("base", a.baseline), ("cand", a.candidate)):
                os.environ["NCC_OVERLAY"] = str(Path(path).resolve())
                res[tag] = anchor_findings(ans, text)
        finally:
            if previous is None:
                os.environ.pop("NCC_OVERLAY", None)
            else:
                os.environ["NCC_OVERLAY"] = previous
        b, c = res["base"], res["cand"]
        new_miss = [m for m in c["miss"] if m not in b["miss"]]
        if not ans.get("mech_clean"):
            for key in ("alerts", "required"):
                new_miss += [f"{name}（{count} → {c[key].get(name, 0)}）" for name, count in b[key].items()
                             if c[key].get(name, 0) < count]
        new_noise = [f"{name}（{b[key].get(name, 0)} → {count}）"
                     for key in ("alerts", "required") for name, count in c[key].items()
                     if ans.get("mech_clean") and count > b[key].get(name, 0)]
        if new_miss or new_noise:
            worse.append(ans["id"])
        rows.append(f"{'FAIL' if new_miss or new_noise else 'PASS'} {ans['id']}：必须修 {len(b['problems'])} → {len(c['problems'])}，"
                    f"提醒 {len(b['warns'])} → {len(c['warns'])}"
                    + (f"；新漏报：{'、'.join(new_miss)}" if new_miss else "")
                    + (f"；干净章新误报：{'；'.join(new_noise)}" if new_noise else ""))
    print("\n".join(rows))
    print(f"GATE {'FAIL' if worse else 'PASS'}：" + (f"候选在 {'、'.join(worse)} 上变差" if worse else "候选没有让任何锚定章变差"))
    sys.exit(1 if worse else 0)


ANCHOR_TPL = {
    "正文.md": "# 第一章 待拟标题\n\n（原创复述那段漏检的戏，几百字即可；不摘真书原文。只埋一两处错，埋在审稿真正容易漏的地方。）\n",
    "场景卡.md": "## 场景 1\n- 视角：\n- 目标：\n- 翻转：\n- 两难：\n- 情感：\n",
    "台账.md": "- 时代背景：\n- 视角：\n",
}


def cmd_anchor(a):
    if not re.fullmatch(r"A\d{2}-\S+", a.id):
        die("编号写成 A07-短名（两位数字）")
    d = ANCHORS / a.id
    if d.exists():
        die(f"已存在：{d}")
    d.mkdir(parents=True)
    for name, tpl in ANCHOR_TPL.items():
        (d / name).write_text(tpl, "utf-8")
    ans = {"id": a.id, "suite": a.suite, "era": a.era, "verdict": "pass" if a.clean else "fail", "mech": [], "expected": []}
    if a.clean:
        ans["mech_clean"] = True
    write_json(d / "answers.json", ans)
    print(f"OK 锚定章骨架 eval/anchors/{a.id}/：写正文、场景卡、台账，再把埋的错写进 answers.json 的 expected（格式见 eval/README.md）")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("anchors"); p.add_argument("--suite")
    p.add_argument("--anchors-dir", action="append", dest="anchors_dirs"); p.set_defaults(fn=cmd_anchors)
    p = sub.add_parser("mech"); p.add_argument("--suite")
    p.add_argument("--anchors-dir", action="append", dest="anchors_dirs"); p.set_defaults(fn=cmd_mech)
    p = sub.add_parser("prepare"); p.add_argument("run_dir"); p.add_argument("--suite")
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--anchors-dir", action="append", dest="anchors_dirs")
    p.add_argument("--packets-dir"); p.add_argument("--seed"); p.set_defaults(fn=cmd_prepare)
    p = sub.add_parser("score"); p.add_argument("run_dir")
    p.add_argument("--anchors-dir", action="append", dest="anchors_dirs"); p.set_defaults(fn=cmd_score)
    p = sub.add_parser("gate"); p.add_argument("--baseline", required=True); p.add_argument("--candidate", required=True)
    p.set_defaults(fn=cmd_gate)
    p = sub.add_parser("anchor"); ans_ = p.add_subparsers(dest="action", required=True)
    q = ans_.add_parser("new"); q.add_argument("id"); q.add_argument("--suite", required=True, choices=["底蕴", "连贯", "承诺", "对照"])
    q.add_argument("--era", required=True); q.add_argument("--clean", action="store_true")
    p.set_defaults(fn=cmd_anchor)
    p = sub.add_parser("bench"); bs = p.add_subparsers(dest="action", required=True)
    for act in ("init", "blind", "score"):
        q = bs.add_parser(act); q.add_argument("book_dir"); q.add_argument("seq", type=int)
    q = bs.add_parser("add"); q.add_argument("book_dir"); q.add_argument("seq", type=int)
    q.add_argument("--model", required=True); q.add_argument("--file", required=True)
    q = bs.add_parser("vote"); q.add_argument("book_dir"); q.add_argument("seq", type=int)
    q.add_argument("--winner", required=True); q.add_argument("--loser", required=True); q.add_argument("--tie", action="store_true")
    p.set_defaults(fn=cmd_bench)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
