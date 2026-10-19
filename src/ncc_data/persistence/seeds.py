from sqlalchemy import select

from ncc_data.domain.definitions import CORE_KINDS, PROPERTIES, RELATIONS, SYSTEM_SCOPE
from ncc_data.persistence.models import Definition, Scope
from ncc_shared.quality.policy import POLICY


async def seed(db):
    if not await db.get(Scope, SYSTEM_SCOPE):
        db.add(Scope(id=SYSTEM_SCOPE, name="NCC系统定义", kind="system", config={}, version=0))
        await db.flush()
    known = set((await db.scalars(select(Definition.key).where(Definition.scope_id == SYSTEM_SCOPE))).all())
    kinds = [(key, label, "通用") for key, label in CORE_KINDS.items()]
    kinds += [(label, label, domain) for domain, labels in POLICY["domains"].items() for label in labels]
    for key, label, domain in kinds:
        if key not in known:
            db.add(
                Definition(
                    scope_id=SYSTEM_SCOPE,
                    key=key,
                    version=1,
                    spec={"label": label, "domain": domain, "properties": PROPERTIES, "required": []},
                )
            )
            known.add(key)
    for key, value in RELATIONS.items():
        key = "rel:" + key
        if key not in known:
            db.add(Definition(scope_id=SYSTEM_SCOPE, key=key, version=1, spec={**value, "relation": True}))
