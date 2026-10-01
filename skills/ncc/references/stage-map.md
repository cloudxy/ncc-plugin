# 阶段图（registry 的人类可读视图）

唯一事实源：`workflow/registry.json`。本文件是派单时查的速览表；两者冲突时以 registry 为准。阶段编号按 D10（完善计划第六稿 §6.1）。

## 主线

```
S0 立书 ─G0书魂闸─▶ S1 立骨(设定 ─G1─▶ 大纲 ─G2─) ─▶ S2 开篇 ─G3开篇闸─▶ S3 连载 ⇄ S4 卷复盘(G4) ─▶ S5 收束(G5) ─▶ 完本
                                    └─ ncc-deconstruct 随时喂设定库 ─┘
```

| 阶段 | 层 | 主责角色 | 参与角色 | 产物 | 闸门 |
|---|---|---|---|---|---|
| S0 立书 | L0 | 经理（按 guidance 引导，先问作者种子） | scout（从种子出整本方向候选） | 作者种子.md、briefing.md、author-intent.md（书魂、类型契约）、book.json soul/contract | **G0** 书魂闸，作者签字 |
| S1 立骨·设定 | L1 | worldbuilder | deconstructor（喂料） | 写作模式；世界观圣经（含社会洞察）、力量体系（可用小说底盘做底料）、设定词典、规则表、人物卡与采访、主角弧光；素材卡起头 | **G1** 设定冻结 |
| S1 立骨·大纲 | L1 | outliner | worldbuilder（答疑） | 总纲、卷纲/、章纲/（深浅随模式）、名场面与母题、承诺台账 | **G2** 大纲冻结 |
| S2 开篇 | L2 | writer | outliner、story-editor、editor、continuity、pulse、reader | 第 1–3 章（关键章：场景卡作者过目、多版比选）、审稿报告、盲评与记忆测试、文风基准回填、签约点登记 | **G3** 开篇闸 |
| S3 连载 | L2–L4 | writer | outliner（场景卡）、story-editor（故事审）、editor、continuity、pulse、reader（关键章） | 场景卡＋逐章正文＋三本账回写 | **G-chapter** 章定稿闸 |
| S4 卷复盘 | L1–L2 | story-editor、pulse、outliner | scout（数据归因） | 复盘/卷N.md（承诺盘点、书魂检验、数据归因、变更提议） | **G4** 卷间闸 |
| S5 收束 | L0–L2 | outliner、continuity | story-editor、writer | 收束清单（承诺清算、暗线收拢、书魂回答）、全书复盘、技艺库条目 | **G5** 完本闸 |

book.json 的 `stage`：`founding → settings → outline → opening → serial ⇄ volume → finale → finished`。

## 每章循环（S2/S3 共用）：先审故事，后写文字

```
每批（混合 3 章 / 建筑师 5 / 园丁 1–2）：
  scene next → chapter add ×N → 场景卡(outliner 一次写完) → 故事审(story-editor 一次审完；关键章作者过目)
  → knowledge plan：标了"知识"的章才派 scholar（一次）→ knowledge check
每章：
  pack(脚本组装写手包) → writer 草稿(关键节拍 2–3 版) + 三本账回写 → check_chapter.py(字数/钩子/AI味/水章)
  → review plan(continuity 必派；pulse 仅兑现章/关键章/开篇) → editor 修订 → review delta → 原审稿人只复审改动
  → 关键章: 成对比较(pulse) + 记忆测试(reader) → 作者 chapter pick
  → ncc_state.py complete --hard pass
```

单元（10–40 章）夹在 S3 里：`unit open` → 章循环 → `report unit` 单元复盘 → `unit close`。详见 `loops.md`。

## 角色分工速查

| 角色 | 一句话职责 | 绝不做 |
|---|---|---|
| scout | 扫榜、对标、briefing、从作者种子出 2–3 套整本方向候选 | 写设定 |
| worldbuilder | 世界观圣经、力量体系、设定词典、人物引擎与角色采访、知识台账初值 | 编情节 |
| outliner | 大纲（深浅随模式）、名场面与母题、承诺登记；连载期即写即做场景卡（按需挂知识与素材） | 写正文 |
| story-editor | 发展编辑：场景卡故事审；单元与卷层面提结构问题、给方向 | 打分、写正文 |
| scholar | 按需：本章知识点清单（有来源或标待核）、设定运转规律核对 | 编造事实、写正文 |
| writer | 按写作简报写章；关键节拍写多版；回写三本账 | 审自己的稿、读审稿清单 |
| editor | 执行修订、去AI味、对齐文风锚点 | 产审稿结论 |
| continuity | 硬伤层主审（常规章唯一审稿人，含毒点）：设定冲突/时间线/承诺义务/场景卡是否落地/知情越权/知识台账，只产 observation；复审只看改动 | 改稿、评好坏 |
| pulse | 只在兑现章、关键章、开篇：契约与欠·挣·超·证；关键章的版本成对比较 | 改稿、打绝对分 |
| reader | 盲评（不给大纲设定）：追读意愿、弃读点、记忆测试 | 看任何生产材料 |
| deconstructor | 按总纲5.0拆对标书，喂设定库；质感细节与机制样本、对标书的书魂与契约 | 写本书正文 |

fresh 标记：continuity、pulse、reader 为无记忆新上下文——派单包不含生产材料。
