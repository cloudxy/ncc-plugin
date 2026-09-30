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


def run(*args, script=STATE):
    r = subprocess.run([sys.executable, script, *map(str, args)], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.book = Path(self.tmp.name) / "测试书"
        code, out = run("init", self.book, "--title", "测试书", "--genre", "都市,诡异")
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


class TestInitAndSoul(Base):
    def test_init_layout(self):
        d = self.book_json()
        self.assertEqual(d["schema_version"], 2)
        self.assertEqual(d["stage"], "founding")
        self.assertEqual(d["experience_level"], "新手")
        for rel in ("06-台账/承诺台账.json", "06-台账/知情台账.json", "06-台账/知识台账.json",
                    "06-台账/状态事件.json", "author-intent.md", "current-focus.md"):
            self.assertTrue((self.book / rel).exists(), rel)
        self.assertIn("书魂", (self.book / "author-intent.md").read_text("utf-8"))

    def test_soul_gate(self):
        out = self.fail("gate", self.book, "soul")
        self.assertIn("主题之问", out)
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

    def test_level(self):
        self.ok("level", self.book, "老手")
        self.assertEqual(self.book_json()["experience_level"], "老手")
        self.fail("level", self.book, "大神")


class TestChaptersAndPromises(Base):
    def test_chapter_registration_and_retry(self):
        self.ok("chapter", "add", self.book, 1, "--file", "04-正文/第0001章-开端.md")
        self.fail("chapter", "add", self.book, 1, "--file", "x.md")
        self.ok("chapter", "hook", self.book, 1, "--type", "悬念", "--intensity", 4)
        self.fail("chapter", "hook", self.book, 1, "--type", "悬念", "--intensity", 9)
        self.fail("chapter", "mark", self.book, 1, "done")
        for _ in range(3):
            self.ok("chapter", "retry", self.book, 1)
        self.assertEqual(self.book_json()["chapters"][0]["status"], "failed")

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

    def test_option_does_not_count_against_water(self):
        self.ok("promise", "add", self.book, "--type", "期权", "--content", "老人手上的旧伤", "--ch", 3)
        self.fail("water", self.book, 3)

    def test_tentative_decision_needs_deadline_and_goes_overdue(self):
        self.fail("promise", "add", self.book, "--type", "暂定决策", "--content", "反派身份", "--ch", 1)
        self.ok("promise", "add", self.book, "--type", "暂定决策", "--content", "反派身份",
                "--ch", 1, "--deadline", 2)
        for seq in (1, 2, 3):
            f = f"04-正文/第{seq:04d}章-x.md"
            self.write(f, "正文")
            self.ok("chapter", "add", self.book, seq, "--file", f)
            self.ok("complete", self.book, seq, "--words", 3000)
        self.assertEqual(self.book_json()["promises"]["overdue"], 1)
        self.assertIn("逾期", self.ok("status", self.book))

    def test_window_overdue(self):
        self.ok("promise", "add", self.book, "--type", "伏笔", "--content", "玉佩", "--ch", 1, "--window", "1-1")
        self.write("04-正文/第0002章-x.md", "正文")
        self.ok("chapter", "add", self.book, 2, "--file", "04-正文/第0002章-x.md")
        self.ok("complete", self.book, 2, "--words", 3000)
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

    def test_fact_conflict(self):
        self.ok("fact", "set", self.book, "青云城到落霞镇", "三日", "--ch", 2, "--category", "距离")
        self.ok("fact", "set", self.book, "青云城到落霞镇", "三日", "--ch", 9)
        self.fail("fact", "set", self.book, "青云城到落霞镇", "一日", "--ch", 12)
        self.ok("fact", "set", self.book, "青云城到落霞镇", "一日", "--ch", 12, "--override")
        facts = json.loads((self.book / "06-台账/知识台账.json").read_text("utf-8"))["facts"]
        self.assertEqual(facts["青云城到落霞镇"]["history"][0]["value"], "三日")


class TestOpeningGate(Base):
    def test_blind_report_required(self):
        for seq in (1, 2, 3):
            f = f"04-正文/第{seq:04d}章-x.md"
            self.write(f, "正文")
            self.ok("chapter", "add", self.book, seq, "--file", f)
            self.ok("complete", self.book, seq, "--words", 3000, "--score", 80)
        out = self.fail("gate", self.book, "opening")
        self.assertIn("盲评", out)
        self.assertIn("签约点未落地", out)
        self.write("05-审稿/blind-ch-0001-0003.md", "盲评")
        for pt in ("主角与欲望", "世界的不公", "主角的机会", "第一次小兑现", "长线钩子"):
            self.ok("sign", self.book, pt, "--ch", 2)
        self.ok("gate", self.book, "opening")

    def test_planned_gates(self):
        self.fail("gate", self.book, "volume", code=3)


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
            code, out = run("status", book)
            self.assertEqual(code, 1, out)
            code, out = run("migrate", book)
            self.assertEqual(code, 0, out)
            d = json.loads((book / "book.json").read_text("utf-8"))
            self.assertEqual(d["stage"], "opening")
            self.assertIn("opening_accepted", d["gates"])
            self.assertIn("soul", d["gates"])
            items = json.loads((book / "06-台账/承诺台账.json").read_text("utf-8"))["items"]
            self.assertEqual(items[0]["id"], "FS-0001")
            self.assertEqual(items[0]["window"], [20, 30])


class TestCheckChapter(Base):
    def test_water_in_check_chapter(self):
        f = "04-正文/第0001章-开端.md"
        self.write(f, "字" * 3200)
        self.ok("chapter", "add", self.book, 1, "--file", f)
        self.ok("chapter", "hook", self.book, 1, "--type", "悬念", "--intensity", 4)
        code, out = run(self.book, 1, script=CHECK)
        self.assertEqual(code, 1, out)
        self.assertIn("水章", out)
        self.ok("promise", "add", self.book, "--type", "悬念", "--content", "门后", "--ch", 1)
        code, out = run(self.book, 1, script=CHECK)
        self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main(verbosity=1)
