#!/usr/bin/env python
"""
Installer utilities for bundled skills and MCP config updates.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from io import StringIO
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field
from ruamel.yaml import YAML

from metagit import DATA_PATH

InstallScope = Literal["project", "user"]
InstallMode = Literal["skills", "mcp"]
McpConfigFormat = Literal["json", "yaml"]

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
        description="JSON/YAML root key for project-scope MCP config",
    )
    user_mcp_root_key: str = Field(
        default="mcpServers",
        description="JSON/YAML root key for user-scope MCP config",
    )
    mcp_config_format: McpConfigFormat = Field(
        default="json",
        description="On-disk format for MCP server registration",
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
        user_skills_path="~/.hermes/skills",
        project_mcp_path=".hermes/config.yaml",
        user_mcp_path="~/.hermes/config.yaml",
        project_mcp_root_key="mcp_servers",
        user_mcp_root_key="mcp_servers",
        mcp_config_format="yaml",
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


def resolve_hermes_home() -> Path:
    """Return the active Hermes home (`HERMES_HOME` or ``~/.hermes``)."""
    raw = os.environ.get("HERMES_HOME", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (Path.home() / ".hermes").resolve()


def target_paths_for(target: str) -> TargetPaths:
    """
    Return install paths for a target, applying Hermes home overrides.

    Hermes user-scope paths follow ``HERMES_HOME`` (default ``~/.hermes``) so the
    gateway and ``metagit skills|mcp install --target hermes`` share one root.
    """
    paths = TARGET_PATHS[target]
    if target != "hermes":
        return paths
    home = resolve_hermes_home()
    return paths.model_copy(
        update={
            "user_skills_path": str(home / "skills"),
            "user_mcp_path": str(home / "config.yaml"),
        }
    )


def resolve_metagit_launch() -> Tuple[str, List[str]]:
    """
    Resolve the preferred command + args for ``metagit mcp serve``.

    Prefer an installed ``metagit`` binary on ``PATH``. Fall back to
    ``python -m metagit`` so ephemeral ``uvx`` environments are not required.
    """
    found = shutil.which("metagit")
    if found:
        return found, ["mcp", "serve"]
    return sys.executable, ["-m", "metagit", "mcp", "serve"]


def build_mcp_server_entry(target: str) -> Dict[str, object]:
    """Build a vendor-appropriate MCP server registration payload."""
    command, args = resolve_metagit_launch()
    entry: Dict[str, object] = {
        "command": command,
        "args": args,
    }
    if target == "hermes":
        entry["enabled"] = True
        entry["connect_timeout"] = 30
        entry["env"] = {"METAGIT_AGENT_MODE": "true"}
    return entry


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
    *,
    project_root: Optional[Path] = None,
) -> List[str]:
    """Resolve install targets by explicit include/exclude or auto-detection."""
    disabled = set(disable_targets)
    if enable_targets:
        return [target for target in enable_targets if target not in disabled]
    detected = autodetect_targets(mode=mode, scope=scope, project_root=project_root)
    return [target for target in detected if target not in disabled]


def autodetect_targets(
    mode: InstallMode,
    scope: InstallScope,
    *,
    project_root: Optional[Path] = None,
) -> List[str]:
    """Detect target applications by existing config/directories."""
    resolved: List[str] = []
    for target in SUPPORTED_TARGETS:
        target_paths = target_paths_for(target)
        if mode == "skills":
            candidate = _expand_target_path(
                target_paths.project_skills_path if scope == "project" else target_paths.user_skills_path,
                project_root=project_root,
            )
        else:
            candidate = _expand_target_path(
                target_paths.project_mcp_path if scope == "project" else target_paths.user_mcp_path,
                project_root=project_root,
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
    project_root: Optional[Path] = None,
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
        target_paths = target_paths_for(target)
        destination = _expand_target_path(
            target_paths.project_skills_path if scope == "project" else target_paths.user_skills_path,
            project_root=project_root,
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
    *,
    project_root: Optional[Path] = None,
) -> List[InstallResult]:
    """Install/update MCP server configuration for selected targets."""
    results: List[InstallResult] = []
    for target in targets:
        target_paths = target_paths_for(target)
        config_path = _expand_target_path(
            target_paths.project_mcp_path if scope == "project" else target_paths.user_mcp_path,
            project_root=project_root,
        )
        root_key = target_paths.project_mcp_root_key if scope == "project" else target_paths.user_mcp_root_key
        entry = build_mcp_server_entry(target)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        if target_paths.mcp_config_format == "yaml":
            _upsert_yaml_mcp_server(config_path, root_key, server_name, entry)
        else:
            _upsert_json_mcp_server(config_path, root_key, server_name, entry)
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


def _upsert_json_mcp_server(
    config_path: Path,
    root_key: str,
    server_name: str,
    entry: Dict[str, object],
) -> None:
    """Merge an MCP server entry into a JSON/JSONC config file."""
    config_data = _read_json_with_comments(config_path)
    if not isinstance(config_data, dict):
        config_data = {}
    mcp_servers = config_data.get(root_key)
    if not isinstance(mcp_servers, dict):
        mcp_servers = {}
    mcp_servers[server_name] = entry
    config_data[root_key] = mcp_servers
    config_path.write_text(
        json.dumps(config_data, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def _upsert_yaml_mcp_server(
    config_path: Path,
    root_key: str,
    server_name: str,
    entry: Dict[str, object],
) -> None:
    """Merge an MCP server entry into a YAML config file (Hermes ``config.yaml``)."""
    yaml = YAML(typ="rt")
    yaml.default_flow_style = False
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    document: object = {}
    if config_path.exists():
        raw = config_path.read_text(encoding="utf-8")
        if raw.strip():
            loaded = yaml.load(StringIO(raw))
            if loaded is not None:
                document = loaded
    if not isinstance(document, dict):
        document = {}
    mcp_servers = document.get(root_key)
    if not isinstance(mcp_servers, dict):
        mcp_servers = {}
    mcp_servers[server_name] = entry
    document[root_key] = mcp_servers
    buffer = StringIO()
    yaml.dump(document, buffer)
    config_path.write_text(buffer.getvalue(), encoding="utf-8")


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


def _find_git_root(start: Optional[Path] = None) -> Optional[Path]:
    """Walk parents from ``start`` (default cwd) looking for a ``.git`` entry."""
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None


def resolve_project_install_root(start: Optional[Path] = None) -> Path:
    """
    Resolve the base directory for ``--scope project`` installs.

    Prefers the nearest git repository root; falls back to ``cwd`` when not
    inside a git work tree (callers that ``chdir`` into a target repo keep
    cwd-relative behavior when they omit ``project_root``).
    """
    git_root = _find_git_root(start)
    return git_root if git_root is not None else (start or Path.cwd()).resolve()


def _expand_target_path(
    path_value: str,
    *,
    project_root: Optional[Path] = None,
) -> Path:
    """
    Expand a target path for install/autodetect.

    Absolute and ``~``-prefixed paths stay as-is. Relative (project-scope) paths
    resolve against ``project_root`` when provided, otherwise ``cwd``.
    """
    expanded = Path(os.path.expanduser(path_value))
    if expanded.is_absolute():
        return expanded
    base = project_root.expanduser().resolve() if project_root is not None else Path.cwd()
    return base / expanded
