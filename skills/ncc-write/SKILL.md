---
name: ncc-write
description: "Use this skill for chapter drafting: the golden three chapters (G3 acceptance) and serialized daily chapters. Every chapter runs pack → draft → mechanical check → review → revise → re-review → commit."
when_to_use: "User says /ncc-write, 写下一章, 今更N章, 黄金三章, or resume a drafting loop. Do NOT use for outline or settings work."
---

# 写章（S3 黄金三章 → S4 连载）

每章都是同一条流水线，黄金三章只是多一道 G3 人工验收与文风校准回填：

```
组装上下文包(留档) → writer 草稿 → check_chapter.py
  → 机械不过: writer 重写(≤max_retry)
  → 机械过: continuity+pulse 审稿 → editor 按观察修订(如需) → 复评(SHA 重绑)
  → 总分≥70 且无未处置 critical → ncc_state.py complete 回写
```

执行阶段**禁停顿**：写作循环内不问作者问题；只有 G3 验收、返工 ≥3、发现设定级矛盾时才回到作者。

## Step 0 — 定位

1. `ncc_state.py status <书目录>` 确认 stage 与断点。`golden` 阶段从第 1 章开始；`serial` 阶段找第一个非 done 章。
2. 章纲缺失（滚动窗没覆盖到）→ 先派 outliner 补该章细纲（轻任务，不重开卷纲），再进循环。
3. `writing_mode: batch` 时按批派 writer（每批 3–5 章串行），批间走一次审稿；默认 `serial` 单章循环。

## Step 1 — 组装上下文包

按 [ncc/context-pack.md](../ncc/references/context-pack.md) 组装并落档 `_packs/ch-XXXX.json`。无包不写。黄金三章的包额外带：开篇承诺（briefing 的爽点承诺）与目标读者画像。

## Step 2 — 派 writer

task: draft。写手按 [references/chapter-loop.md](references/chapter-loop.md) 的每章工艺执行。黄金三章额外按 [references/golden-three.md](references/golden-three.md)。

## Step 3 — 机械检查

`python3 <PLUGIN_ROOT>/scripts/check_chapter.py <书目录> <章号>`：汉字字数、章尾钩子登记、AI 味词表命中。退出码非 0 → writer 重写（retry+1）。

## Step 4 — 审稿与修订（写-审-改分离）

1. 派 continuity（task: audit）＋ pulse（task: pulse），fresh 上下文，按 [../ncc-review/references/review-domains.md](../ncc-review/references/review-domains.md) 的五域累加分制产 observation——**不改稿**。
2. 有需修改项 → 派 editor（task: revise）执行显式修订；正文 SHA 变更后**必须复评**（重跑本步），旧分作废。
3. 连续性审计发现**设定级矛盾**（与圣经/词典/台账冲突且不是笔误）→ 停，回作者：改设定还是改本章。不允许写手悄悄圆。

## Step 5 — 落盘回写

`ncc_state.py complete <书目录> <章号> --words N --score S`：状态 done、字数、审稿摘要、伏笔台账新埋/回收同步。写手同步更新 `current-focus.md` 与设定词典的「首现章」实值。

## 黄金三章特有（G3）

1. 三章全过后：第 1 章定稿回填**文风校准段**到 `03-文风/文风基准.md`（写手执行）。
2. 派 reader（task: blind-read）盲评 1–3 章：追读意愿（1–5）、弃读点、划线点。
3. 呈示作者：三章审稿分＋盲评结论 → 过 / 改 / 重写。过 → `stage: serial`，进入日更节奏。

## 连载节奏（S4）

- 每章完成即是一个可发布单元；`07-导出/` 由作者手动或要求时生成合稿。
- 存稿建议：作者可要求「先攒 N 章再更」——batch 模式即为此设计。
- 每卷收官时：outliner 扩下一卷卷纲＋滚动窗，pulse 出卷级节奏复盘（爽点密度/弃章风险），5 章节档给作者。
