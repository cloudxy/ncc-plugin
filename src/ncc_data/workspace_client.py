import base64
import json
import os
from pathlib import Path
from uuid import uuid4

from .cli import http_request, repo_root
from .utils import digest

MARKER = ".ncc-database.json"
STATE = ".ncc-database-state.json"


def permitted_root(directory):
    directory = directory.expanduser().resolve()
    root = repo_root()
    if directory.is_relative_to(root) and not any(
        directory.is_relative_to(root / name) for name in ("novels", "books", "_作者", "_拆书库")
    ):
        raise ValueError("受控创作工作副本不能放进插件受管目录，请使用私有书库或仓外目录")
    return directory


def local_files(root):
    result = {}
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if any(p in {".git", ".env", MARKER, STATE, ".ncc-conflicts"} for p in rel.parts):
            continue
        if path.is_symlink():
            raise ValueError("工作副本包含软链，请先显式处理：" + str(rel))
        if path.is_file():
            result[rel.as_posix()] = path.read_bytes()
    return result


def write_snapshot(root, snapshot):
    root.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for item in snapshot["files"]:
        path = Path(item["path"])
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("服务端返回了无效工作副本路径")
        target = root / path
        if target.is_symlink():
            raise ValueError("拒绝覆盖工作副本软链")
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = base64.b64decode(item["base64"], validate=True)
        if digest(raw) != item["sha256"]:
            raise ValueError("工作副本摘要不符")
        target.write_bytes(raw)
        hashes[item["path"]] = item["sha256"]
    (root / STATE).write_text(
        json.dumps({"version": snapshot["version"], "hashes": hashes}, ensure_ascii=False)
    )


def manage(action, directory, scope_id):
    root = permitted_root(directory)
    prefix = f"/scopes/{scope_id}/workspace"
    if action == "import":
        files = local_files(root)
        names = sorted(files, key=lambda name: (name != "book.json", name))
        version = http_request("GET", f"/scopes/{scope_id}")["version"]
        # Bounded by both bytes and operation count; activation is a separate explicit action.
        batch, size = [], 0
        for name in names:
            raw = files[name]
            if len(raw) > 12 * 1024 * 1024:
                raise ValueError("大文件请先通过受管附件导入；本轮工作副本文件未截断：" + name)
            item = {"path": name, "base64": base64.b64encode(raw).decode(), "sha256": digest(raw)}
            if batch and (len(batch) >= 100 or size + len(item["base64"]) > 12 * 1024 * 1024):
                version = http_request(
                    "POST",
                    prefix + "/commit",
                    {
                        "format": "ncc.workspace/1",
                        "base_version": version,
                        "files": batch,
                        "request_id": str(uuid4()),
                        "title": "影子导入工作副本",
                    },
                )["version"]
                batch, size = [], 0
            batch.append(item)
            size += len(item["base64"])
        if batch:
            version = http_request(
                "POST",
                prefix + "/commit",
                {
                    "format": "ncc.workspace/1",
                    "base_version": version,
                    "files": batch,
                    "request_id": str(uuid4()),
                    "title": "影子导入工作副本",
                },
            )["version"]
        print(
            f"影子导入完成，版本{version}；原文件未切换。章节有类型化映射，其他原件的语义覆盖请按回执核对。"
        )
    elif action == "bind":
        snapshot = http_request("GET", prefix)
        if not snapshot["files"]:
            raise ValueError("数据库还没有工作副本内容，请先完成影子导入与对账")
        local = local_files(root) if root.exists() else {}
        remote = {i["path"]: base64.b64decode(i["base64"]) for i in snapshot["files"]}
        conflicts = [p for p, raw in local.items() if p not in remote or raw != remote[p]]
        if conflicts:
            raise ValueError("绑定前本地与数据库存在差异，拒绝覆盖：" + ", ".join(conflicts[:10]))
        write_snapshot(root, snapshot)
        (root / MARKER).write_text(
            json.dumps(
                {
                    "schema": 1,
                    "scope_id": scope_id,
                    "api_url": os.environ.get("NCC_API_URL", "http://127.0.0.1:8787"),
                },
                ensure_ascii=False,
            )
        )
        print("已显式绑定数据库权威范围；凭据只从私有环境读取，原文件保留为受控工作副本。")
    else:
        snapshot = http_request("GET", prefix)
        baseline = json.loads((root / STATE).read_text()) if (root / STATE).exists() else {"hashes": {}}
        local = local_files(root) if root.exists() else {}
        changed = [
            p
            for p in set(local) | set(baseline["hashes"])
            if (digest(local[p]) if p in local else None) != baseline["hashes"].get(p)
        ]
        if changed:
            raise ValueError(
                "存在尚未采用的本地修改，请先经CLI回写或比较，拒绝覆盖：" + ", ".join(changed[:10])
            )
        write_snapshot(root, snapshot)
        remote_names = {item["path"] for item in snapshot["files"]}
        for name in set(baseline["hashes"]) - remote_names:
            target = root / name
            if target.is_file() and not target.is_symlink():
                target.unlink()
        print("已从数据库更新受控工作副本。")
