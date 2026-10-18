"""按目标选章，生成机械骨架与有来源的派单上下文。"""
from pathlib import Path
from .common import DECON_CFG as CFG, require, read, write, local, digest, rows, vocabulary_fingerprint
from .contracts import validate
from .index import load, chapter_text, source
from .storage import rebuild, progress, receipts, prefix_rows


def selection(count):
    groups = {'opening': list(range(1, min(10, count) + 1)),
              'interior': sorted({1 + round(k * (count - 1) / 8) for k in range(1, 8)}),
              'ending': list(range(max(1, count - 9), count + 1))}
    return groups


def sequence_set(text, count):
    if not text:
        return []
    values = set()
    for item in text.split(','):
        parts = item.strip().split('-')
        require(len(parts) in (1, 2) and all(p.isdigit() for p in parts), '序号范围使用 1-3,7 格式')
        lo, hi = int(parts[0]), int(parts[-1])
        require(1 <= lo <= hi <= count, '序号范围越界')
        values.update(range(lo, hi + 1))
    return sorted(values)


def current(lib, idx):
    plan = read(local(lib, CFG['plan']))
    if plan:
        validate('plan', plan)
        require(plan['index_fingerprint'] == idx['fingerprint'], '选章计划对应旧索引，请重新确认范围')
        require(plan['fingerprint'] == digest({k: v for k, v in plan.items() if k != 'fingerprint'}), '选章计划已被手改，请用 decon plan 重新生成')
        require(plan['selected'] == sorted(set(plan['selected'])) and set(plan['selected']) <= set(range(1, len(idx['chapters']) + 1)), '计划序号重复、乱序或越界')
        require(set(plan['screenplay']) <= set(plan['selected']), '计划场次不在 L2 范围内')
    return plan


def skeleton(lib, idx):
    totals = {}
    lines = source(lib, idx['source']).read_text('utf-8-sig').splitlines()
    for chapter in idx['chapters']:
        bucket = str((chapter['seq'] - 1) // 100 + 1)
        totals.setdefault(bucket, {'chapters': 0, 'han': 0, 'dialogue_han': 0})
        totals[bucket]['chapters'] += 1; totals[bucket]['han'] += chapter['han']
        _, body = chapter_text(lib, idx, chapter['seq'], lines)
        import re
        totals[bucket]['dialogue_han'] += sum(len(re.findall(r'[\u4e00-\u9fff]', q)) for q in re.findall(r'[“「]([^”」]*)[”」]', body))
    for item in totals.values():
        item['dialogue_ratio'] = round(item['dialogue_han'] / item['han'], 4) if item['han'] else None
    report = {'schema_version': 1, 'layer': 'L1', 'index_fingerprint': idx['fingerprint'], 'mechanical_only': True,
              'chapters': [{'seq': c['seq'], 'no': c['no'], 'volume': c.get('volume', ''), 'title': c['title'], 'han': c['han']} for c in idx['chapters']],
              'hundred_chapter_buckets': totals, 'dialogue_definition': '配对中文引号内汉字 / 全文汉字，仅机械近似',
              'semantic_missing': ['人物结构', '事件链', '爽点与转折：需另有来源的语义抽取，不能由机械比例推断']}
    report['fingerprint'] = digest(report)
    write(local(lib, CFG['skeleton']), report)
    return report


def make_plan(lib, goal, selected=None, reason=None, screenplay=None):
    idx = load(lib, validate_source=False)
    require(idx.get('schema_version') == 2, '旧索引仍可查询 legacy 覆盖；新分层请先显式 decon index 重建到新契约')
    old = current(lib, idx)
    if goal is None and old and selected is None and screenplay is None:
        return old
    goal = goal or 'technique'
    if goal != 'transfer':
        load(lib)
    require(goal in ('structure', 'technique', 'full', 'transfer'), '未知研究目标')
    groups = selection(len(idx['chapters']))
    seqs = list(range(1, len(idx['chapters']) + 1)) if goal == 'full' else sorted({n for group in groups.values() for n in group}) if goal == 'technique' else []
    if selected is not None:
        require(reason, '手动选章必须写 --reason')
        seqs = sequence_set(selected, len(idx['chapters']));groups['author'] = seqs
    scenes = [] if screenplay == 'none' else sequence_set(screenplay, len(idx['chapters'])) if screenplay else (seqs if goal == 'technique' else [])
    require(set(scenes) <= set(seqs), '场次范围必须包含在已选 L2 章节内')
    plan = {'schema_version': 1, 'goal': goal, 'index_fingerprint': idx['fingerprint'], 'selected': seqs, 'groups': groups,
            'screenplay': scenes, 'rounding': 'Python round：到最近整数，正中取偶；1 + round(k*(N-1)/8)，k=1..7',
            'reasons': {'default': '开篇10章、七个内部等分点、结局10章，去重；不展开全书场次', 'author': reason or ''},
            'allowed_statistics': 'continuous' if goal == 'full' else 'sample' if goal == 'technique' else 'mechanical' if goal == 'structure' else 'reports_only'}
    plan['group_adjustments'] = {name: {'excluded': sorted(set(values) - set(seqs)), 'reason': reason} for name, values in groups.items() if selected is not None and set(values) - set(seqs)}
    if goal == 'transfer' and old:
        plan['source_plan'] = old.get('source_plan', old) if old['goal'] == 'transfer' else old
    plan['fingerprint'] = digest(plan);validate('plan', plan)
    if old and old['fingerprint'] != plan['fingerprint']:
        write(local(lib, CFG['plan_history'] + '/' + old['fingerprint'] + '.json'), old)
    write(local(lib, CFG['plan']), plan)
    if goal != 'transfer':
        skeleton(lib, idx)
    pr = rebuild(lib, idx, plan)
    if goal != 'transfer':
        pr['layers']['L1'] = {'planned': ['mechanical'], 'done': ['mechanical'], 'failed': {}, 'waived': {}}
        write(local(lib, CFG['progress']), pr)
    return plan


def context(lib, idx, seq, given=None):
    if seq == 1 and given is None:
        return {'available': True, 'mode': 'initial', 'previous': '', 'entities': [], 'foreshadows': [],
                'sources': [{'kind': 'initial_index', 'sha256': idx['fingerprint'], 'reason': '首章初始化，尚无前章台账'}], 'unread': []}
    if given:
        path = Path(given)
        if not path.is_absolute():
            path = local(lib, given)
        value = read(path)
        require(isinstance(value, dict), '上下文文件必须为对象')
        output = {'available': True, 'mode': 'provided', 'sources': [], 'unread': value.get('unread', [])}
        require(isinstance(output['unread'], list), '未读范围 unread 必须为数组')
        for key in ('previous', 'entities', 'foreshadows'):
            entry = value.get(key)
            require(isinstance(entry, dict) and 'value' in entry and isinstance(entry.get('source'), dict), f'三件套 {key} 缺内容或来源；不能用未知伪装为空')
            origin = entry['source'];p = local(lib, origin.get('path', ''))
            require(p.is_file() and digest(p.read_bytes()) == origin.get('sha256'), f'三件套 {key} 来源缺失或已变')
            require(not str(p.relative_to(Path(lib).resolve())).startswith(CFG['packets']), '派单包不能反向证明自己的上下文')
            require(type(origin.get('observed_through')) is int and 0 <= origin['observed_through'] < seq, f'{key} 来源须声明 observed_through，且不能含本章或未来章')
            if key == 'previous':
                require(origin['observed_through'] == seq - 1, '前情须观察至紧邻前章；不能用前一抽样章替代')
            for directory in (CFG['receipts'], CFG['chapter_dir']):
                relative = p.relative_to(Path(lib).resolve()).as_posix()
                if relative.startswith(directory + '/ch-') and p.stem[3:].isdigit():
                    require(int(p.stem[3:]) < seq, '本章/未来章产物不能反向进入三件套')
            if key == 'previous':
                require(isinstance(entry['value'], str), '前情必须为文本')
            else:
                require(isinstance(entry['value'], list), f'{key} 必须为数组')
            require(entry['value'] or entry.get('empty_reason'), f'{key} 为空须说明依据')
            output[key] = entry['value'];output['sources'].append({'field': key, **origin})
        return output
    previous = next((item for item in receipts(lib, idx) if item['chapter'] == seq - 1 and item['base_complete'] and not item.get('independent')), None)
    if previous:
        source_path = CFG['receipts'] + f'/ch-{seq-1:04d}.json'
        prefix_ledgers = prefix_rows(lib, idx, seq)
        prefix = [r for values in prefix_ledgers.values() for r in values]
        last_seen = {}
        for row in prefix:
            for key in ('id', 'entity', 'subject', 'object', 'source_entity', 'target_entity'):
                ident = row.get(key)
                if isinstance(ident, str):
                    last_seen[ident] = max(last_seen.get(ident, 0), row.get('chapter', 0))
        entity_rows = []
        for row in prefix_ledgers['实体']:
            observed = row.get('chapter') or row.get('first_ch') or 0
            last = max(observed, last_seen.get(row.get('id'), observed))
            if observed < seq and last >= max(1, seq - CFG['active_entity_window']):
                ident = row.get('id') or 'E-' + digest(('legacy:' + row.get('name', '')).encode())[:12]
                entity_rows.append({**row, 'id': ident, 'last_ch': last})
        entity_rows = list({row['id']: row for row in entity_rows}.values())
        aliases = {}
        for entity in entity_rows:
            for alias in entity.get('verified_aliases', []):
                aliases.setdefault(alias['name'], set()).add(entity['id'])
        alias_conflicts = {name: sorted(ids) for name, ids in aliases.items() if len(ids) > 1}
        for entity in entity_rows:
            entity['verified_aliases'] = [a for a in entity.get('verified_aliases', []) if a['name'] not in alias_conflicts]
        history = prefix_ledgers['伏笔']
        active = {}
        for row in sorted(history, key=lambda r: r['chapter']):
            if row.get('op') == '回收':
                active.pop(row.get('id'), None)
            else:
                active[row.get('id')] = row
        foreshadow_rows = list(active.values())
        sources = [{'field': 'previous', 'path': source_path, 'sha256': digest(local(lib, source_path).read_bytes())}]
        for field, kind in (('entities', '实体'), ('foreshadows', '伏笔')):
            p = local(lib, CFG['ledgers'][kind])
            require(p.is_file(), f'已验收前章但 {kind} 台账缺失，先 ingest --recover')
            snapshot = {'index_fingerprint': idx['fingerprint'], 'before': seq, 'kind': field,
                        'origin': {'path': CFG['ledgers'][kind], 'sha256': digest(p.read_bytes())},
                        'value': entity_rows if field == 'entities' else foreshadow_rows}
            snapshot_path = CFG['contexts'] + '/' + digest(snapshot) + '.json'
            write(local(lib, snapshot_path), snapshot)
            sources.append({'field': field, 'path': snapshot_path, 'sha256': digest(local(lib, snapshot_path).read_bytes())})
        import json
        return {'available': True, 'mode': 'adjacent_receipt', 'previous': previous['payload'].get('summary') or json.dumps(previous['ledgers'], ensure_ascii=False),
                'entities': entity_rows, 'alias_conflicts': alias_conflicts, 'foreshadows': foreshadow_rows, 'sources': sources, 'dependencies': [seq - 1], 'unread': []}
    return {'available': False, 'mode': 'missing', 'previous': None, 'entities': None, 'foreshadows': None,
            'sources': [], 'unread': [{'before': seq, 'reason': '没有已核实的紧邻前情三件套；上一抽样章不能冒充前章'}]}


def packet(lib, seq=None, layer='L2', given=None, independent=False, framework=None):
    idx = load(lib, validate_source=layer != 'L3');plan = current(lib, idx)
    require(plan is not None, '先用 decon plan 明确研究目标与范围')
    if layer == 'L3':
        source_plan = plan.get('source_plan', plan)
        active = receipts(lib, idx)
        pr = progress(lib, idx)
        for key, required in (('L2', source_plan.get('selected', [])), ('screenplay', source_plan.get('screenplay', []))):
            done = {r['chapter'] for r in active if (r['base_complete'] if key == 'L2' else r['scene_complete'])}
            waived = {int(k) for k in pr.get('layers', {}).get(key, {}).get('waived', {})}
            require(set(required) <= done | waived, 'L3 源计划覆盖不足，先完成或显式说明豁免，不把未完成样本当已验结论')
        artifacts = []
        skeleton_path = local(lib, CFG['skeleton'])
        if skeleton_path.is_file():
            value = read(skeleton_path)
            require(value.get('index_fingerprint') == idx['fingerprint'], '骨架报告对应旧索引')
            require(value.get('fingerprint') == digest({k: v for k, v in value.items() if k != 'fingerprint'}), '骨架报告被改过')
            artifacts.append({'path': CFG['skeleton'], 'sha256': digest(skeleton_path.read_bytes()), 'data': value})
        contested = {r.get('record_id') for item in active for c in item.get('conflicts', []) for r in c.get('assertions', [])}
        for item in active:
            if not item['base_complete']:
                continue
            data = {'chapter': item['chapter'], 'scope': 'chapter_only' if item.get('independent') else 'context_verified',
                    'source_receipt_fingerprint': item['receipt_fingerprint'],
                    'facts': {kind: [{k: v for k, v in row.items() if k in ('record_id', 'id', 'name', 'chapter', 'attribute', 'old', 'new', 'unit', 'description', 'content', 'op', 'evidence', 'confidence', 'type', 'tension', 'colors', 'parts')} for row in values if row.get('record_id') not in contested] for kind, values in item.get('chapter_facts', item['ledgers']).items()},
                    'scenes': item['scenes']}
            projected_path = CFG['transfer_inputs'] + f'/ch-{item["chapter"]:04d}.json'
            write(local(lib, projected_path), data)
            artifacts.append({'path': projected_path, 'sha256': digest(local(lib, projected_path).read_bytes()), 'data': data})
        require(artifacts, 'L3 没有已验收产物可读')
        result = {'schema_version': 1, 'layer': 'L3', 'index_fingerprint': idx['fingerprint'], 'plan_fingerprint': plan['fingerprint'],
                  'vocab_fingerprint': vocabulary_fingerprint(), 'artifacts': artifacts,
                  'sources_fingerprint': digest([r['receipt_fingerprint'] for r in active]),
                  'boundary': '只读这些已验报告；不交付原文或原始章文件路径，不写作者大纲或正文'}
        name = CFG['transfer_packet']
    else:
        require(seq in plan['selected'], '该 seq 不在 L2 计划内；先显式增补计划')
        c, body = chapter_text(lib, idx, seq);ctx = context(lib, idx, seq, given)
        require(ctx['available'] or independent, '缺少跨章三件套：补有来源上下文，或显式 --independent 降级为章内分析')
        require(framework and Path(framework).is_file(), '请用 --framework 提供实际总纲 5.0 路径，不由记忆拼凑')
        result = {'schema_version': 1, 'layer': 'L2', 'index_fingerprint': idx['fingerprint'], 'plan_fingerprint': plan['fingerprint'],
                  'chapter': c, 'text': body, 'context': ctx, 'independent': bool(independent),
                  'framework': {'path': str(Path(framework).resolve()), 'sha256': digest(Path(framework).read_bytes())},
                  'vocab_fingerprint': vocabulary_fingerprint(),
                  'requires_screenplay': seq in plan['screenplay'], 'act': next((a.get('name', '') for a in idx.get('act_ranges', []) if a.get('start', 0) <= seq <= a.get('end', -1)), '')}
        name = CFG['packets'] + f'/ch-{seq:04d}.json'
    result['fingerprint'] = digest(result);validate('packet', result)
    write(local(lib, name), result)
    return name, result


def validate_transfer_packet(lib, idx, value):
    validate('packet', value)
    require(value['layer'] == 'L3' and value['index_fingerprint'] == idx['fingerprint'], 'L3 包对应旧索引或错误层')
    require(value['fingerprint'] == digest({k: v for k, v in value.items() if k != 'fingerprint'}), 'L3 包已变')
    plan = current(lib, idx)
    require(plan and value.get('plan_fingerprint') == plan['fingerprint'], 'L3 包对应旧计划')
    require(value.get('vocab_fingerprint') == vocabulary_fingerprint(), 'L3 包词表或契约已变')
    active = receipts(lib, idx)
    require(value.get('sources_fingerprint') == digest([r['receipt_fingerprint'] for r in active]), 'L3 源事实集合已变，重新生成转化包')
    accepted = {r['receipt_fingerprint'] for r in active if r['base_complete']}
    require(value.get('artifacts'), 'L3 没有已验输入')
    for artifact in value['artifacts']:
        name = artifact['path']
        require(name == CFG['skeleton'] or name.startswith(CFG['transfer_inputs'] + '/'), 'L3 输入不在报告白名单')
        p = local(lib, name)
        require(p.is_file() and digest(p.read_bytes()) == artifact['sha256'] and read(p) == artifact['data'], 'L3 已验输入缺失或已变')
        if name != CFG['skeleton']:
            require(artifact['data'].get('source_receipt_fingerprint') in accepted, 'L3 输入源章已失效；重新生成转化包')
    return value
