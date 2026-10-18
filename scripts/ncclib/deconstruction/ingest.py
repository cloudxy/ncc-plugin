"""逐文件、逐条目、逐场次验证；坏条目留痕，验收章作为提交点。"""
from collections import defaultdict
from pathlib import Path
import re
from .common import DECON_CFG as CFG, REGISTRY, CONFIDENCE, V, DeconError, require, read, write, local, digest, rows, vocabulary_fingerprint
from .contracts import validate, errors, specification
from .index import load, chapter_text
from .planning import current, validate_transfer_packet
from .storage import commit, receipts, progress, prefix_rows


COLLECTIONS = tuple(k for k, v in specification('chapter')['fields'].items() if v.get('type') == 'array')
LEDGERS = {'entities': '实体', 'relations': '关系', 'events': '事件', 'state_events': '状态事件', 'foreshadows': '伏笔',
           'emotion_points': '情绪', 'information_gaps': '信息差', 'payoffs': '爽点', 'hooks': '钩子', 'units': '单元'}
REFERENCE_FIELDS = ('entity', 'entity_id', 'subject', 'object', 'source_entity', 'target_entity', 'source_id', 'target_id')


def locator(item):
    value = item.get('evidence', item.get('locator'))
    return value.get('locator', '') if isinstance(value, dict) else value or ''


def evidence_errors(item, body):
    quote = locator(item)
    result = []
    if not isinstance(quote, str) or not 5 <= len(quote) <= 15 or quote not in body:
        result.append('定位词须为本章正文中的5–15字连续原文')
    if item.get('confidence') not in CONFIDENCE:
        result.append('置信级不在 registry 词表内')
    return result


def overlaps(text, body):
    text = re.sub(r'\s', '', text)
    body = re.sub(r'\s', '', body)
    return any(text[i:i + 16] in body for i in range(max(0, len(text) - 15)))


def alias_supported(alias, primary, body):
    quote = locator(alias)
    at = body.find(quote) if isinstance(quote, str) else -1
    if at < 0:
        return False
    nearby = body[max(0, at - 80):at + len(quote) + 80]
    return alias['name'] in nearby and primary in nearby


def known_entities(lib, idx, seq):
    known = {}
    for row in sorted(prefix_rows(lib, idx, seq)['实体'], key=lambda r: r.get('chapter', 0)):
        if (row.get('chapter') or row.get('first_ch') or 0) < seq:
            ident = row.get('id') or 'E-' + digest(('legacy:' + row.get('name', '')).encode())[:12]
            known[ident] = row
    return known


def validate_scenes(value, seq, body, entity_ids, local_ids, act):
    from copy import deepcopy
    valid, rejected = [], []
    header_errors = errors(value, specification('screenplay'))
    if header_errors:
        return [], [{'reason': header_errors}]
    if not isinstance(value.get('logline'), str) or not value.get('logline') or overlaps(value['logline'], body):
        rejected.append({'reason': '本章戏剧任务缺失，或连续复制原文超过15字'})
    if value.get('act') != act:
        rejected.append({'reason': 'screenplay.act 须对应索引的显式幕区间；没有分幕时为空字符串'})
    for order, raw in enumerate(value['scenes'], 1):
        raw = deepcopy(raw)
        problem = errors(raw, specification('scene'))
        if not problem:
            raw['characters'] = [local_ids.get(c, c) for c in raw['characters']]
            problem += evidence_errors({**raw, 'evidence': raw['locator']}, body)
            if raw['chapter'] != seq or raw['order'] != order:
                problem.append('场次章号或连续顺序错配')
            expected = f'S-{seq:04d}-{order:03d}'
            if raw.get('scene_id', expected) != expected:
                problem.append('scene_id 与章节/顺序不一致')
            if len(raw['actions']) > 4 or len(raw['dialogue']) > 6:
                problem.append('动作最多4条，对白意图最多6条')
            if any(not isinstance(c, str) or c not in entity_ids for c in raw['characters']):
                problem.append('场次实体引用不存在')
            if raw['int_ext'] not in CFG['int_ext']:
                problem.append('内外景字段不合法')
            if any(not raw[k] for k in ('place', 'time_of_day', 'objective', 'obstacle', 'turn', 'outcome')) and not raw.get('unknown_reason'):
                problem.append('未知/不适用字段留空须有说明，不能为填字段编转折')
            prose = [raw.get(k, '') for k in ('slugline', 'place', 'time_of_day', 'objective', 'obstacle', 'turn', 'outcome', 'unknown_reason')]
            for action in raw['actions']:
                if not isinstance(action, str):
                    problem.append('动作必须为自己的话概括')
                else:
                    prose.append(action)
            for dialogue in raw['dialogue']:
                if not isinstance(dialogue, dict) or not all(isinstance(dialogue.get(k), str) for k in ('speaker', 'intent', 'subtext', 'locator')):
                    problem.append('对白意图须含 speaker/intent/subtext/locator')
                    continue
                dialogue['speaker'] = local_ids.get(dialogue['speaker'], dialogue['speaker'])
                if dialogue['speaker'] not in entity_ids or dialogue['speaker'] not in raw['characters']:
                    problem.append('说话人不在本场')
                if not 5 <= len(dialogue['locator']) <= 15 or dialogue['locator'] not in body:
                    problem.append('对白定位词不在本章或长度错误')
                prose += [dialogue['intent'], dialogue['subtext']]
            if any(overlaps(text, body) for text in prose):
                problem.append('场次自写概括或对白意图连续复制原文超过15字')
            if raw['confidence'] == '弱推断':
                problem.append('弱推断场次留待校验，不记完成')
        if problem:
            rejected.append({'scene_order': order, 'item': raw, 'reason': problem})
        else:
            valid.append({**raw, 'scene_id': f'S-{seq:04d}-{order:03d}', 'record_id': f'S-{seq:04d}-{order:03d}'})
    if not value['scenes']:
        rejected.append({'reason': '计划要求场次时，空场次数组不能完成'})
    return valid, rejected


def validate_chapter(lib, idx, packet, payload):
    validate('chapter', payload)
    seq = payload['chapter']
    c, body = chapter_text(lib, idx, seq)
    require(payload['chapter_hash'] == c['hash'] and packet['chapter']['hash'] == c['hash'], '章文件或派单包正文 hash 错配')
    require(packet['chapter']['seq'] == seq, '章文件与派单包 seq 错配')
    require(payload['packet_fingerprint'] == packet['fingerprint'], '章文件不属于当前派单包')
    require(packet['index_fingerprint'] == idx['fingerprint'], '派单包对应旧索引')
    require(packet['fingerprint'] == digest({k: v for k, v in packet.items() if k != 'fingerprint'}), '派单包被改过')
    require(packet.get('vocab_fingerprint') == vocabulary_fingerprint(), '派单词表或结构契约指纹已失效')
    for source in packet['context'].get('sources', []):
        if source.get('path'):
            path = local(lib, source['path'])
            require(path.is_file() and digest(path.read_bytes()) == source['sha256'], '派单上下文来源已改变')
    framework = packet.get('framework', {})
    fpath = Path(framework.get('path', ''))
    require(fpath.is_file() and digest(fpath.read_bytes()) == framework.get('sha256'), '派单时使用的总纲文件已失效')
    require(packet['context']['available'] or packet.get('independent'), '缺三件套不能进入跨章抽取')
    known = known_entities(lib, idx, seq)
    names = {r.get('name'): k for k, r in known.items() if r.get('name')}
    good = {k: [] for k in COLLECTIONS};rejected = [];pending = [];conflicts = []
    local_ids, ambiguous_names = {}, set()
    supplied = 0
    for collection in COLLECTIONS:
        values = payload.get(collection, [])
        for order, raw in enumerate(values, 1):
            supplied += 1
            if not isinstance(raw, dict):
                rejected.append({'collection': collection, 'item': raw, 'reason': ['条目必须为对象']});continue
            problem = errors(raw, specification('chapter')['fields'][collection]['entry']) + evidence_errors(raw, body)
            for key in ('aliases', 'colors', 'parts'):
                if key in raw and not isinstance(raw[key], list):
                    problem.append(f'{key} 必须为数组')
            for key in REFERENCE_FIELDS:
                if key in raw and not isinstance(raw[key], str):
                    problem.append(f'{key} 必须为实体 ID 字符串')
            if 'time' in raw and type(raw['time']) not in (str, int):
                problem.append('状态时点必须为文本或整数')
            if problem:
                rejected.append({'chapter': seq, 'collection': collection, 'item': raw, 'reason': problem})
                continue
            if raw.get('chapter', seq) != seq:
                problem.append('条目章号错配')
            for key in ('description', 'content', 'summary'):
                if isinstance(raw.get(key), str) and overlaps(raw[key], body):
                    problem.append(f'{key} 连续复制原文超过15字')
            if collection == 'state_events' and any(isinstance(raw.get(k), str) and overlaps(raw[k], body) for k in ('old', 'new')):
                problem.append('状态说明连续复制原文超过15字')
            value = {**raw, 'chapter': seq, 'evidence': locator(raw)}
            if collection == 'entities':
                if not isinstance(raw.get('name'), str) or not raw['name'].strip():
                    problem.append('新实体缺专名')
                ident = raw.get('id')
                if ident and ident not in known:
                    problem.append('实体 ID 不存在；新实体请留空，由归一步分配')
                if not ident and raw.get('name') in names and raw.get('is_new') is not True:
                    problem.append('已有同名实体，请核实 ID；同名新人物须明确 is_new=true')
                if not problem:
                    ident = ident or 'E-' + digest((raw['name'] + ':' + str(seq) + ':' + c['hash'] + ':' + str(raw.get('local_id', ''))).encode())[:12]
                    value['id'] = ident;value['first_ch'] = known.get(ident, {}).get('first_ch', seq)
                    if raw.get('local_id'):
                        if raw['local_id'] in local_ids and local_ids[raw['local_id']] != ident:
                            problem.append('local_id 重复指向不同实体')
                    if not problem and raw['confidence'] != '弱推断':
                        if raw.get('local_id'):
                            local_ids[raw['local_id']] = ident
                        if raw['name'] in local_ids and local_ids[raw['name']] != ident:
                            local_ids.pop(raw['name'], None);ambiguous_names.add(raw['name'])
                        elif raw['name'] not in ambiguous_names:
                            local_ids[raw['name']] = ident
                    category = raw.get('category', '未归类')
                    catalog = REGISTRY['setting_categories']['catalog']
                    category_aliases = {alias: name for name, info in catalog.items() for alias in info['alias']}
                    value['category'] = category if category in catalog else category_aliases.get(category, '未归类')
                    if value['category'] == '未归类' and category != '未归类':
                        pending.append({'chapter': seq, 'entity': ident, 'category': category, 'reason': '词表外类目保留为未归类，不自动创建类目'})
                    verified = []
                    for alias in raw.get('aliases', []):
                        if isinstance(alias, dict) and isinstance(alias.get('name'), str) and bool(alias['name'].strip()) and alias['name'] not in CFG['descriptive_aliases'] and alias.get('same_entity') is True and alias.get('kind') == 'proper' and not evidence_errors({**alias, 'confidence': raw['confidence']}, body) and alias_supported(alias, known.get(ident, {}).get('name', raw['name']), body):
                            verified.append(alias)
                        else:
                            pending.append({'chapter': seq, 'entity': ident, 'alias': alias, 'reason': '别名缺专名/同指声明或有效证据，不自动归并'})
                    value.pop('aliases', None)
                    previous_aliases = known.get(ident, {}).get('verified_aliases', [])
                    value['verified_aliases'] = list({digest(alias): alias for alias in previous_aliases + verified}.values())
                    # Power sources are state events, never empty immutable base-card attributes.
                    power = value.pop('power_source', None)
                    if power not in (None, '', []) and raw['confidence'] != '弱推断' and not problem:
                        good['state_events'].append({'entity': ident, 'attribute': '力量源', 'new': power, 'chapter': seq,
                                                     'confidence': raw['confidence'], 'evidence': locator(raw), 'mode': raw.get('power_mode', 'change')})
            if collection == 'emotion_points':
                if raw.get('tension') not in V['tension'] or any(color not in V['colors'] for color in raw.get('colors', [])):
                    problem.append('情绪词表不合法')
            if collection == 'foreshadows' and (raw.get('op') not in CFG['foreshadow_ops'] or not isinstance(raw.get('id'), str) or not raw['id']):
                problem.append('伏笔操作不在词表内')
            if collection == 'payoffs' and ('parts' not in raw or any(part not in CFG['payoff_parts'] for part in raw.get('parts', [])) or (raw.get('setup') is not None and (type(raw['setup']) is not int or not 1 <= raw['setup'] <= seq))):
                problem.append('爽点构件不在词表内')
            if collection == 'hooks' and (not isinstance(raw.get('type'), str) or type(raw.get('intensity')) is not int or not 1 <= raw['intensity'] <= 5):
                problem.append('钩子缺类型或强度不在1–5')
            if collection == 'units' and not (type(raw.get('start')) is int and type(raw.get('end')) is int and 1 <= raw['start'] <= raw['end'] <= len(idx['chapters'])):
                problem.append('单元范围不在索引内')
            if problem:
                rejected.append({'chapter': seq, 'collection': collection, 'item': raw, 'reason': problem})
            elif raw['confidence'] == '弱推断':
                pending.append({'chapter': seq, 'collection': collection, 'item': raw, 'reason': '弱推断，待校验，不入活跃事实台账'})
            else:
                good[collection].append(value)
    valid_ids = set(known) | {r['id'] for r in good['entities']}
    for collection, values in good.items():
        kept = []
        for value in values:
            problem = []
            for key in REFERENCE_FIELDS:
                if key in value:
                    value[key] = local_ids.get(value[key], value[key])
                    if value[key] not in valid_ids:
                        problem.append(f'{key} 引用不存在实体')
            for key in ('participants', 'characters'):
                if key in value:
                    if not isinstance(value[key], list) or any(not isinstance(v, str) for v in value[key]):
                        problem.append(f'{key} 必须为实体 ID 数组')
                    else:
                        value[key] = [local_ids.get(v, v) for v in value[key]]
                        if not set(value[key]) <= valid_ids:
                            problem.append(f'{key} 引用不存在实体')
            if collection == 'state_events':
                if not value.get('entity') or not value.get('attribute') or 'new' not in value:
                    problem.append('状态事件缺 entity/attribute/new')
                if isinstance(value.get('new'), (int, float)) and not value.get('unit'):
                    problem.append('数值状态须给量纲（或明确无量纲）')
                if value.get('attribute') == '力量源' and value.get('new') in (None, '', []):
                    pending.append({'chapter': seq, 'collection': collection, 'item': value, 'reason': '空力量源表示未确认，不作为状态断言或冲突'})
                    continue
            if problem:
                rejected.append({'chapter': seq, 'collection': collection, 'item': value, 'reason': problem})
            else:
                value['record_id'] = 'R-' + digest({'collection': collection, 'chapter': seq, 'value': value})[:24]
                value.update(schema_version=1, index_fingerprint=idx['fingerprint'], chapter_hash=c['hash'], packet_fingerprint=packet['fingerprint'])
                kept.append(value)
        good[collection] = kept
    grouped = defaultdict(list)
    for event in good['state_events']:
        grouped[(event['entity'], event['attribute'], event.get('time', seq))].append(event)
    remove = set()
    previous_states = prefix_rows(lib, idx, seq)['状态事件']
    for key, events in grouped.items():
        historical = [r for r in previous_states if 'time' in r and (r.get('entity'), r.get('attribute'), r['time']) == key]
        assertions = historical + events
        if len({digest(event['new']) for event in assertions}) > 1 and not all(event.get('mode') == 'coexist' for event in assertions):
            conflicts.append({'chapter': seq, 'entity': key[0], 'attribute': key[1], 'time': key[2], 'assertions': assertions, 'reason': '同一时点互不相容断言，待核对；不先到先得'})
            remove.update(e['record_id'] for e in events)
    good['state_events'] = [r for r in good['state_events'] if r['record_id'] not in remove]
    pre_cross_valid = sum(len(values) for values in good.values())
    chapter_facts = {LEDGERS[k]: list(values) for k, values in good.items()}
    independent = packet.get('independent', False)
    if independent:
        for collection in COLLECTIONS:
            for value in good[collection]:
                pending.append({'chapter': seq, 'collection': collection, 'item': value, 'reason': '章内独立模式，结果保留在章文件，不写跨章事实台账'})
            good[collection] = []
    scene_ids = valid_ids
    screenplay = payload.get('screenplay')
    scenes, scene_errors = validate_scenes(screenplay, seq, body, scene_ids, local_ids, packet.get('act', '')) if screenplay is not None else ([], [{'reason': '计划要求场次但未提交 screenplay'}] if packet.get('requires_screenplay') else [])
    base_errors = []
    for collection in COLLECTIONS:
        if collection not in payload:
            base_errors.append(f'缺少必要集合 {collection}；不适用也须显式提交空数组及依据')
        elif not payload[collection] and not any(isinstance(reason, str) and reason.strip() for reason in (payload.get('empty_reason'), payload.get('empty_collections', {}).get(collection))):
            base_errors.append(f'{collection} 为空但缺少无该类事实的依据')
    if payload.get('summary') and overlaps(payload['summary'], body):
        base_errors.append('章概括连续复制原文超过15字')
    if not supplied and not payload.get('empty_reason'):
        base_errors.append('没有事实条目时必须明确声明无该类事实的依据')
    if supplied and not pre_cross_valid:
        base_errors.append('全章条目均未进入有效事实，不能记完成')
    for row in scenes + rejected + pending + conflicts:
        row.update(schema_version=1, chapter=seq, index_fingerprint=idx['fingerprint'], chapter_hash=c['hash'], packet_fingerprint=packet['fingerprint'])
    return {'schema_version': 1, 'chapter': seq, 'chapter_hash': c['hash'], 'index_fingerprint': idx['fingerprint'], 'packet_fingerprint': packet['fingerprint'],
            'payload': payload, 'context_sources': packet['context'].get('sources', []), 'dependencies': packet['context'].get('dependencies', []), 'vocab_fingerprint': packet['vocab_fingerprint'], 'independent': independent, 'collection_status': {k: ('uncollected' if k not in payload else 'partial' if any(r.get('collection') == k for r in rejected + pending) or (k == 'state_events' and conflicts) else 'verified') for k in COLLECTIONS}, 'base_complete': not base_errors, 'scene_complete': bool(scenes) and not scene_errors,
            'errors': base_errors, 'scene_errors': scene_errors, 'ledgers': {LEDGERS[k]: values for k, values in good.items()},
            'chapter_facts': chapter_facts, 'scenes': scenes, 'rejected': rejected, 'pending': pending, 'conflicts': conflicts}


def ingest(lib, given=None, recover=False, layer='L2'):
    try:
        return _ingest(lib, given, recover, layer)
    except (DeconError, OSError, ValueError) as exc:
        # Source files remain untouched; an explicit rejection report survives restart.
        write(local(lib, CFG['ingest_report'] + '/latest-error.json'), {'file': str(given) if given else None, 'layer': layer, 'reason': str(exc), 'completion_not_assumed': True})
        raise


def _ingest(lib, given=None, recover=False, layer='L2'):
    from .storage import rebuild
    idx = load(lib, validate_source=layer != 'L3');plan = current(lib, idx)
    if recover:
        return rebuild(lib, idx, plan)
    require(given, '给出章 JSON 路径；恢复派生状态使用 --recover')
    path = Path(given)
    if not path.is_absolute():
        path = local(lib, given)
    payload = read(path)
    if layer == 'L3':
        return ingest_transfer(lib, idx, payload)
    validate('chapter', payload)
    seq = payload['chapter']
    require(plan and seq in plan['selected'], '章文件不在当前 L2 计划内')
    packet = read(local(lib, CFG['packets'] + f'/ch-{seq:04d}.json'))
    require(isinstance(packet, dict), '缺少本章派单包')
    validate('packet', packet)
    require(packet.get('layer') == 'L2' and isinstance(packet.get('chapter'), dict) and isinstance(packet.get('context'), dict), 'L2 派单包缺本章或上下文')
    require(packet.get('plan_fingerprint') == plan['fingerprint'], '派单包属于旧选章计划')
    receipt = validate_chapter(lib, idx, packet, payload)
    pr = commit(lib, idx, receipt, plan)
    write(local(lib, CFG['ingest_report'] + f'/ch-{seq:04d}.json'), {k: receipt[k] for k in ('chapter', 'base_complete', 'scene_complete', 'errors', 'scene_errors', 'rejected', 'pending', 'conflicts')})
    return receipt


def ingest_transfer(lib, idx, payload):
    validate('transfer', payload)
    packet = read(local(lib, CFG['transfer_packet']))
    require(packet and packet['fingerprint'] == payload['packet_fingerprint'], 'L3 报告不属于当前转化包')
    validate_transfer_packet(lib, idx, packet)
    allowed = {artifact['path']: artifact for artifact in packet['artifacts']}
    require(payload['modules'], '转化报告不能只有空模块')
    for module in payload['modules']:
        require(isinstance(module, dict) and all(isinstance(module.get(k), str) and module[k].strip() for k in ('method', 'applies', 'cost', 'invalid_when')), '转化模块必须有方法、适用条件、代价和失效条件')
        evidence = module.get('evidence', [])
        require(isinstance(evidence, list) and len(evidence) >= 2, '方法必须有至少两处已验产物证据')
        identities = set()
        for ref in evidence:
            require(isinstance(ref, dict) and isinstance(ref.get('artifact'), str) and ref['artifact'] in allowed and isinstance(ref.get('locator'), str), '转化证据不在白名单')
            artifact = allowed[ref['artifact']]
            require(5 <= len(ref['locator']) <= 15 and ref['locator'] in str(artifact['data']), '转化定位词未出现在已验报告')
            if ref.get('record_id'):
                records = [r for values in artifact['data'].get('facts', {}).values() for r in values] + artifact['data'].get('scenes', [])
                require(any(r.get('record_id') == ref['record_id'] and ref['locator'] in str(r) for r in records), '证据 record_id 或定位词不对应白名单条目')
            identities.add((ref['artifact'], ref.get('record_id', 'artifact')))
        require(len(identities) >= 2, '重复证据不能冒充两处')
    write(local(lib, CFG['transfer_report']), payload)
    pr = progress(lib, idx);pr['layers']['L3'] = {'planned': ['modules'], 'done': ['modules'], 'failed': {}, 'waived': {}, 'artifact_fingerprint': digest(payload)}
    write(local(lib, CFG['progress']), pr)
    return payload
