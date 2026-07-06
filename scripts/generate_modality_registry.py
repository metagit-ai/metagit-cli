#!/usr/bin/env python3
"""Generate docs/reference/modality-feature-registry.md from scripts/modality-parity.yml."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_YAML = ROOT / "scripts" / "modality-parity.yml"
REGISTRY_MD = ROOT / "docs" / "reference" / "modality-feature-registry.md"
START = "<!-- registry:table:start -->"
END = "<!-- registry:table:end -->"
REGISTRY_DOC_DIR = Path("docs/reference")


def _reference_href(reference: str) -> str:
    ref_path = Path(reference)
    if reference.startswith("docs/"):
        return Path(
            os.path.relpath(ref_path, REGISTRY_DOC_DIR),
        ).as_posix()
    return reference


def _load_registry() -> dict:
    with REGISTRY_YAML.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, dict):
        raise ValueError("modality-parity.yml must be a mapping")
    return loaded


def _surface_cell(surfaces: dict, name: str) -> str:
    spec = surfaces.get(name)
    if not isinstance(spec, dict):
        return "—"
    markers = spec.get("markers")
    if isinstance(markers, list) and markers:
        return "yes"
    return "—"


def _build_table(features: list[dict]) -> str:
    lines = [
        "| Feature ID | Description | CLI | MCP | Web | Docs | Skills | Reference |",
        "|------------|-------------|-----|-----|-----|------|--------|-----------|",
    ]
    for feature in features:
        if not isinstance(feature, dict):
            continue
        feature_id = str(feature.get("id", ""))
        description = str(feature.get("description", "")).replace("|", "\\|")
        surfaces = feature.get("surfaces")
        if not isinstance(surfaces, dict):
            surfaces = {}
        reference = str(feature.get("reference_doc", "")).strip()
        ref_cell = f"[{Path(reference).name}]({_reference_href(reference)})" if reference else "—"
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{feature_id}`",
                    description,
                    _surface_cell(surfaces, "cli"),
                    _surface_cell(surfaces, "mcp"),
                    _surface_cell(surfaces, "web"),
                    _surface_cell(surfaces, "documentation"),
                    _surface_cell(surfaces, "skills"),
                    ref_cell,
                ],
            )
            + " |",
        )
    return "\n".join(lines)


def _intro(version: int, feature_count: int) -> str:
    return f"""# Modality & feature registry

Master index of user-facing Metagit capabilities across **CLI**, **MCP**, **Web**, **documentation**, and **bundled skills**.

- **Source of truth:** [`scripts/modality-parity.yml`](../../scripts/modality-parity.yml) (validated in `task qa:prepush`)
- **Registry version:** {version}
- **Features tracked:** {feature_count}

When you add or change a backend feature:

1. Register it in `scripts/modality-parity.yml` (surfaces + `reference_doc`).
2. Add modality anchor comments in docs/skills: `<!-- modality:FEATURE_ID -->`
3. Run `task generate:modality-registry` (or `task generate:schema`) to refresh this table.
4. Run `task qa:prepush`.

See [Agent profile](agent-profile.md), [Campaigns](campaigns.md), and [Metagit agent](metagit-agent.md) for recent agent-native additions.

## Feature matrix

{START}
"""


def main() -> int:
    registry = _load_registry()
    features = registry.get("features")
    if not isinstance(features, list):
        raise ValueError("features must be a list")
    version = int(registry.get("version", 1))
    table = _build_table(features)
    footer = f"""
{END}

## Surface legend

| Column | Meaning |
|--------|---------|
| CLI | `metagit …` command group present |
| MCP | MCP tool registered |
| Web | `metagit web serve` HTTP route or SPA |
| Docs | Narrative reference under `docs/` |
| Skills | Bundled skill playbook under `src/metagit/data/skills/` |

A cell shows **yes** when the feature declares markers for that surface in `modality-parity.yml`. **—** means intentionally CLI-only, not yet built, or documented elsewhere.

## Related

- [For AI agents](../agents.md)
- [Skills catalog](../skills.md)
- [Sharing state (multi-agent)](sharing-state.md)
"""
    body = _intro(version, len(features)) + table + footer
    REGISTRY_MD.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_MD.write_text(body, encoding="utf-8")
    print(f"Wrote {REGISTRY_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
