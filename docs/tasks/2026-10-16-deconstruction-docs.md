# 拆书方案整合与文档目录重组

## 范围与授权

活动仓库与技能根均为 `/Users/xuyun/Documents/ncc-workflow`，分支 main，版本 v3.2.0，基线 `0e3faa0`。作者授权综合 15、16 日全部相关拆书设计与计划，清理旧方案，并实际建立按用途和模块归属的文档架构。当前任务只实施文档与必要路径适配；拆书功能升级仍是方案。

文档架构、迁移步骤与验收见[组织规范](../engineering/documentation.md)；拆书的唯一设计与实施计划见[统一方案](../designs/deconstruction/upgrade.md)。旧三组九份文档以及已完成的开发入口实施计划删除。原始拆书方案尚未跟踪，本地回退副本位于 `/private/tmp/ncc-docs-before-um6fvlll`；仓内不保留重复归档。

## 基线与在途工作

开始时 README 已有完整改写，三组拆书文档和 README 任务/证据尚未跟踪。本次继承旧方案中的有效设计、保留 README 的在途文案，只更新必要导航。README 的必要改链和其任务元数据迁移纳入本次精确范围；该任务旧验证没有重新标为通过。已发布开发入口的任务记录退出活动目录，随其原始报告保留作为当前发布依据。

技能正文只更换流程文档与任务的查找路径，审稿、写作、拆书角色与注册表语义未修改。检查器的任务/证据路径和插件链接检查同步；历史证据正文不用于现行路径扫描，实际报告哈希仍核查。

## 当前验证

检查输入、命令、结果和缺项见[验证报告](../evidence/2026-10-16-deconstruction-docs/validation.md)。作者在任务中明确测试按实际影响范围选择：本次仅做文档导航、生成一致性、路径检查器及其边界用例，不需要全量或无关模型回归。该原则已同步到 AGENTS.md、现行开发规范、设计依据和升级计划。

旧规范下启动的全量与模型评测已停止，不作为本次交付必要证据。全量初轮在文档尚未写齐时发现缺任务链接，补齐后插件链接检查通过；第二轮按作者要求中止。模型评测只进行部分基线盲审，未完成基线/候选比较，未生成通过结论。临时材料留在 `/private/tmp/ncc-docs-eval-n687vnkq`，不进入产品目录。

当前会话完成自查，独立评审待办；不作为本次文档交付的前置条件。后续拆书功能尚未实现，规则候选验证与具体结果确认属于实施任务。

## 回滚与下一步

本地回退副本保存迁移前全部 docs 与作者当时 README；工程脚本/入口按本次差异范围恢复，不能覆盖 README 原改写。未提交、未推送、未更新安装克隆。完成当前文档候选验证后可阅读统一方案；作者要求实现时另开拆书实施任务，从 P1 冻结契约开始。

```ncc-dev-json
{
  "schema": 1,
  "id": "2026-10-16-deconstruction-docs",
  "goal": "Consolidate deconstruction proposal and reorganize documentation",
  "route": "architectural",
  "risk_tags": [
    "rules-paths",
    "documentation-migration"
  ],
  "repo_root": "/Users/xuyun/Documents/ncc-workflow",
  "plugin_root": "/Users/xuyun/Documents/ncc-workflow",
  "branch": "main",
  "base_commit": "0e3faa03f05f05524442c870c0fafda134e0d8b4",
  "stage": "D5",
  "next": "Documentation delivered; deconstruction implementation starts at P1 only when requested",
  "blocked": "",
  "decisions": [
    {
      "source": "Author request on 2026-10-16",
      "scope": "Unify proposals, remove superseded files, reorganize docs and adapt paths; no deconstruction implementation or publication"
    },
    {
      "source": "Existing README task and AGENTS.md",
      "scope": "Preserve ongoing prose and original evidence; old results do not certify migrated candidate"
    },
    {
      "source": "Author clarification on 2026-10-16",
      "scope": "Test affected or new functionality only; full suite for major changes; stop unrelated full and model regression for this documentation task"
    }
  ],
  "spec": "docs/engineering/documentation.md",
  "plan": "docs/engineering/documentation.md",
  "scope": [
    "ACKNOWLEDGMENTS.md",
    "AGENTS.md",
    "README.md",
    "docs/README.md",
    "docs/designs/deconstruction/upgrade.md",
    "docs/designs/engineering/source-audit.md",
    "docs/designs/engineering/workflow.md",
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
    "docs/guides/usage.md",
    "docs/superpowers/specs/2026-10-12-dev-workflow-audit.md",
    "docs/superpowers/specs/2026-10-12-dev-workflow-design.md",
    "docs/tasks/2026-10-12-readme-refresh.md",
    "docs/usage.md",
    "scripts/check_dev_workflow.py",
    "scripts/check_plugin.py",
    "scripts/test_dev_workflow.py",
    "skills/ncc-dev/SKILL.md",
    "workflow/architecture.md"
  ],
  "foreign_changes": {},
  "evidence_paths": [
    "docs/evidence/2026-10-16-deconstruction-docs/validation.md"
  ],
  "candidate": {
    "base_commit": "0e3faa03f05f05524442c870c0fafda134e0d8b4",
    "files": [
      {
        "path": "ACKNOWLEDGMENTS.md",
        "type": "file",
        "sha256": "e9e8853740292f023a4ae851424860774d6efac6841e7ee3ec6d7157ca498d0e",
        "executable": false
      },
      {
        "path": "AGENTS.md",
        "type": "file",
        "sha256": "8ac77e78f016feb4baa5cdb540969f26ad2295494e60128eba156565d4456f7c",
        "executable": false
      },
      {
        "path": "README.md",
        "type": "file",
        "sha256": "27ebc9929a3a18596e1dd91cdb74b0c3b4b353e098813ee656dea7726357fd31",
        "executable": false
      },
      {
        "path": "docs/README.md",
        "type": "file",
        "sha256": "7fe44c91c3a0bd2a1de13f9269810e1989e1b98e23ea671969471cf696464bb2",
        "executable": false
      },
      {
        "path": "docs/designs/deconstruction/upgrade.md",
        "type": "file",
        "sha256": "f6ce1de5b5cb0c8de7505a7e5d38e50299fca54fe755f487fc04f0ac67dea619",
        "executable": false
      },
      {
        "path": "docs/designs/engineering/source-audit.md",
        "type": "file",
        "sha256": "931b668d574e7c37876687491afde6d34864a387e9114df4f19097ff3cc52874",
        "executable": false
      },
      {
        "path": "docs/designs/engineering/workflow.md",
        "type": "file",
        "sha256": "a5f401c140ecbe288e3cad461f747c9e724b79c30b3efb81128b3b2a2f2a412c",
        "executable": false
      },
      {
        "path": "docs/dev-workflow.md",
        "type": "deleted"
      },
      {
        "path": "docs/dev/2026-10-12-ncc-dev-plan.md",
        "type": "deleted"
      },
      {
        "path": "docs/dev/evidence/2026-10-12-ncc-dev/anchors.log",
        "type": "deleted"
      },
      {
        "path": "docs/dev/evidence/2026-10-12-ncc-dev/author.log",
        "type": "deleted"
      },
      {
        "path": "docs/dev/evidence/2026-10-12-ncc-dev/behavior.log",
        "type": "deleted"
      },
      {
        "path": "docs/dev/evidence/2026-10-12-ncc-dev/deterministic-before-independent-fixes.md",
        "type": "deleted"
      },
      {
        "path": "docs/dev/evidence/2026-10-12-ncc-dev/deterministic-isolated.md",
        "type": "deleted"
      },
      {
        "path": "docs/dev/evidence/2026-10-12-ncc-dev/deterministic.md",
        "type": "deleted"
      },
      {
        "path": "docs/dev/evidence/2026-10-12-ncc-dev/review.log",
        "type": "deleted"
      },
      {
        "path": "docs/dev/tasks/2026-10-12-ncc-dev.md",
        "type": "deleted"
      },
      {
        "path": "docs/engineering/documentation.md",
        "type": "file",
        "sha256": "cb8e9d4c749b98d1320098b5310c64c786e97851dd8710377d6930a70e0011e4",
        "executable": false
      },
      {
        "path": "docs/engineering/workflow.md",
        "type": "file",
        "sha256": "1d4069f7b69114eb2155fdffe46b1dc4723c0c8ab0959f522c3a93f42f775d52",
        "executable": false
      },
      {
        "path": "docs/evidence/2026-10-12-ncc-dev/anchors.log",
        "type": "file",
        "sha256": "d04de48d7d3991deb26eea88ec07e0393ffdbab96be4ffb4aa83ef26b6609d87",
        "executable": false
      },
      {
        "path": "docs/evidence/2026-10-12-ncc-dev/author.log",
        "type": "file",
        "sha256": "ea93f0827aa673eb00d9badb24c25f922ed5ae00f9c795a0ff94950f2e087329",
        "executable": false
      },
      {
        "path": "docs/evidence/2026-10-12-ncc-dev/behavior.log",
        "type": "file",
        "sha256": "62f37872e59b6b4f148193b8a547640339a592b429af5cfceacaa4fcb1809e60",
        "executable": false
      },
      {
        "path": "docs/evidence/2026-10-12-ncc-dev/deterministic-before-independent-fixes.md",
        "type": "file",
        "sha256": "21ce6f82caf2d7ed1541cf69998b1d76065542b92535d368953e1456e16d6ebf",
        "executable": false
      },
      {
        "path": "docs/evidence/2026-10-12-ncc-dev/deterministic-isolated.md",
        "type": "file",
        "sha256": "e334dc900800c7b0ce33a989a50cbf525c99f380e375908d331a0d5da2284176",
        "executable": false
      },
      {
        "path": "docs/evidence/2026-10-12-ncc-dev/deterministic.md",
        "type": "file",
        "sha256": "922a4c46b8a8413cec6a957a2df1f36597e54c51aac7cc7a681d183a0254d25f",
        "executable": false
      },
      {
        "path": "docs/evidence/2026-10-12-ncc-dev/review.log",
        "type": "file",
        "sha256": "16a6b890645543c252e6965154852327a76bdd4c03aede31fe7c05c88a510039",
        "executable": false
      },
      {
        "path": "docs/evidence/2026-10-12-ncc-dev/task.md",
        "type": "file",
        "sha256": "28d190b92f01315fc19905a137d1b7196eb8423fc3be82b73ef421ba5b482ade",
        "executable": false
      },
      {
        "path": "docs/evidence/2026-10-13-readme-refresh/validation.md",
        "type": "file",
        "sha256": "271ea73b8f0b3fd0b9640dc9b62cb08a9350f21f1f9c4f399ba0826f333e9d5e",
        "executable": false
      },
      {
        "path": "docs/guides/usage.md",
        "type": "file",
        "sha256": "30f645374b55c64a9309f422e328a29b711c1bfb82c9d1b883cf58ce317dd7ca",
        "executable": false
      },
      {
        "path": "docs/superpowers/specs/2026-10-12-dev-workflow-audit.md",
        "type": "deleted"
      },
      {
        "path": "docs/superpowers/specs/2026-10-12-dev-workflow-design.md",
        "type": "deleted"
      },
      {
        "path": "docs/tasks/2026-10-12-readme-refresh.md",
        "type": "file",
        "sha256": "49445858ec2ead2afe076d5ca2efaada4e1af6dcf965cfcb838d8299f2d4e9b0",
        "executable": false
      },
      {
        "path": "docs/usage.md",
        "type": "deleted"
      },
      {
        "path": "scripts/check_dev_workflow.py",
        "type": "file",
        "sha256": "739e7afaf000eb880d4433bbb343b886ba1f0a54f41614621b50f851f3c165ff",
        "executable": false
      },
      {
        "path": "scripts/check_plugin.py",
        "type": "file",
        "sha256": "4a083324370b84362b5f7b2b3531307a8bcadf328e904e9513bd39d777f1d26a",
        "executable": false
      },
      {
        "path": "scripts/test_dev_workflow.py",
        "type": "file",
        "sha256": "273bee829b1da46bd6f09de2cfadca65ea7d38e7a932162052defb6e065f899a",
        "executable": false
      },
      {
        "path": "skills/ncc-dev/SKILL.md",
        "type": "file",
        "sha256": "b124ec861d683beb92dfefd8f6a5c5e931dd85e5440d12f72c749c5c6271b3fd",
        "executable": false
      },
      {
        "path": "workflow/architecture.md",
        "type": "file",
        "sha256": "bbd50518d01eb76f81afdf3aba5822a5483ef07378e944e0f57ea7e036df4559",
        "executable": false
      }
    ],
    "fingerprint": "0f5f0b5f1f6f2a1122d1ff5ffa19f612fc26ef31f39318b8d23125a3e34cc039"
  },
  "required": [
    "targeted",
    "plugin",
    "docs",
    "paths"
  ],
  "evidence": [
    {
      "id": "targeted",
      "kind": "targeted",
      "candidate": "0f5f0b5f1f6f2a1122d1ff5ffa19f612fc26ef31f39318b8d23125a3e34cc039",
      "status": "passed",
      "command": "python3 -m unittest discover -s scripts -p 'test_dev_workflow.py'",
      "exit_code": 0,
      "summary": "36 tests OK; 23.986s",
      "environment": "macOS; Python 3.9; current Codex session",
      "coverage": "Affected task, evidence, fingerprint and entry path cases",
      "report": "docs/evidence/2026-10-16-deconstruction-docs/validation.md",
      "report_sha256": "93c323e3a65bc7239620f59a4ce23fd5e9f98c2c5b570e207cbab5fc93b398d8"
    },
    {
      "id": "plugin",
      "kind": "plugin",
      "candidate": "0f5f0b5f1f6f2a1122d1ff5ffa19f612fc26ef31f39318b8d23125a3e34cc039",
      "status": "passed",
      "command": "python3 scripts/check_plugin.py -v",
      "exit_code": 0,
      "summary": "PLUGIN OK",
      "environment": "macOS; Python 3.9; current Codex session",
      "coverage": "Live links and static wiring",
      "report": "docs/evidence/2026-10-16-deconstruction-docs/validation.md",
      "report_sha256": "93c323e3a65bc7239620f59a4ce23fd5e9f98c2c5b570e207cbab5fc93b398d8"
    },
    {
      "id": "docs",
      "kind": "docs",
      "candidate": "0f5f0b5f1f6f2a1122d1ff5ffa19f612fc26ef31f39318b8d23125a3e34cc039",
      "status": "passed",
      "command": "python3 scripts/build_docs.py --check",
      "exit_code": 0,
      "summary": "DOCS OK",
      "environment": "macOS; Python 3.9; current Codex session",
      "coverage": "Generated documentation consistency",
      "report": "docs/evidence/2026-10-16-deconstruction-docs/validation.md",
      "report_sha256": "93c323e3a65bc7239620f59a4ce23fd5e9f98c2c5b570e207cbab5fc93b398d8"
    },
    {
      "id": "paths",
      "kind": "paths",
      "candidate": "0f5f0b5f1f6f2a1122d1ff5ffa19f612fc26ef31f39318b8d23125a3e34cc039",
      "status": "passed",
      "command": "Migration byte/path/README comparison and git diff --check",
      "exit_code": 0,
      "summary": "PATHS OK; 8 reports unchanged; whitespace OK",
      "environment": "macOS; Python 3.9; current Codex session",
      "coverage": "Removed old paths, preserved evidence and in-progress prose",
      "report": "docs/evidence/2026-10-16-deconstruction-docs/validation.md",
      "report_sha256": "93c323e3a65bc7239620f59a4ce23fd5e9f98c2c5b570e207cbab5fc93b398d8"
    }
  ],
  "delivery": {
    "local": "accepted",
    "commit": "not_requested",
    "remote": "not_requested",
    "clone": "not_requested",
    "runtime": "unverified"
  }
}
```
