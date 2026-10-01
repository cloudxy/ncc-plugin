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
- 默认写法：主角亮出底牌，众人震惊
- 关键节拍：揭穿的那一刻
"""
SCENE_SHORT = """## 场景 1
- 视角：陆言
- 目标：借到钱
- 翻转：从有退路到没有退路
- 两难：卖掉玉佩还是求林家
- 情感：压
"""


def run(*args, script=STATE, env=None):
    full_env = None
    if env:
        import os
        full_env = {**os.environ, **env}
    r = subprocess.run([sys.executable, script, *map(str, args)], capture_output=True, text=True, env=full_env)
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

    def bad(self, *args, code=1):
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
        self.assertIn("主题之问", self.bad("gate", self.book, "soul"))
        self.ok("soul", self.book, "--question", "Q", "--answer", "A", "--injustice", "I",
                "--ending", "E", "--status", "暂定")
        self.assertIn("最晚决定点", self.bad("gate", self.book, "soul"))
        self.ok("soul", self.book, "--deadline", "第一卷卷复盘")
        self.assertIn("主契约", self.bad("gate", self.book, "soul"))
        self.ok("contract", self.book, "--main", "凡人逆袭＋守护", "--poison", "主角降智,长期憋屈不反击")
        self.ok("gate", self.book, "soul")
        self.ok("gate", self.book, "soul", "--action", "pass", "--quote", "就这样")
        self.assertEqual(self.book_json()["stage"], "settings")

    def test_force_pass_needs_quote(self):
        self.bad("gate", self.book, "soul", "--action", "pass")
        self.bad("gate", self.book, "soul", "--action", "pass", "--force")
        self.ok("gate", self.book, "soul", "--action", "pass", "--force", "--quote", "先开写")
        g = self.book_json()["gates"]["soul"]
        self.assertEqual(g["status"], "passed")
        self.assertTrue(g["forced_over"])

    def test_level_mode_arc(self):
        self.ok("level", self.book, "老手")
        self.bad("level", self.book, "大神")
        self.ok("mode", self.book, "园丁")
        self.bad("mode", self.book, "随便")
        self.ok("soul", self.book, "--arc", "平弧")
        self.bad("soul", self.book, "--arc", "螺旋")
        d = self.book_json()
        self.assertEqual((d["experience_level"], d["mode"], d["soul"]["arc"]), ("老手", "园丁", "平弧"))


class TestSettingsGate(Base):
    def test_character_card_and_arc_required(self):
        self.write("01-设定/世界观圣经.md", "圣经")
        self.write("01-设定/力量体系.md", "量纲")
        rows = "\n".join(f"| 词{i} | 1 | a | b | 9 |" for i in range(30))
        self.write("01-设定/设定词典.md", "| 词条 | 首现章计划 | 读者已知 | 完整真相 | 计划揭示章 |\n|---|---|---|---|---|\n" + rows)
        out = self.bad("gate", self.book, "settings")
        self.assertIn("人物卡", out)
        self.assertIn("弧光", out)
        self.write("01-设定/人物卡/陆言.md", "欲望 需要 恐惧 伤口 声音")
        self.ok("soul", self.book, "--arc", "正向")
        self.assertIn("社会洞察", self.bad("gate", self.book, "settings"))
        self.write("01-设定/世界观圣经.md", "# 圣经\n## 社会洞察\n| 规矩 | 为什么 | 谁受益 | 谁受害 | 主角在哪 | 不公 |\n"
                   "|---|---|---|---|---|---|\n| 夜班不开灯 | 省电 | 厂方 | 工人 | 守夜 | 弱者付成本 |\n## 世界秘密\n")
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
        self.assertIn("故事审", self.bad("chapter", "mark", self.book, 5, "drafting"))
        self.assertIn("缺场景卡", self.bad("scene", "check", self.book, 5))
        self.write("02-大纲/场景卡/ch-0005.md", "## 场景 1\n- 视角：陆言\n- 目标：x\n")
        self.assertIn("翻转", self.bad("scene", "review", self.book, 5, "--result", "pass", "--by", "story-editor"))
        self.write("02-大纲/场景卡/ch-0005.md", SCENE_SHORT)
        self.ok("scene", "check", self.book, 5)
        self.ok("scene", "review", self.book, 5, "--result", "pass", "--by", "story-editor")
        self.ok("chapter", "mark", self.book, 5, "drafting")

    def test_edit_after_review_needs_rereview(self):
        self.add(6)
        self.write("02-大纲/场景卡/ch-0006.md", SCENE_SHORT)
        self.ok("scene", "review", self.book, 6, "--result", "pass", "--by", "story-editor")
        self.write("02-大纲/场景卡/ch-0006.md", SCENE_SHORT + "\n补一句")
        self.assertIn("改动", self.bad("chapter", "mark", self.book, 6, "drafting"))

    def test_key_chapter_needs_full_card_author_and_pick(self):
        self.add(1)                                  # 第 1–3 章默认关键章
        self.write("02-大纲/场景卡/ch-0001.md", SCENE_SHORT)
        self.assertIn("盲区", self.bad("scene", "check", self.book, 1))
        self.write("02-大纲/场景卡/ch-0001.md", SCENE_FULL.format(seq=1))
        self.assertIn("作者", self.bad("scene", "review", self.book, 1, "--result", "pass", "--by", "story-editor"))
        self.ok("scene", "review", self.book, 1, "--result", "pass", "--by", "author")
        self.assertIn("选定", self.bad("complete", self.book, 1, "--words", 3000, "--hard", "pass"))
        self.ok("chapter", "pick", self.book, 1, "--version", "B", "--note", "B 的反转更意外")
        self.bad("complete", self.book, 1, "--words", 3000, "--hard", "fail")
        self.ok("complete", self.book, 1, "--words", 3000, "--hard", "pass")

    def test_pick_only_for_key(self):
        self.add(9)
        self.assertIn("不是关键章", self.bad("chapter", "pick", self.book, 9, "--version", "A"))
        self.ok("chapter", "key", self.book, 9)
        self.ok("chapter", "pick", self.book, 9, "--version", "A")


class TestSlimming(Base):
    def test_scene_next_and_batch_review(self):
        out = self.ok("scene", "next", self.book)
        self.assertIn("第 1–3 章", out)
        self.ok("mode", self.book, "建筑师")
        self.assertIn("第 1–5 章", self.ok("scene", "next", self.book))
        for seq in (4, 5, 6):
            self.add(seq)
            self.write(f"02-大纲/场景卡/ch-{seq:04d}.md", SCENE_SHORT)
        self.ok("chapter", "key", self.book, 6)
        out = self.bad("scene", "review", self.book, 4, 5, 6, "--result", "pass", "--by", "story-editor")
        self.assertIn("整批未写入", out)
        self.assertEqual(self.book_json()["chapters"][0]["scenes"]["review"], "pending")
        self.ok("chapter", "key", self.book, 6, "--off")
        self.ok("scene", "review", self.book, 4, 5, 6, "--result", "pass", "--by", "story-editor")
        self.assertTrue(all(c["scenes"]["review"] == "passed" for c in self.book_json()["chapters"]))
        self.assertIn("第 7–11 章", self.ok("scene", "next", self.book))

    def test_pack_contents_and_soul_guard(self):
        self.ok("soul", self.book, "--question", "谁有资格定义一个人的价值", "--answer", "A", "--injustice", "I", "--ending", "E")
        self.write("01-设定/人物卡/陆言.md", "# 陆言\n## 欲望\n拿回工牌\n## 恐惧\n父亲丢工作\n## 声音\n\"行，我记着。\"\n")
        self.write("00-策划/作者种子.md", "| # | 问题 | 回答 |\n|---|---|---|\n| 1 | 画面 | 雨里的工牌 |\n| 2 | 在乎的问题 | 不该出现 |\n")
        self.ok("fact", "set", self.book, "陆言", "高三", "--ch", 0)
        self.write("01-设定/设定词典.md", "| 词条 | 首现章计划 | 读者已知 | 完整真相 | 计划揭示章 |\n|---|---|---|---|---|\n| 陆言 | 1 | 高三学生 | 死亡之书的宿主 | 卷二 |\n")
        self.add(4)
        self.assertIn("故事审", self.bad("pack", self.book, 4))
        self.write("02-大纲/场景卡/ch-0004.md", SCENE_SHORT)
        self.ok("scene", "review", self.book, 4, "--result", "pass", "--by", "story-editor")
        self.ok("pack", self.book, 4, "--note", "注意雨声")
        pack = (self.book / "04-正文/_packs/ch-0004.md").read_text("utf-8")
        for key in ("写作简报", "读者此刻", "人物声音", "拿回工牌", "我记着", "雨里的工牌", "陆言 = 高三", "注意雨声"):
            self.assertIn(key, pack)
        self.assertIn("读者目前知道「高三学生」", pack)
        for banned in ("不该出现", "谁有资格定义", "硬伤", "审稿清单", "死亡之书的宿主"):
            self.assertNotIn(banned, pack)
        self.write("02-大纲/场景卡/ch-0004.md", SCENE_SHORT + "- 主题：谁有资格定义一个人的价值\n")
        self.ok("scene", "review", self.book, 4, "--result", "pass", "--by", "story-editor")
        self.assertIn("书魂原文", self.bad("pack", self.book, 4))

    def test_review_plan_and_delta(self):
        self.add(4)
        self.assertIn("不派", self.ok("review", "plan", self.book, 4))
        self.ok("promise", "add", self.book, "--type", "爽点欠账", "--content", "退婚", "--ch", 1)
        self.ok("promise", "resolve", self.book, "P-0001", "--ch", 4)
        self.assertIn("本章兑现", self.ok("review", "plan", self.book, 4))
        self.assertIn("开篇", self.plan_opening())
        self.write("04-正文/第0004章-x.md", "第一段\n\n第二段改了\n\n第三段")
        self.ok("review", "plan", self.book, 4)
        self.write("04-正文/第0004章-x.md", "第一段\n\n第二段又改了\n\n第三段")
        out = self.ok("review", "delta", self.book, 4)
        self.assertIn("第二段又改了", out)
        self.assertNotIn("第一段", out)
        self.assertIn("没有改动", self.ok("review", "delta", self.book, 4))

    def plan_opening(self):
        self.add(2)
        return self.ok("review", "plan", self.book, 2)


class TestChaptersAndPromises(Base):
    def test_hook_and_retry(self):
        self.add(4)
        self.bad("chapter", "add", self.book, 4, "--file", "x.md")
        self.ok("chapter", "hook", self.book, 4, "--type", "悬念", "--intensity", 4)
        self.bad("chapter", "hook", self.book, 4, "--type", "悬念", "--intensity", 9)
        self.bad("chapter", "mark", self.book, 4, "done")
        for _ in range(3):
            self.ok("chapter", "retry", self.book, 4)
        self.assertEqual(self.book_json()["chapters"][0]["status"], "failed")

    def test_mood_palette_and_legacy(self):
        self.add(4)
        self.ok("chapter", "mood", self.book, 4, "放", "--colors", "燃,悲")
        self.ok("chapter", "mood", self.book, 4, "释放")
        self.bad("chapter", "mood", self.book, 4, "放", "--colors", "开心")
        self.assertEqual(self.book_json()["chapters"][0]["mood"]["tension"], "放")

    def test_promise_lifecycle_and_water(self):
        self.bad("water", self.book, 2)
        out = self.ok("promise", "add", self.book, "--type", "悬念", "--content", "门后是什么",
                      "--ch", 1, "--strength", 4, "--window", "5-8")
        pid = out.split()[1]
        self.ok("water", self.book, 1)
        self.ok("promise", "touch", self.book, pid, "--ch", 2, "--note", "门缝有光")
        self.ok("water", self.book, 2)
        self.bad("water", self.book, 3)
        self.bad("promise", "drop", self.book, pid, "--ch", 3, "--compensation", " ")
        self.ok("promise", "resolve", self.book, pid, "--ch", 6)
        self.bad("promise", "touch", self.book, pid, "--ch", 7)
        self.assertEqual(self.book_json()["promises"]["resolved"], 1)

    def test_option_and_motif_do_not_count_against_water(self):
        self.ok("promise", "add", self.book, "--type", "期权", "--content", "老人手上的旧伤", "--ch", 3)
        self.ok("promise", "add", self.book, "--type", "母题", "--content", "雨中的工牌", "--ch", 3)
        self.bad("water", self.book, 3)
        out = self.ok("promise", "add", self.book, "--type", "名场面", "--content", "守城夜", "--ch", 3)
        self.assertTrue(out.split()[1].startswith("SC-"))
        self.ok("water", self.book, 3)

    def test_tentative_decision_needs_deadline_and_goes_overdue(self):
        self.bad("promise", "add", self.book, "--type", "暂定决策", "--content", "反派身份", "--ch", 1)
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
        self.bad("fact", "set", self.book, "青云城到落霞镇", "一日", "--ch", 12)
        self.ok("fact", "set", self.book, "青云城到落霞镇", "一日", "--ch", 12, "--override")
        facts = json.loads((self.book / "06-台账/知识台账.json").read_text("utf-8"))["facts"]
        self.assertEqual(facts["青云城到落霞镇"]["history"][0]["value"], "三日")


class TestOpeningGate(Base):
    def test_opening_requirements(self):
        for seq in (1, 2, 3):
            self.finish(seq)
        out = self.bad("gate", self.book, "opening")
        self.assertIn("盲评", out)
        self.assertIn("签约点未落地", out)
        self.write("05-审稿/blind-ch-0001-0003.md", "盲评")
        self.assertIn("记忆测试", self.bad("gate", self.book, "opening"))
        self.write("05-审稿/blind-ch-0001-0003.md", "盲评\n## 记忆测试\n记住了工牌")
        for pt in ("主角与欲望", "世界的不公", "主角的机会", "第一次小兑现", "长线钩子"):
            self.ok("sign", self.book, pt, "--ch", 2)
        self.ok("gate", self.book, "opening")

    def test_volume_gate_outside_review(self):
        self.assertIn("不在卷复盘阶段", self.bad("gate", self.book, "volume"))


class TestLoops(Base):
    def serial(self):
        d = self.book_json()
        d["stage"] = "serial"
        (self.book / "book.json").write_text(json.dumps(d, ensure_ascii=False), "utf-8")

    def test_unit_needs_review_before_close(self):
        self.ok("unit", "open", self.book, "--start", 4, "--title", "工厂夜班")
        self.bad("unit", "open", self.book, "--start", 5)
        self.finish(4)
        report = self.ok("report", self.book, "unit")
        for sec in ("暂定决策", "故事审", "下一单元", "失去", "读者数据"):
            self.assertIn(sec, report)
        self.assertIn("复盘", self.bad("unit", "close", self.book, "--end", 4))
        self.write("00-策划/复盘/单元-U1.md", report)
        self.ok("unit", "close", self.book, "--end", 4)

    def test_volume_cycle(self):
        self.serial()
        self.ok("promise", "add", self.book, "--type", "伏笔", "--content", "玉佩", "--ch", 1, "--window", "2-3")
        self.finish(4)
        self.ok("volume", "end", self.book, "--end", 4)
        self.assertEqual(self.book_json()["stage"], "volume")
        out = self.bad("gate", self.book, "volume")
        self.assertIn("卷1.md", out)
        self.assertIn("逾期", out)
        self.write("00-策划/复盘/卷1.md", self.ok("report", self.book, "volume"))
        self.assertIn("强化", self.bad("promise", "reschedule", self.book, "FS-0001", "--window", "8-10", "--note", " "))
        self.ok("promise", "reschedule", self.book, "FS-0001", "--window", "8-10", "--note", "第 6 章再露一角")
        self.ok("soul", self.book, "--status", "暂定", "--deadline", "第一卷卷复盘")
        self.assertIn("D7", self.bad("gate", self.book, "volume"))
        self.ok("soul", self.book, "--status", "确定")
        self.ok("gate", self.book, "volume", "--action", "pass", "--quote", "进第二卷")
        d = self.book_json()
        self.assertEqual(d["stage"], "serial")
        self.assertEqual([(v["n"], v["status"]) for v in d["volumes"]], [(1, "closed"), (2, "open")])
        self.assertEqual(d["volumes"][1]["start"], 5)

    def test_finale(self):
        self.bad("finale", "begin", self.book)
        self.serial()
        self.ok("promise", "add", self.book, "--type", "悬念", "--content", "门后", "--ch", 1)
        self.ok("finale", "begin", self.book)
        out = self.bad("gate", self.book, "finale")
        for key in ("P-0001", "书魂", "收束清单", "全书", "技艺库"):
            self.assertIn(key, out)
        self.ok("promise", "resolve", self.book, "P-0001", "--ch", 300)
        self.ok("soul", self.book, "--question", "Q", "--answer", "A", "--injustice", "I", "--ending", "E", "--status", "确定")
        self.write("00-策划/收束清单.md", self.ok("report", self.book, "finale"))
        self.write("00-策划/复盘/全书.md", "全书复盘")
        lib = self.book.parent / "_craft-library" / "测试书.md"
        lib.parent.mkdir(parents=True, exist_ok=True)
        lib.write_text("技艺条目", "utf-8")
        self.ok("gate", self.book, "finale", "--action", "pass", "--quote", "完本")
        self.assertEqual(self.book_json()["stage"], "finished")

    def test_feedback_calibration_in_report(self):
        self.ok("unit", "open", self.book, "--start", 4)
        self.finish(4)
        self.bad("feedback", "add", self.book, "--ch", 4, "--source", "猜的", "--kind", "追读", "--value", 3)
        self.ok("feedback", "add", self.book, "--ch", 4, "--source", "模拟", "--kind", "追读", "--value", 4)
        self.ok("feedback", "add", self.book, "--ch", 4, "--source", "真实", "--kind", "追读", "--value", "62%")
        self.assertIn("模拟 4｜真实 62%", self.ok("report", self.book, "unit"))

    def test_publish_buffer_and_team_log(self):
        for seq in (4, 5):
            self.finish(seq)
        self.ok("chapter", "publish", self.book, "--upto", 4)
        self.assertIn("低于存稿线", self.ok("status", self.book))
        self.bad("team", "set", self.book, "校长", "老王")
        code, out = run("team", "set", self.book, "主笔", "小李", env={"NCC_ACTOR": "老王"})
        self.assertEqual(code, 0, out)
        self.assertIn("主笔: 小李", self.ok("team", "list", self.book))
        log = (self.book / "06-台账/操作日志.jsonl").read_text("utf-8").strip().splitlines()
        last = json.loads(log[-1])
        self.assertEqual((last["actor"], last["argv"][0]), ("老王", "team"))
        self.assertFalse(any(json.loads(x)["argv"][0] == "status" for x in log))


KNOW_OK = """| 知识点 | 学科 | 写成什么 | 来源 | 状态 |
|---|---|---|---|---|
| 当天月相 | 天文 | 农历初三，傍晚西天一弯月牙 | 月相与日期对照 | 已核 |
| 行军里程 | 历史 | 一日三十里 | 《左传》 | 已核 |
| 丹炉火候 | 化学 | 火色由红转白 | —— | 待核 |
"""


class TestKnowledge(Base):
    def card(self, seq, extra=""):
        self.add(seq)
        self.write(f"02-大纲/场景卡/ch-{seq:04d}.md", SCENE_SHORT + extra)
        self.ok("scene", "review", self.book, seq, "--result", "pass", "--by", "story-editor")

    def test_plan_and_check(self):
        self.card(4)
        self.card(5, "- 知识：月相；行军里程\n")
        out = self.ok("knowledge", "plan", self.book, 4, 5)
        self.assertIn("第 5 章：月相；行军里程", out)
        self.assertIn("派 scholar（一次）做第 5 章", out)
        self.assertIn("不派", self.ok("knowledge", "plan", self.book, 4))
        self.assertIn("缺知识点清单", self.bad("knowledge", "check", self.book, 5))
        self.write("02-大纲/知识点/ch-0005.md", KNOW_OK.replace("| 天文 |", "| 星象学 |").replace("| 月相与日期对照 |", "| —— |"))
        out = self.bad("knowledge", "check", self.book, 5)
        self.assertIn("不是 24 张卡之一", out)
        self.assertIn("没有来源", out)
        self.write("02-大纲/知识点/ch-0005.md", KNOW_OK.replace("火色由红转白", "炉温升到八百度"))
        self.assertIn("宁缺律", self.bad("knowledge", "check", self.book, 5))
        self.write("02-大纲/知识点/ch-0005.md", KNOW_OK)
        self.assertIn("3 条，待核 1 条", self.ok("knowledge", "check", self.book, 5))

    def test_complete_and_pack(self):
        self.card(5, "- 知识：月相\n")
        self.assertIn("知识点清单不合格", self.bad("complete", self.book, 5, "--words", 3000, "--hard", "pass"))
        self.write("02-大纲/知识点/ch-0005.md", KNOW_OK)
        self.ok("pack", self.book, 5)
        pack = (self.book / "04-正文/_packs/ch-0005.md").read_text("utf-8")
        self.assertIn("本章知识点", pack)
        self.assertIn("火色由红转白（待核：不写具体数字和术语", pack)
        self.assertNotIn("《左传》", pack)
        self.ok("complete", self.book, 5, "--words", 3000, "--hard", "pass")
        self.assertIn("待核知识点 1", self.ok("status", self.book))

    def test_era_study_and_warnings(self):
        self.bad("era", self.book, "唐朝")
        self.ok("era", self.book, "古代")
        self.bad("study", self.book, "--add", "占星")
        self.assertIn("天文、宗教神话民俗", (self.ok("study", self.book, "--add", "天文"), self.ok("study", self.book, "--add", "民俗"))[1])
        f = "04-正文/第0004章-x.md"
        self.write(f, "字" * 3200 + "他掏出手机。我令尊说了。初三夜里，一轮明月挂在天上。")
        self.ok("chapter", "add", self.book, 4, "--file", f)
        self.ok("chapter", "hook", self.book, 4, "--type", "悬念", "--intensity", 3)
        self.ok("promise", "add", self.book, "--type", "悬念", "--content", "x", "--ch", 4)
        self.ok("fact", "set", self.book, "初三", "月牙", "--ch", 1)
        code, out = run(self.book, 4, script=CHECK)
        self.assertEqual(code, 0, out)
        for key in ("时代错置词", "手机", "敬称用在自己身上", "月相与日期可能不符", "初三=月牙"):
            self.assertIn(key, out)

    def test_volume_report_knowledge(self):
        d = self.book_json()
        d["stage"] = "serial"
        (self.book / "book.json").write_text(json.dumps(d, ensure_ascii=False), "utf-8")
        self.card(4, "- 知识：月相\n")
        self.write("02-大纲/知识点/ch-0004.md", KNOW_OK)
        self.ok("feedback", "add", self.book, "--ch", 4, "--source", "真实", "--kind", "出戏", "--value", "天文", "--note", "满月日期不对")
        self.ok("volume", "end", self.book, "--end", 4)
        out = self.ok("report", self.book, "volume")
        self.assertIn("## 底蕴", out)
        self.assertIn("天文：知识点 1 条，待核 0 条；出戏 1 处", out)
        self.assertIn("化学：知识点 1 条，待核 1 条", out)


class TestMaterials(Base):
    def add_material(self, *extra):
        return self.ok("material", "add", self.book, "--content", "凌晨四点换岗，接班的人先摸暖气片",
                       "--source", "作者 2019 年物流园夜班", "--use", "底层人物的疲惫", *extra)

    def test_add_list_check(self):
        out = self.add_material("--domain", "社会", "--trust", "亲历")
        self.assertIn("M-0001", out)
        self.assertTrue(list((self.book / "素材/乙-人间").glob("M-0001-*.md")))
        self.ok("material", "add", self.book, "--content", "医院走廊里有人蹲着吃泡面", "--source", "表姐讲的",
                "--use", "陪护的狼狈", "--trust", "转述", "--shared")
        self.assertTrue(list((self.book.parent / "_素材").rglob("MS-0001-*.md")))
        self.bad("material", "add", self.book, "--content", "x", "--source", "y", "--use", "z", "--domain", "占星")
        self.bad("material", "add", self.book, "--content", "x", "--source", "y", "--use", "z", "--trust", "听说")
        out = self.ok("material", "check", self.book)
        self.assertIn("2 张", out)
        self.assertIn("至少 10 张", out)
        self.write("素材/未分/M-0002-坏卡.md", "# M-0002 坏卡\n- 来源：\n- 内容：x\n")
        out = self.bad("material", "check", self.book)
        self.assertIn("缺「来源」", out)
        self.assertIn("缺「可用处」", out)
        self.assertIn("M-0001", self.ok("material", "list", self.book, "--domain", "社会"))

    def test_scene_reference_pack_and_report(self):
        self.add_material("--trust", "亲历")
        self.ok("material", "add", self.book, "--content", "医院走廊里有人蹲着吃泡面", "--source", "表姐讲的",
                "--use", "陪护的狼狈", "--trust", "转述")
        self.add(4)
        self.write("02-大纲/场景卡/ch-0004.md", SCENE_SHORT + "- 素材：M-0009\n")
        self.assertIn("素材卡不存在", self.bad("scene", "check", self.book, 4))
        self.write("02-大纲/场景卡/ch-0004.md", SCENE_SHORT + "- 素材：M-0001、M-0002\n")
        self.ok("scene", "review", self.book, 4, "--result", "pass", "--by", "story-editor")
        self.ok("pack", self.book, 4)
        pack = (self.book / "04-正文/_packs/ch-0004.md").read_text("utf-8")
        self.assertIn("素材 M-0001：凌晨四点换岗", pack)
        self.assertIn("能认出本人的细节都要换掉", pack)
        self.assertNotIn("物流园夜班", pack)            # 来源不进写手包
        self.ok("unit", "open", self.book, "--start", 4)
        self.ok("complete", self.book, 4, "--words", 3000, "--hard", "pass")
        rep = self.ok("report", self.book, "unit")
        self.assertIn("## 素材", rep)
        self.assertIn("M-0001（第4章）", rep)
        self.assertIn("素材: 2 张", self.ok("status", self.book))


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

    def test_ai_grading_and_waiver(self):
        f = "04-正文/第0004章-开端.md"
        self.write(f, "字" * 3200 + "他不是冷漠，而是绝望。")
        self.ok("chapter", "add", self.book, 4, "--file", f)
        self.ok("chapter", "hook", self.book, 4, "--type", "悬念", "--intensity", 4)
        self.ok("promise", "add", self.book, "--type", "悬念", "--content", "门后", "--ch", 4)
        code, out = run(self.book, 4, script=CHECK)
        self.assertEqual(code, 1, out)
        self.assertIn("五星句式", out)
        self.write("03-文风/放行清单.md", "- 「他不是冷漠，而是绝望」：第4章，主角自辩，有意为之\n")
        code, out = run(self.book, 4, script=CHECK)
        self.assertEqual(code, 0, out)
        self.assertIn("rhythm_reference", out)
        self.write(f, "字" * 3200 + "他知道。仿佛一丝一抹些许。")
        code, out = run(self.book, 4, script=CHECK)
        self.assertEqual(code, 1, out)
        self.assertIn("合计 5 处", out)

    def test_avoidance_warnings(self):
        f = "04-正文/第0004章-开端.md"
        talk = "\n".join(f"“第{i}句话说完了。”" for i in range(12))
        long_sentence = "，".join(["他走"] * 12) + "。"
        self.write(f, "字" * 3200 + "\n" + talk + "\n" + long_sentence + "\n")
        self.ok("chapter", "add", self.book, 4, "--file", f)
        self.ok("chapter", "hook", self.book, 4, "--type", "悬念", "--intensity", 4)
        self.ok("promise", "add", self.book, "--type", "悬念", "--content", "门后", "--ch", 4)
        code, out = run(self.book, 4, script=CHECK)
        self.assertEqual(code, 0, out)                   # 规避点只告警
        self.assertIn("规避点：长段", out)
        self.assertIn("规避点：长句", out)
        self.assertIn("对白流", out)
        self.assertIn("dialogue_share", out)


if __name__ == "__main__":
    unittest.main(verbosity=1)
