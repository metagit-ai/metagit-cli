#!/usr/bin/env python
"""
Resolve manifest repo names for discovered provider repositories.
"""

from __future__ import annotations

from metagit.core.project.source_models import DiscoveredRepo


def resolve_manifest_names(
    repos: list[DiscoveredRepo],
    *,
    strategy: str,
) -> dict[str, str]:
    """
    Map clone_url -> manifest repo name.

    ``strategy`` is ``short`` (provider short name) or ``namespaced`` (collision-aware).
    """
    if strategy == "short":
        return {repo.clone_url: repo.name for repo in repos}

    assigned: dict[str, str] = {}
    used_names: set[str] = set()

    for repo in repos:
        segments = [segment for segment in repo.full_name.split("/") if segment]
        candidates: list[str] = []
        if segments:
            candidates.append(segments[-1])
        if len(segments) >= 2:
            candidates.append(f"{segments[-2]}-{segments[-1]}")
        if len(segments) >= 3:
            candidates.append(f"{segments[-3]}-{segments[-2]}-{segments[-1]}")

        chosen = repo.name
        for candidate in candidates:
            if candidate not in used_names:
                chosen = candidate
                break
        else:
            base = candidates[-1] if candidates else repo.name
            suffix = 2
            chosen = f"{base}-{suffix}"
            while chosen in used_names:
                suffix += 1
                chosen = f"{base}-{suffix}"

        assigned[repo.clone_url] = chosen
        used_names.add(chosen)

    return assigned
