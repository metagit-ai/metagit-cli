#!/usr/bin/env python
"""Validate a curated set of local .metagit.yml manifest fixtures."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.utils.yaml_class import yaml


class ManifestFixture(BaseModel):
    """Single manifest file included in the representative validation set."""

    path: str = Field(..., description="Manifest path relative to repository root")
    label: str | None = Field(
        default=None,
        description="Human-readable note for logs and failure output",
    )


class ManifestFixtureSet(BaseModel):
    """Curated manifest paths validated during QA gates."""

    fixtures: list[ManifestFixture] = Field(default_factory=list)


class ManifestFixtureResult(BaseModel):
    """Outcome of validating one manifest fixture."""

    path: str
    label: str | None = None
    ok: bool
    message: str


def default_fixture_file(root: Path | None = None) -> Path:
    """Return the default manifest fixture list path under the repo root."""
    base = root or Path.cwd()
    return (base / "scripts" / "manifest-fixtures.yml").resolve()


def load_fixture_set(fixture_file: Path) -> ManifestFixtureSet | Exception:
    """Load fixture definitions from YAML."""
    try:
        if not fixture_file.is_file():
            return FileNotFoundError(f"Manifest fixture file not found: {fixture_file}")
        payload = yaml.safe_load(fixture_file.read_text(encoding="utf-8"))
        if payload is None:
            return ManifestFixtureSet(fixtures=[])
        return ManifestFixtureSet.model_validate(payload)
    except Exception as exc:
        return exc


def validate_manifest_fixture(
    fixture: ManifestFixture,
    *,
    root: Path,
) -> ManifestFixtureResult:
    """Validate one manifest path relative to root."""
    resolved = Path(os.path.join(str(root), fixture.path)).resolve()
    manager = MetagitConfigManager(config_path=str(resolved))
    loaded = manager.load_config()
    if isinstance(loaded, Exception):
        return ManifestFixtureResult(
            path=fixture.path,
            label=fixture.label,
            ok=False,
            message=str(loaded),
        )
    return ManifestFixtureResult(
        path=fixture.path,
        label=fixture.label,
        ok=True,
        message="valid",
    )


def validate_manifest_fixtures(
    *,
    root: Path | None = None,
    fixture_file: Path | None = None,
) -> list[ManifestFixtureResult] | Exception:
    """Validate every manifest listed in the fixture file."""
    repo_root = (root or Path.cwd()).resolve()
    target_file = (fixture_file or default_fixture_file(repo_root)).resolve()
    fixture_set = load_fixture_set(target_file)
    if isinstance(fixture_set, Exception):
        return fixture_set
    if not fixture_set.fixtures:
        return ValueError(f"No manifest fixtures listed in {target_file}")
    return [validate_manifest_fixture(fixture, root=repo_root) for fixture in fixture_set.fixtures]
