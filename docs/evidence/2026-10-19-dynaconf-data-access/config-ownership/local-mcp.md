# 配置迁移后本机MCP接线

实际Codex/Claude接线均指向config/.env。用官方SDK按实际Claude清单启动stdio进程，完成初始化、工具发现与状态读取。Codex当前登记可识别，不代表新会话加载；不读取小说正文。

```json
{
  "initialized": true,
  "tools": 9,
  "all_readonly": true,
  "status": {
    "configured": false,
    "connected": false,
    "profile": "production",
    "detail": "请在config/.env填写已确定的PostgreSQL参数"
  },
  "codex": {
    "enabled": true,
    "transport": "stdio",
    "config_path_updated": true
  },
  "private_ignored": [
    "config/.env",
    ".env",
    ".mcp.json",
    ".codex/config.toml"
  ],
  "root_env_removed": true,
  "new_host_sessions": "unverified"
}
```

既定连接字段仍空，真实PG读取尚未完成。未改变连接值，未启动或创建数据库。

O01/O02修复后再次从实际入口启动最终源码stdio，初始化与工具发现成功；配置路径仍为config/.env。结果：

```json
{
  "tools": 9,
  "readonly": true,
  "status": {
    "configured": false,
    "connected": false,
    "profile": "production",
    "detail": "请在config/.env填写已确定的PostgreSQL参数"
  }
}
```
