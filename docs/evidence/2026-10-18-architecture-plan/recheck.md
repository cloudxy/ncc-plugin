# 升级方案复核验证

日期：2026-10-18。环境：macOS、Python 3.9.6。关联任务：[架构方案复核](../../tasks/2026-10-18-architecture-plan.md)。本报告记录当前会话实际完成的文档复核，不是 G1–G5 实现验证，不是新派独立代理的评审。

## 输入、授权与候选

作者要求检查 zcode 的升级方案并完善方案与解决步骤。输入为原 architecture-growth、architecture-audit、拆书升级方案及当前工作树中实际清单、registry、脚本、测试和开发规范。活动仓库与技能根均为 `/Users/xuyun/Documents/ncc-workflow`，main，基线 `0e3faa03f05f05524442c870c0fafda134e0d8b4`，插件 3.2.0。

本轮产品范围仅四份文档：docs/README.md、docs/designs/engineering/architecture-growth.md、docs/designs/engineering/architecture-audit.md、docs/designs/deconstruction/upgrade.md；另更新本任务记录、增加本报告。运行代码、规则与私有目录未修改。原有在途差异未清理、暂存或重新认领；当前精确归属与候选指纹在任务 JSON。

## 实际发现与处理

| 证据输入 | 观察 | 方案处置 |
|---|---|---|
| 五份插件/市场 JSON 的解析结果 | 三个插件清单在顶层持有 name/version，Claude 市场版本在 plugins 的目标项；两个市场顶层 name 都是 ncc-plugin，Codex 市场无 version | 五文件字段矩阵；按插件名匹配，保留宿主格式；增加缺文件/坏格式/重复目标/漂移/路径异常反例 |
| scripts 目录、五个测试文件与路径表达式 | 13 个顶层 .py；测试 2592 行；除了 HERE/sys.path，还有 with_name、HERE.parent、直接模块导入、patch 对象等 | 逐文件迁移表；旧入口兼容；测试发现集合对比、跨 cwd 和恢复验收 |
| core、ncc_prepare、check_plugin、build_docs、test_ncc_state 对 registry 的读取 | 不只 core 一个读取点；ncc_library 间接依赖准备工具 | 先统一纯标准库 loader，再分片；外部原始读取由生成聚合文件兼容 |
| registry 的 41 个键与代码常量 | principle/principles 和 check_words/review_words 职责不同；layout_legacy 参与旧书/书库迁移 | 分片不改键值/schema，不把改名/退役混进等价迁移 |
| book.gate_check、loops.cmd_unit、cli.main/log_op/auto_render | 前两者有业务规则；CLI 派发后还有日志与渲染副作用 | 保留业务归属；只拆 CLI 注册；验收涵盖完整解析契约及只读/写入/失败副作用 |
| 拆书方案接口与 P1 | 三个新增命令 plan/packet/ingest，已有 coverage 扩 --layer；原文本将全部拆书能力误说成未实现 | 区分当前能力与未实施升级；补参考层、机器契约与生成字段表、验证函数和样例归属 |
| 原任务与冻结证据 | 旧记录包含其他任务的文档/代码差异；旧报告只支持旧候选 | 继承任务号，scope 收窄到本轮四份文档；49 个既有路径保留 foreign_changes；旧 validation.md 原字节不动，旧 passed 不沿用 |

优先级复核：清单字段误判、漏掉 registry 读者、等价与改名矛盾、脚本迁移遗漏属于直接实施风险；registry 大小/目录平铺属于维护性判断，没有实测运行故障或冲突频率支持“必然高风险”。不对第三方项目重新作未经核查的断言。

## 已执行检查

| 操作 | 实际结果 | 退出码 |
|---|---|---:|
| 恢复前 `python3 scripts/check_dev_workflow.py check docs/tasks/2026-10-18-architecture-plan.md --repo /Users/xuyun/Documents/ncc-workflow` | 原记录有效，候选 bfd47a04fa4a2fddc8a138eea2d5973ee01bb8461a6f66822ed419a3b3a992bc；这只说明旧记录有效，不说明原方案正确 | 0 |
| Python 标准库解析五份清单、registry，并枚举 scripts 顶层与测试行数 | 五份 JSON 均可解析；四个版本值为 3.2.0；41 键；13 个脚本；5 个测试文件共 2592 行 | 0 |
| Python 提取修订方案的分片归属表，逐行核对数量并与实际 registry 键集合比较 | 7 个分片，41 个键，唯一且完整，无丢失或凭空新增；这是方案映射验证，未创建任何分片 | 0 |
| `python3 scripts/check_plugin.py -v` | PLUGIN OK；文档链接、接线及现有读取预算检查通过 | 0 |
| `python3 scripts/build_docs.py --check` | DOCS OK；未修改生成的运行规则 | 0 |
| `git diff --check` | 无空白错误；另对四份未提交候选文档检查行尾空白 | 0 |
| 将本轮开始前受管文件 SHA-256 与当前工作树对比（Python 标准库） | 仅四份产品文档与本任务记录变化；原有运行文件、规则及旧 validation.md 的字节保持不变。新增文件只有本报告 | 0 |

自查覆盖 R1–R9 与各 G 阶段的对应关系、前置条件、字段/文件落点、失败用例、兼容策略、完成标准、回滚依赖和实施授权边界。G4 的落点已同步到拆书 P1，没有仅在架构文档里留下三行未来待办；本轮仍未创建这些功能文件。

## 限制与后续证据

这是纯文档修订，未运行功能全量测试、CLI 前后行为对照、失败注入或模型回归；这些是方案指定的未来实施验收，不填成已通过。未验证任何宿主的新会话加载。独立评审仍待办，本轮为当前会话代码复核和自查。

候选冻结和最终 `check --delivery` 在任务 JSON 中登记；报告 hash 与候选绑定。未提交、未推送、未发布。后续实施需重新冻结当时基线；不能用本报告作为运行改造已验收的依据。
