#!/usr/bin/env python
"""EverRoom Gateway client errors and degraded-mode statuses."""

from __future__ import annotations

from typing import Literal

EverRoomStatus = Literal[
    "NOT_CONFIGURED",
    "AVAILABLE",
    "UNAVAILABLE",
    "AUTH_FAILED",
    "ROOM_NOT_FOUND",
    "INVALID_RESPONSE",
]


class EverRoomError(Exception):
    """Base error for EverRoom Gateway interactions."""

    def __init__(self, message: str, *, status: EverRoomStatus = "UNAVAILABLE") -> None:
        super().__init__(message)
        self.status: EverRoomStatus = status
        self.message: str = message


class EverRoomAuthError(EverRoomError):
    """Bearer authentication failed against the Gateway."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status="AUTH_FAILED")


class EverRoomNotFoundError(EverRoomError):
    """Configured Room was not found on the Gateway."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status="ROOM_NOT_FOUND")


class EverRoomUnavailableError(EverRoomError):
    """Gateway is unreachable, timed out, or not ready."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status="UNAVAILABLE")


class EverRoomInvalidResponseError(EverRoomError):
    """Gateway returned a payload that could not be interpreted."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status="INVALID_RESPONSE")
