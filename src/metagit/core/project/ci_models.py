#!/usr/bin/env python
"""Durable CI topology metadata for managed workspace repositories."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class CiProvider(str, Enum):
    """CI platform that owns pipeline execution for a repository."""

    GITHUB = "github"
    GITLAB = "gitlab"
    AZURE_DEVOPS = "azure_devops"
    OTHER = "other"
    NONE = "none"
    UNKNOWN = "unknown"


class CiTargetStatus(str, Enum):
    """Lifecycle of a resolved CI target binding."""

    DETECTED = "detected"
    DECLARED = "declared"
    OVERRIDDEN = "overridden"


class RepoCiTarget(BaseModel):
    """Where CI/CD lives for a managed repository (agent-facing topology)."""

    provider: CiProvider = Field(..., description="CI platform identifier")
    config_paths: List[str] = Field(
        default_factory=list,
        description="Repo-relative CI configuration file paths",
    )
    host: Optional[str] = Field(
        None,
        description="API or web host (e.g. dev.azure.com or self-hosted ADO)",
    )
    organization: Optional[str] = Field(
        None,
        description="Azure DevOps organization",
    )
    project: Optional[str] = Field(
        None,
        description="Azure DevOps project (may differ from git project)",
    )
    repository: Optional[str] = Field(
        None,
        description="Azure DevOps repository name",
    )
    definition_ids: List[Union[str, int]] = Field(
        default_factory=list,
        description="Optional ADO pipeline/build definition ids for overrides",
    )
    owner: Optional[str] = Field(None, description="GitHub owner/org")
    name: Optional[str] = Field(None, description="GitHub repository name")
    project_path: Optional[str] = Field(
        None,
        description="GitLab project path with namespace",
    )
    status: CiTargetStatus = Field(
        CiTargetStatus.DETECTED,
        description="detected from files/remote; declared or overridden by humans/agents",
    )
    updated_at: Optional[str] = Field(
        None,
        description="ISO-8601 timestamp of last detect or explicit set",
    )

    @field_validator("config_paths", mode="before")
    @classmethod
    def _normalize_config_paths(cls, value: object) -> List[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("config_paths must be a list of strings")
        return [str(item).strip() for item in value if str(item).strip()]

    @field_validator("definition_ids", mode="before")
    @classmethod
    def _normalize_definition_ids(cls, value: object) -> List[Union[str, int]]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("definition_ids must be a list")
        out: List[Union[str, int]] = []
        for item in value:
            if isinstance(item, bool):
                raise ValueError("definition_ids entries must be str or int")
            if isinstance(item, int):
                out.append(item)
            else:
                text = str(item).strip()
                if text:
                    out.append(text)
        return out

    def is_empty(self) -> bool:
        """True when the binding carries no useful topology for agents."""
        provider = self.provider.value if isinstance(self.provider, CiProvider) else str(self.provider)
        if provider in {CiProvider.NONE.value, CiProvider.UNKNOWN.value} and not self.config_paths:
            return not any(
                [
                    self.organization,
                    self.project,
                    self.repository,
                    self.owner,
                    self.name,
                    self.project_path,
                    self.definition_ids,
                    self.host,
                ]
            )
        return False

    def summary_dict(self) -> dict[str, object]:
        """Compact JSON-friendly summary for repo cards and packs."""
        provider = self.provider.value if isinstance(self.provider, CiProvider) else self.provider
        status = self.status.value if isinstance(self.status, CiTargetStatus) else self.status
        payload: dict[str, object] = {
            "provider": provider,
            "config_paths": list(self.config_paths),
            "status": status,
        }
        if self.host:
            payload["host"] = self.host
        if self.organization:
            payload["organization"] = self.organization
        if self.project:
            payload["project"] = self.project
        if self.repository:
            payload["repository"] = self.repository
        if self.definition_ids:
            payload["definition_ids"] = list(self.definition_ids)
        if self.owner:
            payload["owner"] = self.owner
        if self.name:
            payload["name"] = self.name
        if self.project_path:
            payload["project_path"] = self.project_path
        if self.updated_at:
            payload["updated_at"] = self.updated_at
        return payload

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"


__all__ = ["CiProvider", "CiTargetStatus", "RepoCiTarget"]
