# 对标场次附加层

仅处理计划要求的章节。章文件追加 screenplay:{act,logline,scenes}，不改变原5.0字段。volume 是原书卷标，不自动等于 act；act 来自显式 act_ranges，无分幕时为空。

地点、时间或戏剧任务明显变化时分场；纯交代可压成一场。每场给 chapter、order、slugline、int_ext、place、time_of_day、characters、objective、obstacle、turn、outcome、actions、dialogue、locator、confidence。scene_id 按 seq/order 稳定分配。目标/阻碍/转折/落点不适用可留空，补 unknown_reason，不能为填字段编转折。int_ext 为内、外、内/外或未知。

动作概括最多4条；对白意图最多6条，每条有 speaker（本场实体ID）、intent、subtext、locator。潜台词不明可空。场次和对白定位词都须在本章，5–15字；自写概括与对白意图连续复抄超过15字拒绝，定位词另作受限证据。弱推断场次待校验，不记完成。

仅有效场次进入剧本/场次.jsonl与人读稿；坏场次保留原因。基础事实验收与场次验收分开；场次计划未完成不能称研究计划全部完成。对标场次留拆书库，不导出到作者的02-大纲/场景卡，不替代 story-editor 审核。
