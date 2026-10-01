#!/usr/bin/env python3
"""check_plugin.py：插件自查（七律落到插件本身）。全部通过打印 PLUGIN OK，否则逐条列出并退出 1。

  1. 链接与路径：Markdown 相对链接、反引号里的插件内路径都存在。
  2. 注册表与文件一致：每个角色有 agents/<角色>.md，每条命令有 commands/<命令>.md 与对应 skill。
  3. 写手可读的文件里没有审稿判据（铁律 9）。
  4. 按名称引用（七律五）：不写章节序号（§ 加数字、第几节）；写成 某文件 的"标题" 的引用，标题必须存在。
  5. 版本只在 .zcode-plugin/plugin.json：文档标题行与脚本说明首行不写版本号。
  6. 按需可见（七律七）：每个角色每次调用读的规则文件不超过 registry 的 load_budget 上限；
     agents/<角色>.md 里写了全路径要读的规则文件，必须列进该角色的读取清单。

生成的文档是否与注册表一致，由 build_docs.py --check 查。只依赖标准库。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REG = json.loads((ROOT / "workflow" / "registry.json").read_text(encoding="utf-8"))
SECTION_NO = re.compile(r"§\s*[0-9〇零一二三四五六七八九十]+|第[〇零一二三四五六七八九十0-9]+节")
NAMED = re.compile(r"`?([\w./-]+\.md)`?\s*(?:的|里)\s*[\"「]([^\"」]+)[\"」]")
SELF_NAMED = re.compile(r"(?:下面的|上面的|文末|见)\s*[\"「]([^\"」]+)[\"」]")
WRITER_READABLE = ("skills/ncc-write/references/chapter-loop.md", "skills/ncc-write/references/writing-brief.md", "agents/writer.md")
REVIEW_WORDS = ("可判定率", "critical", "典型硬伤", "诊断问句", "para_max")


def tracked():
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT,
                         capture_output=True, text=True).stdout.split()
    files = [ROOT / f for f in out if (ROOT / f).is_file()]
    return files or [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts]


def rel(p):
    return p.relative_to(ROOT).as_posix()


def nws(p):
    return len(re.sub(r"\s", "", p.read_text(encoding="utf-8")))


def anchors(p):
    """一个文档里能被按名称引用的地方：标题与加粗的小标题。"""
    s = p.read_text(encoding="utf-8")
    return [h.strip() for h in re.findall(r"^#+\s*(.+)$", s, re.M)] + re.findall(r"\*\*([^*]+)\*\*", s)


def resolve(name, here, md):
    for cand in (here.parent / name, ROOT / name):
        if cand.is_file():
            return cand
    base = [p for p in md if p.name == Path(name).name]
    return base[0] if len(base) == 1 else None


def check_links(md, bad):
    for p in md:
        s = p.read_text(encoding="utf-8")
        for m in re.finditer(r"\]\(([^)#\s]+)(#[^)]*)?\)", s):
            t = m.group(1)
            if not t.startswith(("http", "mailto")) and not (p.parent / t).exists():
                bad.append(f"链接不存在：{rel(p)} -> {t}")
        for m in re.finditer(r"`((?:skills|agents|scripts|workflow|commands|docs)/[^`\s<>*]+?\.(?:md|py|json|yaml))`", s):
            if not (ROOT / m.group(1)).exists():
                bad.append(f"路径不存在：{rel(p)} -> {m.group(1)}")


def check_registry(bad):
    for role in REG["roles"]:
        if not (ROOT / "agents" / f"{role}.md").is_file():
            bad.append(f"缺 agents/{role}.md")
    extra = {p.stem for p in (ROOT / "agents").glob("*.md")} - set(REG["roles"])
    if extra:
        bad.append(f"agents 里有注册表没有的角色：{sorted(extra)}")
    for c, v in REG["commands"].items():
        if not (ROOT / "commands" / f"{c}.md").is_file():
            bad.append(f"缺 commands/{c}.md")
        if not (ROOT / "skills" / v["skill"] / "SKILL.md").is_file():
            bad.append(f"缺 skills/{v['skill']}/SKILL.md")
    for f in WRITER_READABLE:
        s = (ROOT / f).read_text(encoding="utf-8")
        for w in REVIEW_WORDS:
            if w in s:
                bad.append(f"写手可读的 {f} 含审稿判据词：{w}")


def check_references(files, md, bad):
    for p in files:
        if p.suffix not in (".md", ".py", ".json", ".yaml"):
            continue
        s = p.read_text(encoding="utf-8")
        for i, line in enumerate(s.splitlines(), 1):
            if SECTION_NO.search(line):
                bad.append(f"章节序号引用（改成按标题名称）：{rel(p)}:{i}")
            for m in NAMED.finditer(line):
                target = resolve(m.group(1), p, md)
                if target and not any(m.group(2) in a for a in anchors(target)):
                    bad.append(f"引用的标题不存在：{rel(p)}:{i} -> {m.group(1)} 的\"{m.group(2)}\"")
            if p.suffix == ".md":
                for m in SELF_NAMED.finditer(line):
                    if NAMED.search(line[max(0, m.start() - 60):m.end()]):
                        continue
                    if m.group(1) in ("词表", "信息地图", "目录契约") or any(m.group(1) in a for a in anchors(p)):
                        continue
                    bad.append(f"引用的标题不存在：{rel(p)}:{i} -> \"{m.group(1)}\"")


def check_versions(files, bad):
    for p in files:
        s = p.read_text(encoding="utf-8")
        if p.suffix == ".md":
            title = next((l for l in s.splitlines() if l.startswith("# ")), "")
        elif p.suffix == ".py":
            m = re.search(r'"""(.*)', s)
            title = m.group(1) if m else ""
        else:
            continue
        if re.search(r"\bv\d+\.\d+", title):
            bad.append(f"标题行写了版本号（版本只在 plugin.json）：{rel(p)}：{title.strip()}")


def check_budget(bad, report):
    lb = REG["load_budget"]
    cards = sorted((nws(p) for p in (ROOT / "skills/ncc/references/domains").glob("A*.md")), reverse=True)
    for role, reads in lb["reads"].items():
        total = 0
        for f in reads:
            if f.startswith("domains:"):
                total += sum(cards[:int(f.split(":")[1])])
            elif not (ROOT / f).is_file():
                bad.append(f"读取清单里的文件不存在：{role} -> {f}")
            else:
                total += nws(ROOT / f)
        cap = lb["ceilings"]["manager" if role.startswith("manager") else "subagent"]
        report.append((role, total, cap))
        if total > cap:
            bad.append(f"读取量超上限：{role} {total} > {cap}")
        if role in REG["roles"]:
            s = (ROOT / "agents" / f"{role}.md").read_text(encoding="utf-8")
            for m in re.finditer(r"`((?:skills|workflow)/[^`\s]+?\.md)`", s):
                if m.group(1) not in reads:
                    bad.append(f"agents/{role}.md 要读 {m.group(1)}，但它不在 load_budget 的读取清单里")


def main():
    files = [p for p in tracked() if p.suffix in (".md", ".py", ".json", ".yaml")]
    md = [p for p in files if p.suffix == ".md"]
    bad, report = [], []
    check_links(md, bad)
    check_registry(bad)
    check_references(files, md, bad)
    check_versions(files, bad)
    check_budget(bad, report)
    if "-v" in sys.argv[1:]:
        for role, total, cap in report:
            print(f"{role:16s} {total:6d} / {cap}")
    print("\n".join(bad) or "PLUGIN OK")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
