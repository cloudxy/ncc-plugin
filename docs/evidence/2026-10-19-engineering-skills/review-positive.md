# 四工程专业技能正向样例补充独立评审

结论：**补充核对通过，无 major、无 minor。** 四份修正后合成设计都有具体专业工件支持 `ready`；结论准确限定为设计可推进，未把产品运行 `pending` 当成设计缺陷，也未据此宣称实现或运行通过。结合原负向样例，本候选没有在这四组样例中表现为一律退回。

## 绑定与执行边界

- 任务：`docs/tasks/2026-10-19-engineering-skills.md`；工作树 `/private/tmp/ncc-role-skills-28g8xt1l`，main，基线 `ac0fc44990a4f8c8e8d22a3a0a4a0540c4446393`。
- 候选：`91397686d3e5a34a93ad00bc58389bc71630a1929169ba78db40661abf9af0c1`。再次逐项核对 53 项文件/软链及执行位，未变化；重算候选载荷指纹一致。
- 独立评审者：`/root/skills_independent_review`。本次只读正向输入、派单和报告，复用已读专业技能/共用协议作语义核对；只写本文件，没有实施、联网、访问数据库/真实私有资料或再派代理。
- 原 `review.md` 保持原字节，SHA-256 仍为 `78cc1ca79e23f4b3fd476b51febf154f19ebf8f746894d4fe9ff5e1576b94421`。该报告中“未追加本候选正向样例”的限制由本补充证据覆盖，其他未验证项继续有效；没有覆盖或重写冻结历史。

## 包与报告核验

四包来自 `behavior/positive-<role>-packet.json`；输入为同目录 `positive-<role>-input.md`，均是原故意缺陷提案的**合成修正设计**，不是真实产品实现。包只包含对应角色、专业 SKILL/SOP/方法/模板/来源、共用协议/经验及指定设计输入，架构师/DBA另含代码归属规范；没有装入隐藏 expectations 或其他角色报告。各角色以 fresh 子代理身份执行，身份分别为 `/root/positive_product`、`/root/positive_designer`、`/root/positive_architect`、`/root/positive_dba`。

独立重算 packet 的 `input_sha256`，核对所有内嵌 content 哈希、当前来源文件哈希，以及 ncc-dev/workflow 额外 bindings，全部一致。四个序列化包非空白字符数依次为产品经理 12833、设计师 12867、架构师 16092、DBA 18102，均低于 20000。

| role | 报告绑定的 input_sha256 | 本次已审报告 SHA-256 |
|---|---|---|
| product-manager | `4c2b6956add3b82d17c37869d90afeb757d488dbeb5aca15ba35b3ee54c6c4d6` | `314c9a1f13b647e4864f601832d170362336eeddf67bba27310a1502f17dc3fc` |
| product-designer | `90cee552609aa392eeb887960bb39cb37d9a9ad95f7cdcd3fe5274cb906ab72f` | `5ae2ebad8e9ae8f79ffca48b7bcfacd89a15f8163515d45b494c9e40fa1c3306` |
| project-architect | `007b4fd01d7f90a81907fd882dd13d785fc0c3498b35807dbfc758983fdc0d10` | `cce095f7d2ad9ad434c1fcb74c8c66eb812d42faa505c49c53566c814eaefaae` |
| dba | `a1b7be185b934785b69624d2c108a49aad74f2b1d9cc748e36b75f65ef76f936` | `709fc509e955d9dbba9278445503068e97989707aab07ced5b8ffa0555ada688` |

独立调用现有 `validate_report`：四份均返回 `passed`，与 `decision=ready`、空 findings、完整职责交付一致。该检查只说明报告契约通过；下面的判断基于工件实际内容，不用字段齐全代替专业判断。

## 对设计 ready 的语义复核

| 报告与定位 | 具体工件及接受依据 | 运行边界 |
|---|---|---|
| `behavior/positive-product-manager-report.json` 的 `author_task/value/scope/priority/acceptance` | 分清作者已确认约束、设计承诺、合成20次走查与真实收益假设；没有恢复45%提升断言。比较独立页、侧栏、管理全套的覆盖/成本/依赖，选择 R1–R4 完整侧栏切片并接受管理功能后置，明确产品经理维护后续需求。逐项验收给两书两章、501条资料、超过200项目标、旧范围响应、状态解释、回执重放及原位恢复。先核服务接口与完整估算，不把5人日粗估当交期。已有任务和成功条件足以推进需求设计，接口/实现尚待核验不推翻该范围的判断。 | 5项 verification 全部 pending；明确未读源码、未运行产品、无用户研究。设计、代码、调用、行为、实际加载分别说明，没有把方案承诺当现成能力。 |
| `behavior/positive-product-designer-report.json` 的 `journey/states/defaults/recovery/acceptance` | 给当前章到引用、纠错回执、关闭原位继续的路径；260章完整范围和稳定选中项已取代前100截断。状态表区分正文/AI/采用/索引，具体解释 r12保存后r13仍未保存、v10候选不覆盖v11、采用版本冲突、索引失败只重试投影、停止等待与真实取消的差别。错误恢复保留输入/正文，字段错误、网络焦点、键盘路径和关闭回焦均有操作标准；刷新未确认键入的持久恢复边界明确。原负向缺陷已有可实现修正机制，规格可推进。 | 8项 verification 全部 pending；没有把状态推演说成持久化验证，没有浏览器/辅助技术或整站WCAG达标宣称。有效托管与必要创作决定均沿既有契约。 |
| `behavior/positive-project-architect-report.json` 的 `ownership/dependencies/read_path/write_path/compatibility/rollback` | ADR说明输入是合成清单，比较 A/B/C，按容量和单一规则来源选现有进程方案，并接受发布耦合。责任表、允许/禁止依赖、每页鉴权读链与候选/采用分离写链具体；采用在同一事务写修订/CAS/候选状态/审计/事件/请求结果，持久幂等含语义摘要。合法旧输入与新缺字段/降级反例成对，保留宿主文件约定位置。B0–B4列实际事务可组合性前置、实施和回退的停止/保留边界，没有把无法组合的半采用留到上线。设计已处理原提案的复制规则、直库和fail-open风险，接受有依据。 | 7项 verification 全部 pending；真实调用、CAS/事务实现、打包和宿主均未验。报告明确目录职责及组件图是设计目标，未宣称当前源码已实现；未知项是实施前核验条件。 |
| `behavior/positive-dba-report.json` 的 `database_scope/integrity/access/migration/operations/verification/rollback` | 不变量用联合唯一/引用和行内约束区分跨scope与行内规则。事务工件给 T1 v5→人工v6 后拒绝原v5，数据库完整重试不换基线；持久请求键/载荷摘要/提交前后故障与投影去重均有明确结果。权限同时覆盖白名单、最小SELECT、只读和全读链scope/隐藏过滤。Q1给稳定keyset与索引验证代价，导出固定不可变修订清单；恢复只在唯一-test经既有守卫/必要授权并核应用结果，无备份存在即通过或随机建库。迁移追加、锁预算、回填、contract另评以及保留历史的回退边界清楚。物理实现尚未提供不妨碍该参考设计可推进。 | 9项 verification 全部 pending；未执行SQL、连接、迁移、计划测量或恢复，PG17只是参考版本；没有宣称权限已生效、性能收益或RPO/RTO已达标。 |

四份 `experience_application` 均说明了旧案例与本次设计的差异及验收落点，没有把历史合成风险说成本次已发生故障，也没有仅凭案例编号判退。原自动定稿授权、配置/双库、只读MCP和十二创作角色的边界未因接受设计而扩大。

## 成对结果、限制与问题清单

每个技能本次只有一份故意缺陷输入和一份相应修正输入。四个负向报告 `changes_required` 与四个正向报告设计 `ready` 均有工件内容支持；没有把“真实运行未验”作为统一退回理由，也没有为了得到正向结果把运行 pending 改写为 passed。

本次补充不主张随机/盲测统计检出率、跨任务泛化、重复稳定性、长期专业熟练度或相对旧提示的量化提升；修正输入来源于同轮已知问题，样例并非独立分布。本结论限四组具体合成设计对照。主任务另行登记的 current_session 自查报告不算本次独立行为报告；本次没有以其数量或状态替代这四个 fresh 输出，也不改变原冻结报告。

| 严重度 | 问题、证据与修法 |
|---|---|
| major | 无。 |
| minor | 无。 |

真实产品实现、数据库连通/权限/并发/恢复/性能、UI与辅助技术、真实作者研究、五宿主新会话及发布仍未验证；本补充未重跑全面测试，未重查外部网页。候选或以上输入/报告字节变化后，按实际影响重新核对相应证据。
