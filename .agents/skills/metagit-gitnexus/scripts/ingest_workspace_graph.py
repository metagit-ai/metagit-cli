#!/usr/bin/env python3
"""Execute GitNexus Cypher tool_calls exported from metagit config graph export."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

_GITNEXUS_PKG = "gitnexus@1.6.4"


def _load_tool_calls(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and "tool_calls" in payload:
        tool_calls = payload["tool_calls"]
        return tool_calls if isinstance(tool_calls, list) else []
    raise ValueError("expected tool-calls JSON array or export bundle with tool_calls")


def _run_cypher(*, repo: str, query: str, dry_run: bool) -> tuple[bool, str]:
    if dry_run:
        return True, f"(dry run) repo={repo} query={query[:80]}..."
    completed = subprocess.run(
        [
            "npx",
            "--yes",
            _GITNEXUS_PKG,
            "cypher",
            "--repo",
            repo,
            query,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    ok = completed.returncode == 0
    return ok, output.strip() or f"exit {completed.returncode}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "tool_calls_file",
        type=Path,
        help="JSON from metagit config graph export --format tool-calls",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print queries without executing gitnexus cypher",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Execute at most N statements (0 = all)",
    )
    args = parser.parse_args()

    if not args.tool_calls_file.is_file():
        print(f"ERROR: file not found: {args.tool_calls_file}", file=sys.stderr)
        return 2

    tool_calls = _load_tool_calls(args.tool_calls_file)
    if not tool_calls:
        print("No tool calls to execute.")
        return 0

    executed = 0
    failed = 0
    for index, call in enumerate(tool_calls):
        if args.limit and executed >= args.limit:
            break
        arguments = call.get("arguments") if isinstance(call, dict) else None
        if not isinstance(arguments, dict):
            failed += 1
            print(f"FAIL [{index}] malformed tool call")
            continue
        query = arguments.get("query")
        repo = arguments.get("repo")
        if not isinstance(query, str) or not isinstance(repo, str):
            failed += 1
            print(f"FAIL [{index}] missing query or repo")
            continue
        ok, message = _run_cypher(
            repo=repo,
            query=query,
            dry_run=args.dry_run,
        )
        executed += 1
        label = "OK" if ok else "FAIL"
        print(f"{label} [{index}] repo={repo} {message}")
        if not ok:
            failed += 1

    print(f"completed={executed} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
