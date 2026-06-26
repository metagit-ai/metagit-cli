#!/usr/bin/env python
"""
Apply packaged workspace templates to workspace projects.
"""

from __future__ import annotations

import contextlib
import os
import shutil
from pathlib import Path
from typing import Any, Optional

from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService


class WorkspaceTemplateService:
    """Copy template files into workspace project directories."""

    def __init__(self, index_service: Optional[WorkspaceIndexService] = None) -> None:
        self._index = index_service or WorkspaceIndexService()

    def apply(
        self,
        config: MetagitConfig,
        workspace_root: str,
        template: str,
        target_projects: list[str],
        *,
        dry_run: bool = True,
        confirm_apply: bool = False,
    ) -> dict[str, Any]:
        """Preview or apply a template to target workspace projects."""
        template_dir = self._resolve_template_dir(template=template)
        if template_dir is None:
            return {
                "ok": False,
                "error": "template_not_found",
                "template": template,
                "results": [],
            }
        if not target_projects:
            return {
                "ok": False,
                "error": "target_projects_required",
                "template": template,
                "results": [],
            }
        if not dry_run and not confirm_apply:
            return {
                "ok": False,
                "error": "confirm_apply_required",
                "template": template,
                "results": [],
            }

        rows = self._index.build_index(config=config, workspace_root=workspace_root)
        project_names = {project.name for project in (config.workspace.projects or [])}
        results: list[dict[str, Any]] = []
        for project_name in target_projects:
            if project_name not in project_names:
                results.append(
                    {
                        "project_name": project_name,
                        "ok": False,
                        "error": "project_not_found",
                        "files": [],
                    }
                )
                continue
            target_root = self._project_target_root(
                workspace_root=workspace_root,
                project_name=project_name,
                rows=rows,
            )
            if target_root is None:
                results.append(
                    {
                        "project_name": project_name,
                        "ok": False,
                        "error": "no_target_path",
                        "files": [],
                    }
                )
                continue
            planned = self._plan_copy(template_dir=template_dir, target_root=target_root)
            if dry_run:
                results.append(
                    {
                        "project_name": project_name,
                        "ok": True,
                        "dry_run": True,
                        "target_root": target_root,
                        "files": planned,
                    }
                )
                continue
            written = self._execute_copy(
                template_dir=template_dir,
                target_root=target_root,
                planned=planned,
            )
            results.append(
                {
                    "project_name": project_name,
                    "ok": True,
                    "dry_run": False,
                    "target_root": target_root,
                    "files": written,
                }
            )

        ok = all(item.get("ok") for item in results)
        return {
            "ok": ok,
            "template": template,
            "dry_run": dry_run,
            "results": results,
        }

    def list_templates(self) -> list[str]:
        """Return available template names."""
        root = self._templates_root()
        if not root.is_dir():
            return []
        return sorted([path.name for path in root.iterdir() if path.is_dir() and not path.name.startswith(".")])

    def _templates_root(self) -> Path:
        """Return packaged templates directory."""
        return Path(__file__).resolve().parents[3] / "data" / "templates"

    def _resolve_template_dir(self, template: str) -> Optional[Path]:
        """Resolve template directory if it exists."""
        if not template or ".." in template or "/" in template:
            return None
        candidate = self._templates_root() / template
        return candidate if candidate.is_dir() else None

    def _project_target_root(
        self,
        workspace_root: str,
        project_name: str,
        rows: list[dict[str, Any]],
    ) -> Optional[str]:
        """Choose a directory to receive template files for a project."""
        project_rows = [row for row in rows if row.get("project_name") == project_name]
        for row in project_rows:
            if row.get("exists"):
                return str(row.get("repo_path"))
        candidate = Path(workspace_root) / project_name
        if candidate.is_dir():
            return str(candidate.resolve())
        return None

    def _plan_copy(self, template_dir: Path, target_root: str) -> list[dict[str, str]]:
        """List files that would be copied."""
        planned: list[dict[str, str]] = []
        target = Path(target_root)
        for source in template_dir.rglob("*"):
            if not source.is_file():
                continue
            relative = source.relative_to(template_dir)
            destination = target / relative
            planned.append(
                {
                    "relative_path": str(relative),
                    "destination": str(destination),
                    "exists": "true" if destination.exists() else "false",
                }
            )
        return planned

    def _execute_copy(
        self,
        template_dir: Path,
        target_root: str,
        planned: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        """Copy planned files, skipping destinations that already exist."""
        written: list[dict[str, str]] = []
        target = Path(target_root)
        for item in planned:
            relative = item["relative_path"]
            destination = target / relative
            if destination.exists():
                item["status"] = "skipped_exists"
                written.append(item)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(template_dir / relative, destination)
            with contextlib.suppress(OSError):
                os.chmod(destination, 0o644)
            item["status"] = "written"
            written.append(item)
        return written
