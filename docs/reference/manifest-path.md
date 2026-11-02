# Manifest path

Commands that read `.metagit.yml` accept the same flag and environment variable:

```bash
metagit config validate -c .metagit.yml
metagit config validate --config .metagit.yml
METAGIT_CONFIG=.metagit.yml metagit config validate
```

`-c` / `--config` on a subcommand is the manifest. The top-level `metagit -c` flag is still the application config (`metagit.config.yaml`).

Older long options still work and print a deprecation notice on stderr:

| Old flag | Commands |
|----------|----------|
| `--config-path` | `config`, `repo`, `graph`, `record`, `detect` |
| `--definition` | worktree, branch, lease, claim, merge, schedule, aos, semantic, task, campaign, context, prompt, and the other workspace commands that took it |
| `--metagit-path` | `fmt` |

`--definition-id` is an Azure DevOps pipeline id and is unchanged.

An unknown command or option includes a `Did you mean` suggestion when a close name exists.
