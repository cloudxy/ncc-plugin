"""已验收章为事件源，派生台账可重建；每库单写者。"""
from .common import DECON_CFG as CFG, read, rows, write, write_rows, atomic, local, digest, require, vocabulary_fingerprint
from .contracts import validate


def receipts(lib, idx):
    directory = local(lib, CFG['receipts'])
    result = []
    vocab = vocabulary_fingerprint()
    paths = list(directory.glob('ch-*.json'))
    require(all(p.stem[3:].isdigit() for p in paths), '验收章文件名必须为 ch-序号.json')
    for path in sorted(paths, key=lambda p: int(p.stem[3:])):
        item = read(path)
        validate('receipt', item)
        require(isinstance(item, dict) and item.get('receipt_fingerprint') == digest({k: v for k, v in item.items() if k != 'receipt_fingerprint'}), f'验收章文件被改过：{path}')
        if item.get('index_fingerprint') == idx['fingerprint']:
            seq = item['chapter']
            require(seq == int(path.stem[3:]) and 1 <= seq <= len(idx['chapters']) and item['chapter_hash'] == idx['chapters'][seq - 1]['hash'], '验收收据 seq/hash 与索引错配')
            require(all(dep < seq for dep in item['dependencies']), '收据不能依赖本章或未来章')
            if item.get('vocab_fingerprint') != vocab:
                continue
            if any(dep not in {r['chapter'] for r in result} for dep in item.get('dependencies', [])):
                continue
            if any(source.get('path') and (not local(lib, source['path']).is_file() or digest(local(lib, source['path']).read_bytes()) != source.get('sha256')) for source in item.get('context_sources', [])):
                continue
            result.append(item)
    return result


def capture_legacy(lib, idx=None):
    path = local(lib, CFG['legacy_snapshot'])
    if not path.exists():
        old = read(local(lib, CFG['progress']), {})
        write(path, {'index_fingerprint': (idx or {}).get('fingerprint'), 'done': old.get('done', []), 'skipped': old.get('skipped', {}),
                     'ledgers': {kind: rows(local(lib, target)) for kind, target in CFG['ledgers'].items()}})
    return read(path)


def progress(lib, idx):
    old = read(local(lib, CFG['progress']), {})
    if old.get('schema_version') == 2 and old.get('index_fingerprint') == idx['fingerprint']:
        return old
    return {'schema_version': 2, 'index_fingerprint': idx['fingerprint'], 'done': old.get('done', []),
            'skipped': old.get('skipped', {}), 'legacy': {'done': old.get('done', []), 'skipped': old.get('skipped', {}), 'source': '旧库覆盖，尚未经过新入库验证'}, 'layers': {}}


def prefix_rows(lib, idx, before):
    """从可信事件源投影前缀；不让陈旧派生台账或未来观察反向影响过去。"""
    legacy = read(local(lib, CFG['legacy_snapshot']), {})
    pr = progress(lib, idx)
    compatible = legacy.get('index_fingerprint') in (None, idx['fingerprint']) and not pr.get('invalidated')
    result = {kind: [r for r in legacy.get('ledgers', {}).get(kind, []) if (r.get('chapter') or r.get('first_ch') or 0) < before] if compatible else [] for kind in CFG['ledgers']}
    contested = set()
    for receipt in receipts(lib, idx):
        if receipt['chapter'] < before and not receipt.get('independent'):
            for kind, values in receipt['ledgers'].items():
                result[kind].extend(values)
            contested.update(r.get('record_id') or digest(r) for c in receipt.get('conflicts', []) for r in c.get('assertions', []))
    result['状态事件'] = [r for r in result['状态事件'] if (r.get('record_id') or digest(r)) not in contested]
    return result


def rebuild(lib, idx, plan=None):
    legacy = capture_legacy(lib, idx)
    accepted = receipts(lib, idx)
    pr = progress(lib, idx)
    # Reindexing must not reattach old seq-based coverage or ledgers.
    invalidated = bool(pr.get('invalidated')) or legacy.get('index_fingerprint') not in (None, idx['fingerprint'])
    legacy_done = [] if invalidated else legacy.get('done', [])
    legacy_skipped = {} if invalidated else legacy.get('skipped', {})
    ledgers = {kind: ([] if invalidated else list(legacy.get('ledgers', {}).get(kind, []))) for kind in CFG['ledgers']}
    ledgers['实体'] = [{**row, 'id': row.get('id') or 'E-' + digest(('legacy:' + row.get('name', '')).encode())[:12]} for row in ledgers.get('实体', [])]
    all_scenes, rejected, pending, conflicts = [], [], [], []
    done, scene_done, failed = [], [], {}
    for receipt in accepted:
        seq = receipt['chapter']
        if receipt['base_complete']:
            done.append(seq)
        else:
            failed[str(seq)] = receipt.get('errors', ['必要产物未满足'])
        if receipt['scene_complete']:
            scene_done.append(seq)
        for kind, values in receipt['ledgers'].items():
            if kind in ledgers:
                ledgers[kind].extend(values)
        all_scenes.extend(receipt['scenes'])
        rejected.extend(receipt['rejected']); pending.extend(receipt['pending']); conflicts.extend(receipt['conflicts'])
        # Receipt payload is authoritative even if a process died after replacing the raw file.
        raw_path = local(lib, CFG['chapter_dir'] + f'/ch-{seq:04d}.json')
        import json
        expected = (json.dumps(receipt['payload'], ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
        if raw_path.is_file() and raw_path.read_bytes() != expected:
            atomic(local(lib, CFG['raw_backups'] + f'/ch-{seq:04d}-' + digest(raw_path.read_bytes()) + '.json'), raw_path.read_bytes())
        write(raw_path, receipt['payload'])
        write_scene_views(lib, receipt)
    def unique(items):
        result = {}
        for item in items:
            result[item.get('record_id') or digest(item)] = item
        return [result[k] for k in sorted(result)]
    contested = {r.get('record_id') or digest(r) for c in conflicts for r in c.get('assertions', [])}
    ledgers['状态事件'] = [r for r in ledgers['状态事件'] if (r.get('record_id') or digest(r)) not in contested]
    last_seen = {}
    for values in ledgers.values():
        for row in values:
            for key in ('entity', 'subject', 'object', 'source_entity', 'target_entity', 'id'):
                ident = row.get(key)
                if isinstance(ident, str) and ident.startswith('E-'):
                    last_seen[ident] = max(last_seen.get(ident, 0), row.get('chapter', 0))
    ledgers['实体'] = [{**r, 'last_ch': max(r.get('last_ch', 0), last_seen.get(r.get('id'), 0))} for r in ledgers.get('实体', [])]
    for kind, target in CFG['ledgers'].items():
        write_rows(local(lib, target), unique(ledgers[kind]))
    write_rows(local(lib, CFG['scenes']), unique(all_scenes))
    write_rows(local(lib, CFG['rejections']), unique(rejected))
    write_rows(local(lib, CFG['pending']), unique(pending))
    # Ambiguous aliases remain visible as pending records and never choose the first entity.
    aliases = {}
    for entity in ledgers.get('实体', []):
        for alias in entity.get('verified_aliases', []):
            aliases.setdefault(alias['name'], set()).add(entity.get('id'))
    ambiguous = {name: sorted(ids) for name, ids in aliases.items() if len(ids) > 1}
    write(local(lib, CFG['alias_index']), {'aliases': {n: next(iter(ids)) for n, ids in aliases.items() if len(ids) == 1}, 'conflicts': ambiguous})
    conflicts.extend({'alias': name, 'entities': ids, 'reason': '同一别名指向多个实体，禁止自动选取'} for name, ids in ambiguous.items())
    write_rows(local(lib, CFG['conflicts']), unique(conflicts))
    pr['legacy'] = {'done': legacy_done, 'skipped': legacy_skipped, 'source': '仅 legacy 覆盖，不证明新校验或场次完成'}
    pr['done'] = sorted(set(legacy_done) | set(done));pr['skipped'] = legacy_skipped
    selected = (plan or {}).get('selected', list(range(1, len(idx['chapters']) + 1)))
    previous = pr.get('layers', {})
    pr['layers'] = {**previous, 'L0': {'planned': [c['seq'] for c in idx['chapters']], 'done': [c['seq'] for c in idx['chapters']], 'failed': {}, 'waived': {}},
                    'L2': {'planned': selected, 'done': sorted(done), 'failed': failed, 'waived': previous.get('L2', {}).get('waived', {})},
                    'screenplay': {'planned': (plan or {}).get('screenplay', []), 'done': sorted(scene_done), 'failed': {str(r['chapter']): r.get('scene_errors', []) for r in accepted if r.get('scene_errors')}, 'waived': previous.get('screenplay', {}).get('waived', {})}}
    pr['artifacts'] = {str(r['chapter']): {'chapter_hash': r['chapter_hash'], 'receipt_fingerprint': r['receipt_fingerprint'], 'packet_fingerprint': r['packet_fingerprint']} for r in accepted}
    pr['derived_fingerprints'] = {path: digest(local(lib, path).read_bytes()) for path in list(CFG['ledgers'].values()) + [CFG['scenes']]}
    validate('progress', pr)
    write(local(lib, CFG['progress']), pr)
    return pr


def write_scene_views(lib, receipt):
    """场次人读稿及对标参照只落拆书库，恢复时同样重建。"""
    seq = receipt['chapter']
    lines = [f'# ch-{seq:04d} 剧本（对标分析）', '', str((receipt['payload'].get('screenplay') or {}).get('logline', ''))]
    for scene in receipt['scenes']:
        lines += ['', f'## {scene["scene_id"]} {scene["slugline"]}', f'- 在场：{", ".join(scene["characters"])}',
                  f'- 目标：{scene["objective"]}', f'- 阻碍：{scene["obstacle"]}', f'- 翻转：{scene["turn"]}', f'- 落点：{scene["outcome"]}']
        lines += ['- 动作：' + action for action in scene['actions']]
        lines += [f'- 对白意图：{d["speaker"]}｜{d["intent"]}｜潜台词：{d["subtext"]}｜定位：{d["locator"]}' for d in scene['dialogue']]
        lines += [f'- 证据：{scene["locator"]}；{scene["confidence"]}']
    atomic(local(lib, CFG['scene_views'] + f'/ch-{seq:04d}.md'), '\n'.join(lines) + '\n')
    write(local(lib, CFG['scene_references'] + f'/ch-{seq:04d}.json'),
          {'schema_version': 1, 'label': '对标参照，不是作者书场景卡', 'chapter': seq,
           'receipt_fingerprint': receipt['receipt_fingerprint'], 'complete': receipt['scene_complete'],
           'scenes': [{k: row[k] for k in ('scene_id', 'characters', 'objective', 'obstacle', 'turn', 'outcome', 'locator')} for row in receipt['scenes']]})


def commit(lib, idx, receipt, plan):
    capture_legacy(lib, idx)
    # Reject failures before this call. Atomic receipt replacement is the commit point.
    seq = receipt['chapter']
    path = local(lib, CFG['chapter_dir'] + f'/ch-{seq:04d}.json')
    if path.is_file():
        atomic(local(lib, CFG['raw_backups'] + f'/ch-{seq:04d}-' + digest(path.read_bytes()) + '.json'), path.read_bytes())
    write(path, receipt['payload'])
    receipt['receipt_fingerprint'] = digest(receipt)
    write(local(lib, CFG['receipts'] + f'/ch-{seq:04d}.json'), receipt)
    return rebuild(lib, idx, plan)
