#!/usr/bin/env python3
"""核查开发任务结构、候选指纹与证据；不判断设计质量，不执行发布。"""
import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath

BLOCK = re.compile(r'^```ncc-dev-json\s*\n(.*?)\n```[ \t]*$', re.M | re.S)
PRIVATE = {'novels', 'books', '_作者', '_拆书库', 'book.json', 'prepare.json',
           '02-大纲', '03-文风', '04-正文', '05-台账', '06-复盘', '07-导出'}
STATUSES = ('passed', 'failed', 'blocked', 'pending')


class Invalid(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise Invalid(message)


def git_raw(root, *args):
    proc = subprocess.run(['git', '-C', str(root), *args], capture_output=True)
    require(proc.returncode == 0, f'Git 核查失败：{args[0]} {proc.stderr.decode(errors="replace").strip()}')
    return proc.stdout


def git(root, *args):
    return git_raw(root, *args).decode('utf-8')


def names(output):
    return {p for p in output.split('\0') if p}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_path(root, name, *, ignored=False):
    require(isinstance(name, str) and bool(name), '路径必须为非空字符串')
    p = PurePosixPath(name)
    require(not p.is_absolute() and p.as_posix() == name and
            not any(x in ('..', '.', '.git') for x in p.parts), f'越界或非规范路径：{name}')
    require(not (set(p.parts) & PRIVATE), f'私有路径禁止读取：{name}')
    target = root / name
    try:
        resolved = target.resolve()
    except (OSError, RuntimeError) as exc:
        raise Invalid(f'软链解析失败：{name}') from exc
    require(resolved.is_relative_to(root), f'软链越界：{name}')
    require(not (set(resolved.relative_to(root).parts) & (PRIVATE | {'.git'})), f'软链指向私有或 Git 路径：{name}')
    if not ignored:
        proc = subprocess.run(['git', '-C', str(root), 'check-ignore', '--no-index', '-q', '--', name])
        require(proc.returncode in (0, 1), f'忽略规则核查失败：{name}')
        require(proc.returncode == 1, f'忽略路径禁止纳入：{name}')
        if resolved != target:
            source = resolved.relative_to(root).as_posix()
            proc = subprocess.run(['git', '-C', str(root), 'check-ignore', '--no-index', '-q', '--', source])
            require(proc.returncode == 1, f'软链指向忽略路径：{name}')
    return target


def read_task(root, task):
    root = Path(root).resolve()
    actual = Path(git(root, 'rev-parse', '--show-toplevel').strip()).resolve()
    require(root == actual, '--repo 必须是活动工作树根')
    task_input = Path(task).absolute()
    require(not task_input.is_symlink(), '任务记录不可为软链')
    task = task_input.parent.resolve() / task_input.name
    require(task.is_relative_to(root), '任务记录不属于活动工作树')
    rel = task.relative_to(root).as_posix()
    safe_path(root, rel)
    require(rel.startswith('docs/tasks/') and task.suffix == '.md', '任务记录须位于 docs/tasks/ 且为 Markdown')
    require(task.is_file() and not task.is_symlink(), '任务记录不存在或为软链')
    text = task.read_text(encoding='utf-8')
    blocks = list(BLOCK.finditer(text))
    require(len(blocks) == 1, '任务须有且仅有一个 ncc-dev-json 块')
    try:
        data = json.loads(blocks[0].group(1))
    except json.JSONDecodeError as exc:
        raise Invalid(f'任务 JSON 无效：{exc}') from exc
    require(isinstance(data, dict), '任务 JSON 须为对象')
    validate(root, rel, data)
    return root, task, text, blocks[0], data


def validate(root, task_rel, d):
    require(type(d.get('schema')) is int and d['schema'] == 1, '不支持的证据 schema')
    for key in ('id', 'goal', 'repo_root', 'plugin_root', 'branch', 'base_commit', 'stage', 'next'):
        require(isinstance(d.get(key), str) and bool(d[key]), f'缺字段：{key}')
    require(d.get('route') in ('spike', 'bounded', 'architectural'), '无效任务路径')
    require(d['stage'] in {f'D{i}' for i in range(8)}, '无效阶段')
    require(Path(d['repo_root']).is_absolute() and Path(d['repo_root']).resolve() == root, 'repo_root 与活动工作树不符')
    require(Path(d['plugin_root']).is_absolute() and (Path(d['plugin_root']) / 'skills/ncc-dev/SKILL.md').is_file(), 'plugin_root 不可定位 ncc-dev')
    require(git(root, 'branch', '--show-current').strip() == d['branch'], '分支变化：先核对任务')
    require(re.fullmatch(r'[0-9a-f]{40}', d['base_commit']) is not None, 'base_commit 必须为冻结的完整 SHA')
    git(root, 'cat-file', '-e', d['base_commit'] + '^{commit}')
    require(subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor', d['base_commit'], 'HEAD'], capture_output=True).returncode == 0, '基线不属于当前历史，需重新定位')
    require(isinstance(d.get('blocked'), str), '缺 blocked（未受阻用空字符串）')
    require(isinstance(d.get('risk_tags'), list) and all(isinstance(x, str) for x in d['risk_tags']), '缺 risk_tags 数组')
    require(isinstance(d.get('decisions'), list) and bool(d['decisions']), '缺决定来源')
    for decision in d['decisions']:
        require(isinstance(decision, dict) and all(isinstance(decision.get(k), str) and decision[k] for k in ('source', 'scope')), '决定须有 source/scope')
    for key in ('scope', 'evidence_paths', 'required', 'evidence'):
        require(isinstance(d.get(key), list), f'缺数组：{key}')
    require(isinstance(d.get('candidate'), dict), '缺 candidate 对象')
    require(isinstance(d.get('foreign_changes'), dict), '缺 foreign_changes 对象')
    require(isinstance(d.get('delivery'), dict), '缺 delivery 对象')
    for k in ('local', 'commit', 'remote', 'clone', 'runtime'):
        require(isinstance(d['delivery'].get(k), str) and bool(d['delivery'][k]), f'缺 delivery.{k}')
    for key in ('scope', 'evidence_paths', 'required'):
        require(all(isinstance(x, str) and x for x in d[key]), f'{key} 须为字符串数组')
        require(len(d[key]) == len(set(d[key])), f'{key} 有重复项')
    metadata = set(d['evidence_paths']) | {task_rel}
    require(not (set(d['scope']) & (metadata | set(d['foreign_changes']))), '产品、证据与他人变更归属重叠')
    for name in d['scope'] + list(d['foreign_changes']) + list(metadata):
        safe_path(root, name)
    for name, reason in d['foreign_changes'].items():
        require(isinstance(reason, str) and bool(reason.strip()), f'缺变更归属理由：{name}')
        require(name not in metadata, f'证据/他人变更归属重叠：{name}')
    for name in metadata:
        require(name == task_rel or name.startswith('docs/evidence/'), f'只能排除本任务记录与证据日志：{name}')
        require(not (root / name).is_symlink(), f'证据元数据不可为软链：{name}')
    if d['route'] == 'architectural':
        for key in ('spec', 'plan'):
            require(isinstance(d.get(key), str) and d[key] in d['scope'], f'结构任务 {key} 必须纳入 scope')
            require(safe_path(root, d[key]).is_file(), f'结构任务缺 {key} 文件')


def snapshot(root, task_rel, d):
    base = d['base_commit']
    changed = names(git(root, 'diff', '--no-renames', '--name-only', '-z', base, '--'))
    changed |= names(git(root, 'diff', '--cached', '--no-renames', '--name-only', '-z', base, '--'))
    changed |= names(git(root, 'ls-files', '--others', '--exclude-standard', '-z'))
    assigned = set(d['scope']) | set(d['foreign_changes']) | set(d['evidence_paths']) | {task_rel}
    require(not (changed - assigned), f'未登记 Git 差异，先报告归属：{sorted(changed - assigned)}')
    inventory = names(git(root, 'ls-files', '--cached', '--others', '--exclude-standard', '-z'))
    baseline = names(git(root, 'ls-tree', '-r', '--name-only', '-z', base))
    pending, entries = set(d['scope']), {}
    while pending:
        name = min(pending)
        pending.remove(name)
        if name in entries:
            continue
        p = safe_path(root, name)
        # Bind directory links traversed by a file path as well as the final link.
        parts = PurePosixPath(name).parts
        for i in range(1, len(parts)):
            ancestor = root.joinpath(*parts[:i])
            if ancestor.is_symlink():
                pending.add(ancestor.relative_to(root).as_posix())
        if p.is_symlink():
            target = os.readlink(p)
            require(not Path(target).is_absolute(), f'候选软链须相对路径：{name}')
            require(p.exists(), f'断链：{name}')
            entries[name] = {'path': name, 'type': 'symlink', 'target': target, 'executable': False}
            direct = Path(os.path.normpath(str(p.parent / target)))
            require(direct.is_relative_to(root), f'软链越界：{name}')
            direct_name = direct.relative_to(root).as_posix()
            safe_path(root, direct_name)
            if direct.is_symlink():
                pending.add(direct_name)
            # Parent links in the target path also affect its meaning.
            for ancestor in direct.parents:
                if ancestor == root:
                    break
                if ancestor.is_symlink():
                    pending.add(ancestor.relative_to(root).as_posix())
            resolved = p.resolve()
            source = resolved.relative_to(root).as_posix()
            if resolved.is_dir():
                members = {x for x in inventory if x.startswith(source + '/')} | {x for x in baseline if x.startswith(source + '/')}
                require(bool(members), f'软链目录没有受管源文件：{name}')
                pending |= members
            else:
                pending.add(source)
        elif p.is_file():
            require(name in inventory, f'文件不在 Git 候选清单：{name}')
            entries[name] = {'path': name, 'type': 'file', 'sha256': digest(p.read_bytes()), 'executable': bool(p.stat().st_mode & stat.S_IXUSR)}
        elif not p.exists():
            require(name in baseline, f'候选缺文件：{name}')
            entries[name] = {'path': name, 'type': 'deleted'}
        else:
            raise Invalid(f'scope 须列精确文件或软链：{name}')
    require(not (set(entries) & (set(d['evidence_paths']) | set(d['foreign_changes']) | {task_rel})), '软链源与排除项重叠')
    files = [entries[n] for n in sorted(entries)]
    payload = {'base_commit': base, 'files': files}
    fingerprint = digest(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())
    return {**payload, 'fingerprint': fingerprint}


def staged_errors(root, candidate):
    """Local acceptance may precede staging, but staged task content must match."""
    staged = names(git(root, 'diff', '--cached', '--no-renames', '--name-only', '-z', 'HEAD', '--'))
    index = {}
    for item in git(root, 'ls-files', '--stage', '-z').split('\0'):
        if not item:
            continue
        header, name = item.split('\t', 1)
        mode, oid, stage = header.split()
        index.setdefault(name, []).append((mode, oid, stage))
    errors = []
    for entry in candidate['files']:
        name = entry['path']
        if name not in staged:
            continue
        rows = index.get(name, [])
        if entry['type'] == 'deleted':
            if rows:
                errors.append(f'暂存内容与候选删除项不符：{name}')
            continue
        if len(rows) != 1 or rows[0][2] != '0':
            errors.append(f'暂存内容缺失或冲突：{name}')
            continue
        mode, oid, _ = rows[0]
        expected_mode = '120000' if entry['type'] == 'symlink' else ('100755' if entry['executable'] else '100644')
        expected_hash = digest(entry['target'].encode()) if entry['type'] == 'symlink' else entry['sha256']
        if mode != expected_mode or digest(git_raw(root, 'cat-file', 'blob', oid)) != expected_hash:
            errors.append(f'暂存内容与已验证候选不符，重新精确暂存并核查：{name}')
    return errors


def evidence_errors(root, d, delivery=False):
    errors, seen, passed = [], set(), set()
    fp = d['candidate']['fingerprint']
    for e in d['evidence']:
        if not isinstance(e, dict):
            errors.append('证据须为对象')
            continue
        eid = e.get('id')
        if not isinstance(eid, str) or not eid or eid in seen:
            errors.append('证据 id 缺失或重复')
        else:
            seen.add(eid)
        if not all(isinstance(e.get(k), str) and e[k] for k in ('kind', 'command', 'summary', 'environment', 'coverage')):
            errors.append(f'证据字段缺失：{eid}')
        if e.get('candidate') != fp:
            errors.append(f'证据陈旧，返回 D4/D5：{eid}')
        if e.get('status') not in STATUSES:
            errors.append(f'证据状态无效：{eid}')
        if 'exit_code' not in e or (e['exit_code'] is not None and type(e['exit_code']) is not int):
            errors.append(f'缺 exit_code（模型/人工可 null）：{eid}')
        if e.get('status') == 'passed' and e.get('exit_code') not in (0, None):
            errors.append(f'失败退出码不能标通过：{eid}')
        report = e.get('report')
        if not isinstance(report, str) or report not in d['evidence_paths']:
            errors.append(f'报告须登记 evidence_paths：{eid}')
        else:
            try:
                p = safe_path(root, report)
                require(p.is_file() and not p.is_symlink(), f'缺报告或报告为软链：{report}')
                require(digest(p.read_bytes()) == e.get('report_sha256'), f'报告内容变化：{report}')
            except Invalid as exc:
                errors.append(str(exc))
        if e.get('status') == 'passed' and isinstance(e.get('kind'), str):
            passed.add(e['kind'])
    if delivery:
        errors += staged_errors(root, d['candidate'])
        require(bool(d['required']), '交付必须声明 required 证据')
        errors += [f'必要证据缺失或未通过：{kind}' for kind in d['required'] if kind not in passed]
        if d['delivery']['local'] != 'accepted':
            errors.append('本地验收尚未 accepted')
        if d['blocked']:
            errors.append(f'任务仍受阻：{d["blocked"]}')
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('snapshot', 'check'))
    parser.add_argument('task')
    parser.add_argument('--repo', required=True)
    parser.add_argument('--delivery', action='store_true')
    args = parser.parse_args(argv)
    try:
        require(not args.delivery or args.action == 'check', '--delivery 仅用于 check')
        root, task, text, block, d = read_task(args.repo, args.task)
        current = snapshot(root, task.relative_to(root).as_posix(), d)
        if args.action == 'snapshot':
            d['candidate'] = current
            task.write_text(text[:block.start(1)] + json.dumps(d, ensure_ascii=False, indent=2) + text[block.end(1):], encoding='utf-8')
            print(f'SNAPSHOT {current["fingerprint"]} ({len(current["files"])} files)；旧证据未自动更新')
        else:
            require(d['candidate'] == current, '候选内容变化或未冻结，返回 D4（语义变化补行为验证和评审）')
            errors = evidence_errors(root, d, args.delivery)
            require(not errors, '\n'.join(errors))
            statuses = ', '.join(f'{e["id"]}={e["status"]}' for e in d['evidence']) or '无证据'
            print(('DELIVERY EVIDENCE OK' if args.delivery else 'RECORD OK（不等于验收通过）') + f' {current["fingerprint"]}\n{statuses}')
        return 0
    except (Invalid, OSError, ValueError) as exc:
        print(f'DEV CHECK FAILED: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
