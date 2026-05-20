#!/usr/bin/env python
"""
Agent-mode detection for non-interactive, agent-optimized interfaces.
"""

from __future__ import annotations

import os

from metagit.core.appconfig.models import AppConfig

_ENV_VAR = "METAGIT_AGENT_MODE"
_TRUTHY = frozenset({"1", "true", "yes", "on"})


def env_agent_mode_enabled() -> bool | None:
    """
    Read METAGIT_AGENT_MODE from the environment.

    Returns None when the variable is unset (caller should use file config).
    """
    raw = os.getenv(_ENV_VAR)
    if raw is None:
        return None
    return raw.strip().lower() in _TRUTHY


def resolve_agent_mode(config: AppConfig) -> bool:
    """Effective agent mode: METAGIT_AGENT_MODE overrides appconfig.agent_mode."""
    from_env = env_agent_mode_enabled()
    if from_env is not None:
        return from_env
    return bool(config.agent_mode)


def apply_agent_mode_override(config: AppConfig) -> AppConfig:
    """Apply METAGIT_AGENT_MODE to config after load."""
    from_env = env_agent_mode_enabled()
    if from_env is not None:
        config.agent_mode = from_env
    return config
