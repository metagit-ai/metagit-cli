#!/usr/bin/env python
"""Injectable clock for deterministic lease expiry in scenarios."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


class ControllableClock:
    """Shared mutable clock for BranchService / LeaseService hooks."""

    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime(2026, 8, 27, 12, 0, 0, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self._now

    def now_iso(self) -> str:
        return self._now.isoformat()

    def advance(self, *, seconds: int = 0, minutes: int = 0, hours: int = 0) -> datetime:
        self._now = self._now + timedelta(seconds=seconds, minutes=minutes, hours=hours)
        return self._now

    def set(self, value: datetime) -> None:
        self._now = value
