#!/usr/bin/env python
"""Deterministic Git remote identity used to map MetaGit repos to EverRoom sources."""

from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse


def canonical_git_identity(url: Optional[str]) -> Optional[str]:
    """Return a host/path identity such as ``github.com/org/repo``.

    Local filesystem paths are rejected so workstation clone locations cannot
    be mistaken for stable source identity.
    """
    if url is None:
        return None
    text = str(url).strip()
    if not text:
        return None
    if text.startswith("git+"):
        text = text[4:]
    if "://" not in text and (text.startswith("/") or text.startswith(".")):
        return None
    if text.startswith("file:"):
        return None
    ssh_match = _ssh_identity(text)
    if ssh_match:
        return _strip_git_suffix(ssh_match)
    parsed = urlparse(text)
    if parsed.scheme in {"http", "https", "ssh", "git"} and parsed.netloc:
        host = parsed.netloc.split("@")[-1].lower()
        path = parsed.path.lstrip("/")
        if not path:
            return None
        return _strip_git_suffix(f"{host}/{path}")
    if text.startswith("git@"):
        return _ssh_identity(text)
    return None


def identity_haystack(values: list[Optional[str]]) -> str:
    """Join candidate EverRoom labels into a lowercase match haystack."""
    parts: list[str] = []
    for value in values:
        if not value:
            continue
        parts.append(str(value).strip().lower())
        canonical = canonical_git_identity(value)
        if canonical:
            parts.append(canonical.lower())
    return " ".join(parts)


def identities_match(metagit_identity: Optional[str], haystack: str) -> bool:
    """True when a MetaGit canonical identity appears in EverRoom source text."""
    if not metagit_identity or not haystack:
        return False
    needle = metagit_identity.strip().lower()
    if not needle or "/" not in needle:
        return False
    return needle in haystack.lower()


def _ssh_identity(text: str) -> Optional[str]:
    if not text.startswith("git@"):
        return None
    rest = text[4:]
    if ":" not in rest:
        return None
    host, path = rest.split(":", 1)
    host = host.strip().lower()
    path = path.lstrip("/")
    if not host or not path:
        return None
    return _strip_git_suffix(f"{host}/{path}")


def _strip_git_suffix(value: str) -> str:
    cleaned = value.rstrip("/")
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]
    return cleaned
