#!/usr/bin/env python
"""Parse compact work-item selectors and Azure DevOps URLs."""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

from metagit.core.workitem.models import ExternalWorkRef, WorkItemProvider

_PROVIDER_PREFIX = re.compile(
    r"^(azure_devops|github|gitlab|jira|linear|other):(.+)$",
    re.IGNORECASE,
)
_ADO_EDIT = re.compile(
    r"/_workitems/edit/(\d+)",
    re.IGNORECASE,
)
_GITHUB_ISSUE = re.compile(
    r"^/([^/]+)/([^/]+)/issues/(\d+)/?$",
    re.IGNORECASE,
)


def parse_work_item_ref(
    value: str,
    *,
    url: Optional[str] = None,
    organization: Optional[str] = None,
    project: Optional[str] = None,
    kind: Optional[str] = None,
    default_provider: WorkItemProvider = "azure_devops",
) -> ExternalWorkRef:
    """Parse ``provider:id`` or a well-known work-item URL into a ref."""
    stripped = value.strip()
    if not stripped:
        raise ValueError("work item ref is required")

    prefixed = _PROVIDER_PREFIX.match(stripped)
    if prefixed:
        provider = prefixed.group(1).lower()
        identifier = prefixed.group(2).strip()
        if provider not in {
            "azure_devops",
            "github",
            "gitlab",
            "jira",
            "linear",
            "other",
        }:
            raise ValueError(f"unsupported work item provider: {provider!r}")
        return ExternalWorkRef(
            provider=provider,  # type: ignore[arg-type]
            id=identifier,
            url=url,
            organization=organization,
            project=project,
            kind=kind,
        )

    from_url = _parse_url(stripped)
    if from_url is not None:
        if url:
            from_url.url = url
        if organization:
            from_url.organization = organization
        if project:
            from_url.project = project
        if kind:
            from_url.kind = kind
        return from_url

    return ExternalWorkRef(
        provider=default_provider,
        id=stripped,
        url=url,
        organization=organization,
        project=project,
        kind=kind,
    )


def _parse_url(value: str) -> Optional[ExternalWorkRef]:
    if "://" not in value:
        return None
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""
    ado_match = _ADO_EDIT.search(path)
    if ("dev.azure.com" in host or "visualstudio.com" in host) and ado_match:
        parts = [part for part in path.split("/") if part and part != "_workitems"]
        organization = parts[0] if parts else None
        project = parts[1] if len(parts) > 1 else None
        return ExternalWorkRef(
            provider="azure_devops",
            id=ado_match.group(1),
            url=value,
            organization=organization,
            project=project,
        )
    gh_match = _GITHUB_ISSUE.match(path)
    if "github.com" in host and gh_match:
        return ExternalWorkRef(
            provider="github",
            id=gh_match.group(3),
            url=value,
            organization=gh_match.group(1),
            project=gh_match.group(2),
            kind="Issue",
        )
    return None


__all__ = ["parse_work_item_ref"]
