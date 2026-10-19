"""Authenticated same-origin FastAPI application. Schema changes are an explicit CLI step."""

from pydantic import Field

from ncc_data.domain.contracts import (
    Query,
    Strict,
)


class ImportInput(Strict):
    attachment_id: str
    mapping: dict = Field(default_factory=dict)


class ImportApply(Strict):
    acknowledge_unmapped: bool = False


class ExportInput(Strict):
    format: str = "json"
    as_of: int | None = None


class FeedbackInput(Strict):
    choice: str
    note: str = Field(default="", max_length=4000)


class ViewInput(Strict):
    name: str
    query: Query


class TokenInput(Strict):
    actions: list[str]
    hours: int = Field(default=24, ge=1, le=168)


class WorkspaceCommit(Strict):
    format: str
    base_version: int = Field(ge=0)
    files: list[dict] = Field(min_length=1, max_length=200)
    request_id: str = Field(min_length=1, max_length=128)
    title: str = Field(default="CLI受控回写", max_length=256)
