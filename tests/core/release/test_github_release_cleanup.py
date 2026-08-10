#!/usr/bin/env python
"""Tests for GitHub release cleanup selection helpers."""

from __future__ import annotations

import re

from metagit.core.release.github_release_cleanup import (
    GitHubReleaseRecord,
    parse_min_keep_version,
    parse_tag_semver,
    select_releases_for_prune,
)


def test_parse_tag_semver_supports_v_prefix() -> None:
    assert parse_tag_semver("0.8.1") == (0, 8, 1)
    assert parse_tag_semver("v1.2.3") == (1, 2, 3)
    assert parse_tag_semver("release-1") is None


def test_parse_min_keep_version_rejects_invalid_values() -> None:
    try:
        parse_min_keep_version("main")
    except ValueError as exc:
        assert "--min-keep-version" in str(exc)
    else:  # pragma: no cover - explicit guard
        raise AssertionError("Expected ValueError for invalid semver")


def test_select_releases_prunes_below_floor_but_keeps_latest() -> None:
    releases = [
        GitHubReleaseRecord(release_id=1, tag_name="0.7.5"),
        GitHubReleaseRecord(release_id=2, tag_name="0.8.0"),
        GitHubReleaseRecord(release_id=3, tag_name="0.9.0"),
    ]

    candidates = select_releases_for_prune(
        releases,
        min_keep_version="0.8.0",
        keep_latest=2,
        include_draft=False,
        include_prerelease=False,
        delete_non_semver=False,
        keep_tag_regexes=(),
    )

    assert [item.tag_name for item in candidates] == ["0.7.5"]


def test_select_releases_skips_draft_and_prerelease_by_default() -> None:
    releases = [
        GitHubReleaseRecord(release_id=1, tag_name="0.7.0", draft=True),
        GitHubReleaseRecord(release_id=2, tag_name="0.7.1", prerelease=True),
        GitHubReleaseRecord(release_id=3, tag_name="0.7.2"),
    ]

    candidates = select_releases_for_prune(
        releases,
        min_keep_version="0.8.0",
        keep_latest=0,
        include_draft=False,
        include_prerelease=False,
        delete_non_semver=False,
        keep_tag_regexes=(),
    )

    assert [item.tag_name for item in candidates] == ["0.7.2"]


def test_select_releases_can_prune_non_semver_when_requested() -> None:
    releases = [
        GitHubReleaseRecord(release_id=1, tag_name="legacy-release"),
        GitHubReleaseRecord(release_id=2, tag_name="0.7.9"),
    ]

    candidates = select_releases_for_prune(
        releases,
        min_keep_version="0.8.0",
        keep_latest=0,
        include_draft=True,
        include_prerelease=True,
        delete_non_semver=True,
        keep_tag_regexes=(re.compile(r"^do-not-delete$"),),
    )

    assert {item.tag_name for item in candidates} == {"legacy-release", "0.7.9"}


def test_select_releases_respects_keep_tag_patterns() -> None:
    releases = [
        GitHubReleaseRecord(release_id=1, tag_name="0.7.0"),
        GitHubReleaseRecord(release_id=2, tag_name="0.7.1"),
    ]

    candidates = select_releases_for_prune(
        releases,
        min_keep_version="0.8.0",
        keep_latest=0,
        include_draft=True,
        include_prerelease=True,
        delete_non_semver=False,
        keep_tag_regexes=(re.compile(r"^0\.7\.1$"),),
    )

    assert [item.tag_name for item in candidates] == ["0.7.0"]
