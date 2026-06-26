#!/usr/bin/env python
"""Pydantic models for metagit init templates."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class InitPromptSpec(BaseModel):
    """One copier-style prompt for template variable collection."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Template variable name")
    label: str = Field(..., description="Human-readable prompt label")
    default: Optional[str] = Field(None, description="Static default value")
    default_from: Optional[Literal["directory_name", "git_remote_url"]] = Field(
        None,
        description="Built-in default resolver when default is not set",
    )
    required: bool = Field(default=True, description="Whether a non-empty value is required")
    secret: bool = Field(default=False, description="Hide input in interactive prompts")


class InitTemplateFileSpec(BaseModel):
    """Rendered file mapping for a template."""

    model_config = ConfigDict(extra="forbid")

    template: str = Field(..., description="Source filename inside the template directory")
    output: str = Field(..., description="Relative output path from init target directory")
    optional: bool = Field(
        default=False,
        description="When true, skip writing if rendered content is empty",
    )


class InitTemplateManifest(BaseModel):
    """Manifest for a bundled init template (copier-style)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Template identifier for --template")
    label: str = Field(..., description="Short label for --list-templates")
    description: str = Field(..., description="Longer description of the template")
    kind: str = Field(..., description="Default MetagitConfig kind for this template")
    prompts: list[InitPromptSpec] = Field(default_factory=list)
    files: list[InitTemplateFileSpec] = Field(default_factory=list)
