# book.json：单一状态源

设计来源：chinese-novelist-skill 的「单一 JSON 状态机」（进度/恢复/校验四合一）＋ InkOS 的「权威 JSON，MD 只是投影」。**正文与 markdown 文件永不回写状态；状态只由 ncc_state.py 和经理派单回收时写入。**

## 状态机

```
书:  ideation → settings → outline → golden → serial → finished
章:  pending → drafting → drafted → checking → reviewing → revising → done | failed
闸门: G1 settings_frozen / G2 outline_frozen / G3 golden_accepted —— 各自 {status: waiting|passed|rejected, at, quote}
```

## 字段

```json
{
  "schema_version": 1,
  "title": "书名",
  "genre_tags": ["都市", "诡异"],
  "premise": "一句话前提",
  "target": {"chapters": 300, "words_per_chapter": [3000, 5000]},
  "stage": "golden",
  "writing_mode": "serial | batch",
  "gates": {
    "settings_frozen": {"status": "passed", "at": "2026-09-29", "quote": "冻结"},
    "outline_frozen": {"status": "waiting"},
    "golden_accepted": {"status": "waiting"}
  },
  "chapters": [
    {
      "seq": 1,
      "file": "04-正文/第0001章-雨夜地铁.md",
      "status": "done",
      "word_count": 3480,
      "hook": {"type": "悬念", "intensity": 4},
      "retry": 0,
      "sha": "…正文sha256…",
      "review": {"score": 78, "coverage": 0.9, "critical": 0, "report": "05-审稿/ch-0001-review.md", "sha": "…评审时正文sha…"},
      "pack": "04-正文/_packs/ch-0001.json"
    }
  ],
  "foreshadows": {"total": 12, "resolved": 3, "overdue": 0},
  "host_spawn": false,
  "updated_at": "2026-09-29T10:00:00"
}
```

## 规则

1. **SHA 新鲜度**：`review.sha` 必须 == 当前正文 `sha`。不等 = 评审作废，必须复评（Openwrite 的 stale 机制）。
2. **恢复协议**：`resume` 时按 stage + 第一个非 done 章节定位断点；`drafting/reviewing` 状态的章按「文件存在 + 字数 + sha」重建事实，不信内存。
3. **重写计数**：`retry ≥ 3` 的章转 `failed`，呈报作者，不自动第 4 轮。
4. **状态事件**：设定/人物/关系的变更不写进 book.json，写 `06-台账/状态事件.json`（事件溯源，见总纲 5.0）：`{entity, chapter, attribute, old, new, reason, evidence}`。
5. **伏笔统计**：`foreshadows` 由脚本从 `06-台账/伏笔台账.json` 汇总，经理不手填。
6. **book.json 损坏**：按文件存在性 + check_chapter.py 重建（chinese-novelist-skill 的兜底策略），重建后 diff 给作者看一眼。

## 目录契约

```
{book_root}/{书名}/
  book.json               # 唯一状态源
  author-intent.md        # 长期创作意图（写给所有帽）——InkOS 控制文档
  current-focus.md        # 近1-3章焦点，writer 每章更新
  00-策划/  briefing.md  对标分析.md  数据回流.md
  01-设定/  世界观圣经.md  力量体系.md  设定词典.md  规则表.md  人物卡/
  02-大纲/  总纲.md  卷纲/卷1.md  章纲/ch-0001.md
  03-文风/  文风基准.md
  04-正文/  第0001章-标题.md  _packs/ch-0001.json
  05-审稿/  ch-0001-review.md  blind-ch-0001-0003.md
  06-台账/  伏笔台账.json  状态事件.json  冲突登记.md  待校验池.md
  07-导出/
  memory/  manager.md  writer.md  editor.md  …（每帽一份）
```
