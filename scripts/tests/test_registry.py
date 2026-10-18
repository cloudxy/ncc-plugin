"""分片注册表的单源、坏输入、生成与中断保护。"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SCRIPTS_ROOT.parent
sys.path.insert(0, str(SCRIPTS_ROOT))
from ncclib import registry
from dev import build_registry


class RegistryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        shutil.copytree(REPO_ROOT / 'workflow', self.root / 'workflow')
        self.view = self.root / 'workflow/registry.json'
        self.directory = self.root / 'workflow/registry'

    def change(self, name='flow.json'):
        path = self.directory / name
        return path, json.loads(path.read_text())

    def test_object_types_and_recursive_order_match_original_view(self):
        data = registry.load_registry(self.root)
        self.assertEqual(registry.serialize_registry(data), self.view.read_text())
        self.assertEqual(tuple(data), registry.KEY_ORDER)
        self.assertEqual(data['schema_version'], 2)
        from ncclib.core import REGISTRY, SCHEMA
        import ncc_prepare
        self.assertEqual(REGISTRY, data)
        self.assertEqual(ncc_prepare.SPEC, data['preparation'])
        self.assertEqual(SCHEMA, 4)

    def test_missing_directory_does_not_fall_back_to_view(self):
        shutil.rmtree(self.directory)
        with self.assertRaisesRegex(registry.RegistryError, '分片目录'):
            registry.load_registry(self.root)

    def test_missing_shard(self):
        (self.directory / 'roles.json').unlink()
        with self.assertRaisesRegex(registry.RegistryError, 'roles.json'):
            registry.load_registry(self.root)

    def test_unknown_shard(self):
        (self.directory / 'unexpected.json').write_text('{}')
        with self.assertRaisesRegex(registry.RegistryError, '未知分片'):
            registry.load_registry(self.root)

    def test_bad_json_and_root_types(self):
        path, _ = self.change()
        for text in ('{', '[]', 'null', '"text"', '{"schema_version":NaN}'):
            path.write_text(text)
            with self.subTest(text=text), self.assertRaisesRegex(registry.RegistryError, 'flow.json'):
                registry.load_registry(self.root)

    def test_duplicate_keys_including_nested_objects(self):
        path, _ = self.change()
        for text in ('{"stages":1,"stages":2}', '{"stages":{"x":1,"x":2}}'):
            path.write_text(text)
            with self.subTest(text=text), self.assertRaisesRegex(registry.RegistryError, '重复 JSON 键'):
                registry.load_registry(self.root)

    def test_wrong_owner_and_cross_shard_duplicate_rejected(self):
        path, data = self.change('roles.json')
        data['stages'] = []
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(registry.RegistryError, '归属错误'):
            registry.load_registry(self.root)

    def test_missing_key(self):
        path, data = self.change()
        del data['gates']
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(registry.RegistryError, 'gates'):
            registry.load_registry(self.root)

    def test_stale_or_reordered_view_and_check_do_not_write(self):
        data = json.loads(self.view.read_text())
        self.view.write_text(registry.serialize_registry(dict(reversed(list(data.items())))))
        before = self.view.read_bytes()
        with self.assertRaisesRegex(registry.RegistryError, '聚合视图陈旧'):
            registry.load_registry(self.root)
        self.assertEqual(build_registry.build(self.root, check=True), 1)
        self.assertEqual(self.view.read_bytes(), before)

    def test_missing_or_malformed_view_can_be_rebuilt_idempotently(self):
        for text in (None, '{', b'\xff\xfe'):
            if text is None:
                self.view.unlink()
            elif isinstance(text, bytes):
                self.view.write_bytes(text)
            else:
                self.view.write_text(text)
            with self.assertRaises(registry.RegistryError):
                registry.load_registry(self.root)
            self.assertEqual(build_registry.build(self.root), 0)
            before = self.view.stat().st_mtime_ns
            self.assertEqual(build_registry.build(self.root), 0)
            self.assertEqual(self.view.stat().st_mtime_ns, before)
            self.assertEqual(build_registry.build(self.root, check=True), 0)

    def test_noncanonical_line_endings_are_stale_and_repaired(self):
        canonical = self.view.read_bytes()
        self.view.write_bytes(canonical.replace(b'\n', b'\r\n'))
        with self.assertRaisesRegex(registry.RegistryError, '聚合视图陈旧'):
            registry.load_registry(self.root)
        self.assertEqual(build_registry.build(self.root, check=True), 1)
        self.assertEqual(build_registry.build(self.root), 0)
        self.assertEqual(self.view.read_bytes(), canonical)

    def test_view_duplicate_and_nonobject_rejected(self):
        for text in ('[]', '{"a":1,"a":2}'):
            self.view.write_text(text)
            with self.assertRaises(registry.RegistryError):
                registry.load_registry(self.root)

    def test_replace_failure_keeps_old_view_and_cleans_temporary_file(self):
        path, data = self.change()
        data['schema_version'] = 3
        path.write_text(json.dumps(data))
        before = self.view.read_bytes()
        existing = sorted(p.name for p in self.view.parent.iterdir())
        with patch('dev.build_registry.os.replace', side_effect=PermissionError('injected replace failure')):
            with self.assertRaises(PermissionError):
                build_registry.build(self.root)
        self.assertEqual(self.view.read_bytes(), before)
        self.assertEqual(sorted(p.name for p in self.view.parent.iterdir()), existing)

    def test_external_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            path = self.directory / 'roles.json'
            target = Path(outside) / 'roles.json'
            shutil.copy2(path, target)
            path.unlink()
            path.symlink_to(target)
            with self.assertRaisesRegex(registry.RegistryError, '越界'):
                registry.load_registry(self.root)

    def test_runtime_startup_rejects_stale_view_before_dispatch(self):
        shutil.copytree(SCRIPTS_ROOT, self.root / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
        self.view.write_text('{}')
        p = subprocess.run([sys.executable, str(self.root / 'scripts/ncc_state.py'), '--help'],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 1)
        self.assertIn('registry.json', p.stderr)
        self.assertNotIn('usage:', p.stdout)


if __name__ == '__main__':
    unittest.main()
