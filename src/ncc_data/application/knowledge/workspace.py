"""Version-bound legacy working copies. Originals and semantic chapter projections commit together."""

import base64
import json
from pathlib import PurePosixPath
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select

from ncc_data.application.security import authorize
from ncc_data.domain.contracts import ChangeInput, Query
from ncc_data.persistence.models import Receipt
from ncc_shared.errors import DomainError, require
from ncc_shared.serialization import digest


def safe_path(value):
    p = PurePosixPath(value)
    require(
        value
        and not p.is_absolute()
        and ".." not in p.parts
        and "\\" not in value
        and not any(
            part in {".git", ".env", ".ncc-database.json", ".ncc-database-state.json"} for part in p.parts
        ),
        "workspace_path",
        "工作副本路径无效",
    )
    return p.as_posix()


class WorkspaceMixin:
    async def workspace_snapshot(self, scope_id):
        scope, actions = await authorize(self.db, self.actor, scope_id, "export")
        require("secret" in actions, "workspace_permission", "完整CLI工作副本需要秘密内容与导出权限", 403)
        files, offset, chapters = {}, 0, []
        while True:
            page = await self.entities(scope_id, Query(limit=200, offset=offset))
            for item in page["items"]:
                if item["kind"] == "legacy-file":
                    full = await self.entity(scope_id, item["id"])
                    path = full["data"]["legacy_path"]
                    if full["data"].get("attachment_id"):
                        attachment = await self.attachment(scope_id, full["data"]["attachment_id"])
                        raw = attachment.data
                    else:
                        raw = full["text"].encode("utf-8")
                    files[path] = raw
                elif item["kind"] == "chapter" and item["data"].get("legacy_path"):
                    chapters.append(await self.entity(scope_id, item["id"]))
            if page["next_offset"] is None:
                break
            offset = page["next_offset"]
        for chapter in chapters:
            files[chapter["data"]["legacy_path"]] = chapter["text"].encode()
        if "book.json" in files:
            state = json.loads(files["book.json"])
            mapped = scope.config.get("legacy_chapters", {})
            by_id = {c["id"]: c for c in chapters}
            for old in state.get("chapters", []):
                obj = by_id.get(mapped.get(str(old["seq"])))
                if obj:
                    old["seq"] = obj["data"].get("position", old["seq"])
                    old["title"] = obj["name"]
                    old["sha"] = digest(obj["text"])[:16]
                    if obj["data"].get("status"):
                        old["status"] = obj["data"]["status"]
            state["chapters"] = sorted(state.get("chapters", []), key=lambda c: c["seq"])
            files["book.json"] = (json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode()
        return {
            "format": "ncc.workspace/1",
            "version": scope.version,
            "files": [
                {"path": p, "base64": base64.b64encode(raw).decode(), "sha256": digest(raw)}
                for p, raw in sorted(files.items())
            ],
        }

    async def workspace_commit(self, scope_id, value):
        scope, actions = await authorize(self.db, self.actor, scope_id, "adopt", lock=True)
        require("secret" in actions, "workspace_permission", "CLI接入需要完整范围权限", 403)
        require(value.get("format") == "ncc.workspace/1", "workspace_format", "工作副本格式不受支持")
        key = "workspace:" + value["request_id"]
        request_hash = digest(value)
        receipt = await self.db.scalar(
            select(Receipt).where(
                Receipt.scope_id == scope_id, Receipt.actor_id == self.actor.id, Receipt.key == key
            )
        )
        if receipt:
            require(
                receipt.request_hash == request_hash, "idempotency_reuse", "工作副本幂等键已用于不同内容", 409
            )
            return receipt.result
        require(
            value.get("base_version") == scope.version,
            "version_conflict",
            "数据库已有新变化，工作副本须三方比较",
            409,
        )
        require(
            isinstance(value.get("files"), list) and 0 < len(value["files"]) <= 200,
            "workspace_size",
            "每批1至200个文件",
        )
        current = await self.workspace_snapshot(scope_id)
        old_files = {x["path"]: base64.b64decode(x["base64"]) for x in current["files"]}
        raw_files, operations = dict(old_files), []
        for item in value["files"]:
            path = safe_path(item.get("path", ""))
            if item.get("deleted"):
                raw_files.pop(path, None)
            else:
                try:
                    raw = base64.b64decode(item["base64"], validate=True)
                except (ValueError, KeyError):
                    raise DomainError("workspace_encoding", "文件编码无效") from None
                require(
                    len(raw) <= 16 * 1024 * 1024,
                    "workspace_size",
                    "单个工作副本文件超过16MiB，请通过受管附件导入",
                )
                require(digest(raw) == item.get("sha256"), "workspace_digest", "工作副本内容摘要不符")
                raw_files[path] = raw
            identity = str(uuid5(NAMESPACE_URL, scope.id + ":file:" + path))
            previous = None
            try:
                previous = await self.entity(scope_id, identity, Query(include_deleted=True))
            except DomainError as exc:
                if exc.status != 404:
                    raise
            if item.get("deleted"):
                if previous and not previous.get("deleted"):
                    operations.append(
                        {"op": "retire", "entity_id": identity, "expected": previous["version"]}
                    )
                continue
            try:
                content = raw.decode("utf-8")
                binary = len(content) > 2_000_000
            except UnicodeError:
                content, binary = "", True
            data = {
                "legacy_path": path,
                "encoding": "binary" if binary else "utf-8",
                "content_hash": digest(raw),
            }
            if binary:
                saved = await self.upload(scope_id, PurePosixPath(path).name, "application/octet-stream", raw)
                data["attachment_id"] = saved["id"]
                content = ""
            operation = {
                "op": "update" if previous else "create",
                "entity_id": identity,
                "kind": "legacy-file",
                "name": path,
                "data": data,
                "text": content,
            }
            if previous:
                operation["expected"] = previous["version"]
                operation["reactivate"] = bool(previous.get("deleted"))
            operations.append(operation)
        # Typed narrative identities and text are projected from legacy metadata. Unknown files remain exact originals.
        legacy = json.loads(raw_files.get("book.json", b"{}"))
        mapping = dict(scope.config.get("legacy_chapters", {}))
        existing = {
            c["data"]["legacy_path"]: c
            for c in await self.all_entities(scope_id, include_deleted=True)
            if c["kind"] == "chapter" and c["data"].get("legacy_path")
        }
        declared = {c.get("file") for c in legacy.get("chapters", [])}
        metadata_changed = any(i["path"] == "book.json" for i in value["files"])
        for path, old in existing.items():
            explicitly_deleted = path in {i["path"] for i in value["files"] if i.get("deleted")}
            if not old.get("deleted") and (explicitly_deleted or (metadata_changed and path not in declared)):
                operations.append({"op": "retire", "entity_id": old["id"], "expected": old["version"]})
        if metadata_changed:
            mapping = {}
        changed_paths = {i["path"] for i in value["files"]}
        for chapter in legacy.get("chapters", []):
            path = safe_path(chapter.get("file", "")) if chapter.get("file") else None
            if not path or path not in raw_files or (path not in changed_paths and not metadata_changed):
                continue
            old = existing.get(path)
            eid = (
                old["id"]
                if old
                else mapping.get(str(chapter["seq"]))
                or str(uuid5(NAMESPACE_URL, scope.id + ":chapter-path:" + path))
            )
            mapping[str(chapter["seq"])] = eid
            try:
                old = await self.entity(scope_id, eid, Query(include_deleted=True))
            except DomainError as exc:
                if exc.status != 404:
                    raise
                old = None
            try:
                text = raw_files[path].decode("utf-8-sig")
            except UnicodeError:
                raise DomainError("chapter_encoding", "章节正文必须是UTF-8文本") from None
            data = {"position": chapter["seq"], "legacy_path": path, "status": chapter.get("status", "draft")}
            name = chapter.get("title") or f"第{chapter['seq']}章"
            if (
                old
                and not old.get("deleted")
                and old["name"] == name
                and old["text"] == text
                and all(old["data"].get(k) == v for k, v in data.items())
            ):
                continue
            operation = {
                "op": "update" if old else "create",
                "entity_id": eid,
                "kind": "chapter",
                "name": name,
                "data": data,
                "text": text,
            }
            if old:
                operation["expected"] = old["version"]
                operation["reactivate"] = bool(old.get("deleted"))
            operations.append(operation)
        scope.config = {**scope.config, "legacy_chapters": mapping}
        require(len(operations) <= 500, "workspace_size", "语义变化超过单批预算，请拆分文件批次")
        if not operations:
            return {"version": scope.version, "unchanged": True}
        change = await self.create_change(
            scope_id,
            ChangeInput(
                title=value.get("title", "CLI工作副本受控回写")[:256],
                base_version=scope.version,
                operations=operations,
            ),
        )
        result = await self.adopt(scope_id, change["id"], value.get("request_id") or change["id"])
        response = {
            **result,
            "coverage": {
                "raw_files": len(raw_files),
                "typed_chapters": len(mapping),
                "other_semantics": "原件保留；专业领域通过定义和关系接口维护，不将原件保存冒充全部语义迁移",
            },
        }
        self.db.add(
            Receipt(
                scope_id=scope_id, actor_id=self.actor.id, key=key, request_hash=request_hash, result=response
            )
        )
        return response
