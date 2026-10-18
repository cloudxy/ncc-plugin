# 拆书分层与选章

L0 是机械索引，所有模式必做；L1 是机械骨架，字数/卷章/引号比例只能证明结构数据，不自动得出人物弧光、事件或爽点判断。缺语义概括时明确列缺项，额外阅读范围与成本单列。

目标：structure 只做 L0/L1；technique 深拆关键章；full 由作者明确选择后逐章基础抽取，场次另选；transfer 只消费已有已验报告。

默认关键章为开篇前10章、七个内部八等分点、结局后10章，去重排序。内部位置为 1 + round(k*(N-1)/8)，k=1..7，Python 正中取偶；短书分组可重叠，长篇去重后不超过27章。作者可用 --select 1-3,10 --reason 明确增补或改选；不把未选章写成 skipped。full 不默认全书场次化；显式 --screenplay 指定范围。

索引 seq 连续唯一，原文章号 no、卷 volume、分章 part 原样保留。特殊序章 no=0，自定义无号标题 no=null。原号缺口/短章可警告；零正文、无法区分的重号、重叠边界阻塞。需要缩进或站点规则时用索引配置，人工边界逐项写理由，不用 --force 放过结构错误。

索引文件仍为索引/chapter_index.json；配置默认为索引/index_config.json，可包含 title_indent、chapter_pattern、exclude_titles、act_ranges。必要时 chapters 给完整显式 start/end/title/no/volume/part/reason 边界列表。修改原文/切片后先看重建影响报告，--accept-reindex 备份旧索引及进度并清除错位覆盖，不自动迁移 seq。

每层覆盖独立；L2 计划完成不等于全书逐章完成，基础事实完成不等于场次完成。统计先核对覆盖、字段缺项和口径；稀疏样本不报告全书密度或最长连续压抑，范围报告不覆盖全书基线。

索引配置可用 `--config <JSON>`，默认读取库内 `索引/index_config.json`。例如：

```json
{"title_indent": 0, "exclude_ranges": [{"start": 1, "end": 2, "reason": "人工确认的站点页眉"}], "act_ranges": [{"name": "第一幕", "start": 1, "end": 8, "source": "人工核对的戏剧分幕"}]}
```

chapter_pattern 为可选整行正则；exclude_titles 仅排除明确标题回声。人工 chapters 数组逐项提供 start/end（1基、含章题与正文末行）、title/no/volume/part/reason；未知原号用 null。切片之外有非空原文会阻塞，必须纳入章节或逐段说明 exclude_ranges，不能静默丢前言/卷引。原文或规则变动先看重建影响，再显式 --accept-reindex；旧 seq 进度不自动续接。

`--select` 替换本计划的 L2 集合，必须写 --reason；欲增补请传完整合并集合。`--screenplay none` 可显式不选场次；完整逐章默认不展开场次，另用范围指定。未选择章不是 skipped。
