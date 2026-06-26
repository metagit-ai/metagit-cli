#!/usr/bin/env python
"""
Lightweight import/reference scanning between workspace repositories.
"""

import json
import re
from pathlib import Path
from typing import Any, Optional

_PATH_DEP_PATTERN = re.compile(r"(?:file:|path:)\s*['\"]?([^'\"\s]+)['\"]?", re.IGNORECASE)
_GO_REPLACE_PATTERN = re.compile(r"^\s*replace\s+[^\s]+\s+=>\s+(.+)$", re.MULTILINE)
_TERRAFORM_MODULE_PATTERN = re.compile(r'source\s*=\s*"([^"]+)"', re.IGNORECASE)


class ImportHintScanner:
    """Detect cross-repo references from common manifest files."""

    def scan_repo(
        self,
        repo_path: str,
        path_to_repo_id: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Return import edges from one repo to other workspace repos."""
        root = Path(repo_path).expanduser().resolve()
        if not root.is_dir():
            return []
        hints: list[dict[str, Any]] = []
        candidates = [
            root / "package.json",
            root / "pyproject.toml",
            root / "go.mod",
            root / "requirements.txt",
        ]
        for candidate in candidates:
            if not candidate.is_file():
                continue
            try:
                text = candidate.read_text(encoding="utf-8")
            except OSError:
                continue
            if candidate.name == "package.json":
                hints.extend(
                    self._scan_package_json(
                        root=root,
                        text=text,
                        file_path=str(candidate),
                        path_to_repo_id=path_to_repo_id,
                    )
                )
            elif candidate.name == "pyproject.toml":
                hints.extend(
                    self._scan_text_paths(
                        root=root,
                        text=text,
                        file_path=str(candidate),
                        path_to_repo_id=path_to_repo_id,
                    )
                )
            elif candidate.name == "go.mod":
                hints.extend(
                    self._scan_go_mod(
                        root=root,
                        text=text,
                        file_path=str(candidate),
                        path_to_repo_id=path_to_repo_id,
                    )
                )
            else:
                hints.extend(
                    self._scan_text_paths(
                        root=root,
                        text=text,
                        file_path=str(candidate),
                        path_to_repo_id=path_to_repo_id,
                    )
                )
        hints.extend(
            self._scan_terraform_modules(
                root=root,
                path_to_repo_id=path_to_repo_id,
            )
        )
        return hints

    def _scan_package_json(
        self,
        root: Path,
        text: str,
        file_path: str,
        path_to_repo_id: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Scan npm package.json for file/workspace path dependencies."""
        hints: list[dict[str, Any]] = []
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return hints
        sections = []
        for key in ("dependencies", "devDependencies", "peerDependencies"):
            value = payload.get(key)
            if isinstance(value, dict):
                sections.append(value)
        for section in sections:
            for dep_name, dep_ref in section.items():
                if not isinstance(dep_ref, str):
                    continue
                target_id = self._resolve_reference(
                    root=root,
                    reference=dep_ref,
                    path_to_repo_id=path_to_repo_id,
                )
                if target_id:
                    hints.append(
                        {
                            "to_id": target_id,
                            "evidence": [f"{file_path}: dependency {dep_name} -> {dep_ref}"],
                        }
                    )
        return hints

    def _scan_go_mod(
        self,
        root: Path,
        text: str,
        file_path: str,
        path_to_repo_id: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Scan go.mod replace directives for local paths."""
        hints: list[dict[str, Any]] = []
        for match in _GO_REPLACE_PATTERN.finditer(text):
            reference = match.group(1).strip()
            target_id = self._resolve_reference(
                root=root,
                reference=reference,
                path_to_repo_id=path_to_repo_id,
            )
            if target_id:
                hints.append(
                    {
                        "to_id": target_id,
                        "evidence": [f"{file_path}: replace => {reference}"],
                    }
                )
        return hints

    def _scan_text_paths(
        self,
        root: Path,
        text: str,
        file_path: str,
        path_to_repo_id: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Scan generic text for file:/path: references."""
        hints: list[dict[str, Any]] = []
        for match in _PATH_DEP_PATTERN.finditer(text):
            reference = match.group(1).strip()
            target_id = self._resolve_reference(
                root=root,
                reference=reference,
                path_to_repo_id=path_to_repo_id,
            )
            if target_id:
                hints.append(
                    {
                        "to_id": target_id,
                        "evidence": [f"{file_path}: path reference {reference}"],
                    }
                )
        return hints

    def _scan_terraform_modules(
        self,
        root: Path,
        path_to_repo_id: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Scan terraform files for module sources pointing at sibling repos."""
        hints: list[dict[str, Any]] = []
        for tf_file in list(root.rglob("*.tf"))[:40]:
            if not tf_file.is_file():
                continue
            try:
                text = tf_file.read_text(encoding="utf-8")
            except OSError:
                continue
            for match in _TERRAFORM_MODULE_PATTERN.finditer(text):
                reference = match.group(1).strip()
                if reference.startswith(("git::", "http://", "https://", "registry")):
                    continue
                target_id = self._resolve_reference(
                    root=root,
                    reference=reference,
                    path_to_repo_id=path_to_repo_id,
                )
                if target_id:
                    hints.append(
                        {
                            "to_id": target_id,
                            "evidence": [f"{tf_file}: module source {reference}"],
                        }
                    )
        return hints

    def _resolve_reference(
        self,
        root: Path,
        reference: str,
        path_to_repo_id: dict[str, str],
        file_path: str = "",
    ) -> Optional[str]:
        """Resolve a relative reference to another workspace repo node id."""
        _ = file_path
        cleaned = reference.removeprefix("file:").strip()
        if cleaned.startswith((".", "/")):
            resolved = (root / cleaned).resolve()
            for repo_path, node_id in path_to_repo_id.items():
                repo_root = Path(repo_path).resolve()
                if resolved == repo_root or repo_root in resolved.parents:
                    return node_id
        return None
