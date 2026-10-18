"""卷/章索引、可解释诊断及原文指纹；不会绕过结构阻塞。"""
import re
from pathlib import Path
from .common import DECON_CFG, DeconError, require, read, write, local, digest
from .contracts import validate

DIGITS = {c: n for n, chars in enumerate(('零〇', '一', '二两', '三', '四', '五', '六', '七', '八', '九')) for c in chars}
UNITS = {'十': 10, '百': 100, '千': 1000, '万': 10000}
RULES = DECON_CFG['index_rules']
CHAPTER = re.compile(RULES['chapter'])
VOLUME = re.compile(RULES['volume'])
SPECIAL = re.compile(RULES['special'])
PART = re.compile(RULES['part'])


def number(text):
    if text.isdigit():
        return int(text)
    total = section = value = 0
    for ch in text:
        if ch in DIGITS:
            value = DIGITS[ch]
        elif ch in UNITS:
            if UNITS[ch] == 10000:
                total += (section + value) * 10000; section = 0
            else:
                section += (value or 1) * UNITS[ch]
            value = 0
    return total + section + value


def build(text, config=None):
    config = config or {}
    lines = text.splitlines()
    warnings, blockers, heads, echoes = [], [], [], []
    volume = ''
    indent = config.get('title_indent', 0)
    require(type(indent) is int and indent >= 0, 'title_indent 必须为非负整数')
    require(isinstance(config.get('exclude_titles', []), list) and all(isinstance(v, str) for v in config.get('exclude_titles', [])), 'exclude_titles 必须为标题字符串数组')
    require(not config.get('chapter_pattern') or isinstance(config['chapter_pattern'], str), 'chapter_pattern 必须为整行正则文本')
    pattern = re.compile(config['chapter_pattern']) if config.get('chapter_pattern') else None
    excluded = set(config.get('exclude_titles', []))
    excluded_lines = set()
    excluded_ranges = config.get('exclude_ranges', [])
    require(isinstance(excluded_ranges, list), 'exclude_ranges 必须为数组')
    for entry in excluded_ranges:
        require(isinstance(entry, dict) and isinstance(entry.get('reason'), str) and entry['reason'].strip(), '排除原文范围必须有核对理由')
        start, end = entry.get('start'), entry.get('end')
        require(type(start) is int and type(end) is int and 1 <= start <= end <= len(lines), '排除行范围越界')
        excluded_lines.update(range(start - 1, end))
    volume_boundaries = []
    for i, line in enumerate(lines):
        title = line.strip()
        if i in excluded_lines or title in excluded:
            continue
        if len(line) - len(line.lstrip()) != indent:
            # Echoes may be indented even when real headings are not.
            if heads and title == heads[-1]['title'] and i - heads[-1]['line'] <= 3 and not any(s.strip() for s in lines[heads[-1]['line'] + 1:i]):
                echoes.append(i)
            continue
        if VOLUME.fullmatch(title):
            volume = title; volume_boundaries.append(i)
            continue
        match = CHAPTER.fullmatch(title)
        if not (match or SPECIAL.fullmatch(title) or (pattern and pattern.fullmatch(title))):
            continue
        if heads and title == heads[-1]['title'] and i - heads[-1]['line'] <= 3 and not any(s.strip() for s in lines[heads[-1]['line'] + 1:i]):
            echoes.append(i)
            continue
        part = PART.search(title)
        heads.append({'line': i, 'title': title, 'volume': volume, 'no': number(match[1]) if match else (0 if SPECIAL.fullmatch(title) else None),
                      'part': (part[1] or part[2]) if part else ''})
    manual = config.get('chapters')
    if manual is not None:
        require(isinstance(manual, list) and manual, '人工章节边界必须为非空数组')
        heads = []
        for entry in manual:
            require(isinstance(entry, dict) and entry.get('reason'), '人工边界必须有核对理由')
            start, end = entry.get('start'), entry.get('end')
            require(type(start) is int and type(end) is int and 1 <= start < end <= len(lines), '人工 span 越界或没有正文')
            require(all(isinstance(entry.get(key, ''), str) for key in ('title', 'volume', 'part')), '人工标题/卷名/分章标记必须为文本')
            require(entry.get('no') is None or type(entry['no']) is int, '人工原文章号必须为整数或 null')
            heads.append({'line': start - 1, 'manual_end': end, 'title': entry.get('title', lines[start - 1].strip()),
                          'volume': entry.get('volume', ''), 'no': entry.get('no'), 'part': entry.get('part', ''), 'override_reason': entry['reason']})
        require(all(a['manual_end'] <= b['line'] for a, b in zip(heads, heads[1:])), '人工章节边界重叠或顺序错误')
    chapters, seen = [], set()
    for k, h in enumerate(heads):
        end = h.get('manual_end', heads[k + 1]['line'] if k + 1 < len(heads) else len(lines))
        bounds = [b for b in volume_boundaries if h['line'] < b < end]
        if bounds and not manual:
            end = min(bounds)
        ignored_echoes = [x for x in echoes if h['line'] < x < end]
        ignored_config = sorted(x for x in excluded_lines if h['line'] < x < end)
        body = '\n'.join(s for j, s in enumerate(lines[h['line'] + 1:end], h['line'] + 1) if j not in set(ignored_echoes) | excluded_lines)
        han = len(re.findall(r'[\u4e00-\u9fff]', body))
        chapter = {key: h[key] for key in ('title', 'volume', 'no', 'part')}
        chapter.update(seq=k + 1, start=h['line'] + 1, end=end, body_start=h['line'] + 2, han=han,
                       hash=digest(body.encode('utf-8'))[:16], ignored_echo_lines=[x + 1 for x in ignored_echoes], ignored_config_lines=[x + 1 for x in ignored_config])
        if h.get('override_reason'):
            chapter['override_reason'] = h['override_reason']
        if not body.strip():
            blockers.append({'seq': k + 1, 'code': 'empty_body', 'message': '零正文章或空篇名，需要核对边界'})
        elif han < 100:
            warnings.append({'seq': k + 1, 'code': 'short', 'message': '短章，请核对；不据字数判空章'})
        if h['part']:
            warnings.append({'seq': k + 1, 'code': 'multipart', 'message': f'原文同号分章标记：{h["part"]}'})
        identity = (h['volume'], h['no'], h['part'])
        if h['no'] is not None and identity in seen and not h.get('override_reason'):
            blockers.append({'seq': k + 1, 'code': 'ambiguous_number', 'message': '同卷同号且无可区分分章；需显式边界与核对理由'})
        seen.add(identity)
        if chapters and h['volume'] == chapters[-1]['volume'] and h['no'] is not None and chapters[-1]['no'] is not None:
            prev = chapters[-1]['no']
            if h['no'] not in (prev, prev + 1) and prev != 0:
                warnings.append({'seq': k + 1, 'code': 'number_gap', 'message': f'原文跳号：第 {prev} 章之后是第 {h["no"]} 章'})
        chapters.append(chapter)
    if not chapters:
        blockers.append({'code': 'no_heading', 'message': '没有可识别章节；请配置整行标题或显式边界'})
    covered = set(excluded_lines) | set(volume_boundaries) | {i for i, line in enumerate(lines) if line.strip() in excluded}
    for chapter in chapters:
        covered.update(range(chapter['start'] - 1, chapter['end']))
    unassigned = [i + 1 for i, line in enumerate(lines) if line.strip() and i not in covered]
    if chapters and unassigned:
        blockers.append({'code': 'unassigned_text', 'lines': unassigned, 'message': '存在章节切片之外的非空原文；核对前言/卷引，配置明确章节或有理由的 exclude_ranges'})
    return chapters, {'warnings': warnings, 'blockers': blockers, 'ignored_echo_lines': [i + 1 for i in echoes], 'excluded_ranges': excluded_ranges}


def source(lib, given=None):
    if given:
        p = Path(given)
        if not p.is_absolute():
            p = local(lib, given)
    else:
        choices = sorted(p for p in local(lib, '原文').glob('*') if p.suffix in ('.txt', '.md') and p.is_file())
        require(bool(choices), '原文目录没有 txt/md，请提供 --source')
        p = choices[0]
    require(p.is_file(), f'原文不存在：{p}')
    return p


def create(lib, given=None, config_path=None, accept=False):
    src = source(lib, given)
    config_file = Path(config_path) if config_path else local(lib, DECON_CFG['index_config'])
    require(not config_path or config_file.is_file(), '显式索引配置文件不存在')
    config = read(config_file, {})
    require(isinstance(config, dict), '索引配置必须为对象')
    raw = src.read_bytes()
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeError as exc:
        raise DeconError(f'原文编码无法读取，请先显式转换为 UTF-8：{exc}') from exc
    chapters, diagnostics = build(text, config)
    act_ranges = config.get('act_ranges', [])
    require(isinstance(act_ranges, list), 'act_ranges 必须为数组')
    seen_end = 0
    for act in act_ranges:
        require(isinstance(act, dict) and all(isinstance(act.get(k), str) and act[k].strip() for k in ('name', 'source')), '戏剧幕区间须有 name 与 source')
        require(type(act.get('start')) is int and type(act.get('end')) is int and seen_end < act['start'] <= act['end'] <= len(chapters), '戏剧幕区间越界、重叠或顺序错误')
        seen_end = act['end']
    write(local(lib, DECON_CFG['diagnostics']), diagnostics)
    require(not diagnostics['blockers'], '索引结构阻塞：' + '；'.join(d['message'] for d in diagnostics['blockers']))
    src_name = str(src.resolve().relative_to(Path(lib).resolve())) if src.resolve().is_relative_to(Path(lib).resolve()) else str(src.resolve())
    payload = {'schema_version': 2, 'source': src_name, 'sha': digest(raw)[:16], 'source_sha256': digest(raw),
               'rule_version': RULES['version'], 'rule_fingerprint': digest(RULES), 'config': config, 'config_sha256': digest(config), 'chapters': chapters, 'diagnostics': diagnostics,
               'act_ranges': config.get('act_ranges', [])}
    payload['fingerprint'] = digest(payload)
    validate('index', payload)
    path = local(lib, DECON_CFG['index']);old = read(path, {})
    if old and (old.get('sha') != payload['sha'] or (old.get('fingerprint') and old['fingerprint'] != payload['fingerprint']) or
                [(c['seq'], c['start'], c['end'], c['hash']) for c in old.get('chapters', [])] != [(c['seq'], c['start'], c['end'], c['hash']) for c in chapters]):
        old_map = {c['seq']: c for c in old.get('chapters', [])}
        impact = {'old_fingerprint': old.get('fingerprint', old.get('sha')), 'new_fingerprint': payload['fingerprint'],
                  'changed_seq': [c['seq'] for c in chapters if old_map.get(c['seq'], {}).get('hash') != c['hash']],
                  'removed_seq': sorted(set(old_map) - {c['seq'] for c in chapters}), 'old_progress_not_migrated': True}
        write(local(lib, DECON_CFG['reindex_report']), impact)
        require(accept, '原文或切片已改变：已生成重建影响清单；核对后用 --accept-reindex 显式重建，不自动迁移进度')
        backup = DECON_CFG['index_backup'] + '/' + str(old.get('fingerprint', old.get('sha', 'legacy')))
        write(local(lib, backup + '/chapter_index.json'), old)
        previous = read(local(lib, DECON_CFG['progress']), {})
        write(local(lib, backup + '/progress.json'), previous)
        write(local(lib, DECON_CFG['progress']), {'schema_version': 2, 'index_fingerprint': payload['fingerprint'], 'done': [], 'skipped': {}, 'layers': {}, 'invalidated': impact})
    write(path, payload)
    return payload


def load(lib, validate_source=True):
    idx = read(local(lib, DECON_CFG['index']))
    require(isinstance(idx, dict) and idx.get('chapters'), '还没有章节索引（decon index）')
    if idx.get('schema_version') == 2:
        validate('index', idx)
        require(idx['fingerprint'] == digest({k: v for k, v in idx.items() if k != 'fingerprint'}), '索引被手改过，请按配置重建')
    require([c['seq'] for c in idx['chapters']] == list(range(1, len(idx['chapters']) + 1)), '索引 seq 不连续')
    require(all(c['start'] < c['end'] for c in idx['chapters']) and all(a['end'] < b['start'] for a, b in zip(idx['chapters'], idx['chapters'][1:])), '索引 span 为空、重叠或乱序')
    require(not idx.get('diagnostics', {}).get('blockers'), '索引含结构 blocker，不能抽取')
    if 'fingerprint' not in idx:
        idx['fingerprint'] = digest(idx)
    if validate_source:
        src = Path(idx['source'])
        if not src.is_absolute():
            src = local(lib, idx['source'])
        require(src.is_file(), '索引对应的原文不存在')
        require(digest(src.read_bytes())[:16] == idx.get('sha'), '原文在建索引之后变过：请显式重建索引')
    return idx


def chapter_text(lib, idx, seq, lines=None):
    require(type(seq) is int and 1 <= seq <= len(idx['chapters']), '章节序号不在索引内')
    chapter = idx['chapters'][seq - 1]
    src = Path(idx['source'])
    if not src.is_absolute():
        src = local(lib, idx['source'])
    if lines is None:
        lines = src.read_text('utf-8-sig').splitlines()
    ignored = set(chapter.get('ignored_echo_lines', [])) | set(chapter.get('ignored_config_lines', []))
    body = '\n'.join(line for n, line in enumerate(lines[chapter['start']:chapter['end']], chapter['start'] + 1) if n not in ignored)
    require(digest(body.encode('utf-8'))[:16] == chapter['hash'], '正文切片 hash 与索引错配')
    return chapter, body
