#!/usr/bin/env python
"""Catalog resolution for agent_profile skill, MCP, and rule references."""

from __future__ import annotations

from pathlib import Path

from metagit import DATA_PATH
from metagit.core.skills.installer import list_bundled_skills

KNOWN_MCP_SERVERS: frozenset[str] = frozenset({"metagit"})


def bundled_rules_root() -> Path:
    """Resolve bundled agent rule source path."""
    return Path(DATA_PATH) / "agent-rules"


def list_bundled_rules() -> list[str]:
    """Return bundled rule ids (filename stem without extension)."""
    rules_root = bundled_rules_root()
    if not rules_root.exists():
        return []
    names: list[str] = []
    for item in rules_root.iterdir():
        if item.is_file() and item.suffix in {".mdc", ".md"}:
            names.append(item.stem)
    return sorted(names)


def local_skill_file(name: str, *, definition_root: Path, skill_sources: list[str]) -> Path | None:
    """Return ``<dir>/<name>/SKILL.md`` when a declared source directory contains it."""
    root = definition_root.resolve()
    for source in skill_sources:
        candidate = (root / source / name / "SKILL.md").resolve()
        if candidate.is_file():
            return candidate
    return None


def declared_skill_sources(config: object) -> list[str]:
    """Collect ``skill_sources`` from every agent profile on the manifest."""
    found: list[str] = []

    def add(profile: object) -> None:
        sources = getattr(profile, "skill_sources", None)
        if not sources:
            return
        for item in sources:
            text = str(item)
            if text not in found:
                found.append(text)

    workspace = getattr(config, "workspace", None)
    if workspace is None:
        return found
    add(getattr(workspace, "agent_profile", None))
    for project in getattr(workspace, "projects", []) or []:
        add(getattr(project, "agent_profile", None))
        for repo in getattr(project, "repos", []) or []:
            add(getattr(repo, "agent_profile", None))
            for component in getattr(repo, "components", []) or []:
                add(getattr(component, "agent_profile", None))
    return found


def validate_profile_references(
    *,
    skills: list[str],
    mcp: list[str],
    rules: list[str],
    definition_root: Path | None = None,
    skill_sources: list[str] | None = None,
) -> list[str]:
    """Return human-readable errors for unknown catalog ids."""
    errors: list[str] = []
    bundled_skills = set(list_bundled_skills())
    sources = skill_sources or []
    unknown_skills = sorted(
        {
            name
            for name in skills
            if name not in bundled_skills
            and (
                definition_root is None
                or local_skill_file(name, definition_root=definition_root, skill_sources=sources) is None
            )
        }
    )
    if unknown_skills:
        available = ", ".join(list_bundled_skills()) if bundled_skills else "(none)"
        if definition_root is None:
            searched = "(none)"
        elif sources:
            searched = ", ".join(str((definition_root / source).resolve()) for source in sources)
        else:
            searched = "(none)"
        errors.append(f"unknown skill(s): {', '.join(unknown_skills)}. Searched: {searched}. Available: {available}")

    unknown_mcp = sorted({name for name in mcp if name not in KNOWN_MCP_SERVERS})
    if unknown_mcp:
        available = ", ".join(sorted(KNOWN_MCP_SERVERS))
        errors.append(f"unknown mcp server(s): {', '.join(unknown_mcp)}. Known: {available}")

    bundled_rules = set(list_bundled_rules())
    unknown_rules = sorted({name for name in rules if name not in bundled_rules})
    if unknown_rules and bundled_rules:
        available = ", ".join(list_bundled_rules())
        errors.append(f"unknown rule(s): {', '.join(unknown_rules)}. Available: {available}")
    elif unknown_rules and not bundled_rules:
        errors.append(
            f"unknown rule(s): {', '.join(unknown_rules)}. No bundled rules catalog installed yet.",
        )
    return errors
