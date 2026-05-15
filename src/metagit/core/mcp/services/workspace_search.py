#!/usr/bin/env python
"""
Workspace-scoped search service using ripgrep with a bounded fallback scanner.
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional


class WorkspaceSearchService:
    """Search configured repositories with bounded, text-based matching."""

    _preset_terms: dict[str, list[str]] = {
        "terraform": ["terraform", "module", "variable", "tf"],
        "docker": ["docker", "from", "image", "container"],
        "infra": ["infra", "network", "cluster", "provision"],
        "ci": ["workflow", "pipeline", "actions", "runner"],
    }

    _intent_globs: dict[str, list[str]] = {
        "config": ["**/*.yml", "**/*.yaml", "**/*.toml", "**/.env.example"],
        "scripts": ["**/*.sh", "**/*.py", "**/scripts/**"],
        "ci": ["**/.github/**", "**/.gitlab-ci.yml", "**/Jenkinsfile"],
        "docker": ["**/Dockerfile", "**/docker-compose*.yml", "**/*.dockerfile"],
        "terraform": ["**/*.tf", "**/*.tfvars"],
    }

    _default_exclude: list[str] = [
        "**/.git/**",
        "**/node_modules/**",
        "**/__pycache__/**",
        "**/.venv/**",
        "**/dist/**",
        "**/build/**",
    ]

    _generated_exclude: list[str] = [
        "**/vendor/**",
        "**/generated/**",
        "**/*.min.js",
        "**/*.min.css",
        "**/package-lock.json",
        "**/yarn.lock",
        "**/pnpm-lock.yaml",
    ]

    _category_rules: list[tuple[str, list[str]]] = [
        ("config", ["**/*.yml", "**/*.yaml", "**/*.toml", "**/.env.example"]),
        ("scripts", ["**/*.sh", "**/*.py", "**/scripts/**"]),
        ("ci", ["**/.github/**", "**/.gitlab-ci.yml", "**/Jenkinsfile"]),
        ("docker", ["**/Dockerfile", "**/docker-compose*.yml"]),
        ("terraform", ["**/*.tf", "**/*.tfvars"]),
        ("docs", ["**/*.md", "**/docs/**"]),
    ]

    def search(
        self,
        query: str,
        repo_paths: list[str],
        preset: Optional[str] = None,
        max_results: int = 25,
        paths: Optional[list[str]] = None,
        exclude: Optional[list[str]] = None,
        context_lines: int = 0,
        include_paths: bool = False,
        intent: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Search across scoped repository paths and return bounded hits."""
        if not repo_paths:
            return []
        glob_paths = list(paths or [])
        if intent and intent in self._intent_globs:
            glob_paths = list(dict.fromkeys(glob_paths + self._intent_globs[intent]))
        exclude_globs = list(dict.fromkeys((exclude or []) + self._default_exclude))
        search_query = self._compose_query(query=query, preset=preset)
        results: list[dict[str, Any]] = []
        for repo_path in repo_paths:
            root = Path(repo_path).expanduser().resolve()
            if not root.exists() or not root.is_dir():
                continue
            if shutil.which("rg"):
                hits = self._search_with_rg(
                    root=root,
                    query=search_query,
                    glob_paths=glob_paths,
                    exclude_globs=exclude_globs,
                    context_lines=context_lines,
                    include_paths=include_paths,
                    max_results=max_results - len(results),
                )
            else:
                hits = self._search_fallback(
                    root=root,
                    query=search_query,
                    max_results=max_results - len(results),
                )
            results.extend(hits)
            if len(results) >= max_results:
                return results[:max_results]
        return results[:max_results]

    def filter_repo_paths(
        self,
        repo_rows: list[dict[str, Any]],
        repos: Optional[list[str]] = None,
    ) -> list[str]:
        """Resolve repo path list from index rows and optional repo selectors."""
        if not repos or repos == ["all"]:
            return [str(row["repo_path"]) for row in repo_rows if row.get("exists")]
        selectors = {item.strip() for item in repos if item.strip()}
        selected: list[str] = []
        for row in repo_rows:
            repo_path = str(row.get("repo_path", ""))
            repo_name = str(row.get("repo_name", ""))
            project_name = str(row.get("project_name", ""))
            keys = {repo_path, repo_name, project_name, f"{project_name}/{repo_name}"}
            if selectors.intersection(keys):
                if row.get("exists"):
                    selected.append(repo_path)
        return selected

    def _compose_query(self, query: str, preset: Optional[str]) -> str:
        """Build ripgrep query text from user query and optional preset terms."""
        terms = self._terms(query=query, preset=preset)
        if not terms:
            return query
        if len(terms) == 1:
            return terms[0]
        return "|".join(terms)

    def _search_with_rg(
        self,
        root: Path,
        query: str,
        glob_paths: list[str],
        exclude_globs: list[str],
        context_lines: int,
        include_paths: bool,
        max_results: int,
    ) -> list[dict[str, Any]]:
        """Run ripgrep and parse JSON output into hit records."""
        if max_results < 1:
            return []
        cmd = [
            "rg",
            "--json",
            "--max-count",
            str(max_results),
            "--no-messages",
        ]
        if include_paths:
            cmd.append("--files-with-matches")
        if context_lines > 0 and not include_paths:
            cmd.extend(["-C", str(context_lines)])
        for pattern in exclude_globs:
            cmd.extend(["--glob", f"!{pattern}"])
        for pattern in glob_paths:
            cmd.extend(["--glob", pattern])
        if query.strip():
            cmd.append(query)
        cmd.append(str(root))

        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return []

        if completed.returncode not in {0, 1}:
            return []

        hits: list[dict[str, Any]] = []
        context_before: list[str] = []
        context_after: list[str] = []
        for line in completed.stdout.splitlines():
            if len(hits) >= max_results:
                break
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            message_type = payload.get("type")
            data = payload.get("data", {})
            if message_type == "context":
                context_text = str(data.get("lines", {}).get("text", "")).rstrip("\n")
                if data.get("line_number") is None:
                    context_before.append(context_text)
                else:
                    context_after.append(context_text)
                continue
            if message_type != "match":
                continue
            path_text = str(data.get("path", {}).get("text", ""))
            line_number = int(data.get("line_number", 0))
            line_text = str(data.get("lines", {}).get("text", "")).rstrip("\n")
            hit = {
                "repo_path": str(root),
                "file_path": path_text,
                "line_number": line_number,
                "line": line_text,
                "context_before": list(context_before),
                "context_after": list(context_after),
                "match_kind": "path" if include_paths else "content",
            }
            hits.append(hit)
            context_before = []
            context_after = []
        return hits

    def _search_fallback(
        self,
        root: Path,
        query: str,
        max_results: int,
    ) -> list[dict[str, Any]]:
        """Fallback scanner when ripgrep is unavailable."""
        terms = [term.lower() for term in query.lower().split() if term]
        if not terms:
            return []
        results: list[dict[str, Any]] = []
        for file_path in root.rglob("*"):
            if len(results) >= max_results:
                return results
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
                            "context_before": [],
                            "context_after": [],
                            "match_kind": "content",
                        }
                    )
                    if len(results) >= max_results:
                        return results
        return results

    def discover_files(
        self,
        repo_paths: list[str],
        *,
        intent: Optional[str] = None,
        pattern: Optional[str] = None,
        exclude_generated: bool = True,
        max_results: int = 200,
        categorize: bool = True,
    ) -> dict[str, Any]:
        """Discover files by intent or glob pattern across repositories."""
        glob_paths: list[str] = []
        if pattern:
            glob_paths.append(pattern)
        if intent and intent in self._intent_globs:
            glob_paths.extend(self._intent_globs[intent])
        if not glob_paths:
            glob_paths = ["**/*"]
        exclude_globs = list(self._default_exclude)
        if exclude_generated:
            exclude_globs.extend(self._generated_exclude)

        files: list[dict[str, str]] = []
        for repo_path in repo_paths:
            root = Path(repo_path).expanduser().resolve()
            if not root.exists() or not root.is_dir():
                continue
            discovered = self._list_files_with_rg(
                root=root,
                glob_paths=glob_paths,
                exclude_globs=exclude_globs,
                max_results=max_results - len(files),
            )
            for file_path in discovered:
                files.append({"repo_path": str(root), "file_path": file_path})
            if len(files) >= max_results:
                break

        payload: dict[str, Any] = {
            "total": len(files[:max_results]),
            "files": files[:max_results],
        }
        if categorize:
            payload["categories"] = self._categorize_files(files=files[:max_results])
        return payload

    def _list_files_with_rg(
        self,
        root: Path,
        glob_paths: list[str],
        exclude_globs: list[str],
        max_results: int,
    ) -> list[str]:
        """List files in a repo root using ripgrep or directory walk."""
        if max_results < 1:
            return []
        if shutil.which("rg"):
            cmd = ["rg", "--files", "--no-messages"]
            for pattern in exclude_globs:
                cmd.extend(["--glob", f"!{pattern}"])
            for pattern in glob_paths:
                cmd.extend(["--glob", pattern])
            cmd.append(str(root))
            try:
                completed = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                )
            except OSError:
                completed = None
            if completed and completed.returncode in {0, 1}:
                lines = [
                    line.strip()
                    for line in completed.stdout.splitlines()
                    if line.strip()
                ]
                return lines[:max_results]
        return self._list_files_fallback(
            root=root,
            glob_paths=glob_paths,
            exclude_globs=exclude_globs,
            max_results=max_results,
        )

    def _list_files_fallback(
        self,
        root: Path,
        glob_paths: list[str],
        exclude_globs: list[str],
        max_results: int,
    ) -> list[str]:
        """Fallback file listing without ripgrep."""
        _ = exclude_globs
        results: list[str] = []
        for glob_pattern in glob_paths:
            for file_path in root.glob(glob_pattern):
                if len(results) >= max_results:
                    return results
                if not file_path.is_file():
                    continue
                if self._is_ignored(file_path=file_path):
                    continue
                results.append(str(file_path))
        return results[:max_results]

    def _categorize_files(
        self, files: list[dict[str, str]]
    ) -> dict[str, list[dict[str, str]]]:
        """Group discovered files into coarse categories."""
        categories: dict[str, list[dict[str, str]]] = {}
        for item in files:
            category = self._category_for_path(file_path=item.get("file_path", ""))
            categories.setdefault(category, []).append(item)
        return categories

    def _category_for_path(self, file_path: str) -> str:
        """Assign a category label for a file path."""
        lower = file_path.lower()
        if "/.github/" in lower or ".gitlab-ci" in lower or "jenkinsfile" in lower:
            return "ci"
        if "dockerfile" in lower or "docker-compose" in lower:
            return "docker"
        if lower.endswith((".tf", ".tfvars", ".tf.json")):
            return "terraform"
        if lower.endswith((".md", ".rst")) or "/docs/" in lower:
            return "docs"
        if lower.endswith((".sh", ".py", ".rb", ".js", ".ts")) or "/scripts/" in lower:
            return "scripts"
        if lower.endswith((".yml", ".yaml", ".toml", ".ini", ".cfg", ".env.example")):
            return "config"
        return "other"

    def _terms(self, query: str, preset: Optional[str]) -> list[str]:
        query_terms = [term for term in query.split() if term]
        if preset and preset in self._preset_terms:
            return list(dict.fromkeys(query_terms + self._preset_terms[preset]))
        return query_terms

    def _is_ignored(self, file_path: Path) -> bool:
        name = file_path.name
        return name.startswith(".") or name.endswith((".png", ".jpg", ".jpeg", ".gif"))
