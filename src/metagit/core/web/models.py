#!/usr/bin/env python
"""Pydantic models for metagit web API."""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ConfigOpKind(str, Enum):
    ENABLE = "enable"
    DISABLE = "disable"
    SET = "set"
    APPEND = "append"
    REMOVE = "remove"


class ConfigOperation(BaseModel):
    op: ConfigOpKind
    path: str
    value: Any | None = None


class ConfigPatchRequest(BaseModel):
    save: bool = False
    auto_format: bool = True
    operations: list[ConfigOperation] = Field(default_factory=list)


class SchemaFieldNode(BaseModel):
    path: str
    key: str
    type: str
    type_label: str | None = None
    description: str | None = None
    required: bool = False
    enabled: bool = False
    editable: bool = True
    sensitive: bool = False
    default_value: Any | None = None
    value: Any | None = None
    enum_options: list[str] = Field(default_factory=list)
    item_count: int | None = None
    can_append: bool = False
    children: list["SchemaFieldNode"] = Field(default_factory=list)


class ConfigTreeResponse(BaseModel):
    ok: bool
    target: Literal["metagit", "appconfig"]
    config_path: str
    tree: SchemaFieldNode
    validation_errors: list[dict[str, str]] = Field(default_factory=list)
    saved: bool = False


class ConfigPreviewRequest(BaseModel):
    style: Literal["normalized", "minimal", "disk"] = "normalized"
    operations: list[ConfigOperation] = Field(default_factory=list)


class ConfigPreviewResponse(BaseModel):
    ok: bool
    target: Literal["metagit", "appconfig"]
    config_path: str
    style: Literal["normalized", "minimal", "disk"]
    yaml: str
    draft: bool = False
    validation_errors: list[dict[str, str]] = Field(default_factory=list)


class SyncJobRequest(BaseModel):
    repos: list[str] | None = None
    mode: Literal["fetch", "pull", "clone"] = "fetch"
    dry_run: bool = False
    allow_mutation: bool = True
    max_parallel: int = 4


class SyncJobStatus(BaseModel):
    job_id: str
    state: Literal["pending", "running", "completed", "failed"]
    summary: dict[str, Any] = Field(default_factory=dict)
    results: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class ObjectiveUpsertRequest(BaseModel):
    """Objective fields accepted on POST `/v3/ops/objectives` (timestamps from server)."""

    id: str
    title: str
    status: Literal["pending", "in_progress", "done", "cancelled"] = "pending"
    repos: list[str] = Field(default_factory=list)
    acceptance: str | None = None
    human_notes: str | None = None
    agent_notes: str | None = None


class ObjectiveStatusPatchRequest(BaseModel):
    """Minimal patch for PATCH `/v3/ops/objectives/{id}`."""

    status: Literal["done", "cancelled"]


class ApprovalResolveRequest(BaseModel):
    """Body for POST `/v3/ops/approvals/{id}/resolve`."""

    decision: Literal["approved", "denied"]
    note: str | None = None
