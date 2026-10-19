# MCP读取与直接数据操作

现行接口说明。先按[后台指南](data-console.md)配置既定PostgreSQL连接、迁移和账号；所有入口使用同一Dynaconf配置及正式库/-test数据库对，不另建库。MCP、直接CLI、HTTP和后台共用应用Service、权限、历史及审计。

## 范围凭据

在“成员与设置”生成范围凭据并保存到config/.env。MCP可使用专用`NCC_MCP_TOKEN`，通常只授read，确需秘密资料再授secret；留空时沿用`NCC_API_TOKEN`，仍强制只读。直接CLI写操作使用`NCC_API_TOKEN`，需要read/edit/adopt及内容所需权限。浏览器会话不能充当范围凭据。

## MCP配置与读取

在本项目执行一次：

```bash
.venv/bin/ncc-data mcp-config --host both
```

安装器生成本机`.codex/config.toml`（Codex）及`.mcp.json`（Claude项目），仅包含启动路径和配置文件位置，不包含密码或令牌。两文件已忽略；换机器后重新生成。原有其他服务器配置保留；发现冲突或不能安全合并的布局会停止，原文件不变。Codex项目配置需受信任项目，格式依据[官方MCP说明](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)。其他宿主可使用同一stdio命令，配置和发现需按各宿主验证。

```bash
.venv/bin/ncc-data mcp
```

MCP提供9个只读工具：连接状态、范围列表、范围详情、定义列表、实体检索、实体详情、时态事实、修订历史和指定修订。数据库事务强制只读，每次读取重验凭据及当前权限，保留秘密字段过滤；没有任意SQL或写工具。

`postgresql_status`返回是否真正连接、数据库名、只读状态及schema是否就绪，不返回密码。工具能发现不等于已连库；连接字段未填写时明确返回configured=false和connected=false。修改宿主清单后需新会话加载；stdio不能混入普通输出。测试时可单独运行`ncc-data --test mcp`，仅选择既定正式连接派生的-test库。

## 非MCP读写与编辑更新

作者可继续在后台操作；HTTP提供同一套能力。直接CLI则不需要启动API或MCP：

```bash
.venv/bin/ncc-data data status
.venv/bin/ncc-data data scopes
.venv/bin/ncc-data data scope --scope '<范围ID>'
.venv/bin/ncc-data data search --scope '<范围ID>'
.venv/bin/ncc-data data get --scope '<范围ID>' --entity '<对象ID>'
.venv/bin/ncc-data data create --scope '<范围ID>' --kind character --file '<字段JSON>' --base-version 0 --request-id '<稳定请求ID>'
.venv/bin/ncc-data data edit --scope '<范围ID>' --entity '<对象ID>' --expected '<对象version>' --file '<修改字段JSON>' --base-version 1 --request-id '<另一稳定请求ID>'
.venv/bin/ncc-data data history --scope '<范围ID>' --entity '<对象ID>'
```

创建JSON例如`{"name":"角色名","text":"设定正文","data":{}}`，编辑JSON只写要改变的字段，例如`{"text":"新的设定正文"}`。base-version取范围详情当前version，expected取对象详情的version；示例数字不能代替实际读取。`update`和`edit`是同一更新操作；`retire`注销身份但保留历史。

定义、实体、名称、关系和事实的批量操作使用：

```bash
.venv/bin/ncc-data data apply --scope '<范围ID>' --file '<完整变更包JSON>'
```

完整变更包沿用ChangeInput的title/base_version/operations，另加request_id。写操作经现有创建变更、预检、批准和采用链，在同一事务保留修订、审计与幂等回执；旧版本及同ID不同内容拒绝，重复请求返回原回执。需要另一位批准者的范围仍执行原规则，CLI不绕过批准。新修订不会覆盖历史。

`search/get/facts --query '<查询条件JSON文件>'`从文件读取与HTTP相同的条件和分页，单页最多200项。`definitions`读取类型/属性/关系定义，`revision`读取指定历史内容；所有命令可加顶层`--test`选择唯一测试库。真实数据库和完整浏览器、恢复测试状态以[本轮任务](../tasks/2026-10-19-dynaconf-data-access.md)记录为准。
