#!/usr/bin/env python
"""Shared caps that keep large umbrella manifests out of agent context."""

from __future__ import annotations

from typing import Optional, Sequence, TypeVar

from metagit.core.config.models import MetagitConfig

DEFAULT_MAP_REPO_LIMIT = 80
DEFAULT_MAX_CARDS = 50
DEFAULT_DIGEST_REPO_LIMIT = 40
DEFAULT_INDEX_ROW_LIMIT = 80
DEFAULT_PROJECT_SUMMARY_REPO_LIMIT = 80
DEFAULT_CAMPAIGN_STATUS_REPO_LIMIT = 40
DEFAULT_CAMPAIGN_EXPAND_LIMIT = 40
DEFAULT_INSTRUCTION_EXCERPT_CHARS = 500
FULL_MANIFEST_REPO_THRESHOLD = 80
MAP_TOKEN_BUDGET_REPO_CAP = 20
CAMPAIGN_SELECTION_LIMIT = 2000

T = TypeVar("T")


def count_workspace_repos(config: MetagitConfig) -> int:
    """Return the number of managed repos in a workspace manifest."""
    if not config.workspace:
        return 0
    return sum(len(project.repos) for project in config.workspace.projects)


def excerpt_text(
    value: Optional[str],
    *,
    limit: int = DEFAULT_INSTRUCTION_EXCERPT_CHARS,
) -> tuple[Optional[str], bool]:
    """Return ``(text, truncated)`` with a hard character cap."""
    if value is None:
        return None, False
    if limit < 1 or len(value) <= limit:
        return value, False
    return value[:limit], True


def page_rows(
    rows: Sequence[T],
    *,
    limit: Optional[int],
    offset: int = 0,
) -> tuple[list[T], bool]:
    """Return a page of ``rows`` plus whether more remain after this page."""
    start = max(offset, 0)
    if limit is None:
        return list(rows[start:]), False
    if limit < 1:
        return [], start < len(rows)
    sliced = list(rows[start : start + limit])
    truncated = (start + len(sliced)) < len(rows)
    return sliced, truncated


def full_manifest_refused_payload(
    *,
    repo_count: int,
    threshold: int = FULL_MANIFEST_REPO_THRESHOLD,
    hint: str,
) -> dict[str, object]:
    """Structured refusal when an agent asks for a full umbrella dump."""
    return {
        "ok": False,
        "error": "full_manifest_refused",
        "view": "full_refused",
        "repo_count": repo_count,
        "threshold": threshold,
        "hint": hint,
    }


__all__ = [
    "CAMPAIGN_SELECTION_LIMIT",
    "DEFAULT_CAMPAIGN_EXPAND_LIMIT",
    "DEFAULT_CAMPAIGN_STATUS_REPO_LIMIT",
    "DEFAULT_DIGEST_REPO_LIMIT",
    "DEFAULT_INDEX_ROW_LIMIT",
    "DEFAULT_INSTRUCTION_EXCERPT_CHARS",
    "DEFAULT_MAP_REPO_LIMIT",
    "DEFAULT_MAX_CARDS",
    "DEFAULT_PROJECT_SUMMARY_REPO_LIMIT",
    "FULL_MANIFEST_REPO_THRESHOLD",
    "MAP_TOKEN_BUDGET_REPO_CAP",
    "count_workspace_repos",
    "excerpt_text",
    "full_manifest_refused_payload",
    "page_rows",
]
