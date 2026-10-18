"""拆书的路径、指纹、原子文件和单库互斥。"""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import tempfile
from ..core import DECON_CFG, REGISTRY, CONFIDENCE, V


class DeconError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise DeconError(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else canonical(value)).hexdigest()


def local(root, relative):
    root = Path(root).resolve()
    require(isinstance(relative, (str, Path)) and bool(str(relative)), '库内路径必须为非空字符串')
    p = Path(relative)
    require(not p.is_absolute() and '..' not in p.parts, f'非法库内路径：{relative}')
    target = root / p
    require(target.resolve().is_relative_to(root), f'输出或引用越界：{relative}')
    return target


def vocabulary_fingerprint():
    """词表和有限契约一起绑定；路径等非语义配置不使历史事实失效。"""
    contract_root = Path(__file__).resolve().parents[3] / 'workflow/contracts/deconstruction'
    return digest({'vocab': REGISTRY['vocab'], 'categories': REGISTRY['setting_categories'],
                   'enums': {k: DECON_CFG[k] for k in ('foreshadow_ops', 'descriptive_aliases', 'payoff_parts', 'int_ext')},
                   'contracts': {p.name: digest(p.read_bytes()) for p in sorted(contract_root.glob('*.json'))}})


def read(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    def unique(pairs):
        out = {}
        for k, v in pairs:
            require(k not in out, f'{path}：重复键 {k}')
            out[k] = v
        return out
    def invalid(token):
        raise DeconError(f'{path}：非法 JSON 常量 {token}')
    try:
        return json.loads(path.read_text('utf-8'), object_pairs_hook=unique, parse_constant=invalid)
    except (OSError, UnicodeError, ValueError) as exc:
        raise DeconError(f'{path}：{exc}') from exc


def atomic(path, content):
    path = Path(path)
    content = content if isinstance(content, bytes) else content.encode('utf-8')
    if path.is_file() and path.read_bytes() == content:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.decon-', suffix='.tmp')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def write(path, value):
    atomic(path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def rows(path):
    path = Path(path)
    if not path.exists():
        return []
    result = []
    for n, line in enumerate(path.read_text('utf-8').splitlines(), 1):
        if line.strip():
            try:
                value = json.loads(line)
            except ValueError as exc:
                raise DeconError(f'{path}:{n}：{exc}') from exc
            require(isinstance(value, dict), f'{path}:{n}：台账行必须为对象')
            result.append(value)
    return result


def write_rows(path, values):
    atomic(path, ''.join(json.dumps(v, ensure_ascii=False, allow_nan=False) + '\n' for v in values))


@contextlib.contextmanager
def locked(root):
    path = local(root, DECON_CFG['lock'])
    with path.open('a+b') as stream:
        if os.name == 'nt':
            import msvcrt
            stream.seek(0)
            if not stream.read(1):
                stream.write(b'0'); stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise DeconError('该拆书库已有写操作，请稍后重试') from exc
            try:
                yield
            finally:
                stream.seek(0); msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise DeconError('该拆书库已有写操作，请稍后重试') from exc
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
