#!/usr/bin/env python
"""Stable component identity: project/repo/component."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ComponentId(BaseModel):
    """Canonical three-segment component identity."""

    model_config = ConfigDict(extra="forbid")

    project: str = Field(..., min_length=1)
    repo: str = Field(..., min_length=1)
    component: str = Field(..., min_length=1)

    @property
    def key(self) -> str:
        return f"{self.project}/{self.repo}/{self.component}"


def component_id(project: str, repo: str, component: str) -> str | ValueError:
    """Return ``project/repo/component`` or ValueError when a part is empty or contains ``/``."""
    parts = (("project", project), ("repo", repo), ("component", component))
    cleaned: list[str] = []
    for label, value in parts:
        stripped = str(value).strip()
        if not stripped or "/" in stripped:
            return ValueError(f"invalid {label} for component id: {value!r}")
        cleaned.append(stripped)
    return f"{cleaned[0]}/{cleaned[1]}/{cleaned[2]}"


def parse_component_id(value: str) -> ComponentId | ValueError:
    """Parse a three-segment component id."""
    trimmed = str(value).strip()
    segments = trimmed.split("/")
    if len(segments) != 3:
        return ValueError(f"invalid component id {value!r}; expected project/repo/component")
    project, repo, component = (item.strip() for item in segments)
    if not project or not repo or not component:
        return ValueError(f"invalid component id {value!r}; empty segment")
    return ComponentId(project=project, repo=repo, component=component)
