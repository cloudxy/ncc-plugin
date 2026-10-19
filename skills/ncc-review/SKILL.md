---
name: ncc-review
description: "Independent hard-defect and story review, typed P1–P5 quality scoring with evidence, bounded revision, and key-chapter pairwise comparison. SHA freshness binding and mandatory re-review after changes. Reviewers never draft or approve their own output."
when_to_use: "User says /ncc-review, 审第N章, 打回重写, 全书体检, 比一比这两版, or asks for a quality pass on chapters."
---

# 审稿与修订闭环（三层评价）

设计来源：Openwrite 的审稿 DAG（证据锚点／SHA 绑定／强制复评）＋ InkOS 的「审计产 observation、修订是显式独立动作」＋ sdlc-workflow 的「产出者不批准」铁律 ＋ v0.3 的三层评价（D13）。

每份AI创作成果按类型评分，提供分项、原文证据、总分和处理建议；规则唯一见[AI内容评分与自动处理](references/quality-scoring.md)。分数是当前量表下的模型评价，硬伤、故事审和作者权限各自保留。关键章仍做版本比较与读者记忆测试。

| 层 | 审什么 | 谁审 | 什么时候 | 输出 |
|---|---|---|---|---|
| 硬伤层 | 连贯逻辑、正典一致、情节承诺（承诺推进、知情越权、场景卡的翻转与两难是否写出来）、角色关系中有据可查的 OOC、契约（毒点、签约点）、底蕴（知识点清单是否写对、有无出处、时代错置与称谓）、AI 味 | 常规章：continuity 一人（含契约与毒点）＋脚本；兑现章、关键章、开篇：加 pulse（D17，`review plan` 给结论） | 每章，正文写完后 | 通过／不通过＋定位 |
| 故事层 | 场景卡：翻转、两难、目标情感、风险升级、人物欲望与需要、意料之外情理之中、一个画面 | story-editor（关键章作者过目） | 每章，**正文写之前**（见 ncc-write Step 2） | 通过／退回＋推荐改法 |
| 品质层 | 按P1–P5量表评估当前成果 | pulse的quality任务独立评分；关键章另做成对比较与reader记忆测试 | 每份AI成果 | 分项、证据、总分、路由；关键章另给比较理由 |

八个检查类别（D11）保留在 [references/review-domains.md](references/review-domains.md)，分别归入上面三层。

**章定稿闸** ＝ 硬伤层通过 ∧ 场景卡已过故事审且之后未改动 ∧（关键章）作者已选定版本 ∧ 评审SHA与正文一致 ∧ AI正文有当前有效评分且达标或作者明确选稿。`complete`检查这些绑定；严重硬伤与缺证据不能靠高分绕过。

## 流程

1. **定位**：章号或范围；读 book.json 确认正文 sha、是否关键章、场景卡状态。
2. **硬伤层**：先 `ncc_state.py review plan` 定派谁并存快照；continuity（task: audit）必派，pulse（task: pulse）按计划参加，fresh 上下文；派单头用 `brief --role continuity|pulse --seq N`（只带本角色的约定与误报漏检记录，不带作者的会话）。每条 observation：`{类别, 严重度: critical|major|minor, 正文引用, 推荐处置与理由}`。
3. **汇总**：经理合成 `05-审稿/ch-XXXX-review.md`：硬伤层结论（通过／不通过）、可判定率（能下结论的检查项占比，<0.8 视为不通过）、observation 清单。记 review.sha。
4. **修订**：有 critical 或 major → 派 editor（task: revise）显式修订。**正文一变 SHA 即变，旧评审作废**：`ncc_state.py review delta` 列出改动的段落，由上次给出不通过项的审稿人只复审这些段落与那几项，更新审稿报告。minor 可留到卷末统一打磨。
5. **品质层**：经理生成quality评分包，pulse以quality任务提供分项与证据；脚本重新计算总分并按统一规则推进有限返修，最多两次总修订。关键章另对 `04-正文/_versions/` 做成对比较，reader按[读者画像](references/reader-personas.md)做记忆测试，作者一次选定版本。接入正文后核对硬伤和评分新鲜度。
6. **打回重写**：审稿判"章级失败"（场景卡里的翻转或两难没写出来、结构问题）→ 先改场景卡、重过故事审，再 `chapter retry` 重写；达上限自动转 failed，停呈作者并给推荐处置。
7. **全书体检**（`全书` 参数；卷复盘时也可调用）：抽样章（首 3、中段、最新 3）＋台账体检——承诺逾期与到期暂定决策（`ncc_state.py status`）、水章、没有翻转的场景比例、知情台账与正文不符、知识台账冲突、状态事件断档、孤儿词条、文风漂移、同型爽点与同色情绪重复。
8. **两版比较**（作者说"比一比这两版"）：直接走第 5 步的成对比较。

9. **文风放行**：作者认定"有意为之"的原句，按 `../ncc/references/craft-canon.md` 的"文风诊断八问"写进 `03-文风/放行清单.md`（附章号与理由），机械检查不再计入。
10. **读者画像与热力**（M6-2）：开篇至少 2 个画像各读一遍；各画像的反应用 `feedback add --persona` 登记，`ncc_state.py heat` 合成弃读热力；"我在等什么"与 `reader-now` 对照，看承诺台账准不准。

## 边界

- 审稿帽不改稿；editor 不产审稿结论。修订依据只能是 observation 清单。
- 审稿报告是唯一评审记录；口头意见不进状态。
- 评分与比较分别留证据；新稿、量表或关键依赖变化后重评，不复制旧分。
- 审稿清单只在审稿侧；不要把它塞进写手的上下文（写作简报与质检清单分离）。
