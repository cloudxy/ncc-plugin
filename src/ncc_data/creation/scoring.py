"""Deterministic report verification and routing; no invented reader-quality probability."""

from decimal import Decimal

from ncc_shared.errors import require
from ncc_shared.quality.policy import POLICY, POLICY_HASH
from ncc_shared.quality.scoring import evaluate_report


def evaluate(scheme, content, raw, sources=()):
    require(scheme in POLICY["profiles"], "scheme", "未知评分方案")
    return evaluate_report(POLICY, POLICY_HASH, scheme, content, raw, sources)


def disagreement(a, b):
    if a.get("verdict") in {"blocked", "incomplete"} or b.get("verdict") in {"blocked", "incomplete"}:
        return True
    if a.get("score") is None or b.get("score") is None:
        return True
    if abs(Decimal(a["score"]) - Decimal(b["score"])) > 10:
        return True
    ar, br = a.get("report", {}), b.get("report", {})
    if ar.get("hard") != br.get("hard"):
        return True
    return any(
        abs(Decimal(str(v["score"])) - Decimal(str(br["dimensions"][k]["score"]))) > 1
        for k, v in ar.get("dimensions", {}).items()
    )
