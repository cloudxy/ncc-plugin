# README 更新

## 范围与计划

作者要求更新项目 README。当前版本重点是 ZCode 与历次机制，五端项目级接入和新读者的使用路径不够清楚。本任务走 bounded 路径，只更新 README 的现行说明，不改流程规则、命令接口或创作数据。

1. 对照 AGENTS.md、插件清单、使用指南和实际目录，重写项目定位、五端接入、常用入口、流程与数据边界。
2. 核对内部链接、生成文档一致性与 Git 差异，再对最终候选运行全量自测、一致性检查和机械回归。
3. 复核文案是否夸大宿主运行状态、误纳入私有内容或触及现行规则；本地交付 README 与证据。

验收标准：新读者可从首页找到接入方式和下一步入口；版本行保持生成脚本格式；现行能力和私有数据边界准确；全部要求的检查通过。文档可按本任务路径回退。当前请求授权本地编辑与验证，未包含提交、推送或更新安装克隆。

## 状态

2026-10-16 文档整理补充：本记录与原验证报告已迁移；README 的必要导航链接随后更新，旧候选及其 passed 证据仅对应改链前版本。恢复本任务必须重新冻结并验证 README；不得沿用旧通过结论验收新内容。原文案完整保留。

基线工作区干净。README 已改写并冻结候选指纹。全量 148 项、自查、文档生成、机械六章和空白检查均通过，结果见[验证记录](../evidence/2026-10-13-readme-refresh/validation.md)。当前会话完成自查，独立评审待办，因此本地验收仍为 pending。旧开发任务 `2026-10-12-ncc-dev` 已完成发布，与本任务无交叉改动。

```ncc-dev-json
{
  "schema": 1,
  "id": "2026-10-12-readme-refresh",
  "goal": "更新项目 README，使五端接入、常用入口、流程和数据边界清楚且符合现状",
  "route": "bounded",
  "risk_tags": [],
  "repo_root": "/Users/xuyun/Documents/ncc-workflow",
  "plugin_root": "/Users/xuyun/Documents/ncc-workflow",
  "branch": "main",
  "base_commit": "0e3faa03f05f05524442c870c0fafda134e0d8b4",
  "stage": "D5",
  "next": "独立评审 README 文案；通过后将本地候选标为 accepted",
  "blocked": "",
  "decisions": [
    {
      "source": "作者当前请求：更新项目的说明文档 README",
      "scope": "更新 README 并本地验证；未请求发布"
    }
  ],
  "spec": "",
  "plan": "",
  "scope": [
    "README.md"
  ],
  "foreign_changes": {},
  "evidence_paths": ["docs/evidence/2026-10-13-readme-refresh/validation.md"],
  "candidate": {
    "base_commit": "0e3faa03f05f05524442c870c0fafda134e0d8b4",
    "files": [
      {
        "path": "README.md",
        "type": "file",
        "sha256": "b8d9e4f1fa0ec696e43f19b60e9f9aa8a5b93cc9ff5f8c584536eed90f6589ec",
        "executable": false
      }
    ],
    "fingerprint": "021bce4ea77aebfa3816caf368e5fa782d99fe936eef534d7eefc054ca382b0a"
  },
  "required": [
    "unit",
    "plugin",
    "docs",
    "mech",
    "review"
  ],
  "evidence": [
    {"id": "unit", "kind": "unit", "candidate": "021bce4ea77aebfa3816caf368e5fa782d99fe936eef534d7eefc054ca382b0a", "status": "passed", "command": "python3 -m unittest discover -s scripts -p 'test_*.py'", "exit_code": 0, "summary": "148 tests OK", "environment": "macOS, Python 3, main", "coverage": "全量脚本自测", "report": "docs/evidence/2026-10-13-readme-refresh/validation.md", "report_sha256": "271ea73b8f0b3fd0b9640dc9b62cb08a9350f21f1f9c4f399ba0826f333e9d5e"},
    {"id": "plugin", "kind": "plugin", "candidate": "021bce4ea77aebfa3816caf368e5fa782d99fe936eef534d7eefc054ca382b0a", "status": "passed", "command": "python3 scripts/check_plugin.py -v", "exit_code": 0, "summary": "PLUGIN OK", "environment": "macOS, Python 3, main", "coverage": "插件链接、引用与一致性", "report": "docs/evidence/2026-10-13-readme-refresh/validation.md", "report_sha256": "271ea73b8f0b3fd0b9640dc9b62cb08a9350f21f1f9c4f399ba0826f333e9d5e"},
    {"id": "docs", "kind": "docs", "candidate": "021bce4ea77aebfa3816caf368e5fa782d99fe936eef534d7eefc054ca382b0a", "status": "passed", "command": "python3 scripts/build_docs.py --check", "exit_code": 0, "summary": "DOCS OK", "environment": "macOS, Python 3, main", "coverage": "生成文档与 README 版本行", "report": "docs/evidence/2026-10-13-readme-refresh/validation.md", "report_sha256": "271ea73b8f0b3fd0b9640dc9b62cb08a9350f21f1f9c4f399ba0826f333e9d5e"},
    {"id": "mech", "kind": "mech", "candidate": "021bce4ea77aebfa3816caf368e5fa782d99fe936eef534d7eefc054ca382b0a", "status": "passed", "command": "python3 scripts/ncc_eval.py mech", "exit_code": 0, "summary": "A01–A06 PASS", "environment": "macOS, Python 3, main", "coverage": "机械锚定章", "report": "docs/evidence/2026-10-13-readme-refresh/validation.md", "report_sha256": "271ea73b8f0b3fd0b9640dc9b62cb08a9350f21f1f9c4f399ba0826f333e9d5e"},
    {"id": "review", "kind": "review", "candidate": "021bce4ea77aebfa3816caf368e5fa782d99fe936eef534d7eefc054ca382b0a", "status": "pending", "command": "README 与 AGENTS.md、usage.md、插件清单和挂载目录对照自查", "exit_code": null, "summary": "自查完成；独立评审待办", "environment": "当前 Codex 会话", "coverage": "文案准确性、私有内容、差异范围", "report": "docs/evidence/2026-10-13-readme-refresh/validation.md", "report_sha256": "271ea73b8f0b3fd0b9640dc9b62cb08a9350f21f1f9c4f399ba0826f333e9d5e"}
  ],
  "delivery": {
    "local": "pending",
    "commit": "not_requested",
    "remote": "not_requested",
    "clone": "not_requested",
    "runtime": "unverified"
  }
}
```
