# README 更新

## 当前范围与计划

承接作者最新要求：重新编写根 README，只介绍 ncc-workflow 本项目。plugin_root/repo_root 均为 /Users/xuyun/Documents/ncc-workflow，main，版本3.2.0；本轮开始时工作树干净。沿用本任务记录，不另建同目标任务。

1. 对照插件清单、技能、CLI 和目录，重写项目用途、八个入口、使用示例、创作与拆书流程、数据边界和开发导航。
2. 删除个人机器配置状态、协作与发布过程、第三方项目及来源讨论；保留实际宿主接入，因为它属于本项目用法。
3. 核对项目事实、内部链接、版本生成行和文本差异；本轮不改功能或规则，不运行功能/模型/宿主测试。

验收以文案聚焦本项目、功能与当前实现一致、路径与生成格式有效为准。2026-10-12/13 的 README 测试记录仅是旧候选历史，本轮不继承其 passed；历史内容由 Git 保留，旧冻结日志不改写。回滚只还原本轮 README 与记录的增量。

## 状态

README 已重写，只介绍本项目；本轮内容、6个相对链接、版本生成格式和空白核对通过。实际结果与范围见[验证记录](../evidence/2026-10-18-readme-project-only/validation.md)。当前会话自查完成，独立评审未执行；无功能变更，不运行功能测试。未请求本轮提交、推送或安装同步。

```ncc-dev-json
{
  "schema": 1,
  "id": "2026-10-12-readme-refresh",
  "goal": "重写根 README，只介绍 ncc-workflow 本身的功能、用法、流程、结构和开发方式",
  "route": "bounded",
  "risk_tags": [],
  "repo_root": "/Users/xuyun/Documents/ncc-workflow",
  "plugin_root": "/Users/xuyun/Documents/ncc-workflow",
  "branch": "main",
  "base_commit": "de8d1abee1a71d169451c994a8de0c9f64242289",
  "stage": "D5",
  "next": "本轮 README 文案与导航已完成本地交付；独立评审未执行，后续发布按作者请求处理。",
  "blocked": "",
  "decisions": [
    {
      "source": "作者本轮要求：重新编写 README，只介绍本项目相关内容",
      "scope": "仅改写根 README 及本任务记录和证据；去除个人机器状态、协作发布过程和第三方来源讨论，保留本项目能力与必要用法。"
    },
    {
      "source": "现行文档验证规范与作者此前测试安排",
      "scope": "本轮不改变规则、代码或数据，只核对文案事实、链接、版本生成格式与空白；不运行功能测试，不继承旧 README 或拆书候选的通过证据。"
    }
  ],
  "spec": "",
  "plan": "",
  "scope": [
    "README.md"
  ],
  "foreign_changes": {},
  "evidence_paths": [
    "docs/evidence/2026-10-18-readme-project-only/validation.md"
  ],
  "candidate": {
    "base_commit": "de8d1abee1a71d169451c994a8de0c9f64242289",
    "files": [
      {
        "path": "README.md",
        "type": "file",
        "sha256": "4e5f93a86745dfcc2e9ae6ba25c0a31598cfd79ccef02e1bb6e969c080f53fd4",
        "executable": false
      }
    ],
    "fingerprint": "1022a8e7be421c8e4d72806563bcc390119d1064f88b61a9760bbe21cc35fe72"
  },
  "required": [
    "docs"
  ],
  "evidence": [
    {
      "id": "readme-project-docs",
      "kind": "docs",
      "candidate": "1022a8e7be421c8e4d72806563bcc390119d1064f88b61a9760bbe21cc35fe72",
      "status": "passed",
      "command": "README 与仓内源对照、6个相对链接/版本/内容核对；python3 scripts/dev/build_docs.py --check；git diff --check",
      "exit_code": 0,
      "summary": "项目内容、八入口/十二角色、分层拆书、链接与生成格式核对通过；仅文档检查",
      "environment": "macOS; Python 3.9.6; main; 当前仓库",
      "coverage": "仅 README 文案、导航及版本格式；未执行功能、模型、宿主或独立评审",
      "report": "docs/evidence/2026-10-18-readme-project-only/validation.md",
      "report_sha256": "b6800a13823d0e4dc8007206da6f627b85f8e04b51cf23ff3271c6dcfa97b2c7"
    }
  ],
  "delivery": {
    "local": "accepted",
    "commit": "not_requested",
    "remote": "not_requested",
    "clone": "not_requested",
    "runtime": "not_applicable_docs_only",
    "review": "self_review_complete; independent_unverified"
  }
}
```
