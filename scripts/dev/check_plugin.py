#!/usr/bin/env python3
"""check_plugin.py：插件自查（七律落到插件本身）。全部通过打印 PLUGIN OK，否则逐条列出并退出 1。

  1. 链接与路径：Markdown 相对链接、反引号里的插件内路径都存在。
  2. 注册表与文件一致：每个角色有 agents/<角色>.md，每条命令有 commands/<命令>.md 与对应 skill。
  3. 写手可读的文件里没有审稿判据（铁律 9）。
  4. 按名称引用（七律五）：不写章节序号（§ 加数字、第几节）；写成 某文件 的"标题" 的引用，标题必须存在。
  5. 版本权威来源为 .zcode-plugin/plugin.json，分发副本按宿主字段校验；标题不写版本号。
  6. 按需可见（七律七）：每个角色每次调用读的规则文件不超过 registry 的 load_budget 上限；
     agents/<角色>.md 里写了全路径要读的规则文件，必须列进该角色的读取清单。
  7. 词表不走样（七律一）：文档里一口气列出某张词表（五个值以上）的几乎全部取值时，必须一个不差；
     注册表增删一个取值，所有手写的完整列举都会被这里拦下。

生成的文档是否与注册表一致，由 build_docs.py --check 查。只依赖标准库。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_ROOT))
from ncclib.registry import RegistryError, load_registry
from dev.development import role_reads

ROOT = SCRIPTS_ROOT.parent
try:
    REG = load_registry(ROOT)
except RegistryError as exc:
    raise SystemExit(str(exc)) from exc
SECTION_NO = re.compile(r"§\s*[0-9〇零一二三四五六七八九十]+|第[〇零一二三四五六七八九十0-9]+节")
NAMED = re.compile(r"`?([\w./-]+\.md)`?\s*(?:的|里)\s*[\"「]([^\"」]+)[\"」]")
SELF_NAMED = re.compile(r"(?:下面的|上面的|文末|见)\s*[\"「]([^\"」]+)[\"」]")
WRITER_READABLE = ("skills/ncc-write/references/chapter-loop.md", "skills/ncc-write/references/writing-brief.md", "agents/writer.md")
REVIEW_WORDS = tuple(REG["review_words"]["values"])


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
        # Frozen reports contain historical paths and commands, not live navigation.
        if p.is_relative_to(ROOT / "docs/evidence"):
            continue
        s = p.read_text(encoding="utf-8")
        for m in re.finditer(r"\]\(([^)#\s]+)(#[^)]*)?\)", s):
            t = m.group(1)
            if not t.startswith(("http", "mailto")) and not (p.parent / t).exists():
                bad.append(f"链接不存在：{rel(p)} -> {t}")
        for m in re.finditer(r"`((?:skills|agents|scripts|workflow|commands|docs)/[^`\s<>*]+?\.(?:md|py|json|yaml))`", s):
            if not (ROOT / m.group(1)).exists():
                bad.append(f"路径不存在：{rel(p)} -> {m.group(1)}")


def owned(path):
    try:
        return path.resolve().is_relative_to(ROOT.resolve())
    except (OSError, RuntimeError):
        return False


def check_skill(skill, bad):
    source = ROOT / 'skills' / skill / 'SKILL.md'
    if not owned(source):
        bad.append('技能源指向仓外：' + str(source.relative_to(ROOT)))
    if not source.is_file():
        bad.append('缺技能入口：' + str(source.relative_to(ROOT)))
    for mount in ('.agents/skills', '.claude/skills'):
        link = ROOT / mount / skill
        if not link.is_symlink():
            bad.append('缺项目级软链：' + str(link.relative_to(ROOT)))
        elif Path(link.readlink()).is_absolute() or not link.exists() or link.resolve() != source.parent.resolve():
            bad.append('项目级软链断裂或目标不符：' + str(link.relative_to(ROOT)))


def check_manifests(root, bad):
    """只读校验已使用的五种清单关系，保留宿主与市场格式差异。"""
    root = Path(root).resolve()
    documents = {}
    paths = ('plugin.json', '.zcode-plugin/plugin.json', '.claude-plugin/plugin.json',
             '.claude-plugin/marketplace.json', '.agents/plugins/marketplace.json')

    def error(path, field, expected, actual):
        bad.append(f'清单不一致：{path} {field} 期望 {expected!r}，实际 {actual!r}')

    for path in paths:
        try:
            data = json.loads((root / path).read_text(encoding='utf-8'))
            if not isinstance(data, dict):
                raise ValueError('根必须为对象')
            documents[path] = data
        except (OSError, ValueError) as exc:
            bad.append(f'清单无法读取：{path}：{exc}')
    authority = '.zcode-plugin/plugin.json'
    reference = documents.get(authority, {})
    for field in ('name', 'version'):
        if not isinstance(reference.get(field), str) or not reference[field].strip():
            error(authority, field, '非空字符串', reference.get(field))

    def location(path, field, value, expected):
        try:
            if not isinstance(value, str) or not value or Path(value).is_absolute():
                raise ValueError('必须为本地相对路径')
            actual = (root / value).resolve()
            if actual != expected or not actual.is_dir():
                raise ValueError(f'必须解析到 {expected}')
        except (OSError, ValueError, RuntimeError) as exc:
            error(path, field, str(expected), f'{value!r} ({exc})')

    for field in ('skills', 'commands', 'agents'):
        location(authority, field, reference.get(field), root / field)
    for path in ('plugin.json', '.claude-plugin/plugin.json'):
        if path in documents:
            for field in ('name', 'version'):
                if documents[path].get(field) != reference.get(field):
                    error(path, field, reference.get(field), documents[path].get(field))
    for path in ('.claude-plugin/marketplace.json', '.agents/plugins/marketplace.json'):
        if path not in documents:
            continue
        plugins = documents[path].get('plugins')
        if not isinstance(plugins, list) or not all(isinstance(p, dict) for p in plugins):
            error(path, 'plugins', '对象数组', plugins)
            continue
        matches = [p for p in plugins if p.get('name') == reference.get('name')]
        if len(matches) != 1:
            error(path, 'plugins[name=插件名]', '恰好一项', len(matches))
            continue
        plugin = matches[0]
        if path.startswith('.claude'):
            if plugin.get('version') != reference.get('version'):
                error(path, 'plugins[name=插件名].version', reference.get('version'), plugin.get('version'))
            location(path, 'plugins[name=插件名].source', plugin.get('source'), root)
        else:
            source = plugin.get('source')
            if not isinstance(source, dict):
                error(path, 'plugins[name=插件名].source', 'local 对象', source)
                continue
            if source.get('source') != 'local':
                error(path, 'plugins[name=插件名].source.source', 'local', source.get('source'))
            location(path, 'plugins[name=插件名].source.path', source.get('path'), root)


def check_registry(bad):
    development = REG.get('development', {})
    engineering = development.get('roles', {})
    professional_skills = set()
    if set(engineering) & set(REG['roles']):
        bad.append('工程角色不得混入创作角色域')
    for role in set(REG["roles"]) | set(engineering):
        if not (ROOT / "agents" / f"{role}.md").is_file():
            bad.append(f"缺 agents/{role}.md")
    extra = {p.stem for p in (ROOT / "agents").glob("*.md")} - set(REG["roles"]) - set(engineering)
    if extra:
        bad.append(f"agents 里有注册表没有的角色：{sorted(extra)}")
    for role, definition in engineering.items():
        try:
            resources = role_reads(definition)
        except ValueError as exc:
            bad.append('工程角色专业技能：' + role + ': ' + str(exc))
            continue
        skill = definition['skill']
        if skill in professional_skills or skill in {c['skill'] for c in REG['commands'].values()}:
            bad.append('工程专业技能必须独立归属：' + skill)
        professional_skills.add(skill)
        for name in resources:
            if not (ROOT / name).is_file() or not owned(ROOT / name):
                bad.append('工程技能资料缺失或越界：' + role + ': ' + name)
        if not definition.get('outputs') or not definition.get('effects') or not definition.get('reads'):
            bad.append('工程角色缺少触发/交付/读取定义：' + role)
        if not {'agents/' + role + '.md', 'skills/ncc-dev/references/roles.md'} <= set(definition.get('reads', [])):
            bad.append('工程角色未读取本角色或共用执行协议：' + role)
        if set(definition.get('effects', [])) - set(development.get('effects', {})):
            bad.append('工程角色含未知影响类型：' + role)
        for mount in ('.claude/agents', '.agents/agents', '.grok/agents'):
            link = ROOT / mount / (role + '.md')
            source = ROOT / 'agents' / (role + '.md')
            if not link.is_symlink() or Path(link.readlink()).is_absolute() or not link.exists() or link.resolve() != source.resolve():
                bad.append('工程角色项目级挂载错误：' + str(link.relative_to(ROOT)))
    for c, v in REG["commands"].items():
        if not owned(ROOT / "commands" / f"{c}.md"):
            bad.append(f"命令源指向仓外：commands/{c}.md")
        if not owned(ROOT / "skills" / v["skill"] / "SKILL.md"):
            bad.append(f"技能源指向仓外：skills/{v['skill']}/SKILL.md")
        if not (ROOT / "commands" / f"{c}.md").is_file():
            bad.append(f"缺 commands/{c}.md")
        if not (ROOT / "skills" / v["skill"] / "SKILL.md").is_file():
            bad.append(f"缺 skills/{v['skill']}/SKILL.md")
    registered_skills = {v["skill"] for v in REG["commands"].values()} | professional_skills
    extra_commands = {p.stem for p in (ROOT / "commands").glob("*.md")} - set(REG["commands"])
    extra_skills = {p.name for p in (ROOT / "skills").iterdir() if p.is_dir()} - registered_skills
    if extra_commands:
        bad.append(f"commands 里有未登记入口：{sorted(extra_commands)}")
    if extra_skills:
        bad.append(f"skills 里有未登记入口：{sorted(extra_skills)}")
    for skill in sorted(registered_skills):
        check_skill(skill, bad)
    for command in REG["commands"]:
        for mount, name, source in ((".claude/commands", command + ".md", ROOT / "commands" / (command + ".md")),):
            link = ROOT / mount / name
            if not link.is_symlink():
                bad.append(f"缺项目级软链：{mount}/{name}")
                continue
            try:
                if Path(link.readlink()).is_absolute() or not link.exists() or link.resolve() != source.resolve():
                    bad.append(f"项目级软链断裂或目标不符：{mount}/{name}")
            except (OSError, RuntimeError):
                bad.append(f"项目级软链无法解析：{mount}/{name}")
    if "ncc-dev" in REG["commands"]:
        flow = ROOT / "docs/engineering/workflow.md"
        if not flow.is_file() or not owned(flow):
            bad.append("开发入口无法定位仓内 docs/engineering/workflow.md")
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


def check_vocab_copies(md, bad):
    gen = re.compile(r"<!-- ncc:gen (\S+) 开始.*?<!-- ncc:gen \1 结束 -->", re.S)
    texts = {p: gen.sub("", p.read_text(encoding="utf-8")) for p in md if p.name != "book-layout.md"}
    for k, v in REG["vocab"].items():
        vals = list(v["values"])
        if len(vals) < 5:
            continue
        alt = "|".join(sorted(map(re.escape, vals), key=len, reverse=True))
        run = re.compile(rf"(?:{alt})(?:\s*[、／|,，/]\s*(?:{alt}))+")
        for p, s in texts.items():
            for i, line in enumerate(s.splitlines(), 1):
                for m in run.finditer(line):
                    got = set(re.findall(alt, m.group(0)))
                    if len(vals) - 1 <= len(got) < len(vals):
                        bad.append(f"词表 {k} 的列举少了 {'、'.join(sorted(set(vals) - got))}：{rel(p)}:{i}")


def check_budget(bad, report):
    lb = REG["load_budget"]
    cards = sorted((nws(p) for p in (ROOT / "skills/ncc/references/domains").glob("A*.md")), reverse=True)
    engineering_reads = {}
    for name, definition in REG.get('development', {}).get('roles', {}).items():
        try:
            engineering_reads[name] = role_reads(definition)
        except ValueError as exc:
            bad.append('工程技能读取契约：' + name + ': ' + str(exc))
    reads_by_role = {**lb['reads'], **engineering_reads}
    for role, reads in reads_by_role.items():
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
        if role in REG["roles"] or role in REG.get('development', {}).get('roles', {}):
            s = (ROOT / "agents" / f"{role}.md").read_text(encoding="utf-8")
            for m in re.finditer(r"`((?:skills|workflow)/[^`\s]+?\.md)`", s):
                if m.group(1) not in reads:
                    bad.append(f"agents/{role}.md 要读 {m.group(1)}，但它不在 load_budget 的读取清单里")


def main():
    files = [p for p in tracked() if p.suffix in (".md", ".py", ".json", ".yaml")]
    md = [p for p in files if p.suffix == ".md"]
    bad, report = [], []
    check_manifests(ROOT, bad)
    check_links(md, bad)
    check_registry(bad)
    check_references(files, md, bad)
    check_versions(files, bad)
    check_vocab_copies(md, bad)
    check_budget(bad, report)
    if "-v" in sys.argv[1:]:
        for role, total, cap in report:
            print(f"{role:16s} {total:6d} / {cap}")
    print("\n".join(bad) or "PLUGIN OK")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
