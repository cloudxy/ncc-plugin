---
name: ncc-review
description: "Use this skill for independent review and the revision loop, in three layers (D13): hard-defect layer (pass/fail with body-text evidence), story layer (scene-card review before prose), quality layer (pairwise comparison and reader memory test on key chapters — no absolute scores). SHA freshness binding, mandatory re-review after any body change. Reviewers never produce drafts; revision is an explicit act."
when_to_use: "User says /ncc-review, 审第N章, 打回重写, 全书体检, 比一比这两版, or asks for a quality pass on chapters."
---

# 审稿与修订闭环（三层评价）

设计来源：Openwrite 的审稿 DAG（证据锚点／SHA 绑定／强制复评）＋ InkOS 的「审计产 observation、修订是显式独立动作」＋ sdlc-workflow 的「产出者不批准」铁律 ＋ v0.3 的三层评价（D13）。

**为什么不再打总分**：用大模型给创意写作打绝对分，与专家判断的相关性接近零（TTCW，CHI 2024）；多个模型彼此一致，却不与真实读者一致（Nakayashiki & Watanabe 2026，预印本）。大模型审得了"查得出对错"的硬伤，判不准"好不好看"。所以按"能不能验证"分三层，只有硬伤层给通过／不通过。

| 层 | 审什么 | 谁审 | 什么时候 | 输出 |
|---|---|---|---|---|
| 硬伤层 | 连贯逻辑、正典一致、情节承诺（承诺推进、知情越权、场景卡的翻转与两难是否写出来）、角色关系中有据可查的 OOC、契约（毒点、签约点）、底蕴（M4 起）、AI 味 | 常规章：continuity 一人（含契约与毒点）＋脚本；兑现章、关键章、开篇：加 pulse（D17，`review plan` 给结论） | 每章，正文写完后 | 通过／不通过＋定位 |
| 故事层 | 场景卡：翻转、两难、目标情感、风险升级、人物欲望与需要、意料之外情理之中、一个画面 | story-editor（关键章作者过目） | 每章，**正文写之前**（见 ncc-write Step 2） | 通过／退回＋推荐改法 |
| 品质层 | 好不好看：节奏、语言、人物鲜活度 | 关键章：pulse 做成对比较，reader 做记忆测试，作者定 | 仅关键章 | 选择与理由（不打分） |

八个检查类别（D11）保留在 [references/review-domains.md](references/review-domains.md)，分别归入上面三层。

**章定稿闸** ＝ 硬伤层通过 ∧ 场景卡已过故事审且之后未改动 ∧（关键章）作者已选定版本 ∧ 评审 SHA 与正文一致。`ncc_state.py complete … --hard pass` 会机械检查前三项。

## 流程

1. **定位**：章号或范围；读 book.json 确认正文 sha、是否关键章、场景卡状态。
2. **硬伤层**：先 `ncc_state.py review plan` 定派谁并存快照；continuity（task: audit）必派，pulse（task: pulse）按计划参加，fresh 上下文。每条 observation：`{类别, 严重度: critical|major|minor, 正文引用, 推荐处置与理由}`。
3. **汇总**：经理合成 `05-审稿/ch-XXXX-review.md`：硬伤层结论（通过／不通过）、可判定率（能下结论的检查项占比，<0.8 视为不通过）、observation 清单。记 review.sha。
4. **修订**：有 critical 或 major → 派 editor（task: revise）显式修订。**正文一变 SHA 即变，旧评审作废**：`ncc_state.py review delta` 列出改动的段落，由上次给出不通过项的审稿人只复审这些段落与那几项，更新审稿报告。minor 可留到卷末统一打磨。
5. **品质层（关键章）**：pulse 对 `04-正文/_versions/` 里的版本两两比较（每组说明哪版更好、好在哪、另一版有什么值得保留），reader 对候选版本做记忆测试；经理把结论和推荐呈给作者，作者 `chapter pick` 选定。选中版本接进正文后再过一次硬伤层。
6. **打回重写**：审稿判"章级失败"（场景卡里的翻转或两难没写出来、结构问题）→ 先改场景卡、重过故事审，再 `chapter retry` 重写；达上限自动转 failed，停呈作者并给推荐处置。
7. **全书体检**（`全书` 参数；卷复盘时也可调用）：抽样章（首 3、中段、最新 3）＋台账体检——承诺逾期与到期暂定决策（`ncc_state.py status`）、水章、没有翻转的场景比例、知情台账与正文不符、知识台账冲突、状态事件断档、孤儿词条、文风漂移、同型爽点与同色情绪重复。
8. **两版比较**（作者说"比一比这两版"）：直接走第 5 步的成对比较。

9. **文风放行**：作者认定"有意为之"的原句，按 `../ncc/references/craft-canon.md` §一写进 `03-文风/放行清单.md`（附章号与理由），机械检查不再计入。

## 边界

- 审稿帽不改稿；editor 不产审稿结论。修订依据只能是 observation 清单。
- 审稿报告是唯一评审记录；口头意见不进状态。
- 品质层不产分数，只产"选哪版、为什么"。常规章不做品质层。
- 审稿清单只在审稿侧；不要把它塞进写手的上下文（写作简报与质检清单分离）。
