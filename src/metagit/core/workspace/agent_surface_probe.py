#!/usr/bin/env python
"""
Read-only agent-access file probes for workspace discovery (RFC-0020).
"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

AGENT_ACCESS_MARKER_START = "<!-- agent-access:start"


class RepoAgentSurfaceProbe(TypedDict):
    """Per-repo agent surface flags."""

    has_agents_md: bool
    has_llms_txt: bool
    has_readme_marker: bool


def probe_repo_agent_surfaces(repo_path: str | Path) -> RepoAgentSurfaceProbe:
    """Probe AGENTS.md, llms.txt, and README agent-access marker (no writes)."""
    root = Path(repo_path)
    readme = root / "README.md"
    has_marker = False
    if readme.is_file():
        try:
            text = readme.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        has_marker = AGENT_ACCESS_MARKER_START in text
    return {
        "has_agents_md": (root / "AGENTS.md").is_file(),
        "has_llms_txt": (root / "llms.txt").is_file(),
        "has_readme_marker": has_marker,
    }


def has_any_agent_surface(probe: RepoAgentSurfaceProbe) -> bool:
    """True when the repo has at least one agent onboarding artifact."""
    return bool(probe["has_agents_md"] or probe["has_llms_txt"] or probe["has_readme_marker"])
