#!/usr/bin/env python3
"""Engineering role planning, bounded packets and fresh report registration. No model calls."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ncclib.registry import load_registry


def digest(value):
    return hashlib.sha256(value).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def require(ok, detail):
    if not ok:
        raise ValueError(detail)


def selection(config, effects):
    effects = sorted(set(effects))
    require(bool(effects), '必须声明实际影响；纯文档使用documentation')
    require(not (set(effects) - set(config['effects'])), '存在未登记的工程影响类型')
    roles = {}
    for name, definition in config['roles'].items():
        hit = sorted(set(effects) & set(definition['effects']))
        roles[name] = {'required': bool(hit), 'reason': '影响：' + '、'.join(hit) if hit else '本次影响不触发该职责'}
    return {'schema': 1, 'effects': effects, 'roles': roles}


def role_reads(definition):
    """Resolve a role's professional skill and assets from one registry mapping."""
    skill = definition.get('skill')
    require(isinstance(skill, str) and len(skill) <= 64
            and re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', skill), 'Missing or invalid professional skill')
    resources = definition.get('resources')
    require(isinstance(resources, dict) and {'sop', 'template', 'sources'} <= set(resources),
            'Professional skill requires SOP, template and sources')
    reads = definition.get('reads')
    require(isinstance(reads, list) and all(isinstance(name, str) for name in reads), 'Invalid role reads')
    paths = list(reads) + ['skills/' + skill + '/SKILL.md']
    for name in resources.values():
        require(isinstance(name, str), 'Invalid skill resource')
        path = PurePosixPath(name)
        require(not path.is_absolute() and path.as_posix() == name and path.suffix == '.md'
                and path.parts[0] in ('references', 'templates')
                and not (set(path.parts) & {'.', '..', '.git'}), 'Skill resource escapes its owner')
        paths.append('skills/' + skill + '/' + name)
    return sorted(set(paths))


def metadata_path(root, name, safe_path):
    require(isinstance(name, str) and name.startswith('docs/evidence/'), '派单/报告只能保存在docs/evidence下')
    path = safe_path(root, name)
    require(not path.is_symlink(), '工程元数据不能是软链')
    return path


def write_json(path, data):
    if path.exists():
        require(json.loads(path.read_text()) == data, '同路径证据已存在且内容不同，请使用新路径保留历史')
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
        os.link(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def make_packet(root, task, role, safe_path):
    registry = load_registry(root)
    config = registry['development']
    plan = task.get('engineering')
    require(isinstance(plan, dict), '先运行development.py plan')
    expected = selection(config, plan['effects'])
    require(plan['roles'] == expected['roles'], '角色触发定义已变化，请重做工程计划')
    require(role in plan['roles'] and plan['roles'][role]['required'], '本任务未触发该工程角色')
    definition = config['roles'][role]
    paths = sorted(set(role_reads(definition) + plan['inputs']))
    sources = []
    for name in paths:
        path = safe_path(root, name)
        require(path.is_file(), '角色输入不存在：' + name)
        content = path.read_text(encoding='utf-8')
        sources.append({'path': name, 'sha256': digest(path.read_bytes()), 'content': content})
    bindings = {}
    for name in ('skills/ncc-dev/SKILL.md', 'docs/engineering/workflow.md'):
        bindings[name] = digest(safe_path(root, name).read_bytes())
    packet = {
        'schema': 1, 'role': role, 'task_id': task['id'], 'goal': task['goal'],
        'product': {'primary': config['primary'], 'support': config['support']},
        'effects': plan['effects'], 'definition': definition,
        'authorization': task['decisions'], 'sources': sources, 'bindings': bindings,
        'execution_scope': '只读设计/评审；仅写协调者指定报告，不访问真实私有配置、书稿或数据库',
    }
    size = sum(not character.isspace() for character in encoded(packet).decode())
    require(size <= registry['load_budget']['ceilings']['subagent'], '派单超过角色读取上限，请缩小明确输入范围')
    packet['input_sha256'] = digest(encoded(packet))
    return packet


def text(value):
    return isinstance(value, str) and bool(value.strip())


def validate_report(packet, report):
    require(isinstance(report, dict) and type(report.get('schema')) is int and report['schema'] == 1, '工程报告schema无效')
    require(report.get('role') == packet['role'], '报告角色不匹配')
    require(report.get('input_sha256') == packet['input_sha256'], '报告输入已过期或不匹配')
    execution = report.get('execution', {})
    require(isinstance(execution, dict) and execution.get('mode') in ('subagent', 'current_session')
            and text(execution.get('identity')), '须如实记录执行方式与会话标识')
    require(report.get('decision') in ('ready', 'changes_required', 'blocked'), '工程结论无效')
    outputs = report.get('deliverables', {})
    require(isinstance(outputs, dict), '缺少职责交付')
    for field in packet['definition']['outputs']:
        require(text(outputs.get(field)), '缺少职责交付：' + field)
    findings = report.get('findings')
    require(isinstance(findings, list), '缺少问题数组')
    for finding in findings:
        require(isinstance(finding, dict) and finding.get('severity') in ('major', 'minor'), '问题严重度无效')
        require(all(text(finding.get(key)) for key in ('location', 'problem', 'evidence', 'fix')), '问题缺定位、证据或修法')
    checks = report.get('verification')
    require(isinstance(checks, list) and bool(checks), '缺少验证场景')
    for check in checks:
        require(isinstance(check, dict) and check.get('status') in ('passed', 'pending', 'blocked'), '验证状态无效')
        require(all(text(check.get(key)) for key in ('scenario', 'expected', 'evidence')), '验证缺观察或证据')
    limits = report.get('limitations')
    require(isinstance(limits, list) and all(text(item) for item in limits), '限制须为字符串数组')
    if report['decision'] == 'ready':
        require(not any(item['severity'] == 'major' for item in findings), '存在major问题不能ready')
    elif report['decision'] == 'changes_required':
        require(bool(findings), '退回结论需要具体问题')
    else:
        require(bool(limits), '受阻结论需要缺项说明')
    return {'ready': 'passed', 'changes_required': 'failed', 'blocked': 'blocked'}[report['decision']]


def legacy_task(root, task, task_rel, safe_path):
    """Prove this definition existed before engineering contracts were introduced."""
    if not task_rel or 'engineering' in task:
        return False
    safe_path(root, task_rel)
    from dev.check_dev_workflow import BLOCK
    history = subprocess.run(['git', '-C', str(root), 'log', '--format=%H', '--', task_rel], capture_output=True)
    require(history.returncode == 0, '无法核对任务历史')
    found_legacy = False
    for revision in history.stdout.decode().splitlines():
        require(re.fullmatch(r'[0-9a-f]{40}', revision) is not None, '无效历史版本')
        old = subprocess.run(['git', '-C', str(root), 'show', revision + ':' + task_rel], capture_output=True)
        if old.returncode:
            continue
        blocks = list(BLOCK.finditer(old.stdout.decode('utf-8')))
        if len(blocks) != 1:
            continue
        previous = json.loads(blocks[0].group(1))
        if not isinstance(previous, dict):
            continue
        if 'engineering_contract' in previous or 'engineering' in previous:
            return False
        if not all(previous.get(key) == task.get(key) for key in ('id', 'goal', 'scope', 'decisions', 'route', 'spec', 'plan')):
            continue
        for name in ('workflow/registry/roles.json', 'workflow/registry.json'):
            old_registry = subprocess.run(['git', '-C', str(root), 'show', revision + ':' + name], capture_output=True)
            if old_registry.returncode == 0:
                config = json.loads(old_registry.stdout)
                if isinstance(config, dict) and 'development' not in config:
                    found_legacy = True
                break
    return found_legacy


def validate_engineering(root, task, safe_path, delivery=False, task_rel=None):
    """Called by the existing task checker; legacy task records remain readable."""
    errors, statuses = [], {}
    try:
        if 'engineering_contract' not in task:
            require(legacy_task(root, task, task_rel, safe_path), '缺少工程职责计划；仅契约引入前已提交且定义不变的旧任务兼容无契约')
            return errors, statuses
        require(task['engineering_contract'] == 1, '工程职责契约版本无效')
        plan = task.get('engineering')
        require(isinstance(plan, dict), '缺少工程职责计划')
        config = load_registry(root)['development']
        expected = selection(config, plan['effects'])
        require(plan['schema'] == 1 and plan['roles'] == expected['roles'], '工程职责计划已过期')
        require(isinstance(plan['inputs'], list) and all(text(item) for item in plan['inputs']), '工程输入路径无效')
        records = plan.get('reports', {})
        require(isinstance(records, dict), '工程报告登记无效')
        require(not (set(records) - set(plan['roles'])), '存在未登记工程角色报告')
        for role, choice in plan['roles'].items():
            if not choice['required']:
                require(role not in records, '未触发职责不应登记报告：' + role)
                statuses[role] = 'not_applicable'
                continue
            record = records.get(role)
            if record is None:
                statuses[role] = 'pending'
            else:
                packet_file = metadata_path(root, record['packet'], safe_path)
                report_file = metadata_path(root, record['report'], safe_path)
                require(record['packet'] in task['evidence_paths'] and record['report'] in task['evidence_paths'], '工程报告及派单须登记evidence_paths')
                require(digest(packet_file.read_bytes()) == record['packet_sha256'], '派单内容变化：' + role)
                require(digest(report_file.read_bytes()) == record['report_sha256'], '报告内容变化：' + role)
                packet = json.loads(packet_file.read_text())
                fresh = make_packet(root, task, role, safe_path)
                require(packet == fresh, '工程输入变化，重新派单：' + role)
                status = validate_report(packet, json.loads(report_file.read_text()))
                require(status == record['status'], '登记结论与报告不符：' + role)
                statuses[role] = status
            if delivery and statuses[role] != 'passed':
                errors.append('必要工程职责未通过：' + role + '=' + statuses[role])
    except (ValueError, OSError, KeyError, TypeError) as error:
        errors.append('工程职责：' + str(error))
    return errors, statuses


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--task', required=True)
    commands = parser.add_subparsers(dest='action', required=True)
    plan = commands.add_parser('plan')
    plan.add_argument('--effects', nargs='+', required=True)
    plan.add_argument('--input', action='append', default=[])
    packet = commands.add_parser('packet')
    packet.add_argument('--role', required=True)
    packet.add_argument('--output', required=True)
    record = commands.add_parser('record')
    record.add_argument('--packet', required=True)
    record.add_argument('--report', required=True)
    status = commands.add_parser('check')
    status.add_argument('--delivery', action='store_true')
    args = parser.parse_args(argv)
    from dev.check_dev_workflow import read_task, safe_path
    try:
        root, task_path, original, block, task = read_task(args.repo, args.repo / args.task)
        config = load_registry(root)['development']
        if args.action == 'plan':
            planned = {**selection(config, args.effects), 'inputs': sorted(set(args.input)), 'reports': {}}
            for name in planned['inputs']:
                require(safe_path(root, name).is_file(), '角色输入不存在：' + name)
            previous = task.get('engineering', {})
            if all(previous.get(key) == planned[key] for key in ('schema', 'effects', 'roles', 'inputs')):
                planned['reports'] = previous.get('reports', {})
            task['engineering_contract'], task['engineering'] = 1, planned
            result = planned
        elif args.action == 'packet':
            result = make_packet(root, task, args.role, safe_path)
            write_json(metadata_path(root, args.output, safe_path), result)
            task['evidence_paths'] = sorted(set(task['evidence_paths'] + [args.output]))
        elif args.action == 'record':
            packet_path = metadata_path(root, args.packet, safe_path)
            packet = json.loads(packet_path.read_text())
            require(packet == make_packet(root, task, packet['role'], safe_path), '派单或来源已变化，请重新生成')
            report_path = metadata_path(root, args.report, safe_path)
            report = json.loads(report_path.read_text())
            status = validate_report(packet, report)
            result = {'packet': args.packet, 'packet_sha256': digest(packet_path.read_bytes()),
                      'report': args.report, 'report_sha256': digest(report_path.read_bytes()), 'status': status}
            task['engineering']['reports'][packet['role']] = result
            task['evidence_paths'] = sorted(set(task['evidence_paths'] + [args.packet, args.report]))
        else:
            require(task.get('engineering_contract') == 1, '先运行development.py plan记录工程职责')
            errors, result = validate_engineering(root, task, safe_path, args.delivery, task_path.relative_to(root).as_posix())
            require(not errors, '\n'.join(errors))
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        task_path.write_text(original[:block.start(1)] + json.dumps(task, ensure_ascii=False, indent=2) + original[block.end(1):])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print('ENGINEERING CHECK FAILED: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
