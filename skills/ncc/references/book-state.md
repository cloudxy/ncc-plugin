# 书项目的信息架构：状态源、视图与目录

设计来源：chinese-novelist-skill 的「单一 JSON 状态机」＋ InkOS 的「权威 JSON，MD 只是投影」＋ ncc 信息架构七律（`workflow/principles.md`）。**每类信息只有一个源头；别处要用就由脚本生成视图，不手抄、不"同步"；源头只有一个写者；历史只追加。**

## 信息地图（唯一源头、写者、视图）

设定、大纲、正文、审稿这些角色产出的文档，各在哪、谁写，见 `book-layout.md` 的"目录契约"。

<!-- ncc:gen info-map 开始（scripts/build_docs.py 由 workflow/registry.json 生成，勿手改） -->
| 信息 | 类别 | 唯一源头 | 谁写、怎么写 | 在哪看 |
|---|---|---|---|---|
| 阶段、闸门、章节状态、写作模式、档位、时代背景 | 源头 | `book.json` | 只经 ncc_state.py（gate、chapter、mode、level、era…） | status |
| 书魂四问、主角弧光 | 源头 | `book.json` 的 `soul` | 作者拍板后 soul | author-intent.md |
| 类型契约、毒点、目标读者、签约点 | 源头 | `book.json` 的 `contract` | 作者拍板后 contract（含 --audience）、sign | author-intent.md |
| 每章结束时的时间、地点、下一章要接的事 | 源头 | `book.json` 的 `chapters[].end` | chapter end | current-focus.md（续写状态卡） |
| 本书用哪些设定类目、本书新提的类目与字段、为什么 | 源头 | `book.json` 的 `setting_categories` | 作者在 G1 确认后 setting use/new/none | setting list |
| 本书的对标书（拆书库里的书名），单元复盘拿它的基线作参照 | 源头 | `book.json` 的 `benchmarks` | decon link | 单元复盘底稿 |
| 作者种子（原话） | 作者 | `00-策划/作者种子.md` | 经理按作者原话记 | 写手包带 #1、#3、#6 |
| 冻结后的变更提议与作者决定（只追加） | 历史 | `00-策划/变更提议.md` | 经理 | — |
| 每章要发生的事：视角、目标、翻转、两难、情感（关键章十项） | 源头 | `02-大纲/场景卡/` | outliner 起草，过故事审 | 写手包；current-focus.md 的近三章 |
| 文风的数字指纹（只给审稿与脚本） | 源头 | `03-文风/文风指纹.json` | style 生成 | — |
| 作者认定有意为之的原句（附章号与理由） | 作者 | `03-文风/放行清单.md` | 作者 | — |
| 读者反馈（真实与模拟，标画像） | 源头 | `05-审稿/读者数据.json` | feedback add | heat；复盘底稿 |
| 承诺：读者在等的事与作者的待定项（类型见词表） | 源头 | `06-台账/承诺台账.json` | promise add/touch/resolve/reschedule/drop | 06-台账/承诺台账.md |
| 谁知道什么（读者与各角色） | 源头 | `06-台账/知情台账.json` | know add/learn | 06-台账/知情台账.md |
| 数据：距离、物价、历法、称谓、数值 | 源头 | `06-台账/知识台账.json` | fact set（同键改值要 --override） | 06-台账/知识台账.md |
| 人物与世界的变化（只追加；指纹记在 book.json） | 历史 | `06-台账/状态事件.json` | event add | event list；读者此刻 |
| 本书素材卡（按八域分目录） | 作者 | `素材/` | material add | material list；写手包 |
| 各角色的本书记忆：约定、教训、手感、校准（<角色>.json 是源头，<角色>.md 是生成的视图；不记作者偏好） | 源头 | `memory/` | memory add/reinforce/merge/archive/restore/promote（经理按角色交回的记忆提议执行） | memory/<角色>.md；派单头（brief）与写手包 |
| 机器工作件：写手包、审稿快照、横评、操作日志、迁移备份 | 工作件 | `.ncc/` | 只由脚本写 | — |
| 写操作日志（团队交接） | 历史 | `.ncc/操作日志.jsonl` | 脚本自动追加 | — |
| 记忆的每次新增、强化、合并、归档、晋升、撤回 | 历史 | `.ncc/记忆日志.jsonl` | memory 命令自动追加 | recall；单元复盘底稿 |
| 会话交接卡：作者在会话里的原话、决定、情绪、待办（只追加，关掉也是追加一条） | 历史 | `.ncc/交接/会话.jsonl` | handoff add/close | handoff list；按角色切进派单头与写手包 |
| 偏好、雷点、否决过的推荐（权重随时间衰减） | 源头 | `{书库}/_作者/偏好.json` | pref like/confirm/reject/dislike | pref show；author-intent.md 的雷点 |
| 跨书共用的素材卡 | 作者 | `{书库}/_作者/素材/` | material add --shared | — |
| 跨书技艺库：每本书一份 | 作者 | `{书库}/_作者/技艺库/` | 完本后 craft init 再填 | 下一本书 craft read |
| 跨书记忆：换一本书也成立的角色经验（<角色>.json 源头＋.md 视图） | 源头 | `{书库}/_作者/记忆/` | memory promote | _作者/记忆/<角色>.md；派单头 |
| 跨书技法库：拆书学来的写法卡，每张带证据、适用条件、代价 | 作者 | `{书库}/_作者/技法库/` | technique add（deconstructor 学法时） | technique list/match；派单头；写手包只带场景卡引用的文笔参考 |
| 技法卡用在哪本书哪一章、结果如何；停用与恢复 | 历史 | `{书库}/_作者/技法库/使用记录.jsonl` | unit close 自动结算；technique result/retire/restore | technique list |
| 作者覆盖层：通过闸门的规则改动（阈值、词表增删、新类目、新技法类别）；插件默认 < 作者覆盖 < 本书设置 | 源头 | `{书库}/_作者/进化/覆盖.json` | evolve apply/revert | evolve rules |
| 进化提议：提出、评测、作者确认、生效、撤回 | 历史 | `{书库}/_作者/进化/提议.jsonl` | evolve propose/eval/apply/reject/revert | evolve list；卷复盘底稿 |
<!-- ncc:gen info-map 结束 -->

**视图**：每次写操作后脚本自动重新生成；文件开头写着"勿手改"。`ncc_state.py check` 逐字比对视图与源头，手改过或过期都会报出来；`render` 手动重新生成。**脚本从不读视图当输入**（写手包的"前情"从 `book.json` 和场景卡现算）。

<!-- ncc:gen views 开始（scripts/build_docs.py 由 workflow/registry.json 生成，勿手改） -->
- `author-intent.md`：书魂、类型契约、目标读者、签约点、作者雷点（render 生成，勿手改）
- `current-focus.md`：续写状态卡：上一章结束在何时何地、下一章要接什么、近三章的翻转、读者此刻（render 生成，勿手改）
- `00-策划/技艺库摘录.md`：别的书里与本书相关的经验（craft read 生成）
- `06-台账/承诺台账.md`：承诺台账，含名场面清单、核心意象（render 生成，勿手改）
- `06-台账/知情台账.md`：知情台账（render 生成，勿手改）
- `06-台账/知识台账.md`：知识台账（render 生成，勿手改）
<!-- ncc:gen views 结束 -->

**生成区块**：复盘与收束文件里，`report … --write` 只重写 `<!-- ncc:生成区块 开始 -->` 到 `<!-- ncc:生成区块 结束 -->` 之间的数据；区块外是作者与角色写的判断，原样保留。关单元、过卷间闸与完本闸只看区块外的内容，还有"（待填）"就不放行。

## 状态机（schema 3）

```
书:  founding → settings → outline → opening → serial ⇄ volume → finale → finished
章:  pending →(场景卡过故事审)→ drafting → drafted → checking → reviewing → revising →(硬伤层通过；关键章作者选定)→ done | failed
闸门: soul / settings_frozen / outline_frozen / opening_accepted / volume（每卷一次）/ finale
      各自 {status: waiting|passed|rejected, at, quote[, forced_over]}
```

## book.json 字段

```json
{
  "schema_version": 3,
  "title": "书名",
  "genre_tags": ["都市", "诡异"],
  "premise": "一句话前提",
  "target": {"chapters": 300, "words_per_chapter": [3000, 5000]},
  "stage": "opening",
  "mode": "混合",
  "era": "架空古代",
  "study": ["天文"],
  "style": {"source": "旧文样本 | 本书第1章", "han": 12000, "at": "…"},
  "writing_mode": "serial | batch",
  "experience_level": "新手",
  "soul": {"question": "", "answer": "", "injustice": "", "ending": "", "status": "暂定", "deadline": "第一卷卷复盘", "arc": "正向"},
  "contract": {"main": "凡人逆袭＋守护", "extras": [], "poison": ["主角降智"], "signing": {"主角与欲望": 1}, "audience": "通勤刷都市文的上班族"},
  "gates": {"soul": {"status": "passed", "at": "…", "quote": "立书"}, "settings_frozen": {}, "outline_frozen": {}, "opening_accepted": {}},
  "chapters": [
    {
      "seq": 1,
      "file": "04-正文/第0001章-雨夜地铁.md",
      "status": "done",
      "key": true,
      "word_count": 3480,
      "hook": {"type": "悬念", "intensity": 4, "line": "一句话"},
      "mood": {"tension": "压", "colors": ["燃", "悲"]},
      "end": {"time": "腊月初三夜里", "place": "保安亭", "next": "去三号库看个究竟"},
      "scenes": {"count": 2, "review": "passed | revise | pending", "by": "story-editor | author", "at": "…", "sha": "…场景卡sha…"},
      "selection": {"version": "B", "note": "B 的反转更意外", "by": "author", "at": "…"},
      "length": {"accepted": 2650, "band": [3000, 5000], "sha": "…收下时正文sha…", "by": "author | recommendation", "compressed": false, "note": "…"},
      "retry": 0,
      "drafting_at": "…", "done_at": "…",
      "sha": "…正文sha256前16位…",
      "review": {"hard": "pass", "decidable": 0.9, "report": "05-审稿/ch-0001-review.md", "sha": "…评审时正文sha…"},
      "pack": ".ncc/写手包/ch-0001.md"
    }
  ],
  "units": [{"id": "U1", "start": 1, "end": 24, "title": "工厂夜班", "status": "closed"}],
  "volumes": [{"n": 1, "start": 1, "end": 120, "status": "closed"}, {"n": 2, "start": 121, "end": null, "status": "open"}],
  "published_upto": 118,
  "team": {"主编": "作者", "主笔": "小李"},
  "history": {"events": {"count": 37, "sha": "…状态事件前 37 条的指纹…"}},
  "host_spawn": false,
  "updated_at": "2026-09-30T10:00:00"
}
```

承诺的开放、逾期等汇总不存进 `book.json`，`status` 与仪表盘现算（派生数据不进权威文件）。

## 三本账（06-台账/）

**承诺台账.json**（`ncc_state.py promise`）

```json
{"items": [{
  "id": "P-0001", "type": "爽点欠账", "content": "退婚之辱当众讨回", "strength": 5,
  "created_ch": 1, "window": [8, 12], "deadline": null, "desire": "1",
  "status": "开放",
  "progress": [{"ch": 4, "note": "林家再施压"}], "resolved_ch": null, "compensation": null
}]}
```

- 类型与编号前缀见 `book-layout.md` 的"词表"。母题即核心意象；暂定决策必须有 `deadline`（章号或节点名）。
- 状态：开放、推进中、已兑现、作废。不面向读者的类型（见 `book-layout.md` 的"词表"）不计入水章判定，也不进"读者在等什么"；名场面计入。
- 逾期：开放中的承诺 `window` 末章 < 当前章；暂定决策的章号 `deadline` < 当前章。
- 作废必须写 `compensation`。

**知情台账.json**（`ncc_state.py know`）

```json
{"items": [{"id": "K-0001", "fact": "主角能看见死亡倒计时", "since_ch": 1,
  "known_by": ["读者", "主角"], "unknown_to": ["林家"], "log": [{"ch": 30, "who": "林家"}]}]}
```

分工：设定词典的"读者已知／完整真相／计划揭示章"管专有名词；知情台账管剧情事实在读者与各角色之间的分布；人物卡的"秘密"写秘密是什么，谁知道它记在知情台账。

**知识台账.json**（`ncc_state.py fact`，属世界账）

```json
{"facts": {"青云城到落霞镇": {"value": "三日", "ch": 2, "source": "设定：地理", "category": "距离",
  "history": [{"value": "…", "ch": 1}]}}}
```

类别建议：物价、距离、历法、称谓、数值。同一键写入不同值时脚本拒绝，除非 `--override`。

**状态事件.json**（`ncc_state.py event add`，只追加，事件溯源见总纲 5.0）

```json
{"events": [{"entity": "陆言", "chapter": 12, "attribute": "境界", "old": "凡武三重", "new": "凡武四重",
  "reason": "吞服…", "evidence": "5–15 字定位词"},
  {"entity": "陆言", "chapter": 15, "attribute": "失去", "old": "父亲的工作", "new": "无", "reason": "…", "evidence": "…"}]}
```

## 规则

1. **SHA 新鲜度**：`review.sha` 必须 == 当前正文 `sha`。不等 = 评审作废，必须复评。
2. **恢复协议**：`resume` 时按 stage＋第一个非 done 章节定位断点；`drafting/reviewing` 状态的章按「文件存在＋字数＋sha」重建事实，不信内存。
3. **重写计数**：`chapter retry` 达 `max_retry`（默认 3）自动转 `failed`，呈报作者，不自动第 4 轮。
4. **字数**：`check_chapter.py` 字数不在区间时返回 needs_decision（退出码 3），怎么处理见 ncc-write 的"Step 5 — 机械检查"。记账：收下 `chapter length --accept [--tentative]`，压缩 `--compressed`；正文改过，收下作废。本章区间：场景卡写了"字数范围：A-B"就用它，否则用 `ncc.config.yaml`。
5. **章节登记**：每章先 `chapter add`（第 1–3 章默认关键章，其余用 `chapter key` 标注）；场景卡写好后 `scene check`、`scene review`；过了故事审才能 `chapter mark … drafting`；写完登记 `chapter hook`（`check_chapter.py` 要查）、`chapter mood` 与 `chapter end`（结束时的时间、地点、下一章要接的事）；关键章 `chapter pick`；审完 `complete --hard pass`。场景卡在审过之后被改动，要重审。主角失去的东西用 `event add --attr 失去` 记，"读者此刻"会列出最近的失去。
6. **旧书迁移**：`ncc_state.py migrate` 把 schema 1、2 的书升到 3：v0.1 的伏笔台账并入承诺台账（原文件保留）；写手包、快照、横评、操作日志移进 `.ncc/`，读者数据移到 `05-审稿/`，书库根目录的偏好、跨书素材、技艺库移进 `_作者/`；手写过的 `author-intent.md`、`current-focus.md` 移到 `.ncc/迁移备份/`，之后由 `render` 生成。v0.2/v0.3 建的书缺 M3 字段时，脚本在用到时自动补齐。
7. **单元与卷**：`unit open/close`（关单元前须有复盘文件，区块外的判断写完）、`volume end` 后过 `gate volume`；卷通过后下一卷自动从下一章开始。
8. **读者数据**：`feedback add --source … --kind … [--persona 画像]`（取值见 `book-layout.md` 的"词表"；出戏的 value 填学科；弃读、略读、划线的 value 填段号，`heat` 按段合成热力）。**知识点清单**：`02-大纲/知识点/ch-NNNN.md`，场景卡标了"知识"的章由 scholar 写；`knowledge check` 校验，`complete` 拦截不合格的。
9. **素材卡**：`素材/` 是作者的生活笔记，不是状态；`material check` 校验必填项（见 `book-layout.md` 的"词表"），场景卡用 `素材：M-NNNN` 引用，`scene check` 查编号存在。
10. **操作日志**：`.ncc/操作日志.jsonl`，每次写操作自动追加（时间、操作者 `NCC_ACTOR`、命令），团队交接用。
11. **自查**：`ncc_state.py check`：视图与源头逐字一致、状态事件只追加、没有旧布局残留；世界观圣经里出现具体数据会提醒挪进知识台账。
12. **book.json 损坏**：按文件存在性＋check_chapter.py 重建，重建后 diff 给作者看一眼。

## 目录契约与词表

每个文件放在哪、是什么、谁写，以及脚本认的取值，见 [book-layout.md](book-layout.md)（由注册表整份生成）。
