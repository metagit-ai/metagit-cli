#!/usr/bin/env python
"""
Compose layered agent instructions from .metagit.yml for controller and subagents.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import WorkspaceProject

_LAYER_HEADERS: dict[str, str] = {
    "file": "[FILE]",
    "workspace": "[WORKSPACE]",
    "project": "[PROJECT]",
    "repo": "[REPO]",
}


class AgentInstructionLayer(BaseModel):
    """One non-empty instruction layer from the manifest."""

    layer: Literal["file", "workspace", "project", "repo"]
    text: str = Field(..., min_length=1)


class AgentInstructionsComposition(BaseModel):
    """Structured and composed agent instructions for a scope."""

    layers: list[AgentInstructionLayer] = Field(default_factory=list)
    effective: str = ""


class AgentInstructionsResolver:
    """Build instruction stacks for workspace, project, and repo scopes."""

    def resolve(
        self,
        config: MetagitConfig,
        *,
        project: Optional[WorkspaceProject] = None,
        repo: Optional[ProjectPath] = None,
    ) -> AgentInstructionsComposition:
        """Compose instructions from file → workspace → project → repo."""
        layers: list[AgentInstructionLayer] = []
        file_text = _normalized(config.agent_instructions)
        if file_text:
            layers.append(AgentInstructionLayer(layer="file", text=file_text))
        if config.workspace:
            workspace_text = _normalized(config.workspace.agent_instructions)
            if workspace_text:
                layers.append(AgentInstructionLayer(layer="workspace", text=workspace_text))
        if project:
            project_text = _normalized(project.agent_instructions)
            if project_text:
                layers.append(AgentInstructionLayer(layer="project", text=project_text))
        if repo:
            repo_text = _normalized(repo.agent_instructions)
            if repo_text:
                layers.append(AgentInstructionLayer(layer="repo", text=repo_text))
        return AgentInstructionsComposition(
            layers=layers,
            effective=_compose_text(layers=layers),
        )

    def find_repo(
        self,
        project: WorkspaceProject,
        *,
        repo_name: Optional[str] = None,
        repo_path: Optional[str] = None,
    ) -> Optional[ProjectPath]:
        """Locate a configured repo entry by name or resolved path."""
        if not repo_name and not repo_path:
            return None
        normalized_path = repo_path.strip() if repo_path else None
        for entry in project.repos:
            if repo_name and entry.name == repo_name:
                return entry
            if normalized_path and entry.path and entry.path == normalized_path:
                return entry
            if normalized_path and entry.path and normalized_path.endswith(entry.path):
                return entry
        return None


def _normalized(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def _compose_text(layers: list[AgentInstructionLayer]) -> str:
    if not layers:
        return ""
    blocks: list[str] = []
    for item in layers:
        header = _LAYER_HEADERS.get(item.layer, item.layer.upper())
        blocks.append(f"{header}\n{item.text}")
    return "\n\n---\n\n".join(blocks)
