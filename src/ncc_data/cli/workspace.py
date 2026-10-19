import base64
from uuid import uuid4

from ncc_shared.http import APIClient
from ncc_shared.paths import project_root as repo_root
from ncc_shared.serialization import digest
from ncc_shared.workspace import MARKER, STATE, read_metadata, scan_files, write_metadata, write_snapshot


def permitted_root(directory):
    directory = directory.expanduser().resolve()
    root = repo_root()
    if directory.is_relative_to(root) and not any(
        directory.is_relative_to(root / name) for name in ("novels", "books", "_作者", "_拆书库")
    ):
        raise ValueError("受控创作工作副本不能放进插件受管目录，请使用私有书库或仓外目录")
    return directory


def manage(action, directory, scope_id, values=None):
    root = permitted_root(directory)
    client = APIClient(values)
    http_request = client.request
    prefix = f"/scopes/{scope_id}/workspace"
    if action == "import":
        files = scan_files(root)
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
        local = scan_files(root) if root.exists() else {}
        remote = {i["path"]: base64.b64decode(i["base64"]) for i in snapshot["files"]}
        conflicts = [p for p, raw in local.items() if p not in remote or raw != remote[p]]
        if conflicts:
            raise ValueError("绑定前本地与数据库存在差异，拒绝覆盖：" + ", ".join(conflicts[:10]))
        write_snapshot(root, snapshot)
        write_metadata(
            root,
            MARKER,
            {
                "schema": 1,
                "scope_id": scope_id,
                "api_url": client.origin,
                "profile": client.profile,
            },
        )
        print("已显式绑定数据库权威范围；凭据从config/.env读取，原文件保留为受控工作副本。")
    else:
        snapshot = http_request("GET", prefix)
        baseline = read_metadata(root, STATE, {"hashes": {}})
        local = scan_files(root) if root.exists() else {}
        changed = [
            p
            for p in set(local) | set(baseline["hashes"])
            if (digest(local[p]) if p in local else None) != baseline["hashes"].get(p)
        ]
        if changed:
            raise ValueError(
                "存在尚未采用的本地修改，请先经CLI回写或比较，拒绝覆盖：" + ", ".join(changed[:10])
            )
        write_snapshot(root, snapshot, baseline["hashes"])
        print("已从数据库更新受控工作副本。")
