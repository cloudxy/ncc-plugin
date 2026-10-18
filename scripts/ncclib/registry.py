"""注册表读取：分片是可编辑源，registry.json 是严格校验的兼容生成视图。"""
import json
from pathlib import Path

KEY_ORDER = ('schema_version', 'preparation', 'commands', 'layers', 'ledgers', 'roles', 'stages', 'gates', 'axioms', 'iron_rules', 'scene_cards', 'writing_modes', 'principle', 'loops', 'review_plan', 'knowledge', 'materials', 'avoidance', 'setting_base', 'style', 'reader_personas', 'preferences', 'craft_library', 'eval', 'dashboard', 'export', 'length', 'principles', 'stage_table', 'vocab', 'layout', 'layout_legacy', 'load_budget', 'memory', 'handoff', 'review_words', 'setting_categories', 'decon', 'techniques', 'evolution', 'check_words')

SHARD_KEYS = {
    'flow.json': ('schema_version', 'stages', 'stage_table', 'layers', 'gates', 'loops', 'writing_modes'),
    'roles.json': ('roles', 'commands', 'load_budget'),
    'rules.json': ('axioms', 'iron_rules', 'principle', 'principles', 'scene_cards', 'review_plan', 'review_words', 'check_words', 'avoidance', 'length', 'reader_personas'),
    'storage.json': ('vocab', 'layout', 'layout_legacy', 'ledgers'),
    'preparation.json': ('preparation', 'knowledge', 'materials', 'setting_base', 'setting_categories'),
    'learning.json': ('style', 'preferences', 'craft_library', 'memory', 'handoff', 'decon', 'techniques', 'evolution'),
    'delivery.json': ('eval', 'dashboard', 'export'),
}


class RegistryError(ValueError):
    """错误必须包含源文件位置，不用空配置掩盖。"""


def _read_object(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise RegistryError(f"{path}: 重复 JSON 键 {key!r}")
            result[key] = value
        return result
    def constant(value):
        raise ValueError(f"非法 JSON 常量 {value}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique, parse_constant=constant)
    except RegistryError:
        raise
    except (OSError, UnicodeError, ValueError) as exc:
        raise RegistryError(f"{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RegistryError(f"{path}: 根必须为对象")
    return data


def _keys(data, expected, path):
    missing, extra = set(expected) - set(data), set(data) - set(expected)
    if missing or extra:
        raise RegistryError(f"{path}: 缺少键 {sorted(missing)}；未知或归属错误的键 {sorted(extra)}")


def registry_path(plugin_root):
    root = Path(plugin_root).resolve()
    path = root / "workflow/registry.json"
    if not path.resolve().is_relative_to(root):
        raise RegistryError(f"{path}: 路径越界")
    return path


def serialize_registry(data):
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def merge_registry(plugin_root):
    """构建时不读取旧聚合视图，保证陈旧/缺失视图可被重新生成。"""
    root = Path(plugin_root).resolve()
    directory = root / "workflow/registry"
    if not directory.is_dir() or not directory.resolve().is_relative_to(root):
        raise RegistryError(f"{directory}: 缺少分片目录或路径越界")
    unknown = {p.name for p in directory.glob("*.json")} - set(SHARD_KEYS)
    if unknown:
        raise RegistryError(f"{directory}: 未知分片 {sorted(unknown)}")
    merged = {}
    for name, keys in SHARD_KEYS.items():
        path = directory / name
        if not path.resolve().is_relative_to(root):
            raise RegistryError(f"{path}: 路径越界")
        data = _read_object(path)
        _keys(data, keys, path)
        duplicate = set(merged) & set(data)
        if duplicate:
            raise RegistryError(f"{path}: 跨片重复键 {sorted(duplicate)}")
        merged.update(data)
    _keys(merged, KEY_ORDER, directory)
    return {key: merged[key] for key in KEY_ORDER}


def load_registry(plugin_root):
    """所有运行消费者共用此接口；不回退单文件或默认值。"""
    merged = merge_registry(plugin_root)
    path = registry_path(plugin_root)
    view = _read_object(path)
    _keys(view, KEY_ORDER, path)
    # 比较规范字节也检查对象迭代顺序；词表/布局等嵌套顺序同样保留。
    if path.read_bytes() != serialize_registry(merged).encode('utf-8'):
        raise RegistryError(f"{path}: 聚合视图陈旧；运行 python3 scripts/dev/build_registry.py")
    return merged
