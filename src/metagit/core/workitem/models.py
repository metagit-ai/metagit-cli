#!/usr/bin/env python
"""Provider-agnostic work item reference bound to campaigns and objectives."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

WorkItemProvider = Literal[
    "azure_devops",
    "github",
    "gitlab",
    "jira",
    "linear",
    "other",
]


class ExternalWorkRef(BaseModel):
    """Pointer to a board/work-item record. Credentials never belong here."""

    provider: WorkItemProvider
    id: str = Field(description="Provider-native id (ADO work item id, GitHub issue number, …)")
    url: Optional[str] = Field(default=None, description="Browser URL for the work item")
    organization: Optional[str] = Field(
        default=None,
        description="ADO organization, GitHub owner, or equivalent namespace",
    )
    project: Optional[str] = Field(
        default=None,
        description="ADO project, GitHub repo, Jira project key, …",
    )
    kind: Optional[str] = Field(
        default=None,
        description="Work item type (Feature, User Story, Bug, Issue, …)",
    )


__all__ = ["ExternalWorkRef", "WorkItemProvider"]
