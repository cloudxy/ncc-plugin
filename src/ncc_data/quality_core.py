"""Shared standard-library scoring kernel for the file CLI and optional web service."""

from decimal import Decimal, InvalidOperation


def evaluate_report(policy, policy_hash, scheme, content, raw, sources=()):
    def incomplete(reason):
        return {"score": None, "verdict": "incomplete", "errors": [reason], "policy_hash": policy_hash}

    if scheme not in policy["profiles"] or not isinstance(raw, dict):
        return incomplete("未知评分方案或报告格式")
    expected = {x["key"] for x in policy["profiles"][scheme]}
    if set(raw) - {"dimensions", "hard", "coverage", "observations", "summary", "suggestions"}:
        return incomplete("报告含未注册字段")
    if not isinstance(raw.get("dimensions"), dict) or set(raw["dimensions"]) != expected:
        return incomplete("适用维度缺失或含未知项")
    if raw.get("hard") not in {"pass", "fail", "unknown"} or raw.get("coverage") != "complete":
        return incomplete("检查结论无效或覆盖不足")
    if not isinstance(raw.get("summary"), str) or not 0 < len(raw["summary"]) <= 4000:
        return incomplete("缺少有效总结")
    if not isinstance(raw.get("observations", []), list) or len(raw.get("observations", [])) > 100:
        return incomplete("问题清单无效")
    if not isinstance(raw.get("suggestions", []), list) or len(raw.get("suggestions", [])) > 10:
        return incomplete("修改建议无效")
    normalized, score, floor = {}, Decimal(0), False
    for rule in policy["profiles"][scheme]:
        key = rule["key"]
        dim = raw["dimensions"][key]
        if not isinstance(dim, dict) or set(dim) != {"score", "evidence", "reason"}:
            return incomplete(key + "分项字段无效")
        try:
            value = Decimal(str(dim["score"]))
        except (InvalidOperation, ValueError):
            return incomplete(key + "分数无效")
        if not value.is_finite() or not 0 <= value <= 5 or value * 2 != int(value * 2):
            return incomplete(key + "须为0至5的半分步长")
        evidence = dim["evidence"]
        if (
            not isinstance(evidence, list)
            or not 1 <= len(evidence) <= 8
            or not all(
                isinstance(quote, str) and quote and any(quote in text for text in (content, *sources))
                for quote in evidence
            )
        ):
            return incomplete(key + "证据不可定位")
        if not isinstance(dim["reason"], str) or not 0 < len(dim["reason"]) <= 2000:
            return incomplete(key + "缺少具体依据")
        normalized[key] = {**dim, "score": str(value)}
        score += Decimal(rule["weight"]) * value / 5
        floor |= value < policy["dimension_floor"]
    observations = raw.get("observations", [])
    if not all(
        isinstance(x, dict) and x.get("severity") in {"critical", "major", "minor"} for x in observations
    ):
        return incomplete("问题严重度无效")
    if not all(
        isinstance(x.get("quote"), str)
        and x["quote"]
        and any(x["quote"] in text for text in (content, *sources))
        and isinstance(x.get("reason"), str)
        and x["reason"].strip()
        for x in observations
    ):
        return incomplete("问题缺少可定位原文或具体理由")
    hard = raw["hard"] != "pass" or any(x["severity"] in {"critical", "major"} for x in observations)
    verdict = (
        "blocked"
        if hard
        else "restructure"
        if score < policy["restructure_threshold"]
        else "revise"
        if floor or score < policy["quality_threshold"]
        else "qualified"
    )
    return {
        "score": str(score.quantize(Decimal("0.1"))),
        "verdict": verdict,
        "policy_hash": policy_hash,
        "report": {**raw, "dimensions": normalized},
        "dimension_floor_failed": floor,
    }
