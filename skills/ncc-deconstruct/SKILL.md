---
name: ncc-deconstruct
description: "Use this skill to deconstruct benchmark novels per the 小说拆分总纲 5.0 framework: chapter index as the single slicing source, evidence-and-confidence-tagged extraction, event-sourced state ledger, entities tagged with the setting categories; then learn from it: technique cards on overall design, plot and payoff planning, hidden lines, emotion, character, setting construction and prose, plus a benchmark baseline. Feeds the setting vault, lexicon and the cross-book technique library."
when_to_use: "User says /ncc-deconstruct, 拆这本书, 喂设定库, 学这本书怎么写, or provides a novel file to deconstruct. Only books the user legally holds."
---

# 拆书：按目标建立可信索引、骨架、技法与转化

只处理作者合法持有的原文。原文、章文件、台账、报告只放私有拆书库，不进入插件仓库。总纲 5.0 仍须使用作者实际提供的文件，不凭记忆补字段。

## 目标与入口

先读 [分层与选章](references/layers.md)，从作者目标给推荐：看结构为 L0/L1；研究写法为关键章 L2；完整逐章由作者明确选择；已有产物学法为 L3。不要默认逐章全拆或全书场次化。

1. `decon index <库>` 建立唯一 seq/span/hash 索引；警告与结构阻塞分开，--force 不能绕过 blocker。规则/原文改变须核对重建影响，不能沿用错位进度。
2. `decon plan <库> --goal structure|technique|full|transfer` 冻结目标与范围。显式增补用 --select/--reason；场次另用 --screenplay 选范围。
3. L2 先读 [派单包](references/packet.md)，执行 `decon packet <库> <seq> --framework <总纲>`；再按包派 deconstructor。不连续抽样不得把上一抽样章当作紧邻前情。
4. 按 [入库与恢复](references/ingest.md)执行 `decon ingest <库> <章JSON>`，通过之后才记相应层完成。需要场次时另外读 [场次](references/screenplay.md)。
5. `decon coverage <库> --layer L0|L1|L2|L3|screenplay|legacy` 区分覆盖；stats 的范围与样本报告不能冒充全书。断点恢复用 ingest --recover，从已验收章重建派生数据。
6. 只读转化按 [学法与转化](references/transfer.md)执行；所有报告留在拆书库，绝不自动进入本书大纲或正文。

## 完成与交接

产物摘要说明目标、索引指纹、选章/已验范围、基础事实与场次完成、丢弃/弱推断/冲突、统计可用性及下一步。未选章节不是跳过，也不是已拆；文件存在不是验收通过。历史 done/skipped 仅作 legacy 记录，不能证明新增契约已满足。

本地升级实现与作者测试分开记录；不得把未执行的验收报告写为通过。
