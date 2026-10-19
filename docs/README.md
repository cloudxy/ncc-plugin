# 文档导航

先按用途找目录，再按模块找文件；目录不按工具名称、写作来源或日期划分。现行工作流规则以仓库的 `workflow/registry/` 分片、`skills/`、`agents/` 为源；`workflow/registry.json` 是可校验的兼容生成视图，docs 只放导航、说明、规范、设计与执行记录。归属怎么判定、怎么命名、何时归档见[文档组织规范](engineering/documentation.md)。

## 现行文档

| 要找什么 | 入口 |
|---|---|
| 如何使用、命令和常见场景 | [使用指南](guides/usage.md) |
| 如何维护、验证与交付插件 | [开发工作流](engineering/workflow.md) |
| 后台代码、前端与测试放哪里 | [代码归属与复用](engineering/code-layout.md) |
| 数据后台安装、配置与操作 | [数据服务与创作后台](guides/data-console.md) |
| MCP读取与非MCP直接读写 | [数据接入指南](guides/data-access.md) |
| 文档怎么分类、命名和维护 | [文档组织规范](engineering/documentation.md) |
| 项目问题如何转成四角色能力 | [工程经验与能力](../skills/ncc-dev/references/experience.md)、[实施验证](tasks/2026-10-19-engineering-experience.md) |
| 引入外部 skill、语料、工具前的筛查 | [外部来源筛查与黑名单](engineering/source-vetting.md) |

## 模块设计（designs/ 按模块分目录）

| 模块 | 文档 | 状态 |
|---|---|---|
| 拆书 | [拆书统一升级方案](designs/deconstruction/upgrade.md)、[生成契约字段表](designs/deconstruction/contracts.md) | P1–P5 功能及 P6 用例已实现本地候选；作者测试待验 |
| 开发流程 | [开发流程设计](designs/engineering/workflow.md)、[来源审查记录](designs/engineering/source-audit.md) | 已实施并发布；留档设计依据与历史审查 |
| 工程架构 | [架构审查及复核](designs/engineering/architecture-audit.md)、[架构成长方案](designs/engineering/architecture-growth.md) | G1/G2/G5/G3a/G3b 已实施本地候选；设计依据留档，验证见实施任务 |
| 记忆与进化 | [记忆与自进化设计](designs/memory/memory-evolution-design.md) | 已实施（v3.0），留档设计依据 |
| 创作前准备 | [准备设计](designs/preparation/preparation-design.md) | 已实施，留档设计依据 |
| 小说数据底座与管理后台 | [PostgreSQL底座](designs/storage/postgresql-foundation.md)、[基础管理后台](designs/storage/management-console.md)、[创作自动化与AI评分](designs/storage/creation-automation.md) | v4已实现并发布；保留设计依据，现行行为和未验范围见使用指南与实施任务 |

## 未执行的计划与待办

尚未执行或未闭环的事项集中在此登记；本表只做索引，计划正文在对应方案或任务记录里，不在别处另写一份。

| 事项 | 状态 | 入口 |
|---|---|---|
| 小说创作主线与产品、架构、DBA职责 | 作者已要求执行工程角色接线；具体实现与验证见任务，后续卷章和完整产品路径另列 | [角色实施](tasks/2026-10-19-engineering-roles.md)、[职责与产品架构](designs/engineering/product-architecture.md) |
| Dynaconf与PostgreSQL双通道数据接入 | 配置及模板已统一归config，本机MCP已重接；既定连接待补，真实读取与专项测试待验 | [实施任务](tasks/2026-10-19-dynaconf-data-access.md)、[设计](designs/engineering/dynaconf-data-access.md) |
| 双库约束与代码归属 | 目录及源码已发布；配置归属由本轮Dynaconf方案接替，真实数据库联调待验 | [实施任务](tasks/2026-10-19-configuration-ownership.md)、[目录规范](engineering/code-layout.md) |
| PostgreSQL底座、专业后台与创作自动化评分 | v4代码已发布，正式数据库/真实模型接入与实际作品验收待办 | [底座](designs/storage/postgresql-foundation.md)、[后台](designs/storage/management-console.md)、[自动化评分](designs/storage/creation-automation.md)、[任务](tasks/2026-10-18-postgresql-design.md) |
| 仓库架构成长：G0 基线 → G1 清单映射校验 → G2 兼容迁移 → G5 CLI 注册拆分 → G3a 统一读取/G3b 分片 | 本地实现完成，历史验收见[实施任务](tasks/2026-10-18-architecture-upgrade.md)；宿主新会话与独立评审待办；后续拆书变化独立记录 | [架构成长方案](designs/engineering/architecture-growth.md) |
| 拆书统一升级 P1–P6：契约 → 索引 → 入库恢复 → 分层场次 → 统计转化 → 验证整合 | 功能和测试代码已交付本地候选；P6 回归、规则行为、独立评审与五端加载由作者单独验证，未执行 | [实施与测试交接](tasks/2026-10-18-deconstruction-upgrade.md) |
| README 文案独立评审 | 自查完成，独立评审待办 | [任务记录](tasks/2026-10-12-readme-refresh.md) |
| 文档与接线任务的独立评审 | 自查完成，独立评审待办；原架构审查由独立角色产出，本轮方案修订为当前会话复核，不冒称独立复审 | [拆书方案整合](tasks/2026-10-16-deconstruction-docs.md)、[文档更新](tasks/2026-10-16-docs-refresh.md)、[zcode 注册切换](tasks/2026-10-17-zcode-registration.md)、[架构方案](tasks/2026-10-18-architecture-plan.md) |
| zcode 新会话加载验证（切换直注册后） | 未验证：config 已改，需新会话确认实际加载根为仓库目录 | [任务记录](tasks/2026-10-17-zcode-registration.md) |
| 五端（claude/codex/kimi/grok/zcode）新会话运行验证 | unverified：静态接线通过，未做新会话冒烟 | [开发入口发布证据](evidence/2026-10-12-ncc-dev/task.md) |
| 未发布任务的提交与推送 | 未请求发布，保留本地候选与精确范围 | `tasks/` 下各记录的 delivery 字段 |

## 活动任务与证据

| 要找什么 | 入口 |
|---|---|
| 正在做什么、如何恢复 | [项目配置与代码归属](tasks/2026-10-19-configuration-ownership.md)、[README 更新任务](tasks/2026-10-12-readme-refresh.md)、[拆书方案整合任务](tasks/2026-10-16-deconstruction-docs.md)、[文档更新任务](tasks/2026-10-16-docs-refresh.md)、[zcode 注册切换任务](tasks/2026-10-17-zcode-registration.md)、[架构方案复核](tasks/2026-10-18-architecture-plan.md)、[架构升级实施](tasks/2026-10-18-architecture-upgrade.md)、[拆书功能实施](tasks/2026-10-18-deconstruction-upgrade.md) |
| 验证输入、结果与限制 | `evidence/<任务号>/`：[已发布开发入口](evidence/2026-10-12-ncc-dev/task.md)、[README 验证](evidence/2026-10-13-readme-refresh/validation.md)、[文档整合验证](evidence/2026-10-16-deconstruction-docs/validation.md)、[文档更新验证](evidence/2026-10-16-docs-refresh/validation.md)、[注册切换验证](evidence/2026-10-17-zcode-registration/validation.md)、[架构方案验证](evidence/2026-10-18-architecture-plan/validation.md)、[架构升级验证](evidence/2026-10-18-architecture-upgrade/validation.md) |

新增模块时在 `designs/` 下建立模块目录并更新[模块清单](engineering/documentation.md)；新增使用说明或工程规范放入对应用途目录。已被替代的方案直接删除并清理引用，历史由 Git 保留。
