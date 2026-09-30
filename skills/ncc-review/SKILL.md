---
name: ncc-review
description: "Use this skill for independent review and the revision loop: five-domain additive scoring with body-text evidence anchors, SHA freshness binding, mandatory re-review after any body change. Reviewers never produce drafts; revision is an explicit act."
when_to_use: "User says /ncc-review, 审第N章, 打回重写, 全书体检, or asks for a quality pass on chapters."
---

# 审稿与修订闭环

设计来源：Openwrite 的审稿 DAG（累加分制/证据锚点/SHA 绑定/强制复评）＋ InkOS 的「审计产 observation、修订是显式独立动作」＋ sdlc-workflow 的「产出者不批准」铁律。

## 五域累加分制（总分 100）

| 域 | 分值 | 审什么 | 主审 |
|---|---|---|---|
| 连贯逻辑 | 20 | 因果、时间线、设定一致 | continuity |
| 角色关系 | 15 | 动机、口吻、关系演变、OOC | continuity |
| 情节承诺 | 20 | 章纲 must-keep 兑现、伏笔义务（due/to_plant）、词典「读者已知」不超前 | continuity |
| 节奏爽点 | 15 | 张力波峰、情绪点强度、钩子、三维节奏 | pulse |
| 文风表达 | 15 | AI 味、句式、对话占比、文风锚对齐 | pulse（editor 复查） |
| 正典一致 | 15 | 与世界观圣经/力量体系/规则表冲突 | continuity |

**计分规则（防失真，Openwrite 机制）**：
1. 只有**引用正文原句**的 evaluated 准则计分；凭印象的断言不计分。
2. 问题**不扣分**——分数衡量做对了多少；问题进 observation 清单。
3. 覆盖率独立计算：inconclusive 的准则降低覆盖率、不降分。
4. critical 问题（设定级矛盾、伏笔义务违约、OOC 主角）只改 gate_status（blocked），不动分。

**通过** = 总分 ≥ pass_score（默认 70）∧ 覆盖率 ≥ 0.8 ∧ 无未处置 critical ∧ 评审 SHA == 当前正文 SHA。

## 流程

1. **定位**：章号或范围；读 book.json 确认正文 sha。
2. **派审**：continuity（task: audit）＋ pulse（task: pulse）并行，fresh 上下文。各域产 observation：`{域, 严重度: critical|major|minor, 正文引用, 建议}`。
3. **汇总**：经理（或 pulse）合成 `05-审稿/ch-XXXX-review.md`：五域得分＋总分＋覆盖率＋observation 清单＋gate_status。记 review.sha。
4. **修订**：有 major/critical → 派 editor（task: revise）显式修订。**正文一变 SHA 即变，旧评审作废**——重跑第 2–3 步复评。minor 可留给下一卷统一打磨。
5. **打回重写**：作者或审稿判「章级失败」（必须清单未兑现/结构问题）→ 章状态回 drafting，writer 拿新章纲重写，retry+1；≥3 轮停呈作者。
6. **全书体检**（`全书` 参数）：抽样章（首3/中段/最新3）＋台账体检——伏笔超期、状态事件断档、孤儿词条、文风漂移（平均句长/对话占比趋势）。

## 边界

- 审稿帽不改稿；editor 不产审稿结论。修订依据只能是 observation 清单。
- 审稿报告是唯一评审记录；口头意见不进状态。
- reader 盲评（黄金三章/关键章）独立于五域：只答「追不追、在哪弃、哪里划线」，不评分域。
