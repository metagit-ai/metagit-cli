#!/usr/bin/env python
"""
Pydantic models for Metagit MCP layered resources.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from metagit.core.mcp.models import McpActivationState


class ResourceDescriptor(BaseModel):
    """One entry in resources/list."""

    uri: str
    name: str
    description: str = ""
    mime_type: str = "application/json"
    estimated_tokens: int = 0
    gate: Literal["any", "active"] = "active"
    mutates_session: bool = False


class DynamicUriPattern(BaseModel):
    """Documented URI template not enumerated in resources/list."""

    pattern: str
    name: str
    description: str = ""
    mime_type: str = "application/json"
    estimated_tokens: int = 0
    example: str = ""


class ResourceCatalogResult(BaseModel):
    """Payload for metagit://catalog."""

    ok: bool = True
    schema_version: str = "1.0"
    gate_state: McpActivationState
    read_order: list[str] = Field(default_factory=list)
    resources: list[ResourceDescriptor] = Field(default_factory=list)
    dynamic_patterns: list[DynamicUriPattern] = Field(default_factory=list)
    escalation: dict[str, Any] = Field(default_factory=dict)


class ResourceReadResult(BaseModel):
    """Normalized result from a resource read."""

    uri: str
    mime_type: str = "application/json"
    data: Any = None
    text: Optional[str] = None
    error: Optional[str] = None


class ParsedResourceUri(BaseModel):
    """Parsed metagit:// resource URI."""

    raw: str
    scheme: str = "metagit"
    host: str = ""
    path: str = ""
    query: dict[str, str] = Field(default_factory=dict)


class ProjectSummaryResult(BaseModel):
    """Lightweight project scope payload."""

    ok: bool = True
    schema_version: str = "1.0"
    project_name: str
    description: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    protected: bool = False
    repo_count: int = 0
    repos: list[dict[str, Any]] = Field(default_factory=list)
    health_summary: dict[str, int] = Field(default_factory=dict)


class ConfigSummaryResult(BaseModel):
    """Slim manifest view for metagit://workspace/config?view=summary."""

    ok: bool = True
    schema_version: str = "1.0"
    view: Literal["summary"] = "summary"
    name: str
    kind: str
    project_count: int = 0
    repo_count: int = 0
    projects: list[dict[str, Any]] = Field(default_factory=list)


__all__ = [
    "ConfigSummaryResult",
    "DynamicUriPattern",
    "ParsedResourceUri",
    "ProjectSummaryResult",
    "ResourceCatalogResult",
    "ResourceDescriptor",
    "ResourceReadResult",
]
