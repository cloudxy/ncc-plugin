"""Engineering routing and report freshness; no model or database calls."""
import contextlib
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from dev import development as roles
from dev.check_dev_workflow import safe_path
from ncclib.registry import load_registry

ROOT = Path(__file__).resolve().parents[2]


class DevelopmentRolesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True, capture_output=True)
        shutil.copytree(ROOT / 'workflow', self.root / 'workflow')
        self.config = load_registry(self.root)['development']
        needed = {'skills/ncc-dev/SKILL.md', 'docs/engineering/workflow.md'}
        for role in self.config['roles'].values():
            needed.update(roles.role_reads(role))
        for name in needed:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        (self.root / '.gitignore').write_text('.env\nnovels/\n')
        (self.root / '.env').write_text('PRIVATE_SYNTHETIC=not-for-packet')
        (self.root / 'proposal.md').write_text('Synthetic author journey and bounded design.')
        plan = roles.selection(self.config, ['configuration'])
        self.task = {'id': 'synthetic', 'goal': 'preserve configuration and author workflow',
                     'decisions': [{'source': 'synthetic test', 'scope': 'read-only design'}],
                     'engineering_contract': 1, 'engineering': {**plan, 'inputs': ['proposal.md'], 'reports': {}},
                     'evidence_paths': []}

    def packet(self, role='project-architect'):
        return roles.make_packet(self.root, self.task, role, safe_path)

    def report(self, packet, decision='ready'):
        return {'schema': 1, 'role': packet['role'], 'input_sha256': packet['input_sha256'],
                'execution': {'mode': 'current_session', 'identity': 'unit-test-not-agent'},
                'decision': decision,
                'deliverables': {key: 'Synthetic bounded design: preserve existing source and version constraints.' for key in packet['definition']['outputs']},
                'findings': [], 'verification': [{'scenario': 'synthetic review', 'expected': 'preserved versions',
                                                  'status': 'pending', 'evidence': 'Not executed; contract unit only.'}],
                'limitations': ['No real model, UI or database execution.']}

    def register(self, role, decision='ready'):
        packet = self.packet(role)
        report = self.report(packet, decision)
        if decision == 'changes_required':
            report['findings'] = [{'severity': 'major', 'location': 'proposal.md', 'problem': 'Synthetic conflict',
                                   'evidence': 'Explicit fixture requirement', 'fix': 'Preserve the newer version'}]
        prefix = 'docs/evidence/synthetic/' + role
        packet_name, report_name = prefix + '-packet.json', prefix + '-report.json'
        roles.write_json(self.root / packet_name, packet)
        roles.write_json(self.root / report_name, report)
        self.task['evidence_paths'] += [packet_name, report_name]
        self.task['engineering']['reports'][role] = {
            'packet': packet_name, 'packet_sha256': roles.digest((self.root / packet_name).read_bytes()),
            'report': report_name, 'report_sha256': roles.digest((self.root / report_name).read_bytes()),
            'status': roles.validate_report(packet, report)}

    def test_configuration_routes_only_architect_and_dba(self):
        selected = {name for name, value in self.task['engineering']['roles'].items() if value['required']}
        self.assertEqual(selected, {'project-architect', 'dba'})

    def test_documentation_skips_all_and_cross_feature_selects_all(self):
        docs = roles.selection(self.config, ['documentation'])
        self.assertFalse(any(value['required'] for value in docs['roles'].values()))
        feature = roles.selection(self.config, ['product', 'interaction', 'architecture', 'data'])
        self.assertEqual(set(feature['roles']), {name for name, value in feature['roles'].items() if value['required']})
        self.assertEqual(len(load_registry(self.root)['roles']), 12)

    def test_unknown_or_absent_effects_are_rejected(self):
        for effects in ([], ['invented']):
            with self.assertRaises(ValueError):
                roles.selection(self.config, effects)

    def test_packet_is_repeatable_and_has_only_bounded_sources(self):
        packet = self.packet()
        self.assertEqual(packet, self.packet())
        self.assertEqual(packet['product']['primary'], '小说创作')
        self.assertNotIn('PRIVATE_SYNTHETIC', json.dumps(packet))

    def test_packet_loads_the_registered_professional_skill_and_resources(self):
        packet = self.packet()
        paths = {source['path'] for source in packet['sources']}
        self.assertIn('skills/ncc-project-architect/SKILL.md', paths)
        self.assertIn('skills/ncc-project-architect/references/sop.md', paths)
        self.assertIn('skills/ncc-project-architect/templates/architecture-decision.md', paths)
        self.assertNotIn('skills/ncc-product-designer/SKILL.md', paths)

    def test_missing_skill_or_escaping_resource_has_no_role_only_fallback(self):
        definition = dict(self.config['roles']['project-architect'])
        del definition['skill']
        with self.assertRaisesRegex(ValueError, 'professional skill'):
            roles.role_reads(definition)
        definition = dict(self.config['roles']['project-architect'])
        definition['resources'] = {**definition['resources'], 'sop': '../outside.md'}
        with self.assertRaisesRegex(ValueError, 'escapes'):
            roles.role_reads(definition)
        (self.root / 'skills/ncc-project-architect/SKILL.md').unlink()
        with self.assertRaises(ValueError):
            self.packet()

    def test_private_and_escaping_inputs_are_rejected(self):
        for name in ('.env', '../outside.md', 'novels/secret.md'):
            self.task['engineering']['inputs'] = [name]
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.packet()

    def test_untriggered_role_and_oversized_context_are_rejected(self):
        with self.assertRaises(ValueError):
            self.packet('product-designer')
        (self.root / 'proposal.md').write_text('x' * 25000)
        with self.assertRaisesRegex(ValueError, '读取上限'):
            self.packet()

    def test_wrong_role_input_or_execution_cannot_be_registered(self):
        packet = self.packet()
        for field, value in [('role', 'dba'), ('input_sha256', 'old'), ('execution', {'mode': 'pretend'})]:
            report = self.report(packet)
            report[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                roles.validate_report(packet, report)

    def test_major_issue_cannot_be_ready_and_missing_deliverable_rejected(self):
        packet = self.packet()
        report = self.report(packet)
        report['findings'] = [{'severity': 'major', 'location': 'proposal.md', 'problem': 'conflict',
                               'evidence': 'synthetic', 'fix': 'keep author version'}]
        with self.assertRaisesRegex(ValueError, 'major'):
            roles.validate_report(packet, report)
        report = self.report(packet)
        del report['deliverables']['write_path']
        with self.assertRaisesRegex(ValueError, 'write_path'):
            roles.validate_report(packet, report)

    def test_missing_failed_or_forged_report_blocks_delivery(self):
        errors, statuses = roles.validate_engineering(self.root, self.task, safe_path, True)
        self.assertTrue(errors)
        self.assertEqual(statuses['dba'], 'pending')
        self.register('project-architect', 'changes_required')
        self.register('dba')
        self.assertTrue(roles.validate_engineering(self.root, self.task, safe_path, True)[0])
        self.task['engineering']['reports']['project-architect']['status'] = 'passed'
        self.assertTrue(roles.validate_engineering(self.root, self.task, safe_path)[0])

    def test_source_or_protocol_changes_invalidate_previous_report(self):
        self.register('project-architect')
        self.register('dba')
        self.assertFalse(roles.validate_engineering(self.root, self.task, safe_path, True)[0])
        for name in ('proposal.md', 'skills/ncc-dev/references/roles.md', 'skills/ncc-project-architect/references/sop.md'):
            path = self.root / name
            before = path.read_text()
            path.write_text(before + '\nchanged\n')
            self.assertTrue(roles.validate_engineering(self.root, self.task, safe_path)[0])
            path.write_text(before)

    def test_report_tampering_and_old_packet_overwrite_are_rejected(self):
        self.register('project-architect')
        record = self.task['engineering']['reports']['project-architect']
        (self.root / record['report']).write_text('{}')
        self.assertTrue(roles.validate_engineering(self.root, self.task, safe_path)[0])
        packet_file = self.root / record['packet']
        with self.assertRaisesRegex(ValueError, '保留历史'):
            roles.write_json(packet_file, {'different': True})

    def commit(self, message):
        subprocess.run(['git', '-C', str(self.root), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.root), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', message], check=True)
        return subprocess.check_output(['git', '-C', str(self.root), 'rev-parse', 'HEAD']).decode().strip()

    def commit_legacy_task(self):
        for name in ('workflow/registry/roles.json', 'workflow/registry.json'):
            path = self.root / name
            data = json.loads(path.read_text())
            del data['development']
            path.write_text(json.dumps(data))
        earlier_base = self.commit('before task creation')
        legacy = {'id': 'legacy', 'goal': 'historical', 'scope': ['proposal.md'], 'base_commit': earlier_base}
        name = 'docs/tasks/legacy.md'
        path = self.root / name
        path.parent.mkdir(parents=True)
        path.write_text('```ncc-dev-json\n' + json.dumps(legacy) + '\n```\n')
        self.commit('legacy task created after its base')
        return name, legacy

    def test_pre_contract_committed_task_with_earlier_base_remains_readable(self):
        name, legacy = self.commit_legacy_task()
        self.assertEqual(roles.validate_engineering(self.root, legacy, safe_path, True, name), ([], {}))
        legacy['goal'] = 'new scope'
        self.assertTrue(roles.validate_engineering(self.root, legacy, safe_path, True, name)[0])

    def test_legacy_task_cannot_remove_contract_after_adopting_it(self):
        name, legacy = self.commit_legacy_task()
        upgraded = {**legacy, 'engineering_contract': 1, 'engineering': self.task['engineering']}
        path = self.root / name
        path.write_text('```ncc-dev-json\n' + json.dumps(upgraded) + '\n```\n')
        self.commit('adopt engineering contract')
        path.write_text('```ncc-dev-json\n' + json.dumps(legacy) + '\n```\n')
        self.assertTrue(roles.validate_engineering(self.root, legacy, safe_path, True, name)[0])

    def test_committing_new_task_after_contract_introduction_does_not_make_it_legacy(self):
        name = 'docs/tasks/new.md'
        path = self.root / name
        path.parent.mkdir(parents=True)
        task = {'id': 'new', 'goal': 'new task', 'scope': ['proposal.md']}
        path.write_text('```ncc-dev-json\n' + json.dumps(task) + '\n```\n')
        self.commit('new task after engineering contract')
        self.assertTrue(roles.validate_engineering(self.root, task, safe_path, True, name)[0])

    def test_new_task_cannot_bypass_roles_by_removing_contract(self):
        new = dict(self.task)
        del new['engineering_contract']
        self.assertTrue(roles.validate_engineering(self.root, new, safe_path, True, 'docs/tasks/new.md')[0])
        del new['engineering']
        self.assertTrue(roles.validate_engineering(self.root, new, safe_path, True, 'docs/tasks/new.md')[0])

    def test_explicit_role_delivery_check_requires_a_plan(self):
        legacy = dict(self.task)
        del legacy['engineering_contract']
        del legacy['engineering']
        error = io.StringIO()
        with patch('dev.check_dev_workflow.read_task', return_value=(self.root, None, None, None, legacy)):
            with contextlib.redirect_stderr(error):
                result = roles.main(['--repo', str(self.root), '--task', 'unused.md', 'check', '--delivery'])
        self.assertEqual(result, 1)
        self.assertIn('development.py plan', error.getvalue())


if __name__ == '__main__':
    unittest.main()
