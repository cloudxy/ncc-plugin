# zcode 注册切换验证

日期：2026-10-17。环境：macOS，Python 3.9.6，main，基线 `0e3faa0`。候选指纹由关联[任务记录](../../tasks/2026-10-17-zcode-registration.md)持有；zcode 配置文件在仓库外，不入指纹，其改动与备份路径记录在任务记录正文。

## 输入与影响范围

输入为 `~/.zcode/cli/config.json`（plugins.dirs / enabledPlugins）、本仓库 `.zcode-plugin/plugin.json`、旧安装克隆 `~/.zcode/local-plugins/ncc-workflow` 的 git 状态、仓内三处 zcode 接入表述。输出为：注册源由安装克隆切换为本仓库目录；AGENTS.md、README.md、docs/README.md 表述同步；docs-refresh 任务记录补记陈旧候选。不改插件代码、创作规则与命令接口。

## 检查与结果

| 检查 | 观察与实际结果 | 退出码 |
|---|---|---|
| 配置断言（wiring） | `plugins.dirs` 含 `/Users/xuyun/Documents/ncc-workflow` 且不再含旧克隆路径；JSON 解析正常；`ncc-workflow@inline` 保持 enabled；仓库 `.zcode-plugin/plugin.json` 名称 `ncc-workflow`、`skills/ncc/SKILL.md` 存在；改前备份 `~/.zcode/cli/config.json.bak-zcode-reg-20261017` | 0 |
| 旧克隆状态核对 | 工作树干净；HEAD `0e3faa0` 与 workspace 基线、origin/main 一致，`HEAD..origin/main` 为 0——退出加载链无在途改动丢失 | 0 |
| `python3 scripts/check_plugin.py -v` | `PLUGIN OK`；接入表与文档改后链接、引用、读取预算正常 | 0 |
| `python3 scripts/build_docs.py --check` | `DOCS OK`；生成内容未漂移 | 0 |
| `git diff --check` | 无空白错误 | 0 |

直注册先例核对：`plugins.dirs` 中 sdlc-workflow、vsc-workflow 已按同一方式注册各自 Documents 工作目录并正常加载（本会话技能列表可证），ncc-workflow 切换为同构配置。

## 测试范围与限制

按影响范围原则：宿主配置一处替换＋仓内文案，只做上述接线与文档检查，不跑全量自测与模型回归。**运行加载验证需要新 zcode 会话**：当前会话仍持旧注册，本会话内无法自证；已在 docs/README.md 未执行计划表登记。本机找不到 `zcode` 命令行二进制，无法用 CLI 冒烟替代。未提交、未推送；旧克隆保留在磁盘未删除。
