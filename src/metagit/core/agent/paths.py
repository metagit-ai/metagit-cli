#!/usr/bin/env python
"""Vendor-specific agent definition install paths."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from metagit.core.skills.installer import SUPPORTED_TARGETS, TARGET_PATHS

AGENT_SUPPORTED_TARGETS = list(SUPPORTED_TARGETS)


class AgentTargetPaths(BaseModel):
    """Project-local and user-global agent definition directories."""

    project_agents_path: str = Field(
        ...,
        description="Project-local agents destination",
    )
    user_agents_path: str = Field(
        ...,
        description="User-global agents destination",
    )


AGENT_TARGET_PATHS: dict[str, AgentTargetPaths] = {
    "opencode": AgentTargetPaths(
        project_agents_path=".opencode/agents",
        user_agents_path="~/.config/opencode/agents",
    ),
    "hermes": AgentTargetPaths(
        project_agents_path=".hermes/agents",
        user_agents_path="~/.config/hermes/agents",
    ),
    "openclaw": AgentTargetPaths(
        project_agents_path=".openclaw/agents",
        user_agents_path="~/.config/openclaw/agents",
    ),
    "claude_code": AgentTargetPaths(
        project_agents_path=".claude/agents",
        user_agents_path="~/.claude/agents",
    ),
    "cursor": AgentTargetPaths(
        project_agents_path=".cursor/agents",
        user_agents_path="~/.cursor/agents",
    ),
    "github_copilot": AgentTargetPaths(
        project_agents_path=".github/agents",
        user_agents_path="~/.github/agents",
    ),
    "windsurf": AgentTargetPaths(
        project_agents_path=".windsurf/skills",
        user_agents_path="~/.codeium/windsurf/skills",
    ),
    "codex": AgentTargetPaths(
        project_agents_path=".agents/skills",
        user_agents_path="~/.agents/skills",
    ),
}


def expand_agent_path(path_value: str, *, project_root: Path | None = None) -> Path:
    """Expand a project-relative or user-home agent path."""
    expanded = Path(os.path.expanduser(path_value))
    if expanded.is_absolute():
        return expanded
    root = project_root or Path.cwd()
    return root / expanded


def autodetect_agent_targets(
    scope: str,
    *,
    project_root: Path | None = None,
) -> list[str]:
    """Detect vendors by existing agent or parent config directories."""
    resolved: list[str] = []
    for vendor in AGENT_SUPPORTED_TARGETS:
        candidates = [
            resolve_agents_directory(vendor, scope, project_root=project_root),
        ]
        if vendor in TARGET_PATHS:
            candidates.append(
                resolve_skills_directory(vendor, scope, project_root=project_root)
            )
        if any(
            candidate.exists() or candidate.parent.exists() for candidate in candidates
        ):
            resolved.append(vendor)
    return resolved


def resolve_skills_directory(
    vendor: str,
    scope: str,
    *,
    project_root: Path | None = None,
) -> Path:
    """Return the skills directory for a vendor and install scope."""
    if vendor not in TARGET_PATHS:
        supported = ", ".join(AGENT_SUPPORTED_TARGETS)
        raise ValueError(f"Unknown vendor {vendor!r}. Supported: {supported}")
    paths = TARGET_PATHS[vendor]
    raw = paths.project_skills_path if scope == "project" else paths.user_skills_path
    return expand_agent_path(raw, project_root=project_root)


def resolve_agents_directory(
    vendor: str,
    scope: str,
    *,
    project_root: Path | None = None,
) -> Path:
    """Return the agents directory for a vendor and install scope."""
    if vendor not in AGENT_TARGET_PATHS:
        supported = ", ".join(AGENT_SUPPORTED_TARGETS)
        raise ValueError(f"Unknown vendor {vendor!r}. Supported: {supported}")
    paths = AGENT_TARGET_PATHS[vendor]
    raw = paths.project_agents_path if scope == "project" else paths.user_agents_path
    return expand_agent_path(raw, project_root=project_root)


def resolve_vendor_artifact_path(
    vendor: str,
    scope: str,
    *,
    primary_name: str,
    install_as: Literal["agent", "skill"] = "agent",
    project_root: Path | None = None,
) -> Path:
    """Return the on-disk path for one vendor install artifact."""
    if install_as == "skill":
        skills_dir = resolve_skills_directory(
            vendor,
            scope,
            project_root=project_root,
        )
        return skills_dir / primary_name / "SKILL.md"
    agents_dir = resolve_agents_directory(
        vendor,
        scope,
        project_root=project_root,
    )
    return agents_dir / primary_name
