#!/usr/bin/env python
"""
Pydantic models for project configuration.
"""

import re
from enum import Enum
from typing import Any, List, Optional, Union

from pydantic import BaseModel, Field, HttpUrl, field_serializer, field_validator
from pydantic_core import core_schema


class GitUrl(str):
    """Custom type for Git repository URLs."""

    GIT_URL_REGEX = re.compile(
        r"((git|ssh|http(s)?)|(git@[\w\.-]+))(:(//)?)([\w\.@\:/\-~]+)(\.git)?(/)?"
    )

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: Any
    ) -> core_schema.CoreSchema:
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.with_info_plain_validator_function(cls.validate),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x)
            ),
        )

    @classmethod
    def validate(cls, value: str, _: Any) -> "GitUrl":
        if not isinstance(value, str) or not cls.GIT_URL_REGEX.match(value):
            raise ValueError("Invalid Git repository URL format")
        return cls(value)


class ProjectKind(str, Enum):
    """Enumeration of project kinds."""

    MONOREPO = "monorepo"
    UMBRELLA = "umbrella"
    APPLICATION = "application"
    GITOPS = "gitops"
    INFRASTRUCTURE = "infrastructure"
    SERVICE = "service"
    LIBRARY = "library"
    WEBSITE = "website"
    OTHER = "other"
    DOCKER_IMAGE = "docker_image"
    REPOSITORY = "repository"
    CLI = "cli"


class ProjectPath(BaseModel):
    """Model for project path, dependency, component, or workspace project information."""

    name: str = Field(..., description="Friendly name for the path or project")
    description: Optional[str] = Field(
        None, description="Short description of the path or project"
    )
    kind: Optional[ProjectKind] = Field(None, description="Project kind")
    ref: Optional[str] = Field(
        None,
        description="Reference in the current project for the target project, used in dependencies",
    )
    path: Optional[str] = Field(None, description="Project path")
    branches: Optional[List[str]] = Field(None, description="Project branches")
    url: Optional[Union[HttpUrl, GitUrl]] = Field(None, description="Project URL")
    sync: Optional[bool] = Field(None, description="Sync setting")
    language: Optional[str] = Field(None, description="Programming language")
    language_version: Optional[Union[str, float, int]] = Field(
        None, description="Language version"
    )
    package_manager: Optional[str] = Field(
        None, description="Package manager used by the project"
    )
    frameworks: Optional[List[str]] = Field(
        None, description="Frameworks used by the project"
    )

    @field_validator("language_version", mode="before")
    def validate_language_version(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        return str(v)

    @field_serializer("url")
    def serialize_url(
        self, url: Optional[Union[HttpUrl, GitUrl]], _info: Any
    ) -> Optional[str]:
        """Serialize the URL to a string."""
        return str(url) if url else None

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"
