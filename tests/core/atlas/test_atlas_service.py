#!/usr/bin/env python
"""Unit tests for Atlas service lifecycle operations."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from metagit.core.atlas.paths import (
    capabilities_file,
    generated_dir,
    invariants_dir,
    inventory_file,
    symbols_file,
    verifications_file,
)
from metagit.core.atlas.serialize import dump_yaml, load_yaml
from metagit.core.atlas.service import AtlasService

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "atlas" / "python_toy"


def _copy_toy_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "python_toy"
    shutil.copytree(FIXTURE, repo_root)
    return repo_root


def test_init_then_generate_writes_safe_generated_artifacts(tmp_path: Path) -> None:
    repo_root = _copy_toy_repo(tmp_path)
    service = AtlasService(repo_root)

    assert service.init(repository="local/python-toy").ok
    assert service.generate().ok

    assert inventory_file(repo_root).is_file()
    assert symbols_file(repo_root).is_file()
    assert verifications_file(repo_root).is_file()
    assert ".env" not in inventory_file(repo_root).read_text(encoding="utf-8")


def test_generate_is_byte_stable_without_source_changes(tmp_path: Path) -> None:
    repo_root = _copy_toy_repo(tmp_path)
    service = AtlasService(repo_root)
    assert service.init().ok
    assert service.generate().ok
    first = {path: path.read_bytes() for path in sorted(generated_dir(repo_root).rglob("*.yaml"))}

    assert service.generate().ok

    assert {path: path.read_bytes() for path in first} == first
    inventory = load_yaml(inventory_file(repo_root).read_text(encoding="utf-8"))
    symbols = load_yaml(symbols_file(repo_root).read_text(encoding="utf-8"))
    assert inventory["provenance"]["observedAt"]
    assert all(symbol["observedAt"] for symbol in symbols["symbols"])


def test_validate_detects_dangling_curated_invariant_reference(tmp_path: Path) -> None:
    repo_root = _copy_toy_repo(tmp_path)
    service = AtlasService(repo_root)
    assert service.init().ok
    capabilities_file(repo_root).write_text(
        dump_yaml(
            {
                "entities": [
                    {
                        "apiVersion": "atlas.metagit.dev/v1alpha1",
                        "kind": "Capability",
                        "metadata": {
                            "id": "capability:refund.issue",
                            "name": "Issue refund",
                            "lifecycle": "active",
                            "classification": "internal",
                            "provenance": {"source": "curated"},
                        },
                        "spec": {"invariants": ["invariant:refund.idempotent"]},
                    },
                ],
            },
        ),
        encoding="utf-8",
    )
    invariants_dir(repo_root).mkdir(parents=True, exist_ok=True)
    invariant_path = invariants_dir(repo_root) / "refunds.yaml"
    invariant_path.write_text(
        dump_yaml(
            {
                "entities": [
                    {
                        "apiVersion": "atlas.metagit.dev/v1alpha1",
                        "kind": "Invariant",
                        "metadata": {
                            "id": "invariant:refund.idempotent",
                            "name": "Refund issuance is idempotent",
                            "lifecycle": "active",
                            "classification": "internal",
                            "provenance": {"source": "curated"},
                        },
                        "spec": {},
                    },
                ],
            },
        ),
        encoding="utf-8",
    )

    assert service.validate().ok

    capability_payload = load_yaml(capabilities_file(repo_root).read_text(encoding="utf-8"))
    capability_payload["entities"][0]["spec"]["invariants"] = ["invariant:missing"]
    capabilities_file(repo_root).write_text(dump_yaml(capability_payload), encoding="utf-8")
    validation = service.validate()

    assert not validation.ok
    assert any(issue["code"] == "dangling_ref" for issue in validation.issues)


def test_refresh_reports_changed_path_and_preserves_symbols(tmp_path: Path) -> None:
    repo_root = _copy_toy_repo(tmp_path)
    service = AtlasService(repo_root)
    assert service.init().ok
    assert service.generate().ok
    refunds_path = repo_root / "src" / "toy" / "refunds.py"
    refunds_path.write_text(
        refunds_path.read_text(encoding="utf-8") + "\n# Trigger refresh\n",
        encoding="utf-8",
    )

    stale = service.status()
    assert stale.freshness["generated"] == "stale"
    refreshed = service.refresh(["src/toy/refunds.py"])

    assert refreshed.ok
    assert "src/toy/refunds.py" in (refreshed.invalidation_reason or "")
    persisted_status = service.status()
    assert "src/toy/refunds.py" in (persisted_status.invalidation_reason or "")
    symbols = load_yaml(symbols_file(repo_root).read_text(encoding="utf-8"))
    assert any("RefundService.issue" in item["locator"] for item in symbols["symbols"])


def test_missing_repo_returns_exceptions() -> None:
    service = AtlasService("/not/a/real/atlas-repository")

    assert isinstance(service.init(), Exception)
    assert isinstance(service.generate(), Exception)
    assert isinstance(service.refresh(), Exception)
    assert isinstance(service.validate(), Exception)
    assert isinstance(service.status(), Exception)


def test_status_marks_missing_generated_artifacts(tmp_path: Path) -> None:
    repo_root = _copy_toy_repo(tmp_path)
    service = AtlasService(repo_root)
    assert service.init().ok
    assert service.generate().ok
    symbols_file(repo_root).unlink()

    status = service.status()

    assert not status.generated
    assert status.freshness["generated"] == "missing"


def test_generate_returns_extractor_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = _copy_toy_repo(tmp_path)
    service = AtlasService(repo_root)
    assert service.init().ok
    expected = PermissionError("extractor denied")

    def raise_permission_error(*_: object) -> dict[str, object]:
        raise expected

    monkeypatch.setattr("metagit.core.atlas.service.build_inventory", raise_permission_error)

    assert service.generate() is expected


def test_status_returns_source_fingerprint_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = _copy_toy_repo(tmp_path)
    service = AtlasService(repo_root)
    assert service.init().ok
    assert service.generate().ok
    expected = PermissionError("source traversal denied")

    def raise_permission_error(*_: object) -> object:
        raise expected

    monkeypatch.setattr("metagit.core.atlas.service.iter_repo_files", raise_permission_error)

    assert service.status() is expected
