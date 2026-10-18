# README 更新验证记录

输入：`README.md`，基线 `0e3faa03f05f05524442c870c0fafda134e0d8b4`，候选指纹 `021bce4ea77aebfa3816caf368e5fa782d99fe936eef534d7eefc054ca382b0a`。执行环境：2026-10-12 至 2026-10-13，macOS，仓库 `/Users/xuyun/Documents/ncc-workflow`，分支 `main`，Python 3。

| 检查 | 观察与实际结果 | 退出码 |
|---|---|---|
| `python3 -m unittest discover -s scripts -p 'test_*.py'` | Ran 148 tests in 278.179s；OK | 0 |
| `python3 scripts/check_plugin.py -v` | 角色读取量检查输出正常，`PLUGIN OK`；覆盖插件链接、引用与一致性 | 0 |
| `python3 scripts/build_docs.py --check` | `DOCS OK`；README 版本行符合生成约定 | 0 |
| `python3 scripts/ncc_eval.py mech` | A01–A06 六个锚定章均 `PASS` | 0 |
| `git diff --check` | 无空白错误 | 0 |
| `python3 scripts/check_dev_workflow.py check docs/dev/tasks/2026-10-12-readme-refresh.md --repo /Users/xuyun/Documents/ncc-workflow` | 冻结后 `RECORD OK`，指纹与 README 内容一致；当时尚未登记证据 | 0 |

自查输入：README 与 `AGENTS.md`、`docs/usage.md`、`docs/dev-workflow.md`、`plugin.json`、五端挂载目录和 `.gitignore` 对照。观察：八个入口、十二个角色、五端接入与 ZCode 独立克隆均有本仓库依据；现行功能仍可从使用指南与架构文档继续查阅。README 的源码与命令示例未包含真实书稿、素材或私人会话。内部相对链接由插件检查覆盖，Git 差异仅含 README 与本次开发记录/证据。没有改动 `registry.json`、`skills/` 或 `agents/`，无需发起规则语义回归派单。

缺项：本会话未取得另一独立会话、作者人工或宿主评审；按开发工作流标记“自查完成，独立评审待办”。五端新会话运行也未因这次文档编辑重新验证。没有执行提交、推送或安装克隆同步。
