# 阶段图（registry 的人类可读视图）

唯一事实源：`workflow/registry.json`。本文件是派单时查的速览表；两者冲突时以 registry 为准。

## 主线（主流网文工业流）

```
S0 选题 ──(可跳过,记理由)──▶ S1 设定 ─G1冻结─▶ S2 大纲 ─G2冻结─▶ S3 黄金三章 ─G3验收─▶ S4 连载(写-审-改循环) ─▶ S5 运营复盘(可选)
                                                                  └─ ncc-deconstruct 随时喂设定库 ─┘
```

| 阶段 | 主责角色 | 参与角色 | 产物 | 闸门 |
|---|---|---|---|---|
| S0 选题 | scout | — | 00-策划/briefing.md、对标分析.md | 无（作者口头确认选题） |
| S1 设定 | worldbuilder | deconstructor(喂料) | 世界观圣经、力量体系、设定词典、人物卡/ | **G1** 作者确认冻结 |
| S2 大纲 | outliner | worldbuilder(答疑) | 总纲、卷纲/、章纲/ | **G2** 作者确认冻结 |
| S3 黄金三章 | writer | editor、continuity、pulse、reader | 第1–3章正文、审稿报告、文风基准回填 | **G3** 作者验收 |
| S4 连载 | writer | editor、continuity、pulse | 逐章正文 + 台账回写 | **G-chapter** 每章软门 |
| S5 运营复盘 | scout | — | 数据回流.md | 无 |

## 每章写-审-改循环（S3/S4 共用）

```
组装上下文包(留档) → writer 草稿 → check_chapter.py(机械检查)
  → 不及格: writer 重写(≤3轮)
  → 及格: continuity + pulse 审稿(五域,产 observation) + editor 按observation修订
      → 正文变了: 复评(SHA 重新绑定)
  → 总分≥70 且无未处置 critical: ncc_state.py complete 落盘回写
```

## 角色分工速查

| 角色 | 一句话职责 | 绝不做 |
|---|---|---|
| scout | 扫榜、对标、briefing | 写设定 |
| worldbuilder | 世界观圣经、力量体系、设定词典、人物卡 | 编情节 |
| outliner | 总-卷-章三级大纲、情绪曲线、50章滚动窗 | 写正文 |
| writer | 按上下文包写章、黄金三章 | 审自己的稿 |
| editor | 执行修订、去AI味、对齐文风锚点 | 产审稿结论 |
| continuity | 设定冲突/时间线/伏笔义务审计，只产 observation | 改稿 |
| pulse | 张力波峰/情绪点/钩子强度/三维节奏评分 | 改稿 |
| reader | 盲评（不给大纲设定）：追读意愿、弃读点 | 看任何生产材料 |
| deconstructor | 按总纲5.0拆对标书，喂设定库 | 写本书正文 |

fresh 标记：continuity、pulse、reader 为无记忆新上下文——派单包不含生产材料。
