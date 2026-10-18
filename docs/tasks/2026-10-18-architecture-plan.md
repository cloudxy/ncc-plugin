# 架构升级方案复核与完善

## 范围与授权

本任务沿用 2026-10-18 架构方案任务，不新增重复活动记录。作者本轮要求检查 zcode 制定的升级方案，完善问题处置、步骤与办法。当前交付是[架构成长方案](../designs/engineering/architecture-growth.md)、[审查复核修正](../designs/engineering/architecture-audit.md)、[拆书方案落点补全](../designs/deconstruction/upgrade.md)和[文档导航](../README.md)，走 bounded 文档路径。架构实施本身后续另按 architectural 路径执行。

plugin_root 与 repo_root 均为 `/Users/xuyun/Documents/ncc-workflow`，分支 main，插件版本 3.2.0。已读取 ncc-dev 与开发规范。未改运行代码、技能、创作规则或任何私有书库；未暂存、提交、推送或同步安装。

## 本轮计划与完成内容

1. 核对原方案和原审查，追踪清单字段、registry 读者、CLI 职责、测试定位方式及拆书 P1 接口。
2. 将问题归为 R1–R9，纠正五份清单/四版本、13 个顶层脚本、三个新增拆书命令等事实；不把文件规模推断当成已发生故障。
3. 重写 G0/G1/G2/G5/G3a/G3b 的具体操作、依赖、失败用例、兼容期限与回退；G4 的文档归属直接同步到拆书 P1。
4. 内容、链接、生成一致性与 41 键归属对照；冻结本轮精确候选并登记报告。未来实现的测试要求写入方案，本轮不伪造功能通过证据。

推荐方案的关键取舍：清单按真实字段校验；脚本移动保留薄入口；CLI 只拆参数注册；registry 先统一消费者再分片，保留生成聚合视图；近似键和旧数据迁移支持本轮不清理。以上是待实施的具体建议，不冒称作者已经确认。

## 证据与差异归属

恢复前运行原任务 check 通过，原候选为 `bfd47a04fa4a2fddc8a138eea2d5973ee01bb8461a6f66822ed419a3b3a992bc`。原 [validation.md](../evidence/2026-10-18-architecture-plan/validation.md) 字节保留，作为旧方案检查历史，不继承其 passed 到新候选。原记录将多个旧任务的在途差异一并纳入 scope；本轮收窄到实际修订的四份文档，其余精确登记为 foreign_changes，不重新认领或验收。

当前报告见 [recheck.md](../evidence/2026-10-18-architecture-plan/recheck.md)。验证选择：纯文档修订，只做事实/字段/消费者核对、链接接线、生成一致性、空白检查和候选新鲜度；不跑无关全量或模型回归。实施阶段的运行兼容、失败注入、完整测试与宿主新会话证据均尚未产生。本轮为当前会话复核与自查，独立评审待办。

## 风险、恢复与回滚

方案与代码之间的差异已标为拟建/待实施；下次实施先重建基线，不能用静态事实数字代替当前盘点。恢复从 JSON 的 next 和现行方案继续；若本轮文档变化，重跑对应检查并更新候选。撤销本轮时只还原四份文档及本记录的本轮增量，保留其他在途差异；不 reset 工作树，不回写冻结历史报告。

```ncc-dev-json
{
  "schema": 1,
  "id": "2026-10-18-architecture-plan",
  "goal": "复核并完善 zcode 架构升级方案，补齐真实字段映射、实施步骤、兼容、验证与回滚；仅交付文档候选",
  "route": "bounded",
  "risk_tags": [],
  "repo_root": "/Users/xuyun/Documents/ncc-workflow",
  "plugin_root": "/Users/xuyun/Documents/ncc-workflow",
  "branch": "main",
  "base_commit": "0e3faa03f05f05524442c870c0fafda134e0d8b4",
  "stage": "D5",
  "next": "本轮方案修订已交付本地候选；独立评审待办。作者要求实施时新开 architectural 任务，从 G0/G1 开始，继承有效授权与推荐方案。",
  "blocked": "",
  "decisions": [
    {
      "source": "作者前序请求（原任务记录）",
      "scope": "固化架构审查并先出升级方案；未授权实施插件功能或发布"
    },
    {
      "source": "作者本轮请求",
      "scope": "检查 zcode 升级方案的问题并完善方案及解决步骤与办法；修改当前方案与必要关联文档，不执行 G1–G5 功能改造"
    },
    {
      "source": "本轮代码复核与常规文档维护决定",
      "scope": "沿用同一任务号；纠正原方案的清单/消费者/业务边界事实；补齐分批执行与验收；调整本次候选为四份相关文档，其他在途差异保留归属"
    },
    {
      "source": "本轮候选设计建议，尚非实施确认",
      "scope": "清单维持现有版本源；迁移保留旧入口；不混做 registry 改名/退役；统一读取后再分片并保留生成兼容视图"
    }
  ],
  "spec": "docs/designs/engineering/architecture-growth.md",
  "plan": "docs/designs/engineering/architecture-growth.md",
  "scope": [
    "docs/README.md",
    "docs/designs/deconstruction/upgrade.md",
    "docs/designs/engineering/architecture-audit.md",
    "docs/designs/engineering/architecture-growth.md"
  ],
  "foreign_changes": {
    "ACKNOWLEDGMENTS.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "AGENTS.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "README.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/designs/engineering/source-audit.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/designs/engineering/workflow.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/designs/memory/memory-evolution-design.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/designs/preparation/preparation-design.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/dev-workflow.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/dev/2026-10-12-ncc-dev-plan.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/dev/evidence/2026-10-12-ncc-dev/anchors.log": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/dev/evidence/2026-10-12-ncc-dev/author.log": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/dev/evidence/2026-10-12-ncc-dev/behavior.log": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/dev/evidence/2026-10-12-ncc-dev/deterministic-before-independent-fixes.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/dev/evidence/2026-10-12-ncc-dev/deterministic-isolated.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/dev/evidence/2026-10-12-ncc-dev/deterministic.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/dev/evidence/2026-10-12-ncc-dev/review.log": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/dev/tasks/2026-10-12-ncc-dev.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/engineering/documentation.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/engineering/source-vetting.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/engineering/workflow.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/evidence/2026-10-12-ncc-dev/anchors.log": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/evidence/2026-10-12-ncc-dev/author.log": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/evidence/2026-10-12-ncc-dev/behavior.log": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/evidence/2026-10-12-ncc-dev/deterministic-before-independent-fixes.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/evidence/2026-10-12-ncc-dev/deterministic-isolated.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/evidence/2026-10-12-ncc-dev/deterministic.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/evidence/2026-10-12-ncc-dev/review.log": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/evidence/2026-10-12-ncc-dev/task.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/evidence/2026-10-13-readme-refresh/validation.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/evidence/2026-10-16-deconstruction-docs/validation.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/evidence/2026-10-16-docs-refresh/validation.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/evidence/2026-10-17-zcode-registration/validation.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/guides/usage.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/superpowers/specs/2026-10-12-dev-workflow-audit.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/superpowers/specs/2026-10-12-dev-workflow-design.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/tasks/2026-10-12-readme-refresh.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/tasks/2026-10-16-deconstruction-docs.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/tasks/2026-10-16-docs-refresh.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/tasks/2026-10-17-zcode-registration.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "docs/usage.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "scripts/check_dev_workflow.py": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "scripts/check_plugin.py": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "scripts/test_dev_workflow.py": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "skills/ncc-dev/SKILL.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "skills/ncc/references/memory.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "workflow/architecture.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "workflow/memory-evolution-design.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "workflow/preparation-design.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收",
    "workflow/source-vetting.md": "本轮开始前已存在的文档整理/开发入口/接线任务差异；保留原归属，本轮未修改或重新验收"
  },
  "evidence_paths": [
    "docs/evidence/2026-10-18-architecture-plan/validation.md",
    "docs/evidence/2026-10-18-architecture-plan/recheck.md"
  ],
  "candidate": {
    "base_commit": "0e3faa03f05f05524442c870c0fafda134e0d8b4",
    "files": [
      {
        "path": "docs/README.md",
        "type": "file",
        "sha256": "cfb522d35318e844deb6a97571497dc4865b81188bfd2a5986b9f83366cbfe45",
        "executable": false
      },
      {
        "path": "docs/designs/deconstruction/upgrade.md",
        "type": "file",
        "sha256": "6978d2231505fb714957db82e269c53e79f0d874b016c30d366982a432c5f0c9",
        "executable": false
      },
      {
        "path": "docs/designs/engineering/architecture-audit.md",
        "type": "file",
        "sha256": "33da284c2df87a2d993c3a1ed65607fcec3fc76028352e734bf8b0bfe76b537e",
        "executable": false
      },
      {
        "path": "docs/designs/engineering/architecture-growth.md",
        "type": "file",
        "sha256": "80cf4b7ac6ed7c828b6cbf98ec46583038639041264f8a4e5988b174ab8bbe7d",
        "executable": false
      }
    ],
    "fingerprint": "0f06f7c2d4f276bc5f603e929cc27ddd44317ad0eeb4577687cc59557fef8972"
  },
  "required": [
    "plan",
    "plugin",
    "docs"
  ],
  "evidence": [
    {
      "id": "plan-review",
      "kind": "plan",
      "candidate": "0f06f7c2d4f276bc5f603e929cc27ddd44317ad0eeb4577687cc59557fef8972",
      "status": "passed",
      "command": "对照实际代码自查 R1–R9；Python 标准库解析清单、统计脚本、核对方案 41 键映射、比对开始前文件 hash",
      "exit_code": 0,
      "summary": "已修正事实错误，补齐依赖、操作、失败用例、兼容与回退；四份产品文档外无运行内容变化",
      "environment": "macOS; Python 3.9.6; main; 当前会话复核/自查",
      "coverage": "方案可执行性、五份清单实际结构、41 键完整唯一归属、脚本与导入/调用路径、修改边界",
      "report": "docs/evidence/2026-10-18-architecture-plan/recheck.md",
      "report_sha256": "4e85d959d56aa238881a1b0649bce2561a642e7efb3c8a958290f56056176348"
    },
    {
      "id": "plugin-recheck",
      "kind": "plugin",
      "candidate": "0f06f7c2d4f276bc5f603e929cc27ddd44317ad0eeb4577687cc59557fef8972",
      "status": "passed",
      "command": "python3 scripts/check_plugin.py -v",
      "exit_code": 0,
      "summary": "PLUGIN OK",
      "environment": "macOS; Python 3.9.6; main; 当前会话复核/自查",
      "coverage": "活动文档链接、接线、现有读取预算；不包含未实现的 G1 清单规则",
      "report": "docs/evidence/2026-10-18-architecture-plan/recheck.md",
      "report_sha256": "4e85d959d56aa238881a1b0649bce2561a642e7efb3c8a958290f56056176348"
    },
    {
      "id": "docs-recheck",
      "kind": "docs",
      "candidate": "0f06f7c2d4f276bc5f603e929cc27ddd44317ad0eeb4577687cc59557fef8972",
      "status": "passed",
      "command": "python3 scripts/build_docs.py --check; git diff --check; Python 文档行尾空白检查",
      "exit_code": 0,
      "summary": "DOCS OK；无空白错误",
      "environment": "macOS; Python 3.9.6; main; 当前会话复核/自查",
      "coverage": "生成一致性与文档格式；不是未来实现的功能验证",
      "report": "docs/evidence/2026-10-18-architecture-plan/recheck.md",
      "report_sha256": "4e85d959d56aa238881a1b0649bce2561a642e7efb3c8a958290f56056176348"
    }
  ],
  "delivery": {
    "local": "accepted",
    "commit": "not_requested",
    "remote": "not_requested",
    "clone": "not_requested",
    "runtime": "not_applicable_docs_only"
  }
}
```
