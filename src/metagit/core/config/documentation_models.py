#!/usr/bin/env python
"""
Documentation source models for .metagit.yml knowledge-graph ingestion.
"""

from __future__ import annotations

from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _looks_like_url(value: str) -> bool:
    trimmed = value.strip().lower()
    return trimmed.startswith("http://") or trimmed.startswith("https://")


def normalize_documentation_entries(
    value: object,
) -> Optional[list[dict[str, Any]]]:
    """
    Accept documentation as strings or dicts; normalize to DocumentationSource dicts.

    - Bare strings: markdown path or web URL (inferred from prefix).
    - Dicts: explicit kind/path/url/tags/metadata for graph pipelines.
    """
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError("documentation must be a list")
    normalized: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, str):
            trimmed = item.strip()
            if not trimmed:
                continue
            if _looks_like_url(trimmed):
                normalized.append({"kind": "web", "url": trimmed})
            else:
                normalized.append({"kind": "markdown", "path": trimmed})
            continue
        if isinstance(item, dict):
            normalized.append(dict(item))
            continue
        raise ValueError(
            "documentation entries must be strings or objects with kind/path/url"
        )
    return normalized


class DocumentationSource(BaseModel):
    """One documentation source for agents and knowledge-graph ingestion."""

    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    kind: str = Field(
        ...,
        description=(
            "Source type (markdown, web, confluence, sharepoint, wiki, api, other)"
        ),
    )
    path: Optional[str] = Field(
        None,
        description="Repo-relative or absolute path to a documentation file",
    )
    url: Optional[str] = Field(None, description="Remote documentation URL")
    title: Optional[str] = Field(None, description="Human-readable title")
    description: Optional[str] = Field(
        None,
        description="Short summary for indexing and graph nodes",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Flat metadata tags for filtering and graph edges",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible key-value payload for downstream graph ingestors",
    )

    @field_validator("kind", mode="before")
    @classmethod
    def _normalize_kind(cls, value: object) -> str:
        if value is None:
            raise ValueError("documentation kind is required")
        return str(value).strip().lower()

    @field_validator("tags", mode="before")
    @classmethod
    def _normalize_tags(cls, value: object) -> dict[str, str]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return {str(key): str(item) for key, item in value.items()}
        if isinstance(value, list):
            return {str(item): "true" for item in value}
        raise ValueError("documentation tags must be a list of strings or a map")

    @model_validator(mode="after")
    def _require_path_or_url(self) -> DocumentationSource:
        if not self.path and not self.url:
            raise ValueError("documentation source requires path or url")
        return self

    def graph_node_payload(self) -> dict[str, Any]:
        """Serialize for knowledge-graph or export pipelines."""
        payload: dict[str, Any] = {
            "kind": self.kind,
            "tags": dict(self.tags),
            "metadata": dict(self.metadata),
        }
        if self.path:
            payload["path"] = self.path
        if self.url:
            payload["url"] = str(self.url)
        if self.title:
            payload["title"] = self.title
        if self.description:
            payload["description"] = self.description
        return payload


DocumentationEntry = Union[str, DocumentationSource]
