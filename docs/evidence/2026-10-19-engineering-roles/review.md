# 工程角色接线 D5 独立评审

结论：接受当前工程角色接线的本地候选。发现的一个 major 和一个 minor 均已修复并独立复核，无未解决的阻断项。本结论不替代完整 D4 证据或五宿主新会话验收。

## 身份与输入

- 评审者：`/root/engineering_review`，受协调者 `/root` 委派的独立子会话；未参与产品实现，未派生代理，只写本报告。产品修复由协调者完成后交回复核。
- 日期：2026-10-19。
- 活动隔离根：`/private/tmp/ncc-engineering-roles-bdm6gxob`。
- 基线：`ac0fc44990a4f8c8e8d22a3a0a4a0540c4446393`。
- 最终候选：`d9851e25dfed8e13bebdd40be08d64bfbee824f4cf5fdc150444e105803d6807`。
- 范围：任务 `docs/tasks/2026-10-19-engineering-roles.md` 中最终 36 个精确产品路径。评审覆盖四工程角色、独立 development 域、生成器、计划/派单/报告登记及新鲜度校验、开发入口与流程、三个项目级角色挂载及原创作域隔离。新增测试路径 `scripts/tests/test_dev_workflow.py` 已纳入最终范围。
- 首轮输入指纹为 `5d43ed3857ce47de9b27fce52dcc4ae4e278194c0e425cc0f0a2f2d300878daa`；本结论只绑定上列最终候选。已用只读 snapshot 重新计算，结果与任务记录相同，计 36 项。

前轮配置/Dynaconf/data-access 的 foreign 变更保留原归属；未将其功能实现扩大为本次审查对象。重叠公共文档只用于核对本次角色边界和已提供的公开方案。未读取真实 `.env`、小说目录或用户凭据，未访问数据库、发布或同步外部克隆。

## 发现及闭环

### R1 — major，缺契约可绕过全部工程报告：已关闭

定位：`scripts/dev/development.py` 的 `validate_engineering`，最终修复位于 `legacy_task`（第 132 行起）和 `validate_engineering`（第 166 行起）。

初版仅因任务没有 `engineering_contract` 就立即成功。独立合成 Git 复现中，任务在基线尚不存在，仅有普通 unit 证据和 `local=accepted`，原 `check_dev_workflow check --delivery` 仍退出 0。因此新任务漏声明或删除两工程字段即可跳过缺报告/失败报告约束。

修复采用实际任务路径的已提交历史证明：必须存在契约引入前、registry 尚无 development、且任务定义相同的无契约版本；任何历史版本曾采用 engineering 或 engineering_contract 都不再允许退回 legacy。检查器传入实际 `task_rel`，不以任务 id 猜路径。曾尝试只在任务自己的 base_commit 查存在性，这会拒绝正常的“先冻结 base、再创建并提交任务”历史，已在复核中纠正。

独立复核结果：

- 同一新任务删掉两工程字段后，完整 `check --delivery` 退出 1。
- 隔离库先提交真正旧任务，再引入 development 并对它提交工程契约，最后删掉两字段：现返回缺少工程职责计划错误；不会回退到更老的无契约版本。
- 当前 HEAD 中九份真实无契约历史任务均保持 legacy 兼容，其中八份在自身起始 base 中尚不存在。
- 新增/变更范围、契约引入后才提交的新任务和显式角色交付缺 plan 的反例进入局部测试。

### R2 — minor，普通检查隐藏工程待办状态：已关闭

定位：`scripts/dev/check_dev_workflow.py` 的 `evidence_errors`（第 233 行起）和 `main` 的状态输出（第 301 行）。

原接线丢弃 `validate_engineering` 返回的状态，普通 check 可能只显示“无证据”，看不到工程 pending/failed/blocked。交付检查仍会拒绝，因此不是放行漏洞。修复保留并输出工程角色状态；`test_regular_check_displays_pending_engineering_roles` 已验证 `product-designer=pending` 可见。

## 行为报告的语义判断

逐份阅读六份真实角色报告和一份调度报告，根据任务、已读证据、具体修法及结论判断，未用关键词数量充当质量判断。以下路径均相对本目录的 `behavior/`。

| 报告 | 独立判断 |
|---|---|
| `feature-product-manager-report.json` | 把 300 章续写任务放在主线，明确指出 200 项选择器及全量资料前置阻塞；区分成果丢失、越权采用、索引恢复和重复规则的优先级，给出可观察验收。changes_required 合理。 |
| `feature-product-designer-report.json` | 给出当前作品到下一章、比较采用及返回位置的完整路径；具体覆盖并发人工稿、保存失败、取消、过期、权限、索引失败及键盘可访问性，修法与界面行为对应。changes_required 合理。 |
| `feature-project-architect-report.json` | 交付模块归属、依赖、代表读写链；用候选分离、版本比较、共同应用服务、持久幂等和正文/索引分离处理提案反例，说明兼容和回退；未把未读实现称为既有事实。changes_required 合理。 |
| `feature-dba-report.json` | 定位任意建库、无历史覆盖、索引删正文、重复事实、可写 MCP 和高分越权；提出正式/-test 范围、CAS、修订/事件事务、只读事务及幂等约束，性能明确待 EXPLAIN 实测。changes_required 合理。 |
| `configuration-project-architect-report.json` | 逐项定位 cwd 路径分裂、筛选丢键、并发替换、新旧静默择一和 MCP 回退；给出唯一装配、完整保留、受保护发布、冲突停止和入口一致性修法，同时拒绝随机库及跨项目账号。changes_required 合理。 |
| `configuration-dba-report.json` | 具体保护既定连接全部参数、唯一测试库、原配置与未知键；处理并发删除风险、MCP 分裂、凭据缺项和维护范围。未连库、未将方案当真实恢复成功。changes_required 合理。 |
| `documentation-routing-report.json` | 对一个错字和两处标点判断 documentation，实际执行 plan 和工程 check；四职责均 not_applicable，无伪造角色报告。报告明确这只证明工程调度契约，不代表完整候选交付或实际产品修改。 |

六份坏提案报告的 changes_required 是样例期望结果，登记器均映射为 failed，不能误当产品可以推进；其全部运行验收项均为 pending。报告提出的是职责内方案，没有报告内越界实施或虚构 DB/UI 实测的证据。

主任务另三份设计自查报告标注 `current_session`、identity `/root`，具体交付本次 B 批次范围与契约，ready 限于设计复核。可以作为诚实的职责执行记录，不能称三位独立专家或替代本次 D5。

## 独立验证

- `python3 -m unittest tests.test_development tests.test_dev_workflow`，cwd 为 `scripts/`：53 tests，20.278 秒，OK，退出 0。覆盖触发、预算、私有/越界输入、错角色/摘要/执行方式、缺交付、major/缺失/失败/篡改报告、来源/协议陈旧、历史兼容及新任务绕过。
- `python3 scripts/dev/build_registry.py --check`：REGISTRY OK，退出 0。
- `python3 scripts/dev/check_plugin.py -v`：PLUGIN OK，退出 0；四工程角色读取预算均低于 20000，三个项目级相对挂载有效。该项是静态发现检查。
- `python3 scripts/dev/build_docs.py --check`：DOCS OK，退出 0。
- 主任务 `development.py ... check --delivery`：产品经理、产品设计师、架构师 passed，DBA not_applicable，退出 0；仅工程职责契约。
- 对九个派单包重新计算自身 input_sha256、逐条 source 内容及摘要、入口/流程 bindings，并验证对应报告：全部新鲜、角色/输入匹配。六行为报告为 failed，三设计自查为 passed。
- 与基线逐字节比对十二创作角色文件，无变化；registry 的 roles、load_budget、commands 及兼容视图除新增 development 外所有原顶层值均无变化。因此未观察到工程职责进入创作角色、章循环或审稿判据。
- 最终只读候选重算与任务冻结指纹相同；本报告属于证据元数据，不修改产品候选。

## 独立性与完成边界

本次独立执行的是代码/规则审查、标准库局部检查、历史/绕过反例及行为报告语义核对。六个角色代理的实际执行由协调者调度；本评审能核对其报告、冻结输入和内容质量，不能从 JSON 身份声明单独证明完整宿主执行轨迹。

落本报告时协调者最终全量检查仍在运行，不能把前一候选的全量结果挪用到当前候选；最终 D4 结果应另绑定当前指纹。本报告未执行真实 PostgreSQL、完整产品浏览器、模型创作链或五宿主新会话。五端加载、参数转入、实际 plugin_root/repo_root、Grok 重复发现/优先级仍待实际新会话核验。没有进行提交、远端发布或消费克隆同步。
