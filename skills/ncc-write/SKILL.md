---
name: ncc-write
description: "Use this skill for chapter drafting: S2 opening (golden three chapters, G3 opening gate) and S3 serialized daily chapters. Every chapter runs register → reader-now + pack → draft + ledger write-back → mechanical check (incl. water chapter) → review → revise → re-review → commit."
when_to_use: "User says /ncc-write, 写下一章, 今更N章, 黄金三章, or resume a drafting loop. Do NOT use for outline or settings work."
---

# 写章（S2 开篇 → S3 连载）

每章都是同一条流水线，开篇只是多一道 G3 人工验收、签约点检查与文风校准回填：

```
chapter add → reader-now + 组装上下文包(留档) → writer 草稿 + 三本账回写 → check_chapter.py
  → 机械不过: writer 重写(chapter retry，≤max_retry)
  → 机械过: continuity+pulse 审稿 → editor 按观察修订(如需) → 复评(SHA 重绑)
  → 总分≥70 且无未处置 critical → ncc_state.py complete
```

执行阶段**禁停顿**：写作循环内不问作者问题。循环里遇到的决策点按推荐项执行，登记为 `暂定决策`，到单元复盘时集中呈给作者（guidance §五）。只有 G3 验收、返工满 3 轮、发现设定级矛盾、战略分歧时才回到作者。

## Step 0 — 定位

1. `ncc_state.py status <书目录>` 确认 stage 与断点。`opening` 阶段从第 1 章开始；`serial` 阶段找第一个非 done 章。
2. 章纲缺失（滚动窗没覆盖到）→ 先派 outliner 补该章细纲（轻任务，不重开卷纲），再进循环。章纲必须写明本章计划建立、推进、兑现哪些承诺 id。
3. `writing_mode: batch` 时按批派 writer（每批 3–5 章串行），批间走一次审稿；默认 `serial` 单章循环。

## Step 1 — 登记与上下文包

1. 登记本章：`ncc_state.py chapter add <书目录> <章号> --file 04-正文/第NNNN章-标题.md`，然后 `chapter mark … drafting`。
2. 生成"读者此刻"：`ncc_state.py reader-now <书目录> <章号>`。
3. 按 [../ncc/references/context-pack.md](../ncc/references/context-pack.md) 组装并落档 `_packs/ch-XXXX.json`（读者此刻进 protected 层）。无包不写。开篇的包额外带：`author-intent.md` 的类型契约与签约点分配、目标读者画像。

## Step 2 — 派 writer

task: draft。写手按 [references/chapter-loop.md](references/chapter-loop.md) 的每章工艺执行，开篇额外按 [references/golden-three.md](references/golden-three.md)。写完后写手负责回写：

- 承诺：`promise add / touch / resolve`（本章至少建立、推进或兑现一条读者向承诺）；
- 知情：`know add / learn`（新的信息差、角色得知真相）；
- 世界：`fact set`（本章新出现或引用的距离、物价、称谓等）；状态事件按 book-state.md 格式追加；
- 章节：`chapter hook`（章尾钩子）、`chapter mood`（压抑／释放／平）；开篇章用 `sign` 登记落地的签约点。

## Step 3 — 机械检查

`python3 <PLUGIN_ROOT>/scripts/check_chapter.py <书目录> <章号>`：汉字字数、章尾钩子登记、AI 味词表、**水章**（本章未建立、推进或兑现任何承诺）。退出码非 0 → writer 重写（`chapter retry`）。

## Step 4 — 审稿与修订（写-审-改分离）

1. 派 continuity（task: audit）＋ pulse（task: pulse），fresh 上下文，按 [../ncc-review/references/review-domains.md](../ncc-review/references/review-domains.md) 的八域累加分制产 observation——**不改稿**。
2. 有需修改项 → 派 editor（task: revise）执行显式修订；正文 SHA 变更后**必须复评**，旧分作废。
3. 连续性审计发现**设定级矛盾**（与圣经、词典、三本账冲突且不是笔误）→ 停，回作者：给"改设定／改本章"的推荐与理由。不允许写手悄悄圆。
4. 审稿问题的处置（改、放行、有意为之）按推荐项执行，放行与有意为之登记为暂定决策，单元复盘时呈给作者。

## Step 5 — 落盘

`ncc_state.py complete <书目录> <章号> --words N --score S --coverage C --report 05-审稿/ch-XXXX-review.md`：状态 done、字数、审稿摘要、承诺汇总刷新。写手同步更新 `current-focus.md` 与设定词典的「首现章」实值。

## 开篇特有（S2 → G3）

1. 三章全过后：第 1 章定稿回填**文风校准段**到 `03-文风/文风基准.md`（写手执行）。
2. 派 reader（task: blind-read）盲评 1–3 章：追读意愿（1–5）、弃读点、划线点，写入 `05-审稿/blind-ch-0001-0003.md`。
3. `ncc_state.py gate <书目录> opening` 检查：三章 done 且过分、盲评已出、五个签约点都在前三章落地。
4. 呈示作者：三章审稿分＋盲评结论＋签约点落地情况 → 过 / 改 / 重写，并给推荐。过 → `--action pass`，`stage: serial`。

## 连载节奏（S3）

- 每章完成即是一个可发布单元；`07-导出/` 由作者手动或要求时生成合稿。
- 存稿：作者可要求「先攒 N 章再更」——batch 模式即为此设计。
- 每个剧情单元（10–40 章）结束：汇总本单元的暂定决策与审稿放行项，按问题卡格式呈给作者（完整单元复盘在 M2-1）。
- 每卷收官：outliner 扩下一卷卷纲与滚动窗，pulse 出卷级节奏复盘（爽点密度、同型重复、弃章风险）（完整卷复盘与 G4 在 M2-1）。
