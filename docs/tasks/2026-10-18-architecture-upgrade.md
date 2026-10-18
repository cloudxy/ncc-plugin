# 架构升级实施

承接[方案复核任务](2026-10-18-architecture-plan.md)，实施[架构成长方案](../designs/engineering/architecture-growth.md)。本次是新执行批次，单独记录实现候选与证据，不覆盖原方案的验证历史。

plugin_root/repo_root 均为 /Users/xuyun/Documents/ncc-workflow，main，插件 3.2.0。原工作树有未提交的文档整理与开发入口改动，已保存受管源基线到仓外临时目录，不读私有书库，不清理在途差异。作者本轮整体实施授权覆盖现行方案具体推荐，按 G0 → G1 → G2 → G5 → G3a/G3b 连续推进；G4 文档归属已经补齐，拆书 P1–P6 业务升级是后续独立任务。

## 执行与验收

沿用现行方案各阶段的文件矩阵、反例、兼容与回滚，不复制计划正文。跨模块改造运行全量测试；清单批先运行局部反例。用实施前真实工作树冻结 CLI 完整解析契约与帮助、registry 对象/顺序、生成文件和运行行为；每批比较后推进。保留三条旧开发脚本入口与旧测试发现方式。

实施与自查由当前会话执行，无独立代码评审代理授权，不冒称独立评审；宿主新会话无法核验时保留 unverified。规则语义保持不变，路径和来源说明调整无需无关模型回归。未授权提交、推送或其他机器同步。

回滚依赖与步骤见方案；基线副本包含已有有效脏改动，回退只撤销本任务增量。任务 JSON 的 scope 随每批实际产品文件更新，旧差异只有在本批真正触及后才从 foreign_changes 转入 scope。

## 当前结果与边界

G0/G1/G2/G5/G3a/G3b 已按批实现及验证。开发实现位于 scripts/dev，测试位于 scripts/tests，三条旧工具命令继续转发；CLI 注册分为七个模块；七个 registry 源片经统一 loader 读取，原 registry.json 保留为原子生成的兼容视图。schema、词表、闸门、角色规则和业务输出保持等价。G4 的拆书 P1 落点已接入现行架构，P1–P6 新业务仍是后续任务。

最终全量 180 项通过，旧测试发现方式同样收集 180 项且包含原始 151 项；102 个导出常量、140 个解析/帮助路径、11 组运行/文件状态、12 个生成区块正文及 agents/commands 对照通过。15 项 registry 反例包含无效 UTF-8/换行恢复、重复/缺失/错归属及替换失败保护。机械六场景、清单/生成检查、60 条软链及干净公开副本冒烟通过。详细输入、实际结果、限制和日志见[验证报告](../evidence/2026-10-18-architecture-upgrade/validation.md)。

作者本轮明确测试将单独进行：本次实现流程的独立评审与五端加载由作者接手，未实测项保持未验证；已有 180 项通过属于前次冻结候选的历史证据，不在本轮重复运行。未提交、未推送、未同步其他机器。若继续发布，先继承有效授权、核对远端合并及候选新鲜度，不能把其他在途文档变更一并误交付。

## 本轮收尾与作者验证交接

按作者“拆书 P1–P6 功能升级属于后续任务；先将流程完成，测试单独进行”的指令，本轮架构实现与本地交付整理完成。拆书临时候选未合入工作树，P1–P6 不在本次交付中，也不自动启动后续实施。当前停在 D5 的作者验证交接；不把实现完成写成独立评审、五端加载或发布完成。

| 项目 | 当前状态 | 后续办法 |
|---|---|---|
| 架构实现与确定性检查 | 本地候选已完成；历史 180 项通过 | 产品候选保持下方 fingerprint；本轮未重跑测试 |
| 独立评审 | 待作者安排 | 按方案逐批核对意图、实现、反例、兼容与回滚；记录评审输入候选和问题处置 |
| claude / codex / kimi / grok / zcode 新会话 | 五端均未验证 | 各开新会话核对实际加载根、版本、入口发现、参数转入、代表调用与任务恢复；grok 另查重复发现与优先级 |
| 拆书 P1–P6 | 后续任务，未合入 | 作者另行启动时从拆书方案 P1 开始，独立记录契约、实现与验证 |
| 提交、推送与其他机器同步 | 未请求、未执行 | 取得发布授权后按现行工作流先拉取合并，再核对候选、精确提交与推送 |

作者测试入口保留如下，供单独验证时选用，本轮不执行：

```bash
python3 -m unittest discover -s scripts/tests -t scripts -p 'test_*.py'
python3 scripts/dev/build_registry.py --check
python3 scripts/dev/check_plugin.py -v
python3 scripts/dev/build_docs.py --check
python3 scripts/ncc_eval.py mech
```

测试或评审若发现问题，记录复现步骤并回 D3 修复；产品发生变化后重新冻结候选，重做受影响检查，不沿用旧候选的 passed。作者验证结果尚未收到时保留本节待验状态。

```ncc-dev-json
{
  "schema": 1,
  "id": "2026-10-18-architecture-upgrade",
  "goal": "按已修订方案实施 G1/G2/G5/G3a/G3b 架构升级，保留 G4 拆书 P1 归属与既有接口",
  "route": "architectural",
  "risk_tags": [],
  "repo_root": "/Users/xuyun/Documents/ncc-workflow",
  "plugin_root": "/Users/xuyun/Documents/ncc-workflow",
  "branch": "main",
  "base_commit": "0e3faa03f05f05524442c870c0fafda134e0d8b4",
  "stage": "D5",
  "next": "架构实现与交付整理完成，等待作者单独测试、独立评审和五端新会话验证；收到结果后处理缺陷。拆书 P1–P6 留作后续独立任务，本轮不实施、不合入、不重跑测试；未授权提交或推送。",
  "blocked": "",
  "decisions": [
    {
      "source": "作者 2026-10-18 本轮请求",
      "scope": "按照修订后的升级方案实施；采用 D1 延后、D2 现有版本源加校验、D3 不改键/不退役、D4 分片加生成兼容视图。未要求发布。"
    },
    {
      "source": "作者本轮指令：先将流程完成，测试会单独进行",
      "scope": "仅收尾已有架构升级，拆书 P1–P6 明确留作后续独立任务，不合入临时候选。已有架构实现与历史证据保留；独立评审、五端新会话和后续测试交作者单独执行，不再次启动测试，不把待验项标为通过。本指令不是提交/推送授权。"
    }
  ],
  "spec": "docs/designs/engineering/architecture-growth.md",
  "plan": "docs/designs/engineering/architecture-growth.md",
  "scope": [
    "AGENTS.md",
    "README.md",
    "docs/README.md",
    "docs/designs/deconstruction/upgrade.md",
    "docs/designs/engineering/architecture-growth.md",
    "docs/engineering/documentation.md",
    "docs/engineering/workflow.md",
    "scripts/build_docs.py",
    "scripts/check_dev_workflow.py",
    "scripts/check_plugin.py",
    "scripts/dev/__init__.py",
    "scripts/dev/build_docs.py",
    "scripts/dev/build_registry.py",
    "scripts/dev/check_dev_workflow.py",
    "scripts/dev/check_plugin.py",
    "scripts/ncc_prepare.py",
    "scripts/ncclib/cli.py",
    "scripts/ncclib/cli_parsers/__init__.py",
    "scripts/ncclib/cli_parsers/book.py",
    "scripts/ncclib/cli_parsers/deconstruction.py",
    "scripts/ncclib/cli_parsers/delivery.py",
    "scripts/ncclib/cli_parsers/learning.py",
    "scripts/ncclib/cli_parsers/ledgers.py",
    "scripts/ncclib/cli_parsers/loops.py",
    "scripts/ncclib/cli_parsers/scenes.py",
    "scripts/ncclib/core.py",
    "scripts/ncclib/registry.py",
    "scripts/test_dev_workflow.py",
    "scripts/test_ncc_library.py",
    "scripts/test_ncc_prepare.py",
    "scripts/test_ncc_state.py",
    "scripts/test_v3_regressions.py",
    "scripts/tests/__init__.py",
    "scripts/tests/_behavior_probe.py",
    "scripts/tests/_cli_contract.py",
    "scripts/tests/fixtures/cli-contract.json",
    "scripts/tests/fixtures/runtime-contract.json",
    "scripts/tests/test_architecture.py",
    "scripts/tests/test_dev_workflow.py",
    "scripts/tests/test_ncc_library.py",
    "scripts/tests/test_ncc_prepare.py",
    "scripts/tests/test_ncc_state.py",
    "scripts/tests/test_plugin_manifests.py",
    "scripts/tests/test_registry.py",
    "scripts/tests/test_v3_regressions.py",
    "skills/ncc-deconstruct/SKILL.md",
    "skills/ncc-dev/SKILL.md",
    "skills/ncc-new/references/worldbuilding.md",
    "skills/ncc/SKILL.md",
    "skills/ncc/references/book-layout.md",
    "skills/ncc/references/book-state.md",
    "skills/ncc/references/loops.md",
    "skills/ncc/references/memory.md",
    "skills/ncc/references/stage-map.md",
    "workflow/architecture.md",
    "workflow/principles.md",
    "workflow/registry.json",
    "workflow/registry/delivery.json",
    "workflow/registry/flow.json",
    "workflow/registry/learning.json",
    "workflow/registry/preparation.json",
    "workflow/registry/roles.json",
    "workflow/registry/rules.json",
    "workflow/registry/storage.json"
  ],
  "foreign_changes": {
    "ACKNOWLEDGMENTS.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/designs/engineering/architecture-audit.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/designs/engineering/source-audit.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/designs/engineering/workflow.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/designs/memory/memory-evolution-design.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/designs/preparation/preparation-design.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/dev-workflow.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/dev/2026-10-12-ncc-dev-plan.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/dev/evidence/2026-10-12-ncc-dev/anchors.log": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/dev/evidence/2026-10-12-ncc-dev/author.log": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/dev/evidence/2026-10-12-ncc-dev/behavior.log": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/dev/evidence/2026-10-12-ncc-dev/deterministic-before-independent-fixes.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/dev/evidence/2026-10-12-ncc-dev/deterministic-isolated.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/dev/evidence/2026-10-12-ncc-dev/deterministic.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/dev/evidence/2026-10-12-ncc-dev/review.log": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/dev/tasks/2026-10-12-ncc-dev.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/engineering/source-vetting.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/evidence/2026-10-12-ncc-dev/anchors.log": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/evidence/2026-10-12-ncc-dev/author.log": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/evidence/2026-10-12-ncc-dev/behavior.log": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/evidence/2026-10-12-ncc-dev/deterministic-before-independent-fixes.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/evidence/2026-10-12-ncc-dev/deterministic-isolated.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/evidence/2026-10-12-ncc-dev/deterministic.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/evidence/2026-10-12-ncc-dev/review.log": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/evidence/2026-10-12-ncc-dev/task.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/evidence/2026-10-13-readme-refresh/validation.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/evidence/2026-10-16-deconstruction-docs/validation.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/evidence/2026-10-16-docs-refresh/validation.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/evidence/2026-10-17-zcode-registration/validation.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/evidence/2026-10-18-architecture-plan/recheck.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/evidence/2026-10-18-architecture-plan/validation.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/guides/usage.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/superpowers/specs/2026-10-12-dev-workflow-audit.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/superpowers/specs/2026-10-12-dev-workflow-design.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/tasks/2026-10-12-readme-refresh.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/tasks/2026-10-16-deconstruction-docs.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/tasks/2026-10-16-docs-refresh.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/tasks/2026-10-17-zcode-registration.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/tasks/2026-10-18-architecture-plan.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "docs/usage.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "workflow/memory-evolution-design.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "workflow/preparation-design.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动",
    "workflow/source-vetting.md": "实施开始前已存在的方案、文档治理、入口/接线差异；本任务仅在确实叠加修改时纳入 scope，保留旧改动"
  },
  "evidence_paths": [
    "docs/evidence/2026-10-18-architecture-upgrade/validation.md",
    "docs/evidence/2026-10-18-architecture-upgrade/unit.log",
    "docs/evidence/2026-10-18-architecture-upgrade/baseline.log"
  ],
  "candidate": {
    "base_commit": "0e3faa03f05f05524442c870c0fafda134e0d8b4",
    "files": [
      {
        "path": "AGENTS.md",
        "type": "file",
        "sha256": "7951d74c2bccf0f1cb1d2e34ae35828c45898651d81465bd6f12314f1195e391",
        "executable": false
      },
      {
        "path": "README.md",
        "type": "file",
        "sha256": "a8ed9d9ad247eb60f57a674f8f47488c6fb0cf99e6e978f74c5c824f480c0f27",
        "executable": false
      },
      {
        "path": "docs/README.md",
        "type": "file",
        "sha256": "f1e3eec662f56384d1544d30c6568ba585c88db982b873c9e83fe453c96598af",
        "executable": false
      },
      {
        "path": "docs/designs/deconstruction/upgrade.md",
        "type": "file",
        "sha256": "72f02b1770b44f841b80292a53a46a04df9355219c4bbe7ea3ec0c1d1c9f0f3a",
        "executable": false
      },
      {
        "path": "docs/designs/engineering/architecture-growth.md",
        "type": "file",
        "sha256": "d7cb9c37cad7492b6620c660ef05df02f35650fdce9f5d6b4d2b778b8e9c173c",
        "executable": false
      },
      {
        "path": "docs/engineering/documentation.md",
        "type": "file",
        "sha256": "4accd459a910229d21253ca43c07d5aafb14cdae83340815b7f58041430d82af",
        "executable": false
      },
      {
        "path": "docs/engineering/workflow.md",
        "type": "file",
        "sha256": "84e9e517995b76ff906ba5640e015b79e8745c045a1a717f1724b918123e9cbb",
        "executable": false
      },
      {
        "path": "scripts/build_docs.py",
        "type": "file",
        "sha256": "ebc0d58c98fc712164772018ebdd92610fd64ccc4175c5a04e6f1ff4895d26a0",
        "executable": false
      },
      {
        "path": "scripts/check_dev_workflow.py",
        "type": "file",
        "sha256": "d239a072722d28291cc99e0a0c567d30c827c3b6fe2b0c0eeb9128066b944528",
        "executable": false
      },
      {
        "path": "scripts/check_plugin.py",
        "type": "file",
        "sha256": "f5fcb23db37540c76105aa94a8308336c3972235058828cec157781415f711da",
        "executable": false
      },
      {
        "path": "scripts/dev/__init__.py",
        "type": "file",
        "sha256": "f9b6e2e97d92e5fda9520902fbd4f4f2a5e850f7e11dee5f03f2e27a04f3a208",
        "executable": false
      },
      {
        "path": "scripts/dev/build_docs.py",
        "type": "file",
        "sha256": "726c65ac15b0aaedca18abeea8e6c01825f315761c99a17d5553834924173ff0",
        "executable": false
      },
      {
        "path": "scripts/dev/build_registry.py",
        "type": "file",
        "sha256": "1848cf8d8de29a54de62ff9bb2fb7ce8b4e6a786da6d1be70d7d05cc01b5eac1",
        "executable": false
      },
      {
        "path": "scripts/dev/check_dev_workflow.py",
        "type": "file",
        "sha256": "739e7afaf000eb880d4433bbb343b886ba1f0a54f41614621b50f851f3c165ff",
        "executable": false
      },
      {
        "path": "scripts/dev/check_plugin.py",
        "type": "file",
        "sha256": "05c2f033d7f82aa4ff8bbcb96e4e16fe7372e0d70afdea703d006fd704b76d89",
        "executable": false
      },
      {
        "path": "scripts/ncc_prepare.py",
        "type": "file",
        "sha256": "eb58ab96135b5a27bfc1e1a0b76bd7cb220b491b4ce6df1f06a3459d25f37453",
        "executable": false
      },
      {
        "path": "scripts/ncclib/cli.py",
        "type": "file",
        "sha256": "25680028bbd4e3b0d05eb12e7c66a131b3193b0fc57967ab2c505ab21a77472c",
        "executable": false
      },
      {
        "path": "scripts/ncclib/cli_parsers/__init__.py",
        "type": "file",
        "sha256": "c5c1cceb710ba8daeb4a308562572c1992034a808640722445313cc4a2d699db",
        "executable": false
      },
      {
        "path": "scripts/ncclib/cli_parsers/book.py",
        "type": "file",
        "sha256": "db763bd16d6cb2c88b10007ec858d04b2fa004d147e54857ec05ddda86d8e1f9",
        "executable": false
      },
      {
        "path": "scripts/ncclib/cli_parsers/deconstruction.py",
        "type": "file",
        "sha256": "3bcf9a4f3e65702da3fa5179feb4389b6d291bbff38e7602c4e3b93a91e44a5c",
        "executable": false
      },
      {
        "path": "scripts/ncclib/cli_parsers/delivery.py",
        "type": "file",
        "sha256": "26096b2b144d3da900b2e1893e876623aa8bd34fd0d90e9ba58c1eb0138575bc",
        "executable": false
      },
      {
        "path": "scripts/ncclib/cli_parsers/learning.py",
        "type": "file",
        "sha256": "bd6fda6d6efe952ada39f69090579fd2f8ec002966687c33bce6ec3db1238bab",
        "executable": false
      },
      {
        "path": "scripts/ncclib/cli_parsers/ledgers.py",
        "type": "file",
        "sha256": "db7c6ee494b4b9816b5480f099259792ba0282a2270c818812f5d8b1a6d45a0b",
        "executable": false
      },
      {
        "path": "scripts/ncclib/cli_parsers/loops.py",
        "type": "file",
        "sha256": "2b390f280ab4ea96b2f92f787e459da4b80d17eb25db2212caadd53318ecabcd",
        "executable": false
      },
      {
        "path": "scripts/ncclib/cli_parsers/scenes.py",
        "type": "file",
        "sha256": "351a6a7743dd9484b7227c5d9fcd99a4abaa6a094dbd3d7c32dd834b6aaee5e1",
        "executable": false
      },
      {
        "path": "scripts/ncclib/core.py",
        "type": "file",
        "sha256": "b582c68dbe8ef8ccb09cf9a0d2b033eacace1444ba54b60dacb3d0b83dd33795",
        "executable": false
      },
      {
        "path": "scripts/ncclib/registry.py",
        "type": "file",
        "sha256": "660457477c7fdcdcb5d3511842bb569579d704e42935ba7bb6ddd988c27b8371",
        "executable": false
      },
      {
        "path": "scripts/test_dev_workflow.py",
        "type": "deleted"
      },
      {
        "path": "scripts/test_ncc_library.py",
        "type": "deleted"
      },
      {
        "path": "scripts/test_ncc_prepare.py",
        "type": "deleted"
      },
      {
        "path": "scripts/test_ncc_state.py",
        "type": "deleted"
      },
      {
        "path": "scripts/test_v3_regressions.py",
        "type": "deleted"
      },
      {
        "path": "scripts/tests/__init__.py",
        "type": "file",
        "sha256": "1f98cbf1b697283affbdc5dd1b68ec7cb480b4fc6165d85183126cef2a72de19",
        "executable": false
      },
      {
        "path": "scripts/tests/_behavior_probe.py",
        "type": "file",
        "sha256": "0836e546e74ceaceed68dc80dcdadba62480ee07ddaee49b67fb3e1a5d3f35d8",
        "executable": false
      },
      {
        "path": "scripts/tests/_cli_contract.py",
        "type": "file",
        "sha256": "0d4fcab62735e314376355ef78ec9c322b9bc47b4eec1ede93a6ab947b1a7b5f",
        "executable": false
      },
      {
        "path": "scripts/tests/fixtures/cli-contract.json",
        "type": "file",
        "sha256": "82d6159976ea78144bce00a4eddbf04dd70de47f9d7b456a648a8053c44aa8d8",
        "executable": false
      },
      {
        "path": "scripts/tests/fixtures/runtime-contract.json",
        "type": "file",
        "sha256": "1a0fb334d3283913c2b0a491338d831fbca64c3f5cd21363ee3f6a42c366cff8",
        "executable": false
      },
      {
        "path": "scripts/tests/test_architecture.py",
        "type": "file",
        "sha256": "d91a95081cb481fdb3013a6fe1a3e90e6b28d29255cb4a3b7eed5d2d4f33c675",
        "executable": false
      },
      {
        "path": "scripts/tests/test_dev_workflow.py",
        "type": "file",
        "sha256": "add011f18a7c147aa21273dffae073c7f4a77e3e5b06a1bb16bf4b4617431dea",
        "executable": false
      },
      {
        "path": "scripts/tests/test_ncc_library.py",
        "type": "file",
        "sha256": "361f84b669114b6c63ccb129b1ff04f165d6ecd5b120ae732a8efaabfbc17ad8",
        "executable": false
      },
      {
        "path": "scripts/tests/test_ncc_prepare.py",
        "type": "file",
        "sha256": "1f54b14ce1230841f5b30b84c7334eb3a2a68bd1504b8aa5cbd2049539e33169",
        "executable": false
      },
      {
        "path": "scripts/tests/test_ncc_state.py",
        "type": "file",
        "sha256": "05dde3d0bcaccae8a8002d727a0dad329e5a0b49fcd13a4634ff299c427155c9",
        "executable": false
      },
      {
        "path": "scripts/tests/test_plugin_manifests.py",
        "type": "file",
        "sha256": "bd64ed3999f43631fd4c5ea7bda748d04faa6b936fe16e7ab92c552f7a17f0fc",
        "executable": false
      },
      {
        "path": "scripts/tests/test_registry.py",
        "type": "file",
        "sha256": "48574cf08b5dc27ff958e9b7a3ed26174b042499ad1b6cb17fc4c8d77920f466",
        "executable": false
      },
      {
        "path": "scripts/tests/test_v3_regressions.py",
        "type": "file",
        "sha256": "14728ab3726c70f8cc7e5efc8fc66ba4ed565018d297bba0691a27fcbf8c95e2",
        "executable": false
      },
      {
        "path": "skills/ncc-deconstruct/SKILL.md",
        "type": "file",
        "sha256": "051326d91f2068c6bbb5173e0f7389338e66668da4ffd27e61122e4d071ff843",
        "executable": false
      },
      {
        "path": "skills/ncc-dev/SKILL.md",
        "type": "file",
        "sha256": "24d9ead8832068f0aa2811bc0a8793ee6ea0abe4124d17a73dca29caa65fe704",
        "executable": false
      },
      {
        "path": "skills/ncc-new/references/worldbuilding.md",
        "type": "file",
        "sha256": "62ac0130a5efd5a4167067761eefe56ae22a993f1b7b2bff38b4cb99579533db",
        "executable": false
      },
      {
        "path": "skills/ncc/SKILL.md",
        "type": "file",
        "sha256": "8cd465fda3741ad7fcf8edee62e6bef45e3c409363d4666f28ef94fab6f7cee1",
        "executable": false
      },
      {
        "path": "skills/ncc/references/book-layout.md",
        "type": "file",
        "sha256": "5b810ceb734cd088b7d6a7efcfa6b1eee661ee61816c036647ee9fbb5687ae28",
        "executable": false
      },
      {
        "path": "skills/ncc/references/book-state.md",
        "type": "file",
        "sha256": "0cd3ff633a7695c2679ab5c3b4263459a6c2f4aea5c80e9e5f4496cd118b34da",
        "executable": false
      },
      {
        "path": "skills/ncc/references/loops.md",
        "type": "file",
        "sha256": "39424438633a3d18d506a432dab10ec3d9a4f0a04593f710e67a1600fa2d522a",
        "executable": false
      },
      {
        "path": "skills/ncc/references/memory.md",
        "type": "file",
        "sha256": "bc6e707987475e223a4148e4fe5d98d78fd9ccf3e1c365211d7219d7c9e48b36",
        "executable": false
      },
      {
        "path": "skills/ncc/references/stage-map.md",
        "type": "file",
        "sha256": "cfd284964c1acb3793db2ff58e7b2e3d9c972d3eb7b98a59e8d80913031bf8c4",
        "executable": false
      },
      {
        "path": "workflow/architecture.md",
        "type": "file",
        "sha256": "bbebfd8ef26269bd84535fbe4083bb7d90766238988424e4cd75258cce835ebb",
        "executable": false
      },
      {
        "path": "workflow/principles.md",
        "type": "file",
        "sha256": "c63e2ed1f8bd4052d0559ba8cc8277c229d59a4050142b3cbf360fb12246d005",
        "executable": false
      },
      {
        "path": "workflow/registry.json",
        "type": "file",
        "sha256": "7892f62f261264d01cfa33b553bfc67c6fef7121ec5c5ca5f37c5f5985a3c4be",
        "executable": false
      },
      {
        "path": "workflow/registry/delivery.json",
        "type": "file",
        "sha256": "197a53501088b7ddefed97783ee59e19a0ed5e10f1b6a30a1c81229bb742b2de",
        "executable": false
      },
      {
        "path": "workflow/registry/flow.json",
        "type": "file",
        "sha256": "c60cccfabc66823aa3cfd874c58ae3055bb2542f0f5873b805c93815e9d857c2",
        "executable": false
      },
      {
        "path": "workflow/registry/learning.json",
        "type": "file",
        "sha256": "cefbbb66ef00eef9204c67fb6cded3f4f8cc64b066f4b00b14ea058adb6dca7d",
        "executable": false
      },
      {
        "path": "workflow/registry/preparation.json",
        "type": "file",
        "sha256": "b354ca94f5fb3648faa5604969f3b8e75b46b45b44fbab7f248abe95b20f9cb9",
        "executable": false
      },
      {
        "path": "workflow/registry/roles.json",
        "type": "file",
        "sha256": "cb364068ba690bb99009bd2d00c4a751003f14f3170e7acf0afca9af488fb8f8",
        "executable": false
      },
      {
        "path": "workflow/registry/rules.json",
        "type": "file",
        "sha256": "12c2640a1794f24856da46ca71c159da8f4507af0a10a2288412ea5d01cd15c7",
        "executable": false
      },
      {
        "path": "workflow/registry/storage.json",
        "type": "file",
        "sha256": "e073de066eab966183674ec295560715b485c25ce5170b9fe3b16394ee3d0ad5",
        "executable": false
      }
    ],
    "fingerprint": "627a7b135bbade386f3b87191a56d12801a387d5663405856e13204ecac01743"
  },
  "required": [
    "unit",
    "compatibility",
    "registry",
    "plugin",
    "docs",
    "mech"
  ],
  "evidence": [
    {
      "id": "unit-final",
      "kind": "unit",
      "candidate": "627a7b135bbade386f3b87191a56d12801a387d5663405856e13204ecac01743",
      "status": "passed",
      "command": "python3 -m unittest discover -s scripts/tests -t scripts -p 'test_*.py'",
      "exit_code": 0,
      "summary": "180 项通过，295.687 秒；全部原始 151 项保留，冻结原副本另跑 151 项通过",
      "environment": "macOS; Python 3.9.6; main; 本地冻结候选",
      "coverage": "全部运行、准备/治理、开发恢复、清单、CLI 兼容、registry 的确定性用例",
      "report": "docs/evidence/2026-10-18-architecture-upgrade/unit.log",
      "report_sha256": "a1f22772e88a372ba6e62d7d9bc0cd8595524baf88dc719a69eaf22a87f9addb"
    },
    {
      "id": "compat-final",
      "kind": "compatibility",
      "candidate": "627a7b135bbade386f3b87191a56d12801a387d5663405856e13204ecac01743",
      "status": "passed",
      "command": "全量中的 CliArchitectureTest/ToolMigrationTest；parser/constants/behavior 基线探针；公开副本启动检查",
      "exit_code": 0,
      "summary": "140 解析/帮助路径、102 常量、11 组运行状态、旧/新工具/发现路径和公开副本兼容通过",
      "environment": "macOS; Python 3.9.6; main; 本地冻结候选",
      "coverage": "命令输入/输出/退出与副作用、完整原始文件状态、跨 cwd/显式 --repo，业务字段仅归一时间和插件/工作根",
      "report": "docs/evidence/2026-10-18-architecture-upgrade/validation.md",
      "report_sha256": "33f20f5099ee77faaa5932a3c796da10bf658a879d4c62e1d32a76fec4d24709"
    },
    {
      "id": "registry-final",
      "kind": "registry",
      "candidate": "627a7b135bbade386f3b87191a56d12801a387d5663405856e13204ecac01743",
      "status": "passed",
      "command": "python3 -m unittest discover -s scripts/tests -t scripts -p test_registry.py; python3 scripts/dev/build_registry.py --check",
      "exit_code": 0,
      "summary": "15 项定向及最终全量通过；REGISTRY OK；原聚合文件逐字节相同",
      "environment": "macOS; Python 3.9.6; main; 本地冻结候选",
      "coverage": "七片41键归属、重复/缺失/未知/坏格式、陈旧/损坏视图、原子替换失败和幂等；schema不变",
      "report": "docs/evidence/2026-10-18-architecture-upgrade/validation.md",
      "report_sha256": "33f20f5099ee77faaa5932a3c796da10bf658a879d4c62e1d32a76fec4d24709"
    },
    {
      "id": "plugin-final",
      "kind": "plugin",
      "candidate": "627a7b135bbade386f3b87191a56d12801a387d5663405856e13204ecac01743",
      "status": "passed",
      "command": "python3 scripts/dev/check_plugin.py -v; Python 60 条宿主软链目标核对",
      "exit_code": 0,
      "summary": "PLUGIN OK；五份清单与60软链静态通过",
      "environment": "macOS; Python 3.9.6; main; 本地冻结候选",
      "coverage": "清单、引用、接线、读取预算；实际宿主新会话未验证",
      "report": "docs/evidence/2026-10-18-architecture-upgrade/validation.md",
      "report_sha256": "33f20f5099ee77faaa5932a3c796da10bf658a879d4c62e1d32a76fec4d24709"
    },
    {
      "id": "docs-final",
      "kind": "docs",
      "candidate": "627a7b135bbade386f3b87191a56d12801a387d5663405856e13204ecac01743",
      "status": "passed",
      "command": "python3 scripts/dev/build_docs.py --check; git diff --check; Python 生成正文与全部候选空白对照",
      "exit_code": 0,
      "summary": "DOCS OK；12个规则生成正文、角色/命令元数据不变；文档接线和空白检查通过",
      "environment": "macOS; Python 3.9.6; main; 本地冻结候选",
      "coverage": "当前指南/工程规范/导航与生成标记，冻结历史报告未重写",
      "report": "docs/evidence/2026-10-18-architecture-upgrade/validation.md",
      "report_sha256": "33f20f5099ee77faaa5932a3c796da10bf658a879d4c62e1d32a76fec4d24709"
    },
    {
      "id": "mech-final",
      "kind": "mech",
      "candidate": "627a7b135bbade386f3b87191a56d12801a387d5663405856e13204ecac01743",
      "status": "passed",
      "command": "python3 scripts/ncc_eval.py mech",
      "exit_code": 0,
      "summary": "A01–A06 六个机械场景全部 PASS",
      "environment": "macOS; Python 3.9.6; main; 本地冻结候选",
      "coverage": "确定性机械层；不冒称完成模型锚定回归或五端会话测试",
      "report": "docs/evidence/2026-10-18-architecture-upgrade/validation.md",
      "report_sha256": "33f20f5099ee77faaa5932a3c796da10bf658a879d4c62e1d32a76fec4d24709"
    }
  ],
  "delivery": {
    "local": "accepted",
    "commit": "not_requested",
    "remote": "not_requested",
    "clone": "not_requested",
    "runtime": "author_pending",
    "review": "author_pending",
    "hosts": {
      "claude": "unverified",
      "codex": "unverified",
      "kimi": "unverified",
      "grok": "unverified",
      "zcode": "unverified"
    }
  },
  "verification_owner": "author"
}
```
