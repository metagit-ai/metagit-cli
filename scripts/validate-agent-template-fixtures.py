#!/usr/bin/env python3
"""Validate bundled agent template fixtures for QA gates."""

from __future__ import annotations

import sys
from pathlib import Path

from metagit.core.agent.catalog import AgentCatalogService
from metagit.core.agent.registry import AgentTemplateRegistry
from metagit.core.utils.yaml_class import yaml


def default_fixture_file(root: Path) -> Path:
    return root / "scripts" / "agent-template-fixtures.yml"


def main() -> int:
    root = Path.cwd()
    fixture_file = default_fixture_file(root)
    loaded = yaml.safe_load(fixture_file.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        print(f"ERROR: invalid fixture file: {fixture_file}", file=sys.stderr)
        return 2
    fixtures = loaded.get("fixtures")
    if not isinstance(fixtures, list):
        print(f"ERROR: fixtures list missing in {fixture_file}", file=sys.stderr)
        return 2

    registry = AgentTemplateRegistry()
    catalog = AgentCatalogService(registry=registry)
    failed = False
    for item in fixtures:
        template_id = item["id"] if isinstance(item, dict) else item
        issues = catalog.validate_all_templates(template_id=str(template_id))
        if issues:
            failed = True
            for issue in issues:
                print(
                    f"FAIL: {template_id} — {issue.message}",
                    file=sys.stderr,
                )
            continue
        print(f"PASS: {template_id}")

    if failed:
        print("Agent template fixture validation failed.", file=sys.stderr)
        return 1

    print(f"All {len(fixtures)} agent template fixture(s) validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
