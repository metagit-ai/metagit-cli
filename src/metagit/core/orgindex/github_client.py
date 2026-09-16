#!/usr/bin/env python
"""GitHub HTTP client for organization indexing (no clones)."""

from __future__ import annotations

import time
from typing import Any, Optional, Protocol

import requests

from metagit.core.appconfig.models import AppConfig


class GitHubOrgApi(Protocol):
    """Minimal GitHub API used by the organization indexer."""

    def list_org_repos(self, organization: str) -> list[dict[str, Any]] | Exception: ...

    def get_languages(self, owner: str, repo: str) -> dict[str, int] | Exception: ...

    def get_tree_paths(self, owner: str, repo: str, ref: str) -> list[str] | Exception: ...

    def get_open_pull_count(self, owner: str, repo: str) -> int | Exception: ...

    def get_latest_release(self, owner: str, repo: str) -> str | None | Exception: ...


def resolve_github_token(app_config: AppConfig | None) -> str:
    """Resolve a GitHub token from app config or the usual environment variables."""
    import os

    if app_config is not None:
        token = (app_config.providers.github.api_token or "").strip()
        if token:
            return token
    for key in ("METAGIT_GITHUB_API_TOKEN", "GITHUB_TOKEN", "GH_TOKEN"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return ""


def resolve_github_api_base(app_config: AppConfig | None) -> str:
    if app_config is not None and app_config.providers.github.base_url:
        return app_config.providers.github.base_url.rstrip("/")
    return "https://api.github.com"


class RequestsGitHubOrgClient:
    """GitHub organization client using the shared requests session pattern."""

    def __init__(
        self,
        *,
        token: str,
        base_url: str = "https://api.github.com",
        session: Optional[requests.Session] = None,
        timeout: int = 30,
        max_retries: int = 2,
        sleep: Any = time.sleep,
    ) -> None:
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._sleep = sleep
        self._session = session or requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def list_org_repos(self, organization: str) -> list[dict[str, Any]] | Exception:
        endpoint = f"{self._base_url}/orgs/{organization}/repos"
        items: list[dict[str, Any]] = []
        page = 1
        while True:
            payload = self._get(endpoint, params={"per_page": 100, "page": page, "type": "all"})
            if isinstance(payload, Exception):
                return payload
            if not isinstance(payload, list) or not payload:
                break
            items.extend(payload)
            if len(payload) < 100:
                break
            page += 1
        return items

    def get_languages(self, owner: str, repo: str) -> dict[str, int] | Exception:
        payload = self._get(f"{self._base_url}/repos/{owner}/{repo}/languages")
        if isinstance(payload, Exception):
            return payload
        if not isinstance(payload, dict):
            return {}
        return {str(key): int(value) for key, value in payload.items()}

    def get_tree_paths(self, owner: str, repo: str, ref: str) -> list[str] | Exception:
        payload = self._get(
            f"{self._base_url}/repos/{owner}/{repo}/git/trees/{ref}",
            params={"recursive": "1"},
        )
        if isinstance(payload, Exception):
            return payload
        if not isinstance(payload, dict):
            return []
        paths: list[str] = []
        for item in payload.get("tree") or []:
            if item.get("type") != "blob":
                continue
            path = item.get("path")
            if path:
                paths.append(str(path))
        return paths

    def get_open_pull_count(self, owner: str, repo: str) -> int | Exception:
        response = self._request(
            f"{self._base_url}/repos/{owner}/{repo}/pulls",
            params={"state": "open", "per_page": 1},
        )
        if isinstance(response, Exception):
            return response
        link = response.headers.get("Link", "")
        if 'rel="last"' in link:
            try:
                last = [part for part in link.split(",") if 'rel="last"' in part][0]
                page_token = [item for item in last.split(";")[0].strip(" <>").split("&") if item.startswith("page=")]
                return int(page_token[0].split("=", 1)[1])
            except (IndexError, ValueError):
                pass
        try:
            body = response.json()
        except ValueError:
            return 0
        return len(body) if isinstance(body, list) else 0

    def get_latest_release(self, owner: str, repo: str) -> str | None | Exception:
        payload = self._get(f"{self._base_url}/repos/{owner}/{repo}/releases/latest")
        if isinstance(payload, Exception):
            message = str(payload)
            if "404" in message:
                return None
            return payload
        if isinstance(payload, dict):
            tag = payload.get("tag_name")
            return str(tag) if tag else None
        return None

    def _get(self, url: str, params: Optional[dict[str, Any]] = None) -> Any | Exception:
        response = self._request(url, params=params)
        if isinstance(response, Exception):
            return response
        try:
            return response.json()
        except ValueError as exc:
            return Exception(f"GitHub API returned invalid JSON: {exc}")

    def _request(self, url: str, params: Optional[dict[str, Any]] = None) -> requests.Response | Exception:
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = self._session.get(url, params=params, timeout=self._timeout)
                if response.status_code in {403, 429}:
                    retry_after = response.headers.get("Retry-After") or response.headers.get("X-RateLimit-Reset")
                    wait_s = 1 + attempt
                    if retry_after and retry_after.isdigit():
                        wait_s = min(int(retry_after), 60)
                    if attempt < self._max_retries:
                        self._sleep(wait_s)
                        continue
                    return Exception(f"GitHub API rate limited: HTTP {response.status_code}")
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last_error = Exception(f"GitHub API request failed: {exc}")
                if attempt < self._max_retries:
                    self._sleep(1 + attempt)
                    continue
                return last_error
        return last_error or Exception("GitHub API request failed")
