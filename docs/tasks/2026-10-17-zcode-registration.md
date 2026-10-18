# zcode 注册切换：仓库目录直载

## 范围与授权

作者要求把 `/Users/xuyun/Documents/ncc-workflow` 注册到 zcode 插件市场，替代 `~/.zcode/local-plugins/ncc-workflow`。走 bounded 路径：一处宿主配置改动＋仓内接入表述同步，插件代码与创作规则不变。

## 改动

- **仓库外（配置，不入指纹）**：`~/.zcode/cli/config.json` → `plugins.dirs` 中 `/Users/xuyun/.zcode/local-plugins/ncc-workflow` 替换为 `/Users/xuyun/Documents/ncc-workflow`；`enabledPlugins` 的 `ncc-workflow@inline` 不变；改前备份为 `~/.zcode/cli/config.json.bak-zcode-reg-20261017`。与 sdlc-workflow、vsc-workflow 的直注册先例同构。
- **仓内**：AGENTS.md（头部说明、五端接入表 zcode 行、同步纪律的 zcode 更新方式）、README.md（接入与更新段、接入表 zcode 行）、docs/README.md（未执行计划清单与活动任务表）、docs/tasks/2026-10-16-docs-refresh.md（陈旧候选补记）。
- 旧克隆退出加载链后保留在磁盘，作为其他机器文档路径与回退副本；其工作树干净、与 origin/main 一致，无丢失。
- 2026-10-17 追记：作者随后要求清理磁盘，已复核该克隆干净且与 origin/main 完全同步（无未跟踪/忽略文件）后删除 `~/.zcode/local-plugins/ncc-workflow`（3.2M）；需要时从 GitHub 重新克隆即可。上条"保留在磁盘"为当时状态。

## 验证与边界

配置 JSON 解析、dirs 条目、manifest 名称与 enabled 状态已程序化断言通过；仓内文档跑插件接线与生成一致性检查。运行加载验证需要新 zcode 会话（当前会话仍加载旧注册），已在 docs/README.md 待办表登记为未验证。回滚：恢复备份配置文件，仓内文档按本任务 diff 还原。未提交、未推送；`runtime` 保持 unverified 直至新会话确认。

```ncc-dev-json
{
  "schema": 1,
  "id": "2026-10-17-zcode-registration",
  "goal": "把 zcode 的插件加载源从安装克隆切换为直接注册本仓库目录，并同步仓内接入表述",
  "route": "bounded",
  "risk_tags": [
    "host-wiring"
  ],
  "repo_root": "/Users/xuyun/Documents/ncc-workflow",
  "plugin_root": "/Users/xuyun/Documents/ncc-workflow",
  "branch": "main",
  "base_commit": "0e3faa03f05f05524442c870c0fafda134e0d8b4",
  "stage": "D5",
  "next": "新 zcode 会话确认实际加载根为仓库目录；提交/推送另行授权",
  "blocked": "",
  "decisions": [
    {
      "source": "作者当前请求",
      "scope": "将仓库目录注册进 zcode（plugins.dirs），替代 ~/.zcode/local-plugins/ncc-workflow；仓内文档同步；本地验证，未授权提交推送"
    },
    {
      "source": "切换前核对",
      "scope": "旧克隆工作树干净、与 origin/main 一致（0e3faa0），无在途改动；克隆保留在磁盘仅退出加载链，不删除"
    },
    {
      "source": "开发者常规决定（可逆）",
      "scope": "AGENTS.md、README.md、docs/README.md 的 zcode 表述改为“本机直注册、其他机器可克隆”；接管全部在途未提交差异纳入本任务范围"
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
    "docs/evidence/2026-10-16-docs-refresh/validation.md",
    "docs/guides/usage.md",
    "docs/superpowers/specs/2026-10-12-dev-workflow-audit.md",
    "docs/superpowers/specs/2026-10-12-dev-workflow-design.md",
    "docs/tasks/2026-10-12-readme-refresh.md",
    "docs/tasks/2026-10-16-deconstruction-docs.md",
    "docs/tasks/2026-10-16-docs-refresh.md",
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
    "docs/evidence/2026-10-17-zcode-registration/validation.md"
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
        "sha256": "77c3238195ed60abf745f6d203a2ead940222244a11722f17b65ded867c04b04",
        "executable": false
      },
      {
        "path": "README.md",
        "type": "file",
        "sha256": "613e0b1ceebffe9f3bb488ddc09d08d48ffa426879a296eba4abacf1ed38c996",
        "executable": false
      },
      {
        "path": "docs/README.md",
        "type": "file",
        "sha256": "4d64aba68a722841565250601aa17f2df7f328305e6e75646df0dfa388ad25e0",
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
        "path": "docs/evidence/2026-10-16-docs-refresh/validation.md",
        "type": "file",
        "sha256": "f64930043a05d956903d93af554400ff07143678f1142d84499e53e82977bc12",
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
        "path": "docs/tasks/2026-10-16-docs-refresh.md",
        "type": "file",
        "sha256": "dd565908e71316f00e7b9dbcc348b601364c14961a58a6214cf7641bba86df72",
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
    "fingerprint": "d0524f69af87f5cdd647d4dba1494e65240db058a9fe14187ecbdd16de46bbdf"
  },
  "required": [
    "wiring",
    "plugin",
    "docs"
  ],
  "evidence": [
    {
      "id": "wiring",
      "kind": "wiring",
      "candidate": "d0524f69af87f5cdd647d4dba1494e65240db058a9fe14187ecbdd16de46bbdf",
      "status": "passed",
      "command": "python3 配置断言：plugins.dirs 替换、JSON 解析、enabledPlugins、manifest 与技能存在性；旧克隆 git 状态核对",
      "exit_code": 0,
      "summary": "注册源已切换；旧克隆干净且与 origin/main 一致；备份留存",
      "environment": "macOS；Python 3.9.6；当前 ZCode 会话",
      "coverage": "zcode 配置接线与切换前事实核对（配置在仓库外，以命令观察为证）",
      "report": "docs/evidence/2026-10-17-zcode-registration/validation.md",
      "report_sha256": "efc82c5a217f7abf7f11d4f4b94d2655159bfd886794d9c1d5dd27ce20b35204"
    },
    {
      "id": "plugin",
      "kind": "plugin",
      "candidate": "d0524f69af87f5cdd647d4dba1494e65240db058a9fe14187ecbdd16de46bbdf",
      "status": "passed",
      "command": "python3 scripts/check_plugin.py -v",
      "exit_code": 0,
      "summary": "PLUGIN OK",
      "environment": "macOS；Python 3.9.6；当前 ZCode 会话",
      "coverage": "仓内文档改后的链接、引用与读取预算",
      "report": "docs/evidence/2026-10-17-zcode-registration/validation.md",
      "report_sha256": "efc82c5a217f7abf7f11d4f4b94d2655159bfd886794d9c1d5dd27ce20b35204"
    },
    {
      "id": "docs",
      "kind": "docs",
      "candidate": "d0524f69af87f5cdd647d4dba1494e65240db058a9fe14187ecbdd16de46bbdf",
      "status": "passed",
      "command": "python3 scripts/build_docs.py --check",
      "exit_code": 0,
      "summary": "DOCS OK",
      "environment": "macOS；Python 3.9.6；当前 ZCode 会话",
      "coverage": "生成文档一致性",
      "report": "docs/evidence/2026-10-17-zcode-registration/validation.md",
      "report_sha256": "efc82c5a217f7abf7f11d4f4b94d2655159bfd886794d9c1d5dd27ce20b35204"
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
