"""Private staged interchange. PostgreSQL backups are separate from portable content export."""

import base64
import csv
import io
import json
from pathlib import PurePosixPath
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select

from .contracts import ChangeInput, Query, StateQuery
from .errors import DomainError, require
from .models import Attachment, ImportRun, Job, Revision
from .security import authorize
from .utils import canonical, digest


class ExchangeMixin:
    async def upload(self, scope_id, name, media_type, data, purpose="source", limit=20 * 1024 * 1024):
        _, actions = await authorize(
            self.db, self.actor, scope_id, "export" if purpose == "export" else "edit"
        )
        require(len(data) <= limit, "upload_size", "附件超过允许大小", 413)
        name = PurePosixPath(name.replace("\\", "/")).name[:256]
        require(name and "\r" not in name and "\n" not in name, "filename", "文件名无效")
        row = Attachment(
            scope_id=scope_id,
            actor_id=self.actor.id,
            name=name,
            media_type=media_type[:128],
            digest=digest(data),
            data=data,
            purpose=purpose,
            requires_secret="secret" in actions,
        )
        self.db.add(row)
        await self.db.flush()
        return {"id": row.id, "name": row.name, "size": len(data), "digest": row.digest}

    async def attachment(self, scope_id, attachment_id, action="export"):
        _, actions = await authorize(self.db, self.actor, scope_id, action)
        row = await self.db.get(Attachment, attachment_id)
        require(row and row.scope_id == scope_id, "not_found", "附件不存在或不可访问", 404)
        require(not row.requires_secret or "secret" in actions, "not_found", "附件不存在或不可访问", 404)
        return row

    async def preflight_import(self, scope_id, attachment_id, mapping):
        scope, import_actions = await authorize(self.db, self.actor, scope_id, "edit")
        require(
            "secret" in import_actions,
            "import_permission",
            "完整导入需秘密内容权限；公开资料可通过普通变更维护",
            403,
        )
        source = await self.attachment(scope_id, attachment_id, "edit")
        try:
            raw = source.data.decode("utf-8-sig")
            if source.name.lower().endswith(".csv"):
                rows = list(csv.DictReader(io.StringIO(raw)))
                wrapper = {}
            elif source.name.lower().endswith(".jsonl"):
                rows, wrapper = [json.loads(line) for line in raw.splitlines() if line.strip()], {}
            elif source.name.lower().endswith((".md", ".txt")):
                rows, wrapper = (
                    [{"name": source.name, "kind": mapping.get("kind", "source"), "text": raw}],
                    {},
                )
            else:
                value = json.loads(raw)
                wrapper = value if isinstance(value, dict) else {}
                rows = value.get("entities", []) if isinstance(value, dict) else value
            require(
                isinstance(rows, list) and 0 < len(rows) <= 50000, "import_format", "导入需包含1至50000条记录"
            )
        except (UnicodeError, ValueError, RecursionError, TypeError):
            raise DomainError("import_parse", "导入文件编码、格式或嵌套深度无效") from None
        allowed_wrapper = {
            "format",
            "entities",
            "facts",
            "definitions",
            "history",
            "attachments",
            "manifest",
            "scope",
            "audit",
        }
        unknown = sorted(set(wrapper) - allowed_wrapper)
        plan = {
            "rows": [],
            "errors": [],
            "warnings": [],
            "definitions": wrapper.get("definitions", []),
            "facts": wrapper.get("facts", []),
            "source_digest": source.digest,
            "unknown_top_level": unknown,
            "history_archived": bool(wrapper.get("history")),
            "attachments_archived": bool(wrapper.get("attachments")),
        }
        row = ImportRun(
            scope_id=scope_id,
            actor_id=self.actor.id,
            attachment_id=source.id,
            base_version=scope.version,
            mapping=mapping,
            plan={},
        )
        self.db.add(row)
        await self.db.flush()
        for value in wrapper.get("definitions", []):
            if value.get("scope_id") == "00000000-0000-0000-0000-000000000001":
                continue
            require(
                isinstance(value, dict) and "key" in value and "spec" in value, "definition", "定义包格式无效"
            )
            existing = (
                await self.definition(scope, value["key"])
                if value["key"] in {d["key"] for d in await self.definitions(scope_id)}
                else None
            )
            if existing and existing.spec == value["spec"]:
                continue
            plan["rows"].append(
                {
                    "op": "definition",
                    "definition": {
                        "key": value["key"],
                        "version": (existing.version + 1) if existing else 1,
                        "spec": value["spec"],
                    },
                }
            )
        attachment_map = {}
        for item in wrapper.get("attachments", []):
            require(isinstance(item, dict), "attachment", "附件格式无效")
            try:
                data = base64.b64decode(item["base64"], validate=True)
            except (KeyError, ValueError):
                raise DomainError("attachment", "附件编码无效") from None
            require(digest(data) == item.get("digest"), "attachment_digest", "附件摘要不符")
            saved = await self.upload(
                scope_id, item.get("name", "source"), item.get("media_type", "application/octet-stream"), data
            )
            attachment_map[item["id"]] = saved["id"]
        id_map = {
            str(v.get("id", i)): str(uuid5(NAMESPACE_URL, row.id + ":" + str(v.get("id", i))))
            for i, v in enumerate(rows)
            if isinstance(v, dict)
        }
        definitions = {d["key"]: d for d in await self.definitions(scope_id)}
        definitions.update({d["key"]: d for d in wrapper.get("definitions", [])})
        for i, value in enumerate(rows):
            if not isinstance(value, dict):
                plan["errors"].append({"row": i + 1, "detail": "记录必须为对象"})
                continue
            name_key, text_key = mapping.get("name", "name"), mapping.get("text", "text")
            kind = value.get(mapping.get("kind_field", "kind")) or mapping.get("kind", "source")
            name = value.get(name_key)
            if not isinstance(name, str) or not name.strip() or kind not in definitions:
                plan["errors"].append({"row": i + 1, "detail": "缺名称或类型尚未注册", "kind": kind})
                continue
            props = definitions[kind]["spec"].get("properties", {})
            data = dict(value.get("data", {})) if isinstance(value.get("data", {}), dict) else {}
            for target, source_field in mapping.get("attributes", {}).items():
                if source_field in value and value[source_field] != "":
                    data[target] = value[source_field]
            for key in list(data):
                rule = props.get(key, {})
                try:
                    if rule.get("type") == "integer" and isinstance(data[key], str):
                        data[key] = int(data[key])
                    elif rule.get("type") in {"tags", "references"} and isinstance(data[key], str):
                        data[key] = [s.strip() for s in data[key].split(",") if s.strip()]
                    if rule.get("type") == "reference":
                        data[key] = id_map.get(str(data[key]), data[key])
                    elif rule.get("type") == "references":
                        data[key] = [id_map.get(str(v), v) for v in data[key]]
                    elif rule.get("type") == "attachment":
                        data[key] = attachment_map.get(data[key], data[key])
                except ValueError:
                    plan["errors"].append({"row": i + 1, "field": key, "detail": "字段转换失败，原件保留"})
            known = {
                "id",
                "kind",
                "name",
                "data",
                "text",
                "secret",
                "deleted",
                "revision",
                "version",
                "content_hash",
                "definition_id",
                name_key,
                text_key,
                *mapping.get("attributes", {}).values(),
            }
            extra = {k: v for k, v in value.items() if k not in known}
            if extra:
                plan["warnings"].append(
                    {"row": i + 1, "unknown_fields": list(extra), "detail": "未知字段保留原件，需确认映射"}
                )
            plan["rows"].append(
                {
                    "op": "create",
                    "entity_id": id_map[str(value.get("id", i))],
                    "kind": kind,
                    "name": name,
                    "data": data,
                    "text": str(value.get(text_key, "")),
                    "secret": bool(value.get("secret", False)),
                }
            )
        creates = [op for op in plan["rows"] if op["op"] == "create"]
        # Order dependency components. A cycle is legal inside a single atomic batch.
        pending = {op["entity_id"]: op for op in creates}
        dependencies = {}
        for eid, op in pending.items():
            refs = set()
            for key, rule in definitions[op["kind"]]["spec"].get("properties", {}).items():
                value = op["data"].get(key)
                if rule["type"] == "reference" and value:
                    refs.add(value)
                elif rule["type"] == "references" and value:
                    refs.update(value)
            dependencies[eid] = refs & set(pending)
        ordered = [op for op in plan["rows"] if op["op"] != "create"]
        batches = [ordered] if ordered else []
        while pending:
            group = set()
            todo = [next(iter(pending))]
            while todo:
                eid = todo.pop()
                if eid in group or eid not in pending:
                    continue
                group.add(eid)
                todo.extend(dependencies[eid] - group)
            if len(group) > 500:
                plan["errors"].append(
                    {
                        "code": "dependency_budget",
                        "detail": "单个引用依赖组超过500项，请先分范围或采用依赖对象",
                    }
                )
                break
            if not batches or len(batches[-1]) + len(group) > 500:
                batches.append([])
            batches[-1].extend(pending.pop(eid) for eid in sorted(group))
        facts = []
        for value in wrapper.get("facts", []):
            require(
                isinstance(value, dict) and str(value.get("subject_id")) in id_map,
                "import_fact",
                "事实起点无法映射",
            )
            facts.append(
                {
                    "op": "fact",
                    "entity_id": id_map[str(value["subject_id"])],
                    "fact": {
                        **{
                            k: value[k]
                            for k in [
                                "predicate",
                                "category",
                                "value",
                                "secret",
                                "calendar",
                                "world_from",
                                "world_to",
                            ]
                            if k in value
                        },
                        "object_id": id_map.get(str(value.get("object_id")), value.get("object_id")),
                        "chapter_id": id_map.get(str(value.get("chapter_id")), value.get("chapter_id")),
                        "source": {
                            "kind": "reference",
                            "attachment_id": source.id,
                            "original_fact": value.get("id"),
                            "original_source": value.get("source", {}),
                        },
                    },
                }
            )
        for start in range(0, len(facts), 500):
            batches.append(facts[start : start + 500])
        plan["batches"] = batches
        plan["rows"] = [op for batch in batches for op in batch]
        if wrapper.get("history"):
            plan["warnings"].append(
                {
                    "detail": "原修订及原审计保存在导入原件中；导入产生新的身份和真实本地审计。原时间戳保真恢复使用PostgreSQL备份恢复。"
                }
            )
        # Validate the complete ordered import in one rolled-back shadow transaction.
        if not plan["errors"]:
            nested = await self.db.begin_nested()
            try:
                for start, batch in enumerate(batches):
                    change = await self.create_change(
                        scope_id,
                        ChangeInput(
                            title=f"影子预检{row.id}/{start}", base_version=scope.version, operations=batch
                        ),
                    )
                    await self.adopt(scope_id, change["id"], f"preflight:{row.id}:{start}")
            except DomainError as exc:
                plan["errors"].append({"code": exc.code, "detail": exc.detail})
            finally:
                await nested.rollback()
                await self.db.refresh(scope)
                await self.db.refresh(row)
        row.plan = plan
        return self.import_json(row)

    def import_json(self, row):
        return {
            "id": row.id,
            "state": row.state,
            "base_version": row.base_version,
            "mapping": row.mapping,
            "count": len(row.plan["rows"]),
            "errors": row.plan["errors"],
            "warnings": row.plan["warnings"],
            "source_digest": row.plan["source_digest"],
        }

    async def queue_import(self, scope_id, import_id, acknowledge_unmapped=False):
        scope, _ = await authorize(self.db, self.actor, scope_id, "adopt", lock=True)
        row = await self.db.get(ImportRun, import_id)
        require(row and row.scope_id == scope_id, "not_found", "导入计划不存在", 404)
        require(row.actor_id == self.actor.id, "not_found", "导入计划不可访问", 404)
        require(not row.plan["errors"], "import_errors", "请先解决预检错误")
        require(
            not row.plan["warnings"] or acknowledge_unmapped,
            "unmapped_fields",
            "有未映射信息，请明确确认保留原件或修改映射",
        )
        require(row.base_version == scope.version, "version_conflict", "预检后数据已变化，请重新预检", 409)
        require(row.state == "preview", "import_state", "此导入已入队", 409)
        row.state = "queued"
        job = Job(
            scope_id=scope_id,
            actor_id=self.actor.id,
            kind="import",
            payload={
                "import_id": row.id,
                "expected_version": scope.version,
                "allowed_actions": sorted((await authorize(self.db, self.actor, scope_id))[1]),
                "credential_id": getattr(self.actor, "_credential_id", None),
                "requires_secret": True,
            },
            progress={"committed": 0, "batch": 0, "total": len(row.plan["rows"])},
        )
        self.db.add(job)
        await self.db.flush()
        return self.job_json(job)

    async def queue_export(self, scope_id, format="json", as_of=None):
        scope, actions = await authorize(self.db, self.actor, scope_id, "export", lock=True)
        require(format in {"json", "csv", "markdown"}, "export_format", "不支持的导出格式")
        pin = scope.version if as_of is None else as_of
        require(0 <= pin <= scope.version, "version", "导出版本无效")
        row = Job(
            scope_id=scope_id,
            actor_id=self.actor.id,
            kind="export",
            payload={
                "format": format,
                "version": pin,
                "include_secret": "secret" in actions,
                "requires_secret": "secret" in actions,
                "allowed_actions": sorted(actions),
                "credential_id": getattr(self.actor, "_credential_id", None),
            },
        )
        self.db.add(row)
        await self.db.flush()
        return self.job_json(row)

    async def export_bytes(self, scope_id, version, format="json"):
        scope, actions = await authorize(self.db, self.actor, scope_id, "export")
        items, offset = [], 0
        while True:
            page = await self.entities(
                scope_id, Query(as_of=version, offset=offset, limit=200, include_deleted=True)
            )
            for item in page["items"]:
                items.append(
                    await self.entity(scope_id, item["id"], Query(as_of=version, include_deleted=True))
                )
            if page["next_offset"] is None:
                break
            offset = page["next_offset"]
        if format == "csv":
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(["id", "kind", "name", "text", "data"])
            for item in items:
                values = [item["id"], item["kind"], item["name"], item["text"], canonical(item["data"])]
                writer.writerow(
                    ["\t" + v if v.startswith(("=", "+", "-", "@", "\t", "\r", "\n")) else v for v in values]
                )
            return buf.getvalue().encode(), "text/csv", "csv"
        if format == "markdown":
            return (
                "\n\n".join(
                    f"# {i['name']}\n\n{i['text']}\n\n```json\n{canonical(i['data'])}\n```" for i in items
                ).encode(),
                "text/markdown",
                "md",
            )
        ids = [i["id"] for i in items]
        history = []
        for sid, pin in await self.lineage(scope, version):
            rows = (
                await self.db.scalars(
                    select(Revision).where(
                        Revision.scope_id == sid, Revision.version <= pin, Revision.entity_id.in_(ids)
                    )
                )
            ).all()
            # Full history can contain formerly-secret text: only export it with secret privileges.
            if "secret" in actions:
                history += [
                    {
                        "id": r.id,
                        "entity_id": r.entity_id,
                        "scope_id": r.scope_id,
                        "version": r.version,
                        "body": r.body,
                        "content_hash": r.content_hash,
                    }
                    for r in rows
                ]
        facts, offset = [], 0
        while True:
            page = await self.facts(
                scope_id, StateQuery(as_of=version, limit=200, offset=offset, include_deleted=True)
            )
            facts.extend(page["items"])
            if offset + 200 >= page["total"]:
                break
            offset += 200
        attachments = []
        if "secret" in actions:
            blobs = (
                await self.db.scalars(
                    select(Attachment).where(Attachment.scope_id == scope_id, Attachment.purpose != "export")
                )
            ).all()
            attachments = [
                {
                    "id": b.id,
                    "name": b.name,
                    "media_type": b.media_type,
                    "digest": b.digest,
                    "base64": base64.b64encode(b.data).decode(),
                }
                for b in blobs
            ]
        payload = {
            "format": "ncc.exchange/1",
            "scope": {"name": scope.name, "kind": scope.kind, "version": version},
            "entities": items,
            "facts": facts,
            "history": history,
            "attachments": attachments,
            "definitions": await self.definitions(scope_id),
            "manifest": {
                "entities": len(items),
                "history": len(history),
                "facts": len(facts),
                "attachments": len(attachments),
                "purpose": "portable-content; full recovery requires PostgreSQL backup",
            },
        }
        payload["manifest"]["digest"] = digest(payload)
        return canonical(payload).encode(), "application/json", "json"
