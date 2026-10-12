# ncc-workflow 开发工作流重建设计（spec）

日期：2026-10-12 ｜ 状态：待作者评审 ｜ 路径：重量级（brainstorming → 本 spec → writing-plans → 分阶段实施）

## 0. 目的与成功标准

为 **开发 ncc-workflow 这个项目**（插件本身的演进）建立一套标准开发工作流，融合 superpowers 生命周期方法与 mattpocock 深模块设计纪律，以 SSOT 为第一原则，claude/codex/zcode/kimi/grok 五端可用。

**不是**：不改小说创作工作流（workflow/registry.json 那套）的业务逻辑；本设计只新增"开发流程层"。

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
| S1 规格 | 意图写成书面 spec | 作者评审通过 spec 文件 | docs/superpowers/specs/…-design.md |
| S2 设计 | 用深模块词汇定接口与 seam；过删除测试 | 设计段落逐段获认可（随 spec 评审） | spec 内设计节 |
| S3 计划 | 分阶段实施计划，每阶段有验收标准 | 计划文件作者过目 | 实施计划（writing-plans 约定） |
| S4 实现 | TDD：先写失败测试（scripts/test_*.py）再实现；小步走 | 新测试红→绿 | 代码 + 测试 |
| S5 验证 | 全量自测 115 + check_plugin；**规则改动**（registry/skills/agents）加跑 ncc-eval 回归 | 全绿 | 验证记录（命令与结果） |
| S6 评审 | fresh 上下文代码评审；作者 ≠ 评审者（同"写手不审自己文字"） | 评审意见清零或豁免 | 评审记录 |
| S7 交付 | git pull → add/commit → push（钩子强制）；zcode 克隆 git pull | push 成功 + 两处 HEAD 一致 | main 新提交 |

阶段升级棘轮（brainstorming 精神）：隐藏复杂度出现时只升不降——bounded 中途发现要动结构，立即升 architectural、回到 S1。

## 4. SSOT 铁律（本 session 教训的固化，写入 doc 首节）

1. **GitHub main 是唯一母本**；本地唯一编辑点是 novel_wk 工作树；`~/.zcode/local-plugins/ncc-workflow` 是只读消费克隆，改动必须经 GitHub 回流（pull→commit→push），禁止在克隆里就地改了不回推。
2. **引用优于拷贝**：junction 是引用（零同步成本）；一切"安装/复制"都会产生过期副本——需要副本时必须写明它的更新通道。
3. **流程自身一事一源**：SKILL 路由不复制 doc 细节，doc 不复制路由；AGENTS.md 只放指针。
4. **新增产物先问三句**：它的母本在哪？谁是唯一编辑点？副本的更新通道是什么？答不出就先补设计。

## 5. 宿主技能映射（doc 内的完整表，技能里只留一行指针）

| 阶段 | 自带清单（任何宿主可用） | 宿主有则借用 |
|---|---|---|
| S0 | 分类问题三选一 + 目的复述 | superpowers:brainstorming |
| S1/S2 | spec 模板 + 深模块词汇表 | mattpocock:to-spec、codebase-design、domain-modeling |
| S3 | 计划骨架（阶段/验收/风险） | superpowers:writing-plans |
| S4 | 红→绿循环 + 小步提交 | superpowers:test-driven-development、mattpocock:tdd |
| S5 | 全量自测命令 + 回归判定 | superpowers:verification-before-completion |
| S6 | 评审清单（接口/测试/SSOT 三问） | mattpocock:code-review、superpowers:receiving-code-review |
| S7 | pull→commit→push 顺序 + 钩子行为说明 | — |

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
