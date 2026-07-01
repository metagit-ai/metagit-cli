#!/usr/bin/env python
"""Pluggable state backends for workspace coordination data."""

from metagit.core.state.base import (
    ApprovalBackend,
    BackendBundle,
    EventsBackend,
    HandoffBackend,
    ObjectiveBackend,
    StateToken,
)
from metagit.core.state.errors import StateBackendError, StateConflictError
from metagit.core.state.local import LocalFileBackend, local_bundle
from metagit.core.state.remote import remote_bundle
from metagit.core.state.resolver import describe_state_backend, resolve_backend

__all__ = [
    "ApprovalBackend",
    "BackendBundle",
    "EventsBackend",
    "HandoffBackend",
    "LocalFileBackend",
    "ObjectiveBackend",
    "StateBackendError",
    "StateConflictError",
    "StateToken",
    "describe_state_backend",
    "local_bundle",
    "remote_bundle",
    "resolve_backend",
]
