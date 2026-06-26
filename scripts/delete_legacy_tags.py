#!/usr/bin/env python3
"""Delete legacy git tags (typically non-v prefixed semver tags) safely.

Examples:
    # Preview legacy numeric tags like 0.7.1282 (default keeps >= 0.8.0)
  python scripts/delete_legacy_tags.py

    # Preview with an explicit keep threshold
    python scripts/delete_legacy_tags.py --min-keep-version 0.9.0

  # Delete locally and on origin after confirmation
  python scripts/delete_legacy_tags.py --apply

  # Non-interactive delete (use with care)
  python scripts/delete_legacy_tags.py --apply --yes

  # Delete every non-v tag, not just numeric semver tags
  python scripts/delete_legacy_tags.py --apply --delete-any-non-v

    # Preview v-prefixed tags and then delete them all (no safety floor)
    python scripts/delete_legacy_tags.py --target-v-prefix
    python scripts/delete_legacy_tags.py --target-v-prefix --no-safety-floor --apply

    # Keep specific tags/patterns no matter what
    python scripts/delete_legacy_tags.py --apply --keep-pattern '^0\\.9\\.'
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass


LEGACY_SEMVER_NO_V = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def _parse_core_semver(value: str) -> tuple[int, int, int] | None:
    """Parse the core MAJOR.MINOR.PATCH part of a semver-ish tag."""
    core = value.split("+", 1)[0].split("-", 1)[0]
    parts = core.split(".")
    if len(parts) != 3:
        return None
    try:
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        return None


@dataclass
class DeleteStats:
    local_deleted: int = 0
    local_failed: int = 0
    remote_deleted: int = 0
    remote_failed: int = 0


def _run_git(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=check,
    )


def _ensure_git_repo() -> None:
    try:
        out = _run_git(["rev-parse", "--is-inside-work-tree"]).stdout.strip()
    except subprocess.CalledProcessError as exc:
        msg = exc.stderr.strip() or exc.stdout.strip() or "unknown git error"
        print(f"ERROR: Not a git repository ({msg})", file=sys.stderr)
        raise SystemExit(2) from exc
    if out != "true":
        print("ERROR: Not inside a git work tree", file=sys.stderr)
        raise SystemExit(2)


def _list_tags() -> list[str]:
    result = _run_git(["tag", "--list"])  # sorted lexicographically by git
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _candidate_tags(
    tags: list[str],
    delete_any_target: bool,
    pattern: re.Pattern[str] | None,
    min_keep_version: str | None,
    keep_patterns: list[re.Pattern[str]],
    target_v_prefix: bool,
) -> list[str]:
    candidates: list[str] = []
    min_keep_core = _parse_core_semver(min_keep_version) if min_keep_version else None
    for tag in tags:
        normalized = tag
        if target_v_prefix:
            if not tag.startswith("v"):
                continue
            normalized = tag[1:]
        else:
            if tag.startswith("v"):
                continue

        if any(rx.search(tag) for rx in keep_patterns):
            continue

        # Explicit regex takes precedence and can include non-semver tags.
        if pattern and pattern.search(tag):
            candidates.append(tag)
            continue

        if delete_any_target:
            candidates.append(tag)
            continue

        if not LEGACY_SEMVER_NO_V.fullmatch(normalized):
            continue

        if min_keep_core is not None:
            tag_core = _parse_core_semver(normalized)
            if tag_core is None:
                continue
            if tag_core >= min_keep_core:
                continue

        candidates.append(tag)
    return candidates


def _delete_local_tag(tag: str) -> bool:
    try:
        _run_git(["tag", "-d", tag])
        return True
    except subprocess.CalledProcessError as exc:
        err = exc.stderr.strip() or exc.stdout.strip() or "unknown error"
        print(f"LOCAL FAIL {tag}: {err}")
        return False


def _delete_remote_tag(remote: str, tag: str) -> bool:
    try:
        _run_git(["push", remote, "--delete", tag])
        return True
    except subprocess.CalledProcessError as exc:
        err = exc.stderr.strip() or exc.stdout.strip() or "unknown error"
        print(f"REMOTE FAIL {tag}: {err}")
        return False


def _prompt_yes_no(prompt: str) -> bool:
    answer = input(f"{prompt} [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Delete extra non-v git tags.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete tags (default is dry-run).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt when --apply is set.",
    )
    parser.add_argument(
        "--remote",
        default="origin",
        help="Remote to delete tags from (default: origin).",
    )
    parser.add_argument(
        "--delete-any-target",
        action="store_true",
        help="Delete all targeted tags, not just numeric semver-like tags.",
    )
    parser.add_argument(
        "--delete-any-non-v",
        dest="delete_any_target",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--target-v-prefix",
        action="store_true",
        help="Target v-prefixed tags instead of non-v tags.",
    )
    parser.add_argument(
        "--min-keep-version",
        default="0.8.0",
        help=(
            "Keep targeted semver tags >= this version when not using --delete-any-target "
            "(default: 0.8.0)."
        ),
    )
    parser.add_argument(
        "--no-safety-floor",
        action="store_true",
        help="Disable min keep floor and consider all targeted semver tags.",
    )
    parser.add_argument(
        "--pattern",
        default="",
        help="Additional regex to match candidate tags for deletion.",
    )
    parser.add_argument(
        "--keep-pattern",
        action="append",
        default=[],
        help="Regex for tags to always keep (can be repeated).",
    )
    parser.add_argument(
        "--no-local",
        action="store_true",
        help="Do not delete local tags.",
    )
    parser.add_argument(
        "--no-remote",
        action="store_true",
        help="Do not delete remote tags.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _ensure_git_repo()

    if args.no_local and args.no_remote:
        print("ERROR: both --no-local and --no-remote were set; nothing to do", file=sys.stderr)
        return 2

    extra_pattern = re.compile(args.pattern) if args.pattern else None
    keep_patterns = [re.compile(expr) for expr in args.keep_pattern]
    tags = _list_tags()
    keep_floor = None if args.no_safety_floor else args.min_keep_version
    candidates = _candidate_tags(
        tags,
        delete_any_target=args.delete_any_target,
        pattern=extra_pattern,
        min_keep_version=keep_floor,
        keep_patterns=keep_patterns,
        target_v_prefix=args.target_v_prefix,
    )

    if not candidates:
        print("No candidate tags found. Nothing to delete.")
        return 0

    print(f"Found {len(candidates)} candidate tag(s):")
    for tag in candidates:
        print(f"  - {tag}")

    if not args.apply:
        print("\nDry run only. Re-run with --apply to delete these tags.")
        target_label = "v-prefixed" if args.target_v_prefix else "non-v"
        print(f"Targeting: {target_label} tags")
        if keep_floor is not None and not args.delete_any_target:
            print(f"Safety floor: keeping targeted semver tags >= {args.min_keep_version}")
        return 0

    if not args.yes:
        destinations = []
        if not args.no_local:
            destinations.append("local")
        if not args.no_remote:
            destinations.append(f"remote '{args.remote}'")
        where = " and ".join(destinations)
        if not _prompt_yes_no(f"Delete {len(candidates)} tag(s) from {where}?"):
            print("Aborted.")
            return 1

    stats = DeleteStats()
    for tag in candidates:
        if not args.no_local:
            if _delete_local_tag(tag):
                stats.local_deleted += 1
                print(f"LOCAL OK   {tag}")
            else:
                stats.local_failed += 1

        if not args.no_remote:
            if _delete_remote_tag(args.remote, tag):
                stats.remote_deleted += 1
                print(f"REMOTE OK  {tag}")
            else:
                stats.remote_failed += 1

    print("\nSummary:")
    if not args.no_local:
        print(f"  local:  deleted={stats.local_deleted}, failed={stats.local_failed}")
    if not args.no_remote:
        print(f"  remote: deleted={stats.remote_deleted}, failed={stats.remote_failed}")

    return 0 if (stats.local_failed == 0 and stats.remote_failed == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
