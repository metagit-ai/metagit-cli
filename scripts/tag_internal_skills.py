#!/usr/bin/env python3
"""
Ensure SKILL.md files outside skills/ carry metadata.internal: true.

Public bundled skills live under skills/<name>/SKILL.md and must not be tagged.
All other SKILL.md copies (package data, editor mirrors, generated skills) are
local/internal and must include:

    metadata:
      internal: true

Usage:
    python3 scripts/tag_internal_skills.py          # apply fixes
    python3 scripts/tag_internal_skills.py --check  # validate only (exit 1 on miss)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
PUBLIC_SKILLS_ROOT = REPO_ROOT / "skills"
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)
INTERNAL_TRUE_RE = re.compile(r"^\s*internal:\s*true\s*$", re.MULTILINE)
METADATA_BLOCK_RE = re.compile(r"^metadata:\s*$", re.MULTILINE)


def is_public_skill(path: Path) -> bool:
    """Return True when path is under skills/<name>/SKILL.md."""
    try:
        rel = path.relative_to(PUBLIC_SKILLS_ROOT)
    except ValueError:
        return False
    parts = rel.parts
    return len(parts) >= 2 and parts[-1] == "SKILL.md"


def find_skill_files(root: Path = REPO_ROOT) -> list[Path]:
    return sorted(root.rglob("SKILL.md"))


def has_internal_metadata(frontmatter: str) -> bool:
    return bool(INTERNAL_TRUE_RE.search(frontmatter))


def add_internal_metadata(text: str) -> tuple[str, bool]:
    """Return updated text and whether a change was applied."""
    match = FRONTMATTER_RE.match(text)
    if not match:
        return text, False

    frontmatter, body = match.group(1), match.group(2)
    if has_internal_metadata(frontmatter):
        return text, False

    if METADATA_BLOCK_RE.search(frontmatter):
        updated_frontmatter = METADATA_BLOCK_RE.sub(
            "metadata:\n  internal: true",
            frontmatter,
            count=1,
        )
    else:
        updated_frontmatter = frontmatter.rstrip() + "\nmetadata:\n  internal: true\n"

    return f"---\n{updated_frontmatter}---\n{body}", True


def tag_internal_skills(*, check_only: bool = False) -> tuple[int, int, int]:
    """Tag or validate internal SKILL.md files.

    Returns (failures_or_updates, already_ok, total).
    """
    internal_files = [p for p in find_skill_files() if not is_public_skill(p)]
    failures = 0
    updated = 0
    already_ok = 0

    for skill_file in internal_files:
        text = skill_file.read_text(encoding="utf-8")
        match = FRONTMATTER_RE.match(text)
        if not match:
            failures += 1
            rel = skill_file.relative_to(REPO_ROOT)
            print(f"  FAIL  {rel} (missing or malformed frontmatter)")
            continue

        if has_internal_metadata(match.group(1)):
            already_ok += 1
            continue

        rel = skill_file.relative_to(REPO_ROOT)
        if check_only:
            failures += 1
            print(f"  FAIL  {rel} (missing metadata.internal: true)")
            continue

        new_text, _ = add_internal_metadata(text)
        skill_file.write_text(new_text, encoding="utf-8")
        updated += 1
        print(f"  TAG   {rel}")

    return failures if check_only else updated, already_ok, len(internal_files)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate only; exit 1 when any internal skill is untagged.",
    )
    args = parser.parse_args()

    mode = "Checking" if args.check else "Tagging"
    print(f"{mode} internal SKILL.md files (excluding skills/)")
    print()

    failures_or_updates, already_ok, total = tag_internal_skills(check_only=args.check)
    print()
    if args.check:
        print(f"{already_ok}/{total} internal skills valid")
        return 0 if failures_or_updates == 0 else 1

    print(f"{already_ok + failures_or_updates}/{total} internal skills tagged")
    if failures_or_updates:
        print(f"  updated {failures_or_updates} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
