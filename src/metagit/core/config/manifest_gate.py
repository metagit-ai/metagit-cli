#!/usr/bin/env python
"""Shared idempotent checks for an existing `.metagit.yml` manifest."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Union

from metagit.core.config.manager import MetagitConfigManager

ManifestGateAction = Literal["create", "exists_valid"]


@dataclass(frozen=True)
class ManifestGateOutcome:
    """Result of evaluating an on-disk manifest before a write."""

    action: ManifestGateAction
    path: Path


@dataclass(frozen=True)
class ManifestGateInvalid:
    """Existing manifest path that failed validation."""

    path: Path
    error: str


ManifestGateResult = Union[ManifestGateOutcome, ManifestGateInvalid, None]


def evaluate_existing_manifest(
    metagit_path: Path,
    *,
    force: bool = False,
) -> ManifestGateResult:
    """
    Decide whether init/detect/bootstrap should write a new manifest.

    Returns:
        ``None`` — file missing or ``force`` is true; caller may write.
        ``ManifestGateOutcome`` — valid file exists; caller should no-op.
        ``ManifestGateInvalid`` — file exists but is invalid.
    """
    if not metagit_path.is_file():
        return None
    if force:
        return None

    manager = MetagitConfigManager(config_path=str(metagit_path))
    loaded = manager.load_config()
    if isinstance(loaded, Exception):
        return ManifestGateInvalid(path=metagit_path, error=str(loaded))
    return ManifestGateOutcome(action="exists_valid", path=metagit_path)


def manifest_gate_error_message(invalid: ManifestGateInvalid) -> str:
    """Human-readable guidance when an existing manifest is invalid."""
    return (
        f".metagit.yml exists but is invalid: {invalid.error}\n"
        "Fix the file manually or re-run with --force to overwrite."
    )
