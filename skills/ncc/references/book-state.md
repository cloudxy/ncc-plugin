# book.json 与三本账：状态源

设计来源：chinese-novelist-skill 的「单一 JSON 状态机」＋ InkOS 的「权威 JSON，MD 只是投影」。**正文与 markdown 文件永不回写状态；状态只由 `scripts/ncc_state.py` 和经理派单回收时写入。** 架构说明见 `workflow/architecture.md`。

## 状态机（schema 2）

```
书:  founding → settings → outline → opening → serial ⇄ volume → finale → finished
章:  pending →(场景卡过故事审)→ drafting → drafted → checking → reviewing → revising →(硬伤层通过；关键章作者选定)→ done | failed
闸门: soul / settings_frozen / outline_frozen / opening_accepted / volume（每卷一次）/ finale
      各自 {status: waiting|passed|rejected, at, quote[, forced_over]}
```

## book.json 字段

```json
{
  "schema_version": 2,
  "title": "书名",
  "genre_tags": ["都市", "诡异"],
  "premise": "一句话前提",
  "target": {"chapters": 300, "words_per_chapter": [3000, 5000]},
  "stage": "opening",
  "mode": "建筑师 | 园丁 | 混合",
  "era": "古代 | 架空古代 | 近代 | 现代 | 架空现代 | 未来",
  "study": ["天文"],
  "writing_mode": "serial | batch",
  "experience_level": "新手 | 熟手 | 老手",
  "soul": {"question": "", "answer": "", "injustice": "", "ending": "", "status": "未填|暂定|确定", "deadline": "第一卷卷复盘", "arc": "正向|负向|平弧"},
  "contract": {"main": "凡人逆袭＋守护", "extras": [], "poison": ["主角降智"], "signing": {"主角与欲望": 1}},
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
      "scenes": {"count": 2, "review": "passed | revise | pending", "by": "story-editor | author", "at": "…", "sha": "…场景卡sha…"},
      "selection": {"version": "B", "note": "B 的反转更意外", "by": "author", "at": "…"},
      "retry": 0,
      "drafting_at": "…", "done_at": "…",
      "sha": "…正文sha256前16位…",
      "review": {"hard": "pass", "decidable": 0.9, "report": "05-审稿/ch-0001-review.md", "sha": "…评审时正文sha…"},
      "pack": "04-正文/_packs/ch-0001.md"
    }
  ],
  "units": [{"id": "U1", "start": 1, "end": 24, "title": "工厂夜班", "status": "closed"}],
  "volumes": [{"n": 1, "start": 1, "end": 120, "status": "closed"}, {"n": 2, "start": 121, "end": null, "status": "open"}],
  "published_upto": 118,
  "team": {"主编": "作者", "主笔": "小李"},
  "promises": {"open": 12, "resolved": 3, "dropped": 0, "overdue": 0, "options": 2, "motifs": 2, "pending_decisions": 1},
  "host_spawn": false,
  "updated_at": "2026-09-30T10:00:00"
}
```

`promises` 是承诺台账的汇总，由脚本计算，不手填。

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

设定词典的"读者已知／完整真相／计划揭示章"栏继续管专有名词；知情台账管剧情事实在读者与各角色之间的分布。

**知识台账.json**（`ncc_state.py fact`，属世界账）

```json
{"facts": {"青云城到落霞镇": {"value": "三日", "ch": 2, "source": "设定：地理", "category": "距离",
  "history": [{"value": "…", "ch": 1}]}}}
```

类别建议：物价、距离、历法、称谓、数值。同一键写入不同值时脚本拒绝，除非 `--override`。

**状态事件.json**（写手回写，事件溯源，见总纲 5.0）

```json
{"events": [{"entity": "陆言", "chapter": 12, "attribute": "境界", "old": "凡武三重", "new": "凡武四重",
  "reason": "吞服…", "evidence": "5–15 字定位词"},
  {"entity": "陆言", "chapter": 15, "attribute": "失去", "old": "父亲的工作", "new": "无", "reason": "…", "evidence": "…"}]}
```

## 规则

1. **SHA 新鲜度**：`review.sha` 必须 == 当前正文 `sha`。不等 = 评审作废，必须复评。
2. **恢复协议**：`resume` 时按 stage＋第一个非 done 章节定位断点；`drafting/reviewing` 状态的章按「文件存在＋字数＋sha」重建事实，不信内存。
3. **重写计数**：`chapter retry` 达 `max_retry`（默认 3）自动转 `failed`，呈报作者，不自动第 4 轮。
4. **章节登记**：每章先 `chapter add`（第 1–3 章默认关键章，其余用 `chapter key` 标注）；场景卡写好后 `scene check`、`scene review`；过了故事审才能 `chapter mark … drafting`；写完登记 `chapter hook`（`check_chapter.py` 要查）与 `chapter mood`；关键章 `chapter pick`；审完 `complete --hard pass`。场景卡在审过之后被改动，要重审。
   **主角失去的东西**记为状态事件 `attribute: 失去`，"读者此刻"会列出最近的失去。
5. **v0.1 书**：`ncc_state.py migrate` 升级到 schema 2（原伏笔台账保留）。v0.2/v0.3 建的书缺 M3 字段（units、volumes、published_upto、team）时，脚本在用到时自动补齐。
6. **单元与卷**：`unit open/close`（关单元前须有复盘文件）、`volume end` 后过 `gate volume`；卷通过后下一卷自动从下一章开始。
7. **读者数据**：`06-台账/读者数据.json`，`feedback add --source 真实|模拟 --kind 追读|弃读|划线|评论|出戏`（出戏的 value 填学科）。
   **知识点清单**：`02-大纲/知识点/ch-NNNN.md`，场景卡标了"知识"的章由 scholar 写；`knowledge check` 校验，`complete` 拦截不合格的。
8. **操作日志**：`06-台账/操作日志.jsonl`，每次写操作自动追加（时间、操作者 `NCC_ACTOR`、命令），团队交接用。
9. **book.json 损坏**：按文件存在性＋check_chapter.py 重建，重建后 diff 给作者看一眼。

## 目录契约

```
{book_root}/{书名}/
  book.json               # 唯一状态源
  author-intent.md        # L0：书魂、类型契约、签约点、目标读者、终局（写给所有帽）
  current-focus.md        # 近1-3章焦点，writer 每章更新
  00-策划/  作者种子.md  briefing.md  对标分析.md  变更提议.md  收束清单.md  复盘/单元-U1.md 卷1.md 全书.md
  01-设定/  世界观圣经.md  力量体系.md  设定词典.md  规则表.md  时代错置词.md（可选）  人物卡/（含 <名字>-采访.md）
  02-大纲/  总纲.md  卷纲/卷1.md  章纲/ch-0001.md  场景卡/ch-0001.md  知识点/ch-0001.md
  03-文风/  文风基准.md  放行清单.md
  04-正文/  第0001章-标题.md  _packs/ch-0001.md（pack 生成）  _versions/ch-0001-<节拍>-A.md
  05-审稿/  story-ch-0001.md  ch-0001-review.md  blind-ch-0001-0003.md  _snapshots/ch-0001.md（review plan/delta 用）
  06-台账/  承诺台账.json  知情台账.json  知识台账.json  状态事件.json  读者数据.json  操作日志.jsonl  冲突登记.md  待校验池.md
  07-导出/
  memory/  manager.md  writer.md  editor.md  reader.md（校准备注）…（每帽一份）

{book_root}/_craft-library/<书名>.md   # 跨书技艺库（书循环写入，下一本书开书时读）
```
