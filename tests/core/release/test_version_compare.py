#!/usr/bin/env python
"""Tests for release version comparison helpers."""

from metagit.core.release.version_compare import compare_versions


def test_compare_versions_orders_semver_parts() -> None:
    assert compare_versions("1.2.3", "1.2.4") < 0
    assert compare_versions("2.0.0", "1.9.9") > 0
    assert compare_versions("1.2.3", "1.2.3") == 0


def test_compare_versions_strips_v_prefix() -> None:
    assert compare_versions("v1.0.0", "1.0.1") < 0
    assert compare_versions("1.0.0", "v1.0.0") == 0


def test_compare_versions_handles_prerelease() -> None:
    assert compare_versions("1.0.0", "1.0.0-rc1") > 0
    assert compare_versions("1.0.0-rc2", "1.0.0-rc10") < 0
