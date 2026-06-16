#!/usr/bin/env python
"""
Filter pipeline for provider-backed repository discovery.
"""

from __future__ import annotations

import fnmatch

from metagit.core.project.source_models import DiscoveredRepo, SourceSpec


def _visibility_matches(repo: DiscoveredRepo, visibility: str) -> bool:
    if visibility == "any":
        return True
    if visibility == "public":
        return repo.private is False
    if visibility == "private":
        return repo.private is True
    if visibility == "internal":
        return repo.private is True
    return True


def apply_source_filters(
    spec: SourceSpec, repos: list[DiscoveredRepo]
) -> list[DiscoveredRepo]:
    """Apply include/ignore and legacy discovery filters to discovered repos."""
    result = list(repos)

    if spec.include_patterns:
        result = [
            repo
            for repo in result
            if any(
                fnmatch.fnmatch(repo.full_name, pattern)
                for pattern in spec.include_patterns
            )
        ]

    if spec.ignore_patterns:
        result = [
            repo
            for repo in result
            if not any(
                fnmatch.fnmatch(repo.full_name, pattern)
                for pattern in spec.ignore_patterns
            )
        ]

    if not spec.include_archived:
        result = [repo for repo in result if not repo.archived]

    if not spec.include_forks:
        result = [repo for repo in result if not repo.fork]

    if spec.path_prefix:
        result = [
            repo for repo in result if repo.full_name.startswith(spec.path_prefix)
        ]

    if spec.visibility != "any":
        result = [repo for repo in result if _visibility_matches(repo, spec.visibility)]

    if spec.ignore_languages:
        blocked = {language.lower() for language in spec.ignore_languages}
        result = [
            repo for repo in result if (repo.language or "").lower() not in blocked
        ]

    return result
