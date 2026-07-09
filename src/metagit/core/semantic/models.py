#!/usr/bin/env python
"""Pydantic models for Semantic Repository Knowledge Graph (RFC-0010)."""

from __future__ import annotations

import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

_ID_PATTERN = re.compile(r"^[\w.-]+$")

SemanticEventType = Literal["ConceptDeclared", "ConceptConflictHint", "ConceptIngested"]
ConceptOwnershipSource = Literal["manual", "ingest", "seed", "gitnexus"]


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


class Concept(BaseModel):
    """Named semantic concept that can be owned by repository paths."""

    concept_id: str
    name: str
    description: Optional[str] = None
    aliases: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str

    @field_validator("concept_id")
    @classmethod
    def validate_concept_id(cls, value: str) -> str:
        return _validate_id(value, label="concept_id")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _validate_nonempty(value, label="name")

    @field_validator("aliases")
    @classmethod
    def validate_aliases(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


class ConceptOwnership(BaseModel):
    """Repository path ownership declaration for a semantic concept."""

    ownership_id: str
    concept_id: str
    repository: str
    patterns: list[str] = Field(min_length=1)
    symbol_hints: list[str] = Field(default_factory=list)
    source: ConceptOwnershipSource = "manual"
    created_at: str
    updated_at: str

    @field_validator("ownership_id", "concept_id")
    @classmethod
    def validate_ids(cls, value: str) -> str:
        return _validate_id(value, label="id")

    @field_validator("repository")
    @classmethod
    def validate_repository(cls, value: str) -> str:
        stripped = value.strip()
        parts = stripped.split("/")
        if len(parts) != 2 or not all(part.strip() for part in parts):
            raise ValueError("repository must be project/repo")
        return stripped

    @field_validator("patterns")
    @classmethod
    def validate_patterns(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("at least one ownership pattern is required")
        return cleaned

    @field_validator("symbol_hints")
    @classmethod
    def validate_symbol_hints(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


class ConceptConflictHint(BaseModel):
    """Advisory hint that multiple agents may be touching one concept."""

    concept_id: str
    concept_name: str
    repository: str
    overlapping_patterns: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    agent_ids: list[str] = Field(default_factory=list)


class ConceptQueryResult(BaseModel):
    """Result envelope for concept lookup."""

    ok: bool = True
    concept: Optional[Concept] = None
    ownerships: list[ConceptOwnership] = Field(default_factory=list)


class ConceptDeclareResult(BaseModel):
    """Result envelope for a concept ownership declaration."""

    ok: bool = True
    concept: Concept
    ownership: ConceptOwnership


class ConceptOwnersResult(BaseModel):
    """Result envelope for path-to-concept owner lookup."""

    ok: bool = True
    path: str
    repository: str
    concepts: list[Concept] = Field(default_factory=list)
    ownerships: list[ConceptOwnership] = Field(default_factory=list)


class ConceptConflictsResult(BaseModel):
    """Result envelope for advisory concept conflict hints."""

    ok: bool = True
    repository: str
    hints: list[ConceptConflictHint] = Field(default_factory=list)


class SemanticSeedResult(BaseModel):
    """Result envelope for static semantic catalog seeding."""

    ok: bool = True
    concepts_added: int = 0
    ownerships_added: int = 0


class SemanticIngestOwnershipHint(BaseModel):
    """Deterministic ownership hint loaded from ingest-hints.json."""

    concept: str
    repository: str
    patterns: list[str] = Field(min_length=1)

    @field_validator("concept", "repository")
    @classmethod
    def validate_required_strings(cls, value: str) -> str:
        return _validate_nonempty(value, label="hint field")

    @field_validator("patterns")
    @classmethod
    def validate_hint_patterns(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("at least one ownership pattern is required")
        return cleaned


class SemanticIngestHints(BaseModel):
    """Root ingest hints document."""

    ownerships: list[SemanticIngestOwnershipHint] = Field(default_factory=list)


class SemanticIngestResult(BaseModel):
    """Result envelope for deterministic semantic ingest."""

    ok: bool = True
    added: int = 0
    skipped: int = 0
    concepts_added: int = 0
    reason: Optional[str] = None


class SemanticEvent(BaseModel):
    """Typed semantic graph lifecycle event."""

    event_id: str
    type: SemanticEventType
    at: str
    payload: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "Concept",
    "ConceptConflictHint",
    "ConceptConflictsResult",
    "ConceptDeclareResult",
    "ConceptOwnersResult",
    "ConceptOwnership",
    "ConceptOwnershipSource",
    "ConceptQueryResult",
    "SemanticIngestHints",
    "SemanticIngestOwnershipHint",
    "SemanticIngestResult",
    "SemanticEvent",
    "SemanticEventType",
    "SemanticSeedResult",
]
