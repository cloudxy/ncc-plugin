"""Stdlib-only database working-copy adapter, activated only by an explicit private marker."""
import base64
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

from ncc_shared.http import APIClient
from ncc_shared.runtime import ensure_data_runtime
from ncc_shared.serialization import digest
from ncc_shared.workspace import MARKER, STATE, metadata_path, read_metadata, scan_files, write_snapshot


def marker_root(path):
    p = Path(path).expanduser().resolve()
    if p.is_file():
        p = p.parent
    for candidate in (p, *p.parents):
        if metadata_path(candidate, MARKER).is_file():
            return candidate
    return None


def invoke(script, argv, root):
    ensure_data_runtime(script, argv)
    marker = read_metadata(root, MARKER)
    client = APIClient(timeout=180)
    if marker.get('api_url', '').rstrip('/') != client.origin:
        raise ValueError('工作副本API地址与config/.env不符；拒绝向资料指定的地址发送凭据')
    if marker.get('profile', 'production') != client.profile:
        raise ValueError('工作副本的正式/测试模式与项目配置不一致')
    prefix = '/scopes/' + marker['scope_id'] + '/workspace'
    def request(method, suffix='', value=None):
        return client.request(method, prefix + suffix, value)
    snapshot = request('GET')
    baseline = read_metadata(root, STATE)
    if baseline is None:
        raise ValueError('工作副本缺少版本基线，请用 ncc-data workspace bind 显式对账')
    remote = {i['path']: base64.b64decode(i['base64']) for i in snapshot['files']}
    local = scan_files(root)
    changed = {p for p in set(local) | set(baseline['hashes']) if (digest(local[p]) if p in local else None) != baseline['hashes'].get(p)}
    conflicts = [p for p in changed if (digest(remote[p]) if p in remote else None) != baseline['hashes'].get(p)]
    if conflicts:
        raise ValueError('本地编辑与数据库同处修改，已保留原稿，需三方比较：' + ', '.join(conflicts[:10]))
    for p in changed:
        if p in local:
            remote[p] = local[p]
        else:
            remote.pop(p, None)
    with tempfile.TemporaryDirectory(prefix='ncc-db-command-') as temporary:
        work = Path(temporary) / 'book'
        work.mkdir()
        for name, raw in remote.items():
            rel = Path(name)
            if rel.is_absolute() or '..' in rel.parts:
                raise ValueError('API返回非法路径')
            target = work / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        mapped = []
        for arg in argv:
            if arg.startswith('-'):
                mapped.append(arg)
                continue
            candidate = Path(arg).expanduser()
            resolved = candidate.resolve()
            mapped.append(str(work / resolved.relative_to(root)) if resolved.is_relative_to(root) else arg)
        env = dict(os.environ, NCC_DATABASE_BRIDGE_ACTIVE='1')
        proc = subprocess.run([sys.executable, str(script), *mapped], cwd=work, env=env, capture_output=True)
        sys.stdout.write(proc.stdout.decode('utf-8', errors='replace').replace(str(work), str(root)))
        sys.stderr.write(proc.stderr.decode('utf-8', errors='replace').replace(str(work), str(root)))
        if proc.returncode:
            return proc.returncode
        after = scan_files(work)
        updates = []
        for p in sorted(set(remote) | set(after)):
            if remote.get(p) != after.get(p) or p in changed:
                item = {'path': p, 'deleted': p not in after}
                if p in after:
                    item.update(base64=base64.b64encode(after[p]).decode(), sha256=digest(after[p]))
                updates.append(item)
        if updates:
            if scan_files(root) != local:
                raise ValueError('命令运行期间作者又修改了工作副本；原稿保留，未采用旧任务结果，请重新比较')
            if len(updates) > 200 or sum(len(i.get('base64', '')) for i in updates) > 18 * 1024 * 1024:
                raise ValueError('单次CLI变化超过事务预算，结果未采用；请分批操作，原工作副本未覆盖')
            request('POST', '/commit', {'format': 'ncc.workspace/1', 'base_version': snapshot['version'],
                'files': updates, 'request_id': str(uuid4()), 'title': 'CLI: ' + ' '.join(argv[:2])})
        fresh = request('GET')
        if scan_files(root) != local:
            raise ValueError('数据库已保存命令结果，但本地出现新编辑；保留本地原稿，请三方比较后pull，不自动覆盖')
        write_snapshot(root, fresh, baseline['hashes'])
    return 0


def dispatch(script, argv, paths):
    if os.environ.get('NCC_DATABASE_BRIDGE_ACTIVE') == '1':
        return None
    roots = {marker_root(path) for path in paths if path is not None}
    roots.discard(None)
    if not roots:
        return None
    if len(roots) != 1:
        raise ValueError('一个CLI事务不能跨多个数据库权威范围，请分别操作')
    return invoke(script, argv, roots.pop())
