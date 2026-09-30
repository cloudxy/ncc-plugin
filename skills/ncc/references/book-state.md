# book.json 与三本账：状态源

设计来源：chinese-novelist-skill 的「单一 JSON 状态机」＋ InkOS 的「权威 JSON，MD 只是投影」。**正文与 markdown 文件永不回写状态；状态只由 `scripts/ncc_state.py` 和经理派单回收时写入。** 架构说明见 `workflow/architecture.md`。

## 状态机（schema 2）

```
书:  founding → settings → outline → opening → serial ⇄ volume → finale → finished
章:  pending → drafting → drafted → checking → reviewing → revising → done | failed
闸门: soul / settings_frozen / outline_frozen / opening_accepted（volume、finale 于 M2）
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
  "writing_mode": "serial | batch",
  "experience_level": "新手 | 熟手 | 老手",
  "soul": {"question": "", "answer": "", "injustice": "", "ending": "", "status": "未填|暂定|确定", "deadline": "第一卷卷复盘"},
  "contract": {"main": "凡人逆袭＋守护", "extras": [], "poison": ["主角降智"], "signing": {"主角与欲望": 1}},
  "gates": {"soul": {"status": "passed", "at": "…", "quote": "立书"}, "settings_frozen": {}, "outline_frozen": {}, "opening_accepted": {}},
  "chapters": [
    {
      "seq": 1,
      "file": "04-正文/第0001章-雨夜地铁.md",
      "status": "done",
      "word_count": 3480,
      "hook": {"type": "悬念", "intensity": 4, "line": "一句话"},
      "mood": "压抑 | 释放 | 平",
      "retry": 0,
      "sha": "…正文sha256前16位…",
      "review": {"score": 78, "coverage": 0.9, "report": "05-审稿/ch-0001-review.md", "sha": "…评审时正文sha…"},
      "pack": "04-正文/_packs/ch-0001.json"
    }
  ],
  "promises": {"open": 12, "resolved": 3, "dropped": 0, "overdue": 0, "options": 2, "pending_decisions": 1},
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

- 类型：伏笔（id 前缀 FS）、悬念、爽点欠账、人物弧、感情线、卷目标、期权、暂定决策（前缀 TD，必须有 `deadline`：章号或节点名）。
- 期权、暂定决策不计入水章判定，也不进"读者在等什么"。
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
  "reason": "吞服…", "evidence": "5–15 字定位词"}]}
```

## 规则

1. **SHA 新鲜度**：`review.sha` 必须 == 当前正文 `sha`。不等 = 评审作废，必须复评。
2. **恢复协议**：`resume` 时按 stage＋第一个非 done 章节定位断点；`drafting/reviewing` 状态的章按「文件存在＋字数＋sha」重建事实，不信内存。
3. **重写计数**：`chapter retry` 达 `max_retry`（默认 3）自动转 `failed`，呈报作者，不自动第 4 轮。
4. **章节登记**：每章动笔前 `chapter add`；写完登记 `chapter hook`（`check_chapter.py` 要查）与 `chapter mood`；审完 `complete`。
5. **v0.1 书**：`ncc_state.py migrate` 升级到 schema 2（原伏笔台账保留）。
6. **book.json 损坏**：按文件存在性＋check_chapter.py 重建，重建后 diff 给作者看一眼。

## 目录契约

```
{book_root}/{书名}/
  book.json               # 唯一状态源
  author-intent.md        # L0：书魂、类型契约、签约点、目标读者、终局（写给所有帽）
  current-focus.md        # 近1-3章焦点，writer 每章更新
  00-策划/  briefing.md  对标分析.md  变更提议.md  数据回流.md
  01-设定/  世界观圣经.md  力量体系.md  设定词典.md  规则表.md  人物卡/
  02-大纲/  总纲.md  卷纲/卷1.md  章纲/ch-0001.md
  03-文风/  文风基准.md
  04-正文/  第0001章-标题.md  _packs/ch-0001.json
  05-审稿/  ch-0001-review.md  blind-ch-0001-0003.md
  06-台账/  承诺台账.json  知情台账.json  知识台账.json  状态事件.json  冲突登记.md  待校验池.md
  07-导出/
  memory/  manager.md  writer.md  editor.md  …（每帽一份）
```
