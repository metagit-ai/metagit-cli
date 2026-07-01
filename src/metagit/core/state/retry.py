#!/usr/bin/env python
"""Retry helper for optimistic state mutations."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from metagit.core.state.errors import StateConflictError

T = TypeVar("T")


def with_state_retry(action: Callable[[], T], *, retries: int = 1) -> T:
    """Run ``action`` and retry on ``StateConflictError`` up to ``retries`` times."""
    attempts = retries + 1
    last_error: StateConflictError | None = None
    for _ in range(attempts):
        try:
            return action()
        except StateConflictError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise RuntimeError("with_state_retry exhausted without executing action")
