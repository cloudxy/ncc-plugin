#!/usr/bin/env python3
"""从受管分片原子生成 registry.json；--check 只读验证生成物。"""
import argparse
import os
from pathlib import Path
import stat
import sys
import tempfile

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_ROOT))
from ncclib.registry import RegistryError, merge_registry, registry_path, serialize_registry

ROOT = SCRIPTS_ROOT.parent


def build(root, check=False):
    target = registry_path(root)
    text = serialize_registry(merge_registry(root))
    if target.is_file() and target.read_bytes() == text.encode('utf-8'):
        print('REGISTRY OK')
        return 0
    if check:
        print(f'{target}: 聚合视图陈旧；运行 python3 scripts/dev/build_registry.py', file=sys.stderr)
        return 1
    mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else 0o644
    fd, name = tempfile.mkstemp(prefix='.registry-', suffix='.tmp', dir=target.parent)
    temp = Path(name)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)
    print(f'已更新 {target}')
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    try:
        return build(ROOT, args.check)
    except (RegistryError, OSError, ValueError) as exc:
        print(f'REGISTRY FAILED: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
