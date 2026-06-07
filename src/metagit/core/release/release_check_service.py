#!/usr/bin/env python
"""Compare installed Metagit against published GitHub/PyPI releases."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import requests

from metagit import __version__
from metagit.core.release.install_detect import (
    build_upgrade_command,
    detect_install_method,
)
from metagit.core.release.models import LatestReleaseInfo, VersionCheckResult
from metagit.core.release.version_compare import compare_versions

_DEFAULT_GITHUB_REPO = "metagit-ai/metagit-cli"
_DEFAULT_PYPI_PACKAGE = "metagit-cli"
_DEFAULT_GITHUB_API = "https://api.github.com"
_DEFAULT_PYPI_API = "https://pypi.org/pypi"
_REQUEST_TIMEOUT_SECONDS = 15


class ReleaseCheckService:
    """Fetch latest release metadata and compare to the installed package."""

    def __init__(
        self,
        *,
        github_repo: str = _DEFAULT_GITHUB_REPO,
        pypi_package: str = _DEFAULT_PYPI_PACKAGE,
        github_api_base: str = _DEFAULT_GITHUB_API,
        pypi_api_base: str = _DEFAULT_PYPI_API,
        github_token: str | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self._github_repo = github_repo
        self._pypi_package = pypi_package
        self._github_api_base = github_api_base.rstrip("/")
        self._pypi_api_base = pypi_api_base.rstrip("/")
        self._session = session or requests.Session()
        self._github_token = github_token

    def check(
        self,
        *,
        installed_version: str | None = None,
        include_notes: bool = True,
    ) -> VersionCheckResult:
        """Return installed vs latest release comparison."""
        installed = (installed_version or __version__).strip()
        fetch_errors: list[str] = []
        github_release = self._fetch_github_latest(
            include_notes=include_notes,
            fetch_errors=fetch_errors,
        )
        pypi_version = self._fetch_pypi_latest(fetch_errors=fetch_errors)
        latest_release = github_release
        if latest_release is None and pypi_version is not None:
            latest_release = LatestReleaseInfo(
                version=pypi_version,
                html_url=f"https://pypi.org/project/{self._pypi_package}/{pypi_version}/",
                source="pypi",
            )

        update_available = False
        is_latest = True
        if latest_release is not None:
            cmp = compare_versions(installed, latest_release.version)
            update_available = cmp < 0
            is_latest = cmp >= 0
        elif pypi_version is not None:
            cmp = compare_versions(installed, pypi_version)
            update_available = cmp < 0
            is_latest = cmp >= 0

        install_method = detect_install_method()
        return VersionCheckResult(
            installed_version=installed,
            latest_release=latest_release,
            pypi_version=pypi_version,
            update_available=update_available,
            is_latest=is_latest,
            install_command=build_upgrade_command(install_method),
            fetch_errors=fetch_errors,
        )

    def _github_headers(self, *, use_token: bool = True) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": f"metagit-cli/{__version__}",
        }
        if not use_token:
            return headers
        token = self._github_token or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _fetch_github_latest(
        self,
        *,
        include_notes: bool,
        fetch_errors: list[str],
    ) -> LatestReleaseInfo | None:
        url = f"{self._github_api_base}/repos/{self._github_repo}/releases/latest"
        try:
            response = self._session.get(
                url,
                headers=self._github_headers(use_token=True),
                timeout=_REQUEST_TIMEOUT_SECONDS,
            )
            if response.status_code == 401:
                response = self._session.get(
                    url,
                    headers=self._github_headers(use_token=False),
                    timeout=_REQUEST_TIMEOUT_SECONDS,
                )
            if response.status_code == 404:
                fetch_errors.append("GitHub latest release not found")
                return None
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
        except requests.RequestException as exc:
            fetch_errors.append(f"GitHub release lookup failed: {exc}")
            return None

        tag_name = str(payload.get("tag_name") or "").strip()
        version = tag_name.lstrip("vV") or str(payload.get("name") or "").strip()
        if not version:
            fetch_errors.append("GitHub latest release missing version")
            return None

        published_raw = payload.get("published_at")
        published_at = None
        if isinstance(published_raw, str) and published_raw:
            published_at = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))

        body = str(payload.get("body") or "").strip() or None
        if not include_notes:
            body = None

        return LatestReleaseInfo(
            version=version,
            tag_name=tag_name or None,
            name=str(payload.get("name") or "").strip() or None,
            published_at=published_at,
            html_url=str(payload.get("html_url") or "").strip() or None,
            body=body,
            source="github",
        )

    def _fetch_pypi_latest(self, *, fetch_errors: list[str]) -> str | None:
        url = f"{self._pypi_api_base}/{self._pypi_package}/json"
        try:
            response = self._session.get(url, timeout=_REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            info = payload.get("info")
            if not isinstance(info, dict):
                fetch_errors.append("PyPI response missing package info")
                return None
            version = str(info.get("version") or "").strip()
            return version or None
        except requests.RequestException as exc:
            fetch_errors.append(f"PyPI version lookup failed: {exc}")
            return None
