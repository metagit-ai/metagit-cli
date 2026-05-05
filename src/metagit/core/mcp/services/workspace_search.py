#!/usr/bin/env python
"""
Workspace-scoped search service.
"""

from pathlib import Path
from typing import Optional


class WorkspaceSearchService:
    """Search configured repositories with bounded, text-based matching."""

    _preset_terms: dict[str, list[str]] = {
        "terraform": ["terraform", "module", "variable", "tf"],
        "docker": ["docker", "from", "image", "container"],
        "infra": ["infra", "network", "cluster", "provision"],
        "ci": ["workflow", "pipeline", "actions", "runner"],
    }

    def search(
        self,
        query: str,
        repo_paths: list[str],
        preset: Optional[str] = None,
        max_results: int = 25,
    ) -> list[dict[str, str | int]]:
        """Search across scoped repository paths and return bounded line hits."""
        terms = self._terms(query=query, preset=preset)
        results: list[dict[str, str | int]] = []

        for repo_path in repo_paths:
            root = Path(repo_path).expanduser().resolve()
            if not root.exists() or not root.is_dir():
                continue

            for file_path in root.rglob("*"):
                if not file_path.is_file():
                    continue
                if file_path.stat().st_size > 1_000_000:
                    continue
                if self._is_ignored(file_path=file_path):
                    continue

                try:
                    lines = file_path.read_text(encoding="utf-8").splitlines()
                except (UnicodeDecodeError, OSError):
                    continue

                for idx, line in enumerate(lines, start=1):
                    lower_line = line.lower()
                    if any(term in lower_line for term in terms):
                        results.append(
                            {
                                "repo_path": str(root),
                                "file_path": str(file_path),
                                "line_number": idx,
                                "line": line.strip(),
                            }
                        )
                        if len(results) >= max_results:
                            return results
        return results

    def _terms(self, query: str, preset: Optional[str]) -> list[str]:
        query_terms = [term for term in query.lower().split() if term]
        if preset and preset in self._preset_terms:
            return list(dict.fromkeys(query_terms + self._preset_terms[preset]))
        return query_terms

    def _is_ignored(self, file_path: Path) -> bool:
        name = file_path.name
        return name.startswith(".") or name.endswith((".png", ".jpg", ".jpeg", ".gif"))
