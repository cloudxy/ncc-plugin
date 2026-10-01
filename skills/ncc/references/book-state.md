# 书项目的信息架构：状态源、视图与目录

设计来源：chinese-novelist-skill 的「单一 JSON 状态机」＋ InkOS 的「权威 JSON，MD 只是投影」＋ ncc 信息架构七律（`workflow/principles.md`）。**每类信息只有一个源头；别处要用就由脚本生成视图，不手抄、不"同步"；源头只有一个写者；历史只追加。**

## 信息地图（唯一源头、写者、视图）

| 信息 | 唯一源头 | 谁写、怎么写 | 在哪看（生成的视图，勿手改） |
|---|---|---|---|
| 阶段、闸门、章节状态、写作模式、档位、时代背景 | `book.json` | 只经 `ncc_state.py`（gate、chapter、mode、level、era…） | `status` |
| 书魂四问、主角弧光 | `book.json` 的 `soul` | 作者拍板后 `soul` | `author-intent.md` |
| 类型契约、毒点、目标读者、签约点 | `book.json` 的 `contract` | 作者拍板后 `contract`（含 `--audience`）、`sign` | `author-intent.md` |
| 作者雷点、偏好、否决过的推荐 | `{书库}/_作者/偏好.json` | `pref like/confirm/reject/dislike` | `pref show`；雷点也进 `author-intent.md` |
| 承诺（伏笔、悬念、爽点欠账、名场面、母题、期权、暂定决策） | `06-台账/承诺台账.json` | `promise add/touch/resolve/reschedule/drop` | `06-台账/承诺台账.md`（含名场面清单、核心意象）；大纲里只写编号 |
| 谁知道什么 | `06-台账/知情台账.json` | `know add/learn` | `06-台账/知情台账.md` |
| 数据：距离、物价、历法、称谓、数值 | `06-台账/知识台账.json` | `fact set`（同键改值要 `--override`） | `06-台账/知识台账.md`；世界观圣经只写规则与关系，提到数据写键 |
| 人物与世界的变化（历史） | `06-台账/状态事件.json`，只追加 | `event add`（不手改 JSON；`check` 查历史有没有被改写） | `event list`；"读者此刻"里的"最近失去了什么" |
| 每章结束时的时间、地点、下一章要接的事 | `book.json` 的 `chapters[].end` | `chapter end` | `current-focus.md`（续写状态卡） |
| 每章要发生的事 | `02-大纲/场景卡/ch-NNNN.md`（作者与 outliner 写） | outliner 起草，过故事审 | 写手包、`current-focus.md` 的"近三章" |
| 设定（世界、力量、专名、规则、人物） | `01-设定/` 各文件 | worldbuilder；冻结后走变更提议 | — |
| 作者自己的材料 | 作者种子 `00-策划/作者种子.md`；素材卡 `素材/`、`{书库}/_作者/素材/` | 经理按作者原话记；素材卡不复制种子 | 写手包 |
| 读者反馈（真实与模拟） | `05-审稿/读者数据.json` | `feedback add` | `heat`、复盘底稿 |
| 复盘与收束里的数据 | 由台账现算 | `report … --write` 写进生成区块 | 复盘文件的生成区块；作者与角色的判断写在区块外 |
| 跨书经验 | `{书库}/_作者/技艺库/<书名>.md` | 完本后 `craft init` 再填 | 下一本书 `craft read` 生成 `00-策划/技艺库摘录.md` |
| 机器工作件（写手包、审稿快照、横评、操作日志、迁移备份） | `.ncc/` | 只由脚本写 | — |

**视图**：`author-intent.md`、`current-focus.md`、`06-台账/承诺台账.md`、`知情台账.md`、`知识台账.md`。每次写操作后脚本自动重新生成；文件开头写着"勿手改"。`ncc_state.py check` 逐字比对视图与源头，手改过或过期都会报出来；`render` 手动重新生成。**脚本从不读视图当输入**（写手包的"前情"从 `book.json` 和场景卡现算）。

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
  "mode": "建筑师 | 园丁 | 混合",
  "era": "古代 | 架空古代 | 近代 | 现代 | 架空现代 | 未来",
  "study": ["天文"],
  "style": {"source": "旧文样本 | 本书第1章", "han": 12000, "at": "…"},
  "writing_mode": "serial | batch",
  "experience_level": "新手 | 熟手 | 老手",
  "soul": {"question": "", "answer": "", "injustice": "", "ending": "", "status": "未填|暂定|确定", "deadline": "第一卷卷复盘", "arc": "正向|负向|平弧"},
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
      "mood": {"tension": "压 | 放 | 平", "colors": ["燃", "悲"]},
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
  "status": "开放 | 推进中 | 已兑现 | 作废",
  "progress": [{"ch": 4, "note": "林家再施压"}], "resolved_ch": null, "compensation": null
}]}
```

- 类型：伏笔（id 前缀 FS）、悬念、爽点欠账、人物弧、感情线、卷目标、名场面（SC）、母题（MT，核心意象）、期权、暂定决策（TD，必须有 `deadline`：章号或节点名）。
- 期权、暂定决策、母题不计入水章判定，也不进"读者在等什么"；名场面计入。
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
4. **字数**：`check_chapter.py` 字数不在区间时返回 needs_decision（退出码 3），不让写手补写；作者收下用 `chapter length --accept`（写章循环里按推荐先收加 `--tentative`，单元复盘列出待确认），超长先 `--compressed` 登记一次只删不加的压缩；正文改过，收下作废。本章区间：场景卡写了"字数范围：A-B"就用它，否则用 `ncc.config.yaml`。写手写完前半段用 `words` 量一次。
5. **章节登记**：每章先 `chapter add`（第 1–3 章默认关键章，其余用 `chapter key` 标注）；场景卡写好后 `scene check`、`scene review`；过了故事审才能 `chapter mark … drafting`；写完登记 `chapter hook`（`check_chapter.py` 要查）、`chapter mood` 与 `chapter end`（结束时的时间、地点、下一章要接的事）；关键章 `chapter pick`；审完 `complete --hard pass`。场景卡在审过之后被改动，要重审。主角失去的东西用 `event add --attr 失去` 记，"读者此刻"会列出最近的失去。
6. **旧书迁移**：`ncc_state.py migrate` 把 schema 1、2 的书升到 3：v0.1 的伏笔台账并入承诺台账（原文件保留）；写手包、快照、横评、操作日志移进 `.ncc/`，读者数据移到 `05-审稿/`，书库根目录的偏好、跨书素材、技艺库移进 `_作者/`；手写过的 `author-intent.md`、`current-focus.md` 移到 `.ncc/迁移备份/`，之后由 `render` 生成。v0.2/v0.3 建的书缺 M3 字段时，脚本在用到时自动补齐。
7. **单元与卷**：`unit open/close`（关单元前须有复盘文件，区块外的判断写完）、`volume end` 后过 `gate volume`；卷通过后下一卷自动从下一章开始。
8. **读者数据**：`feedback add --source 真实|模拟 --kind 追读|弃读|略读|划线|评论|出戏 [--persona 画像]`（出戏的 value 填学科；弃读、略读、划线的 value 填段号，`heat` 按段合成热力）。**知识点清单**：`02-大纲/知识点/ch-NNNN.md`，场景卡标了"知识"的章由 scholar 写；`knowledge check` 校验，`complete` 拦截不合格的。
9. **素材卡**：`素材/` 是作者的生活笔记，不是状态；`material check` 校验三项必填（来源、内容、可用处），场景卡用 `素材：M-NNNN` 引用，`scene check` 查编号存在。
10. **操作日志**：`.ncc/操作日志.jsonl`，每次写操作自动追加（时间、操作者 `NCC_ACTOR`、命令），团队交接用。
11. **自查**：`ncc_state.py check`：视图与源头逐字一致、状态事件只追加、没有旧布局残留；世界观圣经里出现具体数据会提醒挪进知识台账。
12. **book.json 损坏**：按文件存在性＋check_chapter.py 重建，重建后 diff 给作者看一眼。

## 目录契约

```
{book_root}/{书名}/
  book.json               # 状态源头（只有脚本写）
  author-intent.md        # 视图：书魂、类型契约、目标读者、签约点、作者雷点（render 生成，勿手改）
  current-focus.md        # 视图：续写状态卡（render 生成，勿手改）
  00-策划/  作者种子.md  技艺库摘录.md（craft read 生成）  briefing.md  对标分析.md  变更提议.md  收束清单.md  复盘/单元-U1.md 卷1.md 全书.md
  01-设定/  世界观圣经.md  力量体系.md  设定词典.md  规则表.md  时代错置词.md（可选）  人物卡/（含 <名字>-采访.md）
  02-大纲/  总纲.md  卷纲/卷1.md  章纲/ch-0001.md  场景卡/ch-0001.md  知识点/ch-0001.md
  03-文风/  文风基准.md（语感、校准段、负面清单；进写手包）  文风指纹.json（style 生成；只给审稿与脚本）  放行清单.md
  04-正文/  第0001章-标题.md  _versions/ch-0001-<节拍>-A.md（关键节拍的多版，作者比选）
  05-审稿/  story-ch-0001.md  ch-0001-review.md  blind-ch-0001-0003-<画像>.md  读者数据.json
  06-台账/  承诺台账.json  知情台账.json  知识台账.json  状态事件.json（源头）  承诺台账.md  知情台账.md  知识台账.md（视图）
  07-导出/  <书名>-第M-N章.md|txt|epub（export；只收已定稿的章）
  素材/  甲-爽感/ 乙-人间/ … 辛-想象/ 未分/  M-0001-短名.md（素材卡，material add；见 ncc-new/references/material.md）
  memory/  manager.md  writer.md  editor.md  reader.md（校准备注）…（每帽一份；作者偏好与否决不记这里）
  .ncc/  写手包/ch-0001.md  快照/ch-0001.md  横评/ch-0001/  操作日志.jsonl  迁移备份/（机器工作件，脚本写）

{book_root}/_作者/                       # 关于作者本人的跨书资产
  偏好.json                              # pref：权重衰减、否决降权、雷点
  素材/<八域>/MS-0001-短名.md            # 跨书共用的素材卡（material add --shared）
  技艺库/<书名>.md                       # 跨书技艺库（craft init 生成模板；下一本书 craft read）
```
