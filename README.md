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

v4提供PostgreSQL知识底座、Python/FastAPI服务、React小说创作工作台与创作自动化。日常围绕“创作台、大纲与暗线、作品资料、公共陈列库、市场与风向、我的待办”六个创作空间协同推进；类型定义、关系时间线、历史恢复、导入导出和权限在高级管理维护。

AI正文、纲要、设定、抽取和修订按P1–P5量表给分项、证据和总分，系统执行有限返修；作者可直接修改、暂停或采用。自动定稿支持有范围、期限和次数的作者试运行或已校准策略；试运行保留质量闸门并记录校准未验证。

配置由Dynaconf统一管理，公共默认值归`config/default/settings.toml`（默认服务地址为`http://127.0.0.1:8761`），个性化连接与凭据归`config/.env`，命令自动读取。数据库只使用线上库`ncc-pro`及其同连接的本地测试库`ncc-dev`。

PostgreSQL只读MCP供AI检索作品资料；非MCP可通过后台、HTTP接口及`ncc-data data`直接查询、创建、编辑和更新，统一保留权限、版本与审计。原文件模式继续可用；数据库模式显式启用，真实书库不会自动迁移。

### 跨平台快速启动（macOS / Windows）

仓库根目录提供纯标准库启动器 `start.py`，统一完成 `.venv` 环境检查、配置初始化、前端构建产物检查、数据库 `doctor` 自检，并同时拉起管理后台 Web/API 服务（默认监听 `http://127.0.0.1:8761`）与后台创作 Worker，按 `Ctrl+C` 一键安全停止。未指定模式参数时，`./start.py` 默认使用 `production` profile 连接正式库 `ncc-pro`；本地隔离调试传 `--database ncc-dev`（仍使用 `8761` 常规端口），自动化测试专用端口 `8788` 使用 `--test`：

```bash
# macOS / Linux
./start.py --migrate                          # 首次接入正式库 ncc-pro 时执行迁移（空库自动初始化默认管理员 admin / 123456）并启动
./start.py --open                             # 日常启动（连接 ncc-pro）并在就绪后打开 http://127.0.0.1:8761
./start.py --create-user '<账号名>'            # 可选：通过终端交互式增建后台账号（密码至少12字符）
./start.py --database ncc-dev --open          # 切换至同连接测试库 ncc-dev 进行本地隔离调试
```

```powershell
# Windows（PowerShell / CMD）
py -3 start.py --migrate                      # 或 python start.py --migrate（空库自动建立默认管理员 admin / 123456）
py -3 start.py --open
py -3 start.py --create-user <账号名>
```

> **首次使用安全提醒与主机差异化策略**：当目标数据库尚无任何用户时，`--migrate` 会自动初始化默认系统管理员账号 `admin`（初始密码 `123456`，不会覆盖已有账号）。**第一次使用时必须进入后台修改默认账号名与密码**（新密码至少 12 个字符）：通过本机回环地址（`127.0.0.1` / `localhost` / `::1`）访问时后台展示醒目提醒横幅、不阻断操作；当监听或访问非回环真实地址（如局域网/公网 IP、`0.0.0.0` 或远端 `NCC_PUBLIC_ORIGIN` / `Host`）时，系统将在完成账号与密码修改前强制拦截全部业务接口（`403 credential_change_required`）。

常用启动参数：

| 参数 | 说明 |
|---|---|
| `--database {ncc-dev,ncc-pro}` | 选择目标数据库（未指定任何模式参数时默认 `ncc-pro`；本地隔离调试用 `--database ncc-dev`，与 `--test`/`--production`/`--profile` 互斥） |
| `--check` / `--doctor` | 仅检查 Python 环境、前端构建产物与数据库连接状态并输出目标 `profile`/`database`/`origin` 后退出 |
| `--migrate` | 启动前显式执行当前目标数据库的迁移与内置领域种子定义安装 |
| `--create-user USERNAME` | 在当前目标数据库交互式安全创建后台账号并退出（首个账号自动设为系统管理员） |
| `--open` | Web 服务就绪后自动在默认浏览器打开工作台地址 |
| `--host HOST` / `--port PORT` | 自定义监听地址与端口（默认 `127.0.0.1:8761`） |
| `--web-only` / `--worker-only` | 仅启动 Web/API 服务，或仅启动后台任务 Worker |
| `--build-web` / `--no-build-web` | 强制重新构建前端，或缺少前端产物时不自动执行 `npm run build` |
| `--no-install` | 缺少 `.venv` 时不自动执行 `uv sync` |
| `--profile {local,production,test}` | 显式指定运行 profile（无模式参数时默认 `production` 连接 `ncc-pro`；也可用 `--production` 连接 `ncc-pro`，或 `--test` 使用 `ncc-dev` 与 `8788` 测试专用端口） |
| `--config PATH` | 显式指定配置文件路径（默认读取 `config/.env`） |
| `-v` / `--verbose` | 自检异常时打印完整错误详情 |

完整部署、模型配置、CLI工作副本与备份恢复说明见[数据后台使用指南](docs/guides/data-console.md)。

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
| DeepSeek Harness（DSH） | 项目内自动识别 `.agents/skills`；跨目录与 Web 界面通过 `package.json` + `cordis.patch.yml` 作为原生 Cordis bundle 安装并可在 Plugins 页一键启停 |

在 DeepSeek Harness（DSH）中安装到 `web`（或默认）profile，无需手工维护 `~/.dsh/skills/` 软链：

```bash
# 从本地工作区安装（或从远端安装：github:cloudxy/ncc-plugin）
dsh plugin --profile web add /path/to/ncc-workflow
```

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
| `start.py` | 跨平台启动器（支持 macOS 与 Windows，默认端口 `8761`） |
| `skills/` | 八个工作流入口、四个工程专业技能及其SOP、参考和模板 |
| `commands/` | 宿主命令入口 |
| `agents/` | 十二个创作角色，以及ncc-dev按需调用的产品经理、产品设计师、项目架构师和DBA |
| `workflow/registry/` | 阶段、角色、闸门、词表和路径的配置源 |
| `workflow/registry.json` | 由配置分片生成的兼容视图 |
| `workflow/contracts/` | 结构化产物的机器契约 |
| `scripts/cli/` | 书项目状态、机械检查、创作准备、判据评测与数据服务的命令行入口 |
| `scripts/ncclib/` | 按 `foundation`、`narrative`、`quality`、`assets`、`preparation`、`deconstruction`、`evaluation`、`cli` 细分的领域实现 |
| `scripts/dev/` | 按 `builders`（生成）、`checkers`（校验）、`routing`（工程角色派单）细分的研发工具 |
| `scripts/tests/` | 按领域用途细分的标准库自测套件与 `fixtures/` 合成样例 |
| `src/ncc_data/` | 按领域、持久化、应用操作、创作执行和接口划分的后台；迁移归持久化 |
| `src/ncc_shared/` | 文件CLI与后台共用的配置、客户端、工作副本及评分实现 |
| `config/` | Dynaconf公共默认与环境覆盖；私有连接值归 `config/.env` |
| `tests/` | 按子用途细分的 `unit/`（无库单元）、`backend/`（PostgreSQL集成）、`browser/`（Chromium验收）与 `support/`（共用环境） |
| `apps/management-web/` | 创作台与专业资料管理前端 |
| `package.json`、`cordis.patch.yml` | DeepSeek Harness（DSH）原生 Cordis bundle 清单与技能挂载补丁（白名单打包，零外部依赖） |
| `docs/` | 公开的使用指南、工程规范、模块设计与产品层说明（本地任务与证据忽略不入仓） |
| `eval/` | 审稿评测的锚定样章与评测说明 |
| `novels/` | 默认私有书库：书项目、准备工作区和拆书库 |

书稿、原著、素材、书内状态以及含本机环境路径的开发任务与验证证据均属私有或本地数据。`novels/`、`books/`、`_作者/`、`_拆书库/`、`docs/tasks/`、`docs/evidence/` 已加入忽略规则并由提交守卫检查。拆书产物保存短定位证据，技法与场次使用自己的话概括。

## 开发与文档

维护插件使用 `/ncc-dev <目标>`；恢复开发任务使用 `/ncc-dev continue <任务号>`。开发流程见[工程规范](docs/engineering/workflow.md)，代码归属见[目录与复用规范](docs/engineering/code-layout.md)，项目设计见[架构说明](workflow/architecture.md)和[信息架构原则](workflow/principles.md)，其余文档从[文档导航](docs/README.md)查找。

在仓库根目录按改动范围选择检查：

```bash
python3 -m unittest discover -s scripts/tests -t scripts -p 'test_*.py'
python3 scripts/dev/builders/build_registry.py --check
python3 scripts/dev/checkers/check_plugin.py -v
python3 scripts/dev/builders/build_docs.py --check
```

配置值在 `workflow/registry/` 的对应分片中修改，再依次运行 `scripts/dev/builders/build_registry.py` 和 `scripts/dev/builders/build_docs.py` 更新生成文件。纯文档改动核对内容、链接和生成格式；功能与规则变更按影响范围验证。
