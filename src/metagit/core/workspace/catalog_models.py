#!/usr/bin/env python
"""
Pydantic models for workspace catalog list and mutation results.
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import Workspace


class CatalogError(BaseModel):
    """Structured catalog operation error."""

    kind: str
    message: str


class CatalogResult(BaseModel):
    """Uniform envelope for agentic CLI, MCP, and API responses."""

    ok: bool = True
    error: Optional[CatalogError] = None
    data: Optional[dict[str, Any]] = None


class WorkspaceSummary(BaseModel):
    """Workspace section of a manifest with project roll-up."""

    definition_path: str
    workspace_root: str
    file_name: str
    file_description: Optional[str] = None
    file_agent_instructions: Optional[str] = None
    workspace: Optional[Workspace] = None
    project_count: int = 0
    repo_count: int = 0


class ProjectListEntry(BaseModel):
    """Project row for list operations."""

    name: str
    description: Optional[str] = None
    agent_instructions: Optional[str] = None
    dedupe_enabled: Optional[bool] = Field(
        default=None,
        description=(
            "When set in the manifest, overrides app-config workspace.dedupe.enabled "
            "for this project"
        ),
    )
    repo_count: int = 0


class RepoListEntry(BaseModel):
    """Repository row for list operations."""

    project_name: str
    repo: ProjectPath
    configured_path: Optional[str] = None
    repo_path: Optional[str] = None
    exists: Optional[bool] = None
    status: Optional[str] = None


class CatalogMutationResult(BaseModel):
    """Result of add/remove mutations."""

    ok: bool = True
    error: Optional[CatalogError] = None
    entity: Literal["project", "repo"] = "project"
    operation: Literal["add", "remove", "noop"] = "add"
    project_name: str = ""
    repo_name: Optional[str] = None
    config_path: str = ""
