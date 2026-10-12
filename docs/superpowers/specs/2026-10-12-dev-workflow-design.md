# ncc-workflow 开发工作流重建设计（spec）

日期：2026-10-12 ｜ 状态：待作者评审 ｜ 路径：重量级（brainstorming → 本 spec → writing-plans → 分阶段实施）

## 0. 目的与成功标准

为 **开发 ncc-workflow 这个项目**（插件本身的演进）建立一套标准开发工作流，融合 superpowers 生命周期方法与 mattpocock 深模块设计纪律，以 SSOT 为第一原则，claude/codex/zcode/kimi/grok 五端可用。

**不是**：不改小说创作工作流（workflow/registry.json 那套）的业务逻辑；本设计只新增"开发流程层"。

## 0.1 边界声明：两条分支，借鉴思想，不照搬流程

工作流系统有**两条分支**，本 spec 只辖第二条：

- **创作分支**（用工作流创作）：S0 立书→S5 收束。哲学：下限靠系统（闸门、硬伤审、水章判据、三本账），上限靠作者与选择（多版挑选、书魂从种子生长、不打绝对分）。
- **升级分支**（调整优化升级工作流本身）：即本流程。工程方法（superpowers / mattpocock / grill 系列）原生适用，但须翻译成 ncc 概念。

两条纪律：
1. **工程思想进入创作域必须先翻译成 ncc 概念**。逐条对照，ncc 本就是这些思想的领域化实践者：澄清↔书魂四问与快捷通道；规格↔G0/G1/G2 冻结；深模块↔写作简报（小接口）藏审稿清单（实现）；计划↔总纲卷纲章纲；验证↔机械检查+硬伤审+全量自测；评审↔写-审-改分离与盲读；SSOT↔信息架构七律与 book.json 单一状态源。
2. **禁止仪式照搬**：给创作循环插规格评审门、红绿测试或 frontier 质询，等于用可判定性窒息不可判定性，违反"上限靠作者与选择"。**grill 系列只进升级分支**——它质询的对象是"流程变更提案"（工程决策树：影响面/回滚/回归预期），不是创作判断（书魂、弧光、文风属于品味型，质询会把创作变成答辩）。

真正可借鉴的增量只有三条：
- **量级棘轮**（借自 brainstorming 的 spike/bounded/architectural）：插件维护任务先分类——顺手改/局部改/动结构改，流程重量随量级配，发现隐藏复杂度只升不降
- **埋错先行**（TDD 的领域反转）：改审稿判据前，先把该判据应捕获的错例种进锚定章（先红），实现判据后锚定章回归变绿——规则改动从"改完再测"变为"先定义什么算捕获"
- **插件开发工作流本身**（本 spec）：开发插件是软件工程，工程流程在此原生适用

成功标准：
1. 任一 CLI 里说 `/ncc-dev`（或 `/skill:ncc-dev`）即进入标准开发流程，按阶段推进到交付
2. 流程工件自身符合一事一源：接口与实现分离，无内容重复
3. 全量自测（115 项）与 check_plugin 不回归；规则类改动走 ncc-eval 回归
4. 交付阶段被既有 git 钩子（先拉后提交 + 私有守卫）强制兜底

## 1. 方案对比（已选 A）

| 方案 | 内容 | 取舍 |
|---|---|---|
| **A. 深模块分工（选定）** | 技能 = 小接口（阶段路由），文档 = 深实现（标准与理由） | 接口小、引用不复制、五端入口统一；代价是公共技能面 +1 |
| B. 纯文档 | 只写 docs/dev-workflow.md，靠 AGENTS.md 指引 | 不改公共面；但入口弱、五端体验不一致 |
| C. 全塞技能 | SKILL.md 包含一切 | 单文件肥大、文档与技能重复——违反一事一源，否决 |

选 A 的关键论据（codebase-design 词汇）：SKILL 是**深模块的小接口**——大量行为（各阶段标准、边角情况）藏在文档实现里，调用者只学一张路由表；文档是**实现**，不进调用者视野。接口即测试面：验证 = 走一遍技能路由能否到达正确闸门。

## 2. 架构

```
调用者（五 CLI 的会话）
   │  /ncc-dev <意图>            ← 小接口
   ▼
skills/ncc-dev/SKILL.md          阶段路由表（8 阶段：目的/动作/闸门/产物）
   │  按阶段引用                   ← seam：行为可在此替换（宿主有 superpowers/mattpocock 时借用其技能）
   ▼
docs/dev-workflow.md             深实现：每阶段完整标准、理由、边角、宿主技能映射
   │
   ├── scripts/（test_*.py、check_plugin.py、ncc_eval.py）   既有确定性验证面
   └── .githooks/（pre-commit/pre-push）                     既有强制闸门（不动）
```

新增文件：`docs/dev-workflow.md`、`skills/ncc-dev/SKILL.md`、`commands/ncc-dev.md`、三处 junction（.claude/skills、.agents/skills、.claude/commands）。
改动文件：`AGENTS.md`（开发段指向新 SSOT）。**不动**：registry.json、既有七技能、钩子、脚本。

## 3. 生命周期八阶段（技能路由表的内容）

| 阶段 | 目的 | 闸门（过不了不进下一阶段） | 产物 |
|---|---|---|---|
| S0 澄清 | 分类：spike/bounded/architectural；先问目的再问方案 | 作者确认分类与目的 | 一句分类声明 |
| S1 规格 | 意图写成书面 spec | 作者评审通过 spec 文件（评审形态译自 grilling：变更提案建模为决策树，按批问可问的，每题附推荐答案，影响面等事实由脚本查证而非问作者） | docs/superpowers/specs/…-design.md |
| S2 设计 | 用深模块词汇定接口与 seam；过删除测试 | 设计段落逐段获认可（随 spec 评审） | spec 内设计节 |
| S3 计划 | 分阶段实施计划，每阶段有验收标准 | 计划文件作者过目 | 实施计划（writing-plans 约定） |
| S4 实现 | TDD：先写失败测试（scripts/test_*.py）再实现；小步走 | 新测试红→绿 | 代码 + 测试 |
| S5 验证 | 全量自测 115 + check_plugin；**规则改动**（registry/skills/agents）推荐**埋错先行**：先把新判据应捕获的错例种进锚定章（先红），实现判据后 ncc-eval 回归变绿 | 全绿 | 验证记录（命令与结果） |
| S6 评审 | fresh 上下文代码评审；作者 ≠ 评审者（同"写手不审自己文字"） | 评审意见清零或豁免 | 评审记录 |
| S7 交付 | git pull → add/commit → push（钩子强制）；zcode 克隆 git pull | push 成功 + 两处 HEAD 一致 | main 新提交 |

阶段升级棘轮（brainstorming 精神）：隐藏复杂度出现时只升不降——bounded 中途发现要动结构，立即升 architectural、回到 S1。

## 4. SSOT 铁律（本 session 教训的固化，写入 doc 首节）

1. **GitHub main 是唯一母本**；本地唯一编辑点是 novel_wk 工作树；`~/.zcode/local-plugins/ncc-workflow` 是只读消费克隆，改动必须经 GitHub 回流（pull→commit→push），禁止在克隆里就地改了不回推。
2. **引用优于拷贝**：junction 是引用（零同步成本）；一切"安装/复制"都会产生过期副本——需要副本时必须写明它的更新通道。
3. **流程自身一事一源**：SKILL 路由不复制 doc 细节，doc 不复制路由；AGENTS.md 只放指针。
4. **新增产物先问三句**：它的母本在哪？谁是唯一编辑点？副本的更新通道是什么？答不出就先补设计。

## 5. 思想映射与宿主技能借用（doc 内的完整表，技能里只留一行指针）

**思想映射**：每条工程思想在 ncc 里已有原生形态（印证 §0.1 的"翻译"纪律），增量只取三条。

| 工程思想 | ncc 原生形态 | 可借鉴增量 |
|---|---|---|
| 澄清（歧义在便宜时杀死） | 书魂四问、作者种子、类型契约、快捷通道只补问缺口 | 量级棘轮（§0.1） |
| 规格（"完成"写成人人可读的契约） | G0 书魂闸、G1 设定冻结、G2 大纲冻结 | — |
| 设计（小接口藏大实现） | 写作简报=小接口，审稿清单=被藏的实现；场景卡先审结构后产文字 | 删除测试检视技能面 |
| 计划（大跃迁拆可验收小步） | 总纲→卷纲→章纲→场景卡小批量 | — |
| TDD（先写会失败的检验） | 锚定章回归（埋错检测），但目前"改完再测" | **埋错先行**（§0.1） |
| 验证（不跑全套不叫完成） | 改动必跑全量自测；机械检查+硬伤审 | — |
| 评审（作者≠评审者） | 写-审-改分离、写手不看清单、盲读、三层评价不打绝对分 | — |
| SSOT（防止真相分叉） | 信息架构七律、book.json 单一状态源、三本账 | — |

**宿主技能借用**：各阶段自带清单任何宿主可用（不依赖外部插件）；宿主装了 superpowers / mattpocock 时点名借用，效果等价或更细。

| 阶段 | 自带清单（任何宿主可用） | 宿主有则借用 |
|---|---|---|
| S0 | 分类问题三选一 + 目的复述 | superpowers:brainstorming |
| S1/S2 | spec 模板 + 深模块词汇表 | mattpocock:to-spec、codebase-design、domain-modeling |
| S3 | 计划骨架（阶段/验收/风险） | superpowers:writing-plans |
| S4 | 红→绿循环 + 小步提交 | superpowers:test-driven-development、mattpocock:tdd |
| S5 | 全量自测命令 + 回归判定 | superpowers:verification-before-completion |
| S6 | 评审清单（接口/测试/SSOT 三问） | mattpocock:code-review、superpowers:receiving-code-review |
| S7 | pull→commit→push 顺序 + 钩子行为说明 | — |

**grill 家族评估**（升级分支专用，2026-10-12 评审）：

| 技能 | 机制 | 评审结论 |
|---|---|---|
| grilling（引擎） | 变更提案建模为决策树；按轮次问"当前可问的全部问题"（frontier），每题附推荐答案、措辞使"是"即采纳；事实由子代理查证、决策留给用户；frontier 清空才算达成共识 | **译入 S1**：质询的完整性判据（frontier 空 = 无默然假设）优于"作者点头了"；事实/决策分工与 ncc"下限系统/上限作者"同构。风险：默认滑移（顺着推荐点头），用 ncc 已有的"否决降权"对冲 |
| grill-me（入口） | 瘦入口调 grilling | 形态印证深模块：入口即接口 |
| grill-with-docs（组合技） | grilling + domain-modeling，质询过程沉淀 ADR 与词汇表 | **译入升级分支的进化提议**：质询结论直接落档，恰好构成自进化"可撤回"所需的证据链 |
| to-questionnaire（近亲） | "质询发送而非主题"：知识在第三方时只问用户能答的（发给谁/要什么），文档瞄准知识缺口 | "只问能答的"是 S0 通用纪律；ncc 角色采访已是同构形态 |
| wait-what（近亲） | 用统一语言重新讲一遍实现复位 | 与 ncc 交接卡/经理复述同构，不新增 |

## 6. 错误处理

- fetch 失败：pre-commit 阻止提交（既有行为）；流程规定先解决网络再走 S7，不允许 --no-verify 绕过拉取
- 私有内容误拦：--no-verify 逃生门仅限确认非书稿，且必须当次修钩子标记
- 测试红在中途：停在该阶段修复，禁止带红进 S6

## 7. 测试与验收

- Phase 验收由 S5 命令承担：check_plugin 必须先确认"新增 skill 是否需要登记"（check_plugin 的一致性规则），若需要则同步登记进它的清单
- 技能文本与 doc 的一致性：人工评审（S6），对照第 4 节铁律逐条过

## 8. 实施阶段划分（交给 writing-plans 展开）

- Phase 1：docs/dev-workflow.md（SSOT 主体）
- Phase 2：skills/ncc-dev + commands/ncc-dev.md + junctions + check_plugin 登记（如需）
- Phase 3：AGENTS.md 指针 + 115 全量 + check_plugin + 提交推送 + zcode 克隆 pull 闭环演示
