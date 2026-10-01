#!/usr/bin/env python
"""Branch name rendering and prefix checks for ACL allocations."""

from __future__ import annotations

import re

DEFAULT_BRANCH_PATTERN = "agent/{task_id}[-{slug}]"
DEFAULT_ALLOWED_BRANCH_PREFIXES = ["agent/"]

_OPTIONAL_SEGMENT = re.compile(r"\[([^\[\]]*)\]")


def render_branch_name(pattern: str, *, task_id: str, slug: str | None) -> str:
    """Render ``pattern`` with ``{task_id}`` and an optional ``{slug}``.

    Square-bracket groups are included only when ``slug`` is non-empty.
    ``agent/{task_id}[-{slug}]`` therefore stays ``agent/<task>`` when no
    description is given.
    """

    def _optional(match: re.Match[str]) -> str:
        if not slug:
            return ""
        return match.group(1).replace("{slug}", slug)

    rendered = _OPTIONAL_SEGMENT.sub(_optional, pattern)
    rendered = rendered.replace("{task_id}", task_id.strip())
    rendered = rendered.replace("{slug}", slug or "")
    return rendered


def branch_name_allowed(name: str, prefixes: list[str]) -> bool:
    """Return True when ``name`` starts with one of ``prefixes``."""
    return any(bool(prefix) and name.startswith(prefix) for prefix in prefixes)


def branch_prefix_refusal(name: str, prefixes: list[str]) -> str:
    """Refusal that names the config key which overrides it."""
    shown = ", ".join(repr(prefix) for prefix in prefixes) or "(none)"
    return (
        f"branch name {name!r} does not start with an allowed prefix ({shown}). "
        "Set coordination.allowed_branch_prefixes to allow it."
    )


__all__ = [
    "DEFAULT_ALLOWED_BRANCH_PREFIXES",
    "DEFAULT_BRANCH_PATTERN",
    "branch_name_allowed",
    "branch_prefix_refusal",
    "render_branch_name",
]
