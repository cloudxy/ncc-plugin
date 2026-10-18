# 拆书分层升级实施

承接[统一升级方案](../designs/deconstruction/upgrade.md)，独立于已完成的[架构升级](2026-10-18-architecture-upgrade.md)，不覆盖其冻结证据。plugin_root/repo_root 均为当前仓库，main，v3.2.0。原工作树存在架构改造和文档整理差异；不 reset、stash、暂存或触碰私有书库。

## 实施计划与边界

按 P1 → P2 → P3 → P4 → P5 的依赖顺序，补机器契约及生成字段表，完成索引、入库恢复、分层场次和统计转化，再做 P6 代码整合、公开合成用例与作者测试交接。仅把隔离候选相对基线的本轮增量带回工作树，合入前逐文件核对现场未变。旧入口与 legacy 读取保留，legacy 不证明新层验收。

作者明确测试单独进行；本轮只做语法、生成、引用及候选元数据核对，不运行功能、模型或宿主测试。P6 回归验收、实质规则确认及独立评审保持待验。提交、推送与其他机器同步未授权。具体范围、反例和回滚见统一方案。

## 当前状态

代码与接线已整合到本地工作树，P1–P5 的运行模块及 P6 测试代码已完成，当前停在 D4 作者验证交接。P6 的实际回归与规则验收没有执行；此状态不等于功能已验收。详细实现落点、静态核对、测试入口及回滚见[交接报告](../evidence/2026-10-18-deconstruction-upgrade/implementation.md)。

本轮47个产品文件：9个职责明确的 deconstruction 模块、9份机器契约、CLI/旧接口接线、生成器、五份技能参考与角色读取清单、分层使用说明和合成用例。新编写21个验收测试方法，旧兼容快照未重写；仅对方案明确的跳号警告、范围报告位置和新增参数更新对应断言。

实际只执行17个 Python 文件语法、13个 JSON 解析、16份 Markdown 相对链接、文本空白及生成核对。未运行功能、全量、模型、独立评审或宿主测试；已有架构通过证据不适用于当前功能候选。新旧库兼容、中断恢复和四目标实际读取/停止边界均交作者验证。

后续测试入口与实际操作步骤以交接报告为准；通过后补充本指纹的真实证据和规则确认。原始书库未读取、未迁移，未暂存、提交、推送或同步消费克隆。回滚仅撤销47个路径相对本轮基线的增量，保留之前的架构和文档改动。

## 提交与推送授权

作者随后明确要求“提交并推送”。本轮按该授权发布拆书升级、所依赖的架构改造及配套文档迁移；先拉取确认远端最新，再按精确公开路径暂存和提交，保留钩子与私有内容守卫。以上实现报告的“未提交/未推送”为实现交接时状态，后续发布以本节和 Git 回执为准。实际升级提交为 `d8facc221bc7da5b4fb3952c4d50f6a750a68259`，已推送并通过 git ls-remote 核对 origin/main 相同提交。本回执随后作为独立元数据提交保存。测试、规则行为、独立评审及五端新会话继续由作者单独进行，不把提交推送写成验收通过。

```ncc-dev-json
{
  "schema": 1,
  "id": "2026-10-18-deconstruction-upgrade",
  "goal": "完成拆书 P1–P6 的代码模块、技能接线及作者测试交接",
  "route": "architectural",
  "risk_tags": [
    "rule_candidate",
    "core_data_contract"
  ],
  "repo_root": "/Users/xuyun/Documents/ncc-workflow",
  "plugin_root": "/Users/xuyun/Documents/ncc-workflow",
  "branch": "main",
  "base_commit": "0e3faa03f05f05524442c870c0fafda134e0d8b4",
  "stage": "D7",
  "next": "代码已提交并推送 origin/main；等待作者单独测试、独立评审、规则确认与五端新会话结果，发现问题另按对应阶段修复。",
  "blocked": "",
  "decisions": [
    {
      "source": "作者本轮要求：完成拆书 P1–P6 的代码功能模块",
      "scope": "实施分层拆书、索引、派单、验收入库、恢复、场次、统计与转化，接入项目级源；本次授权替代此前的延期决定。"
    },
    {
      "source": "作者此前指令：测试我会单独进行",
      "scope": "交付测试代码和入口，功能与规则行为、独立评审和五端加载保持待验；不运行功能测试、不沿用旧架构180项通过，不提交或推送。"
    },
    {
      "source": "作者本轮明确指令：提交并推送",
      "scope": "发布当前拆书代码及所依赖的架构升级、配套文档迁移；继承测试由作者单独进行的安排。此授权不把 pending 测试、独立评审、规则确认或五端加载变为通过。"
    }
  ],
  "spec": "docs/designs/deconstruction/upgrade.md",
  "plan": "docs/designs/deconstruction/upgrade.md",
  "scope": [
    "agents/deconstructor.md",
    "commands/ncc-deconstruct.md",
    "docs/README.md",
    "docs/designs/deconstruction/contracts.md",
    "docs/designs/deconstruction/upgrade.md",
    "docs/guides/usage.md",
    "scripts/dev/build_docs.py",
    "scripts/ncclib/cli.py",
    "scripts/ncclib/cli_parsers/deconstruction.py",
    "scripts/ncclib/decon.py",
    "scripts/ncclib/deconstruction/__init__.py",
    "scripts/ncclib/deconstruction/commands.py",
    "scripts/ncclib/deconstruction/common.py",
    "scripts/ncclib/deconstruction/contracts.py",
    "scripts/ncclib/deconstruction/index.py",
    "scripts/ncclib/deconstruction/ingest.py",
    "scripts/ncclib/deconstruction/planning.py",
    "scripts/ncclib/deconstruction/reporting.py",
    "scripts/ncclib/deconstruction/storage.py",
    "scripts/tests/fixtures/deconstruction/README.md",
    "scripts/tests/fixtures/deconstruction/multi-volume.txt",
    "scripts/tests/test_architecture.py",
    "scripts/tests/test_deconstruction.py",
    "scripts/tests/test_ncc_state.py",
    "scripts/tests/test_v3_regressions.py",
    "skills/ncc-deconstruct/SKILL.md",
    "skills/ncc-deconstruct/references/ingest.md",
    "skills/ncc-deconstruct/references/layers.md",
    "skills/ncc-deconstruct/references/packet.md",
    "skills/ncc-deconstruct/references/screenplay.md",
    "skills/ncc-deconstruct/references/transfer.md",
    "skills/ncc/references/book-layout.md",
    "skills/ncc/references/stage-map.md",
    "workflow/architecture.md",
    "workflow/contracts/deconstruction/chapter.json",
    "workflow/contracts/deconstruction/index.json",
    "workflow/contracts/deconstruction/packet.json",
    "workflow/contracts/deconstruction/plan.json",
    "workflow/contracts/deconstruction/progress.json",
    "workflow/contracts/deconstruction/receipt.json",
    "workflow/contracts/deconstruction/scene.json",
    "workflow/contracts/deconstruction/screenplay.json",
    "workflow/contracts/deconstruction/transfer.json",
    "workflow/registry.json",
    "workflow/registry/learning.json",
    "workflow/registry/roles.json",
    "workflow/registry/storage.json"
  ],
  "foreign_changes": {
    "ACKNOWLEDGMENTS.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "AGENTS.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "README.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/designs/engineering/architecture-audit.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/designs/engineering/architecture-growth.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/designs/engineering/source-audit.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/designs/engineering/workflow.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/designs/memory/memory-evolution-design.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/designs/preparation/preparation-design.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/dev-workflow.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/dev/2026-10-12-ncc-dev-plan.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/dev/evidence/2026-10-12-ncc-dev/anchors.log": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/dev/evidence/2026-10-12-ncc-dev/author.log": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/dev/evidence/2026-10-12-ncc-dev/behavior.log": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/dev/evidence/2026-10-12-ncc-dev/deterministic-before-independent-fixes.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/dev/evidence/2026-10-12-ncc-dev/deterministic-isolated.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/dev/evidence/2026-10-12-ncc-dev/deterministic.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/dev/evidence/2026-10-12-ncc-dev/review.log": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/dev/tasks/2026-10-12-ncc-dev.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/engineering/documentation.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/engineering/source-vetting.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/engineering/workflow.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/evidence/2026-10-12-ncc-dev/anchors.log": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/evidence/2026-10-12-ncc-dev/author.log": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/evidence/2026-10-12-ncc-dev/behavior.log": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/evidence/2026-10-12-ncc-dev/deterministic-before-independent-fixes.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/evidence/2026-10-12-ncc-dev/deterministic-isolated.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/evidence/2026-10-12-ncc-dev/deterministic.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/evidence/2026-10-12-ncc-dev/review.log": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/evidence/2026-10-12-ncc-dev/task.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/evidence/2026-10-13-readme-refresh/validation.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/evidence/2026-10-16-deconstruction-docs/validation.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/evidence/2026-10-16-docs-refresh/validation.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/evidence/2026-10-17-zcode-registration/validation.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/evidence/2026-10-18-architecture-plan/recheck.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/evidence/2026-10-18-architecture-plan/validation.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/evidence/2026-10-18-architecture-upgrade/baseline.log": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/evidence/2026-10-18-architecture-upgrade/unit.log": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/evidence/2026-10-18-architecture-upgrade/validation.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/superpowers/specs/2026-10-12-dev-workflow-audit.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/superpowers/specs/2026-10-12-dev-workflow-design.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/tasks/2026-10-12-readme-refresh.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/tasks/2026-10-16-deconstruction-docs.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/tasks/2026-10-16-docs-refresh.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/tasks/2026-10-17-zcode-registration.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/tasks/2026-10-18-architecture-plan.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/tasks/2026-10-18-architecture-upgrade.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "docs/usage.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/build_docs.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/check_dev_workflow.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/check_plugin.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/dev/__init__.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/dev/build_registry.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/dev/check_dev_workflow.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/dev/check_plugin.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/ncc_prepare.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/ncclib/cli_parsers/__init__.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/ncclib/cli_parsers/book.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/ncclib/cli_parsers/delivery.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/ncclib/cli_parsers/learning.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/ncclib/cli_parsers/ledgers.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/ncclib/cli_parsers/loops.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/ncclib/cli_parsers/scenes.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/ncclib/core.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/ncclib/registry.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/test_dev_workflow.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/test_ncc_library.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/test_ncc_prepare.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/test_ncc_state.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/test_v3_regressions.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/tests/__init__.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/tests/_behavior_probe.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/tests/_cli_contract.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/tests/fixtures/cli-contract.json": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/tests/fixtures/runtime-contract.json": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/tests/test_dev_workflow.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/tests/test_ncc_library.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/tests/test_ncc_prepare.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/tests/test_plugin_manifests.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "scripts/tests/test_registry.py": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "skills/ncc-dev/SKILL.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "skills/ncc-new/references/worldbuilding.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "skills/ncc/SKILL.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "skills/ncc/references/book-state.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "skills/ncc/references/loops.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "skills/ncc/references/memory.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "workflow/memory-evolution-design.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "workflow/preparation-design.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "workflow/principles.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "workflow/registry/delivery.json": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "workflow/registry/flow.json": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "workflow/registry/preparation.json": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "workflow/registry/rules.json": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。",
    "workflow/source-vetting.md": "本轮前已有的架构升级或文档整理差异，保留；本轮未修改。"
  },
  "evidence_paths": [
    "docs/evidence/2026-10-18-deconstruction-upgrade/implementation.md"
  ],
  "candidate": {
    "base_commit": "0e3faa03f05f05524442c870c0fafda134e0d8b4",
    "files": [
      {
        "path": "agents/deconstructor.md",
        "type": "file",
        "sha256": "fd54447e1c5111acec6060fc955201748fb0424e974f9fa796e23649011805f3",
        "executable": false
      },
      {
        "path": "commands/ncc-deconstruct.md",
        "type": "file",
        "sha256": "9f239fb6ed38d88de7b5b95ca96fa3b94b95be682ae5a454a9193cad1df5d1bc",
        "executable": false
      },
      {
        "path": "docs/README.md",
        "type": "file",
        "sha256": "61ae6496ed93c37dddd1be640cd6fededd8538d736f85b07264f9266c808a8c2",
        "executable": false
      },
      {
        "path": "docs/designs/deconstruction/contracts.md",
        "type": "file",
        "sha256": "dbb6b13329ffa51b61234879846c0dc884d6aa7fa36300f8071b772d9e279e78",
        "executable": false
      },
      {
        "path": "docs/designs/deconstruction/upgrade.md",
        "type": "file",
        "sha256": "6c94edf13105a64b4df110e9172c01ea548e50eeab73a156cd120f1b45389278",
        "executable": false
      },
      {
        "path": "docs/guides/usage.md",
        "type": "file",
        "sha256": "bf5d185d19419c58cd76a5f3ccffb20c7b3ba828627791f4f4c50dbcae4a4c84",
        "executable": false
      },
      {
        "path": "scripts/dev/build_docs.py",
        "type": "file",
        "sha256": "f36ce1857af95037ae4db8eae71f6d3301557e3d7f56c1f6a1c64cc0db35f88a",
        "executable": false
      },
      {
        "path": "scripts/ncclib/cli.py",
        "type": "file",
        "sha256": "c7c9ebb3bd5a4b184e11c88ed044d6837d5d1cac1a5371dc5cbb9e0a74306fca",
        "executable": false
      },
      {
        "path": "scripts/ncclib/cli_parsers/deconstruction.py",
        "type": "file",
        "sha256": "e887f04c4d7347d21870272313dfadb85d581b37ec1fca147c5e84e32dc91675",
        "executable": false
      },
      {
        "path": "scripts/ncclib/decon.py",
        "type": "file",
        "sha256": "a70a59aff23fce3292531853b38cd802b8a676c1bf28550235be605ec337d5eb",
        "executable": false
      },
      {
        "path": "scripts/ncclib/deconstruction/__init__.py",
        "type": "file",
        "sha256": "5f3ac0993f2c51dffac92b6d7ca278b363feffd7211f764e3924dcd0bfe20dbc",
        "executable": false
      },
      {
        "path": "scripts/ncclib/deconstruction/commands.py",
        "type": "file",
        "sha256": "00765897ccb59bc2f94d492680f458f2618536c57c71d49e070d3f860b34eabb",
        "executable": false
      },
      {
        "path": "scripts/ncclib/deconstruction/common.py",
        "type": "file",
        "sha256": "ca1211e0644a7640e1e6bbcb551a7129430d1f17a4974019f25dba6cd3449106",
        "executable": false
      },
      {
        "path": "scripts/ncclib/deconstruction/contracts.py",
        "type": "file",
        "sha256": "0ae9866f75dbb461d99dc2e56def613453931ce6122007188dda26e942f7681c",
        "executable": false
      },
      {
        "path": "scripts/ncclib/deconstruction/index.py",
        "type": "file",
        "sha256": "7c3f37d3d984b95d8536992a0cbbe04456a03121ac665d25013ef08bbee92c32",
        "executable": false
      },
      {
        "path": "scripts/ncclib/deconstruction/ingest.py",
        "type": "file",
        "sha256": "635c5ab5c6b11728bd57213575202f0495d5272034580d340742b9472ede2d2a",
        "executable": false
      },
      {
        "path": "scripts/ncclib/deconstruction/planning.py",
        "type": "file",
        "sha256": "6da89b0e03c371d047add451efbfd58c0eb235c25efff70b825889ad8bacb998",
        "executable": false
      },
      {
        "path": "scripts/ncclib/deconstruction/reporting.py",
        "type": "file",
        "sha256": "2e6f8fdd8c6662d600882aa1af3266ca74b5c766e7c51dac95c3a74b00fdbc91",
        "executable": false
      },
      {
        "path": "scripts/ncclib/deconstruction/storage.py",
        "type": "file",
        "sha256": "7bd17fa247bea8778ad26526730e65ce5723e55bb79889e1fa9b369f8e162ace",
        "executable": false
      },
      {
        "path": "scripts/tests/fixtures/deconstruction/README.md",
        "type": "file",
        "sha256": "e4f67a53250ab0c81fbda5ac49c6fa7b21eccc3d1faecbd7e75ad9b8916b4234",
        "executable": false
      },
      {
        "path": "scripts/tests/fixtures/deconstruction/multi-volume.txt",
        "type": "file",
        "sha256": "4c5216237635880a3449a76b7b3ca9ae72a045accc5fb7009aa51cb7143dc052",
        "executable": false
      },
      {
        "path": "scripts/tests/test_architecture.py",
        "type": "file",
        "sha256": "a5bc088da2b5da62bf9aac5046f821e8d3112d0d6f92bc6e78fe2a44f42b9358",
        "executable": false
      },
      {
        "path": "scripts/tests/test_deconstruction.py",
        "type": "file",
        "sha256": "2bc27beea37e8b474bd187e7b614521fccb0e4fb4d68f5b099df914894b7209f",
        "executable": false
      },
      {
        "path": "scripts/tests/test_ncc_state.py",
        "type": "file",
        "sha256": "19878423744cf662c71e0d2e6b607c035eef2b9929a013ad648e23fbeeb26a33",
        "executable": false
      },
      {
        "path": "scripts/tests/test_v3_regressions.py",
        "type": "file",
        "sha256": "5ba0a0a9015b25c47759befef503ca1c2572e67d71e08c0ea7a6bfdaafb2425c",
        "executable": false
      },
      {
        "path": "skills/ncc-deconstruct/SKILL.md",
        "type": "file",
        "sha256": "ca952417b6ffefeaf7b1673932c58114612957127796a1368337c640b0e501d2",
        "executable": false
      },
      {
        "path": "skills/ncc-deconstruct/references/ingest.md",
        "type": "file",
        "sha256": "9687b9f249e07db0795b8b4ebf1b767883eed23443d466cbcf55a751e7d91065",
        "executable": false
      },
      {
        "path": "skills/ncc-deconstruct/references/layers.md",
        "type": "file",
        "sha256": "47bb68b1dcb0e08e5db8d9f227e527626a3f23fbbf2c80af0b5b6177d840c1b3",
        "executable": false
      },
      {
        "path": "skills/ncc-deconstruct/references/packet.md",
        "type": "file",
        "sha256": "eee90f88bdecf5c04bd1bd60a22c68bdf37573b6597e2fa97e42f0bbaf956b54",
        "executable": false
      },
      {
        "path": "skills/ncc-deconstruct/references/screenplay.md",
        "type": "file",
        "sha256": "aa437f35caf3c4548c6b91367b7a8f6f1772eea15dc9ed1e59c59a9fd3bbbcc8",
        "executable": false
      },
      {
        "path": "skills/ncc-deconstruct/references/transfer.md",
        "type": "file",
        "sha256": "274421166a5241bcfc4dce957615db5a82aa20f040e6b4c860c038e816e3eb5f",
        "executable": false
      },
      {
        "path": "skills/ncc/references/book-layout.md",
        "type": "file",
        "sha256": "400f65946bfa217f9897f3c2b6e7ee528d37f49930cf8a0dd3d431b6ab4b06ea",
        "executable": false
      },
      {
        "path": "skills/ncc/references/stage-map.md",
        "type": "file",
        "sha256": "8029f6df104d94d791c8abcc14d7c024dafec214cfc482daf1b21d12a21a4847",
        "executable": false
      },
      {
        "path": "workflow/architecture.md",
        "type": "file",
        "sha256": "eba213349f83ca795e348efea81965ab24bc2c627c915434aae006f85259ec42",
        "executable": false
      },
      {
        "path": "workflow/contracts/deconstruction/chapter.json",
        "type": "file",
        "sha256": "a2fbc2f70fdcb618738d8950af9a1a375393e8740ac52d94d4962c7695c9a56f",
        "executable": false
      },
      {
        "path": "workflow/contracts/deconstruction/index.json",
        "type": "file",
        "sha256": "eac5cbd4c17e2b049ba33edb17ed05587cfad9b485a16cb0e1ec26ddc5426e1f",
        "executable": false
      },
      {
        "path": "workflow/contracts/deconstruction/packet.json",
        "type": "file",
        "sha256": "9e79e8eb83d009db455d59f8550e8bb108323972fc4bf030a0fcfa2d78091766",
        "executable": false
      },
      {
        "path": "workflow/contracts/deconstruction/plan.json",
        "type": "file",
        "sha256": "8f2b7db9b37d16d7a0a1982cf619335721add7a743c27367c309fd7f5d81c721",
        "executable": false
      },
      {
        "path": "workflow/contracts/deconstruction/progress.json",
        "type": "file",
        "sha256": "430c12bc0c60b35cec9bb28a71ef2cd7ebd2464ef7be3eb12b446352414a87cf",
        "executable": false
      },
      {
        "path": "workflow/contracts/deconstruction/receipt.json",
        "type": "file",
        "sha256": "53693ad77f8083373bdf9d13a21624b232c842231525e06f2902fe1fe8c51363",
        "executable": false
      },
      {
        "path": "workflow/contracts/deconstruction/scene.json",
        "type": "file",
        "sha256": "0c9fea7a71b477e301ffe11216b3208504133c7efb5738941c7a4e5d25dcef99",
        "executable": false
      },
      {
        "path": "workflow/contracts/deconstruction/screenplay.json",
        "type": "file",
        "sha256": "8f9506176e0e1481b69c130d024cb673e0dc4e751bd1c85f5d9707caa68854a4",
        "executable": false
      },
      {
        "path": "workflow/contracts/deconstruction/transfer.json",
        "type": "file",
        "sha256": "e0d4bdc62d68745971d8ed41881b7d4a06bd7e06c51cc9cd49f744a9c756dc70",
        "executable": false
      },
      {
        "path": "workflow/registry.json",
        "type": "file",
        "sha256": "7d2da2d732291f4d3846897071bbaee5b1596cb78792a1eeca1b9be6f73320d4",
        "executable": false
      },
      {
        "path": "workflow/registry/learning.json",
        "type": "file",
        "sha256": "9d6cc8fac8b300d5fa075a54a51a32a11354c583c55be8e5d46d2b018a058c8f",
        "executable": false
      },
      {
        "path": "workflow/registry/roles.json",
        "type": "file",
        "sha256": "001116ba3d061e414449f52597376d08dde3fb74ce7be2103cad5fd8576b6bfe",
        "executable": false
      },
      {
        "path": "workflow/registry/storage.json",
        "type": "file",
        "sha256": "0131c34f12ee1ace79d99557670df5e0c0a4ba8b5285d866d47af8794f4a1835",
        "executable": false
      }
    ],
    "fingerprint": "c37e65b2464441244fa9e818187e0cd5f49d40a5173410bd27be15d2258333bc"
  },
  "required": [
    "unit",
    "compatibility",
    "registry",
    "plugin",
    "docs",
    "behavior",
    "independent_review",
    "runtime",
    "author_confirmation"
  ],
  "evidence": [
    {
      "candidate": "c37e65b2464441244fa9e818187e0cd5f49d40a5173410bd27be15d2258333bc",
      "environment": "macOS; Python 3.9.6; main; 本地工作树；测试由作者另行执行",
      "report": "docs/evidence/2026-10-18-deconstruction-upgrade/implementation.md",
      "report_sha256": "436516c424f78dfe72f2f954a1b34a4807635f511a17b915acf9c725337b2051",
      "id": "static-source",
      "kind": "static",
      "status": "passed",
      "exit_code": 0,
      "command": "ast.parse/json.loads；相对链接/文本与现场基线核对；build_registry.py/build_docs.py 生成",
      "summary": "仅静态：17个Python、13个JSON、16份Markdown及47个路径核对；21个测试方法已编写，未执行",
      "coverage": "源文件语法、可解析结构、相对链接、文本和生成新鲜度；不证明功能正确、规则或宿主运行"
    },
    {
      "candidate": "c37e65b2464441244fa9e818187e0cd5f49d40a5173410bd27be15d2258333bc",
      "environment": "macOS; Python 3.9.6; main; 本地工作树；测试由作者另行执行",
      "report": "docs/evidence/2026-10-18-deconstruction-upgrade/implementation.md",
      "report_sha256": "436516c424f78dfe72f2f954a1b34a4807635f511a17b915acf9c725337b2051",
      "id": "unit-author-pending",
      "kind": "unit",
      "status": "pending",
      "exit_code": null,
      "command": "python3 -m unittest discover -s scripts/tests -t scripts -p 'test_deconstruction.py'；随后全量 test_*.py",
      "summary": "按作者测试安排，尚未执行，不记通过",
      "coverage": "待作者验证；验收重点和限制见交接报告"
    },
    {
      "candidate": "c37e65b2464441244fa9e818187e0cd5f49d40a5173410bd27be15d2258333bc",
      "environment": "macOS; Python 3.9.6; main; 本地工作树；测试由作者另行执行",
      "report": "docs/evidence/2026-10-18-deconstruction-upgrade/implementation.md",
      "report_sha256": "436516c424f78dfe72f2f954a1b34a4807635f511a17b915acf9c725337b2051",
      "id": "compatibility-author-pending",
      "kind": "compatibility",
      "status": "pending",
      "exit_code": null,
      "command": "旧库/旧 CLI/原冻结快照及公开副本的兼容用例，待作者运行",
      "summary": "按作者测试安排，尚未执行，不记通过",
      "coverage": "待作者验证；验收重点和限制见交接报告"
    },
    {
      "candidate": "c37e65b2464441244fa9e818187e0cd5f49d40a5173410bd27be15d2258333bc",
      "environment": "macOS; Python 3.9.6; main; 本地工作树；测试由作者另行执行",
      "report": "docs/evidence/2026-10-18-deconstruction-upgrade/implementation.md",
      "report_sha256": "436516c424f78dfe72f2f954a1b34a4807635f511a17b915acf9c725337b2051",
      "id": "registry-author-pending",
      "kind": "registry",
      "status": "pending",
      "exit_code": null,
      "command": "python3 scripts/dev/build_registry.py --check；相关契约/registry反例",
      "summary": "按作者测试安排，尚未执行，不记通过",
      "coverage": "待作者验证；验收重点和限制见交接报告"
    },
    {
      "candidate": "c37e65b2464441244fa9e818187e0cd5f49d40a5173410bd27be15d2258333bc",
      "environment": "macOS; Python 3.9.6; main; 本地工作树；测试由作者另行执行",
      "report": "docs/evidence/2026-10-18-deconstruction-upgrade/implementation.md",
      "report_sha256": "436516c424f78dfe72f2f954a1b34a4807635f511a17b915acf9c725337b2051",
      "id": "plugin-author-pending",
      "kind": "plugin",
      "status": "pending",
      "exit_code": null,
      "command": "python3 scripts/dev/check_plugin.py -v",
      "summary": "按作者测试安排，尚未执行，不记通过",
      "coverage": "待作者验证；验收重点和限制见交接报告"
    },
    {
      "candidate": "c37e65b2464441244fa9e818187e0cd5f49d40a5173410bd27be15d2258333bc",
      "environment": "macOS; Python 3.9.6; main; 本地工作树；测试由作者另行执行",
      "report": "docs/evidence/2026-10-18-deconstruction-upgrade/implementation.md",
      "report_sha256": "436516c424f78dfe72f2f954a1b34a4807635f511a17b915acf9c725337b2051",
      "id": "docs-author-pending",
      "kind": "docs",
      "status": "pending",
      "exit_code": null,
      "command": "python3 scripts/dev/build_docs.py --check；字段表与引用检查",
      "summary": "按作者测试安排，尚未执行，不记通过",
      "coverage": "待作者验证；验收重点和限制见交接报告"
    },
    {
      "candidate": "c37e65b2464441244fa9e818187e0cd5f49d40a5173410bd27be15d2258333bc",
      "environment": "macOS; Python 3.9.6; main; 本地工作树；测试由作者另行执行",
      "report": "docs/evidence/2026-10-18-deconstruction-upgrade/implementation.md",
      "report_sha256": "436516c424f78dfe72f2f954a1b34a4807635f511a17b915acf9c725337b2051",
      "id": "behavior-author-pending",
      "kind": "behavior",
      "status": "pending",
      "exit_code": null,
      "command": "四个合成目标：结构、稀疏技法、明确全章、只读转化；实际执行者核对读取与停止边界",
      "summary": "按作者测试安排，尚未执行，不记通过",
      "coverage": "待作者验证；验收重点和限制见交接报告"
    },
    {
      "candidate": "c37e65b2464441244fa9e818187e0cd5f49d40a5173410bd27be15d2258333bc",
      "environment": "macOS; Python 3.9.6; main; 本地工作树；测试由作者另行执行",
      "report": "docs/evidence/2026-10-18-deconstruction-upgrade/implementation.md",
      "report_sha256": "436516c424f78dfe72f2f954a1b34a4807635f511a17b915acf9c725337b2051",
      "id": "independent_review-author-pending",
      "kind": "independent_review",
      "status": "pending",
      "exit_code": null,
      "command": "独立会话或作者人工评审本候选的意图、实现、反例、兼容和回滚",
      "summary": "按作者测试安排，尚未执行，不记通过",
      "coverage": "待作者验证；验收重点和限制见交接报告"
    },
    {
      "candidate": "c37e65b2464441244fa9e818187e0cd5f49d40a5173410bd27be15d2258333bc",
      "environment": "macOS; Python 3.9.6; main; 本地工作树；测试由作者另行执行",
      "report": "docs/evidence/2026-10-18-deconstruction-upgrade/implementation.md",
      "report_sha256": "436516c424f78dfe72f2f954a1b34a4807635f511a17b915acf9c725337b2051",
      "id": "runtime-author-pending",
      "kind": "runtime",
      "status": "pending",
      "exit_code": null,
      "command": "claude/codex/kimi/grok/zcode各新会话核对加载根、版本、发现、参数、代表调用与恢复",
      "summary": "按作者测试安排，尚未执行，不记通过",
      "coverage": "待作者验证；验收重点和限制见交接报告"
    },
    {
      "candidate": "c37e65b2464441244fa9e818187e0cd5f49d40a5173410bd27be15d2258333bc",
      "environment": "macOS; Python 3.9.6; main; 本地工作树；测试由作者另行执行",
      "report": "docs/evidence/2026-10-18-deconstruction-upgrade/implementation.md",
      "report_sha256": "436516c424f78dfe72f2f954a1b34a4807635f511a17b915acf9c725337b2051",
      "id": "author_confirmation-author-pending",
      "kind": "author_confirmation",
      "status": "pending",
      "exit_code": null,
      "command": "规则行为与回归完成后，由作者确认该具体候选",
      "summary": "按作者测试安排，尚未执行，不记通过",
      "coverage": "待作者验证；验收重点和限制见交接报告"
    }
  ],
  "delivery": {
    "local": "implementation_complete",
    "commit": "d8facc221bc7da5b4fb3952c4d50f6a750a68259",
    "remote": "origin/main verified d8facc221bc7da5b4fb3952c4d50f6a750a68259",
    "clone": "not_requested; local zcode uses current tree",
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
  "verification_owner": "author",
  "publication": {
    "authorization": "作者本轮：提交并推送",
    "branch": "main",
    "remote": "origin",
    "included_paths": [
      "ACKNOWLEDGMENTS.md",
      "AGENTS.md",
      "README.md",
      "agents/deconstructor.md",
      "commands/ncc-deconstruct.md",
      "docs/README.md",
      "docs/designs/deconstruction/contracts.md",
      "docs/designs/deconstruction/upgrade.md",
      "docs/designs/engineering/architecture-audit.md",
      "docs/designs/engineering/architecture-growth.md",
      "docs/designs/engineering/source-audit.md",
      "docs/designs/engineering/workflow.md",
      "docs/designs/memory/memory-evolution-design.md",
      "docs/designs/preparation/preparation-design.md",
      "docs/dev-workflow.md",
      "docs/dev/2026-10-12-ncc-dev-plan.md",
      "docs/dev/evidence/2026-10-12-ncc-dev/anchors.log",
      "docs/dev/evidence/2026-10-12-ncc-dev/author.log",
      "docs/dev/evidence/2026-10-12-ncc-dev/behavior.log",
      "docs/dev/evidence/2026-10-12-ncc-dev/deterministic-before-independent-fixes.md",
      "docs/dev/evidence/2026-10-12-ncc-dev/deterministic-isolated.md",
      "docs/dev/evidence/2026-10-12-ncc-dev/deterministic.md",
      "docs/dev/evidence/2026-10-12-ncc-dev/review.log",
      "docs/dev/tasks/2026-10-12-ncc-dev.md",
      "docs/engineering/documentation.md",
      "docs/engineering/source-vetting.md",
      "docs/engineering/workflow.md",
      "docs/evidence/2026-10-12-ncc-dev/anchors.log",
      "docs/evidence/2026-10-12-ncc-dev/author.log",
      "docs/evidence/2026-10-12-ncc-dev/behavior.log",
      "docs/evidence/2026-10-12-ncc-dev/deterministic-before-independent-fixes.md",
      "docs/evidence/2026-10-12-ncc-dev/deterministic-isolated.md",
      "docs/evidence/2026-10-12-ncc-dev/deterministic.md",
      "docs/evidence/2026-10-12-ncc-dev/review.log",
      "docs/evidence/2026-10-12-ncc-dev/task.md",
      "docs/evidence/2026-10-13-readme-refresh/validation.md",
      "docs/evidence/2026-10-16-deconstruction-docs/validation.md",
      "docs/evidence/2026-10-16-docs-refresh/validation.md",
      "docs/evidence/2026-10-17-zcode-registration/validation.md",
      "docs/evidence/2026-10-18-architecture-plan/recheck.md",
      "docs/evidence/2026-10-18-architecture-plan/validation.md",
      "docs/evidence/2026-10-18-architecture-upgrade/baseline.log",
      "docs/evidence/2026-10-18-architecture-upgrade/unit.log",
      "docs/evidence/2026-10-18-architecture-upgrade/validation.md",
      "docs/evidence/2026-10-18-deconstruction-upgrade/implementation.md",
      "docs/guides/usage.md",
      "docs/superpowers/specs/2026-10-12-dev-workflow-audit.md",
      "docs/superpowers/specs/2026-10-12-dev-workflow-design.md",
      "docs/tasks/2026-10-12-readme-refresh.md",
      "docs/tasks/2026-10-16-deconstruction-docs.md",
      "docs/tasks/2026-10-16-docs-refresh.md",
      "docs/tasks/2026-10-17-zcode-registration.md",
      "docs/tasks/2026-10-18-architecture-plan.md",
      "docs/tasks/2026-10-18-architecture-upgrade.md",
      "docs/tasks/2026-10-18-deconstruction-upgrade.md",
      "docs/usage.md",
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
      "scripts/ncclib/decon.py",
      "scripts/ncclib/deconstruction/__init__.py",
      "scripts/ncclib/deconstruction/commands.py",
      "scripts/ncclib/deconstruction/common.py",
      "scripts/ncclib/deconstruction/contracts.py",
      "scripts/ncclib/deconstruction/index.py",
      "scripts/ncclib/deconstruction/ingest.py",
      "scripts/ncclib/deconstruction/planning.py",
      "scripts/ncclib/deconstruction/reporting.py",
      "scripts/ncclib/deconstruction/storage.py",
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
      "scripts/tests/fixtures/deconstruction/README.md",
      "scripts/tests/fixtures/deconstruction/multi-volume.txt",
      "scripts/tests/fixtures/runtime-contract.json",
      "scripts/tests/test_architecture.py",
      "scripts/tests/test_deconstruction.py",
      "scripts/tests/test_dev_workflow.py",
      "scripts/tests/test_ncc_library.py",
      "scripts/tests/test_ncc_prepare.py",
      "scripts/tests/test_ncc_state.py",
      "scripts/tests/test_plugin_manifests.py",
      "scripts/tests/test_registry.py",
      "scripts/tests/test_v3_regressions.py",
      "skills/ncc-deconstruct/SKILL.md",
      "skills/ncc-deconstruct/references/ingest.md",
      "skills/ncc-deconstruct/references/layers.md",
      "skills/ncc-deconstruct/references/packet.md",
      "skills/ncc-deconstruct/references/screenplay.md",
      "skills/ncc-deconstruct/references/transfer.md",
      "skills/ncc-dev/SKILL.md",
      "skills/ncc-new/references/worldbuilding.md",
      "skills/ncc/SKILL.md",
      "skills/ncc/references/book-layout.md",
      "skills/ncc/references/book-state.md",
      "skills/ncc/references/loops.md",
      "skills/ncc/references/memory.md",
      "skills/ncc/references/stage-map.md",
      "workflow/architecture.md",
      "workflow/contracts/deconstruction/chapter.json",
      "workflow/contracts/deconstruction/index.json",
      "workflow/contracts/deconstruction/packet.json",
      "workflow/contracts/deconstruction/plan.json",
      "workflow/contracts/deconstruction/progress.json",
      "workflow/contracts/deconstruction/receipt.json",
      "workflow/contracts/deconstruction/scene.json",
      "workflow/contracts/deconstruction/screenplay.json",
      "workflow/contracts/deconstruction/transfer.json",
      "workflow/memory-evolution-design.md",
      "workflow/preparation-design.md",
      "workflow/principles.md",
      "workflow/registry.json",
      "workflow/registry/delivery.json",
      "workflow/registry/flow.json",
      "workflow/registry/learning.json",
      "workflow/registry/preparation.json",
      "workflow/registry/roles.json",
      "workflow/registry/rules.json",
      "workflow/registry/storage.json",
      "workflow/source-vetting.md"
    ],
    "verification": "deferred_by_author; pending evidence retained",
    "source_candidate": "c37e65b2464441244fa9e818187e0cd5f49d40a5173410bd27be15d2258333bc",
    "code_commit": "d8facc221bc7da5b4fb3952c4d50f6a750a68259",
    "remote_verified": "d8facc221bc7da5b4fb3952c4d50f6a750a68259",
    "hooks": "core.hooksPath=.githooks; pre-commit and pre-push completed",
    "receipt": "本回执另作元数据提交保存；未改变功能代码及 pending 验证状态。",
    "staged_scope": "143 explicit public paths; 123 changes after rename detection; private markers and credential scan clear",
    "whitespace": "产品检查通过；两份冻结原始测试日志的末尾空行原样保留"
  }
}
```
