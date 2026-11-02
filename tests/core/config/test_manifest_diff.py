#!/usr/bin/env python
"""config diff, content hash, and split fidelity."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from click.testing import CliRunner

from metagit import DEFAULT_CONFIG
from metagit.cli.main import cli
from metagit.core.config.include_writer import flatten_manifest, split_manifest
from metagit.core.config.manifest_diff import ManifestDifference, content_sha256, diff_manifests, diff_values
from tests.core.config.test_raw_flatten import FIDELITY


def _git(path: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True, text=True)


def test_raw_diff_of_split_form_is_empty(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(FIDELITY, encoding="utf-8")
    original = tmp_path / "original.yml"
    original.write_text(FIDELITY, encoding="utf-8")
    assert not isinstance(split_manifest(manifest, by="all", directory=Path(".metagit.d"), dry_run=False), Exception)
    assert diff_manifests(str(original), str(manifest), mode="raw", cwd=tmp_path) == []


def test_content_sha256_is_stable_across_split_and_flatten(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(FIDELITY, encoding="utf-8")
    before = content_sha256(manifest)
    assert not isinstance(split_manifest(manifest, by="all", directory=Path(".metagit.d"), dry_run=False), Exception)
    assert content_sha256(manifest) == before
    rendered = flatten_manifest(manifest, in_place=True)
    assert isinstance(rendered, str)
    assert content_sha256(manifest) == before


def test_diff_classifies_value_and_whitespace() -> None:
    left = {"name": "demo", "description": "alpha"}
    right = {"name": "other", "description": "alpha\n"}
    kinds = {item.path: item.kind for item in diff_values(left, right)}
    assert kinds["name"] == "value"
    assert kinds["description"] == "whitespace-only"


def test_split_aborts_before_writing_when_fidelity_fails(tmp_path: Path, monkeypatch) -> None:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text("name: demo\nkind: application\n", encoding="utf-8")
    original = manifest.read_bytes()

    def _fake_diff(_left: Path, _right: Path) -> list[ManifestDifference]:
        return [ManifestDifference("name", "value")]

    monkeypatch.setattr("metagit.core.config.manifest_diff.composed_diff", _fake_diff)
    outcome = split_manifest(manifest, by="all", directory=Path(".metagit.d"), dry_run=True)
    assert isinstance(outcome, Exception)
    assert "name (value)" in str(outcome)
    assert manifest.read_bytes() == original
    assert not (tmp_path / ".metagit.d").exists()


def test_config_diff_cli_and_validate_hash(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(FIDELITY, encoding="utf-8")
    _git(tmp_path, "init")
    _git(tmp_path, "add", ".metagit.yml")
    _git(tmp_path, "-c", "user.email=test@example.com", "-c", "user.name=Test", "commit", "-m", "add")
    runner = CliRunner()
    diff = runner.invoke(
        cli,
        ["--config", DEFAULT_CONFIG, "config", "diff", str(manifest), "HEAD:.metagit.yml", "--raw"],
    )
    assert diff.exit_code == 0, diff.output
    assert "0 differences" in diff.output
    validated = runner.invoke(
        cli,
        ["--config", DEFAULT_CONFIG, "config", "validate", "-c", str(manifest), "--json"],
    )
    assert validated.exit_code == 0, validated.output
    payload = json.loads(validated.output)
    assert payload["content_sha256"] == content_sha256(manifest)
    dry = runner.invoke(
        cli,
        ["--config", DEFAULT_CONFIG, "config", "-c", str(manifest), "split", "--by", "all", "--dry-run"],
    )
    assert dry.exit_code == 0, dry.output
    assert "fidelity: ok" in dry.output
