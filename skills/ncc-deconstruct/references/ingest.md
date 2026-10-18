# 拆书可信入库与恢复

章 JSON 的附加契约使用 schema_version=1、chapter（seq）、chapter_hash、packet_fingerprint；总纲 5.0 原字段保留。必须显式给出十类集合：entities、relations、events、state_events、foreshadows、emotion_points、information_gaps、payoffs、hooks、units。每条带 evidence（5–15字本章定位词）与 confidence（引用现有词表）；已有实体必须给真实 ID，新实体 id 留空，必要时给 local_id。原文同名不足以合并不同人物。

文件级缺字段、坏 JSON、错包/错章/hash 失配整章阻塞。条目级错词表、无证据、未知实体等留入库报告及丢弃台账；弱推断进入待校验，不冒充活跃事实。全章均失败不能 done；无该类事实用空数组，并在 empty_collections 中按集合名写依据，或用全局 empty_reason 说明其余空集合；缺少必要集合时保留有效条目但不记基础完成。数值状态须量纲，或写明无量纲。

实体 aliases 使用对象 {name,kind:"proper",same_entity:true,evidence}；只有专名且同指有据时归并别名。描述性称谓与不确定称呼待校验；同一别名指向多个实体保留全部冲突，不按先到先得。力量源为空不造冲突；非空成为状态事件，跨章变化正常；同章并存需 mode=coexist，同一时点不相容断言全部待核对。

入库持有单库写锁，先原子保存章文件，再原子替换验收收据，收据是提交点；派生台账、场次与进度由收据重建，最后写进度。重复执行不追加重复条目；写文件后中断可运行 `decon ingest <库> --recover`。恢复依赖索引/输入/收据指纹，不能按文件存在跳过。

基础事实和场次分别记录。新契约章的 mark --done 只核实已验产物，不绕过 ingest；显式豁免用 mark --skip N --why ... --layer L2|screenplay。旧 done/skipped 继续可读为 legacy，但不证明新校验或场次完成。不会在升级插件时自动迁移真实旧库。

契约字段表见 [维护文档](../../../docs/designs/deconstruction/contracts.md)，由机器契约生成；代码不另抄枚举。对标报告与台账均私有，不进入插件仓库。

章内局部引用用 local_id；同名新实体须 is_new=true，不靠名称猜合并。实体类目引用 setting_categories，未知按未归类保留。独立模式的已验事实只留章级产物，不写全书事实台账；样本报告和 L3 投影必须披露该范围。
