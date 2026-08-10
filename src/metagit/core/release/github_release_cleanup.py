#!/usr/bin/env python
"""Helpers for selecting GitHub releases to prune safely."""

from __future__ import annotations

import re
from dataclasses import dataclass

_SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[-+][0-9A-Za-z.-]+)?$")


@dataclass(frozen=True)
class GitHubReleaseRecord:
    """Minimal release fields used for cleanup planning."""

    release_id: int
    tag_name: str
    draft: bool = False
    prerelease: bool = False
    published_at: str = ""


def parse_tag_semver(tag_name: str) -> tuple[int, int, int] | None:
    """Parse a semver-like tag, supporting optional `v` prefix."""
    match = _SEMVER_RE.fullmatch(tag_name.strip())
    if match is None:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def parse_min_keep_version(version: str) -> tuple[int, int, int]:
    parsed = parse_tag_semver(version)
    if parsed is None:
        raise ValueError("--min-keep-version must be a semver value like 0.8.0 or v0.8.0")
    return parsed


def select_releases_for_prune(
    releases: list[GitHubReleaseRecord],
    *,
    min_keep_version: str,
    keep_latest: int,
    include_draft: bool,
    include_prerelease: bool,
    delete_non_semver: bool,
    keep_tag_regexes: tuple[re.Pattern[str], ...],
) -> list[GitHubReleaseRecord]:
    """Return releases that should be pruned under the configured policy."""
    floor = parse_min_keep_version(min_keep_version)

    eligible: list[GitHubReleaseRecord] = []
    for release in releases:
        if release.draft and not include_draft:
            continue
        if release.prerelease and not include_prerelease:
            continue
        if any(regex.search(release.tag_name) for regex in keep_tag_regexes):
            continue
        eligible.append(release)

    semver_ordered = sorted(
        (
            (release, parse_tag_semver(release.tag_name))
            for release in eligible
            if parse_tag_semver(release.tag_name) is not None
        ),
        key=lambda item: (item[1][0], item[1][1], item[1][2]),
        reverse=True,
    )

    keep_ids = {release.release_id for release, _ in semver_ordered[: max(0, keep_latest)]}

    candidates: list[GitHubReleaseRecord] = []
    for release in eligible:
        if release.release_id in keep_ids:
            continue

        parsed = parse_tag_semver(release.tag_name)
        if parsed is None:
            if delete_non_semver:
                candidates.append(release)
            continue

        if parsed < floor:
            candidates.append(release)

    return candidates
