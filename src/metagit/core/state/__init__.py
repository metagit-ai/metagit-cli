#!/usr/bin/env python
"""Pluggable state backends for workspace coordination data."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS: dict[str, tuple[str, str]] = {
    "ApprovalBackend": ("metagit.core.state.base", "ApprovalBackend"),
    "BackendBundle": ("metagit.core.state.base", "BackendBundle"),
    "DocumentRef": ("metagit.core.state.document", "DocumentRef"),
    "DocumentStore": ("metagit.core.state.document", "DocumentStore"),
    "DynamoDocumentStore": ("metagit.core.state.dynamodb", "DynamoDocumentStore"),
    "EventsBackend": ("metagit.core.state.base", "EventsBackend"),
    "HandoffBackend": ("metagit.core.state.base", "HandoffBackend"),
    "InMemoryDocumentStore": ("metagit.core.state.memory", "InMemoryDocumentStore"),
    "LocalFileBackend": ("metagit.core.state.local", "LocalFileBackend"),
    "MongoDocumentStore": ("metagit.core.state.mongodb", "MongoDocumentStore"),
    "ObjectiveBackend": ("metagit.core.state.base", "ObjectiveBackend"),
    "StateBackendError": ("metagit.core.state.errors", "StateBackendError"),
    "StateConflictError": ("metagit.core.state.errors", "StateConflictError"),
    "StateToken": ("metagit.core.state.base", "StateToken"),
    "describe_state_backend": ("metagit.core.state.resolver", "describe_state_backend"),
    "local_bundle": ("metagit.core.state.local", "local_bundle"),
    "remote_bundle": ("metagit.core.state.remote", "remote_bundle"),
    "resolve_backend": ("metagit.core.state.resolver", "resolve_backend"),
    "resolve_document_store": ("metagit.core.state.resolver", "resolve_document_store"),
}


def __getattr__(name: str) -> Any:
    """Load public state exports without eagerly importing context-backed modules."""
    export = _EXPORTS.get(name)
    if export is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = export
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


__all__ = [
    "ApprovalBackend",
    "BackendBundle",
    "DocumentRef",
    "DocumentStore",
    "DynamoDocumentStore",
    "EventsBackend",
    "HandoffBackend",
    "InMemoryDocumentStore",
    "LocalFileBackend",
    "MongoDocumentStore",
    "ObjectiveBackend",
    "StateBackendError",
    "StateConflictError",
    "StateToken",
    "describe_state_backend",
    "local_bundle",
    "remote_bundle",
    "resolve_backend",
    "resolve_document_store",
]
