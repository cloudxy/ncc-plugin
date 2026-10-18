# 文档全量更新与归属收敛

## 范围与计划

作者要求：按当前项目全方位更新 docs/ 内容；整理出尚未执行的计划方案；对 docs/ 结构做前瞻规划、对文件归属做规则性收敛。本任务走 bounded 路径（文档内容与接线调整，接口与数据契约不变），计划：

1. 归属收敛：`workflow/` 只保留现行事实源（registry.json、principles.md、architecture.md）；已实现的设计记录迁入 `docs/designs/<模块>/`（memory、preparation 两个模块目录随之建立），现行治理规范 source-vetting 迁入 `docs/engineering/`；同步更新全部引用。
2. 规范更新：重写[文档组织规范](../engineering/documentation.md)——归属判定规则、命名与状态标头、生命周期（候选→实施→留档/归档/删除）、模块清单与预留扩展；删除已执行完毕的一次性迁移方案。
3. 导航与计划清单：重写[文档导航](../README.md)——现行文档、模块设计状态、**未执行的计划与待办**集中一处；更新拆书统一方案的 P0 完成状态；核对使用指南与现状一致。
4. 验证：按影响范围只跑文档搬迁类检查（任务检查器用例、插件链接/接线、生成一致性、迁移与引用核对），不跑无关全量与模型回归。

## 决定与接管

- 本次请求授权：docs 内容更新、结构收敛与本地验证；未包含提交、推送、消费克隆同步。
- 接管在途候选：`2026-10-12-readme-refresh` 与 `2026-10-16-deconstruction-docs` 两任务的未提交改动（README、docs 重组、脚本/技能路径适配）全部纳入本任务范围继续交付；两记录保留在 tasks/（一有待办、一待提交授权），其旧通过证据不为本候选背书。
- 归属规则（开发者常规决定，可逆）：现行规则事实源不进 docs；设计记录与升级方案按模块进 `designs/`；现行治理规范进 `engineering/`；使用说明进 `guides/`。
- 已完成任务记录迁入 `evidence/<任务号>/task.md` 的时机定为"交付候选已提交之后"（对齐 2026-10-12-ncc-dev 先例）；未提交的已验收任务仍留 tasks/ 便于恢复与提交前核对。

## 基线与边界

基线 `0e3faa0`，分支 main，环境 macOS / Python 3.9。不改动 `workflow/registry.json`、`skills/`（除 memory.md 一处路径）、`agents/`、`commands/` 的语义；不改创作判据，不触发模型回归；不动 `novels/` 私有内容与冻结证据报告字节。回滚按本任务精确范围恢复（含三份文件的目录位置与引用改点），不覆盖此前任务的既有改动。

## 状态

D5：全部编辑完成，四类检查通过，自查完成、独立评审待办；见[验证报告](../evidence/2026-10-16-docs-refresh/validation.md)。

2026-10-17 补记：后续任务[切换 zcode 注册](2026-10-17-zcode-registration.md)按作者指令更新了 AGENTS.md、README.md、docs/README.md 中的 zcode 接入表述；本记录冻结候选及其 passed 证据仅对应改动前版本，恢复本任务须重新冻结并验证。

```ncc-dev-json
{
  "schema": 1,
  "id": "2026-10-16-docs-refresh",
  "goal": "按当前项目全量更新 docs 内容，收敛文件归属并集中呈现未执行计划",
  "route": "bounded",
  "risk_tags": [
    "documentation-migration"
  ],
  "repo_root": "/Users/xuyun/Documents/ncc-workflow",
  "plugin_root": "/Users/xuyun/Documents/ncc-workflow",
  "branch": "main",
  "base_commit": "0e3faa03f05f05524442c870c0fafda134e0d8b4",
  "stage": "D5",
  "next": "作者复核候选；提交/推送/克隆同步另行授权",
  "blocked": "",
  "decisions": [
    {
      "source": "作者当前请求",
      "scope": "全方位更新 docs、整理未执行计划、结构与归属前瞻收敛；本地验证，未授权发布"
    },
    {
      "source": "既有两任务在途状态",
      "scope": "接管其未提交候选纳入本任务范围；旧记录保留，旧证据不背书新候选"
    },
    {
      "source": "开发者常规决定（可逆）",
      "scope": "workflow/ 只留现行事实源；设计记录进 designs/<模块>/，治理规范进 engineering/；任务记录归档时机为候选提交后"
    }
  ],
  "spec": "",
  "plan": "",
  "scope": [
    "ACKNOWLEDGMENTS.md",
    "AGENTS.md",
    "README.md",
    "docs/README.md",
    "docs/designs/deconstruction/upgrade.md",
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
    "docs/guides/usage.md",
    "docs/superpowers/specs/2026-10-12-dev-workflow-audit.md",
    "docs/superpowers/specs/2026-10-12-dev-workflow-design.md",
    "docs/tasks/2026-10-12-readme-refresh.md",
    "docs/tasks/2026-10-16-deconstruction-docs.md",
    "docs/usage.md",
    "scripts/check_dev_workflow.py",
    "scripts/check_plugin.py",
    "scripts/test_dev_workflow.py",
    "skills/ncc-dev/SKILL.md",
    "skills/ncc/references/memory.md",
    "workflow/architecture.md",
    "workflow/memory-evolution-design.md",
    "workflow/preparation-design.md",
    "workflow/source-vetting.md"
  ],
  "foreign_changes": {},
  "evidence_paths": [
    "docs/evidence/2026-10-16-docs-refresh/validation.md"
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
        "sha256": "fd5a550f46c1050ac4cb7c21d2998ed8f6e75904cff9ff0ed48f0a7116de045b",
        "executable": false
      },
      {
        "path": "docs/designs/deconstruction/upgrade.md",
        "type": "file",
        "sha256": "b916b907be39af02f7a8e803eac06d7f5a205a733155768b3538eec30ffb11da",
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
        "path": "docs/designs/memory/memory-evolution-design.md",
        "type": "file",
        "sha256": "19ac8898cb682af8a7dabbdcd765c590c3f858101f52c0a39d674a4268276f4e",
        "executable": false
      },
      {
        "path": "docs/designs/preparation/preparation-design.md",
        "type": "file",
        "sha256": "462e38fdab062627953aeb3a68fdad00aa5a77e360e17c874969efac759636f0",
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
        "sha256": "0f9324bc1d592d7fb6a2a4f11b5f3c386ff440028404a7703470cecc195fa39a",
        "executable": false
      },
      {
        "path": "docs/engineering/source-vetting.md",
        "type": "file",
        "sha256": "aeec758b024ffa6a02a5f9f8f234ce89f53eda853af15346e22b12bfa28039ae",
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
        "path": "docs/evidence/2026-10-16-deconstruction-docs/validation.md",
        "type": "file",
        "sha256": "93c323e3a65bc7239620f59a4ce23fd5e9f98c2c5b570e207cbab5fc93b398d8",
        "executable": false
      },
      {
        "path": "docs/guides/usage.md",
        "type": "file",
        "sha256": "0d91511f176d90485d781e7429c18d020e54ff565921301ea364e559b2ebb43a",
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
        "path": "docs/tasks/2026-10-16-deconstruction-docs.md",
        "type": "file",
        "sha256": "71cc76349a4dbfa2cafb53c392b764490c33da81ac6db32a8d86f6bb1240ccbd",
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
        "path": "skills/ncc/references/memory.md",
        "type": "file",
        "sha256": "015d0c9e73b18ef71a5650bb0cb3d62d633d1c2903b007de5d552abe1e3d2137",
        "executable": false
      },
      {
        "path": "workflow/architecture.md",
        "type": "file",
        "sha256": "efa96a61e473d8fedb39e3b458e0f7efcadc501f007e7781974dabd49302fc96",
        "executable": false
      },
      {
        "path": "workflow/memory-evolution-design.md",
        "type": "deleted"
      },
      {
        "path": "workflow/preparation-design.md",
        "type": "deleted"
      },
      {
        "path": "workflow/source-vetting.md",
        "type": "deleted"
      }
    ],
    "fingerprint": "c93bdc6dea795b1c27dfaeae1fbe72f573d88161c2d701ebbb8e9c01c933c535"
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
      "candidate": "c93bdc6dea795b1c27dfaeae1fbe72f573d88161c2d701ebbb8e9c01c933c535",
      "status": "passed",
      "command": "python3 -m unittest discover -s scripts -p 'test_dev_workflow.py'",
      "exit_code": 0,
      "summary": "36 tests OK；初轮 25.385s、终轮 46.663s",
      "environment": "macOS；Python 3.9.6；当前 ZCode 会话",
      "coverage": "任务/证据路径、指纹与边界用例",
      "report": "docs/evidence/2026-10-16-docs-refresh/validation.md",
      "report_sha256": "f64930043a05d956903d93af554400ff07143678f1142d84499e53e82977bc12"
    },
    {
      "id": "plugin",
      "kind": "plugin",
      "candidate": "c93bdc6dea795b1c27dfaeae1fbe72f573d88161c2d701ebbb8e9c01c933c535",
      "status": "passed",
      "command": "python3 scripts/check_plugin.py -v",
      "exit_code": 0,
      "summary": "PLUGIN OK；迁移链接修复后通过",
      "environment": "macOS；Python 3.9.6；当前 ZCode 会话",
      "coverage": "活动文档链接、命令/技能接线、读取预算",
      "report": "docs/evidence/2026-10-16-docs-refresh/validation.md",
      "report_sha256": "f64930043a05d956903d93af554400ff07143678f1142d84499e53e82977bc12"
    },
    {
      "id": "docs",
      "kind": "docs",
      "candidate": "c93bdc6dea795b1c27dfaeae1fbe72f573d88161c2d701ebbb8e9c01c933c535",
      "status": "passed",
      "command": "python3 scripts/build_docs.py --check",
      "exit_code": 0,
      "summary": "DOCS OK",
      "environment": "macOS；Python 3.9.6；当前 ZCode 会话",
      "coverage": "生成文档与 README 版本行一致性",
      "report": "docs/evidence/2026-10-16-docs-refresh/validation.md",
      "report_sha256": "f64930043a05d956903d93af554400ff07143678f1142d84499e53e82977bc12"
    },
    {
      "id": "paths",
      "kind": "paths",
      "candidate": "c93bdc6dea795b1c27dfaeae1fbe72f573d88161c2d701ebbb8e9c01c933c535",
      "status": "passed",
      "command": "迁移逐字节/差异对比、全仓旧路径 grep、git diff --check",
      "exit_code": 0,
      "summary": "两份纯移动逐字节一致；preparation-design 仅三行链接深度修复；无残留旧路径；无空白错误",
      "environment": "macOS；Python 3.9.6；当前 ZCode 会话",
      "coverage": "文件迁移、引用同步与冻结证据保全",
      "report": "docs/evidence/2026-10-16-docs-refresh/validation.md",
      "report_sha256": "f64930043a05d956903d93af554400ff07143678f1142d84499e53e82977bc12"
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
