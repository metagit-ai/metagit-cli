"""
Workspace subcommand
"""

import sys
from pathlib import Path

import click

from metagit.cli.commands.project_repo import execute_repo_select
from metagit.cli.commands.workspace_import import workspace_import
from metagit.cli.json_output import (
    emit_json,
    exit_on_catalog_mutation,
    exit_on_layout_mutation,
)
from metagit.cli.shell_completion import complete_projects, complete_repos
from metagit.core.appconfig import AppConfig
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService
from metagit.core.mcp.services.workspace_search import WorkspaceSearchService
from metagit.core.workspace.catalog_models import CatalogError
from metagit.core.workspace.catalog_service import WorkspaceCatalogService
from metagit.core.workspace.dedupe_resolver import resolve_dedupe_for_layout
from metagit.core.workspace.layout_resolver import resolve_active_project_name
from metagit.core.workspace.layout_service import WorkspaceLayoutService

_WORKSPACE_GREP_EPILOG = """
Examples:

  Whole workspace (all managed repos):

    metagit workspace grep "DATABASE_URL" --json

  Single project:

    metagit workspace grep 'module "vpc"' --project platform --json

  Single repo with context lines:

    metagit workspace grep "def main" --project portfolio --repo api -C 2

  Terraform-oriented preset:

    metagit workspace grep "aws_instance" --preset terraform --project infra

  Matching paths only:

    metagit workspace grep "TODO" --files-with-matches --limit 50

  Ripgrep backend status:

    metagit workspace grep info --json
"""


class _WorkspaceGrepGroup(click.Group):
    """Route `grep QUERY` to search and `grep info` to the info subcommand."""

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str | None, click.Command | None, list[str]]:
        if args and args[0] == "info":
            return super().resolve_command(ctx, args)
        if not args:
            return None, None, []
        cmd = self.get_command(ctx, "search")
        return "search", cmd, args


def _catalog_ctx(ctx: click.Context) -> tuple[MetagitConfig, str, str]:
    local_config: MetagitConfig = ctx.obj["local_config"]
    config_path: str = ctx.obj["config_path"]
    app_config: AppConfig = ctx.obj["config"]
    workspace_root = str(Path(app_config.workspace.path).expanduser().resolve())
    return local_config, config_path, workspace_root


def _layout_ctx(ctx: click.Context) -> tuple[MetagitConfig, str, str, AppConfig]:
    local_config, config_path, workspace_root = _catalog_ctx(ctx)
    app_config: AppConfig = ctx.obj["config"]
    return local_config, config_path, workspace_root, app_config


@click.group(name="workspace", invoke_without_command=True)
@click.option(
    "--config",
    "config_path",
    default=".metagit.yml",
    help="Path to the metagit definition file",
)
@click.pass_context
def workspace(ctx: click.Context, config_path: str) -> None:
    """Workspace subcommands"""

    logger = ctx.obj["logger"]
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        return

    ctx.obj["config_path"] = config_path
    try:
        config_manager = MetagitConfigManager(config_path)
        local_config = config_manager.load_config()
        if isinstance(local_config, Exception):
            raise local_config
    except Exception as e:
        logger.error(f"Failed to load metagit definition file: {e}")
        sys.exit(1)
    ctx.obj["local_config"] = local_config


@workspace.command("list")
@click.option("--json", "as_json", is_flag=True, default=False, help="Print JSON for agents")
@click.option(
    "--no-index",
    is_flag=True,
    default=False,
    help="Omit per-repo disk status from workspace list JSON",
)
@click.pass_context
def workspace_list(ctx: click.Context, as_json: bool, no_index: bool) -> None:
    """List workspace manifest summary, projects, and repository index."""
    local_config, config_path, workspace_root = _catalog_ctx(ctx)
    service = WorkspaceCatalogService()
    result = service.list_workspace(
        local_config,
        config_path,
        workspace_root,
        include_index=not no_index,
    )
    if as_json:
        emit_json(result)
        return
    summary = (result.data or {}).get("summary", {})
    click.echo(f"Definition: {summary.get('definition_path', config_path)}")
    click.echo(f"Workspace root: {summary.get('workspace_root', workspace_root)}")
    click.echo(f"Projects: {summary.get('project_count', 0)} | Repos: {summary.get('repo_count', 0)}")
    for project in (result.data or {}).get("projects", []):
        click.echo(f"  - {project.get('name')} ({project.get('repo_count', 0)} repos)")


@workspace.group("project")
@click.pass_context
def workspace_project(_ctx: click.Context) -> None:
    """Manage workspace projects in the manifest."""


@workspace_project.command("list")
@click.option("--json", "as_json", is_flag=True, default=False, help="Print JSON for agents")
@click.pass_context
def workspace_project_list(ctx: click.Context, as_json: bool) -> None:
    """List projects defined in the workspace manifest."""
    local_config, _, _ = _catalog_ctx(ctx)
    result = WorkspaceCatalogService().list_projects(local_config)
    if as_json:
        emit_json(result)
        return
    for project in (result.data or {}).get("projects", []):
        click.echo(f"{project.get('name')} ({project.get('repo_count', 0)} repos)")


@workspace_project.command("add")
@click.argument("name")
@click.option("--description", default=None, help="Project description")
@click.option("--agent-instructions", default=None, help="Agent instructions for the project")
@click.option(
    "--ensure",
    is_flag=True,
    help="Succeed without changes when the project already exists with matching fields",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Print JSON for agents")
@click.pass_context
def workspace_project_add(
    ctx: click.Context,
    name: str,
    description: str | None,
    agent_instructions: str | None,
    ensure: bool,
    as_json: bool,
) -> None:
    """Add a project to the workspace manifest."""
    local_config, config_path, _ = _catalog_ctx(ctx)
    ensure_mode = ensure or bool(ctx.obj.get("agent_mode", False))
    result = WorkspaceCatalogService().add_project(
        local_config,
        config_path,
        name=name,
        description=description,
        agent_instructions=agent_instructions,
        ensure=ensure_mode,
    )
    exit_on_catalog_mutation(result, as_json=as_json)


@workspace_project.command("remove")
@click.argument("name")
@click.option("--force", is_flag=True, default=False, help="Remove protected projects")
@click.option("--json", "as_json", is_flag=True, default=False, help="Print JSON for agents")
@click.pass_context
def workspace_project_remove(
    ctx: click.Context,
    name: str,
    force: bool,
    as_json: bool,
) -> None:
    """Remove a project (and its repos) from the workspace manifest."""
    local_config, config_path, _ = _catalog_ctx(ctx)
    result = WorkspaceCatalogService().remove_project(
        local_config,
        config_path,
        name=name,
        force=force,
    )
    exit_on_catalog_mutation(result, as_json=as_json)


@workspace_project.command("rename")
@click.argument("from_name")
@click.argument("to_name")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show planned manifest and disk steps without applying",
)
@click.option(
    "--manifest-only",
    is_flag=True,
    default=False,
    help="Update .metagit.yml only; do not rename sync folders",
)
@click.option(
    "--no-update-sessions",
    is_flag=True,
    default=False,
    help="Do not migrate .metagit/sessions project files",
)
@click.option("--force", is_flag=True, default=False, help="Overwrite existing targets")
@click.option("--json", "as_json", is_flag=True, default=False, help="Print JSON for agents")
@click.pass_context
def workspace_project_rename(
    ctx: click.Context,
    from_name: str,
    to_name: str,
    dry_run: bool,
    manifest_only: bool,
    no_update_sessions: bool,
    force: bool,
    as_json: bool,
) -> None:
    """Rename a workspace project (manifest and sync folder when present)."""
    local_config, config_path, workspace_root, app_config = _layout_ctx(ctx)
    dedupe = resolve_dedupe_for_layout(
        app_config.workspace.dedupe,
        local_config,
        from_name,
    )
    result = WorkspaceLayoutService().rename_project(
        local_config,
        config_path,
        workspace_root,
        from_name=from_name,
        to_name=to_name,
        dedupe=dedupe,
        dry_run=dry_run,
        move_disk=not manifest_only,
        update_sessions=not no_update_sessions,
        force=force,
    )
    exit_on_layout_mutation(result, as_json=as_json)


@workspace.group("repo")
@click.pass_context
def workspace_repo(_ctx: click.Context) -> None:
    """Manage repository entries in the workspace manifest."""


@workspace_repo.command("list")
@click.option(
    "--project",
    "-p",
    default=None,
    help="Limit to one project name",
    shell_complete=complete_projects,
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Print JSON for agents")
@click.pass_context
def workspace_repo_list(
    ctx: click.Context,
    project: str | None,
    as_json: bool,
) -> None:
    """List repositories in the workspace manifest."""
    local_config, _, workspace_root = _catalog_ctx(ctx)
    result = WorkspaceCatalogService().list_repos(
        local_config,
        workspace_root,
        project_name=project,
    )
    if as_json:
        emit_json(result)
        return
    for row in (result.data or {}).get("repos", []):
        repo = row.get("repo", {})
        click.echo(
            f"{row.get('project_name')}/{repo.get('name')} "
            f"path={row.get('configured_path') or repo.get('path')} "
            f"status={row.get('status') or 'unknown'}"
        )


@workspace_repo.command("add")
@click.option(
    "--project",
    "-p",
    required=True,
    help="Workspace project name",
    shell_complete=complete_projects,
)
@click.option("--name", "-n", required=True, help="Repository name", shell_complete=complete_repos)
@click.option("--description", default=None)
@click.option("--path", default=None, help="Relative path under workspace root")
@click.option("--url", default=None, help="Remote repository URL")
@click.option("--sync/--no-sync", default=None)
@click.option("--agent-instructions", default=None)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Add repos to protected projects",
)
@click.option(
    "--ensure",
    is_flag=True,
    help="Succeed without changes when the repo already exists with matching url/path",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Print JSON for agents")
@click.pass_context
def workspace_repo_add(
    ctx: click.Context,
    project: str,
    name: str,
    description: str | None,
    path: str | None,
    url: str | None,
    sync: bool | None,
    agent_instructions: str | None,
    force: bool,
    ensure: bool,
    as_json: bool,
) -> None:
    """Add a repository entry to a workspace project (manifest only)."""
    local_config, config_path, _ = _catalog_ctx(ctx)
    ensure_mode = ensure or bool(ctx.obj.get("agent_mode", False))
    service = WorkspaceCatalogService()
    built = service.build_repo_from_fields(
        name=name,
        description=description,
        path=path,
        url=url,
        sync=sync,
        agent_instructions=agent_instructions,
    )
    if isinstance(built, CatalogError):
        raise click.ClickException(built.message)
    result = service.add_repo(
        local_config,
        config_path,
        project_name=project,
        repo=built,
        ensure=ensure_mode,
        force=force,
    )
    exit_on_catalog_mutation(result, as_json=as_json)


@workspace_repo.command("remove")
@click.option(
    "--project",
    "-p",
    required=True,
    help="Workspace project name",
    shell_complete=complete_projects,
)
@click.option("--name", "-n", required=True, help="Repository name", shell_complete=complete_repos)
@click.option("--force", is_flag=True, default=False, help="Remove protected repos")
@click.option("--json", "as_json", is_flag=True, default=False, help="Print JSON for agents")
@click.pass_context
def workspace_repo_remove(
    ctx: click.Context,
    project: str,
    name: str,
    force: bool,
    as_json: bool,
) -> None:
    """Remove a repository entry from the workspace manifest (does not delete files)."""
    local_config, config_path, _ = _catalog_ctx(ctx)
    result = WorkspaceCatalogService().remove_repo(
        local_config,
        config_path,
        project_name=project,
        repo_name=name,
        force=force,
    )
    exit_on_catalog_mutation(result, as_json=as_json)


@workspace_repo.command("rename")
@click.option(
    "--project",
    "-p",
    required=True,
    help="Workspace project name",
    shell_complete=complete_projects,
)
@click.argument("from_name")
@click.argument("to_name")
@click.option("--dry-run", is_flag=True, default=False)
@click.option(
    "--manifest-only",
    is_flag=True,
    default=False,
    help="Update manifest only; do not rename sync mount",
)
@click.option("--force", is_flag=True, default=False)
@click.option("--json", "as_json", is_flag=True, default=False, help="Print JSON for agents")
@click.pass_context
def workspace_repo_rename(
    ctx: click.Context,
    project: str,
    from_name: str,
    to_name: str,
    dry_run: bool,
    manifest_only: bool,
    force: bool,
    as_json: bool,
) -> None:
    """Rename a repository entry and its sync mount when present."""
    local_config, config_path, workspace_root, app_config = _layout_ctx(ctx)
    dedupe = resolve_dedupe_for_layout(
        app_config.workspace.dedupe,
        local_config,
        project,
    )
    result = WorkspaceLayoutService().rename_repo(
        local_config,
        config_path,
        workspace_root,
        project_name=project,
        from_name=from_name,
        to_name=to_name,
        dedupe=dedupe,
        dry_run=dry_run,
        move_disk=not manifest_only,
        force=force,
    )
    exit_on_layout_mutation(result, as_json=as_json)


@workspace_repo.command("move")
@click.option("--project", "-p", "from_project", required=True, help="Source project")
@click.option(
    "--name",
    "-n",
    "repo_name",
    required=True,
    help="Repository name",
    shell_complete=complete_repos,
)
@click.option(
    "--to-project",
    required=True,
    help="Target workspace project",
)
@click.option("--dry-run", is_flag=True, default=False)
@click.option(
    "--manifest-only",
    is_flag=True,
    default=False,
    help="Update manifest only; do not move sync mount",
)
@click.option("--force", is_flag=True, default=False)
@click.option("--json", "as_json", is_flag=True, default=False, help="Print JSON for agents")
@click.pass_context
def workspace_repo_move(
    ctx: click.Context,
    from_project: str,
    repo_name: str,
    to_project: str,
    dry_run: bool,
    manifest_only: bool,
    force: bool,
    as_json: bool,
) -> None:
    """Move a repository entry to another workspace project."""
    local_config, config_path, workspace_root, app_config = _layout_ctx(ctx)
    dedupe = resolve_dedupe_for_layout(
        app_config.workspace.dedupe,
        local_config,
        to_project,
    )
    result = WorkspaceLayoutService().move_repo(
        local_config,
        config_path,
        workspace_root,
        repo_name=repo_name,
        from_project=from_project,
        to_project=to_project,
        dedupe=dedupe,
        dry_run=dry_run,
        move_disk=not manifest_only,
        force=force,
    )
    exit_on_layout_mutation(result, as_json=as_json)


@workspace.group(
    "grep",
    cls=_WorkspaceGrepGroup,
    invoke_without_command=True,
    epilog=_WORKSPACE_GREP_EPILOG,
)
@click.pass_context
def workspace_grep_group(ctx: click.Context) -> None:
    """
    Search on-disk file contents across managed workspace repos.

    Use `metagit search` for manifest metadata only. Matches under
    node_modules, .venv, and similar scaffold paths are always excluded.
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@workspace_grep_group.command("search")
@click.argument("query")
@click.option(
    "--project",
    "-p",
    default=None,
    help="Limit search to a workspace project",
    shell_complete=complete_projects,
)
@click.option(
    "--repo",
    "-r",
    multiple=True,
    help="Limit search to repo selector(s); repeatable",
    shell_complete=complete_repos,
)
@click.option("--preset", default=None, help="Search preset (terraform, docker, infra, ci)")
@click.option(
    "--intent",
    default=None,
    help="Intent filter (config, scripts, ci, docker, terraform)",
)
@click.option("--limit", default=25, show_default=True, help="Maximum number of hits")
@click.option(
    "-C",
    "context_lines",
    default=0,
    show_default=True,
    help="Context lines around matches",
)
@click.option(
    "--files-with-matches",
    is_flag=True,
    default=False,
    help="Return matching file paths only",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Print JSON for agents")
@click.pass_context
def workspace_grep_search(
    ctx: click.Context,
    query: str,
    project: str | None,
    repo: tuple[str, ...],
    preset: str | None,
    intent: str | None,
    limit: int,
    context_lines: int,
    files_with_matches: bool,
    as_json: bool,
) -> None:
    """Search file contents (default when a QUERY argument is provided)."""
    local_config, _, workspace_root = _catalog_ctx(ctx)
    query_text = query.strip()
    if not query_text:
        click.echo("Error: query is required", err=True)
        raise SystemExit(1)

    index_service = WorkspaceIndexService()
    search_service = WorkspaceSearchService()
    repo_rows = index_service.build_index(local_config, workspace_root)
    if project:
        repo_rows = [row for row in repo_rows if str(row.get("project_name", "")) == project]
    repo_selectors = [item.strip() for item in repo if item.strip()]
    repo_paths = search_service.filter_repo_paths(
        repo_rows=repo_rows,
        repos=repo_selectors or None,
    )
    path_to_row = {str(row.get("repo_path", "")): row for row in repo_rows}
    bounded_limit = max(1, min(int(limit), 500))
    bounded_context = max(0, min(int(context_lines), 20))
    hits = search_service.search(
        query=query_text,
        repo_paths=repo_paths,
        preset=preset,
        intent=intent,
        max_results=bounded_limit,
        context_lines=bounded_context,
        include_paths=files_with_matches,
    )
    enriched: list[dict[str, object]] = []
    for hit in hits:
        row = path_to_row.get(str(hit.get("repo_path", "")))
        enriched_hit = dict(hit)
        if row is not None:
            enriched_hit["project_name"] = row.get("project_name")
            enriched_hit["repo_name"] = row.get("repo_name")
        enriched.append(enriched_hit)

    payload = {"ok": True, "data": {"hits": enriched}}
    if as_json:
        emit_json(payload)
        return

    if not enriched:
        click.echo("No matches.")
        return
    for hit in enriched:
        project_name = hit.get("project_name", "?")
        repo_name = hit.get("repo_name", "?")
        file_path = hit.get("file_path", "")
        line_number = hit.get("line_number", 0)
        line_text = hit.get("line", "")
        click.echo(f"{project_name}/{repo_name}:{file_path}:{line_number}: {line_text}")


@workspace_grep_group.command("info")
@click.option("--json", "as_json", is_flag=True, default=False, help="Print JSON for agents")
@click.pass_context
def workspace_grep_info(ctx: click.Context, as_json: bool) -> None:
    """Show ripgrep availability and workspace grep search backend."""
    _ = ctx
    status = WorkspaceSearchService.ripgrep_status()
    payload = {"ok": True, "data": status}
    if as_json:
        emit_json(payload)
        return
    if status.get("ripgrep_available"):
        click.echo(f"ripgrep: available ({status.get('ripgrep_path')})")
        version = status.get("ripgrep_version")
        if version:
            click.echo(f"version: {version}")
    else:
        click.echo("ripgrep: not found on PATH")
    click.echo(f"search backend: {status.get('search_backend')}")


@workspace.command("select")
@click.option(
    "--project",
    "-p",
    default=None,
    help="Project within workspace to select target paths from",
    shell_complete=complete_projects,
)
@click.option(
    "--repo",
    "repo_name",
    default=None,
    help="Open this repository in the default editor without the picker TUI",
    shell_complete=complete_repos,
)
@click.pass_context
def workspace_select(ctx: click.Context, project: str = None, repo_name: str | None = None) -> None:
    """Select project repo to work on"""
    app_config: AppConfig = ctx.obj["config"]
    local_config: MetagitConfig = ctx.obj["local_config"]
    ctx.obj["project"] = resolve_active_project_name(
        local_config,
        explicit=project,
        default_project=app_config.workspace.default_project,
    )
    execute_repo_select(ctx, repo_name=repo_name)


workspace.add_command(workspace_import, name="import")
