#!/usr/bin/env python
"""
Canonical repository identity helpers.

Identity is provider-qualified (``github://org/repo``) and must not depend on a
mutable local filesystem path.
"""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

from metagit.core.utils.common import normalize_git_url

GITHUB_IDENTITY_PREFIX = "github://"
_GITHUB_PATH_RE = re.compile(r"^/?([^/]+)/([^/]+?)(?:\.git)?/?$")


def github_identity(organization: str, repository: str) -> str:
    """Return the canonical GitHub identity for an org/repo pair."""
    org = organization.strip().lower()
    name = repository.strip().lower()
    if not org or not name:
        raise ValueError("GitHub identity requires organization and repository")
    return f"{GITHUB_IDENTITY_PREFIX}{org}/{name}"


def parse_github_identity(value: str) -> Optional[tuple[str, str]]:
    """Parse ``github://org/repo`` into ``(org, repo)``."""
    text = value.strip()
    if not text.lower().startswith(GITHUB_IDENTITY_PREFIX):
        return None
    body = text[len(GITHUB_IDENTITY_PREFIX) :]
    match = _GITHUB_PATH_RE.match(body)
    if match is None:
        return None
    return match.group(1).lower(), match.group(2).lower()


def identity_from_git_url(url: str | None) -> Optional[str]:
    """Derive a canonical identity from a git remote URL when possible."""
    if not url:
        return None
    normalized = normalize_git_url(str(url))
    if not normalized:
        return None
    lowered = normalized.lower()
    if lowered.startswith("git@github.com:"):
        path = normalized.split(":", 1)[1]
        match = _GITHUB_PATH_RE.match(path)
        if match is None:
            return None
        return github_identity(match.group(1), match.group(2))
    parsed = urlparse(normalized if "://" in normalized else f"https://{normalized}")
    host = (parsed.hostname or "").lower()
    if host in {"github.com", "www.github.com"} or host.endswith(".github.com"):
        match = _GITHUB_PATH_RE.match(parsed.path)
        if match is None:
            return None
        return github_identity(match.group(1), match.group(2))
    return None


def parse_repository_ref(value: str) -> dict[str, str]:
    """
    Normalize a user-supplied repository identifier.

    Accepts ``github://org/repo``, ``org/repo``, or a bare repo name.
    """
    text = value.strip()
    parsed = parse_github_identity(text)
    if parsed is not None:
        organization, name = parsed
        return {
            "identity": github_identity(organization, name),
            "organization": organization,
            "name": name,
        }
    if "/" in text and not text.startswith("."):
        owner, name = text.split("/", 1)
        if owner and name and "/" not in name:
            identity = github_identity(owner, name)
            return {"identity": identity, "organization": owner.lower(), "name": name.lower()}
    return {"name": text.lower()}
