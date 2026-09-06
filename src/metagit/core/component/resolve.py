#!/usr/bin/env python
"""Path-to-component longest-match resolver and identity lookup."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from metagit.core.component.catalog import ComponentCatalog, ResolvedComponent
from metagit.core.component.identity import parse_component_id
from metagit.core.component.paths import normalize_repo_relative_path
from metagit.core.config.models import MetagitConfig


def resolved_component_payload(row: ResolvedComponent) -> dict[str, Any]:
    """Stable JSON object for CLI/MCP/web adapters."""
    return {
        "id": row.id,
        "project": row.project,
        "repo": row.repo,
        "name": row.name,
        "path": row.spec.path,
        "source": row.source,
        "kind": row.spec.kind,
        "spec": row.spec.model_dump(mode="json"),
    }


def _path_rank(normalized: str) -> int:
    return 0 if normalized == "." else len(normalized.split("/"))


def _matches(query: str, component_path: str) -> bool:
    if component_path == ".":
        return True
    return query == component_path or query.startswith(component_path + "/")


class ComponentResolver:
    """List, look up, and longest-match resolve catalogued components."""

    def __init__(self, catalog: ComponentCatalog | None = None) -> None:
        self._catalog = catalog or ComponentCatalog()

    def list(
        self,
        config: MetagitConfig,
        *,
        project: str | None = None,
        repo: str | None = None,
    ) -> list[ResolvedComponent]:
        rows = self._catalog.list(config)
        if project:
            rows = [row for row in rows if row.project == project]
        if repo:
            rows = [row for row in rows if row.repo == repo]
        return rows

    def get(
        self,
        config: MetagitConfig,
        identity: str,
        *,
        project: str | None = None,
        repo: str | None = None,
    ) -> ResolvedComponent | None | ValueError:
        rows = self.list(config, project=project, repo=repo)
        parsed = parse_component_id(identity)
        if not isinstance(parsed, Exception):
            key = parsed.key
            for row in rows:
                if row.id == key:
                    return row
            return None
        name = str(identity).strip()
        if not name or "/" in name:
            return (
                parsed
                if isinstance(parsed, ValueError)
                else ValueError(f"invalid component id {identity!r}; expected project/repo/component")
            )
        hits = [row for row in rows if row.name == name]
        if not hits:
            return None
        if len(hits) > 1:
            return ValueError(f"ambiguous component name {name!r}; use project/repo/component")
        return hits[0]

    def resolve(
        self,
        config: MetagitConfig,
        path: str,
        *,
        project: str | None = None,
        repo: str | None = None,
        definition_root: str | Path | None = None,
    ) -> ResolvedComponent | None | ValueError:
        mapped = None
        if definition_root is not None:
            mapped = self._map_filesystem_path(config, path, definition_root=Path(definition_root))
            if isinstance(mapped, Exception):
                return mapped
        query_raw = path
        scoped_project = project
        scoped_repo = repo
        if mapped is not None:
            scoped_project, scoped_repo, query_raw = mapped
        normalized = normalize_repo_relative_path(query_raw)
        if isinstance(normalized, Exception):
            return normalized
        rows = self.list(config, project=scoped_project, repo=scoped_repo)
        winners: list[ResolvedComponent] = []
        grouped: dict[tuple[str, str], list[tuple[int, ResolvedComponent]]] = {}
        for row in rows:
            cpath = normalize_repo_relative_path(row.spec.path)
            if isinstance(cpath, Exception):
                continue
            if not _matches(normalized, cpath):
                continue
            grouped.setdefault((row.project, row.repo), []).append((_path_rank(cpath), row))
        for matches in grouped.values():
            _, best = max(matches, key=lambda item: item[0])
            winners.append(best)
        if scoped_project and scoped_repo:
            return winners[0] if winners else None
        if not winners:
            return None
        if len(winners) > 1:
            return ValueError("ambiguous component path; pass --project and --repo")
        return winners[0]

    def _map_filesystem_path(
        self,
        config: MetagitConfig,
        path: str,
        *,
        definition_root: Path,
    ) -> tuple[str, str, str] | None | ValueError:
        candidate = Path(path).expanduser()
        abs_candidates: list[Path] = []
        if candidate.is_absolute():
            abs_candidates.append(candidate)
        else:
            cwd_try = Path.cwd() / candidate
            root_try = definition_root / candidate
            if cwd_try.exists():
                abs_candidates.append(cwd_try.resolve())
            if root_try.exists():
                abs_candidates.append(root_try.resolve())
        if not abs_candidates:
            return None
        target = abs_candidates[0]
        best: tuple[int, str, str, str] | None = None
        rows = self._catalog.list(config)
        seen: set[tuple[str, str]] = set()
        for row in rows:
            key = (row.project, row.repo)
            if key in seen:
                continue
            seen.add(key)
            repo_root = self._repo_root(config, row.project, row.repo, definition_root)
            if repo_root is None:
                continue
            try:
                rel = target.relative_to(repo_root.resolve())
            except ValueError:
                continue
            rel_text = "." if str(rel) in {"", "."} else rel.as_posix()
            rank = len(str(repo_root.resolve()).split("/"))
            if best is None or rank > best[0]:
                best = (rank, row.project, row.repo, rel_text)
        if best is None:
            return None
        return best[1], best[2], best[3]

    def _repo_root(
        self,
        config: MetagitConfig,
        project: str,
        repo: str,
        definition_root: Path,
    ) -> Path | None:
        if config.workspace is not None:
            for wsp in config.workspace.projects:
                if wsp.name != project:
                    continue
                for entry in wsp.repos:
                    if entry.name != repo:
                        continue
                    rel = entry.path or "."
                    return (definition_root / rel).resolve()
            return None
        return definition_root.resolve()
