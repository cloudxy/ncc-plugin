#!/usr/bin/env python3
"""ncc_state.py / check_chapter.py 自测。运行: python3 scripts/test_ncc_state.py"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE = str(HERE / "ncc_state.py")
CHECK = str(HERE / "check_chapter.py")

SCENE_FULL = """# ch-{seq:04d} 场景卡

## 场景 1
- 视角：陆言　盲区：不知道林家已经报了警
- 目标：拿回父亲的工牌　阻碍：保安队长
- 翻转：从"求人"到"被人求"
- 两难：当众揭穿（代价：父亲丢工作）还是忍下（代价：被看轻）
- 情感：先憋后燃，留一点不安
- 画面：工牌在雨里反光
- 风险：比上一场多了警察这一方
"""
SCENE_SHORT = """## 场景 1
- 视角：陆言
- 目标：借到钱
- 翻转：从有退路到没有退路
- 两难：卖掉玉佩还是求林家
- 情感：压
"""


def run(*args, script=STATE):
    r = subprocess.run([sys.executable, script, *map(str, args)], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


class Base(unittest.TestCase):
    MODE = "混合"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.book = Path(self.tmp.name) / "测试书"
        code, out = run("init", self.book, "--title", "测试书", "--genre", "都市,诡异", "--mode", self.MODE)
        self.assertEqual(code, 0, out)

    def tearDown(self):
        self.tmp.cleanup()

    def ok(self, *args):
        code, out = run(*args)
        self.assertEqual(code, 0, out)
        return out

    def fail(self, *args, code=1):
        c, out = run(*args)
        self.assertEqual(c, code, out)
        return out

    def book_json(self):
        return json.loads((self.book / "book.json").read_text("utf-8"))

    def write(self, rel, text):
        p = self.book / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, "utf-8")
        return p

    def add(self, seq, key=False):
        f = f"04-正文/第{seq:04d}章-x.md"
        self.write(f, "正文" * 10)
        self.ok("chapter", "add", self.book, seq, "--file", f, *(["--key"] if key else []))
        return f

    def ready(self, seq):
        key = next(c for c in self.book_json()["chapters"] if c["seq"] == seq)["key"]
        self.write(f"02-大纲/场景卡/ch-{seq:04d}.md", SCENE_FULL.format(seq=seq))
        self.ok("scene", "review", self.book, seq, "--result", "pass", "--by", "author" if key else "story-editor")
        return key

    def finish(self, seq, key=False):
        self.add(seq, key)
        if self.ready(seq):
            self.ok("chapter", "pick", self.book, seq, "--version", "B")
        self.ok("complete", self.book, seq, "--words", 3000, "--hard", "pass")


class TestInitAndSoul(Base):
    def test_init_layout(self):
        d = self.book_json()
        self.assertEqual(d["schema_version"], 2)
        self.assertEqual(d["stage"], "founding")
        self.assertEqual(d["experience_level"], "新手")
        self.assertEqual(d["mode"], "混合")
        for rel in ("06-台账/承诺台账.json", "06-台账/知情台账.json", "06-台账/知识台账.json",
                    "06-台账/状态事件.json", "author-intent.md", "current-focus.md",
                    "00-策划/作者种子.md", "02-大纲/场景卡"):
            self.assertTrue((self.book / rel).exists(), rel)
        self.assertIn("书魂", (self.book / "author-intent.md").read_text("utf-8"))
        self.assertIn("最先出现的是什么画面", (self.book / "00-策划/作者种子.md").read_text("utf-8"))

    def test_soul_gate(self):
        self.assertIn("主题之问", self.fail("gate", self.book, "soul"))
        self.ok("soul", self.book, "--question", "Q", "--answer", "A", "--injustice", "I",
                "--ending", "E", "--status", "暂定")
        self.assertIn("最晚决定点", self.fail("gate", self.book, "soul"))
        self.ok("soul", self.book, "--deadline", "第一卷卷复盘")
        self.assertIn("主契约", self.fail("gate", self.book, "soul"))
        self.ok("contract", self.book, "--main", "凡人逆袭＋守护", "--poison", "主角降智,长期憋屈不反击")
        self.ok("gate", self.book, "soul")
        self.ok("gate", self.book, "soul", "--action", "pass", "--quote", "就这样")
        self.assertEqual(self.book_json()["stage"], "settings")

    def test_force_pass_needs_quote(self):
        self.fail("gate", self.book, "soul", "--action", "pass")
        self.fail("gate", self.book, "soul", "--action", "pass", "--force")
        self.ok("gate", self.book, "soul", "--action", "pass", "--force", "--quote", "先开写")
        g = self.book_json()["gates"]["soul"]
        self.assertEqual(g["status"], "passed")
        self.assertTrue(g["forced_over"])

    def test_level_mode_arc(self):
        self.ok("level", self.book, "老手")
        self.fail("level", self.book, "大神")
        self.ok("mode", self.book, "园丁")
        self.fail("mode", self.book, "随便")
        self.ok("soul", self.book, "--arc", "平弧")
        self.fail("soul", self.book, "--arc", "螺旋")
        d = self.book_json()
        self.assertEqual((d["experience_level"], d["mode"], d["soul"]["arc"]), ("老手", "园丁", "平弧"))


class TestSettingsGate(Base):
    def test_character_card_and_arc_required(self):
        self.write("01-设定/世界观圣经.md", "圣经")
        self.write("01-设定/力量体系.md", "量纲")
        rows = "\n".join(f"| 词{i} | 1 | a | b | 9 |" for i in range(30))
        self.write("01-设定/设定词典.md", "| 词条 | 首现章计划 | 读者已知 | 完整真相 | 计划揭示章 |\n|---|---|---|---|---|\n" + rows)
        out = self.fail("gate", self.book, "settings")
        self.assertIn("人物卡", out)
        self.assertIn("弧光", out)
        self.write("01-设定/人物卡/陆言.md", "欲望 需要 恐惧 伤口 声音")
        self.ok("soul", self.book, "--arc", "正向")
        self.ok("gate", self.book, "settings")


class TestOutlineGateByMode(unittest.TestCase):
    def gate(self, mode, files, promise):
        with tempfile.TemporaryDirectory() as t:
            book = Path(t) / "书"
            run("init", book, "--title", "书", "--mode", mode)
            for rel in files:
                p = book / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("内容", "utf-8")
            if promise:
                run("promise", "add", book, "--type", "悬念", "--content", "x", "--ch", 1)
            return run("gate", book, "outline")[0]

    def test_modes(self):
        self.assertEqual(self.gate("园丁", ["02-大纲/总纲.md"], False), 0)
        self.assertEqual(self.gate("混合", ["02-大纲/总纲.md"], True), 1)
        self.assertEqual(self.gate("混合", ["02-大纲/总纲.md", "02-大纲/卷纲/卷1.md"], True), 0)
        self.assertEqual(self.gate("建筑师", ["02-大纲/总纲.md", "02-大纲/卷纲/卷1.md"], True), 1)
        self.assertEqual(self.gate("建筑师", ["02-大纲/总纲.md", "02-大纲/卷纲/卷1.md", "02-大纲/章纲/ch-0001.md",
                                           "02-大纲/章纲/ch-0002.md", "02-大纲/章纲/ch-0003.md"], True), 0)


class TestSceneLayer(Base):
    def test_story_first_guard(self):
        self.add(5)
        self.assertIn("故事审", self.fail("chapter", "mark", self.book, 5, "drafting"))
        self.assertIn("缺场景卡", self.fail("scene", "check", self.book, 5))
        self.write("02-大纲/场景卡/ch-0005.md", "## 场景 1\n- 视角：陆言\n- 目标：x\n")
        self.assertIn("翻转", self.fail("scene", "review", self.book, 5, "--result", "pass", "--by", "story-editor"))
        self.write("02-大纲/场景卡/ch-0005.md", SCENE_SHORT)
        self.ok("scene", "check", self.book, 5)
        self.ok("scene", "review", self.book, 5, "--result", "pass", "--by", "story-editor")
        self.ok("chapter", "mark", self.book, 5, "drafting")

    def test_edit_after_review_needs_rereview(self):
        self.add(6)
        self.write("02-大纲/场景卡/ch-0006.md", SCENE_SHORT)
        self.ok("scene", "review", self.book, 6, "--result", "pass", "--by", "story-editor")
        self.write("02-大纲/场景卡/ch-0006.md", SCENE_SHORT + "\n补一句")
        self.assertIn("改动", self.fail("chapter", "mark", self.book, 6, "drafting"))

    def test_key_chapter_needs_full_card_author_and_pick(self):
        self.add(1)                                  # 第 1–3 章默认关键章
        self.write("02-大纲/场景卡/ch-0001.md", SCENE_SHORT)
        self.assertIn("盲区", self.fail("scene", "check", self.book, 1))
        self.write("02-大纲/场景卡/ch-0001.md", SCENE_FULL.format(seq=1))
        self.assertIn("作者", self.fail("scene", "review", self.book, 1, "--result", "pass", "--by", "story-editor"))
        self.ok("scene", "review", self.book, 1, "--result", "pass", "--by", "author")
        self.assertIn("选定", self.fail("complete", self.book, 1, "--words", 3000, "--hard", "pass"))
        self.ok("chapter", "pick", self.book, 1, "--version", "B", "--note", "B 的反转更意外")
        self.fail("complete", self.book, 1, "--words", 3000, "--hard", "fail")
        self.ok("complete", self.book, 1, "--words", 3000, "--hard", "pass")

    def test_pick_only_for_key(self):
        self.add(9)
        self.assertIn("不是关键章", self.fail("chapter", "pick", self.book, 9, "--version", "A"))
        self.ok("chapter", "key", self.book, 9)
        self.ok("chapter", "pick", self.book, 9, "--version", "A")


class TestChaptersAndPromises(Base):
    def test_hook_and_retry(self):
        self.add(4)
        self.fail("chapter", "add", self.book, 4, "--file", "x.md")
        self.ok("chapter", "hook", self.book, 4, "--type", "悬念", "--intensity", 4)
        self.fail("chapter", "hook", self.book, 4, "--type", "悬念", "--intensity", 9)
        self.fail("chapter", "mark", self.book, 4, "done")
        for _ in range(3):
            self.ok("chapter", "retry", self.book, 4)
        self.assertEqual(self.book_json()["chapters"][0]["status"], "failed")

    def test_mood_palette_and_legacy(self):
        self.add(4)
        self.ok("chapter", "mood", self.book, 4, "放", "--colors", "燃,悲")
        self.ok("chapter", "mood", self.book, 4, "释放")
        self.fail("chapter", "mood", self.book, 4, "放", "--colors", "开心")
        self.assertEqual(self.book_json()["chapters"][0]["mood"]["tension"], "放")

    def test_promise_lifecycle_and_water(self):
        self.fail("water", self.book, 2)
        out = self.ok("promise", "add", self.book, "--type", "悬念", "--content", "门后是什么",
                      "--ch", 1, "--strength", 4, "--window", "5-8")
        pid = out.split()[1]
        self.ok("water", self.book, 1)
        self.ok("promise", "touch", self.book, pid, "--ch", 2, "--note", "门缝有光")
        self.ok("water", self.book, 2)
        self.fail("water", self.book, 3)
        self.fail("promise", "drop", self.book, pid, "--ch", 3, "--compensation", " ")
        self.ok("promise", "resolve", self.book, pid, "--ch", 6)
        self.fail("promise", "touch", self.book, pid, "--ch", 7)
        self.assertEqual(self.book_json()["promises"]["resolved"], 1)

    def test_option_and_motif_do_not_count_against_water(self):
        self.ok("promise", "add", self.book, "--type", "期权", "--content", "老人手上的旧伤", "--ch", 3)
        self.ok("promise", "add", self.book, "--type", "母题", "--content", "雨中的工牌", "--ch", 3)
        self.fail("water", self.book, 3)
        out = self.ok("promise", "add", self.book, "--type", "名场面", "--content", "守城夜", "--ch", 3)
        self.assertTrue(out.split()[1].startswith("SC-"))
        self.ok("water", self.book, 3)

    def test_tentative_decision_needs_deadline_and_goes_overdue(self):
        self.fail("promise", "add", self.book, "--type", "暂定决策", "--content", "反派身份", "--ch", 1)
        self.ok("promise", "add", self.book, "--type", "暂定决策", "--content", "反派身份",
                "--ch", 1, "--deadline", 2)
        for seq in (4, 5, 6):
            self.finish(seq)
        self.assertEqual(self.book_json()["promises"]["overdue"], 1)
        self.assertIn("逾期", self.ok("status", self.book))

    def test_window_overdue(self):
        self.ok("promise", "add", self.book, "--type", "伏笔", "--content", "玉佩", "--ch", 1, "--window", "1-1")
        self.finish(4)
        self.assertEqual(self.book_json()["promises"]["overdue"], 1)


class TestKnowledgeFactsReaderNow(Base):
    def test_know_and_reader_now(self):
        out = self.ok("know", "add", self.book, "--fact", "主角是剑仙转世", "--ch", 1,
                      "--known-by", "读者,主角", "--unknown-to", "反派甲")
        kid = out.split()[1]
        self.ok("promise", "add", self.book, "--type", "爽点欠账", "--content", "当众打脸反派甲",
                "--ch", 1, "--strength", 5)
        now = self.ok("reader-now", self.book, 3)
        self.assertIn("反派甲 还不知道", now)
        self.assertIn("当众打脸反派甲", now)
        self.ok("know", "learn", self.book, kid, "--who", "反派甲", "--ch", 4)
        self.assertIn("无登记的信息差", self.ok("reader-now", self.book, 5))

    def test_reader_now_losses_and_colors(self):
        ev = self.book / "06-台账/状态事件.json"
        ev.write_text(json.dumps({"events": [{"entity": "陆言", "chapter": 4, "attribute": "失去",
                                              "old": "父亲的工作", "new": "无"}]}, ensure_ascii=False), "utf-8")
        for seq in (4, 5, 6):
            self.add(seq)
            self.ok("chapter", "mood", self.book, seq, "压", "--colors", "虐")
        now = self.ok("reader-now", self.book, 7)
        self.assertIn("最近失去了什么", now)
        self.assertIn("父亲的工作", now)
        self.assertIn("情绪「虐」", now)

    def test_fact_conflict(self):
        self.ok("fact", "set", self.book, "青云城到落霞镇", "三日", "--ch", 2, "--category", "距离")
        self.ok("fact", "set", self.book, "青云城到落霞镇", "三日", "--ch", 9)
        self.fail("fact", "set", self.book, "青云城到落霞镇", "一日", "--ch", 12)
        self.ok("fact", "set", self.book, "青云城到落霞镇", "一日", "--ch", 12, "--override")
        facts = json.loads((self.book / "06-台账/知识台账.json").read_text("utf-8"))["facts"]
        self.assertEqual(facts["青云城到落霞镇"]["history"][0]["value"], "三日")


class TestOpeningGate(Base):
    def test_opening_requirements(self):
        for seq in (1, 2, 3):
            self.finish(seq)
        out = self.fail("gate", self.book, "opening")
        self.assertIn("盲评", out)
        self.assertIn("签约点未落地", out)
        self.write("05-审稿/blind-ch-0001-0003.md", "盲评")
        self.assertIn("记忆测试", self.fail("gate", self.book, "opening"))
        self.write("05-审稿/blind-ch-0001-0003.md", "盲评\n## 记忆测试\n记住了工牌")
        for pt in ("主角与欲望", "世界的不公", "主角的机会", "第一次小兑现", "长线钩子"):
            self.ok("sign", self.book, pt, "--ch", 2)
        self.ok("gate", self.book, "opening")

    def test_planned_gates(self):
        self.assertIn("M3-1", self.fail("gate", self.book, "volume", code=3))


class TestMigrate(unittest.TestCase):
    def test_v01_book(self):
        with tempfile.TemporaryDirectory() as t:
            book = Path(t) / "旧书"
            (book / "06-台账").mkdir(parents=True)
            (book / "book.json").write_text(json.dumps({
                "schema_version": 1, "title": "旧书", "stage": "golden",
                "gates": {"settings_frozen": {"status": "passed"}, "outline_frozen": {"status": "passed"},
                          "golden_accepted": {"status": "waiting"}},
                "chapters": [], "foreshadows": {"total": 1}}, ensure_ascii=False), "utf-8")
            (book / "06-台账/伏笔台账.json").write_text(json.dumps([
                {"id": "FS-0001", "content": "青铜门", "预计埋设章": 1, "预计回收窗口": "20-30", "status": "planned"}],
                ensure_ascii=False), "utf-8")
            self.assertEqual(run("status", book)[0], 1)
            code, out = run("migrate", book)
            self.assertEqual(code, 0, out)
            d = json.loads((book / "book.json").read_text("utf-8"))
            self.assertEqual((d["stage"], d["mode"]), ("opening", "建筑师"))
            self.assertIn("opening_accepted", d["gates"])
            self.assertIn("soul", d["gates"])
            items = json.loads((book / "06-台账/承诺台账.json").read_text("utf-8"))["items"]
            self.assertEqual((items[0]["id"], items[0]["window"]), ("FS-0001", [20, 30]))


class TestCheckChapter(Base):
    def test_water_in_check_chapter(self):
        f = "04-正文/第0004章-开端.md"
        self.write(f, "字" * 3200)
        self.ok("chapter", "add", self.book, 4, "--file", f)
        self.ok("chapter", "hook", self.book, 4, "--type", "悬念", "--intensity", 4)
        code, out = run(self.book, 4, script=CHECK)
        self.assertEqual(code, 1, out)
        self.assertIn("水章", out)
        self.ok("promise", "add", self.book, "--type", "悬念", "--content", "门后", "--ch", 4)
        code, out = run(self.book, 4, script=CHECK)
        self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main(verbosity=1)
