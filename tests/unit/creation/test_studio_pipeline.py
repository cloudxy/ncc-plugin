"""Studio catalog, definition extension and explicit pipeline routing. No database."""

import unittest

from pydantic import ValidationError

from ncc_data.creation.worker import explicit_transition, validate_stage_order
from ncc_data.domain.contracts import CreationInput, StudioMarketConfigInput
from ncc_data.domain.definitions import (
    PROPERTIES,
    STUDIO_EXTRA_KINDS,
    merge_system_properties,
)
from ncc_data.domain.studio_catalog import (
    CODEX_GROUPS,
    COMMONS_CATEGORIES,
    MARKET_PLAYBOOKS,
    PIPELINE_PRESETS,
    PUBLIC_COMMONS_CARDS,
    foreshadow_alert_state,
    producer_guidance,
)
from ncc_data.domain.validation import validate_definition, validate_values
from ncc_shared.errors import DomainError
from ncc_shared.quality.policy import POLICY, POLICY_HASH
from ncc_shared.serialization import digest

PINNED_POLICY_HASH = "64633ae314d2460042c3aa2a5ba19ce66700a0b96563bec379299f5e31578ca3"
PRESET_STAGES = {
    "plan_only": ["plan"],
    "plan_and_review": ["plan", "judge_plan"],
    "write_only": ["write"],
    "write_and_judge": ["write", "judge"],
    "write_judge_revise": ["write", "judge", "revise"],
    "judge_only": ["judge"],
    "revise_and_judge": ["revise", "judge"],
    "full_pipeline": ["plan", "judge_plan", "write", "judge", "revise"],
}
NEW_TEXT = {
    "beat_outline",
    "hook",
    "pov",
    "plotline",
    "line_type",
    "arc_type",
    "psychology",
    "factions",
    "commons_category",
    "market_track",
    "usage_guide",
}


class StudioCatalogTest(unittest.TestCase):
    def test_commons_groups_playbooks_and_presets(self):
        labels = [item["label"] for item in COMMONS_CATEGORIES]
        self.assertEqual(
            labels,
            [
                "写作套路",
                "人物描摹",
                "剧情走向",
                "人物弧光",
                "心理分析",
                "关系分析",
                "哲学思考",
                "管理",
                "财务",
                "技术",
                "艺术",
                "环境",
            ],
        )
        for category in COMMONS_CATEGORIES:
            cards = [card for card in PUBLIC_COMMONS_CARDS if card["category"] == category["id"]]
            self.assertGreaterEqual(len(cards), 2, category["id"])
            for card in cards:
                for field in ("id", "category", "title", "summary", "structure", "ai_prompt_hint", "pitfalls", "tags"):
                    self.assertTrue(card[field], card["id"])
        self.assertEqual(len(CODEX_GROUPS), 6)
        for group in CODEX_GROUPS:
            for field in ("id", "label", "description", "kinds", "recommended_fields"):
                self.assertTrue(group[field], group["id"])
        self.assertEqual(
            [item["name"] for item in MARKET_PLAYBOOKS],
            [
                "东方玄幻·苟道长生",
                "东方玄幻·极道横推",
                "诡秘悬疑·规则序列",
                "都市高武·阶层跃迁",
                "历史朝堂·权谋种田",
                "诸天无限·副本双螺旋",
                "西幻魔兽·法师史诗",
            ],
        )
        for playbook in MARKET_PLAYBOOKS:
            for field in (
                "id",
                "name",
                "core_hook",
                "pacing_3_10_30",
                "hook_mix",
                "midgame_trap",
                "poison_list",
                "target_words_band",
            ):
                self.assertTrue(playbook[field], playbook["id"])
            self.assertEqual(len(playbook["target_words_band"]), 2)
        self.assertEqual({item["id"]: item["stages"] for item in PIPELINE_PRESETS}, PRESET_STAGES)

    def test_catalog_refs_reject_unknown_ids(self):
        guidance = producer_guidance(
            {"builtin_commons_ids": ["routine-choice-cost"], "market_playbook_id": "western-mage"},
            {"studio_market": {"playbook_id": "ignored-when-request-names-one"}},
        )
        self.assertEqual(guidance["cards"][0]["id"], "routine-choice-cost")
        self.assertEqual(guidance["playbook"]["id"], "western-mage")
        with self.assertRaises(DomainError):
            producer_guidance({"builtin_commons_ids": ["missing-card"]})


class DefinitionExtensionTest(unittest.TestCase):
    def test_new_properties_validate_and_policy_hash_is_unchanged(self):
        self.assertEqual(POLICY_HASH, PINNED_POLICY_HASH)
        self.assertEqual(POLICY_HASH, digest(POLICY))
        self.assertLessEqual(len(PROPERTIES), 70)
        self.assertTrue(NEW_TEXT <= set(PROPERTIES))
        self.assertEqual(PROPERTIES["key_chapter"]["type"], "boolean")
        self.assertEqual(PROPERTIES["target_words"]["minimum"], 0)
        self.assertEqual(PROPERTIES["planted_chapter"]["minimum"], 0)
        self.assertEqual(len(STUDIO_EXTRA_KINDS), 11)
        for key, label, domain in STUDIO_EXTRA_KINDS:
            spec = {"label": label, "domain": domain, "properties": PROPERTIES, "required": []}
            validate_definition(spec)
            validate_values(
                spec,
                {
                    "beat_outline": "选择、代价、章尾钩",
                    "line_type": "暗线",
                    "key_chapter": True,
                    "target_words": 3200,
                    "planted_chapter": 4,
                },
            )
            self.assertEqual(key, label)
        stored = {"label": "章节", "domain": "叙事生产", "properties": {"description": {"type": "text", "label": "旧说明"}}, "required": []}
        merged = merge_system_properties(stored)
        self.assertEqual(merged["properties"]["description"]["label"], "旧说明")
        self.assertIn("beat_outline", merged["properties"])
        self.assertEqual(merge_system_properties({"relation": True, "label": "成员归属"}), {"relation": True, "label": "成员归属"})
        with self.assertRaises(DomainError):
            validate_values({"properties": PROPERTIES, "required": []}, {"not_a_field": "x"})


class PipelineContractTest(unittest.TestCase):
    def test_creation_input_stays_compatible_and_checks_stages(self):
        legacy = CreationInput(objective="续写")
        self.assertIsNone(legacy.stages)
        self.assertEqual(legacy.guidance, "")
        self.assertEqual(legacy.beat_outline, "")
        self.assertEqual(legacy.commons_refs, [])
        self.assertEqual(legacy.builtin_commons_ids, [])
        self.assertIsNone(legacy.market_playbook_id)
        self.assertEqual(legacy.max_revisions, 2)
        self.assertEqual(legacy.mode, "create")
        explicit = CreationInput(objective="只出细纲", stages=["plan", "judge_plan"], guidance="先写选择")
        self.assertEqual(explicit.stages, ["plan", "judge_plan"])
        with self.assertRaises(ValidationError):
            CreationInput(objective="坏工序", stages=["publish"])
        with self.assertRaises(ValidationError):
            CreationInput(objective="太长", stages=["plan", "judge_plan", "write", "judge", "revise", "plan"])
        StudioMarketConfigInput(target_min_words=3000, target_max_words=3000)
        with self.assertRaises(ValidationError):
            StudioMarketConfigInput(target_min_words=4000, target_max_words=2000)

    def test_stage_order_and_transitions(self):
        validate_stage_order(["plan"], has_outline=False, has_current=False)
        validate_stage_order(["plan", "judge_plan", "write", "judge", "revise"], has_outline=False, has_current=False)
        validate_stage_order(["revise", "judge"], has_outline=False, has_current=True)
        validate_stage_order(["judge"], has_outline=False, has_current=True)
        for stages, outline, current in (
            (["judge"], False, False),
            (["revise"], False, False),
            (["plan", "revise"], False, False),
            (["judge_plan", "revise"], True, False),
            (["judge_plan"], False, False),
            (["write", "plan"], False, True),
            (["write", "revise"], False, True),
            (["plan", "write", "revise"], False, True),
            (["plan", "judge"], False, True),
            (["plan", "judge_plan", "judge"], False, True),
            (["plan", "plan"], False, False),
            (["judge", "write"], False, True),
        ):
            with self.assertRaises(DomainError, msg=f"expected DomainError for {stages}"):
                validate_stage_order(stages, has_outline=outline, has_current=current)
        for valid_stages in (
            ["plan", "revise"],
            ["plan", "revise", "judge"],
            ["judge_plan", "revise"],
            ["judge_plan", "revise", "judge"],
            ["plan", "judge_plan", "revise"],
            ["plan", "judge_plan", "revise", "judge"],
        ):
            validate_stage_order(valid_stages, has_outline=True, has_current=True)
        self.assertEqual(
            explicit_transition(["plan", "revise"], "plan", qualified=True, revisions=0, max_revisions=2)["next_stage"],
            "revise",
        )
        self.assertEqual(
            explicit_transition(["judge_plan", "revise"], "judge_plan", qualified=True, revisions=0, max_revisions=2)[
                "next_stage"
            ],
            "revise",
        )
        self.assertEqual(
            explicit_transition(
                ["judge_plan", "revise", "judge"], "judge_plan", qualified=True, revisions=0, max_revisions=2
            )["next_stage"],
            "revise",
        )
        self.assertEqual(
            explicit_transition(
                ["judge_plan", "revise", "judge"], "revise", qualified=True, revisions=0, max_revisions=2
            )["next_stage"],
            "judge",
        )
        self.assertEqual(
            explicit_transition(["plan"], "plan", qualified=True, revisions=0, max_revisions=2)["terminal"],
            "waiting",
        )
        self.assertEqual(
            explicit_transition(["plan", "judge_plan"], "judge_plan", qualified=True, revisions=0, max_revisions=2),
            {"terminal": "qualified", "attach_plan": True},
        )
        self.assertEqual(
            explicit_transition(["plan", "judge_plan"], "judge_plan", qualified=False, revisions=0, max_revisions=2)[
                "next_stage"
            ],
            "plan",
        )
        self.assertEqual(
            explicit_transition(["write"], "write", qualified=True, revisions=0, max_revisions=2)["terminal"],
            "waiting",
        )
        self.assertEqual(
            explicit_transition(["write", "judge"], "judge", qualified=True, revisions=0, max_revisions=2)["terminal"],
            "qualified",
        )
        low = explicit_transition(["write", "judge", "revise"], "judge", qualified=False, revisions=0, max_revisions=2)
        self.assertEqual(low["next_stage"], "revise")
        self.assertTrue(low.get("count_revision"))
        capped = explicit_transition(["write", "judge", "revise"], "judge", qualified=False, revisions=2, max_revisions=2)
        self.assertEqual(capped["terminal"], "waiting")
        passed = explicit_transition(["write", "judge", "revise"], "judge", qualified=True, revisions=0, max_revisions=2)
        self.assertEqual(passed["terminal"], "qualified")
        self.assertEqual(
            explicit_transition(["judge"], "judge", qualified=False, revisions=0, max_revisions=2)["terminal"],
            "succeeded",
        )
        self.assertEqual(
            explicit_transition(["revise", "judge"], "revise", qualified=True, revisions=0, max_revisions=2)[
                "next_stage"
            ],
            "judge",
        )
        self.assertEqual(
            explicit_transition(["plan", "judge_plan", "write", "judge", "revise"], "plan", qualified=True, revisions=0, max_revisions=2)[
                "next_stage"
            ],
            "judge_plan",
        )

    def test_foreshadow_alerts_and_book_chapter_ordering(self):
        from ncc_data.domain.studio_catalog import (
            count_han_chars,
            foreshadow_lifecycle,
            ordered_book_chapters,
        )

        self.assertEqual(foreshadow_alert_state({"status": "已兑现", "expected_chapter": 2}, 9), "resolved")
        self.assertEqual(foreshadow_alert_state({"status": "作废", "expected_chapter": 2}, 9), "dropped")
        self.assertEqual(foreshadow_alert_state({"expected_chapter": 4}, 6), "overdue")
        self.assertEqual(foreshadow_alert_state({"expected_chapter": 8}, 6), "due_soon")
        self.assertEqual(foreshadow_alert_state({"planted_chapter": 2}, 5), "active")
        self.assertEqual(foreshadow_alert_state({"planted_chapter": 7, "expected_chapter": 8}, 5), "planned")
        self.assertEqual(foreshadow_alert_state({"status": "待埋设"}, 5), "planned")
        unplanted_due = foreshadow_lifecycle(
            {"status": "待埋设", "line_type": "暗线", "expected_chapter": 6}, 5
        )
        self.assertEqual(
            unplanted_due,
            {"planted": False, "due_state": "due_soon", "alert_state": "due_soon"},
        )
        planted_due = foreshadow_lifecycle(
            {"status": "已埋设", "line_type": "暗线", "planted_chapter": 2, "expected_chapter": 6}, 5
        )
        self.assertEqual(
            planted_due,
            {"planted": True, "due_state": "due_soon", "alert_state": "due_soon"},
        )
        self.assertEqual(count_han_chars("甲，A1。"), 1)
        self.assertEqual(count_han_chars("二〇二六"), 4)
        vols = [{"id": "v2", "position": 1}, {"id": "v1", "position": 0}]
        chs = [
            {"id": f"v2c{i}", "position": i, "parent_id": "v2"} for i in range(4)
        ] + [
            {"id": f"v1c{i}", "position": i, "parent_id": "v1"} for i in range(4)
        ]
        ordered = ordered_book_chapters(vols, chs)
        self.assertEqual([c["id"] for c in ordered], ["v1c0", "v1c1", "v1c2", "v1c3", "v2c0", "v2c1", "v2c2", "v2c3"])
        self.assertEqual([c["book_order"] for c in ordered], [1, 2, 3, 4, 5, 6, 7, 8])


if __name__ == "__main__":
    unittest.main()
