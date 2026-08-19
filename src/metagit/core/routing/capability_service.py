#!/usr/bin/env python
"""Capability resolve/compile orchestration built on routing + workspace topology."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Literal

from metagit.core.agent.profile_service import AgentProfileService
from metagit.core.config.models import MetagitConfig
from metagit.core.context.compiler import ContextCompiler
from metagit.core.routing.capability_models import CapabilityEnvelope, CapabilityMatch, CapabilityRepoRef
from metagit.core.routing.models import CapabilitySpec, RequestClass
from metagit.core.routing.router import rank_classes
from metagit.core.workspace.agent_instructions import AgentInstructionsResolver
from metagit.core.workspace.context_models import utc_now_iso
from metagit.core.workspace.layout_resolver import find_project, find_repo
from metagit.core.workspace.protection import merge_project_repo_tags


class CapabilityService:
    """Compose deterministic capability results and envelopes."""

    def __init__(self, config: MetagitConfig, *, workspace_root: str) -> None:
        self._config = config
        self._workspace_root = Path(workspace_root).expanduser().resolve()
        from metagit.core.routing.routing_service import RoutingService

        self._routing = RoutingService(config, workspace_root=str(self._workspace_root))

    def list_capabilities(self, *, project: str | None = None) -> list[RequestClass]:
        rows = [row for row in self._routing.list_classes() if row.capability is not None]
        if project is not None:
            rows = [row for row in rows if self._selector_has_project_match(row.capability, project)]
        rows.sort(key=lambda row: row.id)
        return rows

    def show_capability(self, capability_id: str) -> dict[str, object]:
        shown = self._routing.show_class(capability_id)
        row = shown["class"]
        if row.capability is None:
            raise ValueError("capability_not_found")
        return shown

    def resolve(
        self,
        ask: str,
        *,
        project: str | None = None,
        repo: str | None = None,
        limit: int = 5,
    ) -> list[CapabilityMatch]:
        classes = [row for row in self._routing.list_classes() if row.capability is not None]
        ranked = rank_classes(classes, ask, limit=max(limit * 3, limit))
        matches: list[CapabilityMatch] = []
        for ranked_row in ranked:
            capability = ranked_row.request_class.capability
            if capability is None:
                continue
            selector_ok, selector_reason = self._selector_passes(
                capability=capability,
                project_name=project,
                repo_name=repo,
            )
            if not selector_ok:
                continue
            matches.append(
                CapabilityMatch(
                    capability_id=ranked_row.request_class.id,
                    confidence=ranked_row.confidence,
                    why=f"{ranked_row.why}; selector:pass:{selector_reason}",
                    selector_ok=True,
                )
            )
        matches.sort(key=lambda row: (-row.confidence, row.capability_id))
        return matches[:limit]

    def compile(
        self,
        capability_id: str,
        *,
        project: str,
        repo: str | None = None,
        task_id: str | None = None,
        graph_id: str | None = None,
        objective_id: str | None = None,
        tier: Literal[0, 1, 2] = 1,
        budget: int | None = None,
        with_context: bool = True,
    ) -> CapabilityEnvelope:
        shown = self._routing.show_class(capability_id)
        request_class = shown["class"]
        capability = request_class.capability
        if capability is None:
            raise ValueError("capability_not_found")

        project_model = find_project(self._config, project)
        if project_model is None:
            raise ValueError("project_not_found")

        resolved_repo_name = repo
        if not resolved_repo_name:
            candidates = self._matching_repo_names(project, capability)
            if not candidates:
                raise ValueError("repository_not_found")
            if len(candidates) > 1:
                raise ValueError(f"ambiguous_repo:{','.join(sorted(candidates))}")
            resolved_repo_name = candidates[0]

        repo_model = find_repo(project_model, resolved_repo_name)
        if repo_model is None:
            raise ValueError("repository_not_found")

        instructions = AgentInstructionsResolver().resolve(
            self._config,
            project=project_model,
            repo=repo_model,
        )
        profile = AgentProfileService(
            config=self._config,
            definition_root=self._workspace_root,
            workspace_root=self._workspace_root,
        ).effective_profile(project_name=project, repo_name=resolved_repo_name)
        merged_tags = merge_project_repo_tags(project_model, repo_model)
        resolved_scope, warnings = self._resolve_scope(capability=capability, protected=bool(project_model.protected))
        if bool(repo_model.protected):
            resolved_scope["writable_paths"] = []
            warnings.append("repository is protected; writable_paths forced empty")
        if not resolved_scope["writable_paths"] and capability.expected_output not in {"report", "none"}:
            warnings.append("read-only capability should use expected_output report or none")

        resolved_repo_path = self._resolve_repo_path(project_name=project, configured_path=repo_model.path)
        compiled_context_path: str | None = None
        if with_context:
            compiled = ContextCompiler().compile(
                config=self._config,
                config_path=str(self._workspace_root / ".metagit.yml"),
                workspace_root=str(self._workspace_root),
                session_root=str(self._workspace_root),
                definition_root=str(self._workspace_root),
                project=project,
                repo=resolved_repo_name,
                tier=tier,
                budget=budget,
                task_id=task_id,
                graph_id=graph_id,
                objective_id=objective_id,
            )
            if isinstance(compiled, Exception):
                warnings.append(f"context compile failed: {compiled}")
            else:
                compiled_context_path = compiled.artifact_path

        gates = list(request_class.gates)
        gates.extend([step.name for step in capability.workflow if step.gate and step.name not in gates])
        envelope = CapabilityEnvelope(
            capability_id=request_class.id,
            title=request_class.title,
            project=project,
            repository=CapabilityRepoRef(
                project=project,
                repo=resolved_repo_name,
                path=str(resolved_repo_path),
                url=str(repo_model.url) if repo_model.url else None,
                allowed_paths=resolved_scope["allowed_paths"],
                writable_paths=resolved_scope["writable_paths"],
            ),
            cwd=str(resolved_repo_path),
            allowed_paths=resolved_scope["allowed_paths"],
            writable_paths=resolved_scope["writable_paths"],
            instructions=instructions.effective,
            instruction_layers=[layer.model_dump(mode="json") for layer in instructions.layers],
            skills=list(profile.skills) if profile else [],
            mcp=list(profile.mcp) if profile else [],
            rules=list(profile.rules) if profile else [],
            required_tools=list(capability.required_tools),
            constraints=list(capability.constraints),
            workflow=list(capability.workflow),
            gates=gates,
            expected_output=capability.expected_output,
            context_artifact_path=compiled_context_path,
            tier=request_class.tier,
            executor=request_class.executor,
            task_id=task_id,
            objective_id=objective_id,
            warnings=warnings,
            generated_at=utc_now_iso(),
        )
        self._append_event(
            {
                "capability_id": capability_id,
                "project": project,
                "repo": resolved_repo_name,
                "path": str(resolved_repo_path),
                "tags": merged_tags,
                "task_id": task_id,
                "objective_id": objective_id,
            }
        )
        return envelope

    def doctor(self) -> dict[str, object]:
        issues: list[dict[str, str]] = []
        for row in self.list_capabilities():
            capability = row.capability
            if capability is None:
                continue
            if capability.expected_output != "none" and not capability.workflow:
                issues.append(
                    {
                        "id": row.id,
                        "error": "workflow_required",
                        "message": "workflow is required when expected_output is not none",
                    }
                )
        return {"ok": len(issues) == 0, "issues": issues}

    def _selector_has_project_match(self, capability: CapabilitySpec | None, project: str) -> bool:
        if capability is None:
            return False
        ok, _ = self._selector_passes(capability=capability, project_name=project, repo_name=None)
        return ok

    def _selector_passes(
        self,
        *,
        capability: CapabilitySpec,
        project_name: str | None,
        repo_name: str | None,
    ) -> tuple[bool, str]:
        if not self._config.workspace:
            return True, "no-workspace"
        selector = capability.selector
        if not any([selector.project_types, selector.domains, selector.tags, selector.path_globs, selector.languages]):
            return True, "empty-selector"
        projects = self._config.workspace.projects
        if project_name:
            project = find_project(self._config, project_name)
            if project is None:
                return False, "project-not-found"
            projects = [project]
        for project in projects:
            repos = project.repos
            if repo_name:
                repo = find_repo(project, repo_name)
                if repo is None:
                    continue
                repos = [repo]
            for repo in repos:
                if self._repo_matches_selector(project.name, project, repo, selector):
                    return True, f"{project.name}/{repo.name}"
        return False, "no-selector-match"

    def _matching_repo_names(self, project_name: str, capability: CapabilitySpec) -> list[str]:
        project = find_project(self._config, project_name)
        if project is None:
            return []
        matches: list[str] = []
        for repo in project.repos:
            if self._repo_matches_selector(project_name, project, repo, capability.selector):
                matches.append(repo.name)
        return matches

    def _repo_matches_selector(self, project_name: str, project: object, repo: object, selector: object) -> bool:
        project_tags = project.tags
        merged_tags = {**project_tags, **repo.tags}
        project_type = (project_tags.get("project_type") or project_tags.get("type") or "").strip().lower()
        domain = (project_tags.get("domain") or "").strip().lower()
        repo_language = (repo.language or "").strip().lower()
        selector_project_types = [str(item).strip().lower() for item in selector.project_types]
        if selector_project_types and project_type not in selector_project_types:
            return False
        selector_domains = [str(item).strip().lower() for item in selector.domains]
        if selector_domains and domain not in selector_domains:
            return False
        for key, value in selector.tags.items():
            if merged_tags.get(key) != value:
                return False
        selector_languages = [str(item).strip().lower() for item in selector.languages]
        if selector_languages and repo_language not in selector_languages:
            return False
        selector_globs = list(selector.path_globs)
        if selector_globs:
            repo_path = self._resolve_repo_path(project_name=project_name, configured_path=repo.path)
            if not repo_path.is_dir():
                return False
            if not any(any(repo_path.glob(pattern)) for pattern in selector_globs):
                return False
        return True

    def _resolve_repo_path(self, *, project_name: str, configured_path: str | None) -> Path:
        if configured_path:
            path = Path(configured_path).expanduser()
            if path.is_absolute():
                return path.resolve()
            return (self._workspace_root / path).resolve()
        return (self._workspace_root / project_name).resolve()

    @staticmethod
    def _resolve_scope(*, capability: CapabilitySpec, protected: bool) -> tuple[dict[str, list[str]], list[str]]:
        warnings: list[str] = []
        allowed_paths = list(capability.scope.allowed_paths)
        writable_paths = list(capability.scope.writable_paths)
        forbidden_paths = set(capability.scope.forbidden_paths)
        writable_paths = [item for item in writable_paths if item not in forbidden_paths]
        allowed_paths = [item for item in allowed_paths if item not in forbidden_paths]
        if protected:
            writable_paths = []
            warnings.append("project is protected; writable_paths forced empty")
        return {"allowed_paths": allowed_paths, "writable_paths": writable_paths}, warnings

    def _append_event(self, payload: dict[str, object]) -> None:
        path = self._workspace_root / ".metagit" / "events" / "capability.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(
            {
                "event_id": uuid.uuid4().hex,
                "type": "CapabilityCompiled",
                "at": utc_now_iso(),
                "payload": payload,
            },
            sort_keys=False,
        )
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
