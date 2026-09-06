#!/usr/bin/env python
"""Pydantic models for first-class repository components."""

from __future__ import annotations

from typing import Any, Optional, Union

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from metagit.core.workspace.agent_profile_models import AgentProfile

RECOMMENDED_COMPONENT_KINDS: tuple[str, ...] = (
    "application",
    "service",
    "library",
    "package",
    "infrastructure",
    "worker",
    "cli",
    "plugin",
    "documentation",
    "data",
    "tool",
    "unknown",
)


class ComponentRef(BaseModel):
    """Qualified component dependency reference."""

    model_config = ConfigDict(extra="forbid")

    project: Optional[str] = Field(None, description="Workspace project name")
    repo: Optional[str] = Field(None, description="Repository name")
    component: str = Field(..., description="Component name")


class ComponentCommand(BaseModel):
    """Named executable command declared on a component."""

    model_config = ConfigDict(extra="forbid")

    command: str = Field(..., description="Shell command to run")

    @field_validator("command")
    @classmethod
    def _non_empty_command(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("command must be non-empty")
        return stripped


class Component(BaseModel):
    """Semantic unit inside a repository (or application manifest path)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str = Field(..., description="Stable component name within the repository")
    path: str = Field(..., description="Repository-relative filesystem path")
    description: Optional[str] = Field(None, description="Short description of the component")
    kind: Optional[str] = Field(
        None,
        description=(
            "Architectural kind (open string). Recommended: application, service, "
            "library, package, infrastructure, worker, cli, plugin, documentation, "
            "data, tool, unknown"
        ),
    )
    language: Optional[str] = Field(None, description="Programming language")
    language_version: Optional[str] = Field(None, description="Language version")
    package_manager: Optional[str] = Field(None, description="Package manager")
    frameworks: list[str] = Field(default_factory=list, description="Frameworks used by the component")
    commands: dict[str, Union[str, ComponentCommand]] = Field(
        default_factory=dict,
        description="Optional executable commands (install, lint, test, build, …)",
    )
    depends_on: list[Union[str, ComponentRef]] = Field(
        default_factory=list,
        description="Local component names or qualified ComponentRef objects",
    )
    produces: list[str] = Field(default_factory=list, description="Artifact names this component produces")
    deploys_to: list[str] = Field(default_factory=list, description="Environment or target names")
    skills: list[str] = Field(
        default_factory=list,
        description="Capability tags (not agent_profile.skills install ids)",
    )
    tags: dict[str, str] = Field(default_factory=dict, description="Flat metadata tags")
    agent_instructions: Optional[str] = Field(
        None,
        validation_alias=AliasChoices("agent_instructions", "agent_prompt"),
        description="Optional instructions for agents working in this component",
    )
    agent_profile: Optional[AgentProfile] = Field(
        default=None,
        description="Structured agent posture for this component",
    )

    @field_validator("language_version", mode="before")
    @classmethod
    def _coerce_language_version(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        return str(value)

    @field_validator("commands")
    @classmethod
    def _reject_empty_command_strings(
        cls,
        value: dict[str, Union[str, ComponentCommand]],
    ) -> dict[str, Union[str, ComponentCommand]]:
        for key, item in value.items():
            if isinstance(item, str) and not item.strip():
                raise ValueError(f"commands.{key} must be non-empty")
        return value
