# Dynaconf 与双通道接入独立评审

日期：2026-10-19。评审会话：`/root/upgrade_review`。活动工作树及技能根均为 `/Users/xuyun/Documents/ncc-workflow`，main，基线 `ac0fc44990a4f8c8e8d22a3a0a4a0540c4446393`。按 ncc-dev 独立评审要求，输入为[本轮方案](../../designs/engineering/dynaconf-data-access.md)。

本报告最终绑定候选 `7942e140baafb9418d09c5afd5952480b9fd4024ed41f161ba06c91b3ae4a372`，任务登记31个产品路径。限定代码与纯本地验证范围的独立复核完成：D01–D03 均已修复，受检范围没有遗留已复现的 P1/P2 问题。真实 PostgreSQL 连接及实际数据读写仍未验，不能把本结论写成全仓、真实运行或全局交付验收通过。

独立运行 `python3 scripts/dev/check_dev_workflow.py check docs/tasks/2026-10-19-dynaconf-data-access.md --repo /Users/xuyun/Documents/ncc-workflow`，返回 RECORD OK 与上述同一候选指纹、退出码0。该命令只核对记录、归属及指纹，不证明业务或数据库行为。

## 已修复发现

| 编号 | 严重度 | 可复现条件与影响 | 当前修复与独立复核 |
|---|---|---|---|
| D02 | P1 | 安装器向现有 Codex TOML 直接追加表。合法原文 `mcp_servers = { other = { command = "python", args = ["other.py"] } }` 能被 tomllib 解析；安装后新增表、返回成功，新文件却因扩展 inline table 无法解析，可使整个项目 Codex 配置失效。 | `src/ncc_data/mcp/configuration.py:28` 在写任何文件前校验完整JSON/TOML；合成 inline-table 布局拒绝且两份既有文件逐字节不变。正常双宿主合并、重复安装保留其他入口。最终增量另拒绝非字典服务器集合/同名入口；单元及合成无损拒绝检查通过。 |
| D01 | P2 | 环境 TOML 原直接 load_file 叠加，未执行其他层使用的数据库来源切换。进程有 DB_HOST/DB_NAME/DB_USER、环境 TOML 有 DATABASE_URL 时，URL 与旧分项并存导致配置拒绝；反向切换同类风险。 | `src/ncc_shared/configuration.py:52` 将环境 TOML 经同一 overlay。合成进程分项→环境URL、进程URL→环境完整分项双向复核，旧来源均清除，目标解析正确；没有连接数据库。 |
| D03 | P2 | 初始化仍用 JSON 双引号编码，读取改用 python-dotenv 后不解释 Unicode 转义。合成密码 `p`+U+0001+`word` 初始化后被读成字面 `p\u0001word`；旧引号 Unicode 转义也从中文变为反斜杠u文本，静默改变既有值。 | `src/ncc_shared/configuration.py:19` 由dotenv负责语法，受控literal_eval兼容旧引号值。独立8个初始化边界值及4个旧Unicode/控制转义/注释样例严格往返；没有执行配置文本或读取真实秘密。 |

上述缺陷属于本轮实现过程中的版本，不表示冻结候选仍存在该行为。

## 检查范围

读取默认 TOML、共享配置与 Settings、直接访问应用适配/契约、CLI data/main、MCP server/安装器及运行环境薄入口。相邻认证、变更集预检/批准/采用链、查询权限和历史触发器为定向阅读；没有重新穷尽评审全部既有Service、后台UI或全仓。下方文件摘要包含全文或定向读取的文件，不能等同于其全部功能均经过独立运行。

没有读取或输出真实 `.env`，没有连接、新建、重置、恢复或删除数据库，没有启动旧PG集群。只使用自建临时配置/文件、Mock与内存MCP协议。本评审没有执行真实stdio进程或读取本机实际宿主清单。

## 独立执行结果

环境：macOS，项目 `.venv`，Python 3.12.14；Dynaconf 3.3.5、python-dotenv 1.2.4、MCP SDK 1.30.0、SQLAlchemy 2.0.55、Pydantic 2.14.1、pytest 9.1.1。

- 最终执行 `.venv/bin/pytest tests/unit -q -k 'not real_stdio'`：**65 passed、1 deselected in 0.89s，退出码0**。先读取全部6个单元文件确认无数据库操作；真实stdio子进程用例明确排除。此前36项与59项执行是中间版本结果，不与最终65项相加。
- 配置合成探针覆盖默认→进程回退→环境TOML→私有文件的优先级、类型/范围校验、URL/分项切换、特殊字符及旧引号转义。`@format`、`@jinja`、`@int`、字面`${...}`不求值；独立environ不偷读进程NCC配置，os.environ前后相同。初始化不覆盖现有合成文件，权限0600。
- 最终单次配置快照增量：CLI每次只调用一次Settings.load，向DataAccess传入该快照的api_token；MCP延迟装配只加载一次Settings，优先使用同快照mcp_token，多次读调用仍经过适配。两个token不出现在Settings repr中。没有向真实目标发送凭据。
- 实际CLI parser的create/edit/update/retire四种参数接线由单元测试覆盖，保留范围、base_version、expected、request_id，并调用直接适配而不需要HTTP。另以Mock比较edit/update产生完全相同的title/op及完整变更包，避免别名重试造成幂等内容不同。
- DataAccess探针确认只读事务第一条语句为SET TRANSACTION READ ONLY，随后设置本地超时；每次重新认证，撤销凭据的下一次调用不进入Service。浏览器凭据、空token、未注册读操作及非法分页拒绝。Mock不能证明PostgreSQL真正强制只读。
- 写适配探针确认adopt/edit权限检查、CAS字段保留及现有Service.create_change/adopt链；receipt重试复用并重新检查当前变更可见性，同请求ID不同内容拒绝。没有模拟业务DML，不将此结果当成真实修订、审计或并发CAS成功。
- SQLAlchemy合成错误含假密码时，适配输出通用database_unavailable，不包含假密码；Pydantic/配置错误的接口包装不回显输入内容。
- MCP内存协议完成initialize、9个只读工具发现、9个outputSchema、字典/列表structuredContent、正常读取、权限拒绝、配置错误脱敏、未知execute_sql工具拒绝及shutdown；捕获stdout为空。无SQL或写入工具注册。
- 安装器合成探针覆盖inline-table与非字典结构的拒绝、两份文件无损、正常合并/重试、其他服务器保留、test参数及无凭据清单。没有改写本机实际宿主配置。
- 阅读新增3项PostgreSQL直接接入测试，没有运行。代码中receipt插入及结果补记在同一个外层db.begin内，既有历史触发器允许同事务行更新，未修改DDL；真实触发器、历史、审计和并发行为仍需数据库实测。

## 未验边界与外部证据

真实连接来源仍待作者提供；本评审未核对实际 `.env` 内容。主代理[验证报告](validation.md)记录73 passed、38项数据库测试跳过，其中3项为新直接接入测试；这些数量不是本评审独立执行结果。尚未证明真实PostgreSQL凭据/连接参数、实际MCP小说读取、数据库强制只读、写入落库及审计/修订/CAS效果。

主代理[本机MCP报告](local-mcp.md)记录其实际stdio初始化及9工具发现，状态为configured=false/connected=false，并记录Codex入口enabled；[安装包报告](packaging.md)记录隔离wheel验证。本评审阅读了这些报告，未将其标为自己实际执行。工具能发现和入口已登记不能证明数据库连通，也不能证明宿主新会话已加载。完整UI、五端新会话、模型质量、恢复专项及发布均不在本报告通过范围。

## 已读文件 SHA-256

以下为本轮实际读取或定向比对的源码、契约、测试和说明文件。查询/变更大模块及历史触发器为相邻边界定向检查，uv.lock为依赖元数据定向读取；不声称已审全部行。任务记录、主代理验证报告及本报告属于证据元数据，不纳入产品摘要。

```text
9000058effc55c65e1fec110418d3a9326b42512f8dd39c5b3ee27a585745e66  .env.example
faf582ad34c78f911f336ea5111cc01d49f2850ddbfd636203a1d1acbdbdb81a  .gitignore
20f13db5ac3ecbf6091c0f317a38b69d1b4ff394361fe08f7e2a306a7244ed5a  .zcodeignore
5c57b1908a4faeeb9acdd3f3cf57399f4af4d3fcec04e83ab3338abab8566dfa  config/default/settings.toml
887aeab55109b07a468afab4d54d608d590a9532e70f68981ce0042b73d7442b  docs/designs/engineering/dynaconf-data-access.md
20d27f178a93db477104e90f8bf9dc298b1d15f07437bbcbbbc4470e761ecf91  docs/engineering/code-layout.md
dff8a0d90e2b217b6d642d6ceecb2e3d6f3950e82c569267222283efa2719acb  docs/guides/data-access.md
99b5356141aa1e50fc517ce07331eae9d3b313a9539b4e40a260baf0bb6fa448  pyproject.toml
732bcaa6f6f361d515766bc17a94695c33f957003205aca0084feeb7d1abbcf2  scripts/ncc_data.py
8f2371dea897b1412dd4a65d5b515109fcbeb309a7bb91cb306a28e13d1c649e  scripts/ncclib/database_bridge.py
7704c53242e71f4103497d49d52a717932ed22e4c1cd7288772f3053f1efe7f4  src/ncc_data/application/access.py
b05b2764f693f14dc27f0527552751ebad74f34fa8d92c52498e9642a6a8632e  src/ncc_data/application/knowledge/changes.py
0bb31946e9d386dad77e209427963b2664f1ddce337ec8f06e054fee8967bba5  src/ncc_data/application/knowledge/queries.py
1d4d6c71c297353323f92318a4cab1e984877cdf6099ebb54bd08e795aadbfcb  src/ncc_data/application/security.py
62f53722e88b98c474c7c64d50a8ea6c770c59c98e133a6435d6247e850a1a9d  src/ncc_data/cli/data.py
7b6ac1e271db2930ed8bd6c842472e1243efcb44d4c17ad0b6cda8003f59801b  src/ncc_data/cli/main.py
9e25fdc5bd154309a9bfb4a6a881c28b04710d970d0a50770a2cefdf7d62209f  src/ncc_data/domain/access.py
10f8fedc7024ea6175f8585a938afb43c41d3f97f7ed8edfc62973aad8ef1b3f  src/ncc_data/domain/contracts.py
a161bf178ae71b80e45dae978633b5d7917f007f21eb26de083523561ea611d2  src/ncc_data/mcp/__init__.py
af9eda0071c1e3407f2bc11fce8eb6604ba2a7669453390876c6c97345255e12  src/ncc_data/mcp/configuration.py
930905d045002d0b7da5b02bcd0fecab2ec004fa73fc145f6abe693407c4db43  src/ncc_data/mcp/server.py
e6f02cfb5299b3e8be8a2221dca52de1e28fc4c6fc61f8d4ed141d71f9d49f11  src/ncc_data/persistence/migrations/versions/5c4c6e012a90_scoped_credentials_and_history_guards.py
40d0e89543d115705884826aa96aaa7840d76f71b447e644ad6693bd107ed65b  src/ncc_data/runtime/settings.py
a78ffd0f54dd92225c0951a9a1f1c0c691751f19df5581ed6264804501ef0c89  src/ncc_shared/configuration.py
766b0c95d4bdbcee6f800c5e38879fab77be1a01fe2b8fc86504f1d33363f80c  src/ncc_shared/runtime.py
fb317532b49fb1520491a7946285eb1e5c02b188936abd9c71dd079d560b3233  tests/backend/test_direct_access.py
dde8a4771b3aadfda659b46ecd96e864b4f86b34e93e02752b19d6d3344cc858  tests/unit/test_boundaries.py
fd1f408408ac76ea1256e1eaacc6179af906c19eb0cfbfd66698feb916abb47f  tests/unit/test_configuration.py
a94a4fd989a26eccb65c394b7454186d2e3ce8909187d8e6bd904ebb9a3b9205  tests/unit/test_data_access.py
a29b5b609b7ad56c79c462005b6f7a361479d18ce2f86912b62ccc802e6594c4  tests/unit/test_mcp.py
b25fac92bb96b2769cd5e4c1534f44a747cee851f5ceaaae16073e36c60f8386  tests/unit/test_runtime.py
837247ec5f99c0caf45d6758ef8b5f3a70ccf7febc36819cd16ba097edad003a  tests/unit/test_workspace.py
ee5a76662a2a2a5c647eec7d492ea7222f2e401dea146d653562704dc484ac70  uv.lock
```
