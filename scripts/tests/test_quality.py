import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from ncc_data.policy import POLICY, POLICY_HASH
from ncc_data.quality_core import evaluate_report


class QualityTest(unittest.TestCase):
    def test_file_packet_ingest_and_staleness_without_optional_dependencies(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            content = root / '设定.md'
            content.write_text('灯下的选择，代价是失去姓名。')
            command = [sys.executable, str(ROOT / 'scripts/ncc_state.py'), 'quality']
            packet = subprocess.run(command + ['plan', str(root), '--file', '设定.md', '--scheme', 'P3'], capture_output=True, text=True)
            self.assertEqual(packet.returncode, 0, packet.stderr)
            data = json.loads(packet.stdout)
            report = {'dimensions': {d['key']: {'score': 4.5, 'evidence': ['灯下的选择'], 'reason': '合成依据'} for d in POLICY['profiles']['P3']},
                      'hard': 'pass', 'coverage': 'complete', 'observations': [], 'summary': '合成评估', 'suggestions': []}
            result = root / 'report.json'
            result.write_text(json.dumps({'content_sha256': data['content_sha256'], 'policy_hash': POLICY_HASH,
                'scheme': 'P3', 'evaluator': 'fixture', 'report': report}, ensure_ascii=False))
            proc = subprocess.run(command + ['ingest', str(root), '--file', '设定.md', '--scheme', 'P3', '--report', str(result)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(proc.stdout)['result']['score'], '90.0')
            content.write_text('作者已经改变设定。')
            proc = subprocess.run(command + ['status', str(root), '--file', '设定.md'], capture_output=True, text=True)
            self.assertFalse(json.loads(proc.stdout)['fresh'])

    def test_forged_totals_and_evidence_do_not_pass(self):
        raw = {'dimensions': {}, 'hard': 'pass', 'coverage': 'complete', 'summary': '未检查'}
        self.assertEqual(evaluate_report(POLICY, POLICY_HASH, 'P1', '文本', raw)['verdict'], 'incomplete')

    def test_database_marker_refuses_direct_file_reads(self):
        from ncclib.core import load
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / '.ncc-database.json').write_text('{}')
            (root / 'book.json').write_text('{"schema_version":4}')
            with self.assertRaises(SystemExit):
                load(root)
