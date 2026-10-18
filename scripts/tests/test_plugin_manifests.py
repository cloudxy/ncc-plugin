"""打包清单跨格式一致性与坏输入反例。"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_ROOT))

from dev import check_plugin as plugin


class ManifestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for directory in ('skills', 'commands', 'agents'):
            (self.root / directory).mkdir()
        self.docs = {
            'plugin.json': {'name': 'ncc-workflow', 'version': '3.2.0'},
            '.zcode-plugin/plugin.json': {'name': 'ncc-workflow', 'version': '3.2.0',
                                        'skills': 'skills', 'commands': 'commands', 'agents': 'agents'},
            '.claude-plugin/plugin.json': {'name': 'ncc-workflow', 'version': '3.2.0'},
            '.claude-plugin/marketplace.json': {'name': 'different-market', 'plugins': [
                {'name': 'other-plugin'}, {'name': 'ncc-workflow', 'version': '3.2.0', 'source': './'}]},
            '.agents/plugins/marketplace.json': {'name': 'codex-market', 'plugins': [
                {'name': 'ncc-workflow', 'source': {'source': 'local', 'path': './'}}]},
        }

    def check(self):
        for path, doc in self.docs.items():
            p = self.root / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(doc))
        bad = []
        plugin.check_manifests(self.root, bad)
        return bad

    def test_different_market_names_order_and_no_codex_version(self):
        self.assertEqual(self.check(), [])

    def test_name_and_version_drift(self):
        original = copy.deepcopy(self.docs)
        for path in ('plugin.json', '.claude-plugin/plugin.json'):
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
                        p.write_text(raw)
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


if __name__ == '__main__':
    unittest.main()
