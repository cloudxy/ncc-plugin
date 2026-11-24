"""打包清单跨格式一致性与坏输入反例（含 DSH Cordis bundle）。"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = SCRIPTS_ROOT.parent
sys.path.insert(0, str(SCRIPTS_ROOT))

from dev.checkers import check_plugin as plugin

VALID_CORDIS_PATCH = """# Synthetic DSH bundle patch
- insert:
    - id: ncc-workflow-skills
      name: '@deepseek-ai/dsh-skill-filesystem'
      config:
        providerName: ncc-workflow
        includeDefaultRoots: false
        bundledSkillDir: !!js "process.getBuiltinModule('node:path').join(process.getBuiltinModule('node:path').dirname(process.getBuiltinModule('node:module').createRequire(baseUrl).resolve('ncc-workflow/package.json')), 'skills')"
"""


class ManifestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for directory in ('skills', 'commands', 'agents'):
            (self.root / directory).mkdir()
        self.docs = {
            'plugin.json': {'name': 'ncc-workflow', 'version': '3.2.0'},
            'package.json': {
                'name': 'ncc-workflow',
                'version': '3.2.0',
                'description': 'Novel Create Center DSH bundle',
                'type': 'module',
                'exports': {
                    './cordis.patch.yml': './cordis.patch.yml',
                    './package.json': './package.json',
                },
                'files': ['cordis.patch.yml', 'skills', 'agents', 'commands', 'workflow'],
                'dsh': {'bundle': {'patch': './cordis.patch.yml'}},
                'engines': {'dsh': '>=0.2.0-0'},
            },
            '.zcode-plugin/plugin.json': {
                'name': 'ncc-workflow',
                'version': '3.2.0',
                'skills': 'skills',
                'commands': 'commands',
                'agents': 'agents',
            },
            '.claude-plugin/plugin.json': {'name': 'ncc-workflow', 'version': '3.2.0'},
            '.claude-plugin/marketplace.json': {
                'name': 'different-market',
                'plugins': [
                    {'name': 'other-plugin'},
                    {'name': 'ncc-workflow', 'version': '3.2.0', 'source': './'},
                ],
            },
            '.agents/plugins/marketplace.json': {
                'name': 'codex-market',
                'plugins': [
                    {'name': 'ncc-workflow', 'source': {'source': 'local', 'path': './'}},
                ],
            },
        }
        self.text_files = {'cordis.patch.yml': VALID_CORDIS_PATCH}

    def check(self):
        for path, doc in self.docs.items():
            p = self.root / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(doc), encoding='utf-8')
        for path, text in self.text_files.items():
            p = self.root / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding='utf-8')
        bad = []
        plugin.check_manifests(self.root, bad)
        return bad

    def test_different_market_names_order_and_no_codex_version(self):
        self.assertEqual(self.check(), [])

    def test_live_repository_manifests_pass_check(self):
        bad = []
        plugin.check_manifests(REPO_ROOT, bad)
        self.assertEqual(bad, [])

    def test_name_and_version_drift(self):
        original = copy.deepcopy(self.docs)
        for path in ('plugin.json', 'package.json', '.claude-plugin/plugin.json'):
            for field in ('name', 'version'):
                with self.subTest(path=path, field=field):
                    self.docs = copy.deepcopy(original)
                    self.docs[path][field] = 'drift'
                    self.assertTrue(any(path in b and field in b for b in self.check()))
        self.docs = copy.deepcopy(original)
        self.docs['.claude-plugin/marketplace.json']['plugins'][1]['version'] = 'drift'
        self.assertTrue(any('version' in b for b in self.check()))

    def test_invalid_plugin_collections_and_matching(self):
        original = copy.deepcopy(self.docs)
        for path in ('.claude-plugin/marketplace.json', '.agents/plugins/marketplace.json'):
            for bad_value in (None, {}, [3], [], [{'name': 'missing'}]):
                with self.subTest(path=path, value=bad_value):
                    self.docs = copy.deepcopy(original)
                    self.docs[path]['plugins'] = bad_value
                    self.assertTrue(self.check())
            self.docs = copy.deepcopy(original)
            self.docs[path]['plugins'] *= 2
            self.assertTrue(self.check())

    def test_missing_malformed_and_nonobject_files(self):
        for path in self.docs:
            for raw in (None, '{', '[]'):
                with self.subTest(path=path, raw=raw):
                    self.check()
                    p = self.root / path
                    if raw is None:
                        p.unlink()
                    else:
                        p.write_text(raw, encoding='utf-8')
                    bad = []
                    plugin.check_manifests(self.root, bad)
                    self.assertTrue(any(path in b for b in bad))

    def test_authority_fields_and_paths(self):
        original = copy.deepcopy(self.docs)
        for field, value in (('name', ''), ('version', 3), ('skills', '../outside'),
                             ('commands', '/tmp'), ('agents', 'missing')):
            with self.subTest(field=field):
                self.docs = copy.deepcopy(original)
                self.docs['.zcode-plugin/plugin.json'][field] = value
                self.assertTrue(self.check())

    def test_market_source_paths_and_kind(self):
        original = copy.deepcopy(self.docs)
        for value in ('../', '/tmp', 'missing', None):
            self.docs = copy.deepcopy(original)
            self.docs['.claude-plugin/marketplace.json']['plugins'][1]['source'] = value
            self.assertTrue(self.check())
        for value in ({'source': 'remote', 'path': './'}, {'source': 'local', 'path': '../'}, None):
            self.docs = copy.deepcopy(original)
            self.docs['.agents/plugins/marketplace.json']['plugins'][0]['source'] = value
            self.assertTrue(self.check())

    def test_external_symlink_entry_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.root / 'skills').rmdir()
            (self.root / 'skills').symlink_to(outside)
            self.assertTrue(self.check())

    def test_dsh_bundle_patch_missing_traversal_and_symlink_rejected(self):
        original = copy.deepcopy(self.docs)
        for bad_dsh in (
            None,
            {},
            {'bundle': None},
            {'bundle': {}},
            {'bundle': {'patch': ''}},
            {'bundle': {'patch': []}},
            {'bundle': {'patch': './missing.patch.yml'}},
            {'bundle': {'patch': '../outside.yml'}},
            {'bundle': {'patch': '/tmp/absolute.yml'}},
            {'bundle': {'patch': './plugin.json'}},
            {'bundle': {'patch': './cordis.patch.yml', 'listedByDefault': 'yes'}},
        ):
            with self.subTest(dsh=bad_dsh):
                self.docs = copy.deepcopy(original)
                if bad_dsh is None:
                    self.docs['package.json'].pop('dsh', None)
                else:
                    self.docs['package.json']['dsh'] = bad_dsh
                self.assertTrue(self.check())

        self.docs = copy.deepcopy(original)
        with tempfile.TemporaryDirectory() as outside:
            ext_patch = Path(outside) / 'cordis.patch.yml'
            ext_patch.write_text(VALID_CORDIS_PATCH, encoding='utf-8')
            self.check()
            (self.root / 'cordis.patch.yml').unlink()
            (self.root / 'cordis.patch.yml').symlink_to(ext_patch)
            bad = []
            plugin.check_manifests(self.root, bad)
            self.assertTrue(any('dsh.bundle.patch' in b for b in bad))

    def test_dsh_package_isolation_and_whitelist_guards(self):
        original = copy.deepcopy(self.docs)
        # Workspaces, external dependencies, and install hooks must be rejected
        for field, bad_val in (
            ('description', ''),
            ('workspaces', ['apps/*']),
            ('dependencies', {'yaml': '^2.0.0'}),
            ('devDependencies', {'typescript': '^5.0.0'}),
            ('optionalDependencies', {'chokidar': '^4.0.0'}),
            ('scripts', {'postinstall': 'echo boom'}),
            ('exports', {'./cordis.patch.yml': './cordis.patch.yml'}),
            ('exports', {'./package.json': './package.json'}),
            ('files', []),
            ('files', ['.']),
            ('files', ['*']),
            ('files', ['cordis.patch.yml']),
            ('files', ['skills']),
        ):
            with self.subTest(field=field, bad_val=bad_val):
                self.docs = copy.deepcopy(original)
                self.docs['package.json'][field] = bad_val
                self.assertTrue(any('package.json' in b for b in self.check()))

        # Private/local/traversal directories must never appear in package.json files whitelist
        for forbidden in (
            'novels', 'novels/book1', 'books', '_作者', '_拆书库', 'docs/tasks', 'docs/evidence',
            'config', 'config/.env', '.env', '.env.local', 'docs/.env.production',
            '.sdlc', '.venv', 'apps/management-web', '../outside', '/tmp/abs',
        ):
            with self.subTest(forbidden=forbidden):
                self.docs = copy.deepcopy(original)
                self.docs['package.json']['files'] = ['cordis.patch.yml', 'skills', forbidden]
                self.assertTrue(any('files' in b for b in self.check()))

    def test_dsh_cordis_patch_content_counterexamples(self):
        for label, bad_patch in (
            ('empty', ''),
            ('mapping-root', 'insert:\n  - id: ncc-workflow-skills\n'),
            ('colliding-id', VALID_CORDIS_PATCH.replace('id: ncc-workflow-skills', 'id: skill-filesystem')),
            ('wrong-module', VALID_CORDIS_PATCH.replace('@deepseek-ai/dsh-skill-filesystem', '@deepseek-ai/other')),
            ('wrong-provider', VALID_CORDIS_PATCH.replace('providerName: ncc-workflow', 'providerName: filesystem')),
            ('default-roots-true', VALID_CORDIS_PATCH.replace('includeDefaultRoots: false', 'includeDefaultRoots: true')),
            ('hardcoded-dir', VALID_CORDIS_PATCH.replace(
                'bundledSkillDir: !!js "process.getBuiltinModule(\'node:path\').join(process.getBuiltinModule(\'node:path\').dirname(process.getBuiltinModule(\'node:module\').createRequire(baseUrl).resolve(\'ncc-workflow/package.json\')), \'skills\')"',
                'bundledSkillDir: ./skills',
            )),
        ):
            with self.subTest(case=label):
                self.text_files = {'cordis.patch.yml': bad_patch}
                self.assertTrue(any('cordis.patch.yml' in b for b in self.check()))


if __name__ == '__main__':
    unittest.main()
