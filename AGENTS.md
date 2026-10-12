# AGENTS.md — ncc-workflow（插件仓库）

Novel Create Center（ncc-workflow）：长篇网文从立书到收束的创作工作流插件，v3.2.0。上游 https://github.com/cloudxy/ncc-plugin ，本目录是它的 git 工作树；写作工作区（书项目、素材、拆书库所在处）在本仓库之外，经软链或插件安装消费这里的内容。

## 同步纪律（钩子强制）

**先拉后推**：远端 main 领先时推送会被 `.githooks/pre-push` 拒绝。正确顺序：

```bash
git pull                         # 1. 先拉取远端并合并（有冲突先解决）
git add … && git commit -m "…"   # 2. 提交
git push                         # 3. 推 main
```

**私有内容守卫**：`.githooks/pre-commit` 拒绝任何命中书项目标记（`book.json`、`prepare.json`、`02-大纲/`…`07-导出/`、`_拆书库/`、`_作者/`、`novels/`、`books/`）的暂存文件——书稿与素材是调试数据，绝不进本仓库。

## 布局

```
├── workflow/      唯一事实源 registry.json（状态机/闸门/决策点）+ principles/architecture
├── skills/        七技能：ncc（经理窗口）、ncc-prepare、ncc-new、ncc-write、ncc-review、ncc-deconstruct、ncc-eval
├── commands/      对应斜杠命令
├── agents/        十二角色：scout、worldbuilder、outliner、writer、editor、story-editor、continuity、pulse、reader、scholar、deconstructor、curator
├── scripts/       ncc_state.py、ncc_prepare.py、check_chapter.py、ncc_eval.py 等
├── docs/          usage.md 使用指南；eval/anchors/ 锚定章样章
├── .zcode-plugin/ .claude-plugin/ plugin.json .agents/plugins/marketplace.json
│                  打包清单：zcode / claude+grok / codex 可移植 / codex 市场，四种宿主格式
└── .githooks/     pre-commit（私有内容守卫）+ pre-push（先拉后推）
```

## 多 CLI 接入（消费方视角）

本仓库的技能、命令、角色可被五套 CLI 直接使用，无需安装：

- **项目级软链**（推荐）：消费工作区里把 `.claude/{skills,commands,agents}/`、`.agents/{skills,agents}/`、`.grok/agents/` 软链指向本仓库对应目录——claude、grok、codex、kimi 均按各自约定扫描这些目录，改动实时生效。codex 与 kimi 官方项目级目录就是 `.agents/skills/`。
- **插件式安装**：zcode 放入 local-plugins；claude/grok 用 `plugin install <本仓库路径>`（读 `.claude-plugin/`）；codex 用 `codex plugin marketplace add <本仓库路径>`（读根 `plugin.json` 与 `.agents/plugins/marketplace.json`）。

被当作子代理派单时，按 `agents/<role>.md` 的角色定义执行并回报，不越界（写手不看审稿清单、审稿不写稿、试读读者盲读）。

## 自测

```bash
python3 -m unittest discover -s scripts -p 'test_*.py'   # 全量（115 项）
python3 scripts/check_plugin.py -v                       # 一致性
```

改动后必须跑全量自测；`workflow/registry.json`、`skills/`、`agents/` 属工作流规则变更，需过 `ncc-eval 回归` 再由作者确认。
