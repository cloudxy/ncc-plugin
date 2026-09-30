# 上下文包契约（context pack）

设计来源：Openwrite 的 write 前上下文包预检 ＋ InkOS Composer 的 protected/compressible 分层 ＋ chinese-novelist-skill 的「动笔前最后读的必须是正文语态」。

**无包不写。** 每章动笔前，经理（或 writer 的 pack 任务）组装以下内容并落档到 `04-正文/_packs/ch-XXXX.json`——它同时是写作输入、审稿对照物和事后追溯凭证（InkOS intent/context 留痕思想）。

## writer 包（写手版）

| 分层 | 内容 | 来源 |
|---|---|---|
| protected（必带，不压缩） | ① 本章章纲（含 must-keep / avoid 清单）② 所在卷纲摘要 ③ 伏笔义务清单：本章 due / to_plant / overdue ④ 出场人物卡（仅本章相关）⑤ author-intent.md + current-focus.md | 02-大纲、06-台账/伏笔台账.json、01-设定 |
| compressible（超预算才裁） | ⑥ 设定词典相关条目（按本章关键词 grep）⑦ 前情摘要（前3章各一段） | 01-设定、book.json 摘要区 |
| 锚（最后读） | ⑧ 前一章结尾 500–800 字**原文** ⑨ 文风基准.md（指纹+基准段落+负面清单） | 04-正文、03-文风 |

组装顺序即阅读顺序：先意图与义务，后词典与前情，**最后是正文语态**——让模型带着「上一章的声音」动笔。

## continuity / pulse 审稿包（fresh 版）

- 正文全文 + 本章章纲（对 must-keep 核账）+ 伏笔义务清单 + 设定词典（仅被引条目）。
- **不给**：写手记忆、author-intent 之外的生产讨论、旧评审报告。

## reader 盲评包

- 只有正文。黄金三章验收时给 1–3 章全文；不给大纲、设定、章纲、作者意图。

## 机械检查项（脚本可查，经理组装时先自查）

- 章纲存在且含钩子设计；伏笔清单非空或显式 `无义务`；前一章文件存在。
- 包文件写入 `_packs/` 后记入 book.json 的 `chapter.pack`，正文落盘后 sha 记入 `chapter.sha`。

## 预算

- writer 包总量建议 ≤ 12k 字（中文），超了先裁 ⑥⑦，永不裁 ①②③⑧⑨。
