#!/usr/bin/env python3
"""Promote CHANGELOG.md Unreleased notes for semantic releases."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from metagit.core.release.changelog_ops import (
    CHANGELOG_PATH,
    promote_unreleased,
    write_changelog,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True, help="Release version (e.g. 1.2.3)")
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="Release date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--range",
        default="",
        help="Optional git revision range for commit-note fallback",
    )
    parser.add_argument(
        "--body-out",
        default=None,
        help="Optional path to write GitHub release body markdown",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print release body without modifying CHANGELOG.md",
    )
    args = parser.parse_args()

    if not CHANGELOG_PATH.exists():
        print("ERROR: CHANGELOG.md is missing", file=sys.stderr)
        return 2

    release_day = date.fromisoformat(args.date)
    updated, release_body = promote_unreleased(
        version=args.version,
        release_date=release_day,
        range_spec=args.range,
    )

    if args.body_out:
        Path(args.body_out).write_text(f"{release_body}\n", encoding="utf-8")

    if args.dry_run:
        print(release_body)
        return 0

    write_changelog(updated)
    if not args.body_out:
        print(release_body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
