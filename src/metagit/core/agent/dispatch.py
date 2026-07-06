#!/usr/bin/env python
"""Build machine-readable agent dispatch plans for overseer handoffs."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from metagit.core.agent.models import (
    AgentArchetype,
    AgentDispatchHandoff,
    AgentDispatchInstall,
    AgentDispatchPlan,
    AgentScopeLevel,
    AgentTemplateManifest,
)
from metagit.core.agent.paths import (
    AGENT_SUPPORTED_TARGETS,
    resolve_vendor_artifact_path,
)
from metagit.core.agent.profile_service import AgentProfileService
from metagit.core.agent.registry import AgentTemplateRegistry
from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.resource_catalog import recommended_mcp_resources
from metagit.core.skills.installer import list_bundled_skills
from metagit.core.workspace.agent_instructions import AgentInstructionsResolver
from metagit.core.workspace.models import WorkspaceProject


class AgentDispatchService:
    """Compose install, launch, and handoff envelopes for one template."""

    def __init__(
        self,
        *,
        registry: AgentTemplateRegistry,
        manifest_root: Path,
        config: MetagitConfig | None = None,
    ) -> None:
        self._registry = registry
        self._manifest_root = manifest_root
        self._config = config
        self._instructions = AgentInstructionsResolver()

    def build_plan(
        self,
        template_id: str,
        *,
        vendor: str,
        scope: Literal["project", "user"] = "project",
        project: str | None = None,
        repo: str | None = None,
        task: str | None = None,
        definition_path: str = ".metagit.yml",
    ) -> AgentDispatchPlan:
        """Return a dispatch envelope for one template and target scope."""
        manifest = self._registry.load_manifest(template_id)
        if manifest is None:
            raise ValueError(f"Unknown agent template: {template_id!r}")
        if vendor not in AGENT_SUPPORTED_TARGETS:
            supported = ", ".join(AGENT_SUPPORTED_TARGETS)
            raise ValueError(f"Unknown vendor {vendor!r}. Supported: {supported}")

        self._validate_scope_inputs(manifest, project=project, repo=repo)

        project_model, repo_model = self._resolve_project_repo(
            project=project,
            repo=repo,
        )
        install = self._build_install(
            manifest,
            vendor=vendor,
            scope=scope,
        )
        launch = self._build_launch_hints(
            manifest,
            vendor=vendor,
            project=project,
            repo=repo,
            task=task,
        )
        handoff = self._build_handoff(
            manifest,
            definition_path=definition_path,
            project=project,
            repo=repo,
            project_model=project_model,
            repo_model=repo_model,
        )
        profile_fields = self._profile_capability_fields(
            vendor=vendor,
            project=project,
            repo=repo,
        )
        return AgentDispatchPlan(
            template_id=template_id,
            vendor=vendor,
            scope=scope,
            project=project,
            repo=repo,
            task=task,
            install=install,
            launch=launch,
            handoff=handoff,
            out_of_scope=self._derive_out_of_scope(manifest),
            delegates_to=list(manifest.delegates_to),
            mcp_tools=list(manifest.mcp_tools),
            recommended_skills=list(manifest.recommended_skills),
            **profile_fields,
        )

    def _validate_scope_inputs(
        self,
        manifest: AgentTemplateManifest,
        *,
        project: str | None,
        repo: str | None,
    ) -> None:
        if manifest.scope == AgentScopeLevel.REPO and (not project or not repo):
            raise ValueError("repo-scoped templates require --project and --repo for dispatch-plan")
        if manifest.scope == AgentScopeLevel.PROJECT and not project:
            raise ValueError("project-scoped templates require --project for dispatch-plan")
        if repo and not project:
            raise ValueError("--repo requires --project")

    def _resolve_project_repo(
        self,
        *,
        project: str | None,
        repo: str | None,
    ) -> tuple[WorkspaceProject | None, object | None]:
        if self._config is None or not self._config.workspace:
            return None, None
        project_model: WorkspaceProject | None = None
        for entry in self._config.workspace.projects:
            if project and entry.name == project:
                project_model = entry
                break
        repo_model = None
        if project_model is not None:
            repo_model = self._instructions.find_repo(project_model, repo_name=repo)
        return project_model, repo_model

    def _build_install(
        self,
        manifest: AgentTemplateManifest,
        *,
        vendor: str,
        scope: Literal["project", "user"],
    ) -> AgentDispatchInstall:
        vendor_spec = manifest.vendors.get(vendor)
        primary_name = vendor_spec.filename if vendor_spec is not None else f"{manifest.id}.md"
        install_as = vendor_spec.install_as if vendor_spec is not None else "agent"
        artifact_path = resolve_vendor_artifact_path(
            vendor,
            scope,
            primary_name=primary_name,
            install_as=install_as,
            project_root=self._manifest_root,
        )
        needed = not artifact_path.is_file()
        command = self._install_command(
            manifest,
            vendor=vendor,
            scope=scope,
        )
        return AgentDispatchInstall(
            needed=needed,
            path=str(artifact_path),
            command=command,
        )

    def _install_command(
        self,
        manifest: AgentTemplateManifest,
        *,
        vendor: str,
        scope: Literal["project", "user"],
    ) -> str:
        parts = [
            f"metagit agent create {manifest.id}",
            f"--vendor {vendor}",
            f"--scope {scope}",
            "--root .",
        ]
        if manifest.recommended_skills:
            parts.append("--install-skills")
        return " ".join(parts)

    def _build_launch_hints(
        self,
        manifest: AgentTemplateManifest,
        *,
        vendor: str,
        project: str | None,
        repo: str | None,
        task: str | None,
    ) -> dict[str, str]:
        task_label = task.strip() if task and task.strip() else manifest.label
        repo_label = f"{project}/{repo}" if project and repo else project or "workspace"
        hints: dict[str, str] = {}
        for target in AGENT_SUPPORTED_TARGETS:
            if target not in manifest.vendors and target != vendor:
                continue
            hints[target] = self._launch_hint_for_vendor(
                manifest,
                vendor=target,
                task_label=task_label,
                repo_label=repo_label,
            )
        if vendor not in hints:
            hints[vendor] = self._launch_hint_for_vendor(
                manifest,
                vendor=vendor,
                task_label=task_label,
                repo_label=repo_label,
            )
        return hints

    def _launch_hint_for_vendor(
        self,
        manifest: AgentTemplateManifest,
        *,
        vendor: str,
        task_label: str,
        repo_label: str,
    ) -> str:
        vendor_spec = manifest.vendors.get(vendor)
        primary_name = vendor_spec.filename if vendor_spec is not None else f"{manifest.id}.md"
        install_as = vendor_spec.install_as if vendor_spec is not None else "agent"
        invoke_name = primary_name if install_as == "skill" else Path(primary_name).stem
        if vendor == "cursor":
            return f"@{invoke_name} — {task_label} ({repo_label})"
        if vendor == "claude_code":
            return f"Use the Agent tool with subagent `{invoke_name}`: {task_label} in {repo_label}"
        if vendor == "github_copilot":
            return f"Assign agent `{primary_name}` under `.github/agents/` for {task_label} in {repo_label}"
        if vendor == "opencode":
            return f"Invoke OpenCode subagent `{invoke_name}` (mode: subagent) for {task_label} in {repo_label}"
        if vendor in {"hermes", "openclaw", "windsurf", "codex"}:
            return f"Load skill `{invoke_name}` for {task_label} in {repo_label}"
        return f"Invoke `{invoke_name}` for {task_label} in {repo_label}"

    def _build_handoff(
        self,
        manifest: AgentTemplateManifest,
        *,
        definition_path: str,
        project: str | None,
        repo: str | None,
        project_model: WorkspaceProject | None,
        repo_model: object | None,
    ) -> AgentDispatchHandoff:
        context_pack = self._context_pack_command(
            manifest,
            definition_path=definition_path,
            project=project,
            repo=repo,
        )
        prompt_kind, prompt_scope = self._handoff_prompt_route(
            manifest,
            project=project,
            repo=repo,
        )
        prompt = self._prompt_command(
            prompt_scope,
            definition_path=definition_path,
            project=project,
            repo=repo,
            kind=prompt_kind,
        )
        effective = ""
        if self._config is not None:
            composition = self._instructions.resolve(
                self._config,
                project=project_model,
                repo=repo_model,  # type: ignore[arg-type]
            )
            effective = composition.effective
        return AgentDispatchHandoff(
            context_pack=context_pack,
            prompt=prompt,
            prompt_kind=prompt_kind,
            prompt_scope=prompt_scope,
            effective_instructions=effective,
            mcp_resources=recommended_mcp_resources(
                project=project,
                repo=repo,
                prompt_kind=prompt_kind,
                prompt_scope=prompt_scope,
            ),
        )

    def _context_pack_command(
        self,
        manifest: AgentTemplateManifest,
        *,
        definition_path: str,
        project: str | None,
        repo: str | None,
    ) -> str:
        tier = 0
        if manifest.scope in {AgentScopeLevel.REPO, AgentScopeLevel.PROJECT}:
            tier = 1
        if manifest.scope == AgentScopeLevel.WORKSPACE and project:
            tier = 1
        parts = [
            "metagit context pack",
            f"--tier {tier}",
            "--json",
            f"-c {definition_path}",
        ]
        if project:
            parts.append(f"--project {project}")
        if repo:
            parts.append(f"--repo {repo}")
        return " ".join(parts)

    def _handoff_prompt_route(
        self,
        manifest: AgentTemplateManifest,
        *,
        project: str | None,
        repo: str | None,
    ) -> tuple[str, Literal["workspace", "project", "repo"]]:
        if project and repo and "subagent-handoff" in manifest.prompt_kinds:
            return "subagent-handoff", "repo"
        if project and "context-pack" in manifest.prompt_kinds:
            return "context-pack", "project"
        if manifest.prompt_kinds:
            kind = manifest.prompt_kinds[0]
            scope: Literal["workspace", "project", "repo"] = "project" if project else "workspace"
            return kind, scope
        return "session-start", "workspace"

    def _prompt_command(
        self,
        prompt_scope: Literal["workspace", "project", "repo"],
        *,
        definition_path: str,
        project: str | None,
        repo: str | None,
        kind: str,
    ) -> str:
        parts = ["metagit prompt", prompt_scope]
        if prompt_scope in {"project", "repo"} and project:
            parts.append(f"-p {project}")
        if prompt_scope == "repo" and repo:
            parts.append(f"-n {repo}")
        parts.extend([f"-k {kind}", "--text-only", f"-c {definition_path}"])
        return " ".join(parts)

    def _profile_capability_fields(
        self,
        *,
        vendor: str,
        project: str | None,
        repo: str | None,
    ) -> dict[str, object]:
        if self._config is None or not project or not repo:
            return {
                "required_profile_skills": [],
                "missing_profile_skills": [],
                "profile_apply_command": None,
            }
        profile_service = AgentProfileService(
            config=self._config,
            definition_root=self._manifest_root,
        )
        effective = profile_service.effective_profile(project_name=project, repo_name=repo)
        if effective is None or not effective.skills:
            return {
                "required_profile_skills": [],
                "missing_profile_skills": [],
                "profile_apply_command": None,
            }
        bundled = set(list_bundled_skills())
        required = [skill for skill in effective.skills if skill in bundled]
        missing = list(required)
        apply_command = (
            f"metagit agent apply --vendor {vendor} --project {project} --repo {repo} --root ." if missing else None
        )
        return {
            "required_profile_skills": required,
            "missing_profile_skills": missing,
            "profile_apply_command": apply_command,
        }

    def _derive_out_of_scope(self, manifest: AgentTemplateManifest) -> list[str]:
        base = [
            "manifest edits without catalog-edit or validate flow",
            "cross-repo sync pull or clone without explicit approval",
            "graph relationship apply without graph-curator tasking",
        ]
        if manifest.archetype == AgentArchetype.SPECIALIST:
            if manifest.scope == AgentScopeLevel.REPO:
                return base + [
                    "cross-repo implementation without overseer coordination",
                    "workspace layout or catalog bootstrap mutations",
                ]
            if manifest.scope == AgentScopeLevel.WORKSPACE:
                return base + [
                    "direct single-repo code edits (delegate to repo-implementer)",
                ]
        if manifest.archetype == AgentArchetype.CONTROL_PLANE:
            return base + [
                "direct single-repo implementation (delegate via dispatch-plan)",
            ]
        return base
