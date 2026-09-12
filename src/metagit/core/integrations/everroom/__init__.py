#!/usr/bin/env python
"""Optional EverRoom Gateway adapter for campaign context."""

from metagit.core.integrations.everroom.client import EverRoomClient, EverRoomHttpClient, markdown_to_tiptap
from metagit.core.integrations.everroom.errors import (
    EverRoomAuthError,
    EverRoomError,
    EverRoomInvalidResponseError,
    EverRoomNotFoundError,
    EverRoomStatus,
    EverRoomUnavailableError,
)
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
from metagit.core.integrations.everroom.source_identity import canonical_git_identity

__all__ = [
    "EverRoomAuthError",
    "EverRoomClient",
    "EverRoomCreateResult",
    "EverRoomDecision",
    "EverRoomDocumentRef",
    "EverRoomError",
    "EverRoomHealth",
    "EverRoomHttpClient",
    "EverRoomInvalidResponseError",
    "EverRoomKnowledgeItem",
    "EverRoomNotFoundError",
    "EverRoomOverview",
    "EverRoomRoom",
    "EverRoomRoomContext",
    "EverRoomSource",
    "EverRoomStatus",
    "EverRoomUnavailableError",
    "canonical_git_identity",
    "markdown_to_tiptap",
]
