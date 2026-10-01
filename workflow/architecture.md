# NCC 架构（v0.5）

五层决策 · 三本账 · 四循环 · 读者模型 · 引导层 · 上限引擎。**下限靠系统，上限靠作者与选择。**设计全文见作者的完善计划（`~/Documents/grok-files/ncc-workflow/2026-09-30-ncc-workflow-完善计划.md`）；本文件是插件内的落地说明，机器可读部分以 `registry.json` 为准。

## 一、五层决策（按可逆度）

| 层 | 内容 | 谁决定 | 怎么改 | 读者信号 |
|---|---|---|---|---|
| L0 书魂 | 书魂四问、类型契约、毒点、终局 | 作者 | G0 书魂闸；开书后只能在卷间闸提变更提议 | 不直接影响 |
| L1 骨架 | 力量体系、地图、势力、暗线、各卷走向 | 作者＋worldbuilder/outliner | G1/G2；冻结后走变更提议，卷间闸拍板 | 经卷复盘间接影响 |
| L2 单元 | 10–40 章的剧情单元 | 作者＋经理 | 滚动窗更新 | 可以 |
| L3 章 | 章纲、场景、钩子 | writer | 章循环 | 可以 |
| L4 文字 | 句子、对话、描写 | writer＋editor | 随时 | 可以 |

**上层约束下层；下层只能提议改上层。** 变更提议格式（经理写入 `00-策划/变更提议.md` 并呈给对应决定人）：

```markdown
## CP-0001（提议层：L1｜提议人：continuity｜第 42 章）
- 改什么：<条目与原文>
- 为什么：<正文证据或读者信号>
- 影响：<已发布章节、承诺台账条目、需复评的章>
- 推荐处置：<按 guidance.md 给推荐与备选>
- 决定：<作者原话｜日期>
```

v0.1 的 `revise-settings` 意图并入此流程：冻结后的设定改动一律走变更提议，留状态事件、标记受影响章节待复评。

## 二、三本账

| 账 | 文件 | 工具 | 回答 |
|---|---|---|---|
| 承诺账 | `06-台账/承诺台账.json` | `ncc_state.py promise` | 我们欠读者什么（伏笔、悬念、爽点欠账、人物弧、感情线、卷目标、期权、暂定决策） |
| 知情账 | `06-台账/知情台账.json`＋设定词典"读者已知／完整真相"栏 | `ncc_state.py know` | 谁知道什么 |
| 世界账 | `06-台账/状态事件.json`、`06-台账/知识台账.json`、`01-设定/` | `ncc_state.py fact`；状态事件由写手回写 | 世界此刻什么样 |

规则：
- **水章**：一章既没建立、推进，也没兑现任何读者向承诺（期权、暂定决策不算）→ `check_chapter.py` 判不过。
- 高强度承诺逾期 → `status` 报警；承诺作废必须写补偿（`promise drop --compensation`）。
- 期权：低成本埋下的含义开放细节，不计逾期；兑现了的改记为伏笔。
- 知情账三规则：打脸前提是读者知道而在场者不知道；反转前提是线索公平；限知视角不泄露视角人物不知道的信息。
- 知识台账：同一事实前后不一致时 `fact set` 拒绝写入，剧情内合理变化须 `--override` 并在正文交代。

## 三、四循环

| 循环 | 频率 | v0.2 状态 |
|---|---|---|
| 章循环 | 每章 | 已有（ncc-write）；v0.2 加读者此刻、水章检测、三本账回写；v0.3 加场景卡与故事审、写作简报、关键章比选 |
| 单元循环 | 10–40 章 | `unit open/close`＋`report unit`；作者集中确认暂定决策、选下一单元走向（loops.md §一） |
| 卷循环 | 每卷 | `volume end`＋`report volume`＋G4：承诺盘点、书魂检验、数据归因、变更提议（loops.md §二） |
| 书循环 | 每本书 | 收束（finale.md，G5）后写全书复盘与跨书技艺库（loops.md §三） |

## 四、读者模型

`ncc_state.py reader-now <书目录> <章号>` 由三本账生成"读者此刻"：知道什么（信息差）、在等什么（强度最高的开放承诺）、情绪在哪（近几章压抑／释放）、可能腻了什么（同型钩子、同型爽点）、到期提醒。它进上下文包的 protected 层。

## 五、引导层

见 `skills/ncc/references/guidance.md`：七步协议、问题卡格式、经验分档、S0–S1 决策点、一句话入口，以及与"执行阶段禁停顿"的关系。

## 六、阶段与闸门（D10）

| 阶段 | registry ID | book.json stage | 闸门 |
|---|---|---|---|
| S0 立书 | S0-founding | founding | G0-soul |
| S1 立骨 | S1-skeleton | settings → outline | G1-settings-frozen、G2-outline-frozen |
| S2 开篇 | S2-opening | opening | G3-opening-accepted |
| S3 连载 | S3-serial | serial | G-chapter |
| S4 卷复盘 | S4-volume | volume | G4-volume |
| S5 收束 | S5-finale | finale → finished | G5-finale |

v0.1 书用 `ncc_state.py migrate` 升级：`ideation→founding`、`golden→opening`、`golden_accepted→opening_accepted`、伏笔台账迁入承诺台账（原文件保留），并补一个待填的书魂闸。

## 七、审稿：三层评价（D13，调整 D11）

八个类别（连贯逻辑、角色关系、情节承诺、节奏爽点、文风表达、正典一致、契约、底蕴）保留为检查项分类，不再合成 100 分：

| 层 | 审什么 | 谁审 | 输出 |
|---|---|---|---|
| 硬伤层 | 可验证的对错：一致性、承诺、场景卡是否落地、知情越权、毒点与签约点、底蕴（知识点是否写对、有无出处） | continuity＋pulse＋脚本 | 通过／不通过 |
| 故事层 | 场景卡：翻转、两难、目标情感、风险升级 | story-editor（关键章作者过目） | 通过／退回（正文之前） |
| 品质层 | 好不好看 | 关键章：成对比较＋读者记忆测试＋作者选定 | 选择与理由，不打分 |

章定稿闸 ＝ 硬伤层通过 ∧ 场景卡已过故事审且未改动 ∧（关键章）作者已选定 ∧ SHA 一致。依据：大模型给创意写作打绝对分与专家相关性接近零（TTCW，CHI 2024）；多个模型彼此一致而不与读者一致（2026 预印本）。

## 八、上限引擎（D12，v0.3）

| 部件 | 落地 |
|---|---|
| U1 作者种子 | `00-策划/作者种子.md`；guidance §〇：推荐标明源自哪条种子 |
| U2 人物引擎 | `skills/ncc-new/references/character.md`；角色采访；主角弧光（`soul --arc`）；`gate settings` 查人物卡 |
| U3 场景层 | `skills/ncc-write/references/scene-card.md`；`scene check/review`；没过故事审不能开写、不能定稿 |
| 写作简报 | `skills/ncc-write/references/writing-brief.md`；写手包不放审稿清单与书魂原文 |
| U4 发散—收敛 | 关键节拍写 2–3 版（`04-正文/_versions/`）→ 成对比较 → 作者 `chapter pick` |
| U5 情感设计 | `chapter mood` 压／放／平＋情绪色（`--colors`）；"失去"记状态事件；reader-now 提示同色重复 |
| U6 经典性元素 | 承诺类型"名场面""母题"；书魂不进写手提示 |
| U7 发展编辑 | `agents/story-editor.md` |
| 写作模式（D15） | `mode` 建筑师／园丁／混合；`gate outline` 按模式检查 |

## 九、循环、收束与作者（M3，v0.4）

| 部件 | 落地 |
|---|---|
| 四循环 | `skills/ncc/references/loops.md`；`unit`、`volume`、`report`；读者数据回流与模拟读者校准（`feedback`） |
| 收束 | `skills/ncc/references/finale.md`；`finale begin`＋`report finale`＋G5 |
| 创作宪法 | `skills/ncc/references/craft-canon.md`：文风诊断八问与放行机制、主体性四问、杂学四通道、文论锚点（写手不读） |
| 机械检查分级 | `check_chapter.py`：五星句式出现即改，其余高危句式与一级词合计限额，二级词只告警，句长起伏只作参考；`03-文风/放行清单.md` |
| 作者可持续 | `skills/ncc/references/sustain.md`：存稿线（`chapter publish`）与保更模式、倦怠信号、噪音隔离、卡文协议 |
| 团队 | `skills/ncc/references/team.md`：`team set`；`NCC_ACTOR`＋操作日志 |

## 十、减重（D16–D18，v0.4.1）

常规章约占八成，按"价值配得上成本"重排：

| 改动 | 做法 | 常规章角色调用 |
|---|---|---|
| 场景卡小批量 | `scene next` 给范围（混合 3、建筑师 5、园丁 2），outliner 一次写、story-editor 一次审（顺带看跨章的升级与重复） | 2 → 约 0.7 |
| 硬伤审合并 | 常规章只派 continuity（含毒点）；`review plan` 判断是否加 pulse（兑现章、关键章、开篇） | 2 → 1 |
| 复审只看改动 | `review delta` 列出快照之后改动的段落，原审稿人只复审这些 | 返工 3 → 2 |
| 写手包脚本组装 | `pack` 按固定顺序组装，审稿文件与书魂原文进不去 | 经理手工 → 0 |

合计：常规章顺利时从 5 次降到约 2.7 次，返工一轮从 8 次降到约 4.7 次；一致性审查、脚本检查、关键章流程不减。

## 十一、底蕴层（M4，v0.5）

**剧情在先，知识随场景来（D3）**；按减重原则按需调用：

| 环节 | 落地 |
|---|---|
| 底蕴卡库 | `skills/ncc/references/domains/`：24 张卡＋README（谁读卡、触发方式、清单格式、场景—学科对照、四通道、45 门学科映射、题材常涉及学科） |
| 触发 | outliner 在场景卡加"知识：…"一栏；`knowledge plan` 判断一批要不要派 scholar（一批最多一次，没有就零成本） |
| scholar | `agents/scholar.md`：本章知识点清单（知识点｜学科｜写成什么｜来源｜状态），核实过的数据进知识台账；立骨时核对设定运转规律 |
| 写手拿什么 | 只拿清单的"写成什么"（待核项附宁缺提示），不拿卡、不拿来源——卡里的典型硬伤与诊断问句是审稿判据（铁律 9） |
| 定稿拦截 | 场景卡标了知识而清单缺失或不合格的章，`complete` 拒绝 |
| 硬伤层 | continuity 按清单与卡核对；`check_chapter.py` 提醒时代错置词（`era` 为古代类时）、敬称谦称用反、月相与日期不符，列出本章用到的知识台账条目 |
| 作者修为 | `study` 登记一书一深学；单元底稿列待核知识点；卷底稿按学科统计知识点、待核与出戏点（`feedback --kind 出戏`），给补学清单（`domains/reading-list.md`） |

