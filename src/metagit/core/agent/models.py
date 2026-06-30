#!/usr/bin/env python
"""Pydantic models for metagit agent templates."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from metagit.core.init.models import InitPromptSpec, InitTemplateFileSpec


class AgentArchetype(str, Enum):
    """High-level agent role tier."""

    CONTROL_PLANE = "control_plane"
    SPECIALIST = "specialist"


class AgentScopeLevel(str, Enum):
    """Manifest scope the agent primarily operates in."""

    WORKSPACE = "workspace"
    PROJECT = "project"
    REPO = "repo"


class AgentTemplateStatus(str, Enum):
    """Template maturity for catalog display."""

    STABLE = "stable"
    BETA = "beta"


class AgentTemplateSource(str, Enum):
    """Where a catalog entry's manifest and files resolve from."""

    BUNDLED = "bundled"
    OVERLAY = "overlay"
    MERGED = "merged"


class AgentExternalSkillRef(BaseModel):
    """Reference to a skill installed outside the metagit bundle."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Skill identifier")
    note: str = Field(
        default="",
        description="When or why to install this skill for the agent",
    )


class AgentVendorSpec(BaseModel):
    """Vendor-specific output filename for an agent definition."""

    model_config = ConfigDict(extra="forbid")

    filename: str = Field(
        ...,
        description="Filename under the vendor agents directory, or skill dir name",
    )
    template: str | None = Field(
        default=None,
        description="Optional alternate template source inside the template directory",
    )
    install_as: Literal["agent", "skill"] = Field(
        default="agent",
        description="Write to vendor agents dir or as a Hermes-style skill tree",
    )


class AgentUiSpec(BaseModel):
    """Catalog presentation metadata."""

    model_config = ConfigDict(extra="forbid")

    category: str = Field(..., description="Grouping label for UI card grids")
    icon: str = Field(default="", description="Optional icon token")
    color: str = Field(default="", description="Optional theme color token")
    sort_order: int = Field(default=100, description="Ascending sort in catalog lists")


class AgentTemplateManifest(BaseModel):
    """Manifest for a bundled or overlay agent template."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(
        default="1.0",
        description="Manifest schema version (major.minor)",
    )
    id: str = Field(..., description="Template identifier for --template")
    label: str = Field(..., description="Short label for list output")
    description: str = Field(..., description="Longer description of the agent role")
    archetype: AgentArchetype = Field(
        default=AgentArchetype.SPECIALIST,
        description="Control-plane vs specialist role",
    )
    scope: AgentScopeLevel = Field(
        default=AgentScopeLevel.WORKSPACE,
        description="Primary operating scope",
    )
    status: AgentTemplateStatus = Field(
        default=AgentTemplateStatus.STABLE,
        description="Template maturity",
    )
    version: str = Field(default="1.0.0", description="Template content semver")
    prompt_kinds: list[str] = Field(
        default_factory=list,
        description="Built-in metagit prompt kinds referenced by the template",
    )
    mcp_tools: list[str] = Field(
        default_factory=list,
        description="Metagit MCP tool names documented for this role",
    )
    delegates_to: list[str] = Field(
        default_factory=list,
        description="Other template IDs this role may spawn",
    )
    delegated_by: list[str] = Field(
        default_factory=list,
        description="Parent template IDs (denormalized for UI)",
    )
    ui: AgentUiSpec = Field(
        default_factory=lambda: AgentUiSpec(category="General", sort_order=100),
        description="Catalog presentation metadata",
    )
    prompts: list[InitPromptSpec] = Field(default_factory=list)
    files: list[InitTemplateFileSpec] = Field(default_factory=list)
    vendors: dict[str, AgentVendorSpec] = Field(
        default_factory=dict,
        description="Per-vendor output filename overrides",
    )
    recommended_skills: list[str] = Field(
        default_factory=list,
        description="Bundled metagit skills to install with --install-skills",
    )
    external_skills: list[AgentExternalSkillRef] = Field(
        default_factory=list,
        description="Non-bundled skills the agent should use when available",
    )

    @field_validator("schema_version")
    @classmethod
    def _validate_schema_version(cls, value: str) -> str:
        major = value.split(".", maxsplit=1)[0]
        if major != "1":
            raise ValueError(f"unsupported agent template schema major version: {value!r}")
        return value


class AgentWriteResult(BaseModel):
    """Summary of files written by export or create."""

    model_config = ConfigDict(extra="forbid")

    template_id: str
    paths: list[str] = Field(default_factory=list)
    vendor: str | None = None
    scope: str | None = None
    dry_run: bool = False


class AgentCatalogEntry(BaseModel):
    """One template row in the catalog envelope."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    description: str
    archetype: AgentArchetype
    scope: AgentScopeLevel
    status: AgentTemplateStatus
    version: str
    source: AgentTemplateSource
    overlay_path: str | None = None
    ui: AgentUiSpec
    prompt_kinds: list[str] = Field(default_factory=list)
    mcp_tools: list[str] = Field(default_factory=list)
    recommended_skills: list[str] = Field(default_factory=list)
    external_skills: list[AgentExternalSkillRef] = Field(default_factory=list)
    vendors: list[str] = Field(default_factory=list)
    delegates_to: list[str] = Field(default_factory=list)
    delegated_by: list[str] = Field(default_factory=list)


class AgentCatalogTaxonomy(BaseModel):
    """Distinct values across the active catalog."""

    model_config = ConfigDict(extra="forbid")

    archetypes: list[str] = Field(default_factory=list)
    scopes: list[str] = Field(default_factory=list)
    vendors: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)


class AgentCatalogEnvelope(BaseModel):
    """Machine-readable catalog for CLI and web."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    templates: list[AgentCatalogEntry] = Field(default_factory=list)
    taxonomy: AgentCatalogTaxonomy = Field(default_factory=AgentCatalogTaxonomy)


class AgentTemplateDetail(BaseModel):
    """Full manifest plus file manifest for detail endpoints."""

    model_config = ConfigDict(extra="forbid")

    source: AgentTemplateSource
    overlay_path: str | None = None
    manifest: AgentTemplateManifest
    template_files: list[str] = Field(default_factory=list)


class AgentPreviewResult(BaseModel):
    """Rendered preview for one vendor artifact."""

    model_config = ConfigDict(extra="forbid")

    template_id: str
    vendor: str
    filename: str
    content: str
    source: AgentTemplateSource


class AgentOverlayInitMode(str, Enum):
    """How much of a bundled template to copy into a workspace overlay."""

    MINIMAL = "minimal"
    FULL = "full"


class AgentOverlayScope(str, Enum):
    """Whether an overlay is team-committed or personal/local."""

    COMMITTED = "committed"
    LOCAL = "local"


class AgentOverlayInitResult(BaseModel):
    """Summary of files scaffolded into a workspace overlay."""

    model_config = ConfigDict(extra="forbid")

    template_id: str
    overlay_path: str
    scope: AgentOverlayScope
    mode: AgentOverlayInitMode
    paths: list[str] = Field(default_factory=list)
    dry_run: bool = False


class AgentDispatchInstall(BaseModel):
    """Whether a vendor artifact must be installed before dispatch."""

    model_config = ConfigDict(extra="forbid")

    needed: bool
    path: str
    command: str


class AgentDispatchHandoff(BaseModel):
    """CLI commands and instructions for subagent handoff."""

    model_config = ConfigDict(extra="forbid")

    context_pack: str
    prompt: str
    prompt_kind: str
    prompt_scope: Literal["workspace", "project", "repo"]
    effective_instructions: str = ""
    mcp_resources: list[str] = Field(default_factory=list)


class AgentDispatchPlan(BaseModel):
    """Machine-readable dispatch envelope for overseer orchestration."""

    model_config = ConfigDict(extra="forbid")

    template_id: str
    vendor: str
    scope: Literal["project", "user"] = "project"
    project: str | None = None
    repo: str | None = None
    task: str | None = None
    install: AgentDispatchInstall
    launch: dict[str, str] = Field(default_factory=dict)
    handoff: AgentDispatchHandoff
    out_of_scope: list[str] = Field(default_factory=list)
    delegates_to: list[str] = Field(default_factory=list)
    mcp_tools: list[str] = Field(default_factory=list)
    recommended_skills: list[str] = Field(default_factory=list)
