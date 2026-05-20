---
name: metagit-cli
description: CLI-only shortcuts for metagit agents — workspace catalog, discovery, prompts, sync, layout, and config. Use instead of MCP or HTTP API when operating from a shell or agent_mode session.
---

# Metagit CLI (agent shortcuts)

Use this skill when an agent should drive metagit **only through the `metagit` command**. Do not call MCP tools or `metagit api` from workflows covered here unless the user explicitly asks.

Set non-interactive defaults when automating:

```bash
export METAGIT_AGENT_MODE=true
```

Global flags (most commands):

- `-c path/to/metagit.config.yaml` — app config (default `metagit.config.yaml`)
- Workspace manifest: `--definition` / `-c` on catalog commands (default `.metagit.yml`)

---

## Prompt commands (all kinds)

List built-in prompt kinds:

```bash
metagit prompt list
metagit prompt list --json
```

Emit prompts (`--text-only` for paste into agent context; `--json` for structured output; `--no-instructions` to omit manifest layers):

| Scope | Command | Default kind |
|-------|---------|--------------|
| Workspace | `metagit prompt workspace -c <definition> -k <kind>` | `instructions` |
| Project | `metagit prompt project -p <project> -c <definition> -k <kind>` | `instructions` |
| Repo | `metagit prompt repo -p <project> -n <repo> -c <definition> -k <kind>` | `instructions` |

### Prompt kinds by scope

| Kind | Workspace | Project | Repo | Purpose |
|------|:---------:|:-------:|:----:|---------|
| `instructions` | yes | yes | yes | Composed `agent_instructions` from manifest layers |
| `session-start` | yes | — | — | Session bootstrap checklist |
| `catalog-edit` | yes | yes | — | Search-before-create; catalog registration |
| `health-preflight` | yes | yes | — | Pre-work workspace/repo status pass |
| `sync-safe` | yes | yes | yes | Guarded sync rules |
| `subagent-handoff` | — | yes | yes | Delegate single-repo work |
| `layout-change` | yes | yes | yes | Rename/move dry-run workflow |
| `repo-enrich` | — | — | yes | **Discover + merge** workspace repo entry |

### Prompt shortcuts (copy-paste)

```bash
# Session bootstrap
metagit prompt workspace -k session-start --text-only -c .metagit.yml

# Composed instructions at each level
metagit prompt workspace -k instructions --text-only -c .metagit.yml
metagit prompt project -p default -k instructions --text-only -c .metagit.yml
metagit prompt repo -p default -n my-api -k instructions --text-only -c .metagit.yml

# Repo catalog enrichment (detect + merge manifest entry)
metagit prompt repo -p default -n my-api -k repo-enrich --text-only -c .metagit.yml

# Catalog registration discipline
metagit prompt workspace -k catalog-edit --text-only -c .metagit.yml

# Safe sync reminder
metagit prompt repo -p default -n my-api -k sync-safe --text-only -c .metagit.yml

# Subagent handoff
metagit prompt repo -p default -n my-api -k subagent-handoff --text-only -c .metagit.yml
```

---

## Repo enrich workflow (`repo-enrich`)

Run the prompt, then execute its steps:

```bash
metagit prompt repo -p <project> -n <repo> -k repo-enrich --text-only -c .metagit.yml
```

Typical discovery chain on the checkout:

```bash
cd "$(metagit search '<repo>' -c .metagit.yml --path-only)"
metagit detect repository -p . -o json
metagit detect repo -p . -o yaml
metagit detect repo_map -p . -o json
```

Provider metadata (dry-run):

```bash
metagit project source sync --provider github --org <org> --mode discover --no-apply
```

After merging fields into `workspace.projects[].repos[]`:

```bash
metagit config validate -c .metagit.yml
metagit workspace repo list --project <project> --json
```

---

## Workspace and catalog

```bash
metagit appconfig show --format json
metagit config info -c .metagit.yml
metagit config show -c .metagit.yml
metagit config validate -c .metagit.yml

metagit workspace list -c .metagit.yml --json
metagit workspace project list -c .metagit.yml --json
metagit workspace repo list -c .metagit.yml --json
metagit workspace repo list -c .metagit.yml --project <name> --json

metagit workspace project add --name <name> --json
metagit workspace repo add --project <name> --name <repo> --url <url> --json
metagit workspace project remove --name <name> --json
metagit workspace repo remove --project <name> --name <repo> --json
```

Search managed repos (always before creating entries):

```bash
metagit search "<query>" -c .metagit.yml --json
metagit search "<query>" -c .metagit.yml --path-only
metagit search "<query>" -c .metagit.yml --tag tier=1 --project <name>
```

---

## Project operations

```bash
metagit project list --config .metagit.yml --all --json
metagit project add --name <name> --json
metagit project remove --name <name> --json
metagit project rename --name <old> --new-name <new> --dry-run --json
metagit project select
metagit project sync

metagit project repo list --json
metagit project repo add --project <name> --name <repo> --url <url>
metagit project repo remove --name <repo> --json
metagit project repo rename --name <old> --new-name <new> --dry-run --json
metagit project repo move --name <repo> --to-project <other> --dry-run --json
metagit project repo prune --project <name> --dry-run

metagit project source sync --provider github --org <org> --mode discover --no-apply
metagit project source sync --provider github --org <org> --mode additive --apply
```

Layout (manifest + disk; always dry-run first):

```bash
metagit workspace project rename --name <old> --new-name <new> --dry-run --json
metagit workspace repo rename --project <p> --name <old> --new-name <new> --dry-run --json
metagit workspace repo move --project <p> --name <repo> --to-project <other> --dry-run --json
```

---

## Discovery and local metadata

```bash
metagit detect project -p <path> -o yaml
metagit detect repo -p <path> -o yaml
metagit detect repo_map -p <path> -o json
metagit detect repository -p <path> -o json
metagit detect repository -p <path> -o metagit
# --save only with operator approval (blocked in agent_mode)
```

Bootstrap new trees:

```bash
metagit init --kind application
metagit init --kind umbrella --template hermes-orchestrator
```

---

## Selection and scope

```bash
metagit workspace select --project <name>
metagit project select
metagit project repo select
```

---

## Config and appconfig

```bash
metagit appconfig validate
metagit appconfig get workspace.path
metagit config example
metagit config schema
metagit config providers
```

---

## Records, skills, version

```bash
metagit record search "<query>"
metagit skills list
metagit skills show metagit-cli
metagit skills install --skill metagit-cli
metagit version
metagit info
```

---

## Agent habits

1. **Search before create** — `metagit search` then catalog add.
2. **Validate after manifest edits** — `metagit config validate`.
3. **Emit prompts instead of rewriting playbooks** — `metagit prompt … --text-only`.
4. **Enrich stale repo entries** — `metagit prompt repo … -k repo-enrich` then detect + merge.
5. **Dry-run layout** — always `--dry-run --json` before apply.
6. **Prefer `METAGIT_AGENT_MODE=true`** in CI and agent loops to skip fuzzy finder and confirm dialogs.

## Related bundled skills

Use topic skills when you need deeper playbooks (some mention MCP): `metagit-projects`, `metagit-workspace-scope`, `metagit-workspace-sync`, `metagit-config-refresh`. This skill is the **CLI-only** index and prompt reference.
