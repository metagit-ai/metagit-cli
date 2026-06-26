#!/usr/bin/env python
"""Sync Metagit workspace repos into a GitNexus group for cross-index analysis."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Callable, Optional

import yaml
from pydantic import BaseModel, Field

from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.services.gitnexus_registry import GitNexusRegistryAdapter
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService

_GITNEXUS_PKG = "gitnexus@1.6.4"
_GROUP_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")


class GitNexusGroupMemberAction(BaseModel):
    """Record of a group membership change."""

    group_path: str
    registry_name: str
    repo_path: str
    action: str


class GitNexusGroupSyncResult(BaseModel):
    """Outcome of aligning a workspace with a GitNexus group."""

    ok: bool = True
    group_name: str = ""
    group_dir: str = ""
    created_group: bool = False
    added: list[GitNexusGroupMemberAction] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    skipped: list[dict[str, str]] = Field(default_factory=list)
    contract_sync_ran: bool = False
    contract_sync: Optional[dict[str, Any]] = None
    contract_sync_error: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)


class GitNexusGroupRunner:
    """Invoke gitnexus group subcommands."""

    def __init__(
        self,
        *,
        package: str = _GITNEXUS_PKG,
        groups_root: Optional[Path] = None,
        runner: Optional[Callable[..., subprocess.CompletedProcess[str]]] = None,
    ) -> None:
        self._package = package
        self._groups_root = groups_root or Path.home() / ".gitnexus" / "groups"
        self._runner = runner or subprocess.run

    def group_dir(self, group_name: str) -> Path:
        return self._groups_root / group_name

    def group_exists(self, group_name: str) -> bool:
        return (self.group_dir(group_name) / "group.yaml").is_file()

    def create_group(self, group_name: str, *, force: bool = False) -> None:
        cmd = ["npx", "--yes", self._package, "group", "create", group_name]
        if force:
            cmd.append("--force")
        self._run(cmd, action=f"create group {group_name}")

    def add_repo(
        self,
        group_name: str,
        group_path: str,
        registry_name: str,
    ) -> None:
        cmd = [
            "npx",
            "--yes",
            self._package,
            "group",
            "add",
            group_name,
            group_path,
            registry_name,
        ]
        self._run(cmd, action=f"add {group_path} to {group_name}")

    def remove_repo(self, group_name: str, group_path: str) -> None:
        cmd = [
            "npx",
            "--yes",
            self._package,
            "group",
            "remove",
            group_name,
            group_path,
        ]
        self._run(cmd, action=f"remove {group_path} from {group_name}")

    def sync_contracts(
        self,
        group_name: str,
        *,
        allow_stale: bool = False,
        skip_embeddings: bool = False,
        exact_only: bool = False,
        verbose: bool = False,
    ) -> dict[str, Any]:
        cmd = ["npx", "--yes", self._package, "group", "sync", group_name, "--json"]
        if allow_stale:
            cmd.append("--allow-stale")
        if skip_embeddings:
            cmd.append("--skip-embeddings")
        if exact_only:
            cmd.append("--exact-only")
        if verbose:
            cmd.append("--verbose")
        completed = self._run(cmd, action=f"sync contracts for {group_name}")
        return self._parse_json_stdout(completed.stdout or "")

    def _run(
        self,
        cmd: list[str],
        *,
        action: str,
    ) -> subprocess.CompletedProcess[str]:
        try:
            completed = self._runner(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=300,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError(f"gitnexus {action} failed: {exc}") from exc
        if completed.returncode != 0:
            output = ((completed.stdout or "") + (completed.stderr or "")).strip()
            raise RuntimeError(f"gitnexus {action} failed (exit {completed.returncode}): {output}")
        return completed

    def _parse_json_stdout(self, stdout: str) -> dict[str, Any]:
        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        for line in reversed(lines):
            if not line.startswith("{"):
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return payload
        return {}


def normalize_group_name(value: str) -> str:
    """Return a GitNexus-safe group name from a workspace manifest name."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug or not _GROUP_NAME_RE.match(slug):
        slug = re.sub(r"[^a-z0-9]+", "-", "workspace").strip("-")
    return slug[:64].rstrip("-") or "workspace"


def load_group_repo_paths(group_yaml: Path) -> dict[str, str]:
    """Return group_path -> registry_name from group.yaml."""
    if not group_yaml.is_file():
        return {}
    try:
        payload = yaml.safe_load(group_yaml.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    if not isinstance(payload, dict):
        return {}
    repos = payload.get("repos")
    if not isinstance(repos, dict):
        return {}
    return {str(key): str(value) for key, value in repos.items() if isinstance(key, str) and isinstance(value, str)}


class GitNexusGroupSyncService:
    """Align workspace.projects repos with a GitNexus cross-index group."""

    def __init__(
        self,
        *,
        index_service: Optional[WorkspaceIndexService] = None,
        registry: Optional[GitNexusRegistryAdapter] = None,
        runner: Optional[GitNexusGroupRunner] = None,
    ) -> None:
        self._index = index_service or WorkspaceIndexService()
        self._registry = registry or GitNexusRegistryAdapter()
        self._runner = runner or GitNexusGroupRunner()

    def sync_workspace(
        self,
        config: MetagitConfig,
        workspace_root: str,
        *,
        group_name: Optional[str] = None,
        create_group: bool = True,
        prune: bool = False,
        run_contract_sync: bool = True,
        allow_stale: bool = False,
        skip_embeddings: bool = False,
        exact_only: bool = False,
        verbose: bool = False,
    ) -> GitNexusGroupSyncResult:
        """Create/update GitNexus group membership from workspace index rows."""
        if not config.workspace or not config.workspace.projects:
            return GitNexusGroupSyncResult(
                ok=False,
                warnings=["workspace_not_configured"],
            )

        resolved_name = normalize_group_name(group_name or config.name or "workspace")
        group_dir = self._runner.group_dir(resolved_name)
        result = GitNexusGroupSyncResult(
            ok=True,
            group_name=resolved_name,
            group_dir=str(group_dir),
        )

        if not self._runner.group_exists(resolved_name):
            if not create_group:
                result.ok = False
                result.warnings.append(f'group "{resolved_name}" does not exist; pass create_group=true')
                return result
            self._runner.create_group(resolved_name)
            result.created_group = True

        existing = load_group_repo_paths(group_dir / "group.yaml")
        desired: dict[str, dict[str, str]] = {}
        rows = self._index.build_index(config=config, workspace_root=workspace_root)

        for row in rows:
            group_path = f"{row['project_name']}/{row['repo_name']}"
            repo_path = str(row.get("repo_path", ""))
            if not row.get("exists"):
                result.skipped.append(
                    {
                        "group_path": group_path,
                        "reason": "missing_clone",
                        "repo_path": repo_path,
                    }
                )
                continue
            if not row.get("is_git_repo"):
                result.skipped.append(
                    {
                        "group_path": group_path,
                        "reason": "not_git_repo",
                        "repo_path": repo_path,
                    }
                )
                continue
            registry_name = self._registry.registry_name_for_path(repo_path=repo_path)
            if not registry_name:
                result.skipped.append(
                    {
                        "group_path": group_path,
                        "reason": "not_in_gitnexus_registry",
                        "repo_path": repo_path,
                    }
                )
                continue
            desired[group_path] = {
                "registry_name": registry_name,
                "repo_path": repo_path,
            }

        for group_path, member in sorted(desired.items()):
            registry_name = member["registry_name"]
            if existing.get(group_path) == registry_name:
                continue
            if group_path in existing and existing[group_path] != registry_name:
                self._runner.remove_repo(resolved_name, group_path)
                result.removed.append(group_path)
            self._runner.add_repo(resolved_name, group_path, registry_name)
            result.added.append(
                GitNexusGroupMemberAction(
                    group_path=group_path,
                    registry_name=registry_name,
                    repo_path=member["repo_path"],
                    action="add",
                )
            )

        if prune:
            for group_path in sorted(set(existing) - set(desired)):
                self._runner.remove_repo(resolved_name, group_path)
                result.removed.append(group_path)

        if run_contract_sync and (result.added or result.removed or desired):
            try:
                result.contract_sync = self._runner.sync_contracts(
                    resolved_name,
                    allow_stale=allow_stale,
                    skip_embeddings=skip_embeddings,
                    exact_only=exact_only,
                    verbose=verbose,
                )
                result.contract_sync_ran = True
            except RuntimeError as exc:
                result.contract_sync_error = str(exc)
                result.warnings.append(str(exc))

        if result.skipped:
            missing_registry = sum(1 for item in result.skipped if item.get("reason") == "not_in_gitnexus_registry")
            if missing_registry:
                result.warnings.append(f"{missing_registry} repos are not indexed; run gitnexus analyze")

        return result
