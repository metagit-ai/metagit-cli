#!/usr/bin/env python
"""
Installer utilities for bundled skills and MCP config updates.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from metagit import DATA_PATH

InstallScope = Literal["project", "user"]
InstallMode = Literal["skills", "mcp"]

SUPPORTED_TARGETS = [
    "opencode",
    "hermes",
    "openclaw",
    "claude_code",
    "cursor",
    "github_copilot",
    "windsurf",
    "codex",
]


class TargetPaths(BaseModel):
    """Paths for target deployment in each scope."""

    project_skills_path: str = Field(..., description="Project-local skills destination")
    user_skills_path: str = Field(..., description="User-global skills destination")
    project_mcp_path: str = Field(..., description="Project-local MCP config path")
    user_mcp_path: str = Field(..., description="User-global MCP config path")
    project_mcp_root_key: str = Field(
        default="mcpServers",
        description="JSON root key for project-scope MCP config",
    )
    user_mcp_root_key: str = Field(
        default="mcpServers",
        description="JSON root key for user-scope MCP config",
    )


class InstallResult(BaseModel):
    """Summary for a single target installation."""

    target: str
    mode: InstallMode
    scope: InstallScope
    applied: bool
    path: str
    details: str
    dry_run: bool = Field(default=False, description="True when no changes were written")


TARGET_PATHS: Dict[str, TargetPaths] = {
    "opencode": TargetPaths(
        project_skills_path=".opencode/skills",
        user_skills_path="~/.config/opencode/skills",
        project_mcp_path=".opencode/mcp.json",
        user_mcp_path="~/.config/opencode/mcp.json",
    ),
    "hermes": TargetPaths(
        project_skills_path=".hermes/skills",
        user_skills_path="~/.config/hermes/skills",
        project_mcp_path=".hermes/mcp.json",
        user_mcp_path="~/.config/hermes/mcp.json",
    ),
    "openclaw": TargetPaths(
        project_skills_path=".openclaw/skills",
        user_skills_path="~/.config/openclaw/skills",
        project_mcp_path=".openclaw/mcp.json",
        user_mcp_path="~/.config/openclaw/mcp.json",
    ),
    "claude_code": TargetPaths(
        project_skills_path=".claude/skills",
        user_skills_path="~/.claude/skills",
        project_mcp_path=".claude/mcp.json",
        user_mcp_path="~/.claude/mcp.json",
    ),
    "cursor": TargetPaths(
        project_skills_path=".cursor/skills",
        user_skills_path="~/.cursor/skills",
        project_mcp_path=".cursor/mcp.json",
        user_mcp_path="~/.cursor/mcp.json",
    ),
    "github_copilot": TargetPaths(
        project_skills_path=".github/skills",
        user_skills_path="~/.copilot/skills",
        project_mcp_path=".vscode/mcp.json",
        user_mcp_path="~/.copilot/mcp-config.json",
        project_mcp_root_key="servers",
        user_mcp_root_key="mcpServers",
    ),
    "windsurf": TargetPaths(
        project_skills_path=".windsurf/skills",
        user_skills_path="~/.codeium/windsurf/skills",
        project_mcp_path=".windsurf/mcp_config.json",
        user_mcp_path="~/.codeium/windsurf/mcp_config.json",
    ),
    "codex": TargetPaths(
        project_skills_path=".agents/skills",
        user_skills_path="~/.agents/skills",
        project_mcp_path=".codex/mcp.json",
        user_mcp_path="~/.codex/mcp.json",
    ),
}


def bundled_skills_root() -> Path:
    """Resolve bundled skill source path."""
    return Path(DATA_PATH) / "skills"


def list_bundled_skills() -> List[str]:
    """Return bundled skill names."""
    skills_root = bundled_skills_root()
    if not skills_root.exists():
        return []
    return sorted([item.name for item in skills_root.iterdir() if item.is_dir()])


def skill_markdown(skill_name: str) -> Optional[str]:
    """Load SKILL.md content for a bundled skill."""
    skill_file = bundled_skills_root() / skill_name / "SKILL.md"
    if not skill_file.exists():
        return None
    return skill_file.read_text(encoding="utf-8")


def resolve_skill_names(skill_names: Optional[List[str]]) -> List[str]:
    """Validate and resolve bundled skill names for install."""
    bundled = list_bundled_skills()
    if not skill_names:
        return bundled
    unknown = sorted({name for name in skill_names if name not in bundled})
    if unknown:
        available = ", ".join(bundled) if bundled else "(none)"
        raise ValueError(f"Unknown skill(s): {', '.join(unknown)}. Available: {available}")
    return list(dict.fromkeys(skill_names))


def resolve_targets(
    mode: InstallMode,
    scope: InstallScope,
    enable_targets: List[str],
    disable_targets: List[str],
) -> List[str]:
    """Resolve install targets by explicit include/exclude or auto-detection."""
    disabled = set(disable_targets)
    if enable_targets:
        return [target for target in enable_targets if target not in disabled]
    detected = autodetect_targets(mode=mode, scope=scope)
    return [target for target in detected if target not in disabled]


def autodetect_targets(mode: InstallMode, scope: InstallScope) -> List[str]:
    """Detect target applications by existing config/directories."""
    resolved: List[str] = []
    for target in SUPPORTED_TARGETS:
        target_paths = TARGET_PATHS[target]
        if mode == "skills":
            candidate = _expand_target_path(
                target_paths.project_skills_path if scope == "project" else target_paths.user_skills_path
            )
        else:
            candidate = _expand_target_path(
                target_paths.project_mcp_path if scope == "project" else target_paths.user_mcp_path
            )
        if candidate.exists() or candidate.parent.exists():
            resolved.append(target)
    return resolved


def _install_details_label(
    installed_names: List[str],
    *,
    dry_run: bool,
) -> str:
    """Build a human-readable install summary line."""
    verb = "Would install" if dry_run else "Installed"
    if len(installed_names) == 1:
        return f"{verb} skill '{installed_names[0]}'"
    names = ", ".join(installed_names)
    return f"{verb} {len(installed_names)} skills: {names}"


def install_skills_for_targets(
    targets: List[str],
    scope: InstallScope,
    skill_names: Optional[List[str]] = None,
    *,
    dry_run: bool = False,
) -> List[InstallResult]:
    """Install bundled skills for selected targets."""
    source_root = bundled_skills_root()
    results: List[InstallResult] = []
    if not source_root.exists():
        return [
            InstallResult(
                target="all",
                mode="skills",
                scope=scope,
                applied=False,
                path=str(source_root),
                details="Bundled skills directory not found",
            )
        ]
    selected_skills = resolve_skill_names(skill_names)
    if not selected_skills:
        return [
            InstallResult(
                target="all",
                mode="skills",
                scope=scope,
                applied=False,
                path=str(source_root),
                details="No bundled skills available to install",
            )
        ]
    for target in targets:
        target_paths = TARGET_PATHS[target]
        destination = _expand_target_path(
            target_paths.project_skills_path if scope == "project" else target_paths.user_skills_path
        )
        if not dry_run:
            destination.mkdir(parents=True, exist_ok=True)
        installed_names: List[str] = []
        for skill_name in selected_skills:
            source_skill = source_root / skill_name
            if not source_skill.is_dir():
                continue
            dest_skill = destination / skill_name
            if dry_run:
                installed_names.append(skill_name)
                continue
            if dest_skill.exists():
                shutil.rmtree(dest_skill)
            shutil.copytree(source_skill, dest_skill)
            installed_names.append(skill_name)
        results.append(
            InstallResult(
                target=target,
                mode="skills",
                scope=scope,
                applied=bool(installed_names),
                path=str(destination),
                details=_install_details_label(installed_names, dry_run=dry_run),
                dry_run=dry_run,
            )
        )
    return results


def install_mcp_for_targets(
    targets: List[str],
    scope: InstallScope,
    server_name: str = "metagit",
) -> List[InstallResult]:
    """Install/update MCP server configuration for selected targets."""
    results: List[InstallResult] = []
    for target in targets:
        target_paths = TARGET_PATHS[target]
        config_path = _expand_target_path(
            target_paths.project_mcp_path if scope == "project" else target_paths.user_mcp_path
        )
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_data = _read_json_with_comments(config_path)
        if not isinstance(config_data, dict):
            config_data = {}
        root_key = target_paths.project_mcp_root_key if scope == "project" else target_paths.user_mcp_root_key
        mcp_servers = config_data.get(root_key)
        if not isinstance(mcp_servers, dict):
            mcp_servers = {}
        mcp_servers[server_name] = {
            "command": "uvx",
            "args": ["metagit-cli", "mcp", "serve"],
        }
        config_data[root_key] = mcp_servers
        config_path.write_text(
            json.dumps(config_data, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        results.append(
            InstallResult(
                target=target,
                mode="mcp",
                scope=scope,
                applied=True,
                path=str(config_path),
                details=f"Updated server '{server_name}'",
            )
        )
    return results


def _read_json_with_comments(path: Path) -> Dict[str, object]:
    """Parse JSON or JSONC-style files."""
    if not path.exists():
        return {}
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return {}
    no_line_comments = re.sub(r"^\s*//.*$", "", content, flags=re.MULTILINE)
    no_block_comments = re.sub(r"/\*.*?\*/", "", no_line_comments, flags=re.DOTALL)
    return json.loads(no_block_comments)


def _expand_target_path(path_value: str) -> Path:
    expanded = Path(os.path.expanduser(path_value))
    return expanded if expanded.is_absolute() else Path.cwd() / expanded
