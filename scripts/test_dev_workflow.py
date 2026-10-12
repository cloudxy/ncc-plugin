"""开发恢复与接线的失败路径，使用独立的合成 Git 仓库。"""
import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import check_dev_workflow as dev
import check_plugin as plugin


class DevWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.run_git('init', '-q')
        self.run_git('config', 'user.email', 'fixture@example.invalid')
        self.run_git('config', 'user.name', 'Fixture')
        self.write('scripts/product.py', 'print("baseline")\n')
        self.write('skills/ncc-dev/SKILL.md', '# synthetic skill\n')
        self.write('.gitignore', 'novels/\nignored/\n')
        self.run_git('add', '.')
        self.run_git('commit', '-qm', 'synthetic baseline')
        self.task = self.root / 'docs/dev/tasks/T1.md'
        self.data = {
            'schema': 1, 'id': 'T1', 'goal': '合成局部修复', 'route': 'bounded', 'risk_tags': [],
            'repo_root': str(self.root), 'plugin_root': str(self.root),
            'branch': self.run_git('branch', '--show-current').strip(),
            'base_commit': self.run_git('rev-parse', 'HEAD').strip(),
            'stage': 'D3', 'next': '验证', 'blocked': '',
            'decisions': [{'source': '合成请求', 'scope': '本地修复'}],
            'scope': ['scripts/product.py'], 'foreign_changes': {}, 'evidence_paths': [],
            'candidate': {}, 'required': ['unit'], 'evidence': [],
            'delivery': {k: 'pending' for k in ('local', 'commit', 'remote', 'clone', 'runtime')},
        }
        self.save()

    def run_git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], stderr=subprocess.DEVNULL).decode()

    def write(self, name, content):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return p

    def save(self):
        self.write('docs/dev/tasks/T1.md', '# 合成任务\n\n```ncc-dev-json\n' + json.dumps(self.data, ensure_ascii=False) + '\n```\n')

    def call(self, action, *extra):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = dev.main([action, str(self.task), '--repo', str(self.root), *extra])
        if result == 0 and action == 'snapshot':
            self.data = dev.read_task(self.root, self.task)[-1]
        return result

    def freeze(self):
        self.assertEqual(self.call('snapshot'), 0)
        return self.data['candidate']['fingerprint']

    def add_evidence(self):
        fp = self.freeze()
        p = self.write('docs/dev/evidence/T1/unit.md', '合成命令观察：成功\n')
        rel = p.relative_to(self.root).as_posix()
        self.data['evidence_paths'] = [rel]
        self.data['evidence'] = [{'id': 'unit-1', 'kind': 'unit', 'candidate': fp, 'status': 'passed',
                                  'command': 'synthetic check', 'exit_code': 0, 'summary': '合成成功',
                                  'environment': 'unittest fixture', 'coverage': 'synthetic',
                                  'report': rel, 'report_sha256': dev.digest(p.read_bytes())}]
        self.data['delivery']['local'] = 'accepted'
        self.save()
        return p

    def test_restore_same_candidate(self):
        self.freeze()
        self.assertEqual(self.call('check'), 0)
        self.assertEqual(self.call('check', '--delivery'), 1)

    def test_new_file_changes_fingerprint(self):
        before = self.freeze()
        self.write('scripts/new.py', 'new\n')
        self.data['scope'].append('scripts/new.py')
        self.save()
        self.assertNotEqual(before, self.freeze())

    def test_rule_edit_invalidates_evidence_even_after_refreeze(self):
        self.add_evidence()
        self.write('scripts/product.py', 'changed\n')
        self.assertEqual(self.call('check'), 1)
        self.freeze()
        self.assertEqual(self.call('check', '--delivery'), 1)

    def test_executable_bit_invalidates_candidate(self):
        self.freeze()
        os.chmod(self.root / 'scripts/product.py', 0o755)
        self.assertEqual(self.call('check'), 1)

    def test_registered_deletion_is_candidate(self):
        before = self.freeze()
        (self.root / 'scripts/product.py').unlink()
        self.assertNotEqual(before, self.freeze())
        self.assertEqual(self.data['candidate']['files'][0]['type'], 'deleted')

    def test_missing_new_file_rejected(self):
        self.data['scope'].append('scripts/missing.py')
        self.save()
        self.assertEqual(self.call('snapshot'), 1)

    def test_unregistered_git_change_rejected(self):
        self.write('scripts/unclaimed.py', 'new\n')
        self.assertEqual(self.call('snapshot'), 1)
        self.data['foreign_changes']['scripts/unclaimed.py'] = '他人合成工作，未纳入交付'
        self.save()
        self.freeze()

    def test_scope_cannot_be_excluded_as_evidence(self):
        self.data['evidence_paths'].append('scripts/product.py')
        self.save()
        self.assertEqual(self.call('snapshot'), 1)

    def test_private_ignored_and_traversal_paths_rejected(self):
        for name in ('novels/secret.md', 'ignored/foo.md', '../outside', '/etc/passwd', '.git/config', 'scripts/../secret'):
            with self.subTest(path=name):
                self.data['scope'] = [name]
                self.save()
                self.assertEqual(self.call('snapshot'), 1)

    def test_relative_symlink_directory_includes_source(self):
        p = self.root / '.agents/skills/ncc-dev'
        p.parent.mkdir(parents=True)
        p.symlink_to('../../skills/ncc-dev')
        self.data['scope'].append('.agents/skills/ncc-dev')
        self.save()
        self.freeze()
        self.assertIn('skills/ncc-dev/SKILL.md', [f['path'] for f in self.data['candidate']['files']])
        self.write('skills/ncc-dev/SKILL.md', 'rule edit\n')
        self.assertEqual(self.call('check'), 1)

    def test_symlink_target_and_source_exclusion_rejected(self):
        p = self.root / 'entry'
        p.symlink_to('scripts/product.py')
        self.data['scope'] = ['entry']
        self.data['foreign_changes'] = {'scripts/product.py': '不能排除软链源'}
        self.save()
        self.assertEqual(self.call('snapshot'), 1)

    def test_intermediate_symlink_cannot_be_excluded(self):
        (self.root / 'relay').symlink_to('scripts/product.py')
        (self.root / 'entry').symlink_to('relay')
        self.data['scope'] = ['entry']
        self.data['foreign_changes'] = {'relay': '他人路径也不能排除候选依赖'}
        self.save()
        self.assertEqual(self.call('snapshot'), 1)
        self.data['foreign_changes'] = {}
        self.data['scope'].append('relay')
        self.save()
        self.freeze()
        paths = [f['path'] for f in self.data['candidate']['files']]
        self.assertIn('relay', paths)
        self.assertIn('scripts/product.py', paths)

    def test_broken_external_private_and_cyclic_symlinks_rejected(self):
        for target in ('missing', '/etc/passwd', 'novels/secret.md', 'entry'):
            with self.subTest(target=target):
                p = self.root / 'entry'
                if p.is_symlink():
                    p.unlink()
                p.symlink_to(target)
                self.data['scope'] = ['entry']
                self.save()
                self.assertEqual(self.call('snapshot'), 1)

    def test_metadata_update_does_not_invalidate_product(self):
        self.add_evidence()
        self.data['next'] = '独立评审'
        self.save()
        self.assertEqual(self.call('check', '--delivery'), 0)

    def test_missing_or_changed_report_rejected(self):
        p = self.add_evidence()
        p.write_text('changed evidence')
        self.assertEqual(self.call('check', '--delivery'), 1)
        p.unlink()
        self.assertEqual(self.call('check', '--delivery'), 1)

    def test_failed_blocked_missing_evidence_not_delivery(self):
        self.add_evidence()
        for status in ('failed', 'blocked', 'pending'):
            self.data['evidence'][0]['status'] = status
            self.save()
            self.assertEqual(self.call('check', '--delivery'), 1)
        self.data['evidence'] = []
        self.save()
        self.assertEqual(self.call('check', '--delivery'), 1)

    def test_unowned_index_only_new_file_rejected(self):
        self.add_evidence()
        p = self.write('scripts/unowned.py', 'unverified staged content\n')
        self.run_git('add', 'scripts/unowned.py')
        p.unlink()
        self.assertEqual(self.call('check', '--delivery'), 1)
        self.assertEqual(self.call('snapshot'), 1)

    def test_staged_task_content_must_match_verified_worktree(self):
        self.add_evidence()
        p = self.root / 'scripts/product.py'
        old = p.read_bytes()
        p.write_text('unverified staged content\n')
        self.run_git('add', 'scripts/product.py')
        p.write_bytes(old)
        self.assertEqual(self.call('check', '--delivery'), 1)
        self.run_git('add', 'scripts/product.py')
        self.assertEqual(self.call('check', '--delivery'), 0)

    def test_staged_verified_content_is_accepted(self):
        self.write('scripts/product.py', 'verified changed content\n')
        self.add_evidence()
        self.run_git('add', 'scripts/product.py')
        self.assertEqual(self.call('check', '--delivery'), 0)

    def test_index_mode_and_symlink_target_mismatch_rejected(self):
        self.add_evidence()
        self.run_git('update-index', '--chmod=+x', 'scripts/product.py')
        self.assertEqual(self.call('check', '--delivery'), 1)
        self.run_git('add', 'scripts/product.py')
        link = self.root / 'entry'
        link.symlink_to('scripts/product.py')
        self.data['scope'].append('entry')
        self.save()
        self.add_evidence()
        link.unlink()
        link.symlink_to('skills/ncc-dev/SKILL.md')
        self.run_git('add', 'entry')
        link.unlink()
        link.symlink_to('scripts/product.py')
        self.assertEqual(self.call('check', '--delivery'), 1)

    def test_false_pass_with_failed_exit_code_rejected(self):
        self.add_evidence()
        self.data['evidence'][0]['exit_code'] = 1
        self.save()
        self.assertEqual(self.call('check'), 1)

    def test_task_through_repository_alias_is_valid(self):
        self.freeze()
        with tempfile.TemporaryDirectory() as tmp:
            alias = Path(tmp) / 'repo-alias'
            alias.symlink_to(self.root, target_is_directory=True)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                result = dev.main(['check', str(alias / 'docs/dev/tasks/T1.md'), '--repo', str(alias)])
            self.assertEqual(result, 0)

    def test_task_file_symlink_rejected(self):
        original = self.task.read_text()
        self.write('docs/dev/evidence/alternate.md', original)
        self.task.unlink()
        self.task.symlink_to('../evidence/alternate.md')
        self.assertEqual(self.call('snapshot'), 1)

    def test_wrong_repository_and_branch_rejected(self):
        self.data['repo_root'] = '/private/tmp'
        self.save()
        self.assertEqual(self.call('snapshot'), 1)
        self.data['repo_root'] = str(self.root)
        self.data['branch'] = 'nonexistent-branch'
        self.save()
        self.assertEqual(self.call('snapshot'), 1)

    def test_architectural_requires_spec_and_plan(self):
        self.data['route'] = 'architectural'
        self.save()
        self.assertEqual(self.call('snapshot'), 1)
        for key in ('spec', 'plan'):
            self.data[key] = f'docs/{key}.md'
            self.write(self.data[key], '# synthetic\n')
            self.data['scope'].append(self.data[key])
        self.save()
        self.freeze()

    def test_malformed_record_and_evidence_fail_cleanly(self):
        original_route = self.data['route']
        self.data['route'] = []
        self.save()
        self.assertEqual(self.call('snapshot'), 1)
        self.data['route'] = original_route
        self.save()
        self.add_evidence()
        self.data['evidence'][0]['kind'] = []
        self.save()
        self.assertEqual(self.call('check'), 1)
        self.data['evidence'][0]['status'] = []
        self.save()
        self.assertEqual(self.call('check'), 1)

    def test_candidate_forged_fingerprint_rejected(self):
        self.freeze()
        self.data['candidate']['fingerprint'] = 'fake'
        self.save()
        self.assertEqual(self.call('check'), 1)


class EntryRegistryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ('skills/entry/SKILL.md', 'commands/entry.md', 'docs/dev-workflow.md'):
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('# synthetic\n')
        (self.root / 'agents').mkdir()
        for mount, name, target in (('.agents/skills', 'entry', '../../skills/entry'),
                                    ('.claude/skills', 'entry', '../../skills/entry'),
                                    ('.claude/commands', 'entry.md', '../../commands/entry.md')):
            p = self.root / mount / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.symlink_to(target)

    def check(self):
        bad = []
        with patch.object(plugin, 'ROOT', self.root), patch.object(plugin, 'REG', {'roles': {}, 'commands': {'entry': {'skill': 'entry'}}}), patch.object(plugin, 'WRITER_READABLE', ()):
            plugin.check_registry(bad)
        return bad

    def test_valid_static_wiring(self):
        self.assertEqual(self.check(), [])

    def test_unregistered_entry_detected(self):
        (self.root / 'commands/extra.md').write_text('extra')
        (self.root / 'skills/extra').mkdir()
        (self.root / 'skills/extra/SKILL.md').write_text('extra')
        self.assertTrue(any('未登记入口' in s for s in self.check()))

    def test_broken_or_wrong_symlink_detected(self):
        p = self.root / '.agents/skills/entry'
        p.unlink()
        p.symlink_to('../../skills/missing')
        self.assertTrue(any('软链断裂' in s for s in self.check()))

    def test_external_skill_directory_source_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            external = Path(tmp)
            (external / 'SKILL.md').write_text('external source')
            (self.root / 'skills/entry/SKILL.md').unlink()
            (self.root / 'skills/entry').rmdir()
            (self.root / 'skills/entry').symlink_to(external)
            self.assertTrue(any('技能源指向仓外' in s for s in self.check()))

    def test_external_skill_file_source_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            external = Path(tmp) / 'SKILL.md'
            external.write_text('external source')
            p = self.root / 'skills/entry/SKILL.md'
            p.unlink()
            p.symlink_to(external)
            self.assertTrue(any('技能源指向仓外' in s for s in self.check()))

    def test_regular_copy_instead_of_symlink_detected(self):
        p = self.root / '.claude/commands/entry.md'
        p.unlink()
        p.write_text('copy')
        self.assertTrue(any('缺项目级软链' in s for s in self.check()))


if __name__ == '__main__':
    unittest.main()
