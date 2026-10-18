# NCC 开发流程升级任务

> 已发布候选的验证依据。2026-10-16 随文档目录整理迁至此处；下方冻结 JSON 和原始报告中的路径、指纹是当时记录，不用于当前工作树恢复。现行规范见[开发工作流](../../engineering/workflow.md)。

已确认候选从隔离目录整合至主工作区，主项目原有文档改动完整保留。新入口的规范、脚本与接线均纳入本次候选；原七创作技能正文及十二角色不改动。书稿、素材和私有会话未纳入。

## 已有改动与基线

开始时 ACKNOWLEDGMENTS.md、AGENTS.md、README.md、设计、architecture.md 已修改，旧 docs/完善计划.md 已删除、审查记录未跟踪。这些作者文档改动属于方案上下文，本次保留并纳入可审查候选，不自动还原。基线 HEAD eee42976e5477b6d407b68c5eac4c5c6b9c2ac3c；hooksPath=.githooks。基线全量115项通过（150.824秒），check_plugin、build_docs --check、mech六章通过。

## 范围、计划与回滚

结构方案和分阶段计划见证据块 spec/plan 路径；已授权实现与验证，不请求重复批准关键既定设计。无真实创作内容，外部参考未安装或调用。隔离副本用于验证；作者已在回归后确认具体候选，现已整合主工作树规则。回滚仅处置本任务候选路径，保留原有文档改动；不得 reset/覆盖消费克隆。

## 验收与环境

Python/平台信息、命令结果、锚定章、开发行为和独立评审见 evidence 的报告。完整锚定章基线与候选各18报告，模型/config按可观测信息记录；允许差异和异常处置已在实施计划冻结。宿主静态接线与实际运行分开，当前会话不冒充五端新会话。

| 宿主 | 静态 | 新会话发现/参数/来源/恢复 |
|---|---|---|
| claude | passed：项目级相对软链/登记 | unverified：本会话无对应 CLI 运行证据 |
| codex | passed：项目级相对软链/登记 | unverified：当前为已有 API 会话 |
| kimi | passed：项目级相对软链/登记 | unverified：本会话无对应 CLI 运行证据 |
| grok | passed：项目级相对软链/登记 | unverified：重复发现/优先级待实测 |
| zcode | passed：打包目录与唯一源；消费克隆未更新 | unverified：未更新独立安装克隆或启动新会话 |

## 当前状态

作者于2026-10-12回复“确认”后，已将已验证指纹的内容整合至 /Users/xuyun/Documents/ncc-workflow，原在途改动完整保留。整合前备份位于 /private/tmp/ncc-dev-before-apply-w8bs2ftl。整合后全量复验完成；隔离目录的最终日志保留为 deterministic-isolated.md。

- 整合后全量 **148项通过**（164.709秒）；一致性、生成、机械六章、技能格式和空白检查全部退出0。原始结果见[确定性日志](deterministic.md)。
- 基线/候选各18份独立fresh盲审，检出/定级24/24、结论18/18、干净章严重误报0、无不稳定；[完整回归证据](anchors.log)包含输入、36原报告、score与完整性核验。模型/推理继承链一致，具体ID和采样参数未暴露。
- [八场景独立执行](behavior.log)保留初始失败与修复后结果；[独立评审](review.log)发现的暂存区/仓外源边界缺陷均已修复，并以原反例复验关闭。原106个创作技能/角色/锚定文件逐字不变，registry仅新增开发命令。
- 五端新会话运行仍unverified；作者规则确认passed、本地整合accepted；作者已另行授权提交并推送；升级提交 213e60132793314f70317cca3a2e781cf138d747 已发布至 origin/main，并由 git ls-remote 核对一致。消费克隆更新未请求。

初轮142项日志保留为历史取证；隔离复验148项（185.758秒）和主工作区整合后148项（164.709秒）日志均对应当前指纹。最终验证日志收集曾因读取旧元数据清单而拒绝新增证据路径（测试命令本身通过），已修正临时收集器重读任务记录并重取完整原始日志；该问题未涉及产品内容变化。检查器普通RECORD OK只表示记录/候选一致；本任务现已取得真实作者确认并通过 --delivery。

发布前暂存检查补充：三份原始证据汇编清理行尾空白和文件末尾空行，语义、输入输出及评测结果不变；相应报告哈希已更新，产品指纹不变。

发布记录（2026-10-12）：先 git pull --ff-only，无远端变化；27路径精确暂存，无私有路径；暂存后 --delivery 与空白检查通过，钩子保持启用。升级提交 213e60132793314f70317cca3a2e781cf138d747 已推送，远端核对相同。补充记录本身另行提交；不改变产品指纹。发布前记录格式失误已在未推送提交中修复并重新检查通过。

```ncc-dev-json
{
  "schema": 1,
  "id": "2026-10-12-ncc-dev",
  "goal": "按修订设计升级 NCC 插件开发流程",
  "route": "architectural",
  "risk_tags": [
    "rules",
    "cross-host",
    "resume"
  ],
  "repo_root": "/Users/xuyun/Documents/ncc-workflow",
  "plugin_root": "/Users/xuyun/Documents/ncc-workflow",
  "branch": "main",
  "base_commit": "eee42976e5477b6d407b68c5eac4c5c6b9c2ac3c",
  "stage": "D7",
  "next": "升级候选已发布；本记录补充提交后同步 main。消费克隆同步未请求，五端新会话运行仍 unverified",
  "blocked": "",
  "decisions": [
    {
      "source": "作者当前请求：根据 specs 计划升级",
      "scope": "实现与验证设计；未请求提交、推送或更新安装克隆"
    },
    {
      "source": "AGENTS.md 与修订设计",
      "scope": "规则回归后由作者确认；保留在途文档；隔离候选"
    },
    {
      "source": "2026-10-12 当前作者会话回复：确认",
      "scope": "将指纹 843589922f691c02da8834f5a80fa0b053c93e0ee4b0a5cb2716dc1f52326599 的具体候选整合到本地工作区并验证；未请求提交发布或更新安装克隆"
    },
    {
      "source": "2026-10-12 作者当前请求：提交并推送",
      "scope": "将已确认并通过整合后验证的候选提交至 main 并推送 origin；未请求更新独立安装克隆或五端新会话验收"
    }
  ],
  "spec": "docs/superpowers/specs/2026-10-12-dev-workflow-design.md",
  "plan": "docs/dev/2026-10-12-ncc-dev-plan.md",
  "scope": [
    ".agents/skills/ncc-dev",
    ".claude/commands/ncc-dev.md",
    ".claude/skills/ncc-dev",
    "ACKNOWLEDGMENTS.md",
    "AGENTS.md",
    "README.md",
    "commands/ncc-dev.md",
    "docs/dev-workflow.md",
    "docs/dev/2026-10-12-ncc-dev-plan.md",
    "docs/superpowers/specs/2026-10-12-dev-workflow-audit.md",
    "docs/superpowers/specs/2026-10-12-dev-workflow-design.md",
    "docs/usage.md",
    "docs/完善计划.md",
    "scripts/check_dev_workflow.py",
    "scripts/check_plugin.py",
    "scripts/test_dev_workflow.py",
    "skills/ncc-dev/SKILL.md",
    "workflow/architecture.md",
    "workflow/registry.json"
  ],
  "foreign_changes": {},
  "evidence_paths": [
    "docs/dev/evidence/2026-10-12-ncc-dev/deterministic.md",
    "docs/dev/evidence/2026-10-12-ncc-dev/deterministic-before-independent-fixes.md",
    "docs/dev/evidence/2026-10-12-ncc-dev/behavior.log",
    "docs/dev/evidence/2026-10-12-ncc-dev/review.log",
    "docs/dev/evidence/2026-10-12-ncc-dev/anchors.log",
    "docs/dev/evidence/2026-10-12-ncc-dev/author.log",
    "docs/dev/evidence/2026-10-12-ncc-dev/deterministic-isolated.md"
  ],
  "candidate": {
    "base_commit": "eee42976e5477b6d407b68c5eac4c5c6b9c2ac3c",
    "files": [
      {
        "path": ".agents/skills/ncc-dev",
        "type": "symlink",
        "target": "../../skills/ncc-dev",
        "executable": false
      },
      {
        "path": ".claude/commands/ncc-dev.md",
        "type": "symlink",
        "target": "../../commands/ncc-dev.md",
        "executable": false
      },
      {
        "path": ".claude/skills/ncc-dev",
        "type": "symlink",
        "target": "../../skills/ncc-dev",
        "executable": false
      },
      {
        "path": "ACKNOWLEDGMENTS.md",
        "type": "file",
        "sha256": "6f14682b8185a16425249df76a0583945dbb5e20e899b6ccaccde03d5fb781dd",
        "executable": false
      },
      {
        "path": "AGENTS.md",
        "type": "file",
        "sha256": "655872cd7c8660c2ca6ad5c03b86f2215f37a9e1e6dffbbb9e15fdc3c414880e",
        "executable": false
      },
      {
        "path": "README.md",
        "type": "file",
        "sha256": "e6e8ba0d49b46df280b65250d8b2c0c800533b37f8944ab46cb266fe5ab9c51b",
        "executable": false
      },
      {
        "path": "commands/ncc-dev.md",
        "type": "file",
        "sha256": "56120144474fa0c14c0add464e7c63552c40a76b433b2a1197351b99070c6d2c",
        "executable": false
      },
      {
        "path": "docs/dev-workflow.md",
        "type": "file",
        "sha256": "819e0a427653092955f2c454fdadfbf85febf4f6b598ca12bcea2a475f062ade",
        "executable": false
      },
      {
        "path": "docs/dev/2026-10-12-ncc-dev-plan.md",
        "type": "file",
        "sha256": "4e62eb7a57598fd0702527b8b4cf6ebfa800629668d90623ba566e729d5ab469",
        "executable": false
      },
      {
        "path": "docs/superpowers/specs/2026-10-12-dev-workflow-audit.md",
        "type": "file",
        "sha256": "77511ddaf773ec8414e5f8bb65735494852aab5607728309ec5ab6f34dd24fbb",
        "executable": false
      },
      {
        "path": "docs/superpowers/specs/2026-10-12-dev-workflow-design.md",
        "type": "file",
        "sha256": "ee99f2fab4396d83f2860710a250f9829fde9767739019bffeea27ba979dbd2e",
        "executable": false
      },
      {
        "path": "docs/usage.md",
        "type": "file",
        "sha256": "dc6da8b732fe9a53fafb4a8cb92b5b301daac0120dec078d606e69a5d0102b1b",
        "executable": false
      },
      {
        "path": "docs/完善计划.md",
        "type": "deleted"
      },
      {
        "path": "scripts/check_dev_workflow.py",
        "type": "file",
        "sha256": "5eee7ea25352f196df2c448e5f7faf4537428abfff6500554a4b8d4ba7d35141",
        "executable": false
      },
      {
        "path": "scripts/check_plugin.py",
        "type": "file",
        "sha256": "32e707f7eeaa3339eb9462b190aa81a9568a886e1d7290da2ff499a44e58a037",
        "executable": false
      },
      {
        "path": "scripts/test_dev_workflow.py",
        "type": "file",
        "sha256": "526aa395d9add47b6d5f7d47180e5a6742eee1a8321839d8ea2d25fbb5b73be3",
        "executable": false
      },
      {
        "path": "skills/ncc-dev/SKILL.md",
        "type": "file",
        "sha256": "24327e679a9ffa137ff6a3d1034e4e2fedf82f605269337b63ce35efbbe4ccc0",
        "executable": false
      },
      {
        "path": "workflow/architecture.md",
        "type": "file",
        "sha256": "05dd81d715352d19072187074dd5db6d21cbad8136b3d3494f3a762d22bb3646",
        "executable": false
      },
      {
        "path": "workflow/registry.json",
        "type": "file",
        "sha256": "7892f62f261264d01cfa33b553bfc67c6fef7121ec5c5ca5f37c5f5985a3c4be",
        "executable": false
      }
    ],
    "fingerprint": "843589922f691c02da8834f5a80fa0b053c93e0ee4b0a5cb2716dc1f52326599"
  },
  "required": [
    "unit",
    "plugin",
    "docs",
    "mech",
    "anchors",
    "behavior",
    "review",
    "author"
  ],
  "evidence": [
    {
      "id": "behavior-independent",
      "kind": "behavior",
      "candidate": "843589922f691c02da8834f5a80fa0b053c93e0ee4b0a5cb2716dc1f52326599",
      "status": "passed",
      "command": "Independent fresh agent execution and targeted final-source reprobes",
      "exit_code": null,
      "summary": "8 real forward scenarios with disclosed boundaries and final fix reprobes",
      "environment": "Same host inherited agent model; synthetic local Git fixtures; exact model ID/parameters unavailable",
      "coverage": "Development paths and recovery; original scenarios before fixes plus final-source boundary reprobes; no fresh CLI/host claim",
      "report": "docs/dev/evidence/2026-10-12-ncc-dev/behavior.log",
      "report_sha256": "62f37872e59b6b4f148193b8a547640339a592b429af5cfceacaa4fcb1809e60"
    },
    {
      "id": "review-independent",
      "kind": "review",
      "candidate": "843589922f691c02da8834f5a80fa0b053c93e0ee4b0a5cb2716dc1f52326599",
      "status": "passed",
      "command": "Independent fresh agent execution and targeted final-source reprobes",
      "exit_code": null,
      "summary": "B1/B2 closed by original independent probes; positive/negative boundary checks passed",
      "environment": "Same host inherited agent model; synthetic local Git fixtures; exact model ID/parameters unavailable",
      "coverage": "Code/protocol review and final-source index/source-boundary probes; no full-test/model/host/author approval claim",
      "report": "docs/dev/evidence/2026-10-12-ncc-dev/review.log",
      "report_sha256": "16a6b890645543c252e6965154852327a76bdd4c03aede31fe7c05c88a510039"
    },
    {
      "id": "anchors-full",
      "kind": "anchors",
      "candidate": "843589922f691c02da8834f5a80fa0b053c93e0ee4b0a5cb2716dc1f52326599",
      "status": "passed",
      "command": "ncc_eval.py prepare (2 groups x 6 anchors x 3 runs); 36 independent fresh continuity reports; ncc_eval.py score both groups; integrity and manual extra review",
      "exit_code": 0,
      "summary": "18/18 reports each; detection/grading 24/24; verdict 18/18; clean severe false alarms 0; no instability or regression",
      "environment": "Same root model/reasoning inheritance chain; exact model ID and sampling parameters unavailable",
      "coverage": "Original creative audit only; frozen inputs identical. Does not cover ncc-dev routing or fresh host loading. Original raw reports and score preserved including one placeholder parse extra.",
      "report": "docs/dev/evidence/2026-10-12-ncc-dev/anchors.log",
      "report_sha256": "d04de48d7d3991deb26eea88ec07e0393ffdbab96be4ffb4aa83ef26b6609d87"
    },
    {
      "id": "author-confirmation",
      "kind": "author",
      "candidate": "843589922f691c02da8834f5a80fa0b053c93e0ee4b0a5cb2716dc1f52326599",
      "status": "passed",
      "command": "Current author conversation: confirmation of concrete post-regression candidate",
      "exit_code": null,
      "summary": "Author replied 确认; local integration authorized for the recorded fingerprint",
      "environment": "Current author conversation",
      "coverage": "Local project rule integration only; excludes remote publication/installed clone/runtime verification",
      "report": "docs/dev/evidence/2026-10-12-ncc-dev/author.log",
      "report_sha256": "ea93f0827aa673eb00d9badb24c25f922ed5ae00f9c795a0ff94950f2e087329"
    },
    {
      "id": "unit-final",
      "kind": "unit",
      "candidate": "843589922f691c02da8834f5a80fa0b053c93e0ee4b0a5cb2716dc1f52326599",
      "status": "passed",
      "command": "python3 -m unittest discover -s scripts -p test_*.py",
      "exit_code": 0,
      "summary": "Ran 148 tests in 164.709s",
      "environment": "macOS-26.6.2-arm64-arm-64bit / Python 3.9.6",
      "coverage": "Deterministic only; no host runtime or model behavior claim",
      "report": "docs/dev/evidence/2026-10-12-ncc-dev/deterministic.md",
      "report_sha256": "922a4c46b8a8413cec6a957a2df1f36597e54c51aac7cc7a681d183a0254d25f"
    },
    {
      "id": "plugin-final",
      "kind": "plugin",
      "candidate": "843589922f691c02da8834f5a80fa0b053c93e0ee4b0a5cb2716dc1f52326599",
      "status": "passed",
      "command": "python3 scripts/check_plugin.py -v",
      "exit_code": 0,
      "summary": "PLUGIN OK",
      "environment": "macOS-26.6.2-arm64-arm-64bit / Python 3.9.6",
      "coverage": "Deterministic only; no host runtime or model behavior claim",
      "report": "docs/dev/evidence/2026-10-12-ncc-dev/deterministic.md",
      "report_sha256": "922a4c46b8a8413cec6a957a2df1f36597e54c51aac7cc7a681d183a0254d25f"
    },
    {
      "id": "docs-final",
      "kind": "docs",
      "candidate": "843589922f691c02da8834f5a80fa0b053c93e0ee4b0a5cb2716dc1f52326599",
      "status": "passed",
      "command": "python3 scripts/build_docs.py --check",
      "exit_code": 0,
      "summary": "DOCS OK",
      "environment": "macOS-26.6.2-arm64-arm-64bit / Python 3.9.6",
      "coverage": "Deterministic only; no host runtime or model behavior claim",
      "report": "docs/dev/evidence/2026-10-12-ncc-dev/deterministic.md",
      "report_sha256": "922a4c46b8a8413cec6a957a2df1f36597e54c51aac7cc7a681d183a0254d25f"
    },
    {
      "id": "mech-final",
      "kind": "mech",
      "candidate": "843589922f691c02da8834f5a80fa0b053c93e0ee4b0a5cb2716dc1f52326599",
      "status": "passed",
      "command": "python3 scripts/ncc_eval.py mech",
      "exit_code": 0,
      "summary": "PASS A06-干净对照",
      "environment": "macOS-26.6.2-arm64-arm-64bit / Python 3.9.6",
      "coverage": "Deterministic only; no host runtime or model behavior claim",
      "report": "docs/dev/evidence/2026-10-12-ncc-dev/deterministic.md",
      "report_sha256": "922a4c46b8a8413cec6a957a2df1f36597e54c51aac7cc7a681d183a0254d25f"
    },
    {
      "id": "whitespace-final",
      "kind": "whitespace",
      "candidate": "843589922f691c02da8834f5a80fa0b053c93e0ee4b0a5cb2716dc1f52326599",
      "status": "passed",
      "command": "git diff --check",
      "exit_code": 0,
      "summary": "No reported errors",
      "environment": "macOS-26.6.2-arm64-arm-64bit / Python 3.9.6",
      "coverage": "Deterministic only; no host runtime or model behavior claim",
      "report": "docs/dev/evidence/2026-10-12-ncc-dev/deterministic.md",
      "report_sha256": "922a4c46b8a8413cec6a957a2df1f36597e54c51aac7cc7a681d183a0254d25f"
    },
    {
      "id": "skill-final",
      "kind": "skill",
      "candidate": "843589922f691c02da8834f5a80fa0b053c93e0ee4b0a5cb2716dc1f52326599",
      "status": "passed",
      "command": "python3 /Users/xuyun/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/ncc-dev",
      "exit_code": 0,
      "summary": "Skill is valid!",
      "environment": "macOS-26.6.2-arm64-arm-64bit / Python 3.9.6",
      "coverage": "Deterministic only; no host runtime or model behavior claim",
      "report": "docs/dev/evidence/2026-10-12-ncc-dev/deterministic.md",
      "report_sha256": "922a4c46b8a8413cec6a957a2df1f36597e54c51aac7cc7a681d183a0254d25f"
    }
  ],
  "delivery": {
    "local": "accepted",
    "commit": "213e60132793314f70317cca3a2e781cf138d747",
    "remote": "origin/main verified by git ls-remote: 213e60132793314f70317cca3a2e781cf138d747",
    "clone": "not_requested",
    "runtime": "unverified"
  }
}
```
