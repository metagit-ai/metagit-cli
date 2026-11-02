#!/usr/bin/env python
"""One manifest path flag: ``-c`` / ``--config`` and ``METAGIT_CONFIG``."""

from __future__ import annotations

import difflib
import os

import click

_MANIFEST_LONG_OPTS = frozenset({"--definition", "--config-path", "--metagit-path", "--config"})
_ENV = "METAGIT_CONFIG"


class LazyManifestGroup(click.Group):
    """Remember child arguments before Click clears them for the group callback."""

    def invoke(self, ctx: click.Context) -> object:
        ctx.meta["metagit_pending_args"] = [*ctx._protected_args, *ctx.args]
        return super().invoke(ctx)


def pending_args(ctx: click.Context) -> list[str]:
    """Return arguments Click has not parsed yet, without the subcommand name."""
    saved = ctx.meta.get("metagit_pending_args")
    protected = list(saved) if isinstance(saved, list) else [*ctx._protected_args, *ctx.args]
    if ctx.invoked_subcommand and protected and protected[0] == ctx.invoked_subcommand:
        protected = protected[1:]
    return protected


def help_in_pending_args(ctx: click.Context) -> bool:
    """True when a later token asks for help, before this group loads a manifest."""
    return any(arg in {"-h", "--help"} for arg in pending_args(ctx))


def manifest_path_from_pending_args(ctx: click.Context) -> str | None:
    """Return the last ``-c`` / ``--config`` still waiting on a child command."""
    args = pending_args(ctx)
    found: str | None = None
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in {"-c", "--config"} and index + 1 < len(args):
            found = args[index + 1]
            index += 2
            continue
        if arg.startswith("--config="):
            found = arg.split("=", 1)[1]
        index += 1
    return found


def install_manifest_flags(root: click.Group) -> None:
    """Normalize manifest path options and add did-you-mean errors.

    The root ``-c`` stays the application config. Every other command that
    already reads a manifest path accepts ``-c`` / ``--config`` and
    ``METAGIT_CONFIG``. The previous long options remain as hidden aliases.
    """
    _install_command_suggestions(root)
    _visit(root, is_root=True, inherit_config=False)


def _visit(command: click.Command, *, is_root: bool, inherit_config: bool) -> None:
    if getattr(command, "_metagit_manifest_flags", False):
        return
    command._metagit_manifest_flags = True  # type: ignore[attr-defined]
    _install_option_suggestions(command)
    if not is_root:
        found = _normalize_manifest_options(command)
        if inherit_config and not found and not _has_short_c(command):
            _add_context_config_option(command)
    if isinstance(command, click.Group):
        child_inherit = inherit_config or command.name in {"config", "project"}
        for child in list(command.commands.values()):
            _visit(child, is_root=False, inherit_config=child_inherit)


def _is_manifest_option(param: click.Parameter) -> bool:
    if not isinstance(param, click.Option) or param.multiple or param.is_flag:
        return False
    longs = {opt for opt in param.opts if opt.startswith("--")}
    if "--definition-id" in longs or "--appconfig-path" in longs:
        return False
    return bool(longs & _MANIFEST_LONG_OPTS)


def _has_short_c(command: click.Command) -> bool:
    return any(isinstance(param, click.Option) and "-c" in param.opts for param in command.params)


def _normalize_manifest_options(command: click.Command) -> bool:
    found = False
    for index, param in enumerate(list(command.params)):
        if not _is_manifest_option(param):
            continue
        found = True
        longs = [opt for opt in param.opts if opt.startswith("--") and opt not in {"--config"}]
        if "-c" in param.opts and "--config" in param.opts:
            param.envvar = _ENV
            continue
        replacement = click.Option(
            ["-c", "--config", param.name],
            default=param.default,
            show_default=bool(param.show_default),
            required=param.required,
            help=param.help or "Path to the metagit manifest",
            envvar=_ENV,
            type=param.type,
            callback=param.callback,
        )
        command.params[index] = replacement
        for alias in longs:
            _add_deprecated_alias(command, replacement, alias)
    return found


def _add_deprecated_alias(command: click.Command, primary: click.Option, alias: str) -> None:
    def callback(ctx: click.Context, param: click.Parameter, value: object) -> None:
        if ctx.get_parameter_source(param.name) != click.core.ParameterSource.COMMANDLINE:
            return None
        message = f"warning: {alias} is deprecated; use -c/--config\n"
        os.write(2, message.encode())
        if ctx.get_parameter_source(primary.name) == click.core.ParameterSource.COMMANDLINE:
            return None
        ctx.params[primary.name] = value
        return None

    command.params.append(
        click.Option(
            [alias],
            expose_value=False,
            hidden=True,
            callback=callback,
            help=f"Deprecated alias for -c/--config ({alias})",
        )
    )


def _add_context_config_option(command: click.Command) -> None:
    """Accept ``-c`` on a config subcommand that reads ``ctx.obj['config_path']``."""

    def callback(ctx: click.Context, param: click.Parameter, value: object) -> None:
        source = ctx.get_parameter_source(param.name)
        if source not in {click.core.ParameterSource.COMMANDLINE, click.core.ParameterSource.ENVIRONMENT}:
            return None
        if value:
            ctx.ensure_object(dict)
            ctx.obj["config_path"] = value
        return None

    command.params.append(
        click.Option(
            ["-c", "--config", "manifest_config"],
            expose_value=False,
            default=None,
            envvar=_ENV,
            help="Path to the metagit manifest",
            callback=callback,
        )
    )


def _install_command_suggestions(root: click.Group) -> None:
    def walk(command: click.Command) -> None:
        if not isinstance(command, click.Group) or getattr(command, "_metagit_suggest", False):
            return
        command._metagit_suggest = True  # type: ignore[attr-defined]
        original = command.get_command

        def get_command(ctx: click.Context, cmd_name: str) -> click.Command | None:
            found = original(ctx, cmd_name)
            if found is not None or not cmd_name:
                return found
            matches = difflib.get_close_matches(cmd_name, list(command.commands), n=3, cutoff=0.6)
            if not matches:
                return None
            raise click.UsageError(f"No such command {cmd_name!r}. Did you mean: {', '.join(matches)}?")

        command.get_command = get_command  # type: ignore[method-assign]
        for child in command.commands.values():
            walk(child)

    walk(root)


def _install_option_suggestions(command: click.Command) -> None:
    if getattr(command, "_metagit_option_suggest", False):
        return
    command._metagit_option_suggest = True  # type: ignore[attr-defined]
    original = command.parse_args

    def parse_args(ctx: click.Context, args: list[str]) -> list[str]:
        try:
            return original(ctx, args)
        except click.NoSuchOption as exc:
            names: list[str] = []
            for param in command.params:
                names.extend(getattr(param, "opts", []))
            matches = difflib.get_close_matches(exc.option_name, names, n=3, cutoff=0.55)
            if not matches:
                raise
            raise click.UsageError(f"No such option {exc.option_name!r}. Did you mean: {', '.join(matches)}?") from exc

    command.parse_args = parse_args  # type: ignore[method-assign]
