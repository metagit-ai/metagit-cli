"""
Click utility functions
"""

import click


def call_click_command(cmd, *args, **kwargs):
    """Wrapper to call a click command

    :param cmd: click cli command function to call
    :param args: arguments to pass to the function
    :param kwargs: keywrod arguments to pass to the function
    :return: None
    """

    # Get positional arguments from args
    arg_values = {c.name: a for a, c in zip(args, cmd.params, strict=False)}
    args_needed = {c.name: c for c in cmd.params if c.name not in arg_values}

    # build and check opts list from kwargs
    opts = {a.name: a for a in cmd.params if isinstance(a, click.Option)}
    for name in kwargs:
        if name in opts:
            arg_values[name] = kwargs[name]
        else:
            if name in args_needed:
                arg_values[name] = kwargs[name]
                del args_needed[name]
            else:
                raise click.BadParameter("Unknown keyword argument '{}'".format(name))

    # check positional arguments list
    for arg in (a for a in cmd.params if isinstance(a, click.Argument)):
        if arg.name not in arg_values:
            raise click.BadParameter(
                "Missing required positionalparameter '{}'".format(arg.name)
            )

    # build parameter lists
    opts_list = sum([[o.opts[0], str(arg_values[n])] for n, o in opts.items()], [])
    args_list = [str(v) for n, v in arg_values.items() if n not in opts]

    # call the command
    cmd(opts_list + args_list)


def call_click_command_with_ctx(cmd, ctx, *args, **kwargs):
    """Wrapper to call a click command with a Context object

    :param cmd: click cli command function to call
    :param ctx: click context
    :param args: arguments to pass to the function
    :param kwargs: keyword arguments to pass to the function
    :return: None
    """

    # monkey patch make_context
    def make_context(*some_args, **some_kwargs):  # noqa: ARG001 ARG002
        child_ctx = click.Context(cmd, parent=ctx)
        with child_ctx.scope(cleanup=False):
            cmd.parse_args(child_ctx, list(args))
        return child_ctx

    cmd.make_context = make_context
    prev_make_context = cmd.make_context

    # call the command
    call_click_command(cmd, *args, **kwargs)

    # restore make_context
    cmd.make_context = prev_make_context
