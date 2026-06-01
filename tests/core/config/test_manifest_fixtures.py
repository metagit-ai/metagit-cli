#!/usr/bin/env python
"""Tests for manifest fixture validation used in qa:prepush."""

from __future__ import annotations

from pathlib import Path

from metagit.core.config.manifest_fixtures import (
    ManifestFixture,
    ManifestFixtureSet,
    load_fixture_set,
    validate_manifest_fixture,
    validate_manifest_fixtures,
)


def test_load_fixture_set_reads_yaml(tmp_path: Path) -> None:
    fixture_file = tmp_path / "manifest-fixtures.yml"
    fixture_file.write_text(
        "fixtures:\n  - path: .metagit.yml\n    label: root\n",
        encoding="utf-8",
    )
    loaded = load_fixture_set(fixture_file)
    assert isinstance(loaded, ManifestFixtureSet)
    assert loaded.fixtures[0].path == ".metagit.yml"
    assert loaded.fixtures[0].label == "root"


def test_validate_manifest_fixture_success(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text("name: demo\n", encoding="utf-8")
    result = validate_manifest_fixture(
        ManifestFixture(path=".metagit.yml"),
        root=tmp_path,
    )
    assert result.ok is True


def test_validate_manifest_fixture_failure(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text("paths:\n  - name: svc\n    kind: service\n", encoding="utf-8")
    result = validate_manifest_fixture(
        ManifestFixture(path=".metagit.yml"),
        root=tmp_path,
    )
    assert result.ok is False
    assert "kind" in result.message


def test_validate_manifest_fixtures_requires_entries(tmp_path: Path) -> None:
    fixture_file = tmp_path / "manifest-fixtures.yml"
    fixture_file.write_text("fixtures: []\n", encoding="utf-8")
    result = validate_manifest_fixtures(root=tmp_path, fixture_file=fixture_file)
    assert isinstance(result, ValueError)


def test_repo_manifest_fixtures_validate() -> None:
    """Guardrail: curated repo manifests must stay schema-valid."""
    results = validate_manifest_fixtures(root=Path.cwd())
    assert not isinstance(results, Exception)
    failures = [item for item in results if not item.ok]
    assert failures == [], failures
