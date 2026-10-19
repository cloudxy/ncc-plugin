"""Allowlisted semantics. Definitions never execute Python, SQL, JS or arbitrary regex."""

import copy
from decimal import Decimal, InvalidOperation

from ncc_shared.errors import DomainError, require

VALUE_TYPES = {
    "text",
    "integer",
    "decimal",
    "boolean",
    "enum",
    "tags",
    "reference",
    "references",
    "ratio",
    "quantity",
    "coordinate",
    "attachment",
    "soft_reference",
}


def validate_definition(spec):
    require(isinstance(spec, dict), "definition", "定义必须为对象")
    allowed = {
        "label",
        "domain",
        "properties",
        "required",
        "relation",
        "source_kinds",
        "target_kinds",
        "exclusive_target",
        "acyclic",
        "capabilities",
    }
    require(not (set(spec) - allowed), "definition", "存在不支持的定义键", fields=sorted(set(spec) - allowed))
    props = spec.get("properties", {})
    require(isinstance(spec.get("label", ""), str), "definition", "类型名称必须是文字")
    require(isinstance(spec.get("required", []), list), "definition", "必填项必须为列表")
    require(isinstance(props, dict) and len(props) <= 100, "definition", "属性定义无效或超过100项")
    for key, value in props.items():
        require(
            isinstance(key, str) and 0 < len(key) <= 128 and isinstance(value, dict),
            "definition",
            "属性定义无效",
        )
        require(value.get("type") in VALUE_TYPES, "definition", f"{key}使用了不支持的值类型")
        require(
            not set(value)
            - {"type", "label", "enum", "minimum", "maximum", "max_length", "kinds", "default", "secret"},
            "definition",
            f"{key}含有不支持的约束",
        )
        if value["type"] == "enum":
            require(
                isinstance(value.get("enum"), list)
                and value["enum"]
                and all(isinstance(item, str) for item in value["enum"]),
                "definition",
                f"{key}枚举必须为非空字符串列表",
            )
        require(isinstance(value.get("secret", False), bool), "definition", f"{key}秘密标记无效")
        require(
            isinstance(value.get("max_length", 100000), int)
            and 0 < value.get("max_length", 100000) <= 2_000_000,
            "definition",
            f"{key}长度约束无效",
        )
        for bound in ["minimum", "maximum"]:
            if bound in value:
                try:
                    valid = Decimal(str(value[bound])).is_finite()
                except (InvalidOperation, ValueError, TypeError):
                    valid = False
                require(valid, "definition", f"{key}数值约束无效")
        if "minimum" in value and "maximum" in value:
            require(
                Decimal(str(value["minimum"])) <= Decimal(str(value["maximum"])),
                "definition",
                f"{key}范围倒置",
            )
        if "default" in value:
            validate_values(
                {"properties": {key: {k: v for k, v in value.items() if k != "default"}}},
                {key: value["default"]},
            )
    require(set(spec.get("required", [])) <= set(props), "definition", "必填项必须已定义")


def decimal_string(value, field):
    require(isinstance(value, str), "precision", f"{field}必须以字符串传递精确数值")
    try:
        number = Decimal(value)
        require(number.is_finite() and len(value) <= 100, "precision", f"{field}数值无效")
        return number
    except InvalidOperation:
        raise DomainError("precision", f"{field}不是有效精确数值") from None


def validate_values(spec, data):
    require(isinstance(data, dict), "attributes", "属性必须是对象")
    props = spec.get("properties", {})
    for key, rule in props.items():
        if key not in data and "default" in rule:
            data[key] = copy.deepcopy(rule["default"])
    require(
        not set(data) - set(props),
        "unknown_attribute",
        "请先注册未知属性",
        fields=sorted(set(data) - set(props)),
    )
    for key in spec.get("required", []):
        require(
            key in data and data[key] not in (None, "", []), "required", f"缺少必填属性：{key}", field=key
        )
    for key, value in data.items():
        rule = props[key]
        kind = rule["type"]
        if kind == "text":
            valid = isinstance(value, str) and len(value) <= rule.get("max_length", 100_000)
        elif kind == "integer":
            valid = isinstance(value, int) and not isinstance(value, bool)
        elif kind == "boolean":
            valid = isinstance(value, bool)
        elif kind == "enum":
            valid = value in rule["enum"]
        elif kind in {"reference", "attachment"}:
            valid = isinstance(value, str) and len(value) == 36
        elif kind == "soft_reference":
            valid = (
                isinstance(value, dict)
                and set(value) <= {"uri", "kind", "label"}
                and isinstance(value.get("uri"), str)
            )
            valid = (
                valid
                and value["uri"].startswith("ncc://")
                and len(value["uri"]) <= 1024
                and all(isinstance(v, str) for v in value.values())
            )
        elif kind in {"tags", "references"}:
            valid = isinstance(value, list) and len(value) <= 1000 and all(isinstance(v, str) for v in value)
        elif kind == "decimal":
            decimal_string(value, key)
            valid = True
        elif kind == "ratio":
            valid = isinstance(value, dict) and set(value) == {"numerator", "denominator"}
            if valid:
                decimal_string(value["numerator"], key)
                require(
                    decimal_string(value["denominator"], key) != 0, "precision", "比率分母不得为零", field=key
                )
        elif kind == "quantity":
            valid = (
                isinstance(value, dict)
                and set(value) == {"amount", "unit"}
                and isinstance(value["unit"], str)
            )
            if valid:
                decimal_string(value["amount"], key)
        elif kind == "coordinate":
            valid = (
                isinstance(value, dict)
                and set(value) == {"x", "y", "frame"}
                and isinstance(value["frame"], str)
            )
            if valid:
                decimal_string(value["x"], key)
                decimal_string(value["y"], key)
        else:
            valid = False
        require(valid, "attribute_type", f"{key}不符合{kind}类型", field=key)
        if kind in {"integer", "decimal"}:
            number = Decimal(str(value))
            require(
                "minimum" not in rule or number >= Decimal(str(rule["minimum"])),
                "range",
                f"{key}低于下限",
                field=key,
            )
            require(
                "maximum" not in rule or number <= Decimal(str(rule["maximum"])),
                "range",
                f"{key}超过上限",
                field=key,
            )
