"""
Config subcommand
"""

import json
import os
from pathlib import Path
from typing import Union

import click

from metagit.cli.config_patch_ops import (
    emit_patch_result,
    emit_preview_result,
    emit_tree_result,
    resolve_operations,
)
from metagit.cli.json_output import emit_json
from metagit.core.appconfig import AppConfig
from metagit.core.config.graph_cypher_export import GraphCypherExportService
from metagit.core.config.graph_suggest import GraphRelationshipSuggestService
from metagit.core.config.manager import MetagitConfigManager, create_metagit_config
from metagit.core.config.patch_service import ConfigPatchService
from metagit.core.config.yaml_display import dump_config_dict


@click.group(name="config", invoke_without_command=True)
@click.option(
    "--config-path",
    "-c",
    help="Path to the metagit configuration file",
    default=".metagit.yml",
)
@click.pass_context
def config(ctx: click.Context, config_path: str) -> None:
    """Configuration subcommands"""
    try:
        # If no subcommand is provided, show help
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())
            return
        ctx.ensure_object(dict)
        ctx.obj["config_path"] = config_path
        # Initialize a dummy logger for testing purposes if not already present
        if "logger" not in ctx.obj:
            from metagit.core.utils.logging import LoggerConfig, UnifiedLogger

            ctx.obj["logger"] = UnifiedLogger(LoggerConfig(log_level="INFO", minimal_console=True))
    except Exception as e:
        logger = ctx.obj.get("logger")
        if logger:
            logger.error(f"An error occurred in the config command: {e}")
        else:
            click.echo(f"An error occurred: {e}", err=True)
        ctx.abort()


@config.command("show")
@click.option(
    "--normalized",
    is_flag=True,
    default=False,
    help="Re-serialize from the loaded model (readable YAML, not the file on disk)",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Print JSON for agents")
@click.pass_context
def config_show(ctx: click.Context, normalized: bool, as_json: bool) -> None:
    """Show metagit configuration (source file by default)."""
    logger = ctx.obj["logger"]
    try:
        config_path = ctx.obj["config_path"]
        config_manager = MetagitConfigManager(config_path=config_path)
        config_result = config_manager.load_config()
        if isinstance(config_result, Exception):
            raise config_result

        if as_json:
            emit_json(config_result.model_dump(mode="json", exclude_none=True))
            return

        path = Path(config_path)
        if not normalized and path.is_file():
            raw = path.read_text(encoding="utf-8")
            click.echo(raw, nl=raw.endswith("\n"))
            return

        output = dump_config_dict(config_result.model_dump(mode="json", exclude_none=True))
        click.echo(output, nl=False)
        if not output.endswith("\n"):
            click.echo()
    except Exception as e:
        logger.error(f"Failed to load metagit configuration file: {e}")
        logger.debug(f"Error: {e}")
        ctx.abort()


@config.command("create")
@click.option(
    "--output-path",
    help="Path to the metagit configuration file",
    default=None,
)
@click.option("--name", help="Project name", default=None)
@click.option(
    "--description",
    help="Project description",
    default=None,
)
@click.option(
    "--url",
    help="Project URL",
    default=None,
)
@click.option(
    "--kind",
    help="Project kind",
    default=None,
)
@click.pass_context
def config_create(
    ctx: click.Context,
    output_path: str,
    name: str,
    description: str,
    url: str,
    kind: str,
) -> None:
    """Create metagit config files"""
    logger = ctx.obj["logger"]

    try:
        config_file = create_metagit_config(name=name, description=description, url=url, kind=kind, as_yaml=True)
        if isinstance(config_file, Exception):
            raise config_file
    except Exception as e:
        logger.error(f"Failed to create config: {e}")
        ctx.abort()

    if output_path is None:
        logger.echo(config_file)
    else:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(config_file)
        logger.success(f"Configuration file {output_path} created")


@config.command("validate")
@click.option(
    "--config-path",
    "-c",
    help="Path to the configuration file",
    default=None,
)
@click.pass_context
def config_validate(ctx: click.Context, config_path: Union[str, None] = None) -> None:
    """Validate metagit configuration"""
    logger = ctx.obj["logger"]
    target_path = config_path or ctx.obj["config_path"]
    try:
        config_manager = MetagitConfigManager(config_path=target_path)
        result = config_manager.load_config()
        if isinstance(result, Exception):
            raise result
        logger.success(f"Configuration file {target_path} is valid")
    except Exception as e:
        logger.error(f"Failed to load metagit configuration file: {e}")
        logger.debug(f"Error: {e}")
        ctx.abort()


@config.command("providers")
@click.option(
    "--show",
    is_flag=True,
    default=False,
    help="Show current provider configuration.",
)
@click.option(
    "--enable-github",
    is_flag=True,
    default=False,
    help="Enable GitHub provider.",
)
@click.option(
    "--disable-github",
    is_flag=True,
    default=False,
    help="Disable GitHub provider.",
)
@click.option(
    "--enable-gitlab",
    is_flag=True,
    default=False,
    help="Enable GitLab provider.",
)
@click.option(
    "--disable-gitlab",
    is_flag=True,
    default=False,
    help="Disable GitLab provider.",
)
@click.option(
    "--github-token",
    help="Set GitHub API token.",
)
@click.option(
    "--gitlab-token",
    help="Set GitLab API token.",
)
@click.option(
    "--github-url",
    help="Set GitHub API base URL (for GitHub Enterprise).",
)
@click.option(
    "--gitlab-url",
    help="Set GitLab API base URL (for self-hosted GitLab).",
)
@click.option(
    "--config-path",
    help="Path to configuration file (default: ~/.config/metagit/config.yml).",
)
@click.pass_context
def providers(
    ctx: click.Context,
    show: bool,
    enable_github: bool,
    disable_github: bool,
    enable_gitlab: bool,
    disable_gitlab: bool,
    github_token: str,
    gitlab_token: str,
    github_url: str,
    gitlab_url: str,
    config_path: str,
) -> None:
    """Manage git provider plugin configuration."""
    logger = ctx.obj["logger"]

    try:
        # Load current configuration
        app_config = AppConfig.load(config_path)
        if isinstance(app_config, Exception):
            logger.error(f"Failed to load configuration: {app_config}")
            ctx.abort()

        # Show current configuration
        if show:
            click.echo("Current Provider Configuration:")
            click.echo(f"  GitHub: {'Enabled' if app_config.providers.github.enabled else 'Disabled'}")
            if app_config.providers.github.api_token:
                click.echo(f"    Token: {'*' * 10}{app_config.providers.github.api_token[-4:]}")
            else:
                click.echo("    Token: Not set")
            click.echo(f"    Base URL: {app_config.providers.github.base_url}")

            click.echo(f"  GitLab: {'Enabled' if app_config.providers.gitlab.enabled else 'Disabled'}")
            if app_config.providers.gitlab.api_token:
                click.echo(f"    Token: {'*' * 10}{app_config.providers.gitlab.api_token[-4:]}")
            else:
                click.echo("    Token: Not set")
            click.echo(f"    Base URL: {app_config.providers.gitlab.base_url}")
            return

        # Update configuration
        modified = False

        # GitHub configuration
        if enable_github:
            app_config.providers.github.enabled = True
            modified = True
            click.echo("✅ GitHub provider enabled")

        if disable_github:
            app_config.providers.github.enabled = False
            modified = True
            click.echo("✅ GitHub provider disabled")

        if github_token:
            app_config.providers.github.api_token = github_token
            modified = True
            click.echo("✅ GitHub token updated")

        if github_url:
            app_config.providers.github.base_url = github_url
            modified = True
            click.echo("✅ GitHub base URL updated")

        # GitLab configuration
        if enable_gitlab:
            app_config.providers.gitlab.enabled = True
            modified = True
            click.echo("✅ GitLab provider enabled")

        if disable_gitlab:
            app_config.providers.gitlab.enabled = False
            modified = True
            click.echo("✅ GitLab provider disabled")

        if gitlab_token:
            app_config.providers.gitlab.api_token = gitlab_token
            modified = True
            click.echo("✅ GitLab token updated")

        if gitlab_url:
            app_config.providers.gitlab.base_url = gitlab_url
            modified = True
            click.echo("✅ GitLab base URL updated")

        # Save configuration if modified
        if modified:
            result = app_config.save(config_path)
            if isinstance(result, Exception):
                logger.error(f"Failed to save configuration: {result}")
                ctx.abort()
            click.echo("✅ Configuration saved")
        else:
            click.echo("No changes made. Use --show to view current configuration.")

    except Exception as e:
        logger.error(f"Error managing provider configuration: {e}")
        ctx.abort()


@config.command("set")
@click.argument("key")
@click.argument("value")
@click.pass_context
def config_set(ctx: click.Context, key: str, value: str) -> None:
    """Set a specific configuration value."""
    logger = ctx.obj["logger"]
    config_path = ctx.obj["config_path"]

    try:
        config_manager = MetagitConfigManager(config_path=config_path)
        current_config = config_manager.load_config()
        if isinstance(current_config, Exception):
            raise current_config

        # Helper to set nested attributes
        def set_nested_attr(obj, attr_path, val):
            parts = attr_path.split(".")
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    setattr(obj, part, val)
                else:
                    obj = getattr(obj, part)

        set_nested_attr(current_config, key, value)

        # Save the updated configuration
        result = config_manager.save_config(current_config)
        if isinstance(result, Exception):
            raise result

        logger.success(f"Configuration key '{key}' set to '{value}' in {config_path}")

    except Exception as e:
        logger.error(f"Failed to set configuration key '{key}': {e}")
        logger.debug(f"Error: {e}")
        ctx.abort()


@config.command("info")
@click.pass_context
def config_info(ctx: click.Context) -> None:
    """
    Display information about the local project configuration.
    """
    logger = ctx.obj["logger"]
    config_path = ctx.obj["config_path"]

    if os.path.exists(ctx.obj["config_path"]):
        logger.config_element(name="config_path", value=config_path, console=True)
        config_manager = MetagitConfigManager(config_path=config_path)
        current_config = config_manager.load_config()
        if isinstance(current_config, Exception):
            logger.error(f"Failed to load configuration: {current_config}")
            ctx.abort()
        logger.config_element(
            name="project_name",
            value=current_config.name or "N/A",
            console=True,
        )
        logger.config_element(
            name="project_kind",
            value=current_config.kind or "N/A",
            console=True,
        )
        project_count = len(current_config.workspace.projects) if current_config.workspace.projects else 0
        logger.config_element(
            name="project_count",
            value=project_count,
            console=True,
        )
        if project_count > 0:
            for project in current_config.workspace.projects:
                logger.config_element(
                    name=f"project_{project.name}_entry_count",
                    value=len(project.repos) if project.repos else 0,
                    console=True,
                )
    else:
        logger.echo("No project config file found!")
        logger.echo("Create a new config file with 'metagit config create' or 'metagit init'")


@config.command("example")
@click.option(
    "--output",
    "output_path",
    help="Write exemplar YAML to this path (default: stdout)",
    default=None,
)
@click.option(
    "--include-workspace/--no-include-workspace",
    default=True,
    help="Include the workspace block in the generated exemplar",
)
@click.option(
    "--comment-style",
    type=click.Choice(["line", "none"], case_sensitive=False),
    default="line",
    help="Emit Field descriptions as YAML comments (line) or plain YAML only",
)
@click.pass_context
def config_example(
    ctx: click.Context,
    output_path: str | None,
    include_workspace: bool,
    comment_style: str,
) -> None:
    """
    Generate a non-production YAML exemplar with optional field descriptions.

    Merges src/metagit/data/config-example-overrides.yml when present.
    """
    from metagit.core.config.example_generator import (
        ConfigExampleGenerator,
        load_example_overrides,
    )

    logger = ctx.obj["logger"]
    try:
        generator = ConfigExampleGenerator(overrides=load_example_overrides())
        rendered = generator.render_yaml(
            include_workspace=include_workspace,
            comment_style=comment_style,
        )
        if output_path:
            with open(output_path, "w", encoding="utf-8") as handle:
                handle.write(rendered)
            logger.success(f"Config exemplar written to {output_path}")
            return
        click.echo(rendered, nl=False)
    except Exception as exc:
        logger.error(f"Failed to generate config exemplar: {exc}")
        ctx.abort()


@config.command("tree")
@click.option("--json", "as_json", is_flag=True, default=False, help="Print JSON for agents")
@click.pass_context
def config_tree(ctx: click.Context, as_json: bool) -> None:
    """Show schema-backed field tree for .metagit.yml (same model as web Config Studio)."""
    logger = ctx.obj["logger"]
    config_path = ctx.obj["config_path"]
    result = ConfigPatchService().build_tree("metagit", config_path)
    if isinstance(result, Exception):
        logger.error(f"Failed to build config tree: {result}")
        ctx.abort()
    emit_tree_result(result, as_json=as_json)


@config.command("preview")
@click.option(
    "--style",
    type=click.Choice(["normalized", "minimal", "disk"], case_sensitive=False),
    default="normalized",
    show_default=True,
    help="YAML preview style",
)
@click.option(
    "--file",
    "operations_file",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="JSON file with operations array or {operations, save}",
)
@click.option(
    "--op",
    type=click.Choice(["enable", "disable", "set", "append", "remove"]),
    default=None,
    help="Single operation kind (use with --path)",
)
@click.option("--path", default=None, help="Field path for a single operation")
@click.option("--value", default=None, help="Value for set (JSON or scalar)")
@click.option(
    "--output",
    "output_path",
    default=None,
    help="Write preview YAML to this path instead of stdout",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Print JSON for agents")
@click.pass_context
def config_preview(
    ctx: click.Context,
    style: str,
    operations_file: str | None,
    op: str | None,
    path: str | None,
    value: str | None,
    output_path: str | None,
    as_json: bool,
) -> None:
    """Preview .metagit.yml after applying draft operations (no save)."""
    logger = ctx.obj["logger"]
    config_path = ctx.obj["config_path"]
    operations = (
        resolve_operations(
            operations_file=operations_file,
            op=op,
            path=path,
            value=value,
        )
        if operations_file or op
        else []
    )
    result = ConfigPatchService().preview(
        "metagit",
        config_path,
        operations,
        style=style,
    )
    if isinstance(result, Exception):
        logger.error(f"Failed to preview config: {result}")
        ctx.abort()
    emit_preview_result(
        result,
        as_json=as_json,
        logger=logger,
        output_path=output_path,
    )


@config.command("patch")
@click.option(
    "--file",
    "operations_file",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="JSON file with operations array or {operations, save}",
)
@click.option(
    "--op",
    type=click.Choice(["enable", "disable", "set", "append", "remove"]),
    default=None,
    help="Single operation kind (use with --path)",
)
@click.option("--path", default=None, help="Field path for a single operation")
@click.option("--value", default=None, help="Value for set (JSON or scalar)")
@click.option(
    "--save",
    is_flag=True,
    default=False,
    help="Write changes to disk when validation passes",
)
@click.option(
    "--no-format",
    "no_format",
    is_flag=True,
    default=False,
    help="Skip schema-ordered YAML formatting when saving",
)
@click.option(
    "--tree",
    "include_tree",
    is_flag=True,
    default=False,
    help="Include updated schema tree in JSON output",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Print JSON for agents")
@click.pass_context
def config_patch(
    ctx: click.Context,
    operations_file: str | None,
    op: str | None,
    path: str | None,
    value: str | None,
    save: bool,
    no_format: bool,
    include_tree: bool,
    as_json: bool,
) -> None:
    """
    Apply schema operations to .metagit.yml (enable/disable/set/append/remove).

    Same operation model as the web Config Studio PATCH API. Example operations file:

    {"operations": [{"op": "set", "path": "name", "value": "my-workspace"}]}
    """
    logger = ctx.obj["logger"]
    config_path = ctx.obj["config_path"]
    operations = resolve_operations(
        operations_file=operations_file,
        op=op,
        path=path,
        value=value,
    )
    result = ConfigPatchService().patch(
        "metagit",
        config_path,
        operations,
        save=save,
        auto_format=not no_format,
        include_tree=include_tree or as_json,
    )
    if isinstance(result, Exception):
        logger.error(f"Failed to patch config: {result}")
        ctx.abort()
    emit_patch_result(result, as_json=as_json, logger=logger)


@config.group("graph")
@click.pass_context
def config_graph(ctx: click.Context) -> None:
    """Export workspace graph data for GitNexus / Cypher ingest."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@config_graph.command("export")
@click.option(
    "--workspace-root",
    default=None,
    help="Workspace root (default: appconfig workspace.path)",
)
@click.option(
    "--gitnexus-repo",
    default=None,
    help="Target GitNexus repo name for tool_calls (default: manifest name)",
)
@click.option(
    "--include-structure/--no-include-structure",
    default=True,
    help="Include project/repo nodes and contains edges",
)
@click.option(
    "--include-documentation/--no-include-documentation",
    default=False,
    help="Include documentation nodes and documents edges",
)
@click.option(
    "--manual-only",
    is_flag=True,
    default=False,
    help="Only export graph.relationships (still ensures endpoint nodes)",
)
@click.option(
    "--with-schema/--no-with-schema",
    default=True,
    help="Emit CREATE NODE/REL TABLE statements first",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["cypher", "json", "tool-calls"], case_sensitive=False),
    default="json",
    show_default=True,
    help="Output: full JSON bundle, tool-calls array, or raw Cypher lines",
)
@click.option("--output", "output_path", default=None, help="Write output to file")
@click.pass_context
def config_graph_export(
    ctx: click.Context,
    workspace_root: str | None,
    gitnexus_repo: str | None,
    include_structure: bool,
    include_documentation: bool,
    manual_only: bool,
    with_schema: bool,
    output_format: str,
    output_path: str | None,
) -> None:
    """
    Export manual graph.relationships as GitNexus-ingestible Cypher.

    Emits MERGE/CREATE statements for MetagitEntity / MetagitLink overlay tables and
    matching gitnexus_cypher MCP tool_calls. Run schema statements once per target index.
    """
    logger = ctx.obj["logger"]
    config_path = ctx.obj["config_path"]
    app_config = ctx.obj.get("config")
    if app_config is None:
        logger.error("App config missing from CLI context")
        ctx.abort()

    try:
        manager = MetagitConfigManager(config_path=config_path)
        loaded = manager.load_config()
        if isinstance(loaded, Exception):
            raise loaded
        root = workspace_root or str(Path(app_config.workspace.path).expanduser().resolve())
        result = GraphCypherExportService().export(
            loaded,
            root,
            gitnexus_repo=gitnexus_repo,
            include_structure=include_structure,
            include_documentation=include_documentation,
            manual_only=manual_only,
            with_schema=with_schema,
        )
    except Exception as exc:
        logger.error(f"Failed to export graph Cypher: {exc}")
        ctx.abort()

    if output_format == "cypher":
        lines = [*result.schema_statements, *result.statements]
        rendered = "\n".join(lines) + ("\n" if lines else "")
    elif output_format == "tool-calls":
        rendered = json.dumps(
            [item.model_dump(mode="json") for item in result.tool_calls],
            indent=2,
        )
    else:
        rendered = json.dumps(result.model_dump(mode="json"), indent=2)

    if output_path:
        Path(output_path).write_text(rendered, encoding="utf-8")
        logger.success(f"Graph Cypher export written to {output_path}")
        if result.warnings:
            for warning in result.warnings:
                logger.warning(warning)
        return

    click.echo(rendered, nl=rendered.endswith("\n"))
    if result.warnings:
        for warning in result.warnings:
            logger.warning(warning)


@config_graph.command("suggest")
@click.option(
    "--workspace-root",
    default=None,
    help="Workspace root (default: appconfig workspace.path)",
)
@click.option(
    "--dependency-type",
    "dependency_types",
    multiple=True,
    type=click.Choice(
        ["imports", "shared_config", "url_match", "declared", "ref"],
        case_sensitive=False,
    ),
    help="Inferred edge collectors to consider (repeatable). Default: imports, shared_config, url_match",
)
@click.option(
    "--depth",
    default=3,
    show_default=True,
    type=int,
    help="Project-hop depth when scanning dependencies",
)
@click.option(
    "--min-confidence",
    type=click.Choice(["high", "medium", "all"], case_sensitive=False),
    default="medium",
    show_default=True,
    help="Minimum confidence for candidates (high | medium | all)",
)
@click.option(
    "--include-declared",
    is_flag=True,
    default=False,
    help="Also consider declared/ref edges (usually low confidence)",
)
@click.option(
    "--candidate-id",
    "candidate_ids",
    multiple=True,
    help="Apply only these candidate ids (repeatable)",
)
@click.option(
    "--apply",
    "do_apply",
    is_flag=True,
    default=False,
    help="Patch graph.relationships on disk (default: suggest only)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="With --apply, build operations without saving",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Print JSON")
@click.option(
    "--output",
    "output_path",
    default=None,
    help="Write JSON result or operations file",
)
@click.pass_context
def config_graph_suggest(
    ctx: click.Context,
    workspace_root: str | None,
    dependency_types: tuple[str, ...],
    depth: int,
    min_confidence: str,
    include_declared: bool,
    candidate_ids: tuple[str, ...],
    do_apply: bool,
    dry_run: bool,
    as_json: bool,
    output_path: str | None,
) -> None:
    """
    Suggest graph.relationships entries from inferred cross-project dependencies.

    Returns candidates, diff against existing manual edges, and config patch operations.
    Use --apply to persist selected candidates (all by default, or --candidate-id).
    """
    logger = ctx.obj["logger"]
    config_path = ctx.obj["config_path"]
    app_config = ctx.obj.get("config")
    if app_config is None:
        logger.error("App config missing from CLI context")
        ctx.abort()

    try:
        manager = MetagitConfigManager(config_path=config_path)
        loaded = manager.load_config()
        if isinstance(loaded, Exception):
            raise loaded
        root = workspace_root or str(Path(app_config.workspace.path).expanduser().resolve())
        service = GraphRelationshipSuggestService()
        selected_types = list(dependency_types) if dependency_types else None
        selected_ids = list(candidate_ids) if candidate_ids else None
        if do_apply:
            result = service.suggest_and_apply(
                loaded,
                root,
                config_path,
                dependency_types=selected_types,
                depth=depth,
                min_confidence=min_confidence,
                include_declared=include_declared,
                candidate_ids=selected_ids,
                dry_run=dry_run,
                save=not dry_run,
            )
        else:
            result = service.suggest(
                loaded,
                root,
                dependency_types=selected_types,
                depth=depth,
                min_confidence=min_confidence,
                include_declared=include_declared,
                candidate_ids=selected_ids,
            )
    except Exception as exc:
        logger.error(f"Failed to suggest graph relationships: {exc}")
        ctx.abort()

    payload = result.model_dump(mode="json")
    rendered = json.dumps(payload, indent=2)

    if output_path:
        Path(output_path).write_text(rendered, encoding="utf-8")
        logger.success(f"Graph suggest result written to {output_path}")
    elif as_json:
        emit_json(payload)
    else:
        click.echo(rendered)

    if result.warnings:
        for warning in result.warnings:
            logger.warning(warning)
    if result.apply and result.apply.validation_errors:
        for item in result.apply.validation_errors:
            logger.error(str(item))


@config.command("schema")
@click.option(
    "--output-path",
    help="Path to output the JSON schema file",
    default="metagit_config.schema.json",
)
@click.pass_context
def config_schema(ctx: click.Context, output_path: str) -> None:
    """
    Generate a JSON schema for the MetagitConfig class and write it to a file.
    """
    from metagit.core.config.models import MetagitConfig
    from metagit.core.config.schema_generator import generate_json_schema

    logger = ctx.obj["logger"]
    try:
        schema = generate_json_schema(MetagitConfig)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2)
        logger.success(f"JSON schema written to {output_path}")
    except Exception as e:
        logger.error(f"Failed to generate JSON schema: {e}")
        ctx.abort()
