# 本机MCP接线核对

读取安装器实际生成的Claude项目入口，通过官方SDK启动真实stdio进程，完成初始化、工具发现及postgresql_status；另以codex mcp get核对当前Codex入口。输出已限于状态，不读取小说正文或输出凭据。宿主新会话未验。

```json
{
  "stdio_initialize": true,
  "readonly_tools": 9,
  "all_readonly": true,
  "status": {
    "configured": false,
    "connected": false,
    "profile": "production",
    "detail": "请在项目.env填写已确定的PostgreSQL参数"
  },
  "codex_registration": {
    "found": true,
    "enabled": true,
    "transport": "stdio"
  },
  "private_paths_ignored": [
    ".mcp.json",
    ".codex/config.toml",
    ".env"
  ],
  "new_host_session": "unverified"
}
```

数据库字段未配置时，工具明确返回未配置/未连接；此结果不能作为真实PostgreSQL读取通过。没有启动服务器或新建数据库。
