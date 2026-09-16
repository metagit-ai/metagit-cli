#!/usr/bin/env python
"""Guardrails so bootstrap/cli skills stay token-cheap."""

from pathlib import Path

from metagit.core.prompt.catalog import template_body

REPO = Path(__file__).resolve().parents[2]


def test_bootstrap_skill_defaults_to_init_and_drops_repo_map() -> None:
    text = (REPO / "skills" / "metagit-bootstrap" / "SKILL.md").read_text(encoding="utf-8")
    assert "metagit init --kind application --no-prompt" in text
    assert "--output-file" in text
    assert "metagit detect repo_map -p" not in text
    assert "Default path (deterministic)" in text


def test_cli_skill_does_not_instruct_repo_map_dumps() -> None:
    text = (REPO / "skills" / "metagit-cli" / "SKILL.md").read_text(encoding="utf-8")
    assert "metagit detect repo_map -p" not in text
    assert "--output-file" in text


def test_repo_enrich_prompt_does_not_include_repo_map() -> None:
    text = template_body("repo-enrich", "repo")
    assert "metagit detect repo_map -p" not in text
    assert "--output-file" in text
