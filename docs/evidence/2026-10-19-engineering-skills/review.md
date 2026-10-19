# 四工程专业技能 D5 独立评审

结论：**通过本轮技能与接线的 D5 评审；无 major、无 minor。** 四角色已各有独立专业技能、具体执行方法和工件模板；派单实际携带其内容，独立合成任务的输出也体现了专业判断。本结论不表示后续引用面板等产品功能、真实数据库或五宿主运行已通过。

## 评审绑定与边界

- 任务：`docs/tasks/2026-10-19-engineering-skills.md`；工作树 `/private/tmp/ncc-role-skills-28g8xt1l`，main，基线 `ac0fc44990a4f8c8e8d22a3a0a4a0540c4446393`。
- 候选：`91397686d3e5a34a93ad00bc58389bc71630a1929169ba78db40661abf9af0c1`。独立核对 scope 与候选均为 53 项，每项文件内容/执行位或软链目标均匹配；重算规范化候选载荷指纹一致。
- 评审者：独立子代理 `/root/skills_independent_review`；按 ncc-dev 的 D5 规范，读取实现、技能、测试、冻结日志及四份行为工件，并对隐藏 `expectations.md` 作语义核对。未参与实现，未再派代理，仅写本报告。
- 继承前轮在途改动；未将全部 Git 脏差异当成本轮新增交付。未读取真实 `.env`、私有小说或凭据，未联网、连接数据库、实施或发布；未独立重跑全面测试。

## 问题清单

| 严重度 | 问题、证据与修法 |
|---|---|
| major | 无。 |
| minor | 无。 |

后文“未验证项”限定证据适用范围，不是已经观察到的产品缺陷。

## 实现与内容核查

| 核查项 | 观察与判断 |
|---|---|
| 产品经理专业能力 | `skills/ncc-product-manager/references/sop.md`、`discovery.md` 和 `templates/product-brief.md` 给出任务证据分级、真实备选、损害/频次/成本排序、纵向切片、验收追踪及反馈闭环；明确无数据时不编造 RICE、收益或用户研究。方法能直接用于本项目需求冲突，不是只列必填字段。 |
| 产品设计专业能力 | `skills/ncc-product-designer/references/sop.md`、`interaction.md` 和 `templates/interaction-spec.md` 从任务/信息架构到主路径、版本/内容保留状态表、并发及取消恢复、组件/键盘/焦点和可用性脚本；区分保存、生成、采用、索引的事实，并说明服务校验与界面提示各自边界。 |
| 架构专业能力 | `skills/ncc-project-architect/references/sop.md`、`evolution.md` 和决策模板要求从实际入口追责任、依赖和代表读写链；给结构化迁移语义、文件并发替换、正反兼容、投影与权威数据及分批回退的具体推演。C4/ADR按真实决策裁剪，不以新层或微服务数量证明架构。 |
| DBA 专业能力 | `skills/ncc-dba/references/sop.md`、`data-design.md`、`operations.md` 和数据变更模板覆盖约束归属、两会话时序、CAS 与数据库重试区别、持久幂等、跨页快照、范围/隐藏权限、计划解释、追加迁移及恢复核对。明确 CHECK 跨行规则、cost/实际时间、EXPLAIN ANALYZE 副作用和 pg_dump 覆盖边界等易错细节；有可执行验收，而非“加事务/索引”。 |
| 可追溯专业来源 | 四个 `references/sources.md` 分别指向 GOV.UK 原始需求/优先级指南，W3C WCAG 2.2/APG 与 GOV.UK 错误摘要，C4/ADR 原始站点，PostgreSQL 17 官方手册；列用途、日期/版本和 NCC 转化边界。`ACKNOWLEDGMENTS.md:191` 集中归因，声明自写 SOP/模板及无上游运行依赖。未发现以框架名替代项目判断或复制上游正文的内容。 |
| agent 与资料归属 | 四个 `agents/<role>.md` 保留职责、边界和由 registry 生成的对应 SKILL 指向，执行方法留在 skills；共用返回协议及案例在 `skills/ncc-dev/references/`。`docs/engineering/documentation.md:74` 明确上述分工，设计文档保留项目设计依据，没有再持有四套 SOP/模板副本。 |
| 注册与真实装包 | `workflow/registry/roles.json` 的 development 为四角色分别映射独立 skill/resources。`scripts/dev/development.py:41` 的单一 `role_reads` 被 packet 与 `check_plugin.py:299` 的预算检查复用；`make_packet:84` 实际内嵌角色、共用协议/经验、专业 SKILL、SOP、专题方法、模板和来源索引，并绑定字节摘要。没有角色文件缺技能时的静默回退。 |
| 反例与来源新鲜度 | `scripts/tests/test_development.py:93–163` 覆盖正确专业资源装入、缺技能/资源、上跳路径、私有输入、不触发角色、超预算及 SOP 改动后报告失效；`scripts/tests/test_dev_workflow.py:389–405` 覆盖无作者新命令的发现、缺挂载/资源和越界资源拒绝。实现配合现有 `safe_path` 对私有/忽略/仓外解析目标作拒绝，`check_plugin.py:171` 检查实际资源与挂载。 |
| 静态发现与创作兼容 | 独立核对 `.agents/skills`、`.claude/skills` 的八条新增相对软链均指向正确技能。与基线比较，原 registry 的 `roles`、`commands`、`load_budget` 完全相同，仍为十二创作角色；没有为四专业技能增加日常创作命令或审批。工程域及 ncc-dev 专业入口边界清楚。 |
| 既定约束 | 四套技能/协议反复以当前授权和既有实现为准，保持配置装配、既定 PostgreSQL 参数、唯一正式/同连接-test、只读 MCP、自动定稿资格与原评分/硬闸门/版本约束。本轮 scope 不包含配置或数据库产品实现；未发现另建库、重选参数或变更创作标准的接线。 |

经验迁移已独立追溯：`experience-move.json` 的 before 哈希 `68ad2d28983b3692ce2352d663a70f2bd692d8b63cf6afb80fdfa6630e8a8ded` 与冻结的 `docs/evidence/2026-10-19-engineering-experience/behavior/alpha-dba-packet.json` 内旧来源内容一致；新文件哈希为记录中的 `a78245630f860112040b96b76058c6587d4814a1bd5fd1c8f68dd0fd287a4f4c`。逐行差异仅第20、37行的相对链接重定向，经验方法完整保留。旧 `docs/engineering/experience.md` 已不存在，现行 README/AGENTS/docs 导航、设计/规范/指南、skills/agents/workflow/scripts 中未搜索到旧路径；历史任务 JSON 与冻结报告里的旧路径不作为现行导航，未要求改写其历史字节。

## 四个独立行为工件

四个 fresh 角色均只获本职责 packet，报告声明未读隐藏预期或他人报告。独立重算四 packet 的 `input_sha256`，并逐来源核对当前内容哈希，均一致且无陈旧来源。序列化包的非空白字符数依次为产品经理 12686、设计师 12573、架构师 15795、DBA 17658，均低于 20000；专业资源本身预算见 `plugin.log`，分别 9214、9119、11735、13522。

| 工件 | 对照隐藏预期的实际观察 |
|---|---|
| `behavior/product-manager-report.json` | `author_task` 分清作者约束、合成20次走查、服务陈述与假设；推翻45%提升断言。`value/scope/priority` 比较现状、侧栏与管理全套，给 R1–R5 完整纵向切片、取舍、粗估依赖、后续触发与归属；`acceptance` 逐项给输入、动作、观察、失败恢复及真实研究计划。不是复述经验编号或只找错。 |
| `behavior/product-designer-report.json` | `journey/defaults` 给第18章原位返回、260章全范围检索/分页和当前项保留；`states` 给正文缓冲、AI任务、候选与索引的正交状态及动作/保留/焦点。明确保存 r12 后继续编辑 r13、v10 候选与 v11 人工稿并存、晚到响应、超时和停止等待的差别；A1–A8 可复现验收覆盖键盘/焦点/恢复，未伪称浏览器或可用性通过。 |
| `behavior/project-architect-report.json` | `ownership/dependencies` 明确清单是合成输入，给具体责任表、依赖限制及 A/B/C 的 ADR 取舍。`read_path/write_path` 给受控 scope 查询、候选提交和双版本原子采用、持久幂等及投影失败语义；没有假定 revise 已支持候选创建或事务组合。`compatibility/rollback` 有合法旧调用与漏字段反例、宿主注册例外和 B0–B4 前置/停止/保留工件。 |
| `behavior/dba-report.json` | `integrity` 用 UNIQUE/联合 FK 等替代跨行 CHECK，给 T1/T2 锁行+期望版本时间线和持久载荷摘要/结果；不把语义冲突当盲重试。`access` 同时约束工具、只读、scope/隐藏范围。`operations` 正确解释估计计划、索引候选代价及 ANALYZE 副作用，给固定修订清单/快照导出；恢复必须复用唯一-test/现有守卫并验证应用结果，未把备份可见记成恢复通过。 |

四份报告均为 `changes_required`，对应原合成提案故意保留的 major；独立调用现有 `validate_report` 返回 `failed`，与该返回语义一致。它们给出修正工件但没有假称原提案已改好，这符合预期。报告中的产品实现、数据库、浏览器验收 `pending` 是如实保留的后续运行状态，**不构成本轮“技能未执行”或行为验证失败**。

本次已语义复核的报告字节：

| role | 报告 SHA-256 |
|---|---|
| product-manager | `6b2ffdae57c5ca6c3df4b0d6637166ec8b34443cc5a5cb4fdcd9973c61b49b6c` |
| product-designer | `1e9c5964a285916c92a513d6768cfebc063bfbb109adf5382a9ea60e6d42e5fa` |
| project-architect | `cc100a559e9ceb2e09b2b706de8538e5e9c9650b82d787eaa0bc842737afa266` |
| dba | `a7963f220aadb8b07eed7b6ca6c7f4bce26a9bbc973488a14e9cb0ba436f7ac4` |

## 确定性证据与未验证项

已读取本轮 `unit.log`（226 tests，OK，exit_code=0）、`plugin.log`（PLUGIN OK）、`registry.log`（REGISTRY OK）、`docs.log`（DOCS OK）及 `skill-validation.log`（四新技能+ncc-dev 均 valid）。`unit-fixture-failure.log` 是修正测试夹具前的冻结失败证据，最终全量日志已通过，不作为当前失败。独立检查仅做候选/来源/报告哈希、挂载、原域兼容、迁移差异与现有报告验证函数核对，没有重复运行全面测试。

- 本候选四个新专业样例均含故意缺陷；尚未对同候选追加无缺陷提案的 fresh 接受样例，也未统计重复稳定性或前后能力提升。四份实质替代工件足以支持本轮 SOP 可执行结论，不支持长期能力认证；前轮 clean/beta 冻结证据不冒充本候选行为通过。
- 原始外部页面的可达性、核对日期与最新内容未由本评审重新联网核实；本次确认的是来源可追溯、版本/用途说明及技能内方法质量。
- 真实源码中的引用面板/候选采用实现、PG身份/连通/读写/并发/性能/备份恢复、浏览器/辅助技术/真实作者研究，均不在本轮技能建设实测范围。
- 五宿主新会话发现/加载、发布、远端与消费克隆同步未验；静态挂载和打包一致性不替代这些证据。主任务另行生成/登记的工程设计报告仍由其来源新鲜度与交付门禁判断，本报告不将尚未登记的状态提前宣称通过。

候选产品字节或以上行为报告字节变化后，应按影响重新验证并更新独立评审；本报告未授权整合以外的产品开发、数据库操作或发布。
