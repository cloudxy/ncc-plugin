"""Working-copy format and file operations shared by both CLI entry paths."""

import base64
import json
import os
import tempfile
from pathlib import Path

from .serialization import digest

MARKER = ".ncc-database.json"
STATE = ".ncc-database-state.json"
PRIVATE_PARTS = {MARKER, STATE, ".git", ".ncc-conflicts"}


def metadata_path(root, name):
    if name not in {MARKER, STATE}:
        raise ValueError("不支持的工作副本元数据")
    path = Path(root) / name
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("工作副本元数据不能是软链或目录")
    return path


def read_metadata(root, name, default=None):
    path = metadata_path(root, name)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write_metadata(root, name, value):
    path = metadata_path(root, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def scan_files(root):
    root = Path(root)
    for name in (STATE, MARKER):
        metadata_path(root, name)
    result = {}
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if any(part in PRIVATE_PARTS or part.startswith(".env") for part in rel.parts):
            continue
        if path.is_symlink():
            raise ValueError("受控工作副本包含未授权软链：" + str(rel))
        if path.is_file():
            result[rel.as_posix()] = path.read_bytes()
    return result


def write_snapshot(root, snapshot, previous_paths=()):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    for name in (STATE, MARKER):
        metadata_path(root, name)
    previous_paths = tuple(previous_paths)
    hashes = {}

    def target(name):
        if not isinstance(name, str) or name in {"", "."}:
            raise ValueError("工作副本路径必须是非空相对文件路径")
        path = Path(name)
        if (
            path.is_absolute()
            or ".." in path.parts
            or any(p in PRIVATE_PARTS or p.startswith(".env") for p in path.parts)
        ):
            raise ValueError("服务端返回非法工作副本路径")
        result = root / path
        if result.is_symlink() or not result.resolve().is_relative_to(root):
            raise ValueError("拒绝通过软链覆盖工作副本")
        return result

    previous = {name: target(name) for name in previous_paths}
    prepared = []
    for item in snapshot["files"]:
        path = target(item["path"])
        if item["path"] in hashes:
            raise ValueError("工作副本快照包含重复路径")
        raw = base64.b64decode(item["base64"], validate=True)
        if digest(raw) != item["sha256"]:
            raise ValueError("工作副本摘要不符")
        hashes[item["path"]] = item["sha256"]
        prepared.append((path, raw))
    for path, raw in prepared:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    for name in set(previous_paths) - set(hashes):
        path = previous[name]
        if path.is_file():
            path.unlink()
    write_metadata(root, STATE, {"version": snapshot["version"], "hashes": hashes})
