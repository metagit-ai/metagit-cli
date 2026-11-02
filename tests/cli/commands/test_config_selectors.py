#!/usr/bin/env python
"""Name and id selectors for config set, patch, and preview."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from metagit import DEFAULT_CONFIG
from metagit.cli.main import cli
from metagit.core.config.include_writer import split_manifest

MANIFEST = """\
name: umbrella
kind: umbrella
workspace:
  projects:
    - name: billing
      repos:
        - name: api
          description: old
          url: https://github.com/acme/api.git
    - name: other
      repos:
        - name: api
          description: elsewhere
"""

AMBIGUOUS = """\
name: umbrella
kind: umbrella
workspace:
  projects:
    - name: billing
      repos:
        - name: shared
          description: one
        - name: shared
          description: two
"""


def _split(tmp_path: Path) -> Path:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(MANIFEST, encoding="utf-8")
    planned = split_manifest(manifest, by="project", directory=Path(".metagit.d"), dry_run=False)
    assert not isinstance(planned, Exception)
    return manifest


def test_set_by_name_changes_only_that_scalar(tmp_path: Path) -> None:
    manifest = _split(tmp_path)
    fragment = tmp_path / ".metagit.d" / "projects" / "billing.yml"
    before = fragment.read_text(encoding="utf-8")
    root_before = manifest.read_text(encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--config",
            DEFAULT_CONFIG,
            "config",
            "-c",
            str(manifest),
            "set",
            "workspace.projects[name=billing].repos[name=api].description",
            "updated",
        ],
    )
    assert result.exit_code == 0, result.output
    after = fragment.read_text(encoding="utf-8")
    assert "description: updated" in after
    assert "url: https://github.com/acme/api.git" in after

    def _untouched(text: str) -> list[str]:
        return [line for line in text.splitlines() if "description" not in line]

    assert _untouched(before) == _untouched(after)
    assert manifest.read_text(encoding="utf-8") == root_before
    other = tmp_path / ".metagit.d" / "projects" / "other.yml"
    if other.is_file():
        assert "elsewhere" in other.read_text(encoding="utf-8")


def test_ambiguous_selector_lists_matches(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(AMBIGUOUS, encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--config",
            DEFAULT_CONFIG,
            "config",
            "-c",
            str(manifest),
            "set",
            "workspace.projects[name=billing].repos[name=shared].description",
            "nope",
        ],
    )
    assert result.exit_code != 0
    assert "matched more than one entry" in result.output
    assert "[0] shared" in result.output
    assert "[1] shared" in result.output
    assert "Traceback" not in result.output


def test_positional_index_and_preview_selector(tmp_path: Path) -> None:
    manifest = _split(tmp_path)
    runner = CliRunner()
    dotted = runner.invoke(
        cli,
        [
            "--config",
            DEFAULT_CONFIG,
            "config",
            "-c",
            str(manifest),
            "set",
            "workspace.projects.0.repos[0].description",
            "indexed",
        ],
    )
    assert dotted.exit_code == 0, dotted.output
    fragment = (tmp_path / ".metagit.d" / "projects" / "billing.yml").read_text(encoding="utf-8")
    assert "description: indexed" in fragment
    preview = runner.invoke(
        cli,
        [
            "--config",
            DEFAULT_CONFIG,
            "config",
            "-c",
            str(manifest),
            "preview",
            "--op",
            "set",
            "--path",
            "workspace.projects[name=other].repos[name=api].description",
            "--value",
            "previewed",
        ],
    )
    assert preview.exit_code == 0, preview.output
    assert "previewed" in preview.output
