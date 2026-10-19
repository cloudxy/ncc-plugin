# AGENTS.md — ncc-workflow 工作区

Novel Create Center（ncc-workflow）：长篇网文从立书到收束的创作工作流插件，v4.0.0。本目录既是日常创作工作区，也是 ncc-workflow 的**开发与编辑现场**——流程文件（skills/agents/commands/scripts/workflow）就在这里更新。上游 https://github.com/cloudxy/ncc-plugin 是唯一共同源；zcode 经 `~/.zcode/cli/config.json` 的 `plugins.dirs` 直接注册本目录加载（2026-10-17 起替代 `~/.zcode/local-plugins/ncc-workflow` 独立克隆；其他机器仍可注册该克隆，两边改动经 GitHub 互通）。

## 目录

```
ncc-workflow/
├── workflow/      registry/ 分片事实源 + registry.json 兼容生成视图；principles/architecture
├── skills/        七个创作技能、ncc-dev开发入口与四个工程专业技能
├── commands/      对应斜杠命令
├── agents/        十二个创作角色；四工程角色：product-manager、product-designer、project-architect、dba
├── scripts/       运行入口与 ncclib/；dev/ 开发工具；tests/ 测试（顶层保留旧工具薄入口）
├── src/           ncc_shared/ 跨入口共享（配置按需Dynaconf）；ncc_data/ 分层后台与只读MCP
├── config/        default/settings.toml 默认配置；<ENV>/settings.toml 按需覆盖；私有值归config/.env
├── apps/          management-web/ 前端：app装配、features页面、shared共用
├── tests/         unit/ 无库单元；backend/ 后端；browser/ 浏览器；support/ 共用环境
├── docs/          README.md 导航；guides/ 使用指南；engineering/ 工程规范；designs/ 按模块设计；tasks/ 活动任务；evidence/ 验证证据
├── eval/          anchors/ 锚定章样章与评测说明
├── novels/        书库根目录：书项目、准备工作区、拆书库都放这里（私有，绝不进仓库）
├── .claude/ .agents/ .grok/                          各 CLI 项目级软链 → 仓内 skills/commands/agents
├── .zcode-plugin/ .claude-plugin/ plugin.json .agents/plugins/marketplace.json
│                                                    打包清单：zcode / claude+grok / codex / codex 市场四种宿主格式
└── .githooks/     pre-commit（先拉取校验+私有内容守卫）+ pre-push（先拉后推）
```

文档只保留现行说明、仍有效的设计依据和在执行方案。过期或被替代的计划直接删除，并同步清理引用；历史由 Git 保留，不新增迁出占位文件或重复归档。

第三方项目作为设计参考，不进入本项目的受管依赖、打包或必需运行链。来源与致谢集中在 `ACKNOWLEDGMENTS.md`；具体设计注明参考的技能/机制、版本依据、转化与落点。使用者按文档自行下载至仓外目录；不为参考来源新增 vendor、锁文件或自动更新管控。具体材料借用如实标明并遵守其许可。

## 五套 CLI 接入（全部项目级，改文件即时生效）

| CLI | 挂载点 | 入口 |
|---|---|---|
| claude | `.claude/skills` `.claude/commands` `.claude/agents`（软链） | `/ncc`、`/ncc-write` 等同名命令 |
| codex | `.agents/skills`（官方项目级约定） | `/` 菜单技能，或直接描述意图 |
| kimi | `.agents/skills`、`.agents/agents` | `/skill:ncc`、`/skill:ncc-write` |
| grok | `.claude/skills`+`.claude/commands`（claude 兼容）、`.agents/skills`、`.grok/agents` | `/` 菜单命令与技能 |
| zcode | 本目录（`plugins.dirs` 直注册；其他机器可用独立克隆 `~/.zcode/local-plugins/ncc-workflow`，`git pull` 更新） | `/ncc`、`/ncc-new`、`/ncc-write`、`/ncc-review`、`/ncc-prepare`、`/ncc-deconstruct`、`/ncc-eval`、`/ncc-dev` |

被当作子代理派单时，按 `agents/<role>.md` 的角色定义执行并回报，不越界（写手不看审稿清单、审稿不写稿、试读读者盲读）。

## 同步纪律（钩子强制）

**先拉后提交**：`.githooks/pre-commit` 在每次提交前 fetch origin/main，远端领先即阻止并要求先 `git pull` 合并；它同时拦截任何命中书项目标记（`book.json`、`prepare.json`、`02-大纲/`…`07-导出/`、`_拆书库/`、`_作者/`、`novels/`、`books/`）的暂存文件。pre-push 再兜一道。

```bash
git pull                         # 1. 先拉取远端并合并
git add … && git commit -m "…"   # 2. 提交（钩子自动验拉取与私有内容）
git push                         # 3. 推 main
```

zcode 插件更新：本机直注册本目录，源文件改完开新会话即加载，无副本同步；其他机器的独立克隆仍走 `cd ~/.zcode/local-plugins/ncc-workflow && git pull`，在那边的改动同样要走 pull→commit→push 回 GitHub。

## 私有内容（硬约束）

书稿与素材是调试与完善 ncc-workflow 的数据，**绝不能上传远端仓库**。`novels/`、`books/`、`_作者/`、`_拆书库/` 已在 `.gitignore`/`.zcodeignore` 忽略并由 pre-commit 守卫兜底。

## 常用意图

开书 `/ncc-new <一句话想法>`；进度 `/ncc status`；续写 `/ncc-write 接着写`；攒稿 `/ncc-write 今更3章`；审稿 `/ncc-review 第N章`；全书体检 `/ncc-review 全书`；准备（无需建书）`/ncc-prepare …`；拆书 `/ncc-deconstruct <原著路径>`；评测 `/ncc-eval 回归`。完整对照表见 `docs/guides/usage.md`。

## 插件开发

升级或修复插件使用 `/ncc-dev <目标>`，恢复用 `/ncc-dev continue <任务号>`。开发路径、阶段、证据与交付规范唯一见 [docs/engineering/workflow.md](docs/engineering/workflow.md)；小说创作继续使用原七技能。规则候选先隔离验证，完成回归后呈作者确认。

新开发任务在D1通过scripts/dev/development.py记录影响和按需角色计划，实际执行选中的工程角色并登记报告。角色定义与触发在registry的development域，与十二创作角色分开；纯文档不增加工程派单。派单绑定输入字节，缺失/失败/陈旧报告不能通过交付检查。作者已经授权的角色接线实施直接执行，不重复要求批准同一范围。

配置使用Dynaconf，按默认文件、兼容进程值、环境文件、`config/.env`的顺序覆盖，初始化不覆盖原值；只允许一个正式库及其同连接的`正式库-test`。不得另建每次测试/评审/恢复专用数据库，不更换既定PostgreSQL参数。代码归属和复用规则见[代码归属规范](docs/engineering/code-layout.md)，操作见[数据后台指南](docs/guides/data-console.md)。

## 自测

```bash
python3 -m unittest discover -s scripts/tests -t scripts -p 'test_*.py'   # 全量（实际数量以当次输出为准）
python3 scripts/dev/build_registry.py --check            # 分片与兼容视图
python3 scripts/dev/check_plugin.py -v                       # 一致性
```

测试按实际影响范围选择：纯文档、注释、排版或不改变功能的路径调整，只检查内容、链接与必要接线；局部修复和新增功能，只测试受影响部分及相邻接口；大范围重构、跨模块行为或核心数据契约变化，才运行全量自测。上面的命令是全量检查入口，不是每次编辑的必跑清单。

`workflow/registry/`（源）、`workflow/registry.json`（生成视图）、`skills/`、`agents/` 的修改按语义影响判断：只改文字、链接或目录定位不触发模型回归；改变创作标准、闸门、角色职责或审稿判据时，做对应行为回归，涉及审稿判据再运行 `ncc-eval`。规则候选完成相应验证后由作者确认。任务记录写明影响范围、所选检查及结果，不因文件名或目录归属机械扩大测试。
