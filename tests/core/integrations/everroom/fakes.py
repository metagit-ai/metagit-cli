#!/usr/bin/env python
"""In-memory EverRoom client for campaign unit tests."""

from __future__ import annotations

from typing import Any, Optional

from metagit.core.integrations.everroom.errors import EverRoomError
from metagit.core.integrations.everroom.models import (
    EverRoomCreateResult,
    EverRoomDecision,
    EverRoomDocumentRef,
    EverRoomHealth,
    EverRoomKnowledgeItem,
    EverRoomOverview,
    EverRoomRoom,
    EverRoomRoomContext,
    EverRoomSource,
)
from tests.core.integrations.everroom.mock_gateway import ROOM_ID, ROOM_TITLE, terraform_fixture


class FakeEverRoomClient:
    """Protocol-compatible client that never performs HTTP."""

    def __init__(
        self,
        *,
        error: Optional[EverRoomError] = None,
        fixture: Optional[dict[str, Any]] = None,
        extra_sources: Optional[list[EverRoomSource]] = None,
    ) -> None:
        self.error = error
        self.method_errors: dict[str, EverRoomError] = {}
        self.fixture = fixture or terraform_fixture()
        self.extra_sources = extra_sources or []
        self.created: list[EverRoomRoom] = []
        self.upserts: list[dict[str, Any]] = []
        self.endpoint = "http://127.0.0.1:3210"

    def _raise(self, method: str = "") -> None:
        if method and method in self.method_errors:
            raise self.method_errors[method]
        if self.error is not None:
            raise self.error

    def health(self) -> EverRoomHealth:
        self._raise("health")
        return EverRoomHealth(status="ok", service="nxcore-gateway")

    def resolve_room(self, room_id: str) -> EverRoomRoom:
        self._raise("resolve_room")
        room = self.fixture["room"]
        if room_id not in {room["id"], *[item.id for item in self.created]}:
            from metagit.core.integrations.everroom.errors import EverRoomNotFoundError

            raise EverRoomNotFoundError(f"EverRoom Room not found: {room_id}")
        if room_id == room["id"]:
            return EverRoomRoom.model_validate(room)
        for item in self.created:
            if item.id == room_id:
                return item
        return EverRoomRoom(id=room_id, title=ROOM_TITLE)

    def create_room(self, *, title: str, description: str) -> EverRoomCreateResult:
        self._raise("create_room")
        room = EverRoomRoom(id=f"room-created-{len(self.created) + 1}", title=title, summary=description)
        self.created.append(room)
        return EverRoomCreateResult(room=room, created=True)

    def get_room_overview(self, room_id: str) -> EverRoomOverview:
        self._raise("get_room_overview")
        _ = room_id
        return EverRoomOverview(roomId=ROOM_ID, payload={"overview": self.fixture["context"]["overview"]})

    def get_room_context(self, room_id: str) -> EverRoomRoomContext:
        self._raise("get_room_context")
        _ = room_id
        return EverRoomRoomContext.model_validate(self.fixture["context"])

    def list_room_sources(self, room_id: str) -> list[EverRoomSource]:
        self._raise("list_room_sources")
        _ = room_id
        sources = [EverRoomSource.model_validate(item) for item in self.fixture["sources"]]
        for source in sources:
            source.identity_hints = [hint for hint in (source.original_name, source.title, source.id) if hint]
        return [*sources, *self.extra_sources]

    def list_room_documents(self, room_id: str) -> list[EverRoomDocumentRef]:
        self._raise("list_room_documents")
        _ = room_id
        return [EverRoomDocumentRef.model_validate(item) for item in self.fixture["documents"]]

    def list_room_decisions(self, room_id: str, *, limit: int = 20) -> list[EverRoomDecision]:
        self._raise("list_room_decisions")
        decisions = [EverRoomDecision.model_validate(item) for item in self.fixture["decisions"]]
        return [item for item in decisions if not item.room_id or item.room_id == room_id][:limit]

    def list_room_knowledge(self, room_id: str) -> list[EverRoomKnowledgeItem]:
        self._raise("list_room_knowledge")
        _ = room_id
        return [EverRoomKnowledgeItem(id="wiki-overview", title="Migration wiki", kind="wiki")]

    def upsert_generated_document(
        self,
        *,
        room_id: str,
        document_id: str,
        title: str,
        markdown: str,
    ) -> EverRoomDocumentRef:
        self._raise("upsert_generated_document")
        self.upserts.append(
            {
                "room_id": room_id,
                "document_id": document_id,
                "title": title,
                "markdown": markdown,
            },
        )
        return EverRoomDocumentRef(id=document_id, title=title, version=1, roomId=room_id, generated=True)
