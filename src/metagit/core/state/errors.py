#!/usr/bin/env python
"""Errors raised by metagit state backends."""


class StateBackendError(Exception):
    """Base error for state backend failures."""


class StateConflictError(StateBackendError):
    """Raised when a write fails optimistic concurrency checks."""
