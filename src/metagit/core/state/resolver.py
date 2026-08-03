#!/usr/bin/env python
"""Resolve the active state backend bundle for a workspace root."""

from __future__ import annotations

import os
import threading
from importlib.util import find_spec
from typing import TYPE_CHECKING, Any

from metagit.core.appconfig.models import AppConfig, StateConfig
from metagit.core.state.document import DocumentStore
from metagit.core.state.identity import resolve_org_id, resolve_workspace_id

if TYPE_CHECKING:
    from metagit.core.state.base import BackendBundle

_MEMORY_STORES: dict[tuple[str, str], DocumentStore] = {}
_MEMORY_STORES_LOCK = threading.RLock()


def _load_state_config() -> StateConfig:
    loaded = AppConfig.load()
    if isinstance(loaded, AppConfig):
        return loaded.state
    return StateConfig()


def _resolve_remote_url(state: StateConfig) -> str:
    env_url = os.getenv("METAGIT_STATE_URL", "").strip()
    if env_url:
        return env_url
    return state.url.strip()


def _resolve_backend_kind(state: StateConfig) -> str:
    env_backend = os.getenv("METAGIT_STATE_BACKEND", "").strip().lower()
    if env_backend:
        return env_backend
    return state.backend


def _resolve_bearer_token(state: StateConfig) -> str:
    env_token = os.getenv("METAGIT_STATE_TOKEN", "").strip()
    if env_token:
        return env_token
    if state.token.strip():
        return state.token.strip()
    loaded = AppConfig.load()
    if isinstance(loaded, AppConfig) and loaded.api_key.strip():
        return loaded.api_key.strip()
    return ""


def describe_state_backend(workspace_root: str) -> dict[str, Any]:
    """
    Summarize effective coordination-state backend selection for diagnostics.

    ``workspace_root`` is the session/manifest root passed to ``resolve_backend``.
    Secrets are never returned — only whether a bearer token is configured.
    """
    state = _load_state_config()
    url = _resolve_remote_url(state)
    backend_kind = _resolve_backend_kind(state)
    effective = "http" if url or backend_kind == "http" else "local"
    if not url and backend_kind in {"memory", "dynamodb", "mongodb"}:
        effective = backend_kind
    if effective == "http":
        from metagit.core.state.http_document import sanitize_base_url_for_describe

        url = sanitize_base_url_for_describe(url)
    return {
        "backend": effective,
        "url": url if effective == "http" else "",
        "configured_backend": backend_kind,
        "org_id": resolve_org_id(state),
        "workspace_id": resolve_workspace_id(state, workspace_root),
        "extras": {
            "dynamodb": find_spec("boto3") is not None,
            "mongodb": find_spec("pymongo") is not None,
        },
        "conflict_retries": state.conflict_retries,
        "env_overrides": {
            "METAGIT_STATE_URL": bool(os.getenv("METAGIT_STATE_URL", "").strip()),
            "METAGIT_STATE_BACKEND": bool(os.getenv("METAGIT_STATE_BACKEND", "").strip()),
            "METAGIT_STATE_TOKEN": bool(os.getenv("METAGIT_STATE_TOKEN", "").strip()),
        },
        "token_configured": bool(_resolve_bearer_token(state)) if effective == "http" else False,
    }


def resolve_document_store(workspace_root: str) -> DocumentStore:
    """Resolve the generic document store selected for ``workspace_root``."""
    state = _load_state_config()
    url = _resolve_remote_url(state)
    backend_kind = _resolve_backend_kind(state)
    if url or backend_kind == "http":
        from metagit.core.state.http_document import HttpDocumentStore

        if not url:
            raise ValueError("remote state backend selected but no state.url configured")
        return HttpDocumentStore(url, bearer_token=_resolve_bearer_token(state))
    if backend_kind == "memory":
        from metagit.core.state.memory import InMemoryDocumentStore

        identity = (resolve_org_id(state), resolve_workspace_id(state, workspace_root))
        # Resolver-scoped cache makes the ephemeral backend stable within this process.
        with _MEMORY_STORES_LOCK:
            store = _MEMORY_STORES.get(identity)
            if store is None:
                store = InMemoryDocumentStore()
                _MEMORY_STORES[identity] = store
            return store
    if backend_kind == "dynamodb":
        from metagit.core.state.dynamodb import DynamoDocumentStore

        table = os.getenv("METAGIT_STATE_DDB_TABLE", "").strip() or state.dynamodb.table.strip()
        region = os.getenv("METAGIT_STATE_DDB_REGION", "").strip() or state.dynamodb.region.strip()
        endpoint_url = os.getenv("METAGIT_STATE_DDB_ENDPOINT", "").strip() or state.dynamodb.endpoint_url.strip()
        if not table:
            raise ValueError("dynamodb state backend requires table (state.dynamodb.table or METAGIT_STATE_DDB_TABLE)")
        return DynamoDocumentStore(
            table,
            region=region,
            endpoint_url=endpoint_url,
        )
    if backend_kind == "mongodb":
        from metagit.core.state.mongodb import MongoDocumentStore

        uri = os.getenv("METAGIT_STATE_MONGO_URI", "").strip() or state.mongodb.uri.strip()
        database = os.getenv("METAGIT_STATE_MONGO_DB", "").strip() or state.mongodb.database.strip()
        if not uri:
            raise ValueError("mongodb state backend requires uri (state.mongodb.uri or METAGIT_STATE_MONGO_URI)")
        if not database:
            raise ValueError(
                "mongodb state backend requires database (state.mongodb.database or METAGIT_STATE_MONGO_DB)"
            )
        collection = state.mongodb.collection.strip() or "metagit_state"
        return MongoDocumentStore(uri, database, collection=collection)
    from metagit.core.state.local_document import LocalDocumentStore

    return LocalDocumentStore(
        workspace_root,
        org_id=resolve_org_id(state),
        workspace_id=resolve_workspace_id(state, workspace_root),
    )


def resolve_backend(workspace_root: str) -> BackendBundle:
    """
    Select objectives/handoffs/approvals/events backends for ``workspace_root``.

    Precedence:
    1. ``METAGIT_STATE_URL`` / ``METAGIT_STATE_BACKEND=http``
    2. App-config ``state`` block
    3. Local files (default)

    All selected backends route through ``resolve_document_store`` + ``coord_bundle``.
    """
    state = _load_state_config()
    from metagit.core.state.adapters.coord import coord_bundle

    store = resolve_document_store(workspace_root)
    return coord_bundle(
        store,
        org_id=resolve_org_id(state),
        workspace_id=resolve_workspace_id(state, workspace_root),
    )


__all__ = [
    "describe_state_backend",
    "resolve_backend",
    "resolve_document_store",
    "resolve_org_id",
    "resolve_workspace_id",
]
