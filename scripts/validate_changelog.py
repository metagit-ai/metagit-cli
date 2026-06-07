#!/usr/bin/env python3
"""Fail QA/CI when product code changes without a CHANGELOG.md update."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from metagit.core.release.changelog_ops import (
    git_changed_paths,
    validate_changelog_update,
)


def main() -> int:
    if os.getenv("SKIP_CHANGELOG_CHECK", "").strip().lower() in {"1", "true", "yes"}:
        print("SKIP: changelog_check (SKIP_CHANGELOG_CHECK is set)")
        return 0

    if not Path("CHANGELOG.md").exists():
        print("ERROR: CHANGELOG.md is missing", file=sys.stderr)
        return 2

    changed = git_changed_paths()
    if changed is None:
        print("SKIP: changelog_check (git metadata unavailable)")
        return 0

    result = validate_changelog_update(changed)
    if result.ok:
        print(f"PASS: changelog_check — {result.message}")
        return 0

    print(f"FAIL: changelog_check — {result.message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
