#!/usr/bin/env python
"""EverRoom implementation of the campaign context provider protocol."""

from __future__ import annotations

from typing import Any, Optional

from metagit.core.campaign.context_models import (
    ContextLimits,
    ContextSummary,
    EverRoomContextSlice,
    ProviderContext,
    ProviderHealth,
)
from metagit.core.campaign.models import CampaignContextProviderConfig, CampaignDocument
from metagit.core.integrations.everroom.client import EverRoomClient
from metagit.core.integrations.everroom.errors import (
    EverRoomAuthError,
    EverRoomError,
    EverRoomInvalidResponseError,
    EverRoomNotFoundError,
    EverRoomUnavailableError,
)
from metagit.core.integrations.everroom.models import EverRoomOpenQuestion, EverRoomRoomContext
from metagit.core.integrations.everroom.source_identity import identity_haystack


class EverRoomCampaignContextProvider:
    """Assemble Room-scoped EverRoom context without mirroring the Room database."""

    def __init__(
        self,
        *,
        campaign: CampaignDocument,
        config: CampaignContextProviderConfig,
        client: EverRoomClient,
    ) -> None:
        self._campaign = campaign
        self._config = config
        self._client = client

    @property
    def provider_type(self) -> str:
        return "everroom"

    def health(self) -> ProviderHealth:
        room_id = self._config.room_id
        if not room_id:
            return ProviderHealth(
                provider_type=self.provider_type,
                status="NOT_CONFIGURED",
                message="No EverRoom Room is associated with this campaign.",
                endpoint=self._config.endpoint,
            )
        try:
            self._client.health()
            room = self._client.resolve_room(room_id)
        except EverRoomError as exc:
            return ProviderHealth(
                provider_type=self.provider_type,
                status=exc.status,
                message=exc.message,
                endpoint=self._config.endpoint,
                room_id=room_id,
            )
        return ProviderHealth(
            provider_type=self.provider_type,
            status="AVAILABLE",
            message="EverRoom Gateway is connected.",
            endpoint=self._config.endpoint,
            room_id=room.id,
            room_title=room.title or None,
        )

    def summarize(self) -> ContextSummary:
        resolved = self.resolve(
            include={"summary", "decisions", "open_questions", "documents", "sources"}, limits=ContextLimits()
        )
        slice_ = resolved.slice
        return ContextSummary(
            provider_type=self.provider_type,
            status=resolved.status,
            room_id=slice_.room_id,
            room_title=slice_.room_title,
            source_count=slice_.source_count,
            decision_count=slice_.decision_count,
            open_question_count=slice_.open_question_count,
            document_count=slice_.document_count,
            message=resolved.warning,
        )

    def resolve(self, *, include: set[str], limits: ContextLimits) -> ProviderContext:
        room_id = self._config.room_id
        if not room_id:
            slice_ = EverRoomContextSlice(status="NOT_CONFIGURED", endpoint=self._config.endpoint)
            return ProviderContext(
                provider_type=self.provider_type,
                status="NOT_CONFIGURED",
                warning="No EverRoom provider is configured for this campaign.",
                slice=slice_,
            )
        try:
            self._client.health()
            room = self._client.resolve_room(room_id)
            return self._assemble(room_id=room.id, room_title=room.title, include=include, limits=limits)
        except EverRoomAuthError as exc:
            return self._failed(exc, room_id=room_id)
        except EverRoomNotFoundError as exc:
            return self._failed(exc, room_id=room_id)
        except EverRoomInvalidResponseError as extra:
            return self._failed(extra, room_id=room_id)
        except EverRoomUnavailableError as exc:
            return self._failed(exc, room_id=room_id)
        except EverRoomError as exc:
            return self._failed(exc, room_id=room_id)

    def _assemble(
        self,
        *,
        room_id: str,
        room_title: str,
        include: set[str],
        limits: ContextLimits,
    ) -> ProviderContext:
        slice_ = EverRoomContextSlice(
            status="AVAILABLE",
            endpoint=self._config.endpoint,
            room_id=room_id,
            room_title=room_title,
        )
        room_context = self._safe_room_context(room_id)
        overview_text: Optional[str] = None
        if room_context is not None:
            slice_.overview = room_context.overview or None
            slice_.room_status = room_context.status or None
            overview_text = room_context.overview
        if "summary" in include and not slice_.overview:
            overview = self._safe_overview(room_id)
            if overview is not None:
                slice_.overview = _overview_text(overview.payload) or slice_.overview
        if "sources" in include:
            sources = self._safe_sources(room_id)
            slice_.source_count = len(sources)
            slice_.sources = [_public_source(item) for item in sources[: limits.sources]]
        if "documents" in include:
            documents = self._safe_documents(room_id)
            slice_.document_count = len(documents)
            slice_.documents = [_public_document(item) for item in documents[: limits.documents]]
        if "decisions" in include:
            decisions = self._safe_decisions(room_id, limits.decisions)
            if overview_text:
                decisions.extend(_overview_decisions(overview_text, room_id, limits.decisions - len(decisions)))
            slice_.decision_count = len(decisions)
            slice_.decisions = [_public_decision(item) for item in decisions[: limits.decisions]]
        if "open_questions" in include:
            questions = _questions_from_context(room_context, limits.open_questions)
            slice_.open_question_count = len(questions)
            slice_.open_questions = [item.model_dump(mode="json", by_alias=False) for item in questions]
        if "knowledge" in include:
            knowledge = self._safe_knowledge(room_id)
            slice_.knowledge = [_public_knowledge(item) for item in knowledge[: limits.knowledge]]
        if "sources" not in include and slice_.source_count == 0:
            slice_.source_count = len(self._safe_sources(room_id))
        return ProviderContext(provider_type=self.provider_type, status="AVAILABLE", slice=slice_)

    def _failed(self, exc: EverRoomError, *, room_id: str) -> ProviderContext:
        warning = exc.message
        if exc.status == "UNAVAILABLE":
            warning = f"{exc.message} Campaign context will use MetaGit-only information."
        slice_ = EverRoomContextSlice(
            status=exc.status,
            warning=warning,
            endpoint=self._config.endpoint,
            room_id=room_id,
        )
        return ProviderContext(
            provider_type=self.provider_type,
            status=exc.status,
            warning=warning,
            slice=slice_,
        )

    def _safe_room_context(self, room_id: str) -> Optional[EverRoomRoomContext]:
        try:
            return self._client.get_room_context(room_id)
        except EverRoomError:
            return None

    def _safe_overview(self, room_id: str) -> Any:
        try:
            return self._client.get_room_overview(room_id)
        except EverRoomError:
            return None

    def _safe_sources(self, room_id: str) -> list[Any]:
        try:
            return self._client.list_room_sources(room_id)
        except EverRoomError:
            return []

    def _safe_documents(self, room_id: str) -> list[Any]:
        try:
            return self._client.list_room_documents(room_id)
        except EverRoomError:
            return []

    def _safe_decisions(self, room_id: str, limit: int) -> list[Any]:
        try:
            return self._client.list_room_decisions(room_id, limit=limit)
        except EverRoomError:
            return []

    def _safe_knowledge(self, room_id: str) -> list[Any]:
        try:
            return self._client.list_room_knowledge(room_id)
        except EverRoomError:
            return []


def _public_source(item: Any) -> dict[str, Any]:
    payload = item.model_dump(mode="json", by_alias=False)
    payload["source"] = "everroom"
    payload["identity"] = identity_haystack(list(item.identity_hints))
    payload.pop("bytes", None)
    return payload


def _public_document(item: Any) -> dict[str, Any]:
    payload = item.model_dump(mode="json", by_alias=False)
    payload["source"] = "everroom"
    return payload


def _public_decision(item: Any) -> dict[str, Any]:
    payload = dict(item) if isinstance(item, dict) else item.model_dump(mode="json", by_alias=False)
    payload["source"] = "everroom"
    return payload


def _public_knowledge(item: Any) -> dict[str, Any]:
    payload = item.model_dump(mode="json", by_alias=False)
    payload["source"] = "everroom"
    return payload


def _questions_from_context(
    room_context: Optional[EverRoomRoomContext],
    limit: int,
) -> list[EverRoomOpenQuestion]:
    if room_context is None:
        return []
    questions: list[EverRoomOpenQuestion] = []
    for step in room_context.next_steps:
        if not step:
            continue
        questions.append(EverRoomOpenQuestion(title=str(step)))
        if len(questions) >= limit:
            return questions
    for item in room_context.action_items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        questions.append(
            EverRoomOpenQuestion(
                title=title,
                owner=item.get("owner"),
                dueDate=item.get("dueDate"),
                sourceTitle=item.get("sourceTitle"),
            ),
        )
        if len(questions) >= limit:
            break
    return questions


def _overview_text(payload: dict[str, Any]) -> Optional[str]:
    for key in ("overview", "summary", "text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _overview_decisions(overview: str, room_id: str, remaining: int) -> list[dict[str, Any]]:
    if remaining <= 0:
        return []
    _ = (overview, room_id)
    return []
