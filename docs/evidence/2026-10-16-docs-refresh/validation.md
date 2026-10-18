# 文档更新与归属收敛验证

日期：2026-10-16。环境：macOS，Python 3.9.6，main，基线 `0e3faa0`。候选指纹由关联[任务记录](../../tasks/2026-10-16-docs-refresh.md)持有；本报告不将历史验证改记为当前结果。

## 输入与影响范围

输入为 docs/ 全部现存文档、workflow/ 下三份设计/规范文件、此前两个任务的在途候选（README、docs 重组、脚本/技能路径适配，一并接管）。输出为：归属收敛（memory-evolution-design、preparation-design 迁入 `docs/designs/`，source-vetting 迁入 `docs/engineering/`，引用同步）；重写的文档组织规范与文档导航（含未执行计划清单）；拆书统一方案 P0 完成状态；使用指南补 `/ncc-prepare` 入口行。

没有修改 `workflow/registry.json`、创作判据、角色职责或命令接口；`skills/ncc/references/memory.md` 仅改一处路径字符串。不动 `novels/` 私有内容与既有冻结证据字节。

## 检查与结果

| 检查 | 观察与实际结果 | 退出码 |
|---|---|---|
| `python3 -m unittest discover -s scripts -p 'test_dev_workflow.py'` | 36 项通过；初轮 25.385 秒、终轮 46.663 秒均 OK；任务/证据路径、指纹与边界用例不受本次目录调整影响 | 0 |
| `python3 scripts/check_plugin.py -v` | `PLUGIN OK`；初轮发现 preparation-design 迁移后 3 条相对链接层级失效（`../skills/` 少两级），修复后通过；角色读取量预算正常输出 | 0 |
| `python3 scripts/build_docs.py --check` | `DOCS OK`；生成文档与 README 版本行未漂移 | 0 |
| 迁移与引用核对 | memory-evolution-design、source-vetting 与 HEAD 逐字节一致（纯移动）；preparation-design 仅 179/238/240 三行链接深度修复；architecture.md 两处、memory.md 一处引用已指向新路径；全仓 grep 无残留旧路径（冻结证据与任务 JSON 中的历史路径除外） | 0 |
| `git diff --check` | 无空白错误 | 0 |

使用指南核对：八个命令入口与 `workflow/registry.json` 的 commands 键一致；此前缺 `/ncc-prepare` 行，已补；导出、仪表盘、migrate、技法库、放行清单等条目与 architecture.md 及脚本能力相符；未把拆书 P1–P6 未实施能力写成可用。

## 测试范围与限制

按作者 2026-10-16 确定的影响范围原则，本次为文档内容与搬迁调整，只运行上表检查，不跑无关全量自测与模型回归。当前会话完成自查，独立评审待办，不宣称独立审查通过。五端新会话运行验证未执行；未提交、未推送、未更新安装克隆。后续拆书实施仍从统一方案 P1 开始，另开任务。
