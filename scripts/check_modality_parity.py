#!/usr/bin/env python3
"""Validate declared modality parity markers exist in the repository."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "scripts" / "modality-parity.yml"


def _load_registry() -> dict:
    with REGISTRY.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, dict):
        raise ValueError("modality-parity.yml must be a mapping")
    return loaded


def _check_markers(feature_id: str, surface: str, markers: list[dict]) -> list[str]:
    errors: list[str] = []
    for marker in markers:
        rel_path = str(marker.get("path", "")).strip()
        needle = str(marker.get("contains", "")).strip()
        if not rel_path or not needle:
            errors.append(f"{feature_id}.{surface}: marker missing path or contains")
            continue
        target = ROOT / rel_path
        if not target.is_file():
            errors.append(f"{feature_id}.{surface}: missing file {rel_path}")
            continue
        text = target.read_text(encoding="utf-8")
        if needle not in text:
            errors.append(f"{feature_id}.{surface}: {rel_path} missing marker {needle!r}")
    return errors


def main() -> int:
    registry = _load_registry()
    features = registry.get("features")
    if not isinstance(features, list):
        print("ERROR: modality-parity.yml features must be a list", file=sys.stderr)
        return 1

    errors: list[str] = []
    for feature in features:
        if not isinstance(feature, dict):
            errors.append("feature entry must be a mapping")
            continue
        feature_id = str(feature.get("id", "unknown"))
        surfaces = feature.get("surfaces")
        if not isinstance(surfaces, dict):
            errors.append(f"{feature_id}: surfaces must be a mapping")
            continue
        for surface, spec in surfaces.items():
            if not isinstance(spec, dict):
                errors.append(f"{feature_id}.{surface}: expected mapping")
                continue
            markers = spec.get("markers")
            if not isinstance(markers, list):
                errors.append(f"{feature_id}.{surface}: markers must be a list")
                continue
            errors.extend(_check_markers(feature_id, surface, markers))

        reference_doc = str(feature.get("reference_doc", "")).strip()
        doc_surface = surfaces.get("documentation") if isinstance(surfaces, dict) else None
        has_doc_markers = (
            isinstance(doc_surface, dict)
            and isinstance(doc_surface.get("markers"), list)
            and doc_surface.get("markers")
        )
        if reference_doc:
            ref_path = ROOT / reference_doc
            if not ref_path.is_file():
                errors.append(f"{feature_id}: missing reference_doc {reference_doc}")
            elif has_doc_markers and f"modality:{feature_id}" not in ref_path.read_text(encoding="utf-8"):
                errors.append(
                    f"{feature_id}: reference_doc {reference_doc} missing anchor modality:{feature_id}",
                )

    if errors:
        print("Modality parity check failed:", file=sys.stderr)
        for item in errors:
            print(f"  - {item}", file=sys.stderr)
        return 1

    print(f"Modality parity OK ({len(features)} features)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
