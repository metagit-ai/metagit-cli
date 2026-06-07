#!/usr/bin/env python3
"""Mirror root CHANGELOG.md into docs/ for MkDocs."""

from __future__ import annotations

import sys

from metagit.core.release.changelog_ops import CHANGELOG_PATH, sync_docs_changelog


def main() -> int:
    if not CHANGELOG_PATH.exists():
        print("ERROR: CHANGELOG.md is missing", file=sys.stderr)
        return 2
    sync_docs_changelog()
    print(f"Synced {CHANGELOG_PATH} -> docs/changelog.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
