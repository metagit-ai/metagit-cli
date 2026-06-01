#!/usr/bin/env python3
"""Validate curated .metagit.yml manifest fixtures for QA gates."""

from __future__ import annotations

import sys
from pathlib import Path

from metagit.core.config.manifest_fixtures import (
    default_fixture_file,
    validate_manifest_fixtures,
)


def main() -> int:
    root = Path.cwd()
    fixture_file = default_fixture_file(root)
    results = validate_manifest_fixtures(root=root, fixture_file=fixture_file)
    if isinstance(results, Exception):
        print(f"ERROR: {results}", file=sys.stderr)
        return 2

    failed = False
    for result in results:
        label = f" ({result.label})" if result.label else ""
        if result.ok:
            print(f"PASS: {result.path}{label}")
            continue
        failed = True
        print(f"FAIL: {result.path}{label} — {result.message}", file=sys.stderr)

    if failed:
        print(
            f"Manifest fixture validation failed ({fixture_file}).",
            file=sys.stderr,
        )
        return 1

    print(f"All {len(results)} manifest fixture(s) validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
