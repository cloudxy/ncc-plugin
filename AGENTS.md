# AGENTS.md — novel_wk（ncc-workflow 工作区）

Novel Create Center（ncc-workflow）：长篇网文从立书到收束的创作工作流插件，v3.2.0。本目录既是日常创作工作区，也是 ncc-workflow 的**开发与编辑现场**——流程文件（skills/agents/commands/scripts/workflow）就在这里更新。上游 https://github.com/cloudxy/ncc-plugin 是唯一共同源；zcode 已安装插件在 `~/.zcode/local-plugins/ncc-workflow`（独立 git 克隆，与本目录区分开，两边改动都经 GitHub 互通）。

## 目录

```
novel_wk/
├── workflow/      工作流唯一事实源 registry.json（状态机/闸门/决策点）+ principles/architecture
├── skills/        七技能：ncc（经理窗口）、ncc-prepare、ncc-new、ncc-write、ncc-review、ncc-deconstruct、ncc-eval
├── commands/      对应斜杠命令
├── agents/        十二角色：scout、worldbuilder、outliner、writer、editor、story-editor、continuity、pulse、reader、scholar、deconstructor、curator
├── scripts/       ncc_state.py、ncc_prepare.py、check_chapter.py、ncc_eval.py 等
├── docs/          usage.md 使用指南；eval/anchors/ 锚定章样章
├── novels/        书库根目录：书项目、准备工作区、拆书库都放这里（私有，绝不进仓库）
├── .claude/ .agents/ .grok/                          各 CLI 项目级软链 → 仓内 skills/commands/agents
├── .zcode-plugin/ .claude-plugin/ plugin.json .agents/plugins/marketplace.json
│                                                    打包清单：zcode / claude+grok / codex / codex 市场四种宿主格式
└── .githooks/     pre-commit（先拉取校验+私有内容守卫）+ pre-push（先拉后推）
```

## 五套 CLI 接入（全部项目级，改文件即时生效）

| CLI | 挂载点 | 入口 |
|---|---|---|
| claude | `.claude/skills` `.claude/commands` `.claude/agents`（软链） | `/ncc`、`/ncc-write` 等同名命令 |
| codex | `.agents/skills`（官方项目级约定） | `/` 菜单技能，或直接描述意图 |
| kimi | `.agents/skills`、`.agents/agents` | `/skill:ncc`、`/skill:ncc-write` |
| grok | `.claude/skills`+`.claude/commands`（claude 兼容）、`.agents/skills`、`.grok/agents` | `/` 菜单命令与技能 |
| zcode | `~/.zcode/local-plugins/ncc-workflow`（独立克隆，`git pull` 更新） | `/ncc`、`/ncc-new`、`/ncc-write`、`/ncc-review`、`/ncc-prepare`、`/ncc-deconstruct`、`/ncc-eval` |

被当作子代理派单时，按 `agents/<role>.md` 的角色定义执行并回报，不越界（写手不看审稿清单、审稿不写稿、试读读者盲读）。

## 同步纪律（钩子强制）

**先拉后提交**：`.githooks/pre-commit` 在每次提交前 fetch origin/main，远端领先即阻止并要求先 `git pull` 合并；它同时拦截任何命中书项目标记（`book.json`、`prepare.json`、`02-大纲/`…`07-导出/`、`_拆书库/`、`_作者/`、`novels/`、`books/`）的暂存文件。pre-push 再兜一道。

```bash
git pull                         # 1. 先拉取远端并合并
git add … && git commit -m "…"   # 2. 提交（钩子自动验拉取与私有内容）
git push                         # 3. 推 main
```

zcode 插件副本更新：`cd ~/.zcode/local-plugins/ncc-workflow && git pull`；在那边的改动同样要走 pull→commit→push 回 GitHub。

## 私有内容（硬约束）

书稿与素材是调试与完善 ncc-workflow 的数据，**绝不能上传远端仓库**。`novels/`、`books/`、`_作者/`、`_拆书库/` 已在 `.gitignore`/`.zcodeignore` 忽略并由 pre-commit 守卫兜底。

## 常用意图

开书 `/ncc-new <一句话想法>`；进度 `/ncc status`；续写 `/ncc-write 接着写`；攒稿 `/ncc-write 今更3章`；审稿 `/ncc-review 第N章`；全书体检 `/ncc-review 全书`；准备（无需建书）`/ncc-prepare …`；拆书 `/ncc-deconstruct <原著路径>`；评测 `/ncc-eval 回归`。完整对照表见 `docs/usage.md`。

## 自测

```bash
python3 -m unittest discover -s scripts -p 'test_*.py'   # 全量（115 项）
python3 scripts/check_plugin.py -v                       # 一致性
```

改动后必须跑全量自测；`workflow/registry.json`、`skills/`、`agents/` 属工作流规则变更，需过 `ncc-eval 回归` 再由作者确认。
