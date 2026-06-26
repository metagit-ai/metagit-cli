#!/usr/bin/env python3
"""Compute the next release version using semantic-release workflow rules.

This mirrors .github/workflows/semantic-release.yaml logic:
- major: commit subject matches (feat|fix|refactor|perf)(scope)!:
- minor: commit subject matches feat(scope)?:
- patch: commit subject matches (fix|refactor|perf)(scope)?:
- otherwise: no release

It also applies the release floor (default 0.8.0) and emits the expected
non-prefixed release tag.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass

MAJOR_RX = re.compile(r"^(feat|fix|refactor|perf)(\([^)]+\))?!:")
MINOR_RX = re.compile(r"^feat(\([^)]+\))?:")
PATCH_RX = re.compile(r"^(fix|refactor|perf)(\([^)]+\))?:")


@dataclass
class Result:
    prev_tag: str
    prev_version: str
    should_release: bool
    new_version: str
    release_tag: str
    reason: str


def run_git(args: list[str], check: bool = True) -> str:
    completed = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=check,
    )
    return completed.stdout.strip()


def parse_semver(value: str) -> tuple[int, int, int]:
    core = value.split("+", 1)[0].split("-", 1)[0]
    parts = core.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid semver: {value}")
    return int(parts[0]), int(parts[1]), int(parts[2])


def semver_max(a: str, b: str) -> str:
    return a if parse_semver(a) >= parse_semver(b) else b


def bump(version: str, kind: str) -> str:
    major, minor, patch = parse_semver(version)
    if kind == "major":
        return f"{major + 1}.0.0"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    if kind == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"Unsupported bump kind: {kind}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-floor", default="0.8.0")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    try:
        _ = run_git(["rev-parse", "--is-inside-work-tree"])
    except subprocess.CalledProcessError:
        print("ERROR: Not inside a git repository", file=sys.stderr)
        return 2

    try:
        prev_tag = run_git(["describe", "--tags", "--abbrev=0"])
    except subprocess.CalledProcessError:
        prev_tag = "0.0.0"

    prev_version = prev_tag[1:] if prev_tag.startswith("v") else prev_tag

    try:
        run_git(["rev-parse", prev_tag])
        range_spec = f"{prev_tag}..HEAD"
        commit_text = run_git(["log", range_spec, "--pretty=format:%s"])
    except subprocess.CalledProcessError:
        commit_text = run_git(["log", "--pretty=format:%s"])

    subjects = [line.strip() for line in commit_text.splitlines() if line.strip()]

    bump_kind = ""
    reason = "No release-eligible commit subjects found"
    if any(MAJOR_RX.search(s) for s in subjects):
        bump_kind = "major"
        reason = "Found breaking Conventional Commit subject"
    elif any(MINOR_RX.search(s) for s in subjects):
        bump_kind = "minor"
        reason = "Found feat commit subject"
    elif any(PATCH_RX.search(s) for s in subjects):
        bump_kind = "patch"
        reason = "Found fix/refactor/perf commit subject"

    should_release = bool(bump_kind)
    if should_release:
        new_version = bump(prev_version, bump_kind)
        new_version = semver_max(new_version, args.release_floor)
    else:
        new_version = prev_version

    release_tag = new_version  # enforced non-prefixed policy

    result = Result(
        prev_tag=prev_tag,
        prev_version=prev_version,
        should_release=should_release,
        new_version=new_version,
        release_tag=release_tag,
        reason=reason,
    )

    if args.json:
        import json

        print(json.dumps(result.__dict__, indent=2))
    else:
        print(f"Previous tag: {result.prev_tag}")
        print(f"Previous version: {result.prev_version}")
        print(f"Should release: {str(result.should_release).lower()}")
        print(f"Next version: {result.new_version}")
        print(f"Release tag: {result.release_tag}")
        print(f"Reason: {result.reason}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
