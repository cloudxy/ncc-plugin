# 配置归属与产品职责修订验证

本轮承接作者对配置归属和产品定位的纠正。保留上一候选7942e140baafb9418d09c5afd5952480b9fd4024ed41f161ba06c91b3ae4a372的原始报告，不将其通过状态直接转用于新候选。基线仍为ac0fc44990a4f8c8e8d22a3a0a4a0540c4446393，main；后台Python3.12.14、Dynaconf3.3.5、官方MCP SDK1.30.0。

## 产品和运行边界

实现：私有配置和模板归config，共享路径、旧文件迁移、MCP原入口安全改接、现行文档同步。配置加载、只读MCP与非MCP适配延续前轮实现。没有改变schema、历史迁移、创作判据或开发代理路由。

设计交付：[小说创作主线与工程职责](../../../designs/engineering/product-architecture.md)基于Shell、CreativePage、创作角色注册表及开发流程给出缺口与四类职责的输入、交付、验收和后续批次。该文档是方案候选；没有宣称四个工程代理已启用，没有实施卷章界面升级，不以方案代替行为测试。不需要无关的锚定章/模型回归。

## 检查与实际观察

| 检查 | 实际结果 | 原始记录 |
|---|---|---|
| 受影响单元及后端收集 | 84 passed，38 skipped；数据库部分仍未实测 | [pytest](tests.log) |
| 相邻原CLI | quality 3项、architecture 7项通过；纯标准库文件入口和系统Python到项目数据环境转入均通过 | [quality](quality.log)、[architecture](architecture.log)、[文件入口](file-cli.log)、[数据入口](data-cli.log) |
| 代码及静态接线 | Ruff、PLUGIN、REGISTRY、DOCS与差异格式通过 | [ruff](ruff.log)、[plugin](plugin.log)、[registry](registry.log)、[docs](docs.log)、[diff](diff.log) |
| 链接目标 | 改动产品文档87个相对文件目标均存在；不核查外部站点或页内锚点 | [links](links.log) |
| 本机私有文件迁移 | init成功；原字节保留、根文件移除、config/.env存在且0600，不输出值或摘要 | [migration](migration.md) |
| 本机MCP重接 | 两宿主实际入口指向config/.env；SDK真实stdio初始化和9工具发现通过；Codex当前登记enabled。状态明确未配置/未连接 | [local-mcp](local-mcp.md) |
| wheel | 构建成功，77成员；模板来自config，仓外默认config/.env初始化/加载、资源、9只读工具、直接CLI通过；4个迁移字节未变，不含私有配置 | [packaging](packaging.md) |

新增11个参数化测试实例覆盖原字节一次迁移、无静默回退、默认/显式规范路径双文件冲突、模板归属、目标并发出现时不覆盖、旧软链拒绝、生产及唯一test两种MCP接线原路径迁移。其他服务器与同入口enabled/timeout设置保持，重复执行不改文件。测试使用临时合成配置，不连数据库。独立初审发现O01/P1（硬链接后源/目标被编辑器替换而遭删除）和O02/P2（TOML字符串伪装入口）；已改为实际macOS排他原子rename，并以真实源/目标替换和TOML多行文本反例验证。迁移不再包含路径unlink清理，MCP解析对象只允许真实args变化。Linux分支和不支持环境的实际系统执行未验。

## 未验和恢复

真实PostgreSQL字段仍为空，既定配置来源未提供，38项数据库用例跳过；实际资料读取、落库、并发CAS、数据库强制只读、审计与恢复仍待专项。没有重启旧临时集群，没有新建、删除或改名任何库。宿主新会话和完整UI未验；产品角色方案和后续卷章/自动化工作没有实施。

本机仅移动私有文件和更新无密钥宿主参数；不改变数据库、模型或范围凭据原值。回退需按对应版本保留一份私有配置并重接MCP，不能同时保留新旧两个默认位置；不回滚数据库。产品方案可独立修订，不影响现有十二个创作角色。
