#!/usr/bin/env python
"""
Pydantic models for Metagit MCP runtime state.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class McpActivationState(str, Enum):
    """Activation state for MCP workspace gating."""

    ACTIVE = "active"
    INACTIVE_MISSING_CONFIG = "inactive_missing_config"
    INACTIVE_INVALID_CONFIG = "inactive_invalid_config"


class WorkspaceStatus(BaseModel):
    """Current workspace status used by MCP tools and resources."""

    state: McpActivationState = Field(
        ...,
        description="Workspace activation state",
    )
    root_path: Optional[str] = Field(
        default=None,
        description="Resolved workspace root path when available",
    )
    reason: Optional[str] = Field(
        default=None,
        description="Human-readable reason for inactive state",
    )
