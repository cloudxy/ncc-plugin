from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Login(Strict):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=1024)


class ScopeInput(Strict):
    name: str = Field(min_length=1, max_length=256)
    kind: Literal["author", "universe", "series", "book", "research", "branch"] = "book"
    parent_id: str | None = None
    base_id: str | None = None
    base_version: int | None = Field(default=None, ge=0)


class Operation(Strict):
    op: Literal["create", "update", "retire", "restore", "fact", "retract", "name", "adopt", "definition"]
    entity_id: str | None = None
    expected: str | None = None
    kind: str | None = Field(default=None, max_length=128)
    name: str | None = Field(default=None, max_length=512)
    data: dict[str, Any] | None = None
    unset: list[str] = Field(default_factory=list, max_length=100)
    text: str | None = Field(default=None, max_length=2_000_000)
    secret: bool | None = None
    reactivate: bool = False
    fact: dict[str, Any] | None = None
    fact_id: str | None = None
    definition: dict[str, Any] | None = None
    definition_id: str | None = None
    revision_id: str | None = None
    target_scope: str | None = None
    target_version: int | None = Field(default=None, ge=0)


class ChangeInput(Strict):
    title: str = Field(min_length=1, max_length=256)
    base_version: int = Field(ge=0)
    operations: list[Operation] = Field(min_length=1, max_length=500)


class MaintenanceInput(Strict):
    action: Literal["restore", "merge", "split", "branch_merge"]
    base_version: int = Field(ge=0)
    entity_id: str | None = None
    target_id: str | None = None
    revision_id: str | None = None
    branch_id: str | None = None
    name: str | None = Field(default=None, max_length=512)
    text: str = Field(default="", max_length=2_000_000)
    fields: list[str] = Field(default_factory=list, max_length=100)
    choices: dict[str, Literal["source", "target"]] = Field(default_factory=dict)


class EditChange(ChangeInput):
    draft_version: int = Field(ge=1)


class Query(Strict):
    q: str = Field(default="", max_length=256)
    kind: str | None = None
    as_of: int | None = Field(default=None, ge=0)
    role: Literal["author", "writer", "reader"] = "author"
    chapter_id: str | None = None
    offset: int = Field(default=0, ge=0, le=100_000)
    limit: int = Field(default=50, ge=1, le=200)
    include_deleted: bool = False
    filters: list[dict] = Field(default_factory=list, max_length=12)
    sort: str = Field(default="name", max_length=128)
    descending: bool = False


class StateQuery(Query):
    subject_id: str | None = None
    predicate: str | None = None
    calendar: str | None = None
    world_at: Decimal | None = None
    category: str | None = None


class CreationInput(Strict):
    objective: str = Field(min_length=1, max_length=12000)
    scheme: Literal["P1", "P2", "P3", "P4", "P5"] = "P1"
    mode: Literal["create", "assess"] = "create"
    content_scheme: Literal["P1", "P2", "P3", "P4"] | None = None
    selection_start: int | None = Field(default=None, ge=0)
    selection_end: int | None = Field(default=None, ge=1)
    entity_id: str | None = None
    kind: str = Field(default="chapter", max_length=128)
    name: str = Field(default="创作候选", min_length=1, max_length=512)
    delegation_id: str | None = None
    source_ids: list[str] = Field(default_factory=list, max_length=30)
    max_revisions: int = Field(default=2, ge=0, le=2)
    token_budget: int = Field(default=24000, ge=1000, le=100000)


class Intervention(Strict):
    action: Literal["pause", "cancel", "resume", "change_objective", "choose"]
    objective: str | None = Field(default=None, max_length=12000)
    candidate: int | None = Field(default=None, ge=0)


class AuthorDraft(Strict):
    version: int = Field(ge=0)
    entity_id: str | None = None
    baseline: str | None = None
    name: str = Field(default="", max_length=512)
    text: str = Field(default="", max_length=2_000_000)
    scheme: Literal["P1", "P2", "P3", "P4", "P5"] = "P1"


class Dimension(Strict):
    score: Decimal = Field(ge=0, le=5)
    evidence: list[str] = Field(min_length=1, max_length=8)
    reason: str = Field(min_length=1, max_length=2000)

    @field_validator("score")
    @classmethod
    def half_steps(cls, value):
        if value * 2 != int(value * 2):
            raise ValueError("分项分数必须是0.5的倍数")
        return value


class AssessmentReport(Strict):
    dimensions: dict[str, Dimension]
    hard: Literal["pass", "fail", "unknown"]
    observations: list[dict] = Field(default_factory=list, max_length=100)
    coverage: Literal["complete", "incomplete"]
    summary: str = Field(min_length=1, max_length=4000)
    suggestions: list[str] = Field(default_factory=list, max_length=10)


class FactInput(Strict):
    predicate: str = Field(min_length=1, max_length=128)
    category: Literal["fact", "relation", "name", "belief", "reveal", "plan"] = "fact"
    object_id: str | None = None
    value: dict = Field(default_factory=dict)
    calendar: str | None = None
    world_from: Decimal | None = None
    world_to: Decimal | None = None
    chapter_id: str | None = None
    supersedes: str | None = None
    secret: bool = False
    source: dict


class DefinitionInput(Strict):
    key: str = Field(pattern=r"^[\w:.-]{1,128}$")
    version: int = Field(ge=1)
    spec: dict


class MemberInput(Strict):
    user_id: str
    actions: list[Literal["read", "edit", "adopt", "assess", "export", "secret", "admin", "operate"]]


class UserInput(Strict):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=12, max_length=1024)


class DelegationInput(Strict):
    target_ids: list[str] = Field(min_length=1, max_length=100)
    schemes: list[Literal["P1", "P2", "P3", "P4", "P5"]] = Field(min_length=1, max_length=5)
    hours: int = Field(default=24, ge=1, le=168)
    count: int = Field(default=3, ge=1, le=100)
    mode: Literal["calibrated", "author_trial"] = "calibrated"
    note: str = Field(default="", max_length=4000)


class CalibrationSample(Strict):
    source_group: str = Field(min_length=1, max_length=128)
    split: Literal["development", "holdout"]
    assessment_ids: list[str] = Field(min_length=1, max_length=10)
    planted_severity: Literal["none", "critical", "major"] = "none"


class CalibrationPreference(Strict):
    left: str
    right: str
    choice: Literal["left", "right"]


class CalibrationInput(Strict):
    scheme: Literal["P1", "P2", "P3", "P4", "P5"]
    evaluator: str = Field(min_length=1, max_length=128)
    samples: list[CalibrationSample] = Field(min_length=1, max_length=1000)
    preferences: list[CalibrationPreference] = Field(default_factory=list, max_length=1000)
    activate: bool = False
    note: str = Field(min_length=1, max_length=4000)
