"""会话审查的 13 项缺陷：从输入、派单与持久化结果验证。"""
import contextlib
import io
import json
import os
import re
from pathlib import Path
from unittest.mock import patch

import check_chapter as cc
import ncc_eval as ne
from ncclib import core, memory, techniques
from test_ncc_state import Base, EVAL, SCENE_SHORT, run


class TestV3Regressions(Base):
    def proposal(self, key, value, parent=None):
        extra = ["--parent", parent] if parent else []
        out = self.ok("evolve", "propose", self.book, "--key", key, "--value=" + value,
                      "--why", "回归测试", "--evidence", "测试夹具", *extra)
        pid = re.search(r"EP-\d+", out).group()
        if key.startswith("check."):
            self.ok("evolve", "eval", self.book, pid)
        self.ok("evolve", "apply", self.book, pid, "--quote", "采用此测试改动")
        return pid

    def card(self, method="环境描写跟着脚步走", kind="文笔参考", source="样书"):
        return self.ok("technique", "add", self.book, "--kind", kind, "--method", method,
                       "--how", "写人物经过的声音", "--evidence", f"拆:{source} 第1章「雨夜长街灯火」",
                       "--applies", "题材=都市", "--cost", "不适合静景", "--confidence", "强推断", "--source", source)

    def scene(self, refs):
        self.add(4)
        self.write("02-大纲/场景卡/ch-0004.md", SCENE_SHORT + f"- 技法：{refs}\n")
        self.ok("scene", "review", self.book, 4, "--result", "pass", "--by", "story-editor")

    def pack(self):
        self.ok("pack", self.book, 4)
        return (self.book / ".ncc/写手包/ch-0004.md").read_text("utf-8")

    def test_gate_covers_each_evolvable_check(self):
        base = self.book.parent / "base.json"
        cand = self.book.parent / "candidate.json"
        core.write_json(base, {"values": {}})
        changes = [
            ("check.ai_level1_max", 999), ("check.level1_words", ["-仿佛"]),
            ("check.para_max", 0), ("check.para_max", 9999),
            ("check.sentence_commas_max", 999), ("check.dialogue_run_max", 999),
        ]
        for key, value in changes:
            with self.subTest(key=key, value=value):
                core.write_json(cand, {"values": {key: value}})
                code, out = run("gate", "--baseline", base, "--candidate", cand, script=EVAL)
                self.assertEqual(code, 1, out)
                self.assertIn("GATE FAIL", out)
        # 仍能检出同一问题时，消息里的阈值数字变化不能被误判成新问题。
        core.write_json(cand, {"values": {"check.ai_level1_max": 2, "check.para_max": 300}})
        code, out = run("gate", "--baseline", base, "--candidate", cand, script=EVAL)
        self.assertEqual(code, 0, out)

    def test_gate_detects_ai_loss_without_mech_hint_and_restores_environment(self):
        base = self.book.parent / "base.json"
        cand = self.book.parent / "candidate.json"
        core.write_json(base, {"values": {}})
        core.write_json(cand, {"values": {"check.ai_level1_max": 999}})
        from types import SimpleNamespace
        case = ({"id": "AI-positive", "era": "现代", "mech": []}, "仿佛。" * 4)
        with patch.object(ne, "gate_cases", return_value=iter([case])), patch.dict(os.environ, {"NCC_OVERLAY": "original"}):
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as caught:
                ne.cmd_gate(SimpleNamespace(baseline=base, candidate=cand))
            self.assertEqual(caught.exception.code, 1)
            self.assertEqual(os.environ["NCC_OVERLAY"], "original")

    def test_revert_preserves_later_word_change_and_reapplication_order(self):
        first = self.proposal("technique.kinds", "+甲类")
        second = self.proposal("technique.kinds", "+乙类")
        self.ok("evolve", "revert", self.book, first)
        self.assertEqual(core.overlay_values(self.book)["technique.kinds"], ["+乙类"])
        self.assertIn("已生效", self.ok("evolve", "list", self.book))
        self.ok("evolve", "apply", self.book, first, "--quote", "重新采用")
        self.ok("evolve", "revert", self.book, second)
        self.assertEqual(core.overlay_values(self.book)["technique.kinds"], ["+甲类"])
        self.ok("evolve", "revert", self.book, first)
        self.assertNotIn("technique.kinds", core.overlay_values(self.book))

    def test_revert_preserves_scalar_baseline_and_other_category(self):
        core.write_json(self.book.parent / core.OVERLAY, {"values": {"check.para_max": 250}})
        first = self.proposal("check.para_max", "260")
        second = self.proposal("check.para_max", "270")
        self.ok("evolve", "revert", self.book, first)
        self.assertEqual(cc.load_config(self.book)["para_max"], 270)
        self.ok("evolve", "revert", self.book, second)
        self.assertEqual(cc.load_config(self.book)["para_max"], 250)
        first = self.proposal("setting.categories", "甲类:条件,代价,结果")
        self.proposal("setting.categories", "乙类:条件,代价,结果")
        self.ok("evolve", "revert", self.book, first)
        self.assertEqual(set(core.overlay_values(self.book)["setting.categories"]), {"乙类"})

    def test_opposite_memory_is_never_auto_reinforced(self):
        old = "打斗场面每场只留一个转折动作，其余用结果带过"
        correction = "打斗场面每场不能只留一个转折动作，其余不能用结果带过"
        for text, evidence in ((old, "第1章"), (correction, "第2章纠正")):
            self.ok("memory", "add", self.book, "--role", "writer", "--kind", "教训", "--text", text, "--evidence", evidence)
        items = memory.memory_items(self.book, "writer")
        self.assertEqual([i["text"] for i in items], [old, correction])
        self.assertEqual([i["status"] for i in items], ["candidate", "candidate"])
        self.assertIn("相似候选", self.ok("memory", "consolidate", self.book))
        self.ok("memory", "archive", self.book, "--role", "writer", "MEM-0001")
        self.ok("memory", "reinforce", self.book, "--role", "writer", "MEM-0002", "--evidence", "第3章")
        own, _, _ = memory.memory_slice(self.book, self.book_json(), "writer")
        self.assertEqual(len(own), 1)
        self.assertIn(correction, own[0])

    def test_duplicate_evidence_does_not_activate_or_promote(self):
        args = ("memory", "add", self.book, "--role", "writer", "--kind", "教训", "--text", "雨夜描写跟着脚步走")
        self.ok(*args, "--evidence", "第1章;第1章")
        self.ok(*args, "--evidence", "第1章")
        self.ok("memory", "reinforce", self.book, "--role", "writer", "MEM-0001", "--evidence", "第1章")
        item = memory.memory_items(self.book, "writer")[0]
        self.assertEqual((item["hits"], item["status"]), (1, "candidate"))
        self.assertEqual(item["recordings"], 3)
        self.bad("memory", "promote", self.book, "MEM-0001", "--role", "writer")
        self.ok("memory", "reinforce", self.book, "--role", "writer", "MEM-0001", "--evidence", "第2章")
        self.ok(*args, "--evidence", "第2章")
        self.bad("memory", "promote", self.book, "MEM-0001", "--role", "writer")
        self.assertEqual(memory.memory_items(self.book, "writer")[0]["hits"], 2)
        # 标点不同的条目会有同一相似度，重复正文必须找到自己的记录。
        self.ok("memory", "add", self.book, "--role", "writer", "--kind", "教训",
                "--text", "雨夜描写跟着脚步走。", "--evidence", "第3章")
        self.ok("memory", "add", self.book, "--role", "writer", "--kind", "教训",
                "--text", "雨夜描写跟着脚步走。", "--evidence", "第4章")
        items = memory.memory_items(self.book, "writer")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[1]["evidence"], ["第3章", "第4章"])

    def test_shared_memory_can_be_edited_archived_restored_and_reinforced(self):
        self.ok("memory", "add", self.book, "--role", "writer", "--kind", "教训", "--text", "吵架先做事再说话", "--evidence", "第1章;第2章;第3章")
        self.ok("memory", "promote", self.book, "--role", "writer")
        other = self.book.parent / "第二本"
        self.ok("init", other, "--title", "第二本", "--genre", "都市")
        self.ok("memory", "edit", other, "--role", "writer", "MX-0001", "--shared", "--text", "吵架先写利益冲突")
        _, shared, _ = memory.memory_slice(other, core.load(other), "writer")
        self.assertIn("利益冲突", shared[0])
        self.bad("memory", "edit", other, "--role", "writer", "MX-0001", "--shared", "--text", "硬伤判据")
        self.ok("memory", "archive", other, "--role", "writer", "MX-0001", "--shared")
        self.assertEqual(memory.memory_slice(other, core.load(other), "writer")[1], [])
        self.ok("memory", "restore", other, "--role", "writer", "MX-0001", "--shared")
        for _ in range(2):
            self.ok("memory", "reinforce", other, "--role", "writer", "MX-0001", "--shared", "--evidence", "第1章")
        item = memory.memory_items(other, "writer", True)[0]
        self.assertEqual(item["hits"], 4)  # 同章号跨书不同；同书同证据不重复计数
        self.assertEqual(item["origin"]["id"], "MEM-0001")
        self.assertEqual(memory.memory_items(self.book, "writer")[0]["text"], "吵架先做事再说话")
        self.ok("memory", "consolidate", other, "--shared", "--apply")

    def test_reader_shared_memory_uses_same_persona_filter(self):
        for text in ("老白画像在日常章低估追读", "新手画像在说明段容易略读"):
            self.ok("memory", "add", self.book, "--role", "reader", "--kind", "校准", "--text", text, "--evidence", "第1章;第2章;第3章")
        self.ok("memory", "promote", self.book, "--role", "reader")
        self.ok("brief", self.book, "--role", "reader", "--persona", "新手")
        text = (self.book / ".ncc/派单/reader-新手.md").read_text("utf-8")
        self.assertNotIn("老白", text)
        self.assertEqual(text.count("说明段容易略读"), 2)

    def test_technique_cannot_leak_review_criteria_at_add_or_dispatch(self):
        self.card()
        self.scene("T-0001")
        self.assertIn("文笔参考：环境描写跟着脚步走", self.pack())
        code, out = run("technique", "add", self.book, "--kind", "文笔参考", "--method", "硬伤层判据",
                        "--how", "照着打分", "--evidence", "拆:样书 第1章「雨夜长街灯火」", "--applies", "题材=都市",
                        "--cost", "测试", "--confidence", "强推断", "--source", "样书")
        self.assertEqual(code, 1, out)
        # 已存在的手写/旧版卡也必须在派单时校验，不能只拦创建入口。
        path = techniques.technique_cards(self.book.parent)["T-0001"]["path"]
        path.write_text(path.read_text("utf-8").replace("写人物经过的声音", "注意硬伤层的时间线"), "utf-8")
        self.assertIn("判据", self.bad("pack", self.book, 4))

    def test_retired_and_auto_retired_techniques_stay_out_of_pack(self):
        self.card()
        self.scene("T-0001")
        self.ok("technique", "retire", self.book, "T-0001", "--note", "作者停用")
        self.assertNotIn("文笔参考：", self.pack())
        self.ok("technique", "restore", self.book, "T-0001")
        self.assertIn("文笔参考：", self.pack())
        for _ in range(2):
            self.ok("technique", "result", self.book, "T-0001", "--outcome", "bad", "--note", "结果不好")
        self.assertNotIn("文笔参考：", self.pack())

    def test_configuration_merges_layers_and_reports_real_source(self):
        root = self.book.parent
        (root / "ncc.config.yaml").write_text("words_min: 3100\npara_max: 200\nwords_max: 6000\n")
        self.write("ncc.config.yaml", "chapter:\n  words_min: 4100\n  para_max: 777\n# max_retry: 99\n")
        core.write_json(root / core.OVERLAY, {"values": {"check.para_max": 300}})
        cfg = cc.load_config(self.book)
        self.assertEqual((cfg["words_min"], cfg["words_max"], cfg["para_max"], cfg["max_retry"]), (4100, 6000, 777, 3))
        self.assertEqual(cfg, core.load_cfg(self.book))
        self.assertIn("777  ← 本书配置", self.ok("evolve", "rules", self.book))
        self.assertIn("300  ← 作者覆盖", self.ok("evolve", "rules", root))
        self.write("ncc.config.yaml", "words_min: 4200\n")
        self.assertEqual(cc.load_config(self.book)["para_max"], 300)

    def test_reusing_custom_setting_preserves_definition_and_alias(self):
        self.ok("setting", "new", self.book, "夜契", "--required", "立契条件,代价,解约方式", "--optional", "见证人",
                "--alias", "月契", "--why", "约束人物", "--gap", "不是现有类目")
        before = self.book_json()["setting_categories"]["used"]["夜契"]
        self.ok("setting", "use", self.book, "月契", "--why", "补充理由")
        after = self.book_json()["setting_categories"]["used"]["夜契"]
        for key in ("custom", "required", "optional", "alias", "gap"):
            self.assertEqual(before[key], after[key])
        self.ok("setting", "add", self.book, "月契", "初契")
        card = (self.book / "01-设定/类目/夜契/初契.md").read_text("utf-8")
        self.assertIn("解约方式", card)
        self.assertIn("见证人", card)

    def test_range_stats_require_current_source_and_index_but_allow_partial_work(self):
        lib = self.book.parent / "_拆书库/样书"
        src = lib / "原文/样书.txt"
        src.parent.mkdir(parents=True)
        src.write_text("第一章 起\n" + "雨夜长街。" * 40 + "\n第二章 续\n" + "长街有雨。" * 40, "utf-8")
        self.ok("decon", "mark", lib, "--done", "1")
        self.assertIn("索引", self.bad("decon", "stats", lib, "--range", "1-1"))
        self.ok("decon", "index", lib)
        self.ok("decon", "stats", lib, "--range", "1-1", "--write")
        baseline = (lib / "报告/基线.json").read_bytes()
        self.bad("decon", "stats", lib, "--range", "1-2")
        self.bad("decon", "stats", lib, "--range", "3-3")
        src.write_text(src.read_text("utf-8") + "原文改变。", "utf-8")
        self.assertIn("变过", self.bad("decon", "stats", lib, "--range", "1-1", "--write"))
        self.assertEqual((lib / "报告/基线.json").read_bytes(), baseline)
        src.rename(src.with_suffix(".removed"))
        self.assertIn("不存在", self.bad("decon", "stats", lib, "--range", "1-1"))

    def test_new_technique_kind_inherits_parent_route_without_review_access(self):
        self.proposal("technique.kinds", "+叙事距离", parent="文笔参考")
        self.card(kind="叙事距离")
        self.scene("T-0001")
        self.assertIn("文笔参考：", self.pack())
        for role in ("reader", "pulse", "continuity", "outliner"):
            self.assertEqual(techniques.match(self.book, self.book_json(), role, [4]), [])
        self.proposal("technique.kinds", "+布局变体")  # 已有无父类提议也兼容到剧情规划
        self.card(kind="布局变体")
        self.assertIn("T-0002", self.ok("technique", "match", self.book, "--role", "outliner"))
        self.bad("evolve", "propose", self.book, "--key", "technique.kinds", "--value", "+越界",
                 "--parent", "reader", "--why", "测试", "--evidence", "测试")
        self.proposal("technique.kinds", "-文笔参考")
        self.assertNotIn("文笔参考", core.technique_kinds(self.book))
        self.proposal("technique.kinds", "+文笔参考")
        self.assertEqual(core.technique_catalog(self.book)["文笔参考"], "文笔参考")

    def test_budget_skips_oversized_entries_and_keeps_shorter_ones(self):
        lines, cut = core.capped(["字" * 2000, "短句", "字" * 599], 600)
        self.assertEqual((lines, cut), (["短句"], 2))
        self.ok("memory", "add", self.book, "--role", "writer", "--kind", "约定", "--text", "字" * 2000)
        self.ok("memory", "add", self.book, "--role", "writer", "--kind", "约定", "--text", "短句")
        own, _, cut = memory.memory_slice(self.book, self.book_json(), "writer")
        self.assertEqual(cut, 1)
        self.assertLessEqual(core.chars(own), core.MEMORY_CFG["caps"]["book_chars"])
        self.assertIn("短句", "".join(own))
        self.ok("handoff", "add", self.book, "--kind", "决定", "--layer", "L3", "--text", "字" * 2000)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(memory.handoff_slice(self.book, self.book_json(), "writer", plain=True), [])

    def test_writer_techniques_share_card_and_character_limits(self):
        for method in ("甲做法", "乙做法", "丙做法"):
            self.card(method)
        self.scene("T-0001、T-0002、T-0003")
        self.assertEqual(self.pack().count("- 文笔参考："), 2)
        for card in techniques.technique_cards(self.book.parent).values():
            p = card["path"]
            p.write_text(p.read_text("utf-8").replace("写人物经过的声音", "字" * 2000), "utf-8")
        self.assertNotIn("- 文笔参考：", self.pack())
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(techniques.brief_lines(self.book, self.book_json(), "writer", [4]), [])


if __name__ == "__main__":
    import unittest
    unittest.main()
