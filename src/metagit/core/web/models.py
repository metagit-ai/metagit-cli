#!/usr/bin/env python
"""Pydantic models for metagit web API."""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ConfigOpKind(str, Enum):
    ENABLE = "enable"
    DISABLE = "disable"
    SET = "set"


class ConfigOperation(BaseModel):
    op: ConfigOpKind
    path: str
    value: Any | None = None


class ConfigPatchRequest(BaseModel):
    save: bool = False
    operations: list[ConfigOperation] = Field(default_factory=list)


class SchemaFieldNode(BaseModel):
    path: str
    key: str
    type: str
    description: str | None = None
    required: bool = False
    enabled: bool = False
    editable: bool = True
    sensitive: bool = False
    default_value: Any | None = None
    value: Any | None = None
    enum_options: list[str] = Field(default_factory=list)
    children: list["SchemaFieldNode"] = Field(default_factory=list)


class ConfigTreeResponse(BaseModel):
    ok: bool
    target: Literal["metagit", "appconfig"]
    config_path: str
    tree: SchemaFieldNode
    validation_errors: list[dict[str, str]] = Field(default_factory=list)
    saved: bool = False


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
