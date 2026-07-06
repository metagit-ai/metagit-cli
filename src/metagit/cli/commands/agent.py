#!/usr/bin/env python
"""Agent template export and vendor install commands."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import click

from metagit.cli.commands.init import _resolve_project_metadata, resolve_target_dir
from metagit.core.agent import AGENT_SUPPORTED_TARGETS, AgentService
from metagit.core.agent.models import AgentOverlayInitMode, AgentOverlayScope
from metagit.core.agent.overlay import primary_overlay_edit_path
from metagit.core.agent.paths import autodetect_agent_targets
from metagit.core.agent.profile_service import AgentProfileService
from metagit.core.agent.schema_generator import write_agent_template_schema
from metagit.core.appconfig import load_config as load_appconfig
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.utils.common import open_editor
from metagit.core.workspace.root_resolver import resolve_definition_root, resolve_sync_root


def _parse_tag_filters(tag_values: tuple[str, ...]) -> dict[str, str] | None:
    if not tag_values:
        return None
    parsed: dict[str, str] = {}
    for item in tag_values:
        if "=" not in item:
            raise click.ClickException(f"Invalid --tag (expected key=value): {item!r}")
        key, value = item.split("=", 1)
        parsed[key] = value
    return parsed


def _profile_service(root: str, *, config_path: str | None = None) -> AgentProfileService:
    manifest_root = _require_manifest_root(root)
    manager = MetagitConfigManager(config_path=os.path.join(root, ".metagit.yml"))
    config = manager.load_config()
    if isinstance(config, Exception):
        raise click.ClickException(str(config))
    workspace_root = manifest_root
    if config_path:
        appconfig = load_appconfig(config_path)
        if not isinstance(appconfig, Exception) and appconfig.workspace and appconfig.workspace.path:
            workspace_root = Path(resolve_sync_root(str(manifest_root), appconfig.workspace.path))
    return AgentProfileService(
        config=config,
        definition_root=manifest_root,
        workspace_root=workspace_root,
    )


def _emit_json(payload: object) -> None:
    click.echo(json.dumps(payload, indent=2, sort_keys=False))


def _resolve_manifest_root(root: Optional[str]) -> Path | None:
    if root is None:
        return None
    return Path(resolve_definition_root(root))


def _service_for_root(root: Optional[str]) -> AgentService:
    return AgentService(manifest_root=_resolve_manifest_root(root))


def _require_manifest_root(root: str) -> Path:
    manifest_root = _resolve_manifest_root(root)
    if manifest_root is None:
        raise click.ClickException("Invalid manifest root")
    manifest_path = manifest_root / ".metagit.yml"
    if not manifest_path.is_file():
        raise click.ClickException(f"No .metagit.yml found under manifest root: {manifest_root}")
    return manifest_root


@click.group(name="agent", invoke_without_command=True)
@click.pass_context
def agent(ctx: click.Context) -> None:
    """Export and install bundled agent definitions for coding vendors."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        return


@agent.command("list")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.option(
    "--root",
    type=click.Path(exists=True, file_okay=True, dir_okay=True),
    default=None,
    help="Manifest root for workspace template overlays.",
)
@click.pass_context
def agent_list(ctx: click.Context, as_json: bool, root: Optional[str]) -> None:
    """List bundled agent templates."""
    service = _service_for_root(root)
    if as_json:
        envelope = service.catalog.list_catalog(
            manifest_root=_resolve_manifest_root(root),
        )
        _emit_json(envelope.model_dump(mode="json"))
        return
    logger = ctx.obj["logger"]
    templates = service.list_templates()
    if not templates:
        logger.warning("No bundled agent templates found.")
        return
    logger.info("Bundled agent templates:")
    for item in templates:
        logger.echo(f"- {item.id}: {item.label}")


@agent.command("show")
@click.argument("template_id")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.option(
    "--root",
    type=click.Path(exists=True, file_okay=True, dir_okay=True),
    default=None,
    help="Manifest root for workspace template overlays.",
)
@click.pass_context
def agent_show(
    ctx: click.Context,
    template_id: str,
    as_json: bool,
    root: Optional[str],
) -> None:
    """Show one agent template manifest."""
    service = _service_for_root(root)
    detail = service.template_detail(template_id)
    if detail is None:
        raise click.ClickException(f"Unknown agent template: {template_id!r}")
    if as_json:
        _emit_json(detail.model_dump(mode="json"))
        return
    manifest = detail.manifest
    logger = ctx.obj["logger"]
    logger.echo(f"id: {manifest.id}")
    logger.echo(f"label: {manifest.label}")
    logger.echo(f"source: {detail.source.value}")
    logger.echo(manifest.description.strip())
    if manifest.recommended_skills:
        logger.echo("recommended_skills:")
        for skill_name in manifest.recommended_skills:
            logger.echo(f"  - {skill_name}")
    if manifest.external_skills:
        logger.echo("external_skills:")
        for ref in manifest.external_skills:
            logger.echo(f"  - {ref.name}: {ref.note.strip()}")
    if manifest.vendors:
        logger.echo("vendors:")
        for vendor_id, spec in sorted(manifest.vendors.items()):
            logger.echo(f"  - {vendor_id}: {spec.filename}")


@agent.command("schema")
@click.option(
    "--output-path",
    type=click.Path(dir_okay=False),
    default="./schemas/agent_template.schema.json",
    show_default=True,
    help="Write JSON Schema to this path.",
)
@click.pass_context
def agent_schema(ctx: click.Context, output_path: str) -> None:
    """Write the agent template manifest JSON Schema."""
    destination = write_agent_template_schema(Path(output_path))
    logger = ctx.obj["logger"]
    logger.echo(f"Wrote schema: {destination}")


@agent.command("validate")
@click.option(
    "--template",
    "template_id",
    default=None,
    help="Validate one template id (default: all bundled + overlays).",
)
@click.option(
    "--root",
    type=click.Path(exists=True, file_okay=True, dir_okay=True),
    default=None,
    help="Manifest root for workspace template overlays.",
)
@click.pass_context
def agent_validate(
    ctx: click.Context,
    template_id: Optional[str],
    root: Optional[str],
) -> None:
    """Validate agent template manifests and template files."""
    service = _service_for_root(root)
    issues = service.catalog.validate_all_templates(
        manifest_root=_resolve_manifest_root(root),
        template_id=template_id,
    )
    logger = ctx.obj["logger"]
    if not issues:
        logger.echo("All agent templates validated.")
        return
    for issue in issues:
        location = f" ({issue.path})" if issue.path else ""
        logger.error(f"{issue.template_id}{location}: {issue.message}")
    raise click.ClickException("Agent template validation failed.")


@agent.command("preview")
@click.argument("template_id")
@click.option(
    "--vendor",
    type=click.Choice(AGENT_SUPPORTED_TARGETS),
    default="claude_code",
    show_default=True,
    help="Vendor artifact to render.",
)
@click.option(
    "--root",
    type=click.Path(exists=True, file_okay=True, dir_okay=True),
    default=".",
    show_default=True,
    help="Manifest root for overlays and prompt defaults.",
)
@click.option(
    "--answers-file",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="YAML/JSON mapping of template variables.",
)
@click.option("--no-prompt", is_flag=True, help="Use defaults only; fail if required.")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def agent_preview(
    ctx: click.Context,
    template_id: str,
    vendor: str,
    root: str,
    answers_file: Optional[str],
    no_prompt: bool,
    as_json: bool,
) -> None:
    """Render a vendor artifact without writing files."""
    root_path = resolve_target_dir(root, create=False)
    directory_name, git_remote_url = _resolve_project_metadata(root_path)
    service = _service_for_root(root)
    preview = service.preview(
        template_id,
        vendor=vendor,
        directory_name=directory_name,
        git_remote_url=git_remote_url,
        answers_file=Path(answers_file) if answers_file else None,
        no_prompt=no_prompt,
    )
    if as_json:
        _emit_json(preview.model_dump(mode="json"))
        return
    logger = ctx.obj["logger"]
    logger.echo(preview.content)


@agent.command("dispatch-plan")
@click.argument("template_id")
@click.option(
    "--vendor",
    type=click.Choice(AGENT_SUPPORTED_TARGETS),
    default="claude_code",
    show_default=True,
    help="Vendor runtime to target for install and launch hints.",
)
@click.option(
    "--project",
    "-p",
    default=None,
    help="Workspace project name for repo- or project-scoped dispatch.",
)
@click.option(
    "--repo",
    "-n",
    default=None,
    help="Repository name within --project.",
)
@click.option(
    "--root",
    type=click.Path(exists=True, file_okay=True, dir_okay=True),
    default=".",
    show_default=True,
    help="Manifest root containing `.metagit.yml`.",
)
@click.option(
    "--scope",
    type=click.Choice(["project", "user"]),
    default="project",
    show_default=True,
    help="Install scope when checking or suggesting `agent create`.",
)
@click.option("--task", default=None, help="Short task summary for launch hints.")
@click.option(
    "--definition",
    "-c",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
    help="Path to workspace definition (for handoff CLI commands).",
)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def agent_dispatch_plan(
    ctx: click.Context,
    template_id: str,
    vendor: str,
    project: Optional[str],
    repo: Optional[str],
    root: str,
    scope: str,
    task: Optional[str],
    definition_path: str,
    as_json: bool,
) -> None:
    """Build install, launch, and handoff envelope for subagent dispatch."""
    manifest_root = _require_manifest_root(root)
    service = AgentService(manifest_root=manifest_root)
    plan = service.dispatch_plan(
        template_id,
        vendor=vendor,
        scope=scope,  # type: ignore[arg-type]
        project=project,
        repo=repo,
        task=task,
        definition_path=definition_path,
    )
    if as_json:
        _emit_json(plan.model_dump(mode="json"))
        return
    logger = ctx.obj["logger"]
    logger.echo(f"template: {plan.template_id}")
    logger.echo(f"install needed: {plan.install.needed} ({plan.install.path})")
    if plan.install.needed:
        logger.echo(f"install: {plan.install.command}")
    logger.echo(f"launch ({vendor}): {plan.launch.get(vendor, '')}")
    logger.echo(f"context: {plan.handoff.context_pack}")
    logger.echo(f"prompt: {plan.handoff.prompt}")


@agent.command("export")
@click.argument("template_id")
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=False, dir_okay=True),
    default=".",
    show_default=True,
    help="Directory to write rendered template files.",
)
@click.option(
    "--root",
    type=click.Path(exists=True, file_okay=True, dir_okay=True),
    default=None,
    help="Manifest root for workspace template overlays.",
)
@click.option(
    "--answers-file",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="YAML/JSON mapping of template variables.",
)
@click.option("--no-prompt", is_flag=True, help="Use defaults only; fail if required.")
@click.option("--force", is_flag=True, help="Overwrite existing output files.")
@click.option("--dry-run", is_flag=True, help="Render without writing files.")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def agent_export(
    ctx: click.Context,
    template_id: str,
    output: str,
    root: Optional[str],
    answers_file: Optional[str],
    no_prompt: bool,
    force: bool,
    dry_run: bool,
    as_json: bool,
) -> None:
    """Export a template to files (vendor-neutral layout)."""
    output_dir = Path(output).expanduser().resolve()
    directory_name, git_remote_url = _resolve_project_metadata(output_dir)
    service = _service_for_root(root)
    result = service.export(
        template_id,
        output_dir,
        directory_name=directory_name,
        git_remote_url=git_remote_url,
        answers_file=Path(answers_file) if answers_file else None,
        no_prompt=no_prompt,
        force=force,
        dry_run=dry_run,
    )
    if as_json:
        _emit_json(result.model_dump())
        return
    logger = ctx.obj["logger"]
    verb = "Would write" if dry_run else "Wrote"
    for path in result.paths:
        logger.echo(f"{verb}: {path}")


@agent.command("create")
@click.argument("template_id")
@click.option(
    "--vendor",
    "--target",
    "vendor",
    type=click.Choice(AGENT_SUPPORTED_TARGETS),
    default=None,
    help="Coding vendor to install for (auto-detect when omitted).",
)
@click.option(
    "--scope",
    type=click.Choice(["project", "user"]),
    default="project",
    show_default=True,
    help="Install to project-local or user-global vendor config.",
)
@click.option(
    "--project-root",
    type=click.Path(file_okay=False, dir_okay=True),
    default=".",
    show_default=True,
    help="Workspace coordinator root (for project scope paths).",
)
@click.option(
    "--root",
    type=click.Path(exists=True, file_okay=True, dir_okay=True),
    default=None,
    help="Manifest root for workspace template overlays.",
)
@click.option(
    "--answers-file",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="YAML/JSON mapping of template variables.",
)
@click.option("--no-prompt", is_flag=True, help="Use defaults only; fail if required.")
@click.option("--force", is_flag=True, help="Overwrite an existing agent definition.")
@click.option("--dry-run", is_flag=True, help="Show actions without writing files.")
@click.option(
    "--install-skills",
    is_flag=True,
    help="Install template recommended_skills for the selected vendor.",
)
@click.option(
    "--install-mcp",
    is_flag=True,
    help="Install metagit MCP server config for the selected vendor.",
)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def agent_create(
    ctx: click.Context,
    template_id: str,
    vendor: Optional[str],
    scope: str,
    project_root: str,
    root: Optional[str],
    answers_file: Optional[str],
    no_prompt: bool,
    force: bool,
    dry_run: bool,
    install_skills: bool,
    install_mcp: bool,
    as_json: bool,
) -> None:
    """Install an agent definition into a vendor-specific agents directory."""
    resolved_root = root or project_root
    root_path = resolve_target_dir(resolved_root, create=False)
    directory_name, git_remote_url = _resolve_project_metadata(root_path)
    vendors = [vendor] if vendor else autodetect_agent_targets(scope, project_root=root_path)
    if not vendors:
        raise click.ClickException("No vendor detected. Pass --vendor (e.g. cursor, claude_code, hermes, opencode).")
    if len(vendors) > 1 and vendor is None:
        raise click.ClickException(f"Multiple vendors detected ({', '.join(vendors)}). Pass --vendor to choose one.")
    selected_vendor = vendors[0]
    service = _service_for_root(resolved_root)
    write_result, install_results = service.create(
        template_id,
        vendor=selected_vendor,
        scope=scope,
        project_root=root_path,
        directory_name=directory_name,
        git_remote_url=git_remote_url,
        answers_file=Path(answers_file) if answers_file else None,
        no_prompt=no_prompt,
        force=force,
        dry_run=dry_run,
        install_skills=install_skills,
        install_mcp=install_mcp,
    )
    if as_json:
        _emit_json(
            {
                "write": write_result.model_dump(),
                "install": [item.model_dump() for item in install_results],
            }
        )
        return
    logger = ctx.obj["logger"]
    verb = "Would write" if dry_run else "Wrote"
    for path in write_result.paths:
        logger.echo(f"{verb} agent: {path}")
    for item in install_results:
        logger.echo(f"{item.details} -> {item.path}")


@agent.command("apply")
@click.option(
    "--vendor",
    type=click.Choice(AGENT_SUPPORTED_TARGETS),
    required=True,
    help="Vendor runtime to materialize profiles into.",
)
@click.option(
    "--project",
    "-p",
    default=None,
    help="Limit to one workspace project.",
)
@click.option(
    "--repo",
    "-n",
    default=None,
    help="Limit to one repository within --project.",
)
@click.option(
    "--tag",
    "tag_values",
    multiple=True,
    help="Filter targets by inherited tag, e.g. --tag agent_tier=full",
)
@click.option(
    "--root",
    type=click.Path(exists=True, file_okay=True, dir_okay=True),
    default=".",
    show_default=True,
    help="Manifest root containing `.metagit.yml`.",
)
@click.option(
    "--scope",
    type=click.Choice(["project", "user"]),
    default="project",
    show_default=True,
    help="Install scope for skills and MCP artifacts.",
)
@click.option("--dry-run", is_flag=True, help="Print the apply plan without writing files.")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def agent_apply(
    ctx: click.Context,
    vendor: str,
    project: Optional[str],
    repo: Optional[str],
    tag_values: tuple[str, ...],
    root: str,
    scope: str,
    dry_run: bool,
    as_json: bool,
) -> None:
    """Materialize merged agent_profile blocks into vendor runtimes."""
    if repo and not project:
        raise click.ClickException("--repo requires --project")
    config_path = ctx.obj.get("config_path")
    service = _profile_service(root, config_path=config_path)
    try:
        summary = service.apply(
            vendor=vendor,
            scope=scope,  # type: ignore[arg-type]
            project=project,
            repo=repo,
            tag_filters=_parse_tag_filters(tag_values),
            dry_run=dry_run,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if as_json:
        _emit_json(summary.model_dump(mode="json"))
        return
    logger = ctx.obj["logger"]
    if not summary.targets:
        logger.warning("No repositories matched the selection or had an agent profile.")
        return
    for target in summary.targets:
        prefix = "Would apply" if dry_run else "Applied"
        logger.echo(f"{prefix} {target.project_name}/{target.repo_name} @ {target.repo_path}")
        for detail in target.details:
            logger.echo(f"  {detail}")


@click.group(name="profile")
def agent_profile() -> None:
    """Inspect and validate agent_profile blocks in the manifest."""


@agent_profile.command("show")
@click.option(
    "--project",
    "-p",
    required=True,
    help="Workspace project name.",
)
@click.option(
    "--repo",
    "-n",
    required=True,
    help="Repository name within --project.",
)
@click.option(
    "--root",
    type=click.Path(exists=True, file_okay=True, dir_okay=True),
    default=".",
    show_default=True,
    help="Manifest root containing `.metagit.yml`.",
)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def agent_profile_show(
    ctx: click.Context,
    project: str,
    repo: str,
    root: str,
    as_json: bool,
) -> None:
    """Print the fully merged effective agent profile for one repo."""
    _ = ctx
    config_path = ctx.obj.get("config_path")
    service = _profile_service(root, config_path=config_path)
    effective = service.effective_profile(project_name=project, repo_name=repo)
    if effective is None:
        raise click.ClickException(f"No profile or repo found for {project}/{repo}")
    if as_json:
        _emit_json(effective.model_dump(mode="json"))
        return
    click.echo(f"tier: {effective.tier or '(unset)'}")
    click.echo(f"skills: {', '.join(effective.skills) if effective.skills else '(none)'}")
    click.echo(f"mcp: {', '.join(effective.mcp) if effective.mcp else '(none)'}")
    click.echo(f"rules: {', '.join(effective.rules) if effective.rules else '(none)'}")
    click.echo(f"vendors: {', '.join(effective.vendors) if effective.vendors else '(all)'}")
    if effective.layers:
        click.echo("layers:")
        for layer in effective.layers:
            click.echo(f"  - {layer.scope}")


agent.add_command(agent_profile)


@click.group(name="overlay")
def agent_overlay() -> None:
    """Workspace overlay templates under `.metagit/.agent-templates/`."""


@agent_overlay.command("init")
@click.argument("template_id")
@click.option(
    "--root",
    type=click.Path(exists=True, file_okay=True, dir_okay=True),
    default=".",
    show_default=True,
    help="Manifest root containing `.metagit.yml`.",
)
@click.option(
    "--mode",
    type=click.Choice(["minimal", "full"]),
    default="full",
    show_default=True,
    help="minimal copies manifest stub + body; full copies all bundled sources.",
)
@click.option(
    "--local",
    is_flag=True,
    help="Write to gitignored `.metagit/.agent-templates/` (personal override).",
)
@click.option("--force", is_flag=True, help="Replace an existing overlay directory.")
@click.option("--dry-run", is_flag=True, help="Show files that would be written.")
@click.option(
    "--open/--no-open",
    "open_editor_flag",
    default=False,
    help="Open the primary overlay file in $EDITOR after scaffolding.",
)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def agent_overlay_init(
    ctx: click.Context,
    template_id: str,
    root: str,
    mode: str,
    local: bool,
    force: bool,
    dry_run: bool,
    open_editor_flag: bool,
    as_json: bool,
) -> None:
    """Scaffold an editable overlay from a bundled agent template."""
    manifest_root = _require_manifest_root(root)
    service = AgentService(manifest_root=manifest_root)
    scope = AgentOverlayScope.LOCAL if local else AgentOverlayScope.COMMITTED
    result = service.init_overlay(
        template_id,
        scope=scope,
        mode=AgentOverlayInitMode(mode),
        force=force,
        dry_run=dry_run,
    )
    if as_json:
        _emit_json(result.model_dump(mode="json"))
    else:
        logger = ctx.obj["logger"]
        verb = "Would write" if dry_run else "Wrote"
        for path in result.paths:
            logger.echo(f"{verb}: {path}")
        logger.echo(f"Overlay path: {result.overlay_path}")

    if open_editor_flag and not dry_run:
        edit_path = primary_overlay_edit_path(result)
        if edit_path is None:
            return
        appconfig = load_appconfig(ctx.obj["config_path"])
        editor = "vim"
        if not isinstance(appconfig, Exception) and appconfig.editor:
            editor = appconfig.editor
        opened = open_editor(editor, edit_path)
        if isinstance(opened, Exception):
            raise click.ClickException(f"Failed to open editor: {opened}")


@agent_overlay.command("path")
@click.argument("template_id")
@click.option(
    "--root",
    type=click.Path(exists=True, file_okay=True, dir_okay=True),
    default=".",
    show_default=True,
    help="Manifest root containing `.metagit.yml`.",
)
@click.pass_context
def agent_overlay_path(ctx: click.Context, template_id: str, root: str) -> None:
    """Print committed and local overlay directories for a template id."""
    from metagit.core.agent.overlay import overlay_path_for_template

    manifest_root = _require_manifest_root(root)
    logger = ctx.obj["logger"]
    logger.echo(
        f"committed: {overlay_path_for_template(manifest_root, template_id, scope=AgentOverlayScope.COMMITTED)}"
    )
    logger.echo(f"local: {overlay_path_for_template(manifest_root, template_id, scope=AgentOverlayScope.LOCAL)}")


agent.add_command(agent_overlay)
