#!/usr/bin/env python
"""Pydantic models for Metagit Atlas (RFC-0014)."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from metagit.core.atlas.ids import validate_entity_id, validate_evidence_id

Lifecycle = Literal["proposed", "active", "deprecated", "retired"]
Classification = Literal["public", "internal", "confidential", "restricted"]
ProvenanceSource = Literal["curated", "generated", "imported"]
FreshnessState = Literal["fresh", "stale", "unknown", "missing"]


class Provenance(BaseModel):
    """Provenance metadata for an Atlas entity."""

    source: ProvenanceSource
    updatedAt: Optional[str] = None


class EvidenceItem(BaseModel):
    """Generated observation linking an entity to source evidence."""

    id: str
    kind: str
    locator: str
    revision: str
    extractor: str
    observedAt: str
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return validate_evidence_id(value)


class EntityMetadata(BaseModel):
    """Shared metadata for Atlas entity envelopes."""

    id: str
    name: str
    lifecycle: Lifecycle
    classification: Classification
    provenance: Provenance
    owners: list[str] = Field(default_factory=list)
    labels: dict[str, str] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return validate_entity_id(value)


class EntityEnvelope(BaseModel):
    """Kubernetes-style envelope for a curated or generated Atlas entity."""

    apiVersion: str
    kind: str
    metadata: EntityMetadata
    spec: dict[str, Any] = Field(default_factory=dict)


class AtlasConfig(BaseModel):
    """Top-level `.atlas/atlas.yaml` configuration."""

    apiVersion: str = "atlas.metagit.dev/v1alpha1"
    repository: str
    formatVersion: str
    commitGenerated: bool = True
    sources: Optional[dict[str, FreshnessState]] = None


class AtlasStatusResult(BaseModel):
    """Result envelope for Atlas status operations."""

    ok: bool = True
    repository: str | None = None
    initialized: bool = False
    generated: bool = False
    freshness: dict[str, FreshnessState] = Field(default_factory=dict)
    invalidation_reason: str | None = None


class AtlasValidateResult(BaseModel):
    """Result envelope for Atlas validation operations."""

    ok: bool = True
    issues: list[dict[str, Any]] = Field(default_factory=list)


class AtlasQueryResult(BaseModel):
    """Result envelope for Atlas query operations."""

    ok: bool = True
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    entities: list[dict[str, Any]] = Field(default_factory=list)
    entity: dict[str, Any] | None = None
