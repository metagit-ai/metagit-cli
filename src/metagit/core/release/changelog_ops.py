#!/usr/bin/env python
"""Parse, validate, promote, and generate release notes for CHANGELOG.md."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path

CHANGELOG_PATH = Path("CHANGELOG.md")
DOCS_CHANGELOG_PATH = Path("docs/changelog.md")

_UNRELEASED_HEADER = "## Unreleased"
_VERSION_HEADER_RE = re.compile(r"^## \[(?P<version>[^\]]+)\]", re.MULTILINE)
_CHANGELOG_REQUIRED_PREFIXES = (
    "src/",
    "schemas/",
    "web/",
)

_COMMIT_SECTION_MAP: tuple[tuple[str, str], ...] = (
    ("feat:", "Added"),
    ("fix:", "Fixed"),
    ("perf:", "Changed"),
    ("refactor:", "Changed"),
    ("docs:", "Changed"),
    ("chore:", "Changed"),
)


@dataclass(frozen=True)
class ChangelogSections:
    """Parsed Keep-a-Changelog sections."""

    preamble: str
    unreleased: str
    released: str


@dataclass(frozen=True)
class ChangelogValidationResult:
    """Outcome for changelog enforcement gates."""

    ok: bool
    message: str


def read_changelog(path: Path = CHANGELOG_PATH) -> str:
    return path.read_text(encoding="utf-8")


def write_changelog(content: str, path: Path = CHANGELOG_PATH) -> None:
    path.write_text(content, encoding="utf-8")


def _docs_site_changelog(content: str) -> str:
    """Rewrite repo-root doc links for MkDocs (docs/ is the site root)."""
    return re.sub(
        r"\]\((?:\./)?docs/([^)]+)\)",
        r"](\1)",
        content,
    )


def sync_docs_changelog(
    *,
    source: Path = CHANGELOG_PATH,
    target: Path = DOCS_CHANGELOG_PATH,
) -> None:
    """Copy root changelog into docs/ for MkDocs builds."""
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = source.read_text(encoding="utf-8")
    target.write_text(_docs_site_changelog(raw), encoding="utf-8")


def parse_changelog(content: str) -> ChangelogSections:
    if _UNRELEASED_HEADER not in content:
        raise ValueError("CHANGELOG.md is missing an ## Unreleased section")

    before, after = content.split(_UNRELEASED_HEADER, 1)
    released_match = _VERSION_HEADER_RE.search(after)
    if released_match is None:
        unreleased = after.strip()
        released = ""
    else:
        unreleased = after[: released_match.start()].strip()
        released = after[released_match.start() :].lstrip()

    return ChangelogSections(
        preamble=before.rstrip(),
        unreleased=unreleased,
        released=released,
    )


def promote_unreleased(
    *,
    version: str,
    release_date: date | None = None,
    content: str | None = None,
    range_spec: str = "",
) -> tuple[str, str]:
    """
    Move ## Unreleased content into a versioned section.

    Returns (updated_changelog, release_body_markdown).
    """
    source = content or read_changelog()
    sections = parse_changelog(source)
    when = (release_date or date.today()).isoformat()
    body = sections.unreleased.strip()
    if not body:
        body = generate_commit_notes(range_spec=range_spec)

    version_header = f"## [{version}] - {when}"
    release_body = f"{version_header}\n\n{body}".strip()
    updated = "\n\n".join(
        part
        for part in (
            sections.preamble,
            _UNRELEASED_HEADER,
            "",
            version_header,
            "",
            body,
            sections.released,
        )
        if part is not None
    )
    return f"{updated.rstrip()}\n", release_body


def generate_commit_notes(*, range_spec: str = "") -> str:
    """Build Keep-a-Changelog sections from conventional commits."""
    command = ["git", "log", "--pretty=format:%s|%h"]
    if range_spec:
        command.append(range_spec)
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return "_No commit notes generated._"

    grouped: dict[str, list[str]] = {}
    for line in completed.stdout.splitlines():
        subject_hash = line.strip()
        if not subject_hash or "|" not in subject_hash:
            continue
        subject, commit_hash = subject_hash.rsplit("|", 1)
        section = _section_for_commit(subject)
        grouped.setdefault(section, []).append(f"- {subject} ({commit_hash})")

    if not grouped:
        return "_No commit notes generated._"

    order = ["Added", "Changed", "Fixed", "Removed"]
    blocks: list[str] = []
    for section in order:
        items = grouped.get(section)
        if not items:
            continue
        blocks.append(f"### {section}\n" + "\n".join(items))
    return "\n\n".join(blocks)


def _section_for_commit(subject: str) -> str:
    lowered = subject.lower()
    for prefix, section in _COMMIT_SECTION_MAP:
        if lowered.startswith(prefix):
            return section
    return "Changed"


def validate_changelog_update(changed_paths: set[str]) -> ChangelogValidationResult:
    """Require CHANGELOG.md when product code changes."""
    meaningful = sorted(
        path for path in changed_paths if any(path.startswith(prefix) for prefix in _CHANGELOG_REQUIRED_PREFIXES)
    )
    if not meaningful:
        return ChangelogValidationResult(
            ok=True,
            message="No changelog-required paths changed.",
        )
    if "CHANGELOG.md" in changed_paths:
        return ChangelogValidationResult(
            ok=True,
            message="CHANGELOG.md updated with product changes.",
        )
    sample = ", ".join(meaningful[:5])
    suffix = "..." if len(meaningful) > 5 else ""
    return ChangelogValidationResult(
        ok=False,
        message=(
            "CHANGELOG.md must be updated when changing product code "
            f"({sample}{suffix}). Add an entry under ## Unreleased or set "
            "SKIP_CHANGELOG_CHECK=1 to bypass locally."
        ),
    )


def git_changed_paths() -> set[str] | None:
    """Collect changed paths from git; None when git metadata is unavailable."""
    if not Path(".git").exists():
        return None

    chunks: list[str] = []
    for spec in (
        ["diff", "--name-only", "HEAD"],
        ["diff", "--cached", "--name-only"],
    ):
        lines = _git_lines(spec)
        if lines is None:
            return None
        chunks.extend(lines)

    upstream = _git_lines(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    if upstream:
        branch_diff = _git_lines(["diff", "--name-only", f"{upstream[0]}...HEAD"])
        if branch_diff is None:
            return None
        chunks.extend(branch_diff)
    return set(chunks)


def _git_lines(args: list[str]) -> list[str] | None:
    completed = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]
