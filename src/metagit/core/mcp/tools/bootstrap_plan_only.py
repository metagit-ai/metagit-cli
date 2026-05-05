#!/usr/bin/env python
"""
Plan-only bootstrap MCP tool implementation.
"""

from typing import Optional


def metagit_bootstrap_config_plan_only(reason: Optional[str]) -> dict[str, str]:
    """Return bootstrap guidance when MCP sampling is not yet available."""
    details = reason or "Workspace is not active. Generate or fix .metagit.yml first."
    return {
        "mode": "plan_only",
        "message": details,
    }
