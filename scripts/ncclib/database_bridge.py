"""Stdlib-only database working-copy adapter, activated only by an explicit private marker."""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4

MARKER = '.ncc-database.json'
STATE = '.ncc-database-state.json'


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def marker_root(path):
    p = Path(path).expanduser().resolve()
    if p.is_file():
        p = p.parent
    for candidate in (p, *p.parents):
        if (candidate / MARKER).is_file():
            return candidate
    return None


def invoke(script, argv, root):
    marker = json.loads((root / MARKER).read_text('utf-8'))
    origin = os.environ.get('NCC_API_URL', 'http://127.0.0.1:8787').rstrip('/')
    if marker.get('api_url', '').rstrip('/') != origin:
        raise ValueError('工作副本的API地址与明确配置不符；拒绝向资料指定的地址发送凭据')
    parsed = urlsplit(origin)
    if parsed.scheme != 'https' and parsed.hostname not in {'127.0.0.1', 'localhost', '::1'}:
        raise ValueError('远端API必须使用HTTPS')
    token = os.environ.get('NCC_API_TOKEN')
    if not token:
        raise ValueError('数据库范围需要私有环境中的NCC_API_TOKEN；不会回退文件写入')
    prefix = '/api/v1/scopes/' + marker['scope_id'] + '/workspace'
    opener = build_opener(NoRedirect)
    def request(method, suffix='', value=None):
        body = json.dumps(value, ensure_ascii=False).encode() if value is not None else None
        req = Request(origin + prefix + suffix, data=body, method=method,
                      headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
        try:
            with opener.open(req, timeout=180) as response:
                return json.load(response)
        except HTTPError as exc:
            problem = json.load(exc)
            raise ValueError(problem.get('detail', '数据库应用接口失败')) from None
    snapshot = request('GET')
    baseline = json.loads((root / STATE).read_text('utf-8')) if (root / STATE).exists() else None
    if baseline is None:
        raise ValueError('工作副本缺少版本基线，请用 ncc-data workspace bind 显式对账')
    def scan(directory):
        result = {}
        for path in directory.rglob('*'):
            rel = path.relative_to(directory)
            if any(part in {MARKER, STATE, '.git', '.env'} for part in rel.parts):
                continue
            if path.is_symlink():
                raise ValueError('受控工作副本包含未授权软链：' + str(rel))
            if path.is_file():
                result[rel.as_posix()] = path.read_bytes()
        return result
    remote = {i['path']: base64.b64decode(i['base64']) for i in snapshot['files']}
    local = scan(root)
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
        after = scan(work)
        updates = []
        for p in sorted(set(remote) | set(after)):
            if remote.get(p) != after.get(p) or p in changed:
                item = {'path': p, 'deleted': p not in after}
                if p in after:
                    item.update(base64=base64.b64encode(after[p]).decode(), sha256=digest(after[p]))
                updates.append(item)
        if updates:
            if scan(root) != local:
                raise ValueError('命令运行期间作者又修改了工作副本；原稿保留，未采用旧任务结果，请重新比较')
            if len(updates) > 200 or sum(len(i.get('base64', '')) for i in updates) > 18 * 1024 * 1024:
                raise ValueError('单次CLI变化超过事务预算，结果未采用；请分批操作，原工作副本未覆盖')
            request('POST', '/commit', {'format': 'ncc.workspace/1', 'base_version': snapshot['version'],
                'files': updates, 'request_id': str(uuid4()), 'title': 'CLI: ' + ' '.join(argv[:2])})
        fresh = request('GET')
        if scan(root) != local:
            raise ValueError('数据库已保存命令结果，但本地出现新编辑；保留本地原稿，请三方比较后pull，不自动覆盖')
        hashes = {}
        remote_paths = {x['path'] for x in fresh['files']}
        for item in fresh['files']:
            target = root / item['path']
            if target.is_symlink():
                raise ValueError('拒绝覆盖本地软链')
            target.parent.mkdir(parents=True, exist_ok=True)
            raw = base64.b64decode(item['base64'])
            target.write_bytes(raw)
            hashes[item['path']] = digest(raw)
        for path in set(baseline['hashes']) - remote_paths:
            target = root / path
            if target.is_file() and not target.is_symlink():
                target.unlink()
        (root / STATE).write_text(json.dumps({'version': fresh['version'], 'hashes': hashes}, ensure_ascii=False))
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
