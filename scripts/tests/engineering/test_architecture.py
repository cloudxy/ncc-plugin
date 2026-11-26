"""工程工具入口、CLI 契约与分层依赖方向的架构边界检查。"""
import ast
import contextlib
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = TESTS_ROOT.parent
REPO_ROOT = SCRIPTS_ROOT.parent
sys.path.insert(0, str(SCRIPTS_ROOT))
from dev.builders import build_docs  # noqa: E402

from tests.engineering import test_dev_workflow as dev_cases  # noqa: E402

_MODULE_MIGRATION_MAP = {
    'ncclib.foundation.core.': 'ncclib.core.',
    'ncclib.narrative.book.': 'ncclib.book.',
    'ncclib.narrative.ledgers.': 'ncclib.ledgers.',
    'ncclib.narrative.loops.': 'ncclib.loops.',
    'ncclib.narrative.scenes.': 'ncclib.scenes.',
    'ncclib.narrative.views.': 'ncclib.views.',
    'ncclib.narrative.delivery.': 'ncclib.delivery.',
    'ncclib.assets.materials.': 'ncclib.materials.',
    'ncclib.assets.settings.': 'ncclib.settings.',
    'ncclib.assets.memory.': 'ncclib.memory.',
    'ncclib.assets.learning.': 'ncclib.learning.',
    'ncclib.assets.evolve.': 'ncclib.evolve.',
    'ncclib.deconstruction.facade.': 'ncclib.decon.',
    'ncclib.deconstruction.techniques.': 'ncclib.techniques.',
    'ncclib.quality.scoring.': 'ncclib.quality.',
}


def _normalize_legacy_module_names(value):
    if isinstance(value, str):
        for new_prefix, old_prefix in _MODULE_MIGRATION_MAP.items():
            if value.startswith(new_prefix):
                return old_prefix + value[len(new_prefix):]
        return value
    if isinstance(value, list):
        return [_normalize_legacy_module_names(item) for item in value]
    if isinstance(value, dict):
        return {k: _normalize_legacy_module_names(v) for k, v in value.items()}
    return value


class ToolMigrationTest(unittest.TestCase):
    def test_legacy_generated_marker_is_upgraded_without_changing_prose(self):
        old = '<!-- ncc:gen example 开始（scripts/build_docs.py 由 workflow/registry.json 生成，勿手改） -->'
        text = '手写开头\n' + old + '\n旧内容\n<!-- ncc:gen example 结束 -->\n手写结尾\n'
        new = build_docs.fill(text, 'example', '新内容', 'fixture')
        self.assertEqual(new, '手写开头\n' + build_docs.begin('example') + '\n新内容\n' + build_docs.end('example') + '\n手写结尾\n')
        self.assertEqual(build_docs.fill(new, 'example', '新内容', 'fixture'), new)
        with self.assertRaises(SystemExit):
            build_docs.fill('没有标记', 'example', '内容', 'fixture')

    def test_checker_and_generator_from_other_cwd(self):
        with tempfile.TemporaryDirectory(prefix='ncc 中文 space ') as cwd:
            for rel_script, args in (
                ('dev/checkers/check_plugin.py', ['-v']),
                ('dev/builders/build_docs.py', ['--check']),
                ('dev/builders/build_registry.py', ['--check']),
            ):
                p = subprocess.run(
                    [sys.executable, str(SCRIPTS_ROOT / rel_script), *args],
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_recovery_checker_uses_explicit_repo_and_preserves_failures(self):
        fixture = dev_cases.DevWorkflowTest()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        checker = SCRIPTS_ROOT / 'dev/checkers/check_dev_workflow.py'
        with tempfile.TemporaryDirectory(prefix='ncc 恢复 space ') as cwd:
            for action, expected in (('snapshot', 0), ('check', 0)):
                p = subprocess.run(
                    [sys.executable, str(checker), action, str(fixture.task), '--repo', str(fixture.root)],
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(p.returncode, expected, p.stdout + p.stderr)
            fixture.write('scripts/product.py', 'changed after snapshot\n')
            p = subprocess.run(
                [sys.executable, str(checker), 'check', str(fixture.task), '--repo', str(fixture.root)],
                cwd=cwd,
                capture_output=True,
                text=True,
            )
            self.assertEqual(p.returncode, 1)
            self.assertIn('候选内容变化', p.stderr)


class CliArchitectureTest(unittest.TestCase):
    def test_complete_parser_contract_matches_pre_upgrade_snapshot(self):
        from ncclib.cli.dispatch import build_parser

        from tests.support._cli_contract import describe

        frozen = json.loads((TESTS_ROOT / 'fixtures/contracts/cli-contract.json').read_text())
        data = _normalize_legacy_module_names(describe(build_parser()))
        extra_top = {'quality', 'plight', 'sandbox'}
        data = [row for row in data if not row['path'] or row['path'][0] not in extra_top]
        for row in data:
            if not row['path']:
                for action in row['actions']:
                    if 'subparsers' in action:
                        action['subparsers'] = [name for name in action['subparsers'] if name not in extra_top]
            elif row['path'] == ['chapter', 'add']:
                row['actions'] = [action for action in row['actions'] if action.get('dest') != 'origin']
            elif row['path'] == ['soul']:
                row['actions'] = [action for action in row['actions'] if action.get('dest') != 'arc_stage']
            elif row['path'] == ['unit', 'open']:
                row['actions'] = [action for action in row['actions'] if action.get('dest') not in {'countdown', 'milestone', 'arc_ch'}]
            elif row['path'] in (['promise', 'add'], ['promise', 'touch']):
                row['actions'] = [action for action in row['actions'] if action.get('dest') not in {'line', 'cover', 'truth'}]
            elif row['path'] == ['promise', 'list']:
                row['actions'] = [action for action in row['actions'] if action.get('dest') not in {'line', 'show_truth'}]
        extra_actions = {'plan', 'packet', 'ingest'}
        extra_options = {
            'index': {'config', 'accept_reindex'},
            'mark': {'layer'},
            'coverage': {'layer'},
            'stats': {'layer'},
        }
        data = [row for row in data if not (len(row['path']) > 1 and row['path'][0] == 'decon' and row['path'][1] in extra_actions)]
        for row in data:
            if row['path'] == ['decon']:
                for action in row['actions']:
                    if 'subparsers' in action:
                        self.assertEqual(set(action['subparsers']) - set(extra_actions), {'index', 'mark', 'coverage', 'stats', 'link'})
                        action['subparsers'] = [name for name in action['subparsers'] if name not in extra_actions]
            elif len(row['path']) == 2 and row['path'][0] == 'decon':
                row['actions'] = [a for a in row['actions'] if a.get('dest') not in extra_options.get(row['path'][1], set())]
        self.assertEqual([row['path'] for row in data], frozen['paths'])
        raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(),
            frozen['sha256'],
            'CLI parameter/handler contract changed; compare with the frozen baseline',
        )

    def test_runtime_outputs_and_files_match_pre_upgrade_snapshot(self):
        from tests.support._behavior_probe import probe

        expected = json.loads((TESTS_ROOT / 'fixtures/contracts/runtime-contract.json').read_text())
        with tempfile.TemporaryDirectory(prefix='ncc 兼容 space ') as tmp:
            rows = probe(REPO_ROOT, Path(tmp) / 'workspace')
        for row in rows:
            raw = json.dumps(row.pop('files'), ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
            row['files_sha256'] = hashlib.sha256(raw).hexdigest()
        self.assertEqual(rows, expected)

    def test_domain_and_parser_import_boundaries(self):
        root = SCRIPTS_ROOT / 'ncclib'
        violations = []
        for path in root.rglob('*.py'):
            rel_parts = path.relative_to(root).parts
            in_cli = rel_parts[0] == 'cli'
            in_parsers = len(rel_parts) >= 2 and rel_parts[:2] == ('cli', 'parsers')
            in_foundation = rel_parts[0] == 'foundation'
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.ImportFrom):
                    names = [node.module or ''] + [a.name for a in node.names]
                elif isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                else:
                    continue
                tokens = {part for name in names for part in name.split('.') if part}
                forbidden = {'dev', 'tests'}
                if not in_cli:
                    forbidden |= {'cli', 'parsers'}
                elif in_parsers:
                    forbidden.add('dispatch')
                if in_foundation:
                    forbidden |= {'narrative', 'assets', 'quality', 'preparation', 'deconstruction', 'evaluation', 'cli'}
                if tokens & forbidden:
                    violations.append((str(path.relative_to(root)), sorted(tokens & forbidden)))
        self.assertEqual(violations, [])

    def test_no_loose_python_files_piled_in_root_containers(self):
        allowed_entries = {
            SCRIPTS_ROOT / 'dev': {'run_browser_suite.py'},
        }
        for container in (
            SCRIPTS_ROOT,
            SCRIPTS_ROOT / 'ncclib',
            SCRIPTS_ROOT / 'dev',
            SCRIPTS_ROOT / 'tests',
            REPO_ROOT / 'tests' / 'unit',
            REPO_ROOT / 'tests' / 'backend',
            REPO_ROOT / 'tests' / 'browser',
        ):
            allowed = {'__init__.py', 'conftest.py'} | allowed_entries.get(container, set())
            loose = [
                p.name
                for p in container.glob('*.py')
                if p.name not in allowed
            ]
            self.assertEqual(loose, [], f'{container} has ungrouped loose files: {loose}')

    def test_bad_argument_and_parse_do_not_dispatch(self):
        from ncclib.cli.dispatch import build_parser

        parser = build_parser()
        with contextlib.redirect_stderr(io.StringIO()):
            for args in ([], ['gate', 'fixture', 'unknown'], ['chapter', 'add', 'fixture']):
                with self.subTest(args=args), self.assertRaises(SystemExit) as exc:
                    parser.parse_args(args)
                self.assertEqual(exc.exception.code, 2)
        args = parser.parse_args(['promise', 'list', 'fixture'])
        self.assertEqual(args.action, 'list')
        self.assertEqual(args.fn.__name__, 'cmd_promise')


if __name__ == '__main__':
    unittest.main()
