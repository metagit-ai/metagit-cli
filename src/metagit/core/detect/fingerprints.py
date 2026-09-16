#!/usr/bin/env python
"""
Path-based fingerprint markers shared by local detectors and remote org indexing.

Detectors remain responsible for deep local analysis. This table only maps
repository paths to the same tag vocabulary those detectors already emit.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath


@dataclass(frozen=True)
class FingerprintMarker:
    """A cheap path signal and the detector tags it implies."""

    tag: str
    names: frozenset[str] = frozenset()
    suffixes: frozenset[str] = frozenset()
    directory_prefixes: frozenset[str] = frozenset()


FINGERPRINT_MARKERS: tuple[FingerprintMarker, ...] = (
    FingerprintMarker(tag="docker", names=frozenset({"dockerfile", "dockerfile.dev", "dockerfile.prod"})),
    FingerprintMarker(
        tag="docker",
        names=frozenset({"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}),
    ),
    FingerprintMarker(tag="terraform", suffixes=frozenset({".tf", ".tfvars"})),
    FingerprintMarker(tag="task", names=frozenset({"taskfile.yml", "taskfile.yaml"})),
    FingerprintMarker(tag="make", names=frozenset({"makefile"})),
    FingerprintMarker(
        tag="azure-pipelines",
        names=frozenset({"azure-pipelines.yml", "azure-pipelines.yaml"}),
    ),
    FingerprintMarker(tag="github-actions", directory_prefixes=frozenset({".github/workflows/"})),
    FingerprintMarker(tag="node", names=frozenset({"package.json"})),
    FingerprintMarker(tag="python", names=frozenset({"pyproject.toml", "requirements.txt", "setup.py"})),
    FingerprintMarker(tag="go", names=frozenset({"go.mod"})),
    FingerprintMarker(tag="rust", names=frozenset({"cargo.toml"})),
    FingerprintMarker(tag="dotnet", suffixes=frozenset({".csproj", ".sln"})),
    FingerprintMarker(tag="java", names=frozenset({"pom.xml", "build.gradle", "build.gradle.kts"})),
    FingerprintMarker(tag="codeowners", names=frozenset({"codeowners"})),
    FingerprintMarker(tag="readme", names=frozenset({"readme", "readme.md", "readme.rst"})),
)


def tags_for_paths(paths: list[str]) -> list[str]:
    """Return sorted unique detector tags implied by repository-relative paths."""
    tags: set[str] = set()
    normalized = [_normalize_path(path) for path in paths]
    for marker in FINGERPRINT_MARKERS:
        for path in normalized:
            if _matches_marker(path, marker):
                tags.add(marker.tag)
                break
    return sorted(tags)


def matching_paths(paths: list[str], *, has: str) -> list[str]:
    """Return paths that match a ``--has`` needle (filename, suffix, or tag)."""
    needle = has.strip().lower().lstrip("/")
    if not needle:
        return []
    hits: list[str] = []
    for path in paths:
        normalized = _normalize_path(path)
        name = PurePosixPath(normalized).name
        if needle in {normalized, name}:
            hits.append(path)
            continue
        if needle.startswith("*.") and name.endswith(needle[1:]):
            hits.append(path)
            continue
        if any(_matches_marker(normalized, marker) and marker.tag == needle for marker in FINGERPRINT_MARKERS):
            hits.append(path)
            continue
        if needle in normalized:
            hits.append(path)
    return hits


def _normalize_path(path: str) -> str:
    text = path.replace("\\", "/").lower()
    while text.startswith("./"):
        text = text[2:]
    return text.lstrip("/")


def _matches_marker(path: str, marker: FingerprintMarker) -> bool:
    name = PurePosixPath(path).name
    if name in marker.names:
        return True
    if any(name.endswith(suffix) for suffix in marker.suffixes):
        return True
    return any(path.startswith(prefix) for prefix in marker.directory_prefixes)
