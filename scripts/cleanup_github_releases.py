#!/usr/bin/env python3
"""Prune old GitHub Releases safely with preview/apply modes.

Examples:
  python3 scripts/cleanup_github_releases.py
  python3 scripts/cleanup_github_releases.py --repo metagit-ai/metagit-cli --apply
  python3 scripts/cleanup_github_releases.py --apply --yes --delete-tag
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Pattern
from urllib.parse import quote

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

try:  # pragma: no branch
    from metagit.core.release.github_release_cleanup import (  # noqa: E402
        GitHubReleaseRecord,
        select_releases_for_prune,
    )
except Exception:  # pragma: no cover - standalone fallback path
    _SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[-+][0-9A-Za-z.-]+)?$")

    @dataclass(frozen=True)
    class GitHubReleaseRecord:
        release_id: int
        tag_name: str
        draft: bool = False
        prerelease: bool = False
        published_at: str = ""

    def _parse_semver(tag_name: str) -> tuple[int, int, int] | None:
        match = _SEMVER_RE.fullmatch(tag_name.strip())
        if match is None:
            return None
        return (int(match.group(1)), int(match.group(2)), int(match.group(3)))

    def select_releases_for_prune(
        releases: list[GitHubReleaseRecord],
        *,
        min_keep_version: str,
        keep_latest: int,
        include_draft: bool,
        include_prerelease: bool,
        delete_non_semver: bool,
        keep_tag_regexes: tuple[Pattern[str], ...],
    ) -> list[GitHubReleaseRecord]:
        floor = _parse_semver(min_keep_version)
        if floor is None:
            raise ValueError("--min-keep-version must be a semver value like 0.8.0 or v0.8.0")

        eligible: list[GitHubReleaseRecord] = []
        for release in releases:
            if release.draft and not include_draft:
                continue
            if release.prerelease and not include_prerelease:
                continue
            if any(regex.search(release.tag_name) for regex in keep_tag_regexes):
                continue
            eligible.append(release)

        semver_ordered = sorted(
            (
                (release, _parse_semver(release.tag_name))
                for release in eligible
                if _parse_semver(release.tag_name) is not None
            ),
            key=lambda item: (item[1][0], item[1][1], item[1][2]),
            reverse=True,
        )
        keep_ids = {release.release_id for release, _ in semver_ordered[: max(0, keep_latest)]}

        candidates: list[GitHubReleaseRecord] = []
        for release in eligible:
            if release.release_id in keep_ids:
                continue

            parsed = _parse_semver(release.tag_name)
            if parsed is None:
                if delete_non_semver:
                    candidates.append(release)
                continue

            if parsed < floor:
                candidates.append(release)

        return candidates


@dataclass
class DeleteStats:
    releases_deleted: int = 0
    releases_failed: int = 0
    tags_deleted: int = 0
    tags_failed: int = 0


def run_gh(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        check=check,
    )


def ensure_gh_ready() -> None:
    try:
        run_gh(["--version"])
    except FileNotFoundError as exc:
        print("ERROR: gh CLI is not installed.", file=sys.stderr)
        raise SystemExit(2) from exc

    auth = run_gh(["auth", "status"], check=False)
    if auth.returncode != 0:
        print("ERROR: gh auth is not configured. Run `gh auth login` first.", file=sys.stderr)
        raise SystemExit(2)


def resolve_repo(explicit_repo: str | None) -> str:
    if explicit_repo:
        return explicit_repo

    remote = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        check=False,
    )
    if remote.returncode != 0:
        raise SystemExit("ERROR: Unable to resolve origin remote. Pass --repo owner/name.")

    url = remote.stdout.strip()
    github_match = re.search(r"github\.com[:/]([^/]+)/([^/.]+)(?:\.git)?$", url)
    if github_match is None:
        raise SystemExit("ERROR: Could not parse owner/repo from origin URL. Pass --repo owner/name.")
    return f"{github_match.group(1)}/{github_match.group(2)}"


def fetch_releases(repo: str) -> list[GitHubReleaseRecord]:
    releases: list[GitHubReleaseRecord] = []
    page = 1
    while True:
        response = run_gh(["api", f"repos/{repo}/releases?per_page=100&page={page}"], check=False)
        if response.returncode != 0:
            msg = response.stderr.strip() or response.stdout.strip() or "unknown gh api error"
            raise SystemExit(f"ERROR: failed to fetch releases ({msg})")

        payload = json.loads(response.stdout)
        if not payload:
            break

        for item in payload:
            release_id = item.get("id")
            tag_name = item.get("tag_name") or ""
            if release_id is None or not tag_name:
                continue
            releases.append(
                GitHubReleaseRecord(
                    release_id=int(release_id),
                    tag_name=tag_name,
                    draft=bool(item.get("draft", False)),
                    prerelease=bool(item.get("prerelease", False)),
                    published_at=item.get("published_at") or "",
                )
            )

        if len(payload) < 100:
            break
        page += 1

    return releases


def delete_release(repo: str, release: GitHubReleaseRecord) -> bool:
    response = run_gh(["api", "-X", "DELETE", f"repos/{repo}/releases/{release.release_id}"], check=False)
    if response.returncode == 0:
        return True
    msg = response.stderr.strip() or response.stdout.strip() or "unknown gh api error"
    print(f"RELEASE FAIL {release.tag_name}: {msg}")
    return False


def delete_tag(repo: str, tag_name: str) -> bool:
    encoded = quote(tag_name, safe="")
    response = run_gh(["api", "-X", "DELETE", f"repos/{repo}/git/refs/tags/{encoded}"], check=False)
    if response.returncode == 0:
        return True
    msg = response.stderr.strip() or response.stdout.strip() or "unknown gh api error"
    print(f"TAG FAIL {tag_name}: {msg}")
    return False


def confirm(prompt: str) -> bool:
    answer = input(f"{prompt} [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prune old GitHub releases with safety controls.")
    parser.add_argument("--repo", default="", help="Repository in owner/name format. Defaults to origin remote.")
    parser.add_argument("--apply", action="store_true", help="Apply deletions. Default is preview mode.")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompts in --apply mode.")
    parser.add_argument(
        "--min-keep-version",
        default="0.8.0",
        help="Keep semver release tags >= this version (default: 0.8.0).",
    )
    parser.add_argument(
        "--keep-latest",
        type=int,
        default=20,
        help="Always keep this many latest semver releases (default: 20).",
    )
    parser.add_argument(
        "--keep-tag-pattern",
        action="append",
        default=[],
        help="Regex for tags to always keep (repeatable).",
    )
    parser.add_argument(
        "--include-prerelease",
        action="store_true",
        help="Include prereleases in prune candidates.",
    )
    parser.add_argument(
        "--include-draft",
        action="store_true",
        help="Include draft releases in prune candidates.",
    )
    parser.add_argument(
        "--delete-non-semver",
        action="store_true",
        help="Also prune non-semver tags after keep filters.",
    )
    parser.add_argument(
        "--delete-tag",
        action="store_true",
        help="Delete the corresponding remote git tag after deleting each release.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ensure_gh_ready()
    repo = resolve_repo(args.repo or None)

    keep_regexes = tuple(re.compile(pattern) for pattern in args.keep_tag_pattern)
    releases = fetch_releases(repo)
    candidates = select_releases_for_prune(
        releases,
        min_keep_version=args.min_keep_version,
        keep_latest=args.keep_latest,
        include_draft=args.include_draft,
        include_prerelease=args.include_prerelease,
        delete_non_semver=args.delete_non_semver,
        keep_tag_regexes=keep_regexes,
    )

    if not candidates:
        print("No release candidates found. Nothing to prune.")
        return 0

    print(f"Repository: {repo}")
    print(f"Total releases scanned: {len(releases)}")
    print(f"Candidate releases: {len(candidates)}")
    print("Candidates:")
    for release in candidates:
        published = release.published_at or "unknown"
        print(
            f"  - id={release.release_id} tag={release.tag_name} "
            f"published={published} draft={release.draft} prerelease={release.prerelease}"
        )

    if not args.apply:
        print("\nPreview only. Re-run with --apply to delete these releases.")
        if args.delete_tag:
            print("Tag deletion is enabled and will run during --apply.")
        return 0

    if not args.yes:
        prompt = f"Delete {len(candidates)} release(s) from {repo}"
        if args.delete_tag:
            prompt += " and their remote tags"
        prompt += "?"
        if not confirm(prompt):
            print("Aborted.")
            return 1

    stats = DeleteStats()
    for release in candidates:
        if delete_release(repo, release):
            stats.releases_deleted += 1
            print(f"RELEASE OK {release.tag_name}")
            if args.delete_tag:
                if delete_tag(repo, release.tag_name):
                    stats.tags_deleted += 1
                    print(f"TAG OK     {release.tag_name}")
                else:
                    stats.tags_failed += 1
        else:
            stats.releases_failed += 1

    print("\nSummary:")
    print(f"  releases: deleted={stats.releases_deleted}, failed={stats.releases_failed}")
    if args.delete_tag:
        print(f"  tags:     deleted={stats.tags_deleted}, failed={stats.tags_failed}")

    return 0 if (stats.releases_failed == 0 and stats.tags_failed == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
