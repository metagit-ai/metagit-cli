#!/usr/bin/env python
"""Resolve the active state backend bundle for a workspace root."""

from __future__ import annotations

import os
from typing import Any

from metagit.core.appconfig.models import AppConfig, StateConfig
from metagit.core.state.base import BackendBundle
from metagit.core.state.local import local_bundle
from metagit.core.state.remote import remote_bundle


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
    _ = workspace_root
    state = _load_state_config()
    url = _resolve_remote_url(state)
    backend_kind = _resolve_backend_kind(state)
    effective = "http" if url or backend_kind == "http" else "local"
    return {
        "backend": effective,
        "url": url if effective == "http" else "",
        "configured_backend": backend_kind,
        "conflict_retries": state.conflict_retries,
        "env_overrides": {
            "METAGIT_STATE_URL": bool(os.getenv("METAGIT_STATE_URL", "").strip()),
            "METAGIT_STATE_BACKEND": bool(os.getenv("METAGIT_STATE_BACKEND", "").strip()),
            "METAGIT_STATE_TOKEN": bool(os.getenv("METAGIT_STATE_TOKEN", "").strip()),
        },
        "token_configured": bool(_resolve_bearer_token(state)) if effective == "http" else False,
    }


def resolve_backend(workspace_root: str) -> BackendBundle:
    """
    Select objectives/handoffs/approvals/events backends for ``workspace_root``.

    Precedence:
    1. ``METAGIT_STATE_URL`` / ``METAGIT_STATE_BACKEND=http``
    2. App-config ``state`` block
    3. Local files (default)
    """
    state = _load_state_config()
    url = _resolve_remote_url(state)
    backend_kind = _resolve_backend_kind(state)
    if url or backend_kind == "http":
        if not url:
            raise ValueError("remote state backend selected but no state.url configured")
        return remote_bundle(url, bearer_token=_resolve_bearer_token(state))
    return local_bundle(workspace_root)


__all__ = ["describe_state_backend", "resolve_backend"]
