"""Human-labelled holdout activation. Never grants trust from a model's self-confidence."""

from decimal import Decimal

from sqlalchemy import select

from .errors import require
from .models import Assessment, Audit, Calibration
from .policy import POLICY_HASH
from .security import authorize


class CalibrationMixin:
    async def calibrations(self, scope_id):
        await authorize(self.db, self.actor, scope_id, "admin")
        await authorize(self.db, self.actor, scope_id, "secret")
        rows = (
            await self.db.scalars(
                select(Calibration)
                .where(Calibration.scope_id == scope_id)
                .order_by(Calibration.created_at.desc())
                .limit(100)
            )
        ).all()
        return [
            {
                "id": r.id,
                "scheme": r.scheme,
                "evaluator": r.evaluator,
                "policy_hash": r.policy_hash,
                "active": r.active,
                "report": r.report,
            }
            for r in rows
        ]

    async def calibrate(self, scope_id, value):
        scope, _ = await authorize(self.db, self.actor, scope_id, "admin", lock=True)
        require(scope.owner_id == self.actor.id, "owner_only", "校准与启用须由作品所有者确认", 403)
        ids = {item for sample in value.samples for item in sample.assessment_ids}
        ids |= {item for pair in value.preferences for item in (pair.left, pair.right)}
        rows = (
            await self.db.scalars(
                select(Assessment).where(Assessment.id.in_(ids), Assessment.scope_id == scope_id)
            )
        ).all()
        found = {r.id: r for r in rows}
        require(
            set(found) == ids
            and all(
                r.policy_hash == POLICY_HASH
                and r.scheme == value.scheme
                and r.evaluator == value.evaluator
                and r.score is not None
                for r in rows
            ),
            "calibration_binding",
            "样本需绑定本范围、当前策略、同一方案与评价器的有效评分",
        )
        train = {s.source_group for s in value.samples if s.split == "development"}
        holdout = [s for s in value.samples if s.split == "holdout"]
        held_groups = {s.source_group for s in holdout}
        require(not train & held_groups, "calibration_leakage", "同源样本不能跨开发集和留出集")
        content_groups = {}
        deltas, defects, false_passes = [], 0, 0
        for sample in value.samples:
            require(
                len(sample.assessment_ids) == len(set(sample.assessment_ids)),
                "calibration_duplicates",
                "重复运行必须使用不同评估记录",
            )
            reports = [found[i] for i in sample.assessment_ids]
            hashes = {r.content_hash for r in reports}
            require(len(hashes) == 1, "calibration_content", "重复稳定性样本必须是同一内容修订")
            content_hash = next(iter(hashes))
            require(
                content_hash not in content_groups,
                "calibration_duplicates",
                "同一文本的重复运行应归入一条样本，不能重复计数",
            )
            content_groups[content_hash] = sample.source_group, sample.split
            if sample.split != "holdout":
                continue
            if len(reports) >= 3:
                scores = [r.score for r in reports]
                deltas.append(max(scores) - min(scores))
            if sample.planted_severity in {"critical", "major"}:
                defects += 1
                false_passes += any(r.verdict == "qualified" for r in reports)
        agreement, pairs = 0, 0
        seen_pairs = set()
        for pair in value.preferences:
            left, right = found[pair.left], found[pair.right]
            key = tuple(sorted((left.content_hash, right.content_hash)))
            require(
                left.content_hash != right.content_hash and key not in seen_pairs,
                "calibration_duplicates",
                "成对偏好不能比较同稿或重复计数",
            )
            seen_pairs.add(key)
            require(
                left.content_hash in content_groups and right.content_hash in content_groups,
                "calibration_preference",
                "偏好比较需来自已登记样本",
            )
            require(
                content_groups[left.content_hash][1] == content_groups[right.content_hash][1] == "holdout",
                "calibration_preference",
                "偏好指标只能使用留出样本",
            )
            pairs += 1
            preferred = left if pair.choice == "left" else right
            other = right if pair.choice == "left" else left
            agreement += preferred.score > other.score
        p90 = sorted(deltas)[max(0, (len(deltas) * 9 + 9) // 10 - 1)] if deltas else None
        ratio = Decimal(agreement) / pairs if pairs else Decimal(0)
        enough = len(held_groups) >= 20 and len(deltas) >= 20 and defects >= 10 and pairs >= 20
        passed = enough and ratio >= Decimal(".8") and p90 <= 5 and false_passes == 0
        active = value.activate and passed
        report = {
            "source": "owner-labelled-holdout",
            "samples": [s.model_dump() for s in value.samples],
            "preferences": [p.model_dump() for p in value.preferences],
            "note": value.note,
            "metrics": {
                "holdout_groups": len(held_groups),
                "repeat_sets": len(deltas),
                "preference_pairs": pairs,
                "preference_agreement": str(ratio),
                "repeat_score_delta_p90": str(p90) if p90 is not None else None,
                "planted_defect_samples": defects,
                "false_passes": false_passes,
            },
            "sample_sufficient": enough,
            "passed": passed,
            "limits": "有限留出证据；不证明未知硬伤零漏检。评价器和策略变化需重新校准。",
        }
        if active:
            previous = (
                await self.db.scalars(
                    select(Calibration).where(
                        Calibration.scope_id == scope_id,
                        Calibration.scheme == value.scheme,
                        Calibration.evaluator == value.evaluator,
                    )
                )
            ).all()
            for row in previous:
                row.active = False
        row = Calibration(
            scope_id=scope_id,
            policy_hash=POLICY_HASH,
            evaluator=value.evaluator,
            scheme=value.scheme,
            report=report,
            active=active,
        )
        self.db.add(row)
        await self.db.flush()
        self.db.add(
            Audit(
                scope_id=scope_id,
                actor_id=self.actor.id,
                action="calibration.record",
                version=scope.version,
                detail={"calibration_id": row.id, "active": active, "passed": passed},
            )
        )
        return {"id": row.id, "active": active, "report": report}
