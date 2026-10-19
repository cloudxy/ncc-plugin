# 配置与双通道接入验证

范围：基线ac0fc44990a4f8c8e8d22a3a0a4a0540c4446393后的Dynaconf配置管理、只读MCP、非MCP直接CLI和既有Service接线。没有修改schema、历史迁移或创作判据；不重跑无关模型回归和完整前端构建。按作者安排，真实数据库、完整浏览器和恢复专项不在本轮冒称通过。

环境：macOS，旧文件入口使用系统Python；后台及MCP使用项目.venv。版本：`{"python": "3.12.14", "dynaconf": "3.3.5", "python-dotenv": "1.2.4", "mcp": "1.30.0", "sqlalchemy": "2.0.55", "fastapi": "0.146.0"}`。Dynaconf实际负责默认文件、环境文件、私有.env合并与类型/范围校验；dotenv只负责严格语法及旧引号值兼容，不更新os.environ。

## 已执行与观察

| 检查 | 实际结果 | 证据 |
|---|---|---|
| pytest tests/unit tests/backend | 73 passed，38 skipped；其中3项新直接接入PG测试同样跳过 | [测试原始输出](tests.log) |
| 原文件CLI相邻边界 | quality 3项、architecture 7项通过；不需要第三方包的文件入口和系统Python到数据运行环境转入均成功 | [quality](quality.log)、[architecture](architecture.log)、[入口](file-cli.log) |
| 语法/规范 | Ruff、插件静态接线、registry/docs生成一致性及git diff格式通过 | [ruff](ruff.log)、[plugin](plugin.log)、[registry](registry.log)、[docs](docs.log)、[diff](diff.log) |
| Markdown链接 | 改动产品文档82个相对文件目标均存在；此检查不核查网站或页内锚点 | [链接输出](links.log) |
| 实际stdio与本机注册 | 使用实际.mcp.json启动SDK进程，完成initialize及9工具发现；Codex登记enabled/stdio；状态明确为configured=false、connected=false | [本机MCP](local-mcp.md) |
| wheel隔离加载 | 77成员、单份默认配置与模板、4份历史迁移原字节；私有配置不入包。仓外加载包内实现，初始化0600/不覆盖、.env优先、不污染环境、唯一-test派生、9个结构化只读工具与CLI解析通过 | [完整探针](packaging.md) |

本轮新用例覆盖配置类型校验与优先级、数据库URL/分项来源切换、特殊字符及旧转义原值、显式路径、无全局环境污染；直接访问只读第一语句、逐次认证及撤销、浏览器凭据拒绝、分页上界、写入使用原采用链及版本/幂等传递；CLI创建/编辑/更新/注销真实参数解析；宿主配置原文件保持、合并与重试；官方SDK真实stdio协议。Mock验证的是适配和拒绝路径，不能证明PostgreSQL自身强制只读、审计落库或并发CAS。

## 未验和恢复条件

本机项目.env的PostgreSQL字段仍为空；没有替换既定参数、猜测URL、启动旧临时集群或另建库。真实读取不能从工具发现推断。新增3项集成用例覆盖真实创建/更新/历史/幂等、数据库强制只读、只读范围凭据拒绝写入；它们与既有35项一起等待既定正式连接所派生的唯一-test库。后台API/UI既有读写功能保留，未在本轮进行真实浏览器联调。五宿主新会话加载未验，当前Codex登记只能证明当前配置可识别。

下一步由作者提供既定连接文件路径，将原值导入/核对项目.env，配置范围凭据后运行只读MCP状态及有限读取。专项测试仅使用正式库-test，遵循共同守卫，不新建随机数据库。没有真实连接与新会话证据前，不宣称整体验收通过。本地候选尚未提交、推送；回退仅限本轮代码和本机无密钥MCP清单，保留私有.env及数据库。
