#!/usr/bin/env python
"""Provider-agnostic campaign context packet and EverRoom settings."""

from __future__ import annotations

from typing import Any, Literal, Optional, Protocol

from pydantic import BaseModel, ConfigDict, Field

from metagit.core.integrations.everroom.errors import EverRoomStatus

CONTEXT_SCHEMA_VERSION = "1"
DEFAULT_CONTEXT_INCLUDES: tuple[str, ...] = (
    "summary",
    "repositories",
    "relationships",
    "decisions",
    "open_questions",
    "documents",
    "sources",
)
CONTEXT_INCLUDE_CHOICES: tuple[str, ...] = (
    "summary",
    "repositories",
    "relationships",
    "git_state",
    "instructions",
    "decisions",
    "open_questions",
    "documents",
    "sources",
    "knowledge",
)

EverRoomConnectionStatus = EverRoomStatus


class ContextLimits(BaseModel):
    """Caps that keep campaign context packets agent-sized."""

    model_config = ConfigDict(extra="forbid")

    repositories: int = 40
    relationships: int = 40
    components: int = 40
    decisions: int = 8
    open_questions: int = 8
    documents: int = 8
    sources: int = 20
    knowledge: int = 8
    instructions_chars: int = 800


class ProvenanceEntry(BaseModel):
    """Identifies which system authored a context section."""

    model_config = ConfigDict(extra="forbid")

    source: Literal["metagit", "everroom"]
    section: str


class TechnicalRepository(BaseModel):
    """Campaign repository as known to MetaGit."""

    model_config = ConfigDict(extra="forbid")

    source: Literal["metagit"] = "metagit"
    project: str
    repo: str
    role: Optional[str] = None
    status: str = "pending"
    url: Optional[str] = None
    identity: Optional[str] = None
    components: list[str] = Field(default_factory=list)
    git: dict[str, Any] = Field(default_factory=dict)
    everroom_source: Optional[str] = None
    mapping: Literal["mapped", "unmapped"] = "unmapped"


class TechnicalRelationship(BaseModel):
    """A graph edge whose endpoints participate in the campaign."""

    model_config = ConfigDict(extra="forbid")

    source: Literal["metagit"] = "metagit"
    relationship_id: Optional[str] = None
    type: str
    from_ref: str
    to_ref: str
    label: Optional[str] = None


class MetagitTechnicalContext(BaseModel):
    """Technical reality owned by MetaGit."""

    model_config = ConfigDict(extra="forbid")

    source: Literal["metagit"] = "metagit"
    repository_count: int = 0
    component_count: int = 0
    relationship_count: int = 0
    dirty_repository_count: int = 0
    repositories: list[TechnicalRepository] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)
    relationships: list[TechnicalRelationship] = Field(default_factory=list)
    instructions: list[str] = Field(default_factory=list)


class EverRoomContextSlice(BaseModel):
    """Contextual reality owned by EverRoom, referenced rather than mirrored."""

    model_config = ConfigDict(extra="forbid")

    source: Literal["everroom"] = "everroom"
    status: EverRoomConnectionStatus = "NOT_CONFIGURED"
    warning: Optional[str] = None
    endpoint: Optional[str] = None
    room_id: Optional[str] = None
    room_title: Optional[str] = None
    overview: Optional[str] = None
    room_status: Optional[str] = None
    source_count: int = 0
    decision_count: int = 0
    open_question_count: int = 0
    document_count: int = 0
    sources: list[dict[str, Any]] = Field(default_factory=list)
    decisions: list[dict[str, Any]] = Field(default_factory=list)
    open_questions: list[dict[str, Any]] = Field(default_factory=list)
    documents: list[dict[str, Any]] = Field(default_factory=list)
    knowledge: list[dict[str, Any]] = Field(default_factory=list)


class CampaignEnvelope(BaseModel):
    """Campaign identity as owned by MetaGit."""

    model_config = ConfigDict(extra="forbid")

    source: Literal["metagit"] = "metagit"
    id: str
    title: str
    objective: Optional[str] = None
    status: str
    reference_impl: Optional[str] = None


class CampaignContextResult(BaseModel):
    """Versioned agent-facing campaign context packet."""

    model_config = ConfigDict(extra="forbid")

    context_schema_version: str = CONTEXT_SCHEMA_VERSION
    campaign: CampaignEnvelope
    metagit: MetagitTechnicalContext
    everroom: EverRoomContextSlice
    provenance: list[ProvenanceEntry] = Field(default_factory=list)
    includes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ProviderHealth(BaseModel):
    """Health snapshot for a campaign context provider."""

    model_config = ConfigDict(extra="forbid")

    provider_type: str
    status: EverRoomConnectionStatus
    message: Optional[str] = None
    endpoint: Optional[str] = None
    room_id: Optional[str] = None
    room_title: Optional[str] = None


class ProviderContext(BaseModel):
    """Resolved slice from one context provider."""

    model_config = ConfigDict(extra="forbid")

    provider_type: str
    status: EverRoomConnectionStatus
    warning: Optional[str] = None
    slice: EverRoomContextSlice


class ContextSummary(BaseModel):
    """Compact provider summary used by status output."""

    model_config = ConfigDict(extra="forbid")

    provider_type: str
    status: EverRoomConnectionStatus
    room_id: Optional[str] = None
    room_title: Optional[str] = None
    source_count: int = 0
    decision_count: int = 0
    open_question_count: int = 0
    document_count: int = 0
    message: Optional[str] = None


class CampaignContextProvider(Protocol):
    """Keep campaign orchestration independent from a specific context system."""

    @property
    def provider_type(self) -> str: ...

    def health(self) -> ProviderHealth: ...

    def resolve(self, *, include: set[str], limits: ContextLimits) -> ProviderContext: ...

    def summarize(self) -> ContextSummary: ...
