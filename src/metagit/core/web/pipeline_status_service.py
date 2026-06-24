#!/usr/bin/env python
"""Live CI/CD pipeline status aggregation for mapped workspace repositories."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
from typing import Any
from urllib.parse import quote, urlparse

import requests

from metagit.core.appconfig.models import AppConfig
from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService


@dataclass(frozen=True)
class PipelineQueryOptions:
    """Pipeline query options from HTTP query parameters."""

    project: str | None = None
    provider: str | None = None
    status: str | None = None
    repos: tuple[str, ...] = ()
    include_unsynced: bool = True
    limit: int = 200


class PipelineStatusService:
    """Resolve provider auth and aggregate normalized pipeline status rows."""

    def __init__(
        self,
        *,
        index_service: WorkspaceIndexService | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._index = index_service or WorkspaceIndexService()
        self._timeout_seconds = timeout_seconds

    def provider_diagnostics(self, app_config: AppConfig) -> dict[str, Any]:
        """Return provider availability metadata without exposing secrets."""
        gh_token, gh_source = self._resolve_github_token(app_config)
        gl_token, gl_source = self._resolve_gitlab_token(app_config)

        return {
            "ok": True,
            "fetched_at": _iso_now(),
            "providers": [
                {
                    "provider": "github",
                    "enabled": bool(app_config.providers.github.enabled),
                    "available": bool(gh_token),
                    "auth_source": gh_source,
                    "base_url": app_config.providers.github.base_url,
                },
                {
                    "provider": "gitlab",
                    "enabled": bool(app_config.providers.gitlab.enabled),
                    "available": bool(gl_token),
                    "auth_source": gl_source,
                    "base_url": app_config.providers.gitlab.base_url,
                },
            ],
        }

    def pipeline_status(
        self,
        *,
        config: MetagitConfig,
        app_config: AppConfig,
        workspace_root: str,
        definition_root: str,
        options: PipelineQueryOptions,
    ) -> dict[str, Any]:
        """Build normalized pipeline status rows from mapped repos."""
        rows = self._index.build_index(
            config=config,
            workspace_root=workspace_root,
            definition_root=definition_root,
        )
        filtered = self._apply_repo_filters(rows, options)

        out_rows: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        for row in filtered[: options.limit]:
            try:
                result = self._status_for_repo(row, app_config)
            except Exception as exc:  # defensive guard to preserve partial results
                result = {
                    "project_name": str(row.get("project_name", "")),
                    "repo_name": str(row.get("repo_name", "")),
                    "provider": self._provider_for_url(row.get("url")),
                    "repo_url": row.get("url"),
                    "repo_path": row.get("repo_path"),
                    "local_status": str(row.get("status", "unknown")),
                    "branch_used": None,
                    "pipeline_status": "unknown",
                    "pipeline_name": None,
                    "updated_at": None,
                    "duration_sec": None,
                    "web_url": None,
                    "source": "fallback",
                    "reason": f"pipeline lookup error: {exc}",
                }
            if options.status and result.get("pipeline_status") != options.status:
                continue
            out_rows.append(result)
            if result.get("reason"):
                errors.append(
                    {
                        "project_name": str(result.get("project_name", "")),
                        "repo_name": str(result.get("repo_name", "")),
                        "message": str(result.get("reason")),
                    }
                )

        summary: dict[str, int] = {
            "total": len(out_rows),
            "passed": 0,
            "failed": 0,
            "running": 0,
            "pending": 0,
            "canceled": 0,
            "skipped": 0,
            "unknown": 0,
        }
        for row in out_rows:
            key = str(row.get("pipeline_status", "unknown"))
            if key not in summary:
                key = "unknown"
            summary[key] = summary.get(key, 0) + 1

        return {
            "ok": True,
            "fetched_at": _iso_now(),
            "summary": summary,
            "rows": out_rows,
            "errors": errors,
        }

    def _status_for_repo(
        self,
        row: dict[str, Any],
        app_config: AppConfig,
    ) -> dict[str, Any]:
        project_name = str(row.get("project_name", ""))
        repo_name = str(row.get("repo_name", ""))
        repo_url = row.get("url")
        provider = self._provider_for_url(repo_url)
        local_status = str(row.get("status", "unknown"))
        repo_path = str(row.get("repo_path", ""))

        base = {
            "project_name": project_name,
            "repo_name": repo_name,
            "provider": provider,
            "repo_url": repo_url,
            "repo_path": repo_path,
            "local_status": local_status,
            "branch_used": None,
            "pipeline_status": "unknown",
            "pipeline_name": None,
            "updated_at": None,
            "duration_sec": None,
            "web_url": None,
            "source": "live",
            "reason": None,
        }

        if provider not in {"github", "gitlab"}:
            base["source"] = "fallback"
            base["reason"] = "unsupported or missing remote provider URL"
            return base

        if provider == "github":
            token, _ = self._resolve_github_token(app_config)
            api_base = app_config.providers.github.base_url.rstrip("/")
            if not token:
                base["source"] = "fallback"
                base["reason"] = "no GitHub auth context available"
                return base
            owner, repo = self._parse_github_repo(repo_url)
            if not owner or not repo:
                base["source"] = "fallback"
                base["reason"] = "unable to parse GitHub repository URL"
                return base
            payload = self._fetch_github_pipeline(
                api_base=api_base,
                token=token,
                owner=owner,
                repo=repo,
                local_status=local_status,
                repo_path=repo_path,
            )
            return {**base, **payload}

        token, _ = self._resolve_gitlab_token(app_config)
        api_base = app_config.providers.gitlab.base_url.rstrip("/")
        if not token:
            base["source"] = "fallback"
            base["reason"] = "no GitLab auth context available"
            return base
        namespace_repo = self._parse_gitlab_repo_path(repo_url)
        if not namespace_repo:
            base["source"] = "fallback"
            base["reason"] = "unable to parse GitLab repository URL"
            return base
        payload = self._fetch_gitlab_pipeline(
            api_base=api_base,
            token=token,
            namespace_repo=namespace_repo,
            local_status=local_status,
            repo_path=repo_path,
        )
        return {**base, **payload}

    def _fetch_github_pipeline(
        self,
        *,
        api_base: str,
        token: str,
        owner: str,
        repo: str,
        local_status: str,
        repo_path: str,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
        }
        session = requests.Session()
        session.headers.update(headers)

        repo_resp = session.get(
            f"{api_base}/repos/{owner}/{repo}", timeout=self._timeout_seconds
        )
        repo_resp.raise_for_status()
        repo_data = repo_resp.json()
        default_branch = str(repo_data.get("default_branch", "") or "").strip() or None

        branch = self._local_branch(repo_path) if local_status == "synced" else None
        branch = branch or default_branch

        runs_params: dict[str, Any] = {"per_page": 1}
        if branch:
            runs_params["branch"] = branch
        runs_resp = session.get(
            f"{api_base}/repos/{owner}/{repo}/actions/runs",
            params=runs_params,
            timeout=self._timeout_seconds,
        )
        runs_resp.raise_for_status()
        runs = runs_resp.json().get("workflow_runs") or []
        if not runs:
            if branch != default_branch and default_branch:
                runs_resp = session.get(
                    f"{api_base}/repos/{owner}/{repo}/actions/runs",
                    params={"per_page": 1, "branch": default_branch},
                    timeout=self._timeout_seconds,
                )
                runs_resp.raise_for_status()
                runs = runs_resp.json().get("workflow_runs") or []
                branch = default_branch
        if not runs:
            return {
                "branch_used": branch,
                "pipeline_status": "unknown",
                "source": "fallback",
                "reason": "no workflow runs found",
            }

        run = runs[0]
        updated_at = run.get("updated_at") or run.get("run_started_at")
        return {
            "branch_used": branch,
            "pipeline_status": self._normalize_github_status(
                str(run.get("status", "")),
                run.get("conclusion"),
            ),
            "pipeline_name": run.get("name") or run.get("display_title"),
            "updated_at": updated_at,
            "duration_sec": _duration_seconds(
                run.get("run_started_at"), run.get("updated_at")
            ),
            "web_url": run.get("html_url"),
            "source": "live",
            "reason": None,
        }

    def _fetch_gitlab_pipeline(
        self,
        *,
        api_base: str,
        token: str,
        namespace_repo: str,
        local_status: str,
        repo_path: str,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        session = requests.Session()
        session.headers.update(headers)

        encoded = quote(namespace_repo, safe="")
        project_resp = session.get(
            f"{api_base}/projects/{encoded}", timeout=self._timeout_seconds
        )
        project_resp.raise_for_status()
        project_data = project_resp.json()
        default_branch = (
            str(project_data.get("default_branch", "") or "").strip() or None
        )
        branch = self._local_branch(repo_path) if local_status == "synced" else None
        branch = branch or default_branch

        pipeline_params: dict[str, Any] = {"per_page": 1}
        if branch:
            pipeline_params["ref"] = branch
        pipelines_resp = session.get(
            f"{api_base}/projects/{encoded}/pipelines",
            params=pipeline_params,
            timeout=self._timeout_seconds,
        )
        pipelines_resp.raise_for_status()
        pipelines = pipelines_resp.json() or []
        if not pipelines:
            if branch != default_branch and default_branch:
                pipelines_resp = session.get(
                    f"{api_base}/projects/{encoded}/pipelines",
                    params={"per_page": 1, "ref": default_branch},
                    timeout=self._timeout_seconds,
                )
                pipelines_resp.raise_for_status()
                pipelines = pipelines_resp.json() or []
                branch = default_branch
        if not pipelines:
            return {
                "branch_used": branch,
                "pipeline_status": "unknown",
                "source": "fallback",
                "reason": "no pipelines found",
            }

        pipeline = pipelines[0]
        return {
            "branch_used": branch,
            "pipeline_status": self._normalize_gitlab_status(
                str(pipeline.get("status", ""))
            ),
            "pipeline_name": f"Pipeline #{pipeline.get('id')}",
            "updated_at": pipeline.get("updated_at") or pipeline.get("created_at"),
            "duration_sec": None,
            "web_url": pipeline.get("web_url"),
            "source": "live",
            "reason": None,
        }

    def _apply_repo_filters(
        self,
        rows: list[dict[str, Any]],
        options: PipelineQueryOptions,
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        repo_filters = {value.lower() for value in options.repos if value.strip()}
        for row in rows:
            project_name = str(row.get("project_name", ""))
            repo_name = str(row.get("repo_name", ""))
            local_status = str(row.get("status", ""))
            provider = self._provider_for_url(row.get("url"))
            selector = f"{project_name}/{repo_name}".lower()

            if options.project and project_name.lower() != options.project.lower():
                continue
            if options.provider and provider != options.provider:
                continue
            if not options.include_unsynced and local_status != "synced":
                continue
            if (
                repo_filters
                and repo_name.lower() not in repo_filters
                and selector not in repo_filters
            ):
                continue
            out.append(row)
        return out

    @staticmethod
    def _provider_for_url(url: Any) -> str:
        if not isinstance(url, str) or not url.strip():
            return "unknown"
        host = urlparse(url.strip()).netloc.lower()
        if "github" in host:
            return "github"
        if "gitlab" in host:
            return "gitlab"
        return "unknown"

    @staticmethod
    def _parse_github_repo(url: Any) -> tuple[str | None, str | None]:
        if not isinstance(url, str):
            return None, None
        parsed = urlparse(url)
        parts = [piece for piece in parsed.path.split("/") if piece]
        if len(parts) < 2:
            return None, None
        owner = parts[0]
        repo = parts[1]
        if repo.endswith(".git"):
            repo = repo[:-4]
        return owner, repo

    @staticmethod
    def _parse_gitlab_repo_path(url: Any) -> str | None:
        if not isinstance(url, str):
            return None
        parsed = urlparse(url)
        parts = [piece for piece in parsed.path.split("/") if piece]
        if len(parts) < 2:
            return None
        if parts[-1].endswith(".git"):
            parts[-1] = parts[-1][:-4]
        return "/".join(parts)

    def _resolve_github_token(self, app_config: AppConfig) -> tuple[str | None, str]:
        provider = app_config.providers.github
        if provider.enabled and provider.api_token.strip():
            return provider.api_token.strip(), "appconfig.github"
        if os.getenv("METAGIT_GITHUB_API_TOKEN"):
            return str(
                os.getenv("METAGIT_GITHUB_API_TOKEN")
            ).strip(), "env.METAGIT_GITHUB_API_TOKEN"
        if os.getenv("GITHUB_TOKEN"):
            return str(os.getenv("GITHUB_TOKEN")).strip(), "env.GITHUB_TOKEN"
        if os.getenv("GH_TOKEN"):
            return str(os.getenv("GH_TOKEN")).strip(), "env.GH_TOKEN"
        return None, "none"

    def _resolve_gitlab_token(self, app_config: AppConfig) -> tuple[str | None, str]:
        provider = app_config.providers.gitlab
        if provider.enabled and provider.api_token.strip():
            return provider.api_token.strip(), "appconfig.gitlab"
        if os.getenv("METAGIT_GITLAB_API_TOKEN"):
            return str(
                os.getenv("METAGIT_GITLAB_API_TOKEN")
            ).strip(), "env.METAGIT_GITLAB_API_TOKEN"
        if os.getenv("GITLAB_TOKEN"):
            return str(os.getenv("GITLAB_TOKEN")).strip(), "env.GITLAB_TOKEN"
        if os.getenv("GLAB_TOKEN"):
            return str(os.getenv("GLAB_TOKEN")).strip(), "env.GLAB_TOKEN"
        return None, "none"

    @staticmethod
    def _normalize_github_status(status: str, conclusion: Any) -> str:
        status_lower = status.lower()
        conclusion_lower = str(conclusion).lower() if conclusion is not None else ""
        if status_lower in {"queued", "waiting", "requested", "pending"}:
            return "pending"
        if status_lower in {"in_progress", "running"}:
            return "running"
        if status_lower == "completed":
            if conclusion_lower == "success":
                return "passed"
            if conclusion_lower in {
                "failure",
                "timed_out",
                "action_required",
                "startup_failure",
            }:
                return "failed"
            if conclusion_lower in {"cancelled", "canceled"}:
                return "canceled"
            if conclusion_lower in {"skipped", "neutral"}:
                return "skipped"
        return "unknown"

    @staticmethod
    def _normalize_gitlab_status(status: str) -> str:
        mapped = status.lower()
        if mapped in {"success", "passed"}:
            return "passed"
        if mapped in {"failed", "failure"}:
            return "failed"
        if mapped in {"running"}:
            return "running"
        if mapped in {
            "pending",
            "created",
            "preparing",
            "scheduled",
            "waiting_for_resource",
            "manual",
        }:
            return "pending"
        if mapped in {"canceled", "cancelled"}:
            return "canceled"
        if mapped in {"skipped"}:
            return "skipped"
        return "unknown"

    @staticmethod
    def _local_branch(repo_path: str) -> str | None:
        if not repo_path:
            return None
        path = Path(repo_path)
        if not path.is_dir():
            return None
        try:
            proc = subprocess.run(
                ["git", "-C", str(path), "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
        except Exception:
            return None
        if proc.returncode != 0:
            return None
        value = proc.stdout.strip()
        if not value or value == "HEAD":
            return None
        return value


def _duration_seconds(start: Any, end: Any) -> int | None:
    if not isinstance(start, str) or not isinstance(end, str):
        return None
    try:
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
    except ValueError:
        return None
    duration = int((end_dt - start_dt).total_seconds())
    return duration if duration >= 0 else None


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()
