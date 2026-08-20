#!/usr/bin/env python
"""Resolve durable CI topology from remotes and on-disk CI config files."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import unquote, urlparse

from metagit import DATA_PATH
from metagit.core.project.ci_models import CiProvider, CiTargetStatus, RepoCiTarget

_LABEL_TO_PROVIDER: Dict[str, CiProvider] = {
    "github actions": CiProvider.GITHUB,
    "gitlab ci": CiProvider.GITLAB,
    "azure devops": CiProvider.AZURE_DEVOPS,
}


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_ci_file_map(path: Optional[str] = None) -> Dict[str, str]:
    map_path = path or os.path.join(DATA_PATH, "ci-files.json")
    try:
        with open(map_path, encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, dict):
            return {str(k): str(v) for k, v in payload.items()}
    except (OSError, json.JSONDecodeError, TypeError):
        return {}
    return {}


def split_remote_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    """Split a git remote into (host, path) without leading slash or .git."""
    text = (url or "").strip()
    if not text:
        return None, None
    if "://" not in text and "@" in text and ":" in text:
        # SCP-style: git@host:path or org@vs-ssh.visualstudio.com:v3/...
        _, remainder = text.split("@", 1)
        host, _, path = remainder.partition(":")
        path = path.lstrip("/").removesuffix(".git")
        return host.lower() or None, path or None
    parsed = urlparse(text)
    host = (parsed.hostname or "").lower() or None
    path = unquote(parsed.path or "").lstrip("/").removesuffix(".git")
    return host, path or None


def provider_from_host(host: Optional[str]) -> CiProvider:
    """Map a git host to a CI provider hint."""
    if not host:
        return CiProvider.UNKNOWN
    lowered = host.lower()
    if "github" in lowered:
        return CiProvider.GITHUB
    if "gitlab" in lowered:
        return CiProvider.GITLAB
    if "dev.azure.com" in lowered or "visualstudio.com" in lowered or lowered.startswith("ssh.dev.azure."):
        return CiProvider.AZURE_DEVOPS
    return CiProvider.UNKNOWN


def parse_remote_locator(url: str) -> Dict[str, Any]:
    """Extract provider-specific locator fields from a git remote URL."""
    host, path = split_remote_url(url)
    provider = provider_from_host(host)
    result: Dict[str, Any] = {"provider": provider, "host": host}
    if not path:
        return result
    parts = [part for part in path.split("/") if part]
    if provider == CiProvider.AZURE_DEVOPS:
        # HTTPS: {org}/{project}/_git/{repo}
        # SSH v3: v3/{org}/{project}/{repo}
        if parts and parts[0].lower() == "v3":
            parts = parts[1:]
        if "_git" in parts:
            git_idx = parts.index("_git")
            org = parts[0] if git_idx >= 1 else None
            project = "/".join(parts[1:git_idx]) if git_idx >= 2 else None
            repo = parts[git_idx + 1] if git_idx + 1 < len(parts) else None
        elif len(parts) >= 3:
            org, project, repo = parts[0], parts[1], parts[2]
        else:
            org = parts[0] if parts else None
            project = parts[1] if len(parts) > 1 else None
            repo = parts[2] if len(parts) > 2 else None
        result["organization"] = org
        result["project"] = project
        result["repository"] = repo
        return result
    if provider == CiProvider.GITHUB and len(parts) >= 2:
        result["owner"] = parts[0]
        result["name"] = parts[1]
        return result
    if provider == CiProvider.GITLAB and parts:
        result["project_path"] = "/".join(parts)
        if len(parts) >= 2:
            result["owner"] = parts[0]
            result["name"] = parts[-1]
        return result
    return result


def _provider_from_label(label: str) -> CiProvider:
    return _LABEL_TO_PROVIDER.get(label.strip().lower(), CiProvider.OTHER)


def scan_ci_config_paths(
    repo_path: Optional[str],
    *,
    ci_file_map: Optional[Dict[str, str]] = None,
) -> Tuple[List[str], Optional[CiProvider]]:
    """Find CI config files under a local checkout and infer a primary provider."""
    if not repo_path:
        return [], None
    root = Path(repo_path)
    if not root.is_dir():
        return [], None
    mapping = ci_file_map if ci_file_map is not None else _load_ci_file_map()
    found: List[Tuple[str, CiProvider]] = []
    for pattern, label in mapping.items():
        provider = _provider_from_label(label)
        if "*" in pattern or "?" in pattern:
            parent = root / Path(pattern).parent
            if not parent.is_dir():
                continue
            for child in sorted(parent.iterdir()):
                if not child.is_file():
                    continue
                rel = child.relative_to(root).as_posix()
                if fnmatch(rel, pattern.replace("\\", "/")):
                    found.append((rel, provider))
            continue
        candidate = root / pattern
        if candidate.is_file():
            found.append((pattern.replace("\\", "/"), provider))
    # Prefer first-party platforms when multiple configs exist
    preference = [
        CiProvider.AZURE_DEVOPS,
        CiProvider.GITHUB,
        CiProvider.GITLAB,
        CiProvider.OTHER,
    ]
    primary: Optional[CiProvider] = None
    for preferred in preference:
        if any(item[1] == preferred for item in found):
            primary = preferred
            break
    if primary is None and found:
        primary = found[0][1]
    paths = sorted({path for path, _ in found})
    return paths, primary


class CiTargetResolver:
    """Derive ``RepoCiTarget`` from remotes, CI files, and existing bindings."""

    def __init__(self, *, ci_file_map: Optional[Dict[str, str]] = None) -> None:
        self._ci_file_map = ci_file_map

    def resolve(
        self,
        *,
        repo_path: Optional[str] = None,
        url: Optional[str] = None,
        existing_ci: Optional[RepoCiTarget] = None,
        force: bool = False,
    ) -> Optional[RepoCiTarget]:
        """
        Resolve CI topology for a repository.

        Preserves declared/overridden bindings unless ``force`` is true.
        Returns None when nothing useful can be asserted (omit from manifests).
        """
        if existing_ci is not None and not force:
            status = existing_ci.status
            status_value = status.value if isinstance(status, CiTargetStatus) else str(status)
            if status_value in {CiTargetStatus.DECLARED.value, CiTargetStatus.OVERRIDDEN.value}:
                return existing_ci

        locator = parse_remote_locator(str(url)) if url else {"provider": CiProvider.UNKNOWN}
        config_paths, file_provider = scan_ci_config_paths(
            repo_path,
            ci_file_map=self._ci_file_map,
        )
        remote_provider = locator.get("provider", CiProvider.UNKNOWN)
        if not isinstance(remote_provider, CiProvider):
            try:
                remote_provider = CiProvider(str(remote_provider))
            except ValueError:
                remote_provider = CiProvider.UNKNOWN

        provider = file_provider or remote_provider
        if provider == CiProvider.UNKNOWN and not config_paths and not url:
            return None
        if provider == CiProvider.UNKNOWN and not config_paths:
            # Remote present but unrecognized and no CI files — still useful for Phase 2 fallback
            if remote_provider == CiProvider.UNKNOWN:
                return None
            provider = remote_provider
        if provider is None:
            provider = CiProvider.NONE

        target = RepoCiTarget(
            provider=provider if provider != CiProvider.UNKNOWN or config_paths else CiProvider.NONE,
            config_paths=config_paths,
            host=locator.get("host"),
            organization=locator.get("organization"),
            project=locator.get("project"),
            repository=locator.get("repository"),
            owner=locator.get("owner"),
            name=locator.get("name"),
            project_path=locator.get("project_path"),
            status=CiTargetStatus.DETECTED,
            updated_at=_iso_now(),
        )
        if force and existing_ci is not None and existing_ci.definition_ids and not target.definition_ids:
            target.definition_ids = list(existing_ci.definition_ids)
        if target.is_empty():
            return None
        # Prefer remote provider when files say "other" but remote is a known host
        if target.provider == CiProvider.OTHER and remote_provider in {
            CiProvider.GITHUB,
            CiProvider.GITLAB,
            CiProvider.AZURE_DEVOPS,
        }:
            target.provider = remote_provider
        return target

    def detect_for_url(self, url: str) -> Optional[RepoCiTarget]:
        """Detect locator-only CI target when no local checkout exists (e.g. source import)."""
        return self.resolve(url=url, force=True)


__all__ = [
    "CiTargetResolver",
    "parse_remote_locator",
    "provider_from_host",
    "scan_ci_config_paths",
    "split_remote_url",
]
