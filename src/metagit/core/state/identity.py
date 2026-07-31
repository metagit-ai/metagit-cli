#!/usr/bin/env python
"""Resolve organization and workspace identities for the state plane."""

from __future__ import annotations

import os

from metagit.core.appconfig.models import StateConfig
from metagit.core.state.plane import default_org_id, derive_workspace_id


def resolve_org_id(state: StateConfig) -> str:
    """Resolve the effective organization partition identifier."""
    env_org_id = os.getenv("METAGIT_STATE_ORG_ID", "").strip()
    if env_org_id:
        return env_org_id
    return state.org_id.strip() or default_org_id()


def resolve_workspace_id(state: StateConfig, workspace_root: str) -> str:
    """Resolve the effective workspace partition identifier."""
    env_workspace_id = os.getenv("METAGIT_STATE_WORKSPACE_ID", "").strip()
    if env_workspace_id:
        return env_workspace_id
    return state.workspace_id.strip() or derive_workspace_id(workspace_root)


__all__ = ["resolve_org_id", "resolve_workspace_id"]
