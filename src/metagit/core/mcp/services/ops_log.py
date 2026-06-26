#!/usr/bin/env python
"""
Bounded operations log for MCP runtime.
"""

from collections import deque
from datetime import UTC, datetime


class OperationsLogService:
    """Store a bounded in-memory operations trail."""

    def __init__(self, capacity: int = 100) -> None:
        self._entries: deque[dict[str, str]] = deque(maxlen=capacity)

    def append(self, action: str, detail: str) -> None:
        """Append an operation log entry."""
        self._entries.append(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "action": action,
                "detail": detail,
            }
        )

    def list_entries(self) -> list[dict[str, str]]:
        """List operation log entries."""
        return list(self._entries)
