"""分层拆书的公开合成验收；不读真实书库，不调用模型。"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from ncclib.deconstruction import index, planning, ingest, storage, reporting
from ncclib.deconstruction.common import DECON_CFG as CFG, DeconError, read, write, rows, local, digest, locked
from ncclib.deconstruction.contracts import validate
from ncclib.decon import baseline


class DeconstructionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='ncc decon ')
        self.addCleanup(self.tmp.cleanup)
        self.lib = Path(self.tmp.name) / 'library'
        (self.lib / '原文').mkdir(parents=True)
        self.src = self.lib / '原文/synthetic.txt'
        self.framework = Path(self.tmp.name) / 'framework.md'
        self.framework.write_text('合成总纲路径替身，只供机械接口用例；不代替真实5.0。\n')
        self.prepare()

    def prepare(self, count=4, select=None, screenplay='none'):
        self.src.write_text('\n'.join(f'第{n}章 灯影\n青石门前灯未灭，林舟问船夫何时能过河。林舟又名胡爷。守门人也被称为胡爷，缓缓收起旧伞。' for n in range(1, count + 1)))
        self.idx = index.create(self.lib)
        self.plan = planning.make_plan(self.lib, 'technique' if select else 'full', select, '合成的定向研究' if select else None, screenplay)

    def packet(self, seq=1, independent=False):
        return planning.packet(self.lib, seq, independent=independent, framework=self.framework)[1]

    def payload(self, seq=1, packet=None):
        packet = packet or self.packet(seq)
        value = {'schema_version': 1, 'chapter': seq, 'chapter_hash': self.idx['chapters'][seq - 1]['hash'],
                 'packet_fingerprint': packet['fingerprint'], 'summary': '旅人询问渡河条件',
                 'empty_reason': '本合成章中其余类型没有可确认事实'}
        value.update({key: [] for key in ingest.COLLECTIONS})
        value['events'] = [{'description': '旅人询问过河的办法', 'evidence': '青石门前灯未灭', 'confidence': '原文明说'}]
        return value

    def submit(self, payload):
        path = self.lib / 'input.json'
        write(path, payload)
        return ingest.ingest(self.lib, path)

    def scene(self, seq=1):
        return {'chapter': seq, 'order': 1, 'slugline': '渡口·时刻未知', 'int_ext': '外', 'place': '渡口', 'time_of_day': '',
                'characters': ['traveler'], 'objective': '弄清过河的条件', 'obstacle': '仍需等候', 'turn': '', 'outcome': '继续等待',
                'actions': ['向船夫提问'], 'dialogue': [{'speaker': 'traveler', 'intent': '询问通行办法', 'subtext': '', 'locator': '林舟问船夫何时'}],
                'locator': '青石门前灯未灭', 'confidence': '原文明说', 'unknown_reason': '时刻与转折未明，不补造'}

    def entity(self, name='林舟', local_id='traveler', aliases=None):
        return {'name': name, 'local_id': local_id, 'category': '人物', 'aliases': aliases or [], 'evidence': '青石门前灯未灭', 'confidence': '原文明说'}

    def test_contract_versions_types_and_strict_json(self):
        value = self.payload()
        for change in ({'schema_version': 0}, {'chapter': True}, {'events': {}}, {'chapter_hash': None}):
            with self.subTest(change=change), self.assertRaises(DeconError):
                validate('chapter', {**value, **change})
        path = self.lib / 'bad.json'
        for text in ('{"a":1,"a":2}', '{"a":NaN}', '{"events": [}'):
            path.write_text(text)
            with self.assertRaises(DeconError):
                read(path)

    def test_index_volume_echo_parts_gaps_and_short_are_usable(self):
        text = (Path(__file__).parent / 'fixtures/deconstruction/multi-volume.txt').read_text()
        chapters, diagnostics = index.build(text)
        self.assertFalse(diagnostics['blockers'])
        self.assertEqual([c['seq'] for c in chapters], [1, 2, 3, 4, 5])
        self.assertEqual([c['no'] for c in chapters], [0, 1, 1, 3, 1])
        self.assertEqual([c['part'] for c in chapters[1:3]], ['上', '下'])
        self.assertEqual(diagnostics['ignored_echo_lines'], [5])
        self.assertIn('number_gap', {r['code'] for r in diagnostics['warnings']})
        self.assertNotEqual(chapters[1]['volume'], chapters[-1]['volume'])

    def test_real_duplicate_empty_unassigned_and_force_are_blocked(self):
        for text in ('第一章 雨\n正文有灯。\n第一章 雨\n正文有伞。', '第一章 空\n第二章 有\n正文。', '被遗漏的卷引\n第一章 起\n正文。'):
            with self.subTest(text=text):
                self.assertTrue(index.build(text)[1]['blockers'])
        self.src.write_text('第一章 空\n第二章 有\n正文。')
        before = local(self.lib, CFG['index']).read_bytes()
        proc = subprocess.run([sys.executable, str(SCRIPTS / 'ncc_state.py'), 'decon', 'index', str(self.lib), '--force'], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(local(self.lib, CFG['index']).read_bytes(), before)
        self.assertTrue(read(local(self.lib, CFG['diagnostics']))['blockers'])

    def test_manual_boundaries_require_explanation_and_do_not_overlap(self):
        text = '第一章 同题\n正文甲。\n第一章 同题\n正文乙。'
        config = {'chapters': [{'start': 1, 'end': 2, 'no': 1, 'reason': '核对不同章节'}, {'start': 3, 'end': 4, 'no': 1, 'reason': '核对不同章节'}]}
        self.assertFalse(index.build(text, config)[1]['blockers'])
        config['chapters'][0]['end'] = 4
        with self.assertRaises(DeconError):
            index.build(text, config)

    def test_long_book_default_plan_is_bounded_and_unselected_not_skipped(self):
        # Use a fresh library to avoid exercising the explicit reindex path here.
        self.src.write_text('\n'.join(f'第{n}章 起\n合成正文有灯。' for n in range(1, 1002)))
        self.idx = index.create(self.lib, accept=True)
        plan = planning.make_plan(self.lib, 'technique')
        self.assertLessEqual(len(plan['selected']), 27)
        self.assertEqual(plan['groups']['opening'], list(range(1, 11)))
        self.assertEqual(plan['groups']['ending'], list(range(992, 1002)))
        self.assertEqual(plan['groups']['interior'], [126, 251, 376, 501, 626, 751, 876])
        state = read(local(self.lib, CFG['progress']))
        self.assertEqual(state['done'], [])
        self.assertEqual(state['skipped'], {})
        self.assertEqual(state['layers']['L2']['planned'], plan['selected'])

    def test_sparse_context_does_not_use_previous_sample_and_independent_is_local(self):
        self.submit(self.payload())
        with self.assertRaisesRegex(DeconError, '三件套'):
            self.packet(3)
        packet = self.packet(3, independent=True)
        value = self.payload(3, packet)
        value['entities'] = [self.entity('船夫', 'boatman')]
        receipt = self.submit(value)
        self.assertTrue(receipt['base_complete'])
        self.assertEqual(rows(local(self.lib, CFG['ledgers']['实体'])), [])
        self.assertTrue(receipt['chapter_facts']['实体'])

    def test_good_ingest_is_idempotent_and_adjacent_context_is_sourced(self):
        value = self.payload()
        value['entities'] = [self.entity()]
        self.submit(value)
        ledger = local(self.lib, CFG['ledgers']['事件'])
        before = ledger.read_bytes()
        self.submit(value)
        self.assertEqual(ledger.read_bytes(), before)
        self.assertEqual(len(rows(ledger)), 1)
        packet = self.packet(2)
        self.assertEqual(packet['context']['dependencies'], [1])
        self.assertTrue(all(s.get('path') for s in packet['context']['sources']))
        self.assertNotIn(2, [r.get('chapter') for r in packet['context']['entities']])

    def test_file_errors_do_not_complete_or_modify_input(self):
        value = self.payload()
        value['chapter_hash'] = 'wrong'
        path = self.lib / 'bad-input.json'
        write(path, value)
        before = path.read_bytes()
        with self.assertRaises(DeconError):
            ingest.ingest(self.lib, path)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(read(local(self.lib, CFG['progress']))['layers']['L2']['done'], [])
        self.assertTrue(local(self.lib, CFG['ingest_report'] + '/latest-error.json').exists())

    def test_bad_fact_is_quarantined_while_good_fact_survives(self):
        value = self.payload()
        value['state_events'] = [{'entity': 'E-missing', 'attribute': '高度', 'new': 9, 'evidence': '青石门前灯未灭', 'confidence': '原文明说'}]
        receipt = self.submit(value)
        self.assertTrue(receipt['base_complete'])
        self.assertTrue(receipt['rejected'])
        self.assertEqual(len(rows(local(self.lib, CFG['ledgers']['事件']))), 1)
        self.assertEqual(rows(local(self.lib, CFG['ledgers']['状态事件'])), [])

    def test_missing_collections_and_all_weak_facts_do_not_complete(self):
        value = self.payload()
        value.pop('relations')
        self.assertFalse(self.submit(value)['base_complete'])
        value = self.payload()
        value['events'][0]['confidence'] = '弱推断'
        result = self.submit(value)
        self.assertFalse(result['base_complete'])
        self.assertTrue(result['pending'])
        self.assertNotIn(1, read(local(self.lib, CFG['progress']))['layers']['L2']['done'])

    def test_alias_conflict_and_same_time_state_conflict_are_not_first_wins(self):
        value = self.payload()
        alias = {'name': '胡爷', 'kind': 'proper', 'same_entity': True, 'evidence': '青石门前灯未灭'}
        value['entities'] = [self.entity(aliases=[alias]), self.entity('守门人', 'guard', [alias])]
        common = {'entity': 'traveler', 'attribute': '力量源', 'evidence': '青石门前灯未灭', 'confidence': '原文明说'}
        value['state_events'] = [{**common, 'new': '灯火'}, {**common, 'new': '潮水'}]
        self.submit(value)
        aliases = read(local(self.lib, CFG['alias_index']))
        self.assertNotIn('胡爷', aliases['aliases'])
        self.assertEqual(len(aliases['conflicts']['胡爷']), 2)
        self.assertEqual(rows(local(self.lib, CFG['ledgers']['状态事件'])), [])
        self.assertTrue(rows(local(self.lib, CFG['conflicts'])))
        for item in value['state_events']:
            item['mode'] = 'coexist'
        self.submit(value)
        self.assertEqual(len(rows(local(self.lib, CFG['ledgers']['状态事件']))), 2)

    def test_scene_completion_is_separate_and_references_stay_in_library(self):
        planning.make_plan(self.lib, 'full', screenplay='1')
        value = self.payload()
        value['entities'] = [self.entity()]
        result = self.submit(value)
        self.assertTrue(result['base_complete'])
        self.assertFalse(result['scene_complete'])
        value['screenplay'] = {'act': '', 'logline': '旅人被迫等待过河', 'scenes': [self.scene()]}
        result = self.submit(value)
        self.assertTrue(result['scene_complete'], result['scene_errors'])
        self.assertEqual(rows(local(self.lib, CFG['scenes']))[0]['characters'], [result['ledgers']['实体'][0]['id']])
        self.assertTrue(local(self.lib, CFG['scene_references'] + '/ch-0001.json').exists())
        self.assertFalse((self.lib / '02-大纲').exists())
        value['screenplay']['scenes'][0]['actions'] *= 5
        self.assertFalse(self.submit(value)['scene_complete'])

    def test_empty_power_and_later_change_are_allowed_but_same_time_contradiction_is_quarantined(self):
        first = self.payload()
        first['entities'] = [{**self.entity(), 'power_source': None}]
        fact = {'entity': 'traveler', 'attribute': '力量源', 'new': '灯火', 'time': '初见', 'evidence': '青石门前灯未灭', 'confidence': '原文明说'}
        first['state_events'] = [fact]
        result = self.submit(first)
        ident = result['ledgers']['实体'][0]['id']
        self.assertFalse(result['conflicts'])
        second = self.payload(2, self.packet(2))
        second['state_events'] = [{**fact, 'entity': ident, 'new': '潮水', 'time': '重逢'}]
        self.assertFalse(self.submit(second)['conflicts'])
        third = self.payload(3, self.packet(3))
        third['state_events'] = [{**fact, 'entity': ident, 'new': '风声', 'time': '重逢'}]
        self.assertTrue(self.submit(third)['conflicts'])
        states = rows(local(self.lib, CFG['ledgers']['状态事件']))
        self.assertEqual([r['new'] for r in states], ['灯火'])

    def test_receipt_commit_can_recover_after_progress_write_failure(self):
        value = self.payload()
        original = storage.write
        def interrupted(path, data):
            if Path(path) == local(self.lib, CFG['progress']):
                raise OSError('injected crash after receipt commit')
            return original(path, data)
        with patch.object(storage, 'write', side_effect=interrupted), self.assertRaises(OSError):
            self.submit(value)
        ingest.ingest(self.lib, recover=True)
        ingest.ingest(self.lib, recover=True)
        self.assertEqual(read(local(self.lib, CFG['progress']))['layers']['L2']['done'], [1])
        self.assertEqual(len(rows(local(self.lib, CFG['ledgers']['事件']))), 1)

    def test_interruptions_before_and_after_commit_restore_one_consistent_version(self):
        original = self.payload()
        self.submit(original)
        for point in ('raw', 'receipt', 'ledger', 'progress'):
            with self.subTest(point=point):
                self.submit(original)
                changed = json.loads(json.dumps(original))
                changed['events'][0]['description'] = '新的自写观察说明'
                target = {'raw': CFG['chapter_dir'] + '/ch-0001.json', 'receipt': CFG['receipts'] + '/ch-0001.json',
                          'ledger': CFG['ledgers']['事件'], 'progress': CFG['progress']}[point]
                method = 'write_rows' if point == 'ledger' else 'write'
                real = getattr(storage, method)
                def crash(path, value):
                    if Path(path) == local(self.lib, target):
                        raise OSError('injected ' + point)
                    return real(path, value)
                with patch.object(storage, method, side_effect=crash), self.assertRaises(OSError):
                    self.submit(changed)
                ingest.ingest(self.lib, recover=True)
                records = rows(local(self.lib, CFG['ledgers']['事件']))
                self.assertEqual(len(records), 1)
                expected = original if point in ('raw', 'receipt') else changed
                self.assertEqual(records[0]['description'], expected['events'][0]['description'])
                self.assertEqual(read(local(self.lib, CFG['chapter_dir'] + '/ch-0001.json')), expected)

    def test_changed_context_invalidates_dependents_and_missing_ledgers_are_recoverable(self):
        self.submit(self.payload())
        second = self.payload(2, self.packet(2))
        self.submit(second)
        first = self.payload()
        first['summary'] = '修改后的首章自写概括'
        self.submit(first)
        state = reporting.coverage(self.lib, 'L2')
        self.assertNotIn(2, state['done'])
        ledger = local(self.lib, CFG['ledgers']['事件'])
        ledger.unlink()
        ingest.ingest(self.lib, recover=True)
        self.assertTrue(ledger.is_file())
        self.assertEqual(len(rows(ledger)), 1)

    def test_reindex_requires_acknowledgment_and_does_not_move_done_by_seq(self):
        self.submit(self.payload())
        self.src.write_text('序\n从前有条河。\n' + self.src.read_text())
        with self.assertRaisesRegex(DeconError, '重建影响'):
            index.create(self.lib)
        self.assertTrue(local(self.lib, CFG['reindex_report']).exists())
        idx = index.create(self.lib, accept=True)
        planning.make_plan(self.lib, 'full')
        self.assertEqual(storage.receipts(self.lib, idx), [])
        self.assertEqual(read(local(self.lib, CFG['progress']))['done'], [])

    def test_sample_stats_never_emit_whole_density_and_range_report_is_separate(self):
        planning.make_plan(self.lib, 'technique', '1,3', '定向稀疏样本', 'none')
        self.submit(self.payload())
        self.submit(self.payload(3, self.packet(3, independent=True)))
        result, target = reporting.statistics(self.lib, None, None, baseline)
        self.assertEqual(result['scope'], 'sample')
        self.assertNotIn('爽点', result)
        self.assertIn('最长连续压抑', result['unavailable'])
        self.assertNotEqual(target, CFG['baseline'])
        _, target = reporting.statistics(self.lib, (1, 1), None, baseline)
        self.assertEqual(target, CFG['range_reports'] + '/1-1.json')

    def test_transfer_uses_only_accepted_projections_and_survives_without_original(self):
        planning.make_plan(self.lib, 'technique', '1,3', '两个独立观察点', 'none')
        self.submit(self.payload())
        self.submit(self.payload(3, self.packet(3, independent=True)))
        planning.make_plan(self.lib, 'transfer')
        self.src.rename(self.src.with_suffix('.unavailable'))
        _, packet = planning.packet(self.lib, layer='L3')
        self.assertNotIn('原文/', json.dumps(packet, ensure_ascii=False))
        artifacts = [a for a in packet['artifacts'] if a['data'].get('chapter')]
        report = {'schema_version': 1, 'layer': 'L3', 'packet_fingerprint': packet['fingerprint'],
                  'modules': [{'method': '通过询问制造行动门槛', 'applies': '进入新场域', 'cost': '有拖慢节奏的代价', 'invalid_when': '信息已经公开',
                               'evidence': [{'artifact': a['path'], 'locator': '旅人询问过河的办法'} for a in artifacts]}]}
        path = self.lib / 'transfer.json'
        write(path, report)
        ingest.ingest(self.lib, path, layer='L3')
        self.assertTrue(reporting.coverage(self.lib, 'L3')['complete'])
        write(local(self.lib, artifacts[0]['path']), {})
        self.assertFalse(reporting.coverage(self.lib, 'L3')['complete'])

    def test_library_lock_rejects_second_writer(self):
        with locked(self.lib), self.assertRaises(DeconError):
            with locked(self.lib):
                pass

    def test_new_cli_parameters_are_part_of_public_contract(self):
        from ncclib.cli import build_parser
        parser = build_parser()
        cases = [(['plan', 'lib', '--goal', 'technique', '--screenplay', 'none'], {'action': 'plan', 'goal': 'technique'}),
                 (['packet', 'lib', '3', '--independent', '--framework', 'framework.md'], {'action': 'packet', 'seq': 3, 'independent': True}),
                 (['ingest', 'lib', '--recover'], {'action': 'ingest', 'recover': True}),
                 (['coverage', 'lib', '--layer', 'screenplay'], {'action': 'coverage', 'layer': 'screenplay'})]
        for args, expected in cases:
            parsed = parser.parse_args(['decon', *args])
            for key, value in expected.items():
                self.assertEqual(getattr(parsed, key), value)


if __name__ == '__main__':
    unittest.main()
