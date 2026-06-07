#!/usr/bin/env python
"""Tests for changelog promotion and enforcement helpers."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from metagit.core.release.changelog_ops import (
    parse_changelog,
    promote_unreleased,
    sync_docs_changelog,
    validate_changelog_update,
)


def test_parse_changelog_splits_unreleased_section() -> None:
    content = "\n".join(
        [
            "# Changelog",
            "",
            "## Unreleased",
            "",
            "### Added",
            "- new thing",
            "",
            "## [0.1.0] - 2026-01-01",
            "",
            "### Fixed",
            "- bug",
            "",
        ]
    )
    sections = parse_changelog(content)
    assert "### Added" in sections.unreleased
    assert "new thing" in sections.unreleased
    assert sections.released.startswith("## [0.1.0]")


def test_promote_unreleased_moves_notes_into_version_section() -> None:
    content = "\n".join(
        [
            "# Changelog",
            "",
            "## Unreleased",
            "",
            "### Added",
            "- feature alpha",
            "",
            "## [0.1.0] - 2026-01-01",
            "",
            "### Fixed",
            "- bug",
            "",
        ]
    )
    updated, release_body = promote_unreleased(
        version="0.2.0",
        release_date=date(2026, 6, 7),
        content=content,
        range_spec="",
    )

    assert "## Unreleased" in updated
    assert "## [0.2.0] - 2026-06-07" in updated
    assert "feature alpha" in updated
    assert updated.index("## [0.2.0]") < updated.index("## [0.1.0]")
    assert "feature alpha" in release_body


def test_validate_changelog_requires_update_for_src_changes() -> None:
    result = validate_changelog_update({"src/metagit/cli/main.py"})
    assert result.ok is False
    assert "CHANGELOG.md" in result.message


def test_validate_changelog_passes_when_changelog_updated() -> None:
    result = validate_changelog_update(
        {"src/metagit/cli/main.py", "CHANGELOG.md"},
    )
    assert result.ok is True


def test_validate_changelog_skips_docs_only_changes() -> None:
    result = validate_changelog_update({"docs/agents.md"})
    assert result.ok is True


def test_sync_docs_changelog_rewrites_doc_links(tmp_path: Path) -> None:
    root = tmp_path / "CHANGELOG.md"
    root.write_text(
        "\n".join(
            [
                "# Changelog",
                "",
                "- [agents](docs/agents.md)",
                "- [guide](docs/hermes-iac-workspace-guide.md)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    target = tmp_path / "docs" / "changelog.md"
    sync_docs_changelog(source=root, target=target)
    rendered = target.read_text(encoding="utf-8")
    assert "](agents.md)" in rendered
    assert "](hermes-iac-workspace-guide.md)" in rendered
