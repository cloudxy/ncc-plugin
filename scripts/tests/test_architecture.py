"""开发入口迁移、CLI 契约与依赖方向的兼容检查。"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SCRIPTS_ROOT.parent
sys.path.insert(0, str(SCRIPTS_ROOT))
from dev import build_docs
from tests import test_dev_workflow as dev_cases


class ToolMigrationTest(unittest.TestCase):
    def test_legacy_generated_marker_is_upgraded_without_changing_prose(self):
        old = '<!-- ncc:gen example 开始（scripts/build_docs.py 由 workflow/registry.json 生成，勿手改） -->'
        text = '手写开头\n' + old + '\n旧内容\n<!-- ncc:gen example 结束 -->\n手写结尾\n'
        new = build_docs.fill(text, 'example', '新内容', 'fixture')
        self.assertEqual(new, '手写开头\n' + build_docs.begin('example') + '\n新内容\n' + build_docs.end('example') + '\n手写结尾\n')
        self.assertEqual(build_docs.fill(new, 'example', '新内容', 'fixture'), new)
        with self.assertRaises(SystemExit):
            build_docs.fill('没有标记', 'example', '内容', 'fixture')

    def test_old_and_new_checker_and_generator_from_other_cwd(self):
        with tempfile.TemporaryDirectory(prefix='ncc 中文 space ') as cwd:
            for name, args in (('check_plugin', ['-v']), ('build_docs', ['--check'])):
                outputs = []
                for directory in (SCRIPTS_ROOT, SCRIPTS_ROOT / 'dev'):
                    p = subprocess.run([sys.executable, str(directory / (name + '.py')), *args],
                                       cwd=cwd, capture_output=True, text=True)
                    self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                    outputs.append(p.stdout + p.stderr)
                self.assertEqual(*outputs)

    def test_recovery_wrapper_uses_explicit_repo_and_preserves_failures(self):
        fixture = dev_cases.DevWorkflowTest()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        with tempfile.TemporaryDirectory(prefix='ncc 恢复 space ') as cwd:
            for action, expected in (('snapshot', 0), ('check', 0)):
                outputs = []
                for directory in (SCRIPTS_ROOT, SCRIPTS_ROOT / 'dev'):
                    p = subprocess.run([sys.executable, str(directory / 'check_dev_workflow.py'), action,
                                        str(fixture.task), '--repo', str(fixture.root)],
                                       cwd=cwd, capture_output=True, text=True)
                    self.assertEqual(p.returncode, expected, p.stdout + p.stderr)
                    outputs.append(p.stdout + p.stderr)
                self.assertEqual(*outputs)
            fixture.write('scripts/product.py', 'changed after snapshot\n')
            for directory in (SCRIPTS_ROOT, SCRIPTS_ROOT / 'dev'):
                p = subprocess.run([sys.executable, str(directory / 'check_dev_workflow.py'), 'check',
                                    str(fixture.task), '--repo', str(fixture.root)],
                                   cwd=cwd, capture_output=True, text=True)
                self.assertEqual(p.returncode, 1)
                self.assertIn('候选内容变化', p.stderr)


class CliArchitectureTest(unittest.TestCase):
    def test_complete_parser_contract_matches_pre_upgrade_snapshot(self):
        from ncclib.cli import build_parser
        from tests._cli_contract import describe
        frozen = json.loads((Path(__file__).parent / 'fixtures/cli-contract.json').read_text())
        data = describe(build_parser())
        # P1 contract explicitly adds only these decon actions/options. Keep the
        # original baseline immutable and continue checking every other action.
        extra_actions = {'plan', 'packet', 'ingest'}
        extra_options = {'index': {'config', 'accept_reindex'}, 'mark': {'layer'},
                         'coverage': {'layer'}, 'stats': {'layer'}}
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
        self.assertEqual(hashlib.sha256(raw).hexdigest(), frozen['sha256'],
                         'CLI parameter/handler contract changed; compare with the frozen baseline')

    def test_runtime_outputs_and_files_match_pre_upgrade_snapshot(self):
        from tests._behavior_probe import probe
        expected = json.loads((Path(__file__).parent / 'fixtures/runtime-contract.json').read_text())
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
            is_parser = 'cli_parsers' in path.parts
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.ImportFrom):
                    names = [node.module or ''] + [a.name for a in node.names]
                elif isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                else:
                    continue
                tokens = {part for name in names for part in name.split('.')}
                forbidden = {'dev'}
                if path.name != 'cli.py':
                    forbidden.add('cli')
                    if not is_parser:
                        forbidden.add('cli_parsers')
                if tokens & forbidden:
                    violations.append((str(path.relative_to(root)), sorted(tokens & forbidden)))
        self.assertEqual(violations, [])

    def test_bad_argument_and_parse_do_not_dispatch(self):
        from ncclib.cli import build_parser
        import contextlib
        import io
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
