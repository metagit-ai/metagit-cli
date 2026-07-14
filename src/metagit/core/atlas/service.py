#!/usr/bin/env python
"""Atlas lifecycle orchestration for repository-local semantic artifacts."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from metagit.core.atlas.extractors.inventory import build_inventory, iter_repo_files
from metagit.core.atlas.extractors.python_ast import extract_python_symbols
from metagit.core.atlas.extractors.tests_discovery import discover_tests
from metagit.core.atlas.models import (
    AtlasConfig,
    AtlasStatusResult,
    AtlasValidateResult,
)
from metagit.core.atlas.paths import (
    atlas_yaml_path,
    generated_dir,
    inventory_file,
    symbols_file,
    verifications_file,
)
from metagit.core.atlas.serialize import dump_yaml, load_yaml
from metagit.core.atlas.store import AtlasStore
from metagit.core.atlas.validate import validate_config_dict, validate_entities

_FORMAT_VERSION = "v1alpha1"


def _replace_observed_at(payload: Any, observed_at: str) -> Any:
    """Replace volatile extractor timestamps with a reproducible value."""
    if isinstance(payload, dict):
        return {
            key: observed_at if key == "observedAt" else _replace_observed_at(value, observed_at)
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [_replace_observed_at(value, observed_at) for value in payload]
    return payload


def _content_hash(payload: Any) -> str:
    """Return the stable SHA-256 of a YAML-serializable payload."""
    return hashlib.sha256(dump_yaml(payload).encode("utf-8")).hexdigest()


def _source_fingerprint(repo_root: Path) -> str:
    """Hash source paths and bytes while excluding Atlas-generated artifacts."""
    digest = hashlib.sha256()
    for path in iter_repo_files(repo_root):
        relative_path = path.relative_to(repo_root).as_posix()
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


class AtlasService:
    """Create, generate, refresh, validate, and report an Atlas."""

    def __init__(self, repo_root: str | Path) -> None:
        self._repo_root = Path(repo_root)
        self._store = AtlasStore(self._repo_root)

    def init(
        self,
        *,
        repository: str | None = None,
        generate: bool = False,
    ) -> AtlasStatusResult | Exception:
        """Create the Atlas layout without overwriting curated artifacts."""
        root_error = self._require_repo_root()
        if root_error is not None:
            return root_error
        config = AtlasConfig(
            repository=repository or self._repo_root.name,
            formatVersion=_FORMAT_VERSION,
        )
        initialized = self._store.init_layout(config)
        if isinstance(initialized, Exception):
            return initialized
        if generate:
            return self.generate()
        return self.status()

    def generate(self) -> AtlasStatusResult | Exception:
        """Regenerate deterministic evidence artifacts for the repository."""
        return self._generate()

    def refresh(self, paths: list[str] | None = None) -> AtlasStatusResult | Exception:
        """Regenerate evidence and record the paths that invalidated it."""
        reason = (
            f"refreshed after source changes: {', '.join(sorted(paths))}" if paths else "refreshed all Atlas sources"
        )
        return self._generate(invalidation_reason=reason)

    def _generate(self, *, invalidation_reason: str | None = None) -> AtlasStatusResult | Exception:
        """Run the evidence pipeline and persist its deterministic metadata."""
        root_error = self._require_repo_root()
        if root_error is not None:
            return root_error
        config = self._load_or_init_config()
        if isinstance(config, Exception):
            return config

        try:
            revision = self._git_revision()
            observed_at = self._git_observed_at()
            inventory = _replace_observed_at(build_inventory(self._repo_root, revision), observed_at)
            symbols = _replace_observed_at(extract_python_symbols(self._repo_root, revision), observed_at)
            verifications = _replace_observed_at(discover_tests(self._repo_root, revision), observed_at)
            payloads = {
                "inventory.yaml": inventory,
                "symbols.yaml": {
                    "symbols": symbols,
                    "provenance": {
                        "extractor": "python-ast@1.0.0",
                        "observedAt": observed_at,
                        "revision": revision,
                    },
                },
                "verifications.yaml": {
                    "verifications": verifications,
                    "provenance": {
                        "extractor": "tests-discovery@1.0.0",
                        "observedAt": observed_at,
                        "revision": revision,
                    },
                },
            }
            payloads["manifests.yaml"] = {
                "contentHashes": {path: _content_hash(payload) for path, payload in sorted(payloads.items())},
                "invalidationReason": invalidation_reason,
                "revision": revision,
                "sourceFingerprint": _source_fingerprint(self._repo_root),
            }

            written = self._store.write_generated(payloads)
            if isinstance(written, Exception):
                return written
            rebuilt = self._store.rebuild_index()
            if isinstance(rebuilt, Exception):
                return rebuilt
            saved = self._save_config(config.model_copy(update={"sources": {"generated": "fresh"}}))
            if isinstance(saved, Exception):
                return saved
            return self.status()
        except Exception as exc:  # noqa: BLE001
            return exc

    def validate(self) -> AtlasValidateResult | Exception:
        """Validate Atlas configuration and curated cross-entity references."""
        root_error = self._require_repo_root()
        if root_error is not None:
            return root_error
        raw_config = self._load_config_dict()
        if isinstance(raw_config, Exception):
            return raw_config
        config_issues = validate_config_dict(raw_config)
        entities = self._store.load_curated_entities()
        if isinstance(entities, Exception):
            return entities
        issues = [*config_issues, *validate_entities(entities)]
        return AtlasValidateResult(
            ok=not issues,
            issues=[issue.model_dump(mode="json", exclude_none=True) for issue in issues],
        )

    def status(self) -> AtlasStatusResult | Exception:
        """Return the current layout, generation, and freshness state."""
        root_error = self._require_repo_root()
        if root_error is not None:
            return root_error
        config = self._load_config()
        if isinstance(config, Exception):
            return config
        manifest = self._load_manifest()
        if isinstance(manifest, Exception):
            return manifest
        freshness = dict(config.sources or {})
        generated = all(
            path.is_file()
            for path in (
                inventory_file(self._repo_root),
                symbols_file(self._repo_root),
                verifications_file(self._repo_root),
            )
        )
        if not generated:
            freshness["generated"] = "missing"
        stored_fingerprint = manifest.get("sourceFingerprint") if manifest else None
        if generated and isinstance(stored_fingerprint, str):
            try:
                current_fingerprint = _source_fingerprint(self._repo_root)
            except Exception as exc:  # noqa: BLE001
                return exc
            if stored_fingerprint != current_fingerprint:
                freshness["generated"] = "stale"
        return AtlasStatusResult(
            repository=config.repository,
            initialized=atlas_yaml_path(self._repo_root).is_file(),
            generated=generated,
            freshness=freshness,
            invalidation_reason=(
                manifest.get("invalidationReason")
                if isinstance(manifest, dict) and isinstance(manifest.get("invalidationReason"), str)
                else None
            ),
        )

    def _require_repo_root(self) -> Exception | None:
        if self._repo_root.is_dir():
            return None
        return FileNotFoundError(f"Atlas repository root does not exist: {self._repo_root}")

    def _load_or_init_config(self) -> AtlasConfig | Exception:
        if not atlas_yaml_path(self._repo_root).is_file():
            initialized = self.init()
            if isinstance(initialized, Exception):
                return initialized
        return self._load_config()

    def _load_config_dict(self) -> dict[str, Any] | Exception:
        path = atlas_yaml_path(self._repo_root)
        if not path.is_file():
            return FileNotFoundError(f"Atlas config does not exist: {path}")
        try:
            loaded = load_yaml(path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                return ValueError(f"Atlas config must be a YAML mapping: {path}")
            return loaded
        except Exception as exc:  # noqa: BLE001
            return exc

    def _load_config(self) -> AtlasConfig | Exception:
        raw = self._load_config_dict()
        if isinstance(raw, Exception):
            return raw
        try:
            return AtlasConfig.model_validate(raw)
        except ValidationError as exc:
            return exc

    def _save_config(self, config: AtlasConfig) -> None | Exception:
        try:
            atlas_yaml_path(self._repo_root).write_text(
                dump_yaml(config.model_dump(mode="json", exclude_none=True)),
                encoding="utf-8",
            )
            return None
        except Exception as exc:  # noqa: BLE001
            return exc

    def _load_manifest(self) -> dict[str, Any] | Exception | None:
        path = generated_dir(self._repo_root) / "manifests.yaml"
        if not path.is_file():
            return None
        try:
            loaded = load_yaml(path.read_text(encoding="utf-8"))
            return loaded if isinstance(loaded, dict) else ValueError(f"Atlas manifest must be a mapping: {path}")
        except Exception as exc:  # noqa: BLE001
            return exc

    def _git_revision(self) -> str:
        try:
            completed = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self._repo_root,
                check=False,
                capture_output=True,
                text=True,
            )
            revision = completed.stdout.strip()
            return revision if completed.returncode == 0 and revision else "unknown"
        except OSError:
            return "unknown"

    def _git_observed_at(self) -> str:
        try:
            completed = subprocess.run(
                ["git", "show", "-s", "--format=%cI", "HEAD"],
                cwd=self._repo_root,
                check=False,
                capture_output=True,
                text=True,
            )
            observed_at = completed.stdout.strip()
            if completed.returncode == 0 and observed_at:
                return observed_at.replace("+00:00", "Z")
        except OSError:
            pass
        return "1970-01-01T00:00:00Z"


__all__ = [
    "AtlasService",
]
