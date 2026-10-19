# ncc-workflow — Novel Create Center

ZCode 插件 · v4.0.0 · 小说创作与数据工作流

NCC 是面向长篇网文的创作工作流，覆盖资料准备、立书规划、章节写作、审稿修订、连载复盘、完本导出和拆书学习。

作者决定作品方向，经理入口协调各创作角色，脚本保存进度、检查产物并生成视图。任务可以从一句想法开始，也可以从已有资料、书项目或指定章节继续。

## 功能与入口

| 入口 | 用途 |
|---|---|
| `/ncc` | 统一入口：识别创作意图、查看进度、恢复任务、处理卡文、复盘和收束 |
| `/ncc-prepare` | 整理、完善或创建资料与设定；诊断和治理素材库，无需先建书 |
| `/ncc-new` | 从作者想法建立书魂、类型契约、人物、世界设定和大纲 |
| `/ncc-write` | 写开篇、续写章节和攒稿；执行场景规划、写稿、检查与定稿循环 |
| `/ncc-review` | 审查场景与正文、记录问题、安排修订和复评，支持全书体检 |
| `/ncc-deconstruct` | 建立对标书索引、分析结构、抽取关键章技法、整理场次和转化写作方法 |
| `/ncc-eval` | 评测审稿判据的检出与稳定性，或比较同一写作任务的模型结果 |
| `/ncc-dev` | 维护插件的技能、脚本、规则和文档，记录开发任务与交付状态 |

## 数据服务与创作后台

v4提供PostgreSQL知识底座、Python/FastAPI服务、React管理后台与创作自动化。日常只有“创作台、作品资料、我的待办”三个入口；类型定义、人物与世界资料、关系时间线、历史恢复、导入导出和权限在高级管理维护。

AI正文、纲要、设定、抽取和修订按P1–P5量表给分项、证据和总分，系统执行有限返修；作者可直接修改、暂停或采用。自动定稿支持有范围、期限和次数的作者试运行或已校准策略；试运行保留质量闸门并记录校准未验证。

原文件模式继续可用。数据库模式显式启用，真实书库不会自动迁移；安装、模型配置、CLI接入与备份恢复见[数据后台使用指南](docs/guides/data-console.md)。

## 开始使用

在宿主中加载本项目后，可以调用对应入口，也可以直接描述目标，由 `/ncc` 推荐下一步。

```text
/ncc 我想写一本长篇小说，先帮我梳理想法
/ncc-prepare 整理资料 <资料目录>
/ncc-new 都市悬疑，主角是一名夜班值守员
/ncc-write 黄金三章
/ncc-write 接着写
/ncc-review 第1章
/ncc status
/ncc-deconstruct <原著路径>
/ncc 导出成 epub
```

项目提供以下宿主接入文件。命令菜单与调用语法按所用宿主选择，详细示例见[使用指南](docs/guides/usage.md)。

| 宿主 | 接入位置 |
|---|---|
| Claude | `.claude/skills`、`.claude/commands`、`.claude/agents` |
| Codex | `.agents/skills` |
| Kimi | `.agents/skills`、`.agents/agents` |
| Grok | `.claude/skills`、`.claude/commands`、`.agents/skills`、`.grok/agents` |
| ZCode | 通过 `plugins.dirs` 注册本仓库目录 |

## 创作流程

创作前准备可以独立进行：收集资料、整理素材、补全设定，再选择需要的成果用于具体作品。

书项目按以下阶段推进：

```mermaid
flowchart LR
  A[立书：想法、书魂、类型契约] --> B[立骨：人物、世界、纲要]
  B --> C[开篇：黄金三章]
  C --> D[连载：写章、审稿、修订]
  D --> E[卷复盘]
  E --> D
  E --> F[收束：清算承诺、完本、导出]
```

每章依次经过章节登记、场景卡、故事审、写作简报、正文起草、台账回写、机械检查、硬伤审、AI成果评分和定稿。需要修订时，修改后的正文重新评审；关键章节可准备多个版本，由作者比较和选择。

文件模式的 `book.json` 与承诺、知情、世界三本账保存作品状态和连续性。记忆与交接记录按角色提供，帮助任务恢复和后续写作。单元、卷及全书复盘用于检查承诺兑现、读者反馈和故事走向。完本内容可导出为 Markdown、TXT 或 EPUB。

## 拆书学习

拆书按研究目标确定范围：

| 层次 | 处理内容 |
|---|---|
| L0 索引 | 识别卷章与正文边界，记录唯一序号、字数和内容指纹 |
| L1 骨架 | 汇总卷章结构、字数和对话比例等机械信息，明确尚未分析的语义内容 |
| L2 技法 | 深拆已选章节，记录事实、证据、状态变化和可选场次；默认关键章去重后最多27章，完整逐章需明确选择 |
| L3 转化 | 从已验收结论中提炼方法，写明证据、适用条件、代价和失效条件 |

抽取结果经校验入库后才计入相应层的完成进度，基础事实与场次分别记录。统计区分全书、连续范围和非连续样本。技法可供后续规划参考，对标报告保留在拆书库中。

具体操作见[拆书技能](skills/ncc-deconstruct/SKILL.md)。

## 项目结构与数据

| 路径 | 内容 |
|---|---|
| `skills/` | 八个工作流入口及其参考文件、模板 |
| `commands/` | 宿主命令入口 |
| `agents/` | 十二个创作角色的职责与执行约束 |
| `workflow/registry/` | 阶段、角色、闸门、词表和路径的配置源 |
| `workflow/registry.json` | 由配置分片生成的兼容视图 |
| `workflow/contracts/` | 结构化产物的机器契约 |
| `scripts/ncclib/` | 状态管理、创作支撑、拆书和交付的领域实现 |
| `scripts/dev/`、`scripts/tests/` | 开发工具、自动化用例和合成样例 |
| `src/ncc_data/`、`alembic/` | 数据服务、事务规则、自动编排与数据库迁移 |
| `apps/management-web/` | 创作台与专业资料管理前端 |
| `docs/` | 使用指南、工程规范、模块设计和任务记录 |
| `eval/` | 审稿评测的锚定样章与评测说明 |
| `novels/` | 默认私有书库：书项目、准备工作区和拆书库 |

书稿、原著、素材和书内状态属于私有创作数据。`novels/`、`books/`、`_作者/`、`_拆书库/` 已加入忽略规则，提交守卫检查私有内容路径。拆书产物保存短定位证据，技法与场次使用自己的话概括。

## 开发与文档

维护插件使用 `/ncc-dev <目标>`；恢复开发任务使用 `/ncc-dev continue <任务号>`。开发流程见[工程规范](docs/engineering/workflow.md)，项目设计见[架构说明](workflow/architecture.md)和[信息架构原则](workflow/principles.md)，其余文档从[文档导航](docs/README.md)查找。

在仓库根目录按改动范围选择检查：

```bash
python3 -m unittest discover -s scripts/tests -t scripts -p 'test_*.py'
python3 scripts/dev/build_registry.py --check
python3 scripts/dev/check_plugin.py -v
python3 scripts/dev/build_docs.py --check
```

配置值在 `workflow/registry/` 的对应分片中修改，再依次运行 `scripts/dev/build_registry.py` 和 `scripts/dev/build_docs.py` 更新生成文件。纯文档改动核对内容、链接和生成格式；功能与规则变更按影响范围验证。
