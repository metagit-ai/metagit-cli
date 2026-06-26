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


def normalize_documentation_tags(value: object) -> list[str]:
    """
    Normalize documentation tags to a sorted unique list of strings.

    Accepts a list of tag names or a legacy map (``{name: "true"}``).
    Map entries with non-boolean values become ``key=value`` tag strings.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return _dedupe_tag_strings(value)
    if isinstance(value, dict):
        tags: list[str] = []
        for key, item in value.items():
            key_str = str(key).strip()
            if not key_str:
                continue
            val_str = str(item).strip().lower()
            if val_str in ("true", "1", "yes"):
                tags.append(key_str)
            elif val_str in ("false", "0", "no"):
                continue
            elif not val_str:
                tags.append(key_str)
            else:
                tags.append(f"{key_str}={item}")
        return _dedupe_tag_strings(tags)
    raise ValueError("documentation tags must be a list of strings or a map")


def _dedupe_tag_strings(values: object) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    if not isinstance(values, list):
        return ordered
    for raw in values:
        tag = str(raw).strip()
        if not tag or tag in seen:
            continue
        seen.add(tag)
        ordered.append(tag)
    return ordered


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
        raise ValueError("documentation entries must be strings or objects with kind/path/url")
    return normalized


class DocumentationSource(BaseModel):
    """One documentation source for agents and knowledge-graph ingestion."""

    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    kind: str = Field(
        ...,
        description=("Source type (markdown, web, confluence, sharepoint, wiki, api, other)"),
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
    tags: list[str] = Field(
        default_factory=list,
        description="Flat tag labels for filtering and graph edges",
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
    def _normalize_tags(cls, value: object) -> list[str]:
        return normalize_documentation_tags(value)

    @model_validator(mode="after")
    def _require_path_or_url(self) -> DocumentationSource:
        if not self.path and not self.url:
            raise ValueError("documentation source requires path or url")
        return self

    def graph_node_payload(self) -> dict[str, Any]:
        """Serialize for knowledge-graph or export pipelines."""
        payload: dict[str, Any] = {
            "kind": self.kind,
            "tags": list(self.tags),
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


def documentation_entry_identity(entry: DocumentationSource) -> str:
    """Stable deduplication key for a documentation source."""
    if entry.path:
        return f"path:{entry.path.strip()}"
    if entry.url:
        return f"url:{str(entry.url).strip()}"
    return f"kind:{entry.kind}"


def is_documentation_shorthand_eligible(entry: DocumentationSource) -> bool:
    """Return True when a source can be written as a bare path or URL string."""
    if entry.title or entry.description or entry.tags or entry.metadata:
        return False
    if entry.kind == "markdown" and entry.path and not entry.url:
        return True
    return entry.kind == "web" and entry.url is not None and not entry.path


def compact_documentation_entry(
    entry: DocumentationSource,
) -> str | dict[str, Any]:
    """Serialize one documentation entry for formatted YAML output."""
    if is_documentation_shorthand_eligible(entry):
        return entry.path if entry.kind == "markdown" else str(entry.url)
    payload = entry.model_dump(exclude_none=True, mode="json")
    if not payload.get("tags"):
        payload.pop("tags", None)
    if not payload.get("metadata"):
        payload.pop("metadata", None)
    return payload


def _documentation_representation_richness(item: str | dict[str, Any]) -> int:
    if isinstance(item, str):
        return 0
    score = 0
    for key in ("title", "description"):
        if item.get(key):
            score += 2
    if item.get("tags"):
        score += 2
    if item.get("metadata"):
        score += 2
    return score


def _merge_documentation_representations(
    existing: str | dict[str, Any],
    candidate: str | dict[str, Any],
) -> str | dict[str, Any]:
    """Keep the richer duplicate; prefer shorthand when equally simple."""
    existing_score = _documentation_representation_richness(existing)
    candidate_score = _documentation_representation_richness(candidate)
    if candidate_score > existing_score:
        return candidate
    if existing_score > candidate_score:
        return existing
    if isinstance(existing, str):
        return existing
    if isinstance(candidate, str):
        return candidate
    return existing


def compact_documentation_list(
    entries: list[DocumentationSource],
) -> list[str | dict[str, Any]]:
    """Deduplicate and compact documentation entries for formatted YAML."""
    seen: dict[str, str | dict[str, Any]] = {}
    order: list[str] = []
    for entry in entries:
        identity = documentation_entry_identity(entry)
        compact = compact_documentation_entry(entry)
        if identity not in seen:
            seen[identity] = compact
            order.append(identity)
            continue
        seen[identity] = _merge_documentation_representations(
            seen[identity],
            compact,
        )
    return [seen[key] for key in order]
