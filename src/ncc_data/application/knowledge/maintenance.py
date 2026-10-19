"""Reviewable recovery, identity maintenance and three-way branch merge plans."""

import copy

from ncc_data.application.security import authorize
from ncc_data.domain.contracts import ChangeInput, Query
from ncc_data.persistence.models import Definition, uid
from ncc_shared.errors import require


class MaintenanceMixin:
    async def all_entities(self, scope_id, as_of=None, include_deleted=False):
        offset, items = 0, []
        while True:
            page = await self.entities(
                scope_id, Query(as_of=as_of, include_deleted=include_deleted, offset=offset, limit=200)
            )
            items.extend(
                [
                    await self.entity(scope_id, i["id"], Query(as_of=as_of, include_deleted=include_deleted))
                    for i in page["items"]
                ]
            )
            if page["next_offset"] is None:
                return items
            offset = page["next_offset"]

    async def maintenance_plan(self, scope_id, value):
        scope, actions = await authorize(self.db, self.actor, scope_id, "edit", lock=True)
        require("secret" in actions, "maintenance_permission", "完整影响分析需要秘密内容权限", 403)
        require(scope.version == value.base_version, "version_conflict", "维护基线已变化", 409)
        operations, conflicts = [], []
        action = value.action
        source = (
            await self.entity(scope_id, value.entity_id, Query(include_deleted=True))
            if value.entity_id
            else None
        )
        if action == "restore":
            require(source and value.revision_id, "restore", "恢复需指定对象及历史修订")
            old = await self.revision(scope_id, source["id"], value.revision_id)
            operations.append(
                {
                    "op": "restore",
                    "entity_id": source["id"],
                    "expected": source["version"],
                    "revision_id": old["revision"],
                }
            )
        elif action == "split":
            require(source and value.name, "split", "拆分需指定来源及新名称")
            fields = set(value.fields)
            require(fields <= set(source["data"]), "split", "拆分属性不属于源对象")
            operations = [
                {
                    "op": "create",
                    "entity_id": uid(),
                    "kind": source["kind"],
                    "name": value.name,
                    "data": {k: v for k, v in source["data"].items() if k in fields},
                    "text": value.text,
                    "secret": source["secret"],
                }
            ]
            if fields:
                operations.append(
                    {
                        "op": "update",
                        "entity_id": source["id"],
                        "expected": source["version"],
                        "unset": sorted(fields),
                    }
                )
        elif action == "merge":
            require(
                source and value.target_id and source["id"] != value.target_id, "merge", "合并需两个不同对象"
            )
            target = await self.entity(scope_id, value.target_id)
            require(source["kind"] == target["kind"], "merge", "不同类型不能合并身份")
            for key, val in source["data"].items():
                if (
                    key in target["data"]
                    and target["data"][key] != val
                    and value.choices.get(key) not in {"source", "target"}
                ):
                    conflicts.append({"field": key, "source": val, "target": target["data"][key]})
            if (
                source["text"] != target["text"]
                and source["text"]
                and target["text"]
                and value.choices.get("$text") not in {"source", "target"}
            ):
                conflicts.append({"field": "$text", "source": source["text"], "target": target["text"]})
            if conflicts:
                return {"conflicts": conflicts, "change": None}
            data = {**source["data"], **target["data"]}
            for key, choice in value.choices.items():
                if choice == "source" and key in source["data"]:
                    data[key] = source["data"][key]
            text = (
                source["text"] if value.choices.get("$text") == "source" else target["text"] or source["text"]
            )
            operations.append(
                {
                    "op": "update",
                    "entity_id": target["id"],
                    "expected": target["version"],
                    "data": data,
                    "text": text,
                    "secret": source["secret"] or target["secret"],
                }
            )
            for obj in await self.all_entities(scope_id):
                definition = await self.db.get(Definition, obj["definition_id"])
                rewritten = {}
                for key, rule in definition.spec.get("properties", {}).items():
                    val = obj["data"].get(key)
                    if rule["type"] == "reference" and val == source["id"]:
                        rewritten[key] = target["id"]
                    elif rule["type"] == "references" and isinstance(val, list) and source["id"] in val:
                        rewritten[key] = list(
                            dict.fromkeys(target["id"] if x == source["id"] else x for x in val)
                        )
                if rewritten and obj["id"] == target["id"]:
                    operations[0]["data"].update(rewritten)
                elif rewritten and obj["id"] != source["id"]:
                    operations.append(
                        {
                            "op": "update",
                            "entity_id": obj["id"],
                            "expected": obj["version"],
                            "data": rewritten,
                        }
                    )
            facts = await self.raw_facts(scope)
            for fact in facts:
                if fact.subject_id != source["id"] and fact.object_id != source["id"]:
                    continue
                operations.append({"op": "retract", "entity_id": fact.subject_id, "fact_id": fact.id})
                operations.append(
                    {
                        "op": "fact",
                        "entity_id": target["id"] if fact.subject_id == source["id"] else fact.subject_id,
                        "fact": {
                            "predicate": fact.predicate,
                            "category": fact.category,
                            "object_id": target["id"] if fact.object_id == source["id"] else fact.object_id,
                            "value": fact.value,
                            "secret": fact.secret,
                            "calendar": fact.calendar,
                            "world_from": str(fact.world_from) if fact.world_from is not None else None,
                            "world_to": str(fact.world_to) if fact.world_to is not None else None,
                            "chapter_id": fact.chapter_id,
                            "source": {"kind": "author", "merged_fact": fact.id},
                        },
                    }
                )
            operations.append({"op": "retire", "entity_id": source["id"], "expected": source["version"]})
        else:
            branch, branch_actions = await authorize(self.db, self.actor, value.branch_id, "read")
            require(
                {"export", "secret"} <= set(branch_actions) and branch.base_id == scope_id,
                "branch_merge",
                "仅能合并当前范围直接派生且有完整权限的分支",
            )
            base = {i["id"]: i for i in await self.all_entities(scope_id, branch.base_version, True)}
            destination = {i["id"]: i for i in await self.all_entities(scope_id, include_deleted=True)}
            changed = await self.all_entities(branch.id, include_deleted=True)
            remap = {i["id"]: uid() for i in changed if i["id"] not in base}
            for obj in changed:
                eid, before, current = obj["id"], base.get(obj["id"]), destination.get(obj["id"])
                fields = ("name", "data", "text", "secret", "deleted")

                def snapshot(x, fields=fields):
                    return {k: x[k] for k in fields} if x else None

                if snapshot(obj) == snapshot(before):
                    continue
                if current and snapshot(current) != snapshot(before) and snapshot(current) != snapshot(obj):
                    choice = value.choices.get(eid)
                    if choice not in {"source", "target"}:
                        conflicts.append(
                            {
                                "entity_id": eid,
                                "base": snapshot(before),
                                "source": snapshot(obj),
                                "target": snapshot(current),
                            }
                        )
                        continue
                    if choice == "target":
                        continue
                data = copy.deepcopy(obj["data"])
                definition = await self.definition(scope, obj["kind"])
                for key, rule in definition.spec.get("properties", {}).items():
                    if key in data and rule["type"] == "reference":
                        data[key] = remap.get(data[key], data[key])
                    elif key in data and rule["type"] == "references":
                        data[key] = [remap.get(x, x) for x in data[key]]
                if obj["deleted"]:
                    if current and not current["deleted"]:
                        operations.append({"op": "retire", "entity_id": eid, "expected": current["version"]})
                else:
                    op = {
                        "op": "update" if current else "create",
                        "entity_id": remap.get(eid, eid),
                        "kind": obj["kind"],
                        "name": obj["name"],
                        "data": data,
                        "text": obj["text"],
                        "secret": obj["secret"],
                    }
                    if current:
                        op.update(expected=current["version"], unset=list(set(current["data"]) - set(data)))
                    operations.append(op)
            if conflicts:
                return {"conflicts": conflicts, "change": None}
            # Facts require explicit reconciliation rather than silently selecting a timeline.
            base_facts = {f.id for f in await self.raw_facts(scope, branch.base_version)}
            branch_facts = await self.raw_facts(branch)
            dest_facts = {f.id for f in await self.raw_facts(scope)}
            removed = base_facts - {f.id for f in branch_facts}
            for fact in await self.raw_facts(scope):
                if fact.id in removed:
                    operations.append({"op": "retract", "entity_id": fact.subject_id, "fact_id": fact.id})
            for fact in branch_facts:
                if fact.id in base_facts or fact.id in dest_facts:
                    continue
                operations.append(
                    {
                        "op": "fact",
                        "entity_id": remap.get(fact.subject_id, fact.subject_id),
                        "fact": {
                            "predicate": fact.predicate,
                            "category": fact.category,
                            "object_id": remap.get(fact.object_id, fact.object_id),
                            "value": fact.value,
                            "secret": fact.secret,
                            "calendar": fact.calendar,
                            "world_from": str(fact.world_from) if fact.world_from is not None else None,
                            "world_to": str(fact.world_to) if fact.world_to is not None else None,
                            "chapter_id": remap.get(fact.chapter_id, fact.chapter_id),
                            "source": {"kind": "author", "branch_fact": fact.id, "branch_scope": branch.id},
                        },
                    }
                )
        require(operations, "unchanged", "没有需要采用的变化")
        require(len(operations) <= 500, "maintenance_size", "影响超过500项，请分批明确处理")
        draft = await self.create_change(
            scope_id,
            ChangeInput(title=f"{action}：身份与历史维护", base_version=scope.version, operations=operations),
        )
        checked = await self.validate_change(scope_id, draft["id"])
        return {"conflicts": [], "change": checked}
