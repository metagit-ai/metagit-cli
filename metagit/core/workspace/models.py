#!/usr/bin/env python
"""
Pydantic models for .metagit.yml workspace configuration.
"""

from typing import Any, List

from pydantic import BaseModel, Field, field_validator

from metagit.core.project.models import ProjectPath


class WorkspaceProject(BaseModel):
    """Model for workspace project."""

    name: str = Field(..., description="Workspace project name")
    repos: List[ProjectPath] = Field(..., description="Repository list")

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

    projects: List[WorkspaceProject] = Field(..., description="Workspace projects")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
