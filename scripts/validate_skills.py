#!/usr/bin/env python3
"""
Validate every SKILL.md under skills/ against Claude Code skill conventions.

Usage:
    python3 scripts/validate_skills.py

Checks performed on each skills/<name>/SKILL.md:
  - YAML frontmatter is present and parseable
  - Required fields ``name`` and ``description`` are present
  - ``name`` is lowercase-hyphenated and matches the directory name
  - ``description`` is a non-empty string within the length budget
  - SKILL.md body has substantive content

Exit codes:
  0  all skills passed
  1  one or more skills failed validation
  2  configuration error (skills directory missing, PyYAML not installed)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print(
        "ERROR: PyYAML is required. Install with: pip install pyyaml",
        file=sys.stderr,
    )
    sys.exit(2)

REPO_ROOT = Path(__file__).parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]*[a-z0-9]$")
MAX_NAME_LEN = 64
MAX_DESCRIPTION_LEN = 1024
MIN_DESCRIPTION_LEN = 20
MIN_BODY_LEN = 200

REQUIRED_FIELDS = {"name", "description"}
KNOWN_FIELDS = {"name", "description", "license", "allowed-tools", "metadata"}

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


def validate_skill(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    skill_file = skill_dir / "SKILL.md"

    if not skill_file.is_file():
        rel = skill_file.relative_to(REPO_ROOT)
        return [f"missing SKILL.md (expected at {rel})"]

    text = skill_file.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return [
            "missing or malformed YAML frontmatter (must open and close with '---')"
        ]

    frontmatter_raw, body = match.group(1), match.group(2)
    try:
        frontmatter = yaml.safe_load(frontmatter_raw)
    except yaml.YAMLError as exc:
        return [f"invalid YAML frontmatter: {exc}"]

    if not isinstance(frontmatter, dict):
        return ["YAML frontmatter must be a mapping of key/value pairs"]

    missing = REQUIRED_FIELDS - frontmatter.keys()
    if missing:
        errors.append(
            "missing required frontmatter field(s): " + ", ".join(sorted(missing))
        )

    unknown = set(frontmatter.keys()) - KNOWN_FIELDS
    if unknown:
        errors.append("unknown frontmatter field(s): " + ", ".join(sorted(unknown)))

    name = frontmatter.get("name")
    if name is not None:
        if not isinstance(name, str):
            errors.append(f"'name' must be a string, got {type(name).__name__}")
        else:
            if not NAME_PATTERN.match(name):
                errors.append(
                    f"'name' must match {NAME_PATTERN.pattern} "
                    f"(lowercase, hyphen-separated, no leading/trailing hyphen), got {name!r}"
                )
            if len(name) > MAX_NAME_LEN:
                errors.append(f"'name' exceeds {MAX_NAME_LEN} chars (got {len(name)})")
            if name != skill_dir.name:
                errors.append(
                    f"'name' ({name!r}) must match the directory name ({skill_dir.name!r})"
                )

    desc = frontmatter.get("description")
    if desc is not None:
        if not isinstance(desc, str):
            errors.append(f"'description' must be a string, got {type(desc).__name__}")
        else:
            stripped = desc.strip()
            if not stripped:
                errors.append("'description' must not be empty")
            elif len(stripped) > MAX_DESCRIPTION_LEN:
                errors.append(
                    f"'description' exceeds {MAX_DESCRIPTION_LEN} chars (got {len(stripped)})"
                )
            elif len(stripped) < MIN_DESCRIPTION_LEN:
                errors.append(
                    f"'description' is suspiciously short ({len(stripped)} chars); "
                    "it should describe when to invoke the skill"
                )

    body_stripped = body.strip()
    if len(body_stripped) < MIN_BODY_LEN:
        errors.append(
            f"SKILL.md body is too short ({len(body_stripped)} chars, "
            f"minimum {MIN_BODY_LEN}); skill instructions should be substantive"
        )

    metadata = frontmatter.get("metadata")
    if isinstance(metadata, dict) and metadata.get("internal") is True:
        errors.append(
            "public bundled skills under skills/ must not set metadata.internal: true"
        )

    return errors


def main() -> int:
    if not SKILLS_DIR.is_dir():
        print(
            f"ERROR: skills directory not found at {SKILLS_DIR.relative_to(REPO_ROOT)}/",
            file=sys.stderr,
        )
        return 2

    skill_dirs = sorted(
        p for p in SKILLS_DIR.iterdir() if p.is_dir() and not p.name.startswith(".")
    )
    if not skill_dirs:
        print(
            f"ERROR: no skill subdirectories found under {SKILLS_DIR.relative_to(REPO_ROOT)}/",
            file=sys.stderr,
        )
        return 2

    print(
        f"Validating {len(skill_dirs)} skill(s) in {SKILLS_DIR.relative_to(REPO_ROOT)}/"
    )
    print()

    failed = 0
    for skill_dir in skill_dirs:
        errs = validate_skill(skill_dir)
        if errs:
            failed += 1
            print(f"  FAIL  {skill_dir.name}")
            for err in errs:
                print(f"          - {err}")
        else:
            print(f"  OK    {skill_dir.name}")

    total = len(skill_dirs)
    print()
    print(f"{total - failed}/{total} skills passed validation")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
