"""Direct data commands. No web service or MCP process is required."""

import asyncio
import json
from pathlib import Path

from ncc_data.application.access import DataAccess
from ncc_data.runtime.settings import Settings


def register(commands):
    data = commands.add_parser(
        "data", help="直接PostgreSQL读写；与后台共用权限、修订和审计，无需启动API或MCP"
    )
    operations = data.add_subparsers(dest="data_action", required=True)
    operations.add_parser("status", help="只读连接与schema状态，不返回凭据")
    operations.add_parser("scopes", help="读取范围凭据可访问的作品/资料范围")
    for name in ("scope", "definitions", "search", "get", "history", "revision", "facts"):
        item = operations.add_parser(name)
        item.add_argument("--scope", required=True)
        if name in {"get", "history", "revision"}:
            item.add_argument("--entity", required=True)
        if name == "revision":
            item.add_argument("--revision", required=True)
        if name in {"search", "get", "facts"}:
            item.add_argument("--query", type=Path, help="与HTTP共用的查询条件JSON")
    for name in ("create", "update", "edit", "retire", "apply"):
        item = operations.add_parser(name)
        item.add_argument("--scope", required=True)
        item.add_argument(
            "--file",
            type=Path,
            required=name != "retire",
            help="实体字段或完整变更包JSON",
        )
        if name != "apply":
            item.add_argument("--base-version", type=int, required=True)
            item.add_argument("--request-id", required=True, help="重试保持相同ID，不可用于不同内容")
        if name == "create":
            item.add_argument("--kind", required=True)
        elif name in {"update", "edit", "retire"}:
            item.add_argument("--entity", required=True)
            item.add_argument("--expected", required=True, help="读取结果的对象修订version，用于比较更新")


def run(args):
    settings = Settings.load(args.config, "test" if args.test else "production")
    access = DataAccess(settings, settings.api_token)
    reads = {
        "get": "entity",
        "revision": "revision",
        "status": "status",
        "scopes": "scopes",
        "scope": "scope",
        "definitions": "definitions",
        "search": "search",
        "history": "history",
        "facts": "facts",
    }

    async def execute():
        try:
            action = args.data_action
            if action == "status":
                return await access.status()
            if action in reads:
                query = json.loads(args.query.read_text()) if getattr(args, "query", None) else None
                return await access.read(
                    reads[action],
                    scope_id=getattr(args, "scope", None),
                    entity_id=getattr(args, "entity", None),
                    revision_id=getattr(args, "revision", None),
                    query=query,
                )
            payload = json.loads(args.file.read_text()) if args.file else {}
            if action != "apply":
                if not isinstance(payload, dict):
                    raise ValueError("实体变更文件必须是JSON对象")
                write_action = "update" if action == "edit" else action
                operation = {**payload, "op": write_action}
                if action == "create":
                    operation["kind"] = args.kind
                else:
                    operation.update(entity_id=args.entity, expected=args.expected)
                payload = {
                    "request_id": args.request_id,
                    "title": "CLI " + write_action,
                    "base_version": args.base_version,
                    "operations": [operation],
                }
            return await access.apply(args.scope, payload)
        finally:
            await access.close()

    return asyncio.run(execute())
