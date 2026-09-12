#!/usr/bin/env python
"""Narrow Pydantic models for EverRoom Gateway payloads used by campaigns."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class EverRoomHealth(BaseModel):
    """Liveness or readiness payload from `/v1/health/*`."""

    model_config = ConfigDict(extra="ignore")

    status: str = "ok"
    service: str = "nxcore-gateway"
    version: str = ""
    pid: Optional[int] = None
    uptime_seconds: Optional[float] = Field(default=None, alias="uptimeSeconds")


class EverRoomRoom(BaseModel):
    """A Context Room snapshot item or knowledge-room DTO."""

    model_config = ConfigDict(extra="ignore")

    id: str
    title: str = ""
    kind: Optional[str] = None
    origin: Optional[str] = None
    summary: Optional[str] = None
    data: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = Field(default=None, alias="createdAt")
    updated_at: Optional[str] = Field(default=None, alias="updatedAt")


class EverRoomCreateResult(BaseModel):
    """Result of `POST /v1/context-rooms`."""

    model_config = ConfigDict(extra="ignore")

    room: EverRoomRoom
    created: bool = True


class EverRoomSource(BaseModel):
    """A Room-linked source or uploaded file, referenced rather than mirrored."""

    model_config = ConfigDict(extra="ignore")

    id: str
    title: Optional[str] = None
    original_name: Optional[str] = Field(default=None, alias="originalName")
    status: Optional[str] = None
    source_kind: Optional[str] = Field(default=None, alias="sourceKind")
    source_id: Optional[str] = Field(default=None, alias="sourceId")
    bytes: Optional[int] = None
    uploaded_at: Optional[str] = Field(default=None, alias="uploadedAt")
    identity_hints: list[str] = Field(default_factory=list)


class EverRoomDocumentRef(BaseModel):
    """A Room document listed without dumping its body."""

    model_config = ConfigDict(extra="ignore")

    id: str
    title: str = ""
    version: int = 0
    room_id: Optional[str] = Field(default=None, alias="roomId")
    updated_at: Optional[str] = Field(default=None, alias="updatedAt")
    generated: bool = False


class EverRoomDecision(BaseModel):
    """A knowledge route decision or Room overview conclusion."""

    model_config = ConfigDict(extra="ignore")

    decision_id: str = Field(default="", alias="decisionId")
    title: str = ""
    reason: Optional[str] = None
    status: Optional[str] = None
    room_id: Optional[str] = Field(default=None, alias="roomId")
    room_title: Optional[str] = Field(default=None, alias="roomTitle")
    decided_by: Optional[str] = Field(default=None, alias="decidedBy")
    confidence: Optional[float] = None
    created_at: Optional[str] = Field(default=None, alias="createdAt")
    evidence: Optional[str] = None


class EverRoomOpenQuestion(BaseModel):
    """An unresolved next step or action item from Room-scoped context."""

    model_config = ConfigDict(extra="ignore")

    title: str
    owner: Optional[str] = None
    due_date: Optional[str] = Field(default=None, alias="dueDate")
    status: Optional[str] = None
    source_title: Optional[str] = Field(default=None, alias="sourceTitle")


class EverRoomKnowledgeItem(BaseModel):
    """A wiki page or material reference inside a Room."""

    model_config = ConfigDict(extra="ignore")

    id: str
    title: str = ""
    kind: str = "wiki"
    path: Optional[str] = None
    version: Optional[int] = None
    updated_at: Optional[str] = Field(default=None, alias="updatedAt")


class EverRoomRoomContext(BaseModel):
    """Room-scoped context from `GET /v1/knowledge/rooms/:id/context`."""

    model_config = ConfigDict(extra="ignore")

    room_id: str = Field(default="", alias="roomId")
    generated_at: Optional[str] = Field(default=None, alias="generatedAt")
    overview: str = ""
    status: str = ""
    next_steps: list[str] = Field(default_factory=list, alias="nextSteps")
    source_documents: list[dict[str, Any]] = Field(default_factory=list, alias="sourceDocuments")
    entities: list[dict[str, Any]] = Field(default_factory=list)
    action_items: list[dict[str, Any]] = Field(default_factory=list, alias="actionItems")
    meetings: list[dict[str, Any]] = Field(default_factory=list)


class EverRoomOverview(BaseModel):
    """Best-effort Room overview payload from `/v1/context-rooms/:roomId/overview`."""

    model_config = ConfigDict(extra="ignore")

    room_id: Optional[str] = Field(default=None, alias="roomId")
    payload: dict[str, Any] = Field(default_factory=dict)
