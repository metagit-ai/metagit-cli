#!/usr/bin/env python
"""Load, validate, and mutate native workspace campaigns."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from metagit.core.campaign.models import (
    CampaignDocument,
    CampaignExpandResult,
    CampaignListItem,
    CampaignListResult,
    CampaignRepoEntry,
    CampaignRepoStatus,
    CampaignSelection,
    CampaignStatusResult,
    CampaignValidationIssue,
)
from metagit.core.config.models import MetagitConfig
from metagit.core.context.objective_service import ObjectiveService
from metagit.core.project.search_service import ManagedRepoSearchService
from metagit.core.utils.yaml_class import yaml
from metagit.core.workspace.layout_resolver import find_project, find_repo
from metagit.core.workspace.root_resolver import resolve_campaigns_root


class CampaignService:
    """Manage diffable campaign YAML under a configurable campaigns directory."""

    def __init__(
        self,
        *,
        config: MetagitConfig,
        definition_root: Path,
        workspace_root: Optional[Path] = None,
        campaigns_path: Optional[str] = None,
    ) -> None:
        self._config = config
        self._definition_root = definition_root.resolve()
        self._workspace_root = (workspace_root or definition_root).resolve()
        self._campaigns_dir = Path(
            resolve_campaigns_root(str(self._definition_root), campaigns_path),
        )
        self._search = ManagedRepoSearchService()

    def campaigns_dir(self) -> Path:
        return self._campaigns_dir

    def list_campaigns(self) -> CampaignListResult:
        items: list[CampaignListItem] = []
        for path in sorted(self._campaigns_dir.glob("*.yml")):
            campaign = self._load_file(path)
            if campaign is None:
                continue
            items.append(self._summary_item(campaign))
        return CampaignListResult(campaigns=items)

    def load(self, slug: str) -> Optional[CampaignDocument]:
        path = self._campaign_path(slug)
        if not path.is_file():
            return None
        return self._load_file(path)

    def status(self, slug: str) -> Optional[CampaignStatusResult]:
        campaign = self.load(slug)
        if campaign is None:
            return None
        merged = sum(1 for repo in campaign.repos if repo.status == "merged")
        open_mr = sum(1 for repo in campaign.repos if repo.status == "mr-open")
        blocked = sum(1 for repo in campaign.repos if repo.status == "blocked")
        pending = sum(1 for repo in campaign.repos if repo.status in {"pending", "routed"})
        return CampaignStatusResult(
            campaign=campaign,
            merged_count=merged,
            open_mr_count=open_mr,
            blocked_count=blocked,
            pending_count=pending,
        )

    def create(
        self,
        *,
        slug: str,
        title: str,
        query: Optional[str] = None,
        repos: Optional[list[str]] = None,
        tag_filters: Optional[dict[str, str]] = None,
        objective_id: Optional[str] = None,
        goal: Optional[str] = None,
        reference_impl: Optional[str] = None,
    ) -> CampaignDocument:
        existing = self.load(slug)
        if existing is not None:
            raise ValueError(f"Campaign already exists: {slug!r}")
        if not query and not repos:
            raise ValueError("Provide --query or at least one --repo to select campaign repos.")
        if repos:
            repo_entries = self._explicit_selection(repos)
        else:
            repo_entries = self._resolve_selection(query=query or "", tag_filters=tag_filters)
        now = datetime.now(timezone.utc).isoformat()
        campaign = CampaignDocument(
            slug=slug,
            title=title,
            status="draft",
            goal=goal,
            reference_impl=reference_impl,
            objective_id=objective_id,
            created=now,
            updated=now,
            selection=CampaignSelection(
                query=query,
                tags=dict(tag_filters or {}),
                resolved_at=now,
            ),
            repos=repo_entries,
        )
        self._save(campaign)
        return campaign

    def validate_all(self) -> list[CampaignValidationIssue]:
        issues: list[CampaignValidationIssue] = []
        if not self._campaigns_dir.is_dir():
            return issues
        for path in sorted(self._campaigns_dir.glob("*.yml")):
            slug = path.stem
            campaign = self._load_file(path)
            if campaign is None:
                issues.append(CampaignValidationIssue(slug=slug, message="invalid campaign YAML"))
                continue
            issues.extend(self._validate_campaign(campaign))
        return issues

    def set_repo_status(
        self,
        *,
        slug: str,
        project: str,
        repo: str,
        status: CampaignRepoStatus,
        mr: Optional[str] = None,
        note: Optional[str] = None,
    ) -> CampaignDocument:
        campaign = self.load(slug)
        if campaign is None:
            raise ValueError(f"Unknown campaign: {slug!r}")
        key = f"{project}/{repo}"
        for entry in campaign.repos:
            if f"{entry.project}/{entry.repo}" != key:
                continue
            entry.status = status
            if mr is not None:
                entry.mr = mr
            if note is not None:
                entry.note = note
            campaign.updated = datetime.now(timezone.utc).isoformat()
            self._save(campaign)
            return campaign
        raise ValueError(f"Repo not in campaign {slug!r}: {key}")

    def expand(
        self,
        *,
        slug: str,
        session_root: Path,
        tag_filters: Optional[dict[str, str]] = None,
        dry_run: bool = False,
    ) -> CampaignExpandResult:
        """Create one spine objective per matching campaign repo."""
        campaign = self.load(slug)
        if campaign is None:
            raise ValueError(f"Unknown campaign: {slug!r}")
        objective_service = ObjectiveService(workspace_root=str(session_root))
        objective_ids: list[str] = []
        filters = tag_filters or dict(campaign.selection.tags)
        for entry in campaign.repos:
            if filters and not self._repo_matches_tags(entry, filters):
                continue
            objective_id = f"campaign-{slug}-{entry.project}-{entry.repo}"
            if dry_run:
                objective_ids.append(objective_id)
                continue
            objective_service.upsert_partial(
                {
                    "id": objective_id,
                    "title": f"{campaign.title}: {entry.project}/{entry.repo}",
                    "status": "active",
                    "repos": [f"{entry.project}/{entry.repo}"],
                    "agent_notes": f"Generated from campaign {slug}",
                },
            )
            objective_ids.append(objective_id)
        return CampaignExpandResult(slug=slug, objective_ids=objective_ids, dry_run=dry_run)

    def _repo_matches_tags(
        self,
        entry: CampaignRepoEntry,
        filters: dict[str, str],
    ) -> bool:
        project = find_project(self._config, entry.project)
        if project is None:
            return False
        repo = find_repo(project, entry.repo)
        if repo is None:
            return False
        from metagit.core.workspace.protection import merge_project_repo_tags

        tags = merge_project_repo_tags(project, repo)
        return all(tags.get(key) == value for key, value in filters.items())

    def _explicit_selection(self, repos: list[str]) -> list[CampaignRepoEntry]:
        """Build a frozen repo set from explicit ``project/repo`` selectors.

        Unlike query resolution, this does not re-resolve against the atlas on
        every run — the campaign's repo set is fixed at creation time (no query
        drift). Atlas membership is enforced later by ``validate_all``.
        """
        entries: list[CampaignRepoEntry] = []
        seen: set[str] = set()
        for selector in repos:
            if "/" not in selector:
                raise ValueError(f"--repo must be project/repo, got {selector!r}")
            project, repo_name = selector.split("/", 1)
            key = f"{project}/{repo_name}"
            if key in seen:
                continue
            seen.add(key)
            entries.append(CampaignRepoEntry(project=project, repo=repo_name, status="pending"))
        return entries

    def _resolve_selection(
        self,
        *,
        query: str,
        tag_filters: Optional[dict[str, str]] = None,
    ) -> list[CampaignRepoEntry]:
        result = self._search.search(
            config=self._config,
            workspace_root=str(self._workspace_root),
            query=query,
            tags=tag_filters,
            limit=500,
        )
        repos: list[CampaignRepoEntry] = []
        for match in result.matches:
            repos.append(
                CampaignRepoEntry(
                    project=match.project_name,
                    repo=match.repo_name,
                    status="pending",
                ),
            )
        return repos

    def _validate_campaign(self, campaign: CampaignDocument) -> list[CampaignValidationIssue]:
        issues: list[CampaignValidationIssue] = []
        if not self._config.workspace:
            return issues
        for entry in campaign.repos:
            project = find_project(self._config, entry.project)
            if project is None:
                issues.append(
                    CampaignValidationIssue(
                        slug=campaign.slug,
                        message=f"unknown project {entry.project!r}",
                    ),
                )
                continue
            if find_repo(project, entry.repo) is None:
                issues.append(
                    CampaignValidationIssue(
                        slug=campaign.slug,
                        message=f"unknown repo {entry.project}/{entry.repo}",
                    ),
                )
        return issues

    def _summary_item(self, campaign: CampaignDocument) -> CampaignListItem:
        merged = sum(1 for repo in campaign.repos if repo.status == "merged")
        open_mr = sum(1 for repo in campaign.repos if repo.status == "mr-open")
        blocked = sum(1 for repo in campaign.repos if repo.status == "blocked")
        return CampaignListItem(
            slug=campaign.slug,
            title=campaign.title,
            status=campaign.status,
            repo_count=len(campaign.repos),
            merged_count=merged,
            open_mr_count=open_mr,
            blocked_count=blocked,
        )

    def _campaign_path(self, slug: str) -> Path:
        return self._campaigns_dir / f"{slug}.yml"

    def _load_file(self, path: Path) -> Optional[CampaignDocument]:
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            return None
        if not isinstance(raw, dict):
            return None
        return CampaignDocument.model_validate(raw)

    def _save(self, campaign: CampaignDocument) -> Path:
        self._campaigns_dir.mkdir(parents=True, exist_ok=True)
        path = self._campaign_path(campaign.slug)
        payload = campaign.model_dump(mode="json", exclude_none=True)
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        return path
