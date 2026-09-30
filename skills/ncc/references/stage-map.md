# 阶段图（registry 的人类可读视图）

唯一事实源：`workflow/registry.json`。本文件是派单时查的速览表；两者冲突时以 registry 为准。阶段编号按 D10（完善计划第六稿 §6.1）。

## 主线

```
S0 立书 ─G0书魂闸─▶ S1 立骨(设定 ─G1─▶ 大纲 ─G2─) ─▶ S2 开篇 ─G3开篇闸─▶ S3 连载 ⇄ S4 卷复盘(G4) ─▶ S5 收束(G5) ─▶ 完本
                                    └─ ncc-deconstruct 随时喂设定库 ─┘
```

| 阶段 | 层 | 主责角色 | 参与角色 | 产物 | 闸门 |
|---|---|---|---|---|---|
| S0 立书 | L0 | 经理（按 guidance 引导） | scout（出整本方向候选） | briefing.md、author-intent.md（书魂、类型契约）、book.json soul/contract | **G0** 书魂闸，作者签字 |
| S1 立骨·设定 | L1 | worldbuilder | deconstructor（喂料） | 世界观圣经、力量体系、设定词典、规则表、人物卡/ | **G1** 设定冻结 |
| S1 立骨·大纲 | L1 | outliner | worldbuilder（答疑） | 总纲、卷纲/、章纲/、承诺台账（大纲层承诺） | **G2** 大纲冻结 |
| S2 开篇 | L2 | writer | editor、continuity、pulse、reader | 第 1–3 章、审稿报告、盲评、文风基准回填、签约点登记 | **G3** 开篇闸 |
| S3 连载 | L2–L4 | writer | editor、continuity、pulse | 逐章正文＋三本账回写 | **G-chapter** 每章软门 |
| S4 卷复盘 | L1–L2 | pulse、outliner | scout（数据归因） | 卷复盘报告、变更提议 | **G4** 卷间闸（M2） |
| S5 收束 | L0–L2 | outliner、continuity | — | 收束清单（承诺清算） | **G5** 完本闸（M2） |

book.json 的 `stage`：`founding → settings → outline → opening → serial ⇄ volume → finale → finished`。

## 每章写-审-改循环（S2/S3 共用）

```
reader-now + 组装上下文包(留档) → writer 草稿 + 三本账回写 → check_chapter.py(字数/钩子/AI味/水章)
  → 不及格: writer 重写(chapter retry，≤3轮)
  → 及格: continuity + pulse 审稿(八域，产 observation) + editor 按 observation 修订
      → 正文变了: 复评(SHA 重新绑定)
  → 总分≥70 且无未处置 critical: ncc_state.py complete 落盘
```

## 角色分工速查

| 角色 | 一句话职责 | 绝不做 |
|---|---|---|
| scout | 扫榜、对标、briefing、2–3 套整本方向候选 | 写设定 |
| worldbuilder | 世界观圣经、力量体系、设定词典、人物卡、知识台账初值 | 编情节 |
| outliner | 总-卷-章三级大纲、情绪曲线、50章滚动窗、大纲层承诺登记 | 写正文 |
| writer | 按上下文包写章；每章至少建立、推进或兑现一条承诺；回写三本账 | 审自己的稿 |
| editor | 执行修订、去AI味、对齐文风锚点 | 产审稿结论 |
| continuity | 设定冲突/时间线/承诺义务/知情越权/知识台账一致性审计，只产 observation | 改稿 |
| pulse | 张力波峰/情绪点/钩子强度/欠·挣·超·证/三维节奏评分 | 改稿 |
| reader | 盲评（不给大纲设定）：追读意愿、弃读点 | 看任何生产材料 |
| deconstructor | 按总纲5.0拆对标书，喂设定库 | 写本书正文 |

fresh 标记：continuity、pulse、reader 为无记忆新上下文——派单包不含生产材料。
