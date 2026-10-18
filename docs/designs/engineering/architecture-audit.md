# 仓库架构审查记录（2026-10-18）

审查者：sdlc-workflow 架构师角色（独立子代理，全新上下文），应作者要求对本仓做只读审查。作者提出的抱怨：结构层级不清晰、文件归属有问题、架构缺乏前瞻性、目录不为未来规划导致文件堆积。本记录保存审查证据与结论；处置方案见[仓库架构成长方案](architecture-growth.md)。

审查边界：尊重作者已定约束（单仓扁平、五端项目级接入、`novels/` 私有、十二角色与七技能体系为产品本体），这些不是发现；2026-10-16/17 已完成的 docs 重组与 workflow/ 收敛不重复报告。运行了 `check_plugin.py`（PLUGIN OK）与 `build_docs.py --check`（DOCS OK）取证，未修改任何文件。

## 方案复核修正（2026-10-18）

作者随后要求检查并完善升级方案。本次由当前开发会话对照实际文件复核，未另派独立代理；下文保留原审查观察，涉及下表的数量、优先级和处置建议以本次修正及[现行成长方案](architecture-growth.md)为准。原检查通过只能说明当时检查器覆盖的项目通过，不能证明其未实现的跨清单校验有效。

| 原判断 | 复核事实与修正 |
|---|---|
| 四份打包清单、name/version 可统一比较 | 实际有五份相关 JSON、四个版本值。两个 marketplace 的顶层名称都是市场名；Claude 插件版本在 plugins 内，Codex 本地市场没有 version。必须按实际字段映射检查，不能统一比较顶层字段 |
| scripts 顶层 14 个 Python 文件 | 实际 13 个：5 个运行入口、3 个开发工具、5 个测试；测试共 2592 行。并非所有测试都用 sys.path，另有 with_name 和直接模块导入 |
| registry 分片只需改 core | ncc_prepare、check_plugin、build_docs、test_ncc_state 也直接读取原文件。须列完整消费者并保留原路径的兼容办法 |
| 分片顺便清理近似键 | principle/principles 和 check_words/review_words 各有不同职责；layout_legacy 被迁移逻辑使用。分片保持原键值，改名/退役另作兼容方案 |
| book/loops 是纯聚合层 | book.gate_check 实现闸门业务，loops.cmd_unit 实现循环状态转移。可约束依赖方向，不能以一条新口号否定已有领域职责 |
| 拆书增加 4 个子命令 | 当前方案明确的是 plan、packet、ingest 三个新子命令，以及已有 coverage 的 --layer 扩展；参数与退出码尚待 P1 冻结 |
| registry 体积/平铺直接列为高风险 | 尚无冲突频率、运行故障或维护成本的实测因果证据；降为维护性风险。清单漏检与迁移兼容错误优先，统一读取可先独立交付 |
| docs 健康等于方案已可执行 | 文档归属已改善，但契约唯一来源、路径迁移、行为对照和依赖回滚仍需补全；现行方案已逐批补上 |

本次不重新验证第三方项目，也不把原报告的“预计膨胀 3–5 倍”“便宜一个数量级”当作实测结论。低优先级 L1/L3 属查找体验，现有链接有效；不为改日期或同名文档移动已冻结证据。后续如整理，只更新活动导航并保留历史引用。原 H1/H3 不直接驱动全面重构，实施依据是现行方案中的具体消费者、兼容接口和验收反例。

## 结论摘要

运行时架构纪律显著好于仓库外观：ncclib 分层单向、生成-校验闭环真实工作、docs/ 有成文的归属与生命周期规范。作者三条抱怨的核实结果：层级不清主要在 **scripts/ 与根目录打包层**；归属问题集中在**打包清单四处手工同步、新 schema 与测试样例无固定归属**；前瞻性缺口的实质是三个"单点枢纽"吸收一切新关切而无分区机制——`workflow/registry.json`、`scripts/`、宿主清单层。

## 问题清单

### 高

**H1 registry.json 是多领域混合的单点事实源，无分片机制。** 2776 行 / 91KB / 41 个顶层键，至少五类异质内容混居：状态机（stages/gates/layers）、创作标准（axioms、iron_rules、scene_cards）、工具词表（vocab 35 键、layout 58 条、load_budget、check_words、review_words）、特性配置（memory、handoff、decon、techniques、evolution、preparation、setting_categories）、遗留兼容（layout_legacy）。体积分布 roles 约 20%、layout 约 18%、vocab 约 8%。两对易混键并存：`principle`（口号字符串）与 `principles`（七律）；`check_words` 与 `review_words`。拆书升级方案的"接口与落点"一节明言"词表/元数据仅在这里增补"。违反自家"按变化内聚"：改词表与改状态机节奏完全不同却同文件，合并冲突面随每个新特性线性增长；`schema_version` 是唯一版本机制，无法表达"某领域契约变了、其余没变"。

**H2 打包清单与版本号多处手工副本，无生成、无校验。** `"version": "3.2.0"` 手工存在于根 `plugin.json`、`.zcode-plugin/plugin.json`、`.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json` 四处（2026-10-18 复核仍一致）。`check_plugin.py` 只查文档标题不写版本号，不比对清单；`build_docs.py` 仅从 `.zcode-plugin/plugin.json` 读版本写 README，不反向同步。`architecture.md` 自称"版本号一处"与事实不符。`.zcode-plugin/plugin.json` 达 8947 字节，三语 description 各 2000+ 字符纯手工维护。

**H3 scripts/ 四种角色平铺混杂。** 14 个 .py 同层：运行时入口 5（ncc_state、ncc_prepare、ncc_library、ncc_eval、check_chapter）、开发检查器 2（check_plugin、check_dev_workflow）、生成器 1（build_docs）、测试 5（合计 2592 行，最大 test_ncc_state.py 1370 行），外加 ncclib/ 包。AGENTS.md 的 `unittest discover -s scripts` 把该布局固化为契约。运行链与开发工具链变化节奏不同；测试文件以 `sys.path.insert(0, HERE)` 定位包，搬迁需同步指针。

### 中

**M1 ncc-deconstruct 是唯一没有 references/ 层的创作技能。** 仅 101 行 SKILL.md；其余创作技能都有 references（ncc-new 6 份、ncc-prepare 5、ncc-write 4、ncc-review 2）。拆书升级的六个规则域（目标路由、默认抽样、三件套、场次、层覆盖、转化边界）按现方案全部进单文件，"按需可见"最先断裂。仓内先例：`skills/ncc/references/domains/`（26 文件）。

**M2 新 schema 与测试样例无固定归属。** 拆书升级新增章文件/场次/进度三类 schema，落点只有代码与 registry 键；合成测试样例只有一句"公开测试与评测"，无目录归属。`eval/` 独占根目录一层，语义是审稿判据锚定章，混入拆书样例会稀释。

**M3 cli.py 单文件平铺 88 个命令名。** 487 行内 127 个 add_parser（去重 88 命令），横跨十余领域；拆书升级再加 4 个子命令。入口聚合本身合理，但内部无分组结构。

**M4 ncclib 聚合层无边界约束。** 实测依赖严格单向（core 最底，book.py/loops.py 各 import 9 个领域模块、cli.py 12 个，无人反向 import cli/book）；但聚合点无"只聚合不落逻辑"的成文约束，是内聚缓蚀的典型路径。

### 低

**L1 任务-证据关联键日期错位**：`docs/tasks/2026-10-12-readme-refresh.md` 链向 `docs/evidence/2026-10-13-readme-refresh/`，链接通但关联键不稳定。
**L2 registry 键名易混对**：`principle`/`principles`；`layout_legacy` 无退役条件标记。
**L3 同名异义文档对**：`designs/engineering/workflow.md`（设计依据）与 `engineering/workflow.md`（现行规范）符合自订规则且互链，仅检索与口头指称易混。

## 成长压力测试

| 场景 | 断裂点（按出现顺序） |
|---|---|
| 拆书升级 P1–P6 落地 | ① ncc-deconstruct SKILL.md 被六个规则域压垮（M1）；② 三类 schema 无契约归属，作者读不到（M2）；③ decon.py（现 274 行）预计 3–5 倍膨胀后平铺进 ncclib，包内无领域子包先例；④ cli.py 再加 4 命令（M3）；⑤ 合成样例无家（M2）。docs 侧无断裂 |
| 第六端宿主接入 | 软链挂载成本低（加一个 dot-dir）；断裂在清单层——第 5 份手工清单，版本副本 4→5，仍无校验（H2），三语 description 再抄或再膨胀 |
| 第二条创作产品线（剧本/短剧等） | 每一层都无隔离：插件以整个 `skills/` 目录挂载全端；registry 全局键全是长篇语义；agents 平铺、commands 的 ncc-* 前缀是唯一隔离手段。同仓则全端强制捆绑，独立仓则改变单仓定位——作者级未决决策，当前结构对两个方向都没准备 |

## 对照发现

- **sdlc-workflow**：`adapters/`（hosts.json＋各宿主适配＋渲染脚本）＋`agent-sources/`——宿主差异收敛到一层。可借鉴其"适配层"思想补 H2 的清单校验；不适用处：ncc 软链已是内容单一源，照搬渲染管线是过度工程。
- **vsc-workflow**：`tests/` 分离、显式 `migrations/`、`library/` 按领域分子目录。可借鉴 tests 分离（H3）与 schema 迁移显式化（H1 的分片与局部版本）；不适用处：DB 迁移目录是数据库产品需要；ncc 已有同等机制（references/domains/），只是没推广到 schema 与样例。

## 检查过且健康的部分

ncclib 依赖方向实测与 architecture.md 宣称一致；生成-校验闭环真实工作；五端软链零内容复制（.claude 28 条 / .agents 21 条 / .grok 12 条）；docs/ 治理规范含预留模块命名，是全仓最有前瞻性的一处；workflow/ 已收敛为三件现行事实源；私有内容双层守卫有效；AGENTS.md 与现实一致；测试纪律成文（按影响范围选测）；agents/ 十二角色当前规模下平铺正确。

## 建议顺序与开放决策

1. 先做 H2（清单校验，机械可验、风险最低）；
2. H1（registry 分片）先出设计、走规则改动闸门；
3. M1/M2/M3 的归属补全并入拆书 P1 冻结契约，比事后补便宜一个数量级；
4. 开放决策（作者）：第二创作产品线的仓属与插件身份——影响 registry 分片命名空间与清单层长期形态，应在分片设计定稿前拍板或明确推迟。
