#!/usr/bin/env python3
"""build_docs.py：插件文档里由 workflow/registry.json 生成的部分（七律二：副本只能生成）。

  python3 scripts/build_docs.py          重新生成
  python3 scripts/build_docs.py --check  只比对，有出入就列出来并退出 1（自测会跑）

生成什么：
  skills/ncc/references/book-state.md   信息地图、视图清单
  skills/ncc/references/book-layout.md  整份：目录契约、词表
  skills/ncc/references/stage-map.md    阶段表、每批场景卡章数、角色分工
  skills/ncc/SKILL.md                   铁律
  skills/ncc/references/memory.md       记忆门槛与上限、各角色记什么、交接卡切给谁
  skills/ncc/references/loops.md        进化的四档与能提议的键
  skills/ncc-new/references/worldbuilding.md   设定类目表
  skills/ncc-deconstruct/SKILL.md       技法卡：谁拿哪些类别、状态与版权口径
  agents/*.md、commands/*.md            frontmatter 的 description、color、argument-hint
  README.md                             版本行（版本只在 .zcode-plugin/plugin.json 写一份）

文档里的生成区块用 <!-- ncc:gen 名字 开始 … --> 与 <!-- ncc:gen 名字 结束 --> 包住；区块外是手写的说明，原样保留。
只依赖标准库。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REG = json.loads((ROOT / "workflow" / "registry.json").read_text(encoding="utf-8"))
VERSION = json.loads((ROOT / ".zcode-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
LAYOUT = REG["layout"]


def begin(name):
    return f"<!-- ncc:gen {name} 开始（scripts/build_docs.py 由 workflow/registry.json 生成，勿手改） -->"


def end(name):
    return f"<!-- ncc:gen {name} 结束 -->"


def fill(text, name, body, where):
    pat = re.compile(re.escape(begin(name)) + r".*?" + re.escape(end(name)), re.S)
    if not pat.search(text):
        raise SystemExit(f"{where} 缺生成区块标记：{name}")
    return pat.sub(lambda _: f"{begin(name)}\n{body.rstrip()}\n{end(name)}", text)


def shown(e):
    """布局条目在文档里的写法：书库根目录下的加 {书库}/ 前缀。"""
    path = e["path"] + ("/" if e.get("dir") else "")
    return f"{{书库}}/{path}" if e.get("scope") == "root" else path


def info_map():
    rows = ["| 信息 | 类别 | 唯一源头 | 谁写、怎么写 | 在哪看 |", "|---|---|---|---|---|"]
    for e in LAYOUT.values():
        if e["kind"] not in ("源头", "历史", "作者", "工作件") or e["writer"] == "—":
            continue
        if e["kind"] == "工作件" and e["path"] != REG["layout"]["work"]["path"]:
            continue
        rows.append(f"| {e['what']} | {e['kind']} | `{shown(e)}` | {e['writer']} | {e.get('view', '—')} |")
        for f in e.get("fields", []):
            rows.append(f"| {f['what']} | {e['kind']} | `{shown(e)}` 的 `{f['field']}` | {f['writer']} | {f['view']} |")
    return "\n".join(rows)


def views():
    out = []
    for e in LAYOUT.values():
        if e["kind"] == "视图":
            out.append(f"- `{e['path']}`：{e['what']}（{e['writer']}）")
    return "\n".join(out)


def tree(scope, top):
    nodes = {}
    for e in LAYOUT.values():
        if e.get("scope", "book") != scope:
            continue
        cur = nodes
        parts = e["path"].split("/")
        for part in parts[:-1]:
            cur = cur.setdefault(part, {"_e": None, "_kids": {}})["_kids"]
        node = cur.setdefault(parts[-1], {"_e": None, "_kids": {}})
        node["_e"] = e
    lines = [top]

    def walk(level, depth):
        for name, node in level.items():
            e = node["_e"]
            isdir = bool(node["_kids"]) or (e and e.get("dir"))
            label = "  " * depth + name + ("/" if isdir else "")
            if e:
                desc = f"[{e['kind']}] {e['what']}" + (f"｜{e['writer']}" if e["writer"] != "—" else "")
                if e.get("eg"):
                    desc += f"｜如 {e['eg']}"
                label += "    # " + desc
            lines.append(label)
            walk(node["_kids"], depth + 1)

    walk(nodes, 1)
    return lines


def layout():
    return "\n".join(["```"] + tree("book", "{book_root}/{书名}/") + [""] + tree("root", "{book_root}/") + ["```"])


def values(v):
    if isinstance(v, list):
        return "、".join(v)
    parts = []
    for k, x in v.items():
        if isinstance(x, list):
            parts.append(f"{k}：{'、'.join(x)}")
        elif isinstance(x, int):
            parts.append(f"{k} {x}")
        else:
            parts.append(f"{k}→{x}")
    return "；".join(parts) if any(isinstance(x, list) for x in v.values()) else "、".join(parts)


def vocab():
    rows = ["| 词表 | 取值 | 用在哪 |", "|---|---|---|"]
    for k, v in REG["vocab"].items():
        rows.append(f"| {v['label']}（`{k}`） | {values(v['values'])} | {v['used_by']} |")
    rows.append(f"| 写作模式（`writing_modes`） | {'、'.join(REG['writing_modes'])} | init --mode、mode |")
    return "\n".join(rows)


def book_layout():
    return "\n".join([
        "# 书项目的目录契约与词表",
        "",
        "<!-- 整份由 scripts/build_docs.py 从 workflow/registry.json 的 layout 与 vocab 生成，勿手改；要改就改注册表再运行 build_docs.py。 -->",
        "",
        "信息的源头、写者与视图见 [book-state.md](book-state.md) 的\"信息地图\"。",
        "",
        "## 目录契约",
        "",
        "每一项标了类别：源头（权威数据，只经脚本或指定写者）、历史（只追加）、视图（生成，勿手改）、作者（作者本人的材料）、"
        "角色（角色产出的文档）、工作件（机器写）。",
        "",
        layout(),
        "",
        "## 词表",
        "",
        "脚本认的取值都在这里；别的文档要列取值，就引用\"词表\"，不再抄一份。",
        "",
        vocab(),
        "",
    ])


def stages():
    rows = ["| 阶段 | 层 | 主责角色 | 参与角色 | 产物 | 闸门 |", "|---|---|---|---|---|---|"]
    for s in REG["stage_table"]:
        rows.append(f"| {s['stage']} | {s['layer']} | {s['lead']} | {s['support']} | {s['products']} | {s['gate']} |")
    return "\n".join(rows)


def batch():
    b = REG["vocab"]["scene_batch"]["values"]
    return "每批场景卡的章数：" + "、".join(f"{m} {n} 章" for m, n in b.items()) + "。"


def roles():
    rows = ["| 角色 | 一句话职责 | 绝不做 |", "|---|---|---|"]
    for name, r in REG["roles"].items():
        rows.append(f"| {name} | {r['duty']} | {r['never']} |")
    fresh = [n for n, r in REG["roles"].items() if r.get("fresh")]
    rows += ["", f"fresh 标记：{'、'.join(fresh)} 为无记忆新上下文——派单包不含生产材料。"]
    return "\n".join(rows)


def iron_rules():
    return "\n".join(f"{i}. {r}" for i, r in enumerate(REG["iron_rules"], 1))


def memory_rules():
    m, c = REG["memory"], REG["memory"]["caps"]
    once = "、".join(m["once_ok"])
    return "\n".join([
        f"- 门槛：同类独立证据至少 {m['min_evidence']} 处才生效（重复提交不计数），不到的先记为候选；{once}一处即可（作者原话就是证据）。",
        f"- 相近：正文完全相同才自动合并证据；字面重合度 ≥ {m['similar']} 的不同正文独立保存并提示候选，经理确认同义后才 merge，纠正意见用 edit 或 archive。",
        f"- 上限：本书记忆每个角色 {c['book_chars']} 字、{c['book_items']} 条；跨书记忆每个角色 {c['shared_chars']} 字。放不下的整条跳过并报告省略数，不截断句意。",
        f"- 久未出现：连续 {m['stale_units']} 个单元没再出现的（{once}除外），关单元时自动归档，memory restore 可撤回。",
        f"- 晋升：有 ≥ {m['promote_hits']} 处独立证据且已生效、不是{once}的，够格进跨书记忆；完本时默认晋升，作者可以划掉。",
    ])


def memory_roles():
    rows = ["| 角色 | 记哪些种类 | 记什么 | 不记什么 |", "|---|---|---|---|"]
    for r, v in REG["memory"]["roles"].items():
        rows.append(f"| {r} | {'、'.join(v['kinds'])} | {v['keeps']} | {v['never']} |")
    return "\n".join(rows)


def handoff_visibility():
    h = REG["handoff"]
    rows = ["| 角色 | 拿哪些种类 | 作用层 | 只拿覆盖本章的 |", "|---|---|---|---|"]
    for r, v in h["visibility"].items():
        if v is None:
            rows.append(f"| {r} | 不拿 | — | — |")
            continue
        kinds = "全部" if v["kinds"] == "*" else "、".join(v["kinds"])
        layers = "全部" if v["layers"] == "*" else "、".join(v["layers"])
        rows.append(f"| {r} | {kinds} | {layers} | {'是' if v.get('chapter') else '—'} |")
    rows += ["", h["why_none"], "", f"写手包里\"作者刚说的\"最多 {h['writer_chars']} 字，派单头里最多 {h['brief_chars']} 字，新的在前。"]
    return "\n".join(rows)


def setting_catalog():
    sc = REG["setting_categories"]
    rows = ["| 类目 | 别名 | 常见题材 | 必填字段 |", "|---|---|---|---|"]
    for name, v in sc["catalog"].items():
        rows.append(f"| {name} | {'、'.join(v['alias'])} | {'、'.join(v['genres'])} | {'、'.join(v['required'])} |")
    rows += ["", f"每个类目都要有：{'、'.join(sc['common'])}（本书新提的类目由脚本补上）。"]
    return "\n".join(rows)


def technique_roles():
    t = REG["techniques"]
    rows = ["| 角色 | 拿哪些类别 | 最多几张 | 最多几字 |", "|---|---|---|---|"]
    for r, v in t["per_role"].items():
        rows.append(f"| {r} | {'、'.join(v['kinds'])}{'（只拿场景卡引用了的）' if v.get('only_referenced') else ''} | {v['max']} | {v['chars']} |")
    rows.append(f"| {'、'.join(t['never'])} | 不拿 | — | — |")
    rows += ["", f"{t['why_never']}写手拿到的由脚本转成\"写成什么\"，不带证据、出处与代价。同一本对标书每次最多 {t['per_source_max']} 张。", "",
             f"状态：一处证据是样本，同一本书 {t['method_evidence']} 处以上是手法；用过且结果好是已验证；连续 {t['retire_after_bad']} 次结果差自动停用"
             f"（technique restore 可恢复）；{t['general_books']} 本书以上都有的标\"通用\"。定位词 {t['locator'][0]}–{t['locator'][1]} 字；"
             f"卡片正文和原文连续重合超过 {t['overlap_max']} 字就拒绝写入。"]
    return "\n".join(rows)


def evolution():
    e = REG["evolution"]
    rows = ["| 档 | 改什么 | 怎么生效 |", "|---|---|---|"] + [f"| {t['tier']} | {t['what']} | {t['how']} |" for t in e["tiers"]]
    rows += ["", "能提议的键：", ""]
    rows += [f"- `{k}`（{v['tier']}）：{v['what']}" + (f"；插件默认 {v['default']}" if "default" in v else "") for k, v in e["keys"].items()]
    rows += ["", f"永不自动：{'、'.join(e['never'])}。"]
    return "\n".join(rows)


def frontmatter(text, key, value, where):
    pat = re.compile(rf"^{re.escape(key)}: .*$", re.M)
    head, sep, rest = text.partition("\n---\n")
    if not pat.search(head):
        raise SystemExit(f"{where} 的 frontmatter 缺 {key}")
    return pat.sub(lambda _: f"{key}: {value}", head, count=1) + sep + rest


def q(s):
    return json.dumps(s, ensure_ascii=False)


def targets():
    """(相对路径, 由旧文本算出新文本的函数)。"""
    yield "skills/ncc/references/book-state.md", lambda t, w: fill(fill(t, "info-map", info_map(), w), "views", views(), w)
    yield "skills/ncc/references/book-layout.md", lambda t, w: book_layout()
    yield "skills/ncc/references/stage-map.md", lambda t, w: fill(fill(fill(
        t, "stages", stages(), w), "batch", batch(), w), "roles", roles(), w)
    yield "skills/ncc/SKILL.md", lambda t, w: fill(t, "iron-rules", iron_rules(), w)
    yield "skills/ncc/references/memory.md", lambda t, w: fill(fill(fill(
        t, "memory-rules", memory_rules(), w), "memory-roles", memory_roles(), w), "handoff-visibility", handoff_visibility(), w)
    yield "skills/ncc/references/loops.md", lambda t, w: fill(t, "evolution", evolution(), w)
    yield "skills/ncc-new/references/worldbuilding.md", lambda t, w: fill(t, "setting-catalog", setting_catalog(), w)
    yield "skills/ncc-deconstruct/SKILL.md", lambda t, w: fill(t, "technique-roles", technique_roles(), w)
    for name, r in REG["roles"].items():
        yield f"agents/{name}.md", lambda t, w, r=r: frontmatter(frontmatter(t, "description", q(r["description"]), w), "color", r["color"], w)
    for name, c in REG["commands"].items():
        def cmd(t, w, c=c):
            t = frontmatter(t, "description", q(c["description"]), w)
            return frontmatter(t, "argument-hint", q(c["argument_hint"]), w) if c.get("argument_hint") else t
        yield f"commands/{name}.md", cmd

    def readme(t, w):
        new, n = re.subn(r"^(ZCode 插件 · )v[\w.\-]+( · )", rf"\g<1>v{VERSION}\g<2>", t, count=1, flags=re.M)
        if not n:
            raise SystemExit(f"{w} 缺版本行（ZCode 插件 · vX.Y.Z · …）")
        return new
    yield "README.md", readme


def main():
    check = "--check" in sys.argv[1:]
    stale = []
    for rel, build in targets():
        p = ROOT / rel
        old = p.read_text(encoding="utf-8") if p.exists() else ""
        new = build(old, rel)
        if new != old:
            stale.append(rel)
            if not check:
                p.write_text(new, encoding="utf-8")
    if check:
        if stale:
            print("与 registry 不一致（运行 python3 scripts/build_docs.py 重新生成）：\n  " + "\n  ".join(stale))
            sys.exit(1)
        print("DOCS OK")
    else:
        print("\n".join(f"已更新 {r}" for r in stale) or "无改动")


if __name__ == "__main__":
    main()
