# 仓库架构成长方案

状态：已实施的设计依据（2026-10-18，本地候选，未发布）；适用基线为 v3.2.0、`0e3faa0` 及任务记录登记的工作树差异。原[方案复核记录](../../tasks/2026-10-18-architecture-plan.md)、[审查及复核](architecture-audit.md)保留取舍依据；作者随后授权按本方案实施，结果与待验项统一见[升级实施任务](../../tasks/2026-10-18-architecture-upgrade.md)。下文保留采用的设计、步骤及验收标准，不作为第二份执行进度表。

本方案解决清单漂移、开发工具归属、拆书扩展落点和配置耦合。保留原阶段编号以便追踪，执行顺序改为 **G0 基线 → G1 清单校验 → G2 工具与测试迁移 → G5 CLI 内聚 → G3 配置接入与分片**；G4 拆书落点已补入[拆书方案](../deconstruction/upgrade.md)，其实现随拆书 P1–P6 执行，不要求等完整架构升级结束。方案评审通过不等于已执行；后续获得整段实施授权后可连续推进，只在新关键取舍、实质规则确认或发布授权边界停下，不逐阶段重复索要许可。

## 问题复核与处置

原方案给出了方向，但以下问题使其不能直接成为实施单。优先级按可能造成的错误与阻塞判断，文件大或层次少本身不认定为高风险。

| 编号 | 现有证据与原方案问题 | 实际后果 | 修正与验收位置 |
|---|---|---|---|
| R1 高 | `.claude-plugin/marketplace.json` 顶层 name 是 `ncc-plugin`，插件的 name/version 在 plugins 数组内；原 G1 要求所有顶层 name/version 一致 | 正常清单会被误报，甚至误改市场身份 | G1 按字段路径映射，补 `.agents/plugins/marketplace.json` 的无版本格式与异常测试 |
| R2 高 | registry 直接读者有 core、ncc_prepare、check_plugin、build_docs 和测试；原 G3 只改 core | 准备工具、生成器、检查器仍读旧文件或启动失败 | G3a 先统一读取；G3b 再分片，保留生成的兼容聚合视图 |
| R3 高 | 原 G3 同时要求合并视图等价、键名清理与 legacy 退役 | 改键名必然破坏等价；旧书迁移可能失效 | 分片批次保持所有键、值、顺序与 schema；键名/退役单独决策 |
| R4 高 | 原 G2 只说明修改 sys.path；实际还有 ROOT 层级、with_name 定位、子进程路径、自动生成段和开发任务恢复入口 | 测试可能找不到入口、发现 0 项却退出 0；旧会话不能恢复 | G2 给逐文件迁移矩阵、旧入口兼容、发现数量与跨 cwd 验收 |
| R5 中 | book.py 的 gate_check 实现闸门，loops.py 的 cmd_unit 实现状态转移；原 G5 声称两者只编排 | 新规范与现代码直接矛盾，诱发无边界业务搬迁 | G5 限定 CLI 参数注册拆分，明确 book/loops 的业务归属；只禁止反向依赖 |
| R6 中 | 原 G4 把契约正文与代码常量并列，却未说明谁是源、如何检验；也未接好生成段与 load_budget | 新 schema 重复维护，引用层增加却没有控制读取量 | 拆书 P1 冻结机器契约、生成字段表、校验入口、样例目录与读取清单 |
| R7 中 | 原 G2 要求旧路径全仓零残留，但冻结证据有意保留旧路径；原方案称阶段可任意独立回滚 | 验收目标无法满足；反向撤销前置会破坏后续阶段 | 只查活动引用，列兼容例外；回滚遵守阶段依赖并复测 |
| R8 中 | 原证据主要是链接检查和数字核对，没有 CLI 行为对照、消费者矩阵、失败注入 | 文档检查通过会被误当成架构正确 | 每批给正例、反例、产物和退出条件；本轮仅验文档，实施证据后续产生 |
| R9 低 | scripts 顶层实际为 13 个 .py，并非 14；拆书拟新增 3 个子命令及 1 个已有命令参数，并非 4 个新子命令 | 盘点基线不可靠 | 修订审查结论；每个实施批次重新记录实测值，不把静态数字写成长期闸门 |

原审查未证明 registry 已造成运行故障，也未量化并发冲突；分片是维护性改善，排在明确的清单缺检与兼容风险之后。仅需要集中读入口时可在 G3a 完成后停下，不把“目录拆得更多”作为收益证明。

## 目标、边界与方案选择

完成后应能回答四件事：哪个字段由谁维护；新增文件落在哪里；旧入口为何仍能工作；失败时撤回哪些文件和依赖。机器可判定的目标为：清单漂移能定位到字段；测试发现数量不因迁移缩水；CLI 解析、退出码及写入行为一致；registry 消费者同源，分片丢键/重键/坏格式立即失败。

保留单仓、五端项目级接入、十二创作角色、现有命令与书库私有边界。架构批次不改闸门、创作判据、词表内容、默认选章或书项目数据，不迁移真实书库。拆书新增业务由其 P1–P6 承担。纯等价搬迁不自动触发模型回归；若实际改变角色读取、流程路由或创作判据，返回方案影响评估并执行对应行为验证。

| 决策 | 本次推荐及理由 | 备选与代价 | 确认边界 |
|---|---|---|---|
| D1 第二产品线 | 延后；当前按长篇单产品设计，出现真实第二产品需求再评估仓属 | 现在做多产品安装/命名空间会增加尚无消费者的机制 | 不阻塞 G1–G3，不把推迟写成已经确认的新产品战略 |
| D2 清单源与构建 | G1 以现有 `.zcode-plugin/plugin.json` 的 name/version 为权威，其他副本手工同步并强校验；宿主专属字段各自维护 | 生成清单可另立局部任务，但版本变更本身不是强制引入生成器的理由 | 使用现有版本来源；本轮不新增打包依赖或改变字段 |
| D3 键名与 legacy | 本次不改键名，不删 layout_legacy；先给消费者与兼容说明 | 改名需别名、弃用期及数据/调用迁移；与分片混做无法证明等价 | 真要改公开键或停止旧书支持时另呈具体迁移方案 |
| D4 registry 形态 | G3a 集中读取后，G3b 采用分片为源、registry.json 为可校验生成视图，保留现有原始文件消费者 | 继续单文件最省机制，可在 G3a 停止；直接删聚合文件则必须迁移所有外部读者 | G3b 在实施任务 D1 冻结分组和兼容期；整体授权覆盖具体方案时不重复问 |

## G0：建立可比较的实施基线

这是后续实施的准备步骤，本轮方案复核不运行无关全量测试。

1. 记录 plugin_root、repo_root、分支、完整提交号、当前 Git 差异归属。不能直接把“所有脏文件”收入升级交付；本次既有文档整理、脚本修复按原任务保留归属。需要隔离时，从已核实的受管源和已授权差异建立临时候选，不复制私有书库。
2. 保存五份清单的实际字段、registry 的解析对象及文件 hash、当前命令树、生成目标列表、五个测试模块与实际发现/执行数。基线取实施当时的工作树，不只取 HEAD，避免丢掉已有效的本地改动。
3. 对本批受影响接口跑一次基线检查。G2/G5/G3 属跨模块改造时跑全量；G1 只跑检查器与相邻接口。已有失败单列原因，不把它改写成此次回归，也不以此免除新失败。
4. 在实施任务登记精确 scope、验证命令、预期、回滚范围。下文新增文件均为拟建，创建时同步登记；不存在的命令/目录不能标已可用。

交付：实施基线报告、候选文件清单、前后对照方法。进入下一批条件是基线可复现、已有失败有归属；不要求先清空他人工作树。

## G1：按真实结构校验打包清单

前置：G0 完成该批基线；无 G2/G3 依赖。改动范围：现有 `scripts/check_plugin.py`、检查器测试、`workflow/architecture.md` 的版本来源说明及检查器说明。新增测试模块名拟为 test_plugin_manifests.py，G2 后随测试目录迁移。

### 字段契约

| 文件 | 要校验的字段 | 约束 |
|---|---|---|
| `.zcode-plugin/plugin.json` | name、version；skills/commands/agents | name/version 是比对基准，必须为非空字符串；三个入口目录按当前登记值解析到仓内有效目录 |
| `plugin.json` | name、version | 与基准相同；保留其 schema、作者、repository 等原字段 |
| `.claude-plugin/plugin.json` | name、version | 与基准相同；描述允许宿主差异 |
| `.claude-plugin/marketplace.json` | plugins 中唯一 name 等于基准的项，其 version、source | 目标插件恰好一项；version 一致；source 按当前本地相对格式解析到仓库根；顶层 name 保留市场名称 `ncc-plugin` |
| `.agents/plugins/marketplace.json` | plugins 中唯一目标项的 name、source.source、source.path | 当前为 local 与 `./`；解析到仓库根。该格式当前无 version，不补造字段、不要求顶层市场名等于插件名 |

这里只校验仓内实际使用的字段及关系，不宣称是各宿主完整 schema 验证器。未知字段保留；如果未来新增宿主或改变源格式，先更新该宿主映射与测试，不用统一对象覆盖不同格式。五份文件中有四个版本值，不能把它简写成“只有四份打包文件”。

### 执行步骤

1. 写接收显式 root 参数的清单检查函数，沿用 bad 错误集合；逐文件捕获缺失、JSON 解析和结构错误。报错至少给文件、字段路径、期望/实际值，退出码沿用 1。
2. 对 marketplace 先验证 plugins 为数组、元素为对象，再按插件名查找；不硬编码 plugins[0]。漏项、重复项均失败。
3. 检查本地 source/入口目录的解析边界，保留本文件格式差异。检查器只读，不修改清单、不在失败时自动同步。
4. 接入 main 的正常检查链；更新“版本号一处”的表述为“权威来源一处，分发副本校验”。README 仍由现有 build_docs 读取同一权威版本。

验收：正常五份清单通过；任意一个副本改 version/name 失败；缺文件、坏 JSON、plugins 类型错、重复/缺失目标、source 越界失败；修改市场顶层 name 为既有合法市场名不误报；Codex 市场无 version 通过。所有反例在临时合成目录构造，不篡改实际安装配置。

验证入口（G2 前）：`python3 -m unittest discover -s scripts -p 'test_plugin_manifests.py'`，再运行 `python3 scripts/check_plugin.py -v` 与 `python3 scripts/build_docs.py --check`；新增测试文件存在后执行。交付字段矩阵、测试结果和真实清单只读检查结果。失败留在 G1 修复；回退仅撤销本批检查器、测试和说明，不更改真实清单身份。

## G4：把拆书扩展落点接入 P1

本轮已将下列归属写入[拆书方案的接口与落点](../deconstruction/upgrade.md)，这是方案补全，不是新增功能已落地。P1 负责冻结其字段和样例；P2–P6 才实现运行行为。

| 对象 | 拟落点与唯一职责 | 实施完成依据 |
|---|---|---|
| 规则入口 | ncc-deconstruct 的 SKILL.md 留目标路由、阶段顺序、必读参考链接及授权边界 | 经理能够按目标选择参考，入口不复制完整规则正文 |
| 按需参考 | 该技能 references 下分 layers.md（层/抽样）、packet.md（三件套/缺上下文）、ingest.md（入库/恢复）、screenplay.md（场次）、transfer.md（转化） | 每项现有约束有唯一正文；按角色/层列出必读集合，实测读取预算 |
| 机器结构契约 | workflow/contracts/deconstruction 下的章、场次、进度 JSON 契约；按 P1 需要扩展索引/派单包契约 | 使用标准库支持的有限类型/必填/枚举/版本描述，明确支持语法；不声称支持完整 JSON Schema |
| 字段说明 | designs/deconstruction 下 contracts.md，P1 新建；字段表由机器契约生成，人工只写语义与迁移 | 生成检查能发现字段表陈旧；词表通过 registry 引用，不再抄一份枚举常量 |
| 运行校验 | decon 对外接口保留；出现完整职责时把内部 schema/索引/入库/存储实现放 ncclib 的 deconstruction 子包 | 结构校验使用同一契约；证据、幂等、跨章一致性用明确函数实现，不能由字段表冒充 |
| 合成样例 | G2 前 scripts/fixtures/deconstruction，G2 后 scripts/tests/fixtures/deconstruction | 正常、坏格式、错 hash、缺上下文、中断恢复都有输入和预期；eval/anchors 保持审稿锚定用途 |

P1 同时更新 registry 的 load_budget 和 build_docs 的 technique-roles 生成目标；若生成段仍留 SKILL.md 就显式保留，若随内容搬入 transfer.md 就改生成器后再生成，不能手工复制。按需读取的检查方式先兼容现有检查器：在对应角色 reads 中登记所有可能读到的参考，以全部相加的保守上界验收，同时记录真实派单的层级读取集；超预算则缩减/重组参考，另行设计按路由计预算，不能漏报引用。

G4 不依赖 G2 完成。拆书先开工时用旧测试目录，G2 再一次迁移；架构先完成时直接采用新目录。P1 验收除了链接检查，还需让实际拆书执行者跑合成的“结构研究、稀疏技法抽样、完整逐章、只读转化”场景，检查读取范围和停止边界；实质规则候选完成回归后按开发流程呈作者确认。

## G2：迁移开发工具与测试，保留调用连续性

前置：G1 验收；G4 的文档补全已完成。目标是实现归属清晰，不以立即删掉旧脚本路径为验收条件。

拟目标结构（只创建有实际内容的目录）：

```text
scripts/
  ncc_state.py / ncc_prepare.py / ncc_library.py / ncc_eval.py / check_chapter.py
  check_plugin.py / check_dev_workflow.py / build_docs.py  # 过渡期薄转发入口
  ncclib/                                                 # 运行领域实现
  dev/
    __init__.py
    check_plugin.py / check_dev_workflow.py / build_docs.py
  tests/
    __init__.py
    test_*.py
    fixtures/deconstruction/                              # P1 有样例才创建
```

### 迁移矩阵与顺序

| 顺序 | 文件/接口 | 具体处理与容易漏掉的点 |
|---|---|---|
| 1 | 三个开发工具 | 移实现到 dev；check_plugin/build_docs 的 ROOT 改为从文件位置解析仓库根，不能只改 sys.path；check_dev_workflow 保留调用者显式传入的 --repo 语义 |
| 2 | 三个旧路径 | 留仅转发 main 的兼容入口，返回码、参数、输出保留；不得复制业务实现。兼容是现有 shell/恢复命令的兼容，测试 patch 要指向新实现模块，避免 patch 到无效的 wrapper 全局变量 |
| 3 | test_ncc_state | HERE 拆成 TEST_ROOT、SCRIPTS_ROOT、REPO_ROOT；STATE/CHECK/EVAL 仍指运行入口；生成器/检查器指 dev；eval 与 workflow 路径从 REPO_ROOT 拼接 |
| 4 | test_ncc_prepare、test_ncc_library | with_name("ncc_prepare.py") 改为 SCRIPTS_ROOT 定位；ncc_prepare 导入仍解析运行实现 |
| 5 | test_v3_regressions、test_dev_workflow、新增清单测试 | 更新 ncc_eval/ncclib 与 dev 模块导入；所有 patch 对象绑定真实实现；新增 tests 包保证递归发现 |
| 6 | 活动引用和生成目标 | 改 AGENTS、ncc-dev 技能、当前工程规范/指南/设计、build_docs 自述/生成标记/错误提示、现行自测调用；由生成器更新生成段。本批不改已冻结历史报告字节 |
| 7 | 恢复与打包 | 从仓外 cwd 调旧入口和新入口；--repo 指向合成仓时不得误用工具自身仓库；核查插件分发能带上 dev、tests 中所需文件 |

新规范测试命令为 `python3 -m unittest discover -s scripts/tests -t scripts -p 'test_*.py'`；显式 top-level 保证 scripts 在导入路径中。旧命令 `python3 -m unittest discover -s scripts -p 'test_*.py'` 在兼容期仍应发现同一组用例；需 tests/__init__.py，不能只凭退出 0 判断通过。两个命令的测试 ID 集合应相同，不要求重复执行整套测试：先比较发现集合，再执行一次全量。

兼容入口保留到至少一个后续发布批次完成所有受影响宿主的新会话验证，且活动文档及任务恢复不再依赖旧路径；没有新会话证据就继续保留。冻结历史证据永远不因退役而重写；删除入口另列兼容变更，不夹在本次移动中。

### 验收与回退

- 全量用例数不得少于迁移前基线，新增/删除逐项解释；零发现必须失败。额外覆盖从根目录、仓外 cwd 的 CLI 调用，含中文/空格路径。
- 旧/新检查入口正常、失败退出码一致；snapshot/check 在临时合成仓上产生相同候选指纹并保持 --repo 边界。
- 生成两次第二次无改动，--check 通过；差异仅为计划内路径/标记等元数据，生成业务内容不变。
- 旧路径扫描只针对活动源和文档；允许薄入口、兼容测试、当前迁移说明和 docs/evidence 的历史命令，输出剩余命中分类表，不能写“全仓零残留”。

交付：迁移映射、用例发现对照、全量结果、兼容/跨 cwd 报告、引用命中分类。回退时将实现、测试和活动引用一并恢复；如果 G5/G3 已落地，先分析其依赖，不能只反向 git mv。

## G5：收拢 CLI 参数注册，约束依赖方向

前置：G2 完成；不与 G2 同一提交，先验收路径迁移再拆逻辑。当前 `scripts/ncclib/cli.py` 的 main 同时创建 parser、解析、派发、记录操作和生成视图；保留最后四项顺序，优先抽出可单独检验的 parser 构建。

1. 先在原文件提取 build_parser()，main 仍执行 parse_args → handler → log_op → auto_render；不改变异常、退出和失败后的副作用。冻结此时完整 CLI 契约，按“命令路径”区分同名子命令，不把去重命令单词数当接口覆盖数。
2. 将参数注册函数放入拟建的 ncclib/cli_parsers 子包：book（书/闸门/章）、loops（单元/卷/反馈）、ledgers（账本/事件）、scenes（场景/审稿/简报）、learning（材料/偏好/记忆/设置）、deconstruction（拆书/技法）、delivery（进化/导出/全局工具）。各模块提供“顶层命令名 → register_<command>(sub)”映射，主入口按旧命令顺序逐项注册，避免按领域成批注册改变 help 顺序；完整归属表从旧 parser 提取，每条命令恰好注册一次。注册函数仅定义参数并绑定 handler。
3. cli 保留 READ_ONLY、RENDER_SKIP、日志和自动视图策略。book.py 明确负责书生命周期与闸门，loops.py 负责单元/卷/完本业务；本批不迁移其中的 gate_check、cmd_unit 等规则函数。
4. 通过 AST 的 Import/ImportFrom 收集依赖，加入测试禁止 core/领域实现导入 cli 或 cli_parsers，禁止 parser 反向导入 cli，禁止 ncclib 依赖 scripts/dev；parser 只能依赖其绑定的领域函数与 core 常量。发现新循环先移除反向调用，不通过扩大允许表掩盖。
5. 保持 `scripts/ncc_state.py` 的命令入口及对其他脚本的导出接口；不顺手清理星号导入、重命名 handler 或更改业务默认值。

验收分三层：

| 层 | 操作 | 必须保持 |
|---|---|---|
| parser 契约 | 递归比较所有命令路径、位置参数、options、dest、类型、choices、default、required、nargs 与 handler 模块/名称；逐条命令 --help，并测试缺参/非法值 | 完整命令集合及默认行为相同；错误用法返回 2；help 可仅规范化可执行路径和环境换行 |
| 运行副作用 | 在同样的合成书项目依次执行 init/status、chapter add、promise add/list、gate check、非法命令；另测 decon coverage、prepare 状态 | 退出码、标准输出及文件差异匹配；只读操作不写状态/日志，成功写操作的日志与渲染次数不变，失败不新增副作用 |
| 依赖与集成 | 导入图检查、全量自测、check_plugin、build_docs --check、ncc_eval mech | 无新循环；运行脚本不依赖开发工具；原机械结果不变 |

时间戳、临时绝对路径只能按事先列出的字段归一；不得删除业务状态字段来制造等价。交付完整命令契约、差异报告及依赖测试。失败按提取批次退回旧 parser；业务层无需随本批回滚。

## G3：先统一读取，再做可逆分片

前置：G2、G5 已验收；冻结 D4。分成 G3a 与 G3b 两个提交/验收点，均不改 registry 业务键值、书项目 SCHEMA 或语义版本。配置文件规模与版本兼容是不同问题，物理分片不自动引入“各片独立业务版本”。

### G3a：统一注册表读取

拟在 ncclib 增加 registry.py，提供 load_registry(plugin_root) → dict。它只依赖标准库，不 import core；否则 core 加载注册表会形成循环。G3a 仍读原 registry.json，返回对象与现状一致。

| 当前消费者 | 改造与验收 |
|---|---|
| `scripts/ncclib/core.py` | 使用统一 loader；REGISTRY 以及从中导出的 V/LAYOUT/GATES 等值不变 |
| `scripts/ncc_prepare.py` | 用同一 loader 取 preparation；ncc_library 的间接依赖一起验证 |
| check_plugin、build_docs（G2 后在 dev） | 用同一 loader；仍以工具所在插件根读规则，--repo 的任务工作树语义不被改写 |
| test_ncc_state 的直接 JSON 对比 | 保留至少一个原始兼容视图检查，另加 loader/生成视图对比；不能把期望和实际全换成同一函数而丢掉独立预期 |
| 文档/外部脚本读取 registry.json | G3a 无变动；G3b 由生成视图保留旧路径，并标明只读与生成办法 |

运行时读取失败要包含文件路径和具体原因，立即停止；不得返回空字典、默认旧配置或静默回退。测试覆盖缺文件、坏 JSON、非对象根、重复 JSON 键（使用 object_pairs_hook 检测）、缺必需键。该阶段比较旧/新读取对象、所有导出常量、prepare 和生成结果，再跑跨模块全量。

### G3b：分片为源，保留生成聚合视图

拟文件在 workflow/registry 下。以下表覆盖本基线全部 41 个顶层键，每键只归属一处；实施开始时若基线增长，先更新映射并解释新增键，不能悄悄漏掉。

| 拟分片文件 | 顶层键 | 数量 |
|---|---|---:|
| flow.json | schema_version, stages, stage_table, layers, gates, loops, writing_modes | 7 |
| roles.json | roles, commands, load_budget | 3 |
| rules.json | axioms, iron_rules, principle, principles, scene_cards, review_plan, review_words, check_words, avoidance, length, reader_personas | 11 |
| storage.json | vocab, layout, layout_legacy, ledgers | 4 |
| preparation.json | preparation, knowledge, materials, setting_base, setting_categories | 5 |
| learning.json | style, preferences, craft_library, memory, handoff, decon, techniques, evolution | 8 |
| delivery.json | eval, dashboard, export | 3 |

分组依据是消费者与修改原因；嵌套 vocab/layout 暂不继续按领域分裂，避免同时改变数据接口。roles/commands 可能含生成文本、rules 含审稿内容；分片不是角色读取包，不给写手新增“整片读取”权限。真正派给角色的仍是既有受限参考与派单包。

执行方法：

1. 冻结分片前解析对象、对象键顺序、原文件 hash 和全部生成输出，在临时实施证据中保存。对照物来自旧工作树，不能用候选反向生成“旧预期”。
2. loader 显式登记允许的分片名及顶层归属，不 glob 任意文件；拒绝缺片、未知 JSON 片、重复键、跨片归属错误、非对象根和缺键。禁止 dict.update 静默覆盖。片内嵌套对象不做深合并，沿用原数组与字典顺序。
3. 使用机器迁移保留原值和类型，把每个顶层键写入其归属文件；合并后按冻结的原顶层顺序重组，避免渲染及迭代顺序变化。归属表只描述所有权，不复制业务值。
4. 增加开发构建入口 build_registry.py：从分片生成现有 workflow/registry.json，固定 UTF-8/缩进/末尾换行，临时文件后原子替换；--check 只比较、不写入，陈旧退出 1。路径和用法在创建后接入现行文档。
5. G3b 后运行代码经 loader 读分片；聚合文件是只读兼容视图。loader 核对兼容视图与分片一致，不一致就说明重新构建的方法并失败；生成器调用同一合并函数但不要求旧视图先一致，避免无法修复的启动死锁。不并行维护两套人工配置、不用“有哪个读哪个”的回退。
6. 将构建顺序固定为 build_registry → build_docs；检查链顺序为 build_registry --check → check_plugin → build_docs --check。在插件检查链加入聚合视图新鲜度检查；构建和检查都不自动写书项目。
7. 更新 AGENTS、workflow 的事实源说明、工程文档及生成标记，明示“分片可编辑、聚合文件由工具生成”。新增分片与聚合生成物均计入候选指纹和分发；旧单文件资料不会被误称为新唯一可编辑源。

### 等价、版本和兼容验收

- 逐 JSON 路径比较旧对象与新合并对象：键集合、值、类型、数组顺序全部相同；字典迭代顺序另比。只做字典 == 不能证明输出顺序不变。
- registry 的 schema_version 继续为当前值 2，书项目 SCHEMA 继续为当前值 4；分片不触发书库 migrate。layout_legacy 继续被 core/book/learning 等迁移调用使用。
- principle 是理念字符串、principles 是工程七律；check_words 是机械检测词表、review_words 是写手上下文隔离词表，职责不同。补说明即可，不能按“名称近似”合并或删键。
- 故障注入：缺片、片内/跨片重键、错误归属、未知片、坏 JSON、手改聚合视图、旧生成物、无权限输出均须明确失败。构建中断不能留下半个有效聚合文件；重跑构建幂等。
- 用 G0 的旧基线对照所有生成目标及 G5 的命令行为样例；全量自测、清单/链接检查、生成检查、ncc_eval mech 通过。生成器路径/说明的计划内差异单列，不允许顺带变化业务文本。
- 打包/复制后的干净插件目录能运行五个入口和开发检查；受影响宿主新会话确认实际加载根、版本和代表调用。静态通过不能填成五端运行通过。

回退：G3b 回退为 G3a 的单文件读取与原聚合内容，撤销分片/生成器接线，保留 G3a 集中接口；G3a 再回退才恢复原读法。回退对象取紧邻本批的已验收基线，不能用仓库最初 HEAD 覆盖后续拆书已增补的配置。若拆书在 G3b 后改过分片，先将这些增量合并回单文件并重验；存在无法判定的业务差异时修复优先，不自动反向迁移。

## 依赖、验收与交付办法

| 批次 | 前置/交接 | 最小完整证据 | 停止/返回条件 |
|---|---|---|---|
| G1 | G0 的清单基线 | 字段映射、正常/漂移/坏格式用例、插件和生成检查 | 误报合法格式或漏报漂移，回 G1 |
| G4 → 拆书 P1 | 本轮已补方案；不依赖 G2 | P1 的契约/样例/生成字段表/读取集/行为验证 | 结构或语义归属不清，回 P1，不先扩规模 |
| G2 | G1；接收拆书已存在样例的目录 | 测试发现集合、迁移矩阵、跨 cwd 与恢复报告、全量结果 | 少发现用例、旧入口断裂，回迁移矩阵 |
| G5 | G2 | 完整 CLI 契约、正反例副作用对照、依赖检查与全量 | 解析、日志、渲染有未授权差异，回对应提取 |
| G3a | G5 | 消费者清单、统一读取对照、全量 | 任一消费者读旧规则/接口失效，回读取接入 |
| G3b | G3a；冻结 D4 | 全键映射、顺序与值等价、失败注入、生成/打包检查、全量与适用宿主证据 | 丢键、双源、生成陈旧或业务差异，回映射/兼容设计 |

本次[实施任务](../../tasks/2026-10-18-architecture-upgrade.md)按 [开发工作流](../../engineering/workflow.md) 走 architectural 路径，可将上表作为阶段验收点。每批在任务记录写入：实际 scope、前置候选、执行命令、测试数/退出码、差异解释、报告 hash、候选指纹、未验宿主和回滚依赖。不能沿用前一候选的 passed，也不能以本轮文档检查代替未来功能证据。

独立评审核查实际实现与反例；当次没有独立能力时如实写自查和待办，不调用小说角色冒充代码评审。发布按已有授权处理；未授权时交付本地候选。获得发布授权后按先拉取/合并、复验候选、精确暂存、检查私有内容、提交/推送、核对远端和新会话加载执行。当前 zcode 直注册本目录，其他机器的消费克隆分别记录；不把本地改完等同于已加载。

回滚按依赖反序或显式兼容补丁处理。G4 文档可以独立调整，G1 不修改书数据；G5 依赖 G2 的工具接线，G3b 依赖 G3a 和构建接线，不能承诺任意单阶段 revert 都安全。未提交时只撤销本批文件差异；已发布时对具体提交做已授权的 revert，不 reset 他人工作。

完成含义分开记录：方案复核与架构实现分别绑定原记录和实施任务；G1/G2/G5/G3a/G3b 的本地实现已完成，G4 的方案接线已完成，拆书 P1–P6 业务不在本次架构范围。独立评审与五端新会话结果以实施任务的待验项为准。原审查保留为取舍依据，但以其复核修正和当前代码为准，不反复维护第二份进度表。
