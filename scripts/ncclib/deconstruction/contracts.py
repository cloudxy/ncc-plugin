"""有限结构契约解释器；语义证据校验由入库层负责。"""
from pathlib import Path
from .common import read, require, DeconError, REGISTRY

CONTRACT_ROOT = Path(__file__).resolve().parents[3] / 'workflow/contracts/deconstruction'


def specification(name):
    value = read(CONTRACT_ROOT / (name + '.json'))
    require(isinstance(value, dict) and value.get('format') == 'ncc-structure-1', f'未知结构契约：{name}')
    return value['structure']


def errors(value, spec, path='$'):
    result = []
    kind = spec.get('type', 'any')
    types = {'object': lambda v: isinstance(v, dict), 'array': lambda v: isinstance(v, list),
             'string': lambda v: isinstance(v, str), 'integer': lambda v: type(v) is int,
             'boolean': lambda v: type(v) is bool, 'any': lambda v: True}
    if value is None and spec.get('nullable'):
        return []
    if kind not in types or not types[kind](value):
        return [f'{path} 应为 {kind}']
    if 'const' in spec and (value != spec['const'] or type(value) is not type(spec['const'])):
        result.append(f'{path} 应为 {spec["const"]!r}')
    choices = spec.get('enum')
    if spec.get('vocab'):
        choices = REGISTRY['vocab'][spec['vocab']]['values']
    if choices is not None and value not in choices:
        result.append(f'{path} 不在允许词表内')
    if type(value) is int:
        if 'minimum' in spec and value < spec['minimum']:
            result.append(f'{path} 小于下限 {spec["minimum"]}')
        if 'maximum' in spec and value > spec['maximum']:
            result.append(f'{path} 超过上限 {spec["maximum"]}')
    if isinstance(value, (str, list)):
        if len(value) < spec.get('min_length', 0):
            result.append(f'{path} 长度不足')
        if 'max_length' in spec and len(value) > spec['max_length']:
            result.append(f'{path} 长度超限')
    if kind == 'object':
        fields = spec.get('fields', {})
        if spec.get('additional') is False:
            result += [f'{path}.{key} 不是允许字段' for key in set(value) - set(fields)]
        for key in spec.get('required', []):
            if key not in value:
                result.append(f'{path}.{key} 缺失')
        for key, child in fields.items():
            if key in value:
                result += errors(value[key], child, path + '.' + key)
    if kind == 'array' and 'items' in spec:
        for i, item in enumerate(value):
            result += errors(item, spec['items'], f'{path}[{i}]')
    return result


def validate(name, value):
    problem = errors(value, specification(name))
    if problem:
        raise DeconError('结构契约不符：' + '；'.join(problem))


def field_rows(name):
    def walk(spec, path=''):
        for key, field in spec.get('fields', {}).items():
            here = path + key
            limits = {k: field[k] for k in ('minimum', 'maximum', 'min_length', 'max_length') if k in field}
            yield here, field.get('type', 'any'), key in spec.get('required', []), field.get('nullable', False), field.get('description', ''), field.get('const', field.get('enum', 'vocab:' + field['vocab'] if field.get('vocab') else '')), field.get('default', '不自动补值'), limits
            if field.get('type') == 'object':
                yield from walk(field, here + '.')
            if field.get('entry'):
                yield from walk(field['entry'], here + '[条目].')
            elif field.get('items', {}).get('type') == 'object':
                yield from walk(field['items'], here + '[].')
    return list(walk(specification(name)))
