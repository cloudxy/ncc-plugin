"""按层、连续范围与样本分别报告；不把缺测写成零。"""
from collections import Counter
from pathlib import Path
from .common import DECON_CFG as CFG, DeconError, require, read, write, atomic, local, rows, digest
from .index import load
from .planning import current, validate_transfer_packet
from .storage import progress, receipts


def coverage(lib, layer=None):
    idx = load(lib, validate_source=False);plan = current(lib, idx);pr = progress(lib, idx)
    active = receipts(lib, idx)
    if layer is None:
        layer = 'L3' if plan and plan['goal'] == 'transfer' else 'L1' if plan and plan['goal'] == 'structure' else 'L2'
    if layer != 'L3':
        load(lib)
    if layer == 'L0':
        return {'layer': layer, 'planned': [c['seq'] for c in idx['chapters']], 'done': [c['seq'] for c in idx['chapters']], 'missing': [], 'complete': True}
    if layer == 'L1':
        value = read(local(lib, CFG['skeleton']), {})
        ok = value.get('index_fingerprint') == idx['fingerprint'] and value.get('fingerprint') == digest({k: v for k, v in value.items() if k != 'fingerprint'})
        return {'layer': layer, 'complete': bool(ok), 'mechanical_only': True, 'missing': [] if ok else ['可信机械骨架'], 'semantic_missing': value.get('semantic_missing', [])}
    if layer == 'L3':
        value = read(local(lib, CFG['transfer_report']))
        packet = read(local(lib, CFG['transfer_packet']))
        ok = bool(value and packet and value.get('packet_fingerprint') == packet.get('fingerprint') and pr.get('layers', {}).get('L3', {}).get('artifact_fingerprint') == digest(value))
        reason = ''
        if ok:
            try:
                validate_transfer_packet(lib, idx, packet)
            except DeconError as exc:
                ok = False;reason = str(exc)
        return {'layer': layer, 'complete': ok, 'missing': [] if ok else ['已验收方法模块'], 'scope': 'reports_only', 'stale_reason': reason}
    require(layer in ('L2', 'screenplay', 'legacy'), '未知覆盖层')
    if layer == 'legacy':
        planned = [c['seq'] for c in idx['chapters']]
        done = pr.get('legacy', pr).get('done', [])
        waived = pr.get('legacy', pr).get('skipped', {})
    else:
        require(plan is not None, '新层覆盖必须先有 decon plan；旧库查询可用 --layer legacy')
        planned = plan['screenplay'] if layer == 'screenplay' else plan['selected']
        done = [r['chapter'] for r in active if r['scene_complete']] if layer == 'screenplay' else [r['chapter'] for r in active if r['base_complete']]
        waived = pr.get('layers', {}).get(layer, {}).get('waived', {})
    missing = sorted(set(planned) - set(done) - {int(k) for k in waived})
    groups = {}
    if plan and layer == 'L2':
        for name, values in plan['groups'].items():
            expected = set(values) & set(planned)
            groups[name] = {'planned': sorted(expected), 'missing': sorted(expected - set(done) - {int(k) for k in waived})}
    result = {'layer': layer, 'planned': planned, 'done': sorted(set(done) & set(planned)), 'waived': waived, 'missing': missing,
              'complete': not missing, 'groups': groups, 'not_selected': len(idx['chapters']) - len(set(planned)), 'not_selected_are_not_skipped': True}
    result['stale_or_missing_receipts'] = sorted(set(pr.get('layers', {}).get(layer, {}).get('done', [])) - set(done))
    if layer == 'L2' and plan and plan['screenplay']:
        scene_done = {r['chapter'] for r in active if r['scene_complete']}
        scene_waived = pr.get('layers', {}).get('screenplay', {}).get('waived', {})
        result['scene_missing'] = sorted(set(plan['screenplay']) - scene_done - {int(k) for k in scene_waived})
        result['complete'] = result['complete'] and not result['scene_missing']
    return result


def statistics(lib, window, layer, legacy_baseline):
    idx = load(lib);plan = current(lib, idx)
    if layer == 'L1':
        report = read(local(lib, CFG['skeleton']))
        require(coverage(lib, 'L1')['complete'], '机械骨架尚未完成')
        return report, CFG['skeleton']
    if plan and plan['allowed_statistics'] == 'sample' and window is None:
        state = coverage(lib, 'L2');require(state['complete'], '样本计划覆盖不足，不能产出已完成样本报告')
        active = [r for r in receipts(lib, idx) if r['chapter'] in plan['selected']]
        counts = {kind: sum(len(r.get('chapter_facts', r['ledgers']).get(kind, [])) for r in active) for kind in CFG['ledgers']}
        result = {'scope': 'sample', 'index_fingerprint': idx['fingerprint'], 'plan_fingerprint': plan['fingerprint'], 'selected': plan['selected'],
                  'groups': state['groups'], 'chapter_count': len(active), 'scene_chapters': sum(r['scene_complete'] for r in active), 'scene_count': sum(len(r['scenes']) for r in active),
                  'counts_in_sample': counts, 'unavailable': ['全书爽点密度', '最长连续压抑', '跨未读区间伏笔遗忘'],
                  'rejected': sum(len(r['rejected']) for r in active), 'pending': sum(len(r['pending']) for r in active),
                  'field_coverage': {k: sum(r.get('collection_status', {}).get(k) == 'verified' for r in active) for k in ('entities', 'foreshadows', 'emotion_points', 'payoffs')}}
        result['average_scenes'] = round(result['scene_count'] / result['scene_chapters'], 2) if result['scene_chapters'] else None
        result['waived'] = state['waived']
        result['chapter_only'] = [r['chapter'] for r in active if r.get('independent')]
        return result, CFG['sample_reports'] + '/' + plan['fingerprint'][:16] + '.json'
    lo, hi = window or (1, len(idx['chapters']))
    require(1 <= lo <= hi <= len(idx['chapters']), '统计范围不在章节索引内')
    pr = progress(lib, idx);valid = {r['chapter'] for r in receipts(lib, idx) if r['base_complete']}
    legacy = set(pr.get('legacy', pr).get('done', []));waived = pr.get('legacy', pr).get('skipped', {})
    missing = set(range(lo, hi + 1)) - valid - legacy - {int(k) for k in waived}
    require(not missing, '统计要先过覆盖率闸门；本范围仍缺章：' + ','.join(map(str, sorted(missing))))
    if pr.get('schema_version') == 2:
        expected = {str(r['chapter']): r['receipt_fingerprint'] for r in receipts(lib, idx)}
        require({k: v['receipt_fingerprint'] for k, v in pr.get('artifacts', {}).items()} == expected, '验收章与派生进度不同步，请 decon ingest --recover')
        for path, fingerprint in pr.get('derived_fingerprints', {}).items():
            require(local(lib, path).is_file() and digest(local(lib, path).read_bytes()) == fingerprint, '派生台账缺失或被改过，请 decon ingest --recover')
    result = legacy_baseline(lib, lo, hi)
    result.update(scope='range' if window else 'whole', coverage={'validated': sorted(valid & set(range(lo, hi + 1))), 'legacy': sorted(legacy & set(range(lo, hi + 1))), 'skipped': {k: v for k, v in waived.items() if lo <= int(k) <= hi}}, availability={})
    paths = {'伏笔': 'foreshadows', '爽点': 'payoffs', '情绪': 'emotion_points', '钩子': 'hooks', '单元': 'units', '实体': 'entities'}
    active = {r['chapter']: r for r in receipts(lib, idx)}
    for kind, collection in paths.items():
        path = local(lib, CFG['ledgers'][kind])
        if valid and any(lo <= int(k) <= hi for k in waived):
            result[kind] = None;result['availability'][kind] = '范围含显式跳过，不能把未观察章当作零事实'
        elif not path.exists():
            result[kind] = None;result['availability'][kind] = '未采集：缺台账，不将缺测写成零'
        elif valid and any(seq in active and active[seq].get('collection_status', {}).get(collection) != 'verified' for seq in range(lo, hi + 1)):
            result[kind] = None;result['availability'][kind] = '字段覆盖不足或存在丢弃/待校验条目'
        else:
            result['availability'][kind] = 'legacy口径，完整性未证实' if legacy & set(range(lo, hi + 1)) else '已验收字段口径'
    emotions = {r.get('chapter') for r in rows(local(lib, CFG['ledgers']['情绪'])) if r.get('tension') is not None}
    if result.get('情绪') is not None and not set(range(lo, hi + 1)) <= emotions:
        for key in ('最长连续压抑', '压抑段平均章数', '释放段平均章数'):
            result['情绪'][key] = None
        result['availability']['情绪连续段'] = '情绪观察有缺章，不能跨缺口累计连续段'
    if lo != 1 and result.get('伏笔'):
        result['伏笔']['疑似遗忘'] = None
        result['availability']['伏笔遗忘'] = '范围没有冻结全量前置伏笔状态，不判断疑似遗忘'
    relevant = [r for r in active.values() if lo <= r['chapter'] <= hi]
    collected = relevant and any(r['scenes'] for r in relevant)
    result['screenplay'] = {'status': '已采集' if collected else '未采集',
                            'chapters': sum(r['scene_complete'] for r in relevant) if collected else None, 'scenes': sum(len(r['scenes']) for r in relevant) if collected else None}
    result['discarded_items'] = sum(len(r['rejected']) for r in relevant)
    result['planned_chapters'] = plan['selected'] if plan else None
    result['validated_chapters'] = len(valid & set(range(lo, hi + 1)))
    result['screenplay']['average_scenes'] = round(result['screenplay']['scenes'] / result['screenplay']['chapters'], 2) if result['screenplay']['chapters'] else None
    return result, (CFG['range_reports'] + f'/{lo}-{hi}.json' if window else CFG['baseline'])


def write_report(lib, result, target):
    write(local(lib, target), result)
    human = '# 拆书分析报告\n\n> 生成内容，勿手改；口径以 JSON 的 scope/availability/coverage 为准。\n\n'
    import json
    human += '```json\n' + json.dumps(result, ensure_ascii=False, indent=2) + '\n```\n'
    atomic(local(lib, str(Path(target).with_suffix('.md'))), human)
