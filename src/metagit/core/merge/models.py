#!/usr/bin/env python
"""Pydantic models for the Merge Orchestrator (RFC-0011)."""

from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

_ID_PATTERN = re.compile(r"^[\w.-]+$")

MergeStatus = Literal["queued", "running", "succeeded", "failed", "conflict", "validation_failed"]


def _validate_id(value: str, *, label: str) -> str:
    stripped = value.strip()
    if not stripped or not _ID_PATTERN.match(stripped):
        raise ValueError(f"{label} must match slug pattern [alphanumeric, underscore, dot, hyphen]")
    return stripped


def _validate_nonempty(value: str, *, label: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{label} is required")
    return stripped


def _validate_repository(value: str) -> str:
    stripped = value.strip()
    parts = stripped.split("/")
    if len(parts) != 2 or not all(part.strip() for part in parts):
        raise ValueError("repository must be project/repo")
    return stripped


class MergeConflict(BaseModel):
    """Conflict details captured for a merge request."""

    files: list[str] = Field(min_length=1)
    message: str
    dispatch_hint: Optional[str] = None

    @field_validator("files")
    @classmethod
    def validate_files(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("at least one conflict file is required")
        return cleaned

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        return _validate_nonempty(value, label="message")

    @field_validator("dispatch_hint")
    @classmethod
    def validate_dispatch_hint(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class MergeValidationCommand(BaseModel):
    """Result for one validation command executed around a merge."""

    cmd: str
    exit_code: int
    stdout: str = ""
    stderr: str = ""

    @field_validator("cmd")
    @classmethod
    def validate_cmd(cls, value: str) -> str:
        return _validate_nonempty(value, label="cmd")


class MergeValidation(BaseModel):
    """Validation summary for a merge request."""

    ok: bool
    commands: list[MergeValidationCommand] = Field(default_factory=list)


class MergeRequest(BaseModel):
    """File-backed merge request document."""

    merge_id: str
    repository: str
    source_branch: str
    target_branch: str
    status: MergeStatus = "queued"
    node_id: Optional[str] = None
    agent_id: Optional[str] = None
    conflict: Optional[MergeConflict] = None
    validation: Optional[MergeValidation] = None
    acl_commands: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str

    @field_validator("merge_id")
    @classmethod
    def validate_merge_id(cls, value: str) -> str:
        return _validate_id(value, label="merge_id")

    @field_validator("repository")
    @classmethod
    def validate_repository(cls, value: str) -> str:
        return _validate_repository(value)

    @field_validator("source_branch", "target_branch", "created_at", "updated_at")
    @classmethod
    def validate_required_strings(cls, value: str) -> str:
        return _validate_nonempty(value, label="required field")

    @field_validator("node_id", "agent_id")
    @classmethod
    def validate_optional_ids(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return _validate_id(value, label="id")

    @field_validator("acl_commands")
    @classmethod
    def validate_acl_commands(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


class MergeQueueEntry(BaseModel):
    """Lightweight listing row for ``queue.json``."""

    merge_id: str
    repository: str
    status: MergeStatus
    updated_at: str

    @field_validator("merge_id")
    @classmethod
    def validate_merge_id(cls, value: str) -> str:
        return _validate_id(value, label="merge_id")

    @field_validator("repository")
    @classmethod
    def validate_repository(cls, value: str) -> str:
        return _validate_repository(value)

    @field_validator("updated_at")
    @classmethod
    def validate_updated_at(cls, value: str) -> str:
        return _validate_nonempty(value, label="updated_at")


class MergeQueue(BaseModel):
    """Queue index for merge request documents."""

    merges: list[MergeQueueEntry] = Field(default_factory=list)


__all__ = [
    "MergeConflict",
    "MergeQueue",
    "MergeQueueEntry",
    "MergeRequest",
    "MergeStatus",
    "MergeValidation",
    "MergeValidationCommand",
]
