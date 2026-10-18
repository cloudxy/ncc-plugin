# 拆书有限结构契约

唯一机器源位于 `workflow/contracts/deconstruction/*.json`，格式为 `ncc-structure-1`，由运行校验与字段表生成共用。支持 object/array/string/integer/boolean/any、required/nullable/const/enum/vocab、fields/items、additional=false、整数 minimum/maximum、字符串或数组 min_length/max_length；不支持完整 JSON Schema。未声明 default 的字段不自动补值；数组内 entry 是入库逐条校验规则，条目失败被隔离，不整章拒收。

文件层识别章号、版本、hash、包和根结构；十类基础集合必须显式给出，空集合必须有依据，缺项会保留有效条目但不记基础完成。screenplay 对象结构与逐场语义单独验收，不因场次未通过把基础完成混写成场次完成。附加契约不替代作者提供的总纲5.0，未声明扩展字段原样保存在原始章中，不自动进入活跃台账或 L3 投影。

错误码：成功0；结构、证据、过期输入、范围、锁或写入错误1；argparse 参数错误2。文件级阻塞不写 done，原因另存入库报告；条目级失败留丢弃/待校验/冲突记录；有效收据是原子提交点，恢复重新派生台账并最后写进度。所有版本和词表指纹绑定原始机器契约；变更后旧包须重新生成。

兼容策略：旧 done/skipped 仅作 legacy 覆盖；新层必须由 ingest 验收。原文/规则变更先生成重建影响，--accept-reindex 显式重建并备份索引与进度，不猜 seq 映射。--force 不绕过结构 blocker。原始章文件替换前保留备份，不自动迁移真实书库。

公开最小对象和反例由 `scripts/tests/fixtures/deconstruction/README.md` 与 `scripts/tests/test_deconstruction.py` 提供；测试由作者另行执行，未运行不称通过。索引配置和上下文来源示例见技能 references/layers.md 与 packet.md。

<!-- ncc:gen decon-contracts 开始（scripts/dev/build_docs.py 由 workflow/contracts/deconstruction/ 生成，勿手改） -->
## chapter

| 字段 | 类型 | 必填 | 可空 | 默认/缺省 | 枚举/约束 | 说明 |
|---|---|---|---|---|---|---|
| schema_version | integer | 是 | 否 | 不自动补值 | 1 | 本次附加契约版本 |
| chapter | integer | 是 | 否 | 不自动补值 |  | 章节索引 seq |
| chapter_hash | string | 是 | 否 | 不自动补值 |  | 索引正文 hash |
| packet_fingerprint | string | 是 | 否 | 不自动补值 |  | 派单包指纹 |
| summary | string | 否 | 否 | 不自动补值 |  | 自写概括，可缺省 |
| empty_reason | string | 否 | 否 | 不自动补值 |  | 所有事实均不适用时的明确说明 |
| entities | array | 否 | 否 | 不自动补值 |  | 总纲 5.0 对应条目，逐条语义验证，未给出时不伪造 |
| entities[条目].evidence | any | 是 | 否 | 不自动补值 |  | 5–15 字定位词，或含 locator 的对象；语义校验必做 |
| entities[条目].confidence | string | 是 | 否 | 不自动补值 | vocab:confidence | 事实置信级 |
| entities[条目].chapter | integer | 否 | 否 | 不自动补值 |  {'minimum': 1} | 必须为本章 seq |
| entities[条目].description | string | 否 | 否 | 不自动补值 |  | 自写说明 |
| entities[条目].content | string | 否 | 否 | 不自动补值 |  | 自写内容 |
| entities[条目].entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| entities[条目].entity_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| entities[条目].subject | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| entities[条目].object | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| entities[条目].source_entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| entities[条目].target_entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| entities[条目].source_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| entities[条目].target_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| entities[条目].participants | array | 否 | 否 | 不自动补值 |  | 实体 ID / local_id 数组 |
| entities[条目].characters | array | 否 | 否 | 不自动补值 |  | 实体 ID / local_id 数组 |
| entities[条目].name | string | 是 | 否 | 不自动补值 |  {'min_length': 1} | 实体专名或章内称呼 |
| entities[条目].id | string | 否 | 是 | 不自动补值 |  | 已知 ID；新实体留空/null |
| entities[条目].local_id | string | 否 | 否 | 不自动补值 |  | 本章唯一局部引用 |
| entities[条目].category | string | 否 | 否 | 不自动补值 |  | setting_categories 类目或别名；未知归未归类 |
| entities[条目].aliases | array | 否 | 否 | 不自动补值 |  | 专名/同指证据候选，逐个验收 |
| entities[条目].is_new | boolean | 否 | 否 | 不自动补值 |  | 同名不同实体时显式为 true |
| entities[条目].power_source | any | 否 | 否 | 不自动补值 |  | 可缺省；有值转状态事件，不作为底卡冲突 |
| entities[条目].power_mode | string | 否 | 否 | 不自动补值 | ['change', 'coexist'] | 同点多源并存须标 coexist |
| relations | array | 否 | 否 | 不自动补值 |  | 总纲 5.0 对应条目，逐条语义验证，未给出时不伪造 |
| relations[条目].evidence | any | 是 | 否 | 不自动补值 |  | 5–15 字定位词，或含 locator 的对象；语义校验必做 |
| relations[条目].confidence | string | 是 | 否 | 不自动补值 | vocab:confidence | 事实置信级 |
| relations[条目].chapter | integer | 否 | 否 | 不自动补值 |  {'minimum': 1} | 必须为本章 seq |
| relations[条目].description | string | 否 | 否 | 不自动补值 |  | 自写说明 |
| relations[条目].content | string | 否 | 否 | 不自动补值 |  | 自写内容 |
| relations[条目].entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| relations[条目].entity_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| relations[条目].subject | string | 是 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| relations[条目].object | string | 是 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| relations[条目].source_entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| relations[条目].target_entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| relations[条目].source_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| relations[条目].target_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| relations[条目].participants | array | 否 | 否 | 不自动补值 |  | 实体 ID / local_id 数组 |
| relations[条目].characters | array | 否 | 否 | 不自动补值 |  | 实体 ID / local_id 数组 |
| relations[条目].type | string | 是 | 否 | 不自动补值 |  {'min_length': 1} | 关系说明 |
| events | array | 否 | 否 | 不自动补值 |  | 总纲 5.0 对应条目，逐条语义验证，未给出时不伪造 |
| events[条目].evidence | any | 是 | 否 | 不自动补值 |  | 5–15 字定位词，或含 locator 的对象；语义校验必做 |
| events[条目].confidence | string | 是 | 否 | 不自动补值 | vocab:confidence | 事实置信级 |
| events[条目].chapter | integer | 否 | 否 | 不自动补值 |  {'minimum': 1} | 必须为本章 seq |
| events[条目].description | string | 是 | 否 | 不自动补值 |  {'min_length': 1} | 本章事件概括 |
| events[条目].content | string | 否 | 否 | 不自动补值 |  | 自写内容 |
| events[条目].entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| events[条目].entity_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| events[条目].subject | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| events[条目].object | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| events[条目].source_entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| events[条目].target_entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| events[条目].source_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| events[条目].target_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| events[条目].participants | array | 否 | 否 | 不自动补值 |  | 实体 ID / local_id 数组 |
| events[条目].characters | array | 否 | 否 | 不自动补值 |  | 实体 ID / local_id 数组 |
| state_events | array | 否 | 否 | 不自动补值 |  | 总纲 5.0 对应条目，逐条语义验证，未给出时不伪造 |
| state_events[条目].evidence | any | 是 | 否 | 不自动补值 |  | 5–15 字定位词，或含 locator 的对象；语义校验必做 |
| state_events[条目].confidence | string | 是 | 否 | 不自动补值 | vocab:confidence | 事实置信级 |
| state_events[条目].chapter | integer | 否 | 否 | 不自动补值 |  {'minimum': 1} | 必须为本章 seq |
| state_events[条目].description | string | 否 | 否 | 不自动补值 |  | 自写说明 |
| state_events[条目].content | string | 否 | 否 | 不自动补值 |  | 自写内容 |
| state_events[条目].entity | string | 是 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| state_events[条目].entity_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| state_events[条目].subject | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| state_events[条目].object | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| state_events[条目].source_entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| state_events[条目].target_entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| state_events[条目].source_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| state_events[条目].target_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| state_events[条目].participants | array | 否 | 否 | 不自动补值 |  | 实体 ID / local_id 数组 |
| state_events[条目].characters | array | 否 | 否 | 不自动补值 |  | 实体 ID / local_id 数组 |
| state_events[条目].attribute | string | 是 | 否 | 不自动补值 |  {'min_length': 1} | 状态属性 |
| state_events[条目].new | any | 是 | 否 | 不自动补值 |  | 新值；数值必须给 unit |
| state_events[条目].old | any | 否 | 否 | 不自动补值 |  | 可缺省，不臆造前值 |
| state_events[条目].unit | string | 否 | 否 | 不自动补值 |  {'min_length': 1} | 量纲或无量纲 |
| state_events[条目].time | any | 否 | 否 | 不自动补值 |  | 明确时点；缺省按本章比较 |
| state_events[条目].mode | string | 否 | 否 | 不自动补值 | ['change', 'coexist'] | change 或显式并存 coexist |
| foreshadows | array | 否 | 否 | 不自动补值 |  | 总纲 5.0 对应条目，逐条语义验证，未给出时不伪造 |
| foreshadows[条目].evidence | any | 是 | 否 | 不自动补值 |  | 5–15 字定位词，或含 locator 的对象；语义校验必做 |
| foreshadows[条目].confidence | string | 是 | 否 | 不自动补值 | vocab:confidence | 事实置信级 |
| foreshadows[条目].chapter | integer | 否 | 否 | 不自动补值 |  {'minimum': 1} | 必须为本章 seq |
| foreshadows[条目].description | string | 否 | 否 | 不自动补值 |  | 自写说明 |
| foreshadows[条目].content | string | 否 | 否 | 不自动补值 |  | 自写内容 |
| foreshadows[条目].entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| foreshadows[条目].entity_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| foreshadows[条目].subject | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| foreshadows[条目].object | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| foreshadows[条目].source_entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| foreshadows[条目].target_entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| foreshadows[条目].source_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| foreshadows[条目].target_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| foreshadows[条目].participants | array | 否 | 否 | 不自动补值 |  | 实体 ID / local_id 数组 |
| foreshadows[条目].characters | array | 否 | 否 | 不自动补值 |  | 实体 ID / local_id 数组 |
| foreshadows[条目].id | string | 是 | 否 | 不自动补值 |  {'min_length': 1} | 伏笔稳定 ID |
| foreshadows[条目].op | string | 是 | 否 | 不自动补值 |  | registry.decon.foreshadow_ops |
| emotion_points | array | 否 | 否 | 不自动补值 |  | 总纲 5.0 对应条目，逐条语义验证，未给出时不伪造 |
| emotion_points[条目].evidence | any | 是 | 否 | 不自动补值 |  | 5–15 字定位词，或含 locator 的对象；语义校验必做 |
| emotion_points[条目].confidence | string | 是 | 否 | 不自动补值 | vocab:confidence | 事实置信级 |
| emotion_points[条目].chapter | integer | 否 | 否 | 不自动补值 |  {'minimum': 1} | 必须为本章 seq |
| emotion_points[条目].description | string | 否 | 否 | 不自动补值 |  | 自写说明 |
| emotion_points[条目].content | string | 否 | 否 | 不自动补值 |  | 自写内容 |
| emotion_points[条目].entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| emotion_points[条目].entity_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| emotion_points[条目].subject | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| emotion_points[条目].object | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| emotion_points[条目].source_entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| emotion_points[条目].target_entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| emotion_points[条目].source_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| emotion_points[条目].target_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| emotion_points[条目].participants | array | 否 | 否 | 不自动补值 |  | 实体 ID / local_id 数组 |
| emotion_points[条目].characters | array | 否 | 否 | 不自动补值 |  | 实体 ID / local_id 数组 |
| emotion_points[条目].tension | string | 是 | 否 | 不自动补值 | vocab:tension | 张力 |
| emotion_points[条目].colors | array | 是 | 否 | 不自动补值 |  | 情绪色彩 |
| information_gaps | array | 否 | 否 | 不自动补值 |  | 总纲 5.0 对应条目，逐条语义验证，未给出时不伪造 |
| information_gaps[条目].evidence | any | 是 | 否 | 不自动补值 |  | 5–15 字定位词，或含 locator 的对象；语义校验必做 |
| information_gaps[条目].confidence | string | 是 | 否 | 不自动补值 | vocab:confidence | 事实置信级 |
| information_gaps[条目].chapter | integer | 否 | 否 | 不自动补值 |  {'minimum': 1} | 必须为本章 seq |
| information_gaps[条目].description | string | 是 | 否 | 不自动补值 |  {'min_length': 1} | 读者/人物知情差 |
| information_gaps[条目].content | string | 否 | 否 | 不自动补值 |  | 自写内容 |
| information_gaps[条目].entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| information_gaps[条目].entity_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| information_gaps[条目].subject | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| information_gaps[条目].object | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| information_gaps[条目].source_entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| information_gaps[条目].target_entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| information_gaps[条目].source_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| information_gaps[条目].target_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| information_gaps[条目].participants | array | 否 | 否 | 不自动补值 |  | 实体 ID / local_id 数组 |
| information_gaps[条目].characters | array | 否 | 否 | 不自动补值 |  | 实体 ID / local_id 数组 |
| payoffs | array | 否 | 否 | 不自动补值 |  | 总纲 5.0 对应条目，逐条语义验证，未给出时不伪造 |
| payoffs[条目].evidence | any | 是 | 否 | 不自动补值 |  | 5–15 字定位词，或含 locator 的对象；语义校验必做 |
| payoffs[条目].confidence | string | 是 | 否 | 不自动补值 | vocab:confidence | 事实置信级 |
| payoffs[条目].chapter | integer | 否 | 否 | 不自动补值 |  {'minimum': 1} | 必须为本章 seq |
| payoffs[条目].description | string | 否 | 否 | 不自动补值 |  | 自写说明 |
| payoffs[条目].content | string | 否 | 否 | 不自动补值 |  | 自写内容 |
| payoffs[条目].entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| payoffs[条目].entity_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| payoffs[条目].subject | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| payoffs[条目].object | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| payoffs[条目].source_entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| payoffs[条目].target_entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| payoffs[条目].source_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| payoffs[条目].target_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| payoffs[条目].participants | array | 否 | 否 | 不自动补值 |  | 实体 ID / local_id 数组 |
| payoffs[条目].characters | array | 否 | 否 | 不自动补值 |  | 实体 ID / local_id 数组 |
| payoffs[条目].parts | array | 是 | 否 | 不自动补值 |  | registry.decon.payoff_parts 中的构件 |
| payoffs[条目].setup | integer | 否 | 是 | 不自动补值 |  {'minimum': 1} | 铺垫起始 seq，可空 |
| hooks | array | 否 | 否 | 不自动补值 |  | 总纲 5.0 对应条目，逐条语义验证，未给出时不伪造 |
| hooks[条目].evidence | any | 是 | 否 | 不自动补值 |  | 5–15 字定位词，或含 locator 的对象；语义校验必做 |
| hooks[条目].confidence | string | 是 | 否 | 不自动补值 | vocab:confidence | 事实置信级 |
| hooks[条目].chapter | integer | 否 | 否 | 不自动补值 |  {'minimum': 1} | 必须为本章 seq |
| hooks[条目].description | string | 否 | 否 | 不自动补值 |  | 自写说明 |
| hooks[条目].content | string | 否 | 否 | 不自动补值 |  | 自写内容 |
| hooks[条目].entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| hooks[条目].entity_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| hooks[条目].subject | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| hooks[条目].object | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| hooks[条目].source_entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| hooks[条目].target_entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| hooks[条目].source_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| hooks[条目].target_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| hooks[条目].participants | array | 否 | 否 | 不自动补值 |  | 实体 ID / local_id 数组 |
| hooks[条目].characters | array | 否 | 否 | 不自动补值 |  | 实体 ID / local_id 数组 |
| hooks[条目].type | string | 是 | 否 | 不自动补值 |  {'min_length': 1} | 章尾钩子类型 |
| hooks[条目].intensity | integer | 是 | 否 | 不自动补值 |  {'minimum': 1, 'maximum': 5} | 强度 |
| units | array | 否 | 否 | 不自动补值 |  | 总纲 5.0 对应条目，逐条语义验证，未给出时不伪造 |
| units[条目].evidence | any | 是 | 否 | 不自动补值 |  | 5–15 字定位词，或含 locator 的对象；语义校验必做 |
| units[条目].confidence | string | 是 | 否 | 不自动补值 | vocab:confidence | 事实置信级 |
| units[条目].chapter | integer | 否 | 否 | 不自动补值 |  {'minimum': 1} | 必须为本章 seq |
| units[条目].description | string | 否 | 否 | 不自动补值 |  | 自写说明 |
| units[条目].content | string | 否 | 否 | 不自动补值 |  | 自写内容 |
| units[条目].entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| units[条目].entity_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| units[条目].subject | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| units[条目].object | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| units[条目].source_entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| units[条目].target_entity | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| units[条目].source_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| units[条目].target_id | string | 否 | 否 | 不自动补值 |  | 已有实体 ID 或本章 local_id |
| units[条目].participants | array | 否 | 否 | 不自动补值 |  | 实体 ID / local_id 数组 |
| units[条目].characters | array | 否 | 否 | 不自动补值 |  | 实体 ID / local_id 数组 |
| units[条目].start | integer | 是 | 否 | 不自动补值 |  {'minimum': 1} | 单元起 seq |
| units[条目].end | integer | 是 | 否 | 不自动补值 |  {'minimum': 1} | 单元终 seq |
| screenplay | object | 否 | 否 | 不自动补值 |  | 可选章内场次；计划选中时必须提供，单独按 screenplay/scene 契约验收 |
| empty_collections | object | 否 | 否 | 不自动补值 |  | 空集合名到不适用/未出现依据；也可用全局 empty_reason |

## index

| 字段 | 类型 | 必填 | 可空 | 默认/缺省 | 枚举/约束 | 说明 |
|---|---|---|---|---|---|---|
| schema_version | integer | 是 | 否 | 不自动补值 | 2 | 索引版本 |
| source | string | 是 | 否 | 不自动补值 |  | 原文路径，L3 不读取 |
| sha | string | 是 | 否 | 不自动补值 |  | 原始文件 SHA256 前16位 |
| fingerprint | string | 是 | 否 | 不自动补值 |  | 除自身外规范 JSON SHA256 |
| chapters | array | 是 | 否 | 不自动补值 |  {'min_length': 1} | 唯一章节索引 |
| chapters[].seq | integer | 是 | 否 | 不自动补值 |  {'minimum': 1} | 连续唯一序号 |
| chapters[].no | integer | 是 | 是 | 不自动补值 |  {'minimum': 0} | 原号；特殊序为0，未知为null |
| chapters[].volume | string | 是 | 否 | 不自动补值 |  | 原书卷名，不等于戏剧幕 |
| chapters[].part | string | 是 | 否 | 不自动补值 |  | 同号分章标记 |
| chapters[].title | string | 是 | 否 | 不自动补值 |  | 原始标题 |
| chapters[].start | integer | 是 | 否 | 不自动补值 |  {'minimum': 1} | 1基含章题起始行 |
| chapters[].end | integer | 是 | 否 | 不自动补值 |  {'minimum': 1} | 1基含正文末行 |
| chapters[].hash | string | 是 | 否 | 不自动补值 |  | 正文 LF 规范化 SHA256 前16位 |
| chapters[].han | integer | 是 | 否 | 不自动补值 |  {'minimum': 0} | 正文汉字数 |
| diagnostics | object | 是 | 否 | 不自动补值 |  | warnings/blockers/excluded_ranges |
| act_ranges | array | 是 | 否 | 不自动补值 |  | 显式戏剧幕区间 |

## packet

| 字段 | 类型 | 必填 | 可空 | 默认/缺省 | 枚举/约束 | 说明 |
|---|---|---|---|---|---|---|
| schema_version | integer | 是 | 否 | 不自动补值 | 1 | 本契约格式版本，不能把旧版本当新验收 |
| layer | string | 是 | 否 | 不自动补值 | ['L2', 'L3'] | 本次执行层 |
| index_fingerprint | string | 是 | 否 | 不自动补值 |  | 绑定唯一索引 |
| chapter | object | 否 | 否 | 不自动补值 |  | L2 本章唯一索引条目；L3 不提供 |
| chapter.seq | integer | 是 | 否 | 不自动补值 |  {'minimum': 1} | 连续唯一序号 |
| chapter.no | integer | 是 | 是 | 不自动补值 |  {'minimum': 0} | 原号；特殊序为0，未知为null |
| chapter.volume | string | 是 | 否 | 不自动补值 |  | 原书卷名，不等于戏剧幕 |
| chapter.part | string | 是 | 否 | 不自动补值 |  | 同号分章标记 |
| chapter.title | string | 是 | 否 | 不自动补值 |  | 原始标题 |
| chapter.start | integer | 是 | 否 | 不自动补值 |  {'minimum': 1} | 1基含章题起始行 |
| chapter.end | integer | 是 | 否 | 不自动补值 |  {'minimum': 1} | 1基含正文末行 |
| chapter.hash | string | 是 | 否 | 不自动补值 |  | 正文 LF 规范化 SHA256 前16位 |
| chapter.han | integer | 是 | 否 | 不自动补值 |  {'minimum': 0} | 正文汉字数 |
| context | object | 否 | 否 | 不自动补值 |  | 带来源的前情、实体和未回收伏笔，仅 L2 |
| context.available | boolean | 是 | 否 | 不自动补值 |  |  |
| context.mode | string | 是 | 否 | 不自动补值 |  |  |
| context.previous | string | 否 | 是 | 不自动补值 |  |  |
| context.entities | array | 否 | 是 | 不自动补值 |  |  |
| context.foreshadows | array | 否 | 是 | 不自动补值 |  |  |
| context.unread | array | 否 | 否 | 不自动补值 |  |  |
| context.dependencies | array | 否 | 否 | 不自动补值 |  |  |
| context.sources | array | 是 | 否 | 不自动补值 |  |  |
| context.sources[].path | string | 否 | 否 | 不自动补值 |  |  |
| context.sources[].sha256 | string | 是 | 否 | 不自动补值 |  |  |
| context.sources[].field | string | 否 | 否 | 不自动补值 |  |  |
| fingerprint | string | 是 | 否 | 不自动补值 |  | 除自身外的规范 JSON SHA256 |
| artifacts | array | 否 | 否 | 不自动补值 |  | L3 仅包含已验报告与结构化产物 |
| artifacts[].path | string | 是 | 否 | 不自动补值 |  |  |
| artifacts[].sha256 | string | 是 | 否 | 不自动补值 |  |  |
| artifacts[].data | object | 是 | 否 | 不自动补值 |  |  |
| plan_fingerprint | string | 是 | 否 | 不自动补值 |  | 绑定选章及场次计划 |
| vocab_fingerprint | string | 是 | 否 | 不自动补值 |  | 词表、设定类目和机器契约共同指纹 |
| text | string | 否 | 否 | 不自动补值 |  | 仅 L2 本章正文；L3 无此字段 |
| independent | boolean | 否 | 否 | 不自动补值 |  | 章内独立，不写全书事实台账 |
| requires_screenplay | boolean | 否 | 否 | 不自动补值 |  | 本章是否在场次计划内 |
| act | string | 否 | 否 | 不自动补值 |  | 显式戏剧幕；无则空 |
| framework | object | 否 | 否 | 不自动补值 |  | 实际总纲文件的 path 与 sha256，仅 L2 |
| framework.path | string | 是 | 否 | 不自动补值 |  |  |
| framework.sha256 | string | 是 | 否 | 不自动补值 |  |  |
| sources_fingerprint | string | 否 | 否 | 不自动补值 |  | L3 全部有效验收收据集合指纹，新增冲突也使旧包失效 |

## plan

| 字段 | 类型 | 必填 | 可空 | 默认/缺省 | 枚举/约束 | 说明 |
|---|---|---|---|---|---|---|
| schema_version | integer | 是 | 否 | 不自动补值 | 1 | 本契约格式版本，不能把旧版本当新验收 |
| goal | string | 是 | 否 | 不自动补值 | ['structure', 'technique', 'full', 'transfer'] | 作者明确选择的研究目标 |
| index_fingerprint | string | 是 | 否 | 不自动补值 |  | 绑定唯一索引 |
| selected | array | 是 | 否 | 不自动补值 |  | 已选 L2 seq 去重排序集合 |
| groups | object | 是 | 否 | 不自动补值 |  | 开篇/内部/结局/作者选择分组与理由 |
| screenplay | array | 是 | 否 | 不自动补值 |  | 在已选 L2 集合中另选的场次范围 |
| fingerprint | string | 是 | 否 | 不自动补值 |  | 除自身外的规范 JSON SHA256 |
| rounding | string | 否 | 否 | 不自动补值 |  | rounding |
| reasons | object | 否 | 否 | 不自动补值 |  | reasons |

## progress

| 字段 | 类型 | 必填 | 可空 | 默认/缺省 | 枚举/约束 | 说明 |
|---|---|---|---|---|---|---|
| schema_version | integer | 是 | 否 | 不自动补值 | 2 | 本契约格式版本，不能把旧版本当新验收 |
| index_fingerprint | string | 是 | 否 | 不自动补值 |  | 绑定唯一索引 |
| layers | object | 是 | 否 | 不自动补值 |  | 各层 planned/done/failed/waived，基础与场次分开 |
| done | array | 是 | 否 | 不自动补值 |  | legacy 与可信基本抽取覆盖，不能证明场次完成 |
| skipped | object | 是 | 否 | 不自动补值 |  | 显式 legacy 跳过及理由 |
| legacy | object | 否 | 否 | 不自动补值 |  | 旧覆盖的来源，不能证明新校验已通过 |
| artifacts | object | 否 | 否 | 不自动补值 |  | 每章正文/派单包/验收收据指纹 |
| derived_fingerprints | object | 否 | 否 | 不自动补值 |  | 派生台账文件路径到SHA256；统计前校验 |
| invalidated | object | 否 | 否 | 不自动补值 |  | 重建导致旧 seq 失效的清单，不自动迁移 |

## receipt

| 字段 | 类型 | 必填 | 可空 | 默认/缺省 | 枚举/约束 | 说明 |
|---|---|---|---|---|---|---|
| schema_version | integer | 是 | 否 | 不自动补值 | 1 | 验收收据版本 |
| chapter | integer | 是 | 否 | 不自动补值 |  {'minimum': 1} | 本章seq |
| chapter_hash | string | 是 | 否 | 不自动补值 |  | 正文hash |
| index_fingerprint | string | 是 | 否 | 不自动补值 |  | 索引指纹 |
| packet_fingerprint | string | 是 | 否 | 不自动补值 |  | 派单包指纹 |
| vocab_fingerprint | string | 是 | 否 | 不自动补值 |  | 词表及契约指纹 |
| receipt_fingerprint | string | 是 | 否 | 不自动补值 |  | 原子提交点的完整收据指纹 |
| base_complete | boolean | 是 | 否 | 不自动补值 |  | 必要集合与有效事实已满足 |
| scene_complete | boolean | 是 | 否 | 不自动补值 |  | 场次另行满足 |
| independent | boolean | 是 | 否 | 不自动补值 |  | 章内独立范围 |
| payload | object | 是 | 否 | 不自动补值 |  | 原始章对象，扩展字段保留但不自动生效 |
| ledgers | object | 是 | 否 | 不自动补值 |  | 经过语义验收的全书事实 |
| chapter_facts | object | 是 | 否 | 不自动补值 |  | 经过语义验收的章内事实，独立模式保留在此 |
| collection_status | object | 是 | 否 | 不自动补值 |  | 各集合 verified/partial/uncollected |
| dependencies | array | 是 | 否 | 不自动补值 |  | 实际依赖的前章seq |
| context_sources | array | 是 | 否 | 不自动补值 |  | 上下文真实路径与指纹 |
| scenes | array | 是 | 否 | 不自动补值 |  | 有效场次 |
| errors | array | 是 | 否 | 不自动补值 |  | 基础缺项 |
| scene_errors | array | 是 | 否 | 不自动补值 |  | 场次缺项 |
| rejected | array | 是 | 否 | 不自动补值 |  | 丢弃条目与原因 |
| pending | array | 是 | 否 | 不自动补值 |  | 待校验条目与原因 |
| conflicts | array | 是 | 否 | 不自动补值 |  | 冲突全部断言 |

## scene

| 字段 | 类型 | 必填 | 可空 | 默认/缺省 | 枚举/约束 | 说明 |
|---|---|---|---|---|---|---|
| scene_id | string | 否 | 否 | 不自动补值 |  | 稳定场次 ID，可由入库分配 |
| chapter | integer | 是 | 否 | 不自动补值 |  {'minimum': 1} | 本章 seq |
| order | integer | 是 | 否 | 不自动补值 |  {'minimum': 1} | 从 1 开始的连续顺序 |
| slugline | string | 是 | 否 | 不自动补值 |  | 场头，可为空 |
| int_ext | string | 是 | 否 | 不自动补值 |  | 内外景或未知 |
| place | string | 是 | 否 | 不自动补值 |  | 地点，可为空 |
| time_of_day | string | 是 | 否 | 不自动补值 |  | 时间，可为空 |
| characters | array | 是 | 否 | 不自动补值 |  | 在场实体 ID |
| objective | string | 是 | 否 | 不自动补值 |  | 目标或交代任务，可为空 |
| obstacle | string | 是 | 否 | 不自动补值 |  | 阻碍，可为空 |
| turn | string | 是 | 否 | 不自动补值 |  | 转折，可为空 |
| outcome | string | 是 | 否 | 不自动补值 |  | 落点，可为空 |
| actions | array | 是 | 否 | 不自动补值 |  {'max_length': 4} | 动作概括，最多四条 |
| dialogue | array | 是 | 否 | 不自动补值 |  {'max_length': 6} | 对白意图，最多六条 |
| dialogue[].speaker | string | 是 | 否 | 不自动补值 |  | 说话人/意图/潜台词/定位词 |
| dialogue[].intent | string | 是 | 否 | 不自动补值 |  | 说话人/意图/潜台词/定位词 |
| dialogue[].subtext | string | 是 | 否 | 不自动补值 |  | 说话人/意图/潜台词/定位词 |
| dialogue[].locator | string | 是 | 否 | 不自动补值 |  | 说话人/意图/潜台词/定位词 |
| locator | string | 是 | 否 | 不自动补值 |  | 5–15 字正文定位词 |
| confidence | string | 是 | 否 | 不自动补值 | vocab:confidence | 置信级，引用现有词表 |
| unknown_reason | string | 否 | 否 | 不自动补值 |  | 未知或不适用字段的说明 |

## screenplay

| 字段 | 类型 | 必填 | 可空 | 默认/缺省 | 枚举/约束 | 说明 |
|---|---|---|---|---|---|---|
| act | string | 是 | 否 | 不自动补值 |  | 索引 act_ranges 命中幕名，无则空 |
| logline | string | 是 | 否 | 不自动补值 |  {'min_length': 1} | 自写戏剧任务 |
| scenes | array | 是 | 否 | 不自动补值 |  | 逐场验收；不在文件层丢弃整章 |

## transfer

| 字段 | 类型 | 必填 | 可空 | 默认/缺省 | 枚举/约束 | 说明 |
|---|---|---|---|---|---|---|
| schema_version | integer | 是 | 否 | 不自动补值 | 1 | 本契约格式版本，不能把旧版本当新验收 |
| layer | string | 是 | 否 | 不自动补值 | L3 | 本次执行层 |
| packet_fingerprint | string | 是 | 否 | 不自动补值 |  | 当前派单包指纹 |
| modules | array | 是 | 否 | 不自动补值 |  | 每项写方法、两处证据、适用条件、代价与失效 |
| modules[].method | string | 是 | 否 | 不自动补值 |  |  |
| modules[].applies | string | 是 | 否 | 不自动补值 |  |  |
| modules[].cost | string | 是 | 否 | 不自动补值 |  |  |
| modules[].invalid_when | string | 是 | 否 | 不自动补值 |  |  |
| modules[].evidence | array | 是 | 否 | 不自动补值 |  |  |
<!-- ncc:gen decon-contracts 结束 -->
