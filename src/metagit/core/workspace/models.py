#!/usr/bin/env python
"""
Pydantic models for .metagit.yml workspace configuration.
"""

from typing import Any, List, Optional

from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator

from metagit.core.config.documentation_models import (
    DocumentationSource,
    normalize_documentation_entries,
)
from metagit.core.project.models import ProjectPath
from metagit.core.project.source_models import ProjectSource
from metagit.core.workspace.agent_profile_models import AgentProfile


class DerivedSourceScope(BaseModel):
    """Intent record for which source project(s) a derived project may pull from."""

    project: str = Field(..., description="Source workspace project name")
    repos: List[str] = Field(
        default_factory=list,
        description=(
            "Optional allow-list of source repo names recorded at create time; "
            "empty means membership is whatever repos[] currently holds"
        ),
    )

    class Config:
        """Pydantic configuration."""

        extra = "forbid"


class DerivedProjectConfig(BaseModel):
    """Marks a workspace project as a derived surgical working set."""

    enabled: bool = Field(
        default=True,
        description="When true, this project is treated as a derived working set",
    )
    sources: List[DerivedSourceScope] = Field(
        default_factory=list,
        description="Provenance roots allowed for refresh/include operations",
    )

    class Config:
        """Pydantic configuration."""

        extra = "forbid"


class ProjectDedupeOverride(BaseModel):
    """Per-project override of app-config ``workspace.dedupe``."""

    enabled: Optional[bool] = Field(
        default=None,
        description=(
            "When set, overrides workspace.dedupe.enabled from metagit.config.yaml "
            "for sync and layout under this project only"
        ),
    )

    class Config:
        """Pydantic configuration."""

        extra = "forbid"


class WorkspaceProject(BaseModel):
    """Model for workspace project."""

    name: str = Field(..., description="Workspace project name")
    description: Optional[str] = Field(None, description="Human-readable description of this workspace project")
    agent_instructions: Optional[str] = Field(
        None,
        validation_alias=AliasChoices("agent_instructions", "agent_prompt"),
        description="Optional instructions for agents working in this workspace project",
    )
    agent_profile: Optional[AgentProfile] = Field(
        default=None,
        description="Structured agent posture (skills, MCP, rules) inherited by repos unless overridden",
    )
    dedupe: Optional[ProjectDedupeOverride] = Field(
        default=None,
        description=(
            "Optional override of app-config workspace.dedupe for this project (currently supports enabled only)"
        ),
    )
    protected: Optional[bool] = Field(
        False,
        description=("If true, catalog and layout mutations on this project and its repos require force"),
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Flat metadata tags inherited by repos unless overridden",
    )
    documentation: Optional[List[DocumentationSource]] = Field(
        None,
        description=("Documentation sources for this workspace project group (paths, URLs, graph metadata)"),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible key-value payload for exports and tooling",
    )
    sources: List[ProjectSource] = Field(
        default_factory=list,
        description="Declarative provider import scopes for this project",
    )
    derived: Optional[DerivedProjectConfig] = Field(
        default=None,
        description=(
            "When set, this project is a derived surgical subset of other "
            "workspace projects in the same umbrella manifest"
        ),
    )
    repos: List[ProjectPath] = Field(..., description="Repository list")

    @model_validator(mode="after")
    def validate_unique_source_ids(self) -> "WorkspaceProject":
        seen: set[str] = set()
        for source in self.sources:
            if source.id in seen:
                raise ValueError(f"duplicate sources[].id '{source.id}' in project '{self.name}'")
            seen.add(source.id)
        return self

    @model_validator(mode="after")
    def validate_derived_provenance(self) -> "WorkspaceProject":
        """Ensure derived repos carry provenance when the project is marked derived."""
        if self.derived is None or not self.derived.enabled:
            return self
        for repo in self.repos:
            if repo.derived_from is None:
                raise ValueError(f"derived project '{self.name}' repo '{repo.name}' requires derived_from provenance")
        return self

    @field_validator("documentation", mode="before")
    @classmethod
    def _coerce_documentation(cls, value: object) -> object:
        """Accept strings or dicts in YAML documentation lists."""
        return normalize_documentation_entries(value)

    @field_validator("repos", mode="before")
    def validate_repos(cls, v: Any) -> Any:
        """Handle YAML anchors and complex repo structures."""
        if isinstance(v, list):
            # Flatten any nested lists that might come from YAML anchors
            flattened: List[Any] = []
            for item in v:
                if isinstance(item, list):
                    flattened.extend(item)
                else:
                    flattened.append(item)
            return flattened
        return v

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"


class Workspace(BaseModel):
    """Model for workspace configuration."""

    description: Optional[str] = Field(None, description="Human-readable description of this workspace")
    agent_instructions: Optional[str] = Field(
        None,
        validation_alias=AliasChoices("agent_instructions", "agent_prompt"),
        description="Optional instructions for agents working in this workspace",
    )
    agent_profile: Optional[AgentProfile] = Field(
        default=None,
        description="Workspace-wide structured agent posture inherited by projects and repos",
    )
    projects: List[WorkspaceProject] = Field(..., description="Workspace projects")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
