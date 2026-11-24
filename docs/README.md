# 文档导航

先按用途找目录，再按模块找文件；目录不按工具名称、写作来源或日期划分。现行工作流规则以仓库的 `workflow/registry/` 分片、`skills/`、`agents/` 为源；`workflow/registry.json` 是可校验的兼容生成视图。仓库公开文档仅保留导航、使用指南、工程规范、模块设计与产品层基线；涉及本机路径、会话标识或本地环境快照的 `docs/tasks/`、`docs/evidence/` 与 `.sdlc/` 作为本地开发工作件统一忽略，不进入公开仓库。归属判定、命名与生命周期见[文档组织规范](engineering/documentation.md)。

## 现行文档

| 要找什么 | 入口 |
|---|---|
| 如何使用、命令和常见场景 | [使用指南](guides/usage.md) |
| 如何启动与维护数据后台、AI模型与工作副本 | [数据服务与创作后台](guides/data-console.md) |
| MCP只读检索与非MCP直接读写 | [数据接入指南](guides/data-access.md) |
| 创作后台产品策略、功能地图与设计系统 | [产品层说明](product/README.md) |
| 如何维护、验证与交付插件 | [开发工作流](engineering/workflow.md) |
| 后台代码、前端、脚本与测试目录归属 | [代码归属与复用](engineering/code-layout.md) |
| 文档怎么分类、命名、脱敏与维护 | [文档组织规范](engineering/documentation.md) |
| 项目问题如何转成四角色能力 | [工程经验与能力](../skills/ncc-dev/references/experience.md) |
| 引入外部 skill、语料、工具前的筛查 | [外部来源筛查与黑名单](engineering/source-vetting.md) |

## 模块设计（designs/ 按模块分目录）

| 模块 | 文档 | 状态 |
|---|---|---|
| 拆书 | [拆书统一升级方案](designs/deconstruction/upgrade.md)、[生成契约字段表](designs/deconstruction/contracts.md) | P1–P5 功能及 P6 用例已实现；留档契约与设计依据 |
| 开发流程 | [开发流程设计](designs/engineering/workflow.md)、[来源审查记录](designs/engineering/source-audit.md) | 已实施并发布；留档设计依据与历史审查 |
| 工程架构 | [架构审查及复核](designs/engineering/architecture-audit.md)、[架构成长方案](designs/engineering/architecture-growth.md)、[配置与代码归属](designs/engineering/configuration-ownership.md)、[Dynaconf双通道接入](designs/engineering/dynaconf-data-access.md)、[小说创作主线与工程职责](designs/engineering/product-architecture.md) | 已实施；留档架构演进与边界取舍依据 |
| 记忆与进化 | [记忆与自进化设计](designs/memory/memory-evolution-design.md) | 已实施（v3.0），留档设计依据 |
| 创作前准备 | [准备设计](designs/preparation/preparation-design.md) | 已实施，留档设计依据 |
| 小说数据底座与管理后台 | [PostgreSQL底座](designs/storage/postgresql-foundation.md)、[基础管理后台](designs/storage/management-console.md)、[创作自动化与AI评分](designs/storage/creation-automation.md)、[实施计划](designs/storage/implementation.md)、[小说创作工作台重构](designs/storage/novel-studio-overhaul.md) | v4底座与小说创作工作台（六大创作空间＋可拆合五工序AI协同）已落地 |
| 写章与白金连载引擎 | [起点白金连载引擎与出品人工作流升级方案](designs/writing/platinum-upgrade.md) | 已落地并留档设计依据 |

## 后续演进与持续验证事项

尚未闭环或需随真实创作持续验证的事项集中在此登记；本表只做公开架构与验证边界索引，本地单次执行批次记录保留在本机已忽略的 `docs/tasks/` 与 `docs/evidence/` 中。

| 事项 | 状态 | 公开设计或规范入口 |
|---|---|---|
| 真实作品规模下的自动定稿校准与留出集评估 | 试运行模式已就绪；正式校准需真实人工标注样本与留出验证 | [创作自动化与AI评分](designs/storage/creation-automation.md)、[数据后台指南](guides/data-console.md) |
| 多宿主（Claude / Codex / Kimi / Grok / ZCode / DSH）新会话持续回归 | 静态清单与软链自检已纳入 `check_plugin.py`；跨宿主升级后按需做新会话冒烟 | [开发工作流](engineering/workflow.md) |
| 大体量拆书与多书共用资产库的实书压测 | 分层拆书（L0–L3）与素材库治理已实现；超大规模书库性能按实际数据持续观察 | [拆书升级方案](designs/deconstruction/upgrade.md)、[准备设计](designs/preparation/preparation-design.md) |

新增模块时在 `designs/` 下建立模块目录并更新[模块清单](engineering/documentation.md)；新增使用说明或工程规范放入对应用途目录。已被替代的方案直接删除并清理引用，历史由 Git 保留。
