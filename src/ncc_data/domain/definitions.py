"""Ontology seed definitions, independent of persistence and interface code."""

SYSTEM_SCOPE = "00000000-0000-0000-0000-000000000001"

CORE_KINDS = {
    "character": "人物",
    "chapter": "章节",
    "volume": "卷",
    "outline": "大纲",
    "scene": "场景",
    "location": "地点",
    "organization": "组织",
    "item": "器物",
    "source": "来源资料",
    "foreshadow": "伏笔",
    "event": "事件",
    "legacy-file": "受管文件原件",
}

PROPERTIES = {
    **{
        key: {"type": "text", "label": label}
        for key, label in {
            "description": "说明",
            "status": "状态",
            "realm": "境界",
            "unit": "单位",
            "quote": "原文",
            "author": "原作者",
            "edition": "版本",
            "translation": "译文",
            "commentary": "注释",
            "attribution": "归属核实状态",
            "calendar": "历法",
            "limitations": "限制与代价",
            "side_effects": "副作用",
            "habitat": "栖息地",
            "motivation": "动机",
            "voice": "语言风格",
            "beat_type": "节拍类型",
            "legacy_path": "原相对路径",
            "encoding": "编码",
            "content_hash": "内容摘要",
            "mime_type": "媒体类型",
            "knowledge_state": "信念状态",
            "attitude": "表达态度",
            "truth": "世界真假",
            "publication_status": "发布状态",
            "note": "备注",
        }.items()
    },
    **{
        key: {"type": "reference", "label": label}
        for key, label in {
            "parent_id": "所属节点",
            "chapter_id": "叙述章节",
            "proposition_id": "命题",
            "currency_id": "币种",
            "map_id": "地图",
            "last_mentioned": "最后提及章节",
            "reveal_chapter": "揭示章节",
            "source_id": "来源对象",
        }.items()
    },
    **{
        key: {"type": "references", "label": label}
        for key, label in {
            "source_ids": "来源",
            "known_by": "知情角色",
            "actual_chapters": "实际出现章节",
            "observed_chapters": "已观察章节",
            "payoff_chapters": "兑现章节",
        }.items()
    },
    "tags": {"type": "tags", "label": "标签"},
    "aliases": {"type": "tags", "label": "别名"},
    "position": {"type": "integer", "label": "排序", "minimum": 0},
    "strength": {"type": "integer", "label": "强度", "minimum": 0, "maximum": 5},
    "expected_chapter": {"type": "integer", "label": "期望章节", "minimum": 0},
    "amount": {"type": "decimal", "label": "精确数量"},
    "rate": {"type": "ratio", "label": "精确比率"},
    "cost": {"type": "quantity", "label": "数量与单位"},
    "coordinate": {"type": "coordinate", "label": "坐标"},
    "attachment_id": {"type": "attachment", "label": "附件"},
    "secret_note": {"type": "text", "label": "作者秘密", "secret": True},
}

RELATIONS = {
    "owns": {"label": "所有权", "exclusive_target": True},
    "custody": {"label": "保管", "exclusive_target": True},
    "member_of": {"label": "成员归属"},
    "reports_to": {"label": "行政隶属", "acyclic": True},
    "commands": {"label": "指挥", "acyclic": True},
    "secret_controls": {"label": "秘密控制"},
    "appointed": {"label": "任职", "exclusive_target": True},
    "located_in": {"label": "位置", "acyclic": True},
    "appears_in": {"label": "章节关联"},
    "knows": {"label": "认知"},
    "revealed_in": {"label": "读者揭示"},
    "derived_from": {"label": "来源"},
    "payoff": {"label": "兑现"},
}
