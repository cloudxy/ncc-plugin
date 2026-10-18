"""拆书统一 CLI 调度；保持旧 link/技法接口，输出只在拆书库。"""
import json
from pathlib import Path
from .common import DECON_CFG as CFG, DeconError, require, read, write, local, locked
from . import index, planning, ingest, reporting, storage


def run(args, legacy, legacy_baseline):
    if args.action == 'link':
        return legacy(args)
    lib = Path(args.lib).resolve()
    require(lib.is_dir(), f'拆书库目录不存在：{lib}')
    action = args.action
    # Read-only actions keep their side-effect-free contract.
    write_action = action in ('index', 'plan', 'packet', 'ingest', 'mark') or (action == 'stats' and getattr(args, 'write', False))
    from contextlib import nullcontext
    with locked(lib) if write_action else nullcontext():
        if action == 'index':
            result = index.create(lib, getattr(args, 'source', None), getattr(args, 'config', None), getattr(args, 'accept_reindex', False))
            print(f"OK 章节索引 {len(result['chapters'])} 章；warning {len(result['diagnostics']['warnings'])} 项，blocker 0 项")
            for warning in result['diagnostics']['warnings']:
                print('WARNING: ' + warning['message'])
            return
        if action == 'plan':
            result = planning.make_plan(lib, args.goal, args.select, args.reason, args.screenplay)
            print(json.dumps(result, ensure_ascii=False, indent=2));return
        if action == 'packet':
            path, result = planning.packet(lib, args.seq, args.layer, args.context, args.independent, args.framework)
            print(f"OK {path} {result['fingerprint']}");return
        if action == 'ingest':
            result = ingest.ingest(lib, args.file, args.recover, args.layer)
            if args.recover:
                print('OK 已从验收章重建台账和逐章进度');return
            print(json.dumps({k: v for k, v in result.items() if k in ('chapter', 'base_complete', 'scene_complete', 'errors', 'scene_errors', 'layer', 'modules')}, ensure_ascii=False, indent=2))
            if result.get('base_complete') is False:
                raise DeconError('章文件尚需修复；有效条目已留存，进度未记完成')
            if result.get('scene_errors'):
                raise DeconError('基本事实与场次分别记账；场次尚需修复，不能记场次完成')
            return
        if action in ('mark', 'coverage') and not getattr(args, 'layer', None) and not local(lib, CFG['plan']).exists():
            old = read(local(lib, CFG['progress']), {})
            if old.get('schema_version', 0) < 2:
                return legacy(args)
        if action == 'coverage' and (getattr(args, 'layer', None) or local(lib, CFG['plan']).exists()):
            result = reporting.coverage(lib, args.layer)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            require(result['complete'], 'COVERAGE FAIL：仍有未验收或未说明的计划缺项');return
        idx = index.load(lib)
        plan = planning.current(lib, idx)
        if action == 'mark':
            old = read(local(lib, CFG['progress']), {})
            if old.get('schema_version', 0) < 2 and plan is None and not getattr(args, 'layer', None):
                return legacy(args)
            pr = storage.progress(lib, idx)
            if args.done:
                selected = planning.sequence_set(args.done, len(idx['chapters']))
                valid = {r['chapter'] for r in storage.receipts(lib, idx) if r['base_complete']}
                if getattr(args, 'layer', None) == 'screenplay':
                    valid = {r['chapter'] for r in storage.receipts(lib, idx) if r['scene_complete']}
                require(set(selected) <= valid, '新契约章不能手动绕过产物验证；请先 decon ingest')
                storage.rebuild(lib, idx, plan);print('OK 已核实入库产物并刷新进度');return
            require(args.skip is not None and args.why and 1 <= args.skip <= len(idx['chapters']), '跳过须给合法 seq 和 --why')
            layer = getattr(args, 'layer', None) or 'L2'
            require(layer in ('L2', 'screenplay'), '新层只允许显式豁免 L2 或 screenplay')
            require(plan and args.skip in (plan['selected'] if layer == 'L2' else plan['screenplay']), '只能豁免当前层计划中的 seq，未选章不计跳过')
            entry = pr['layers'].setdefault(layer, {'planned': [], 'done': [], 'failed': {}, 'waived': {}})
            entry.setdefault('waived', {})[str(args.skip)] = args.why
            write(local(lib, CFG['progress']), pr);print(f'OK {layer} 显式豁免 {args.skip}：{args.why}');return
        if action == 'coverage':
            if not getattr(args, 'layer', None) and plan is None:
                return legacy(args)
            result = reporting.coverage(lib, args.layer)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            require(result['complete'], 'COVERAGE FAIL：仍有未验收或未说明的计划缺项');return
        if action == 'stats':
            window = None
            if args.range:
                values = planning.sequence_set(args.range, len(idx['chapters']))
                require(values and values == list(range(min(values), max(values) + 1)), '统计 --range 必须是连续范围')
                window = (min(values), max(values))
            result, target = reporting.statistics(lib, window, getattr(args, 'layer', None), legacy_baseline)
            if args.write:
                reporting.write_report(lib, result, target)
                print(f'OK 报告写入 {target}')
            print(json.dumps(result, ensure_ascii=False, indent=2));return
        raise DeconError(f'未知拆书操作：{action}')
