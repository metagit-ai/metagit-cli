---
name: metagit-cli
description: CLI-only shortcuts for metagit agents — workspace catalog, discovery, prompts, sync, layout, and config. Use instead of MCP or HTTP API when operating from a shell or agent_mode session.
metadata:
  internal: true
---
# Metagit CLI (agent shortcuts)

Use this skill when an agent should drive metagit **only through the `metagit` command**. Do not call MCP tools or `metagit api` from workflows covered here unless the user explicitly asks.

Set non-interactive defaults when automating:

```bash
export METAGIT_AGENT_MODE=true
```

**Session start** (from umbrella repo with `.metagit.yml`):

```bash
metagit context pack --tier 2 --json
metagit prompt workspace -k session-start --text-only -c .metagit.yml
```

Repo-root agent docs: [AGENTS.md](https://github.com/metagit-ai/metagit-cli/blob/main/AGENTS.md) · [llms.txt](https://github.com/metagit-ai/metagit-cli/blob/main/llms.txt) · [docs/agents.md](https://metagit-ai.github.io/metagit-cli/agents/).

Global flags (most commands):

- `-c path/to/metagit.config.yaml` — app config (default `metagit.config.yaml`)
- Workspace manifest: `--definition` / `-c` on catalog commands (default `.metagit.yml`)

---

## Manifest editing fast map (`.metagit.yml`)

Use this table first when changing a workspace manifest from the CLI. Prefer **catalog commands** for projects/repos; use **`config patch`** for everything else in the schema (documentation, graph, dedupe overrides, nested fields).

| Task | Command |
|------|---------|
| **Inspect** manifest on disk | `metagit config show -c .metagit.yml` |
| **Inspect** normalized model | `metagit config show -c .metagit.yml --normalized` |
| **Inspect** as JSON (agents) | `metagit config show -c .metagit.yml --json` |
| **Browse** fields / paths | `metagit config tree -c .metagit.yml` or `… --json` |
| **Validate** after edits | `metagit config validate -c .metagit.yml` |
| **Dry-run** schema change | `metagit config preview -c .metagit.yml --file ops.json` |
| **Apply** schema change | `metagit config patch -c .metagit.yml --file ops.json --save` |
| **Set one field** | `metagit config patch -c .metagit.yml --op set --path <path> --value <v> --save` |
| **Enable** optional block | `metagit config patch … --op enable --path <path> --save` |
| **Add list item** | `metagit config patch … --op append --path <list.path> --save` then `set` on `[index].field` |
| **Remove list item** | `metagit config patch … --op remove --path <list.path>[index] --save` |

### Catalog shortcuts (projects & repos)

| Task | Command |
|------|---------|
| List projects | `metagit workspace project list -c .metagit.yml --json` |
| List repos (all / one project) | `metagit workspace repo list -c .metagit.yml --json` / `… --project <p> --json` |
| Add project | `metagit workspace project add -c .metagit.yml --name <p> --json` |
| Remove project | `metagit workspace project remove -c .metagit.yml --name <p> --json` |
| Rename project (dry-run) | `metagit workspace project rename -c .metagit.yml --name <old> --new-name <new> --dry-run --json` |
| Add repo | `metagit workspace repo add -c .metagit.yml --project <p> --name <r> --url <url> --json` |
| Remove repo (manifest only) | `metagit workspace repo remove -c .metagit.yml --project <p> --name <r> --json` |
| Rename / move repo (dry-run) | `metagit workspace repo rename …` / `metagit workspace repo move … --dry-run --json` |
| Search before adding | `metagit search "<name>" -c .metagit.yml --json` |

Active project context (optional): `metagit project repo add --name <r> --url <url>` after `metagit project select`.

### Schema patch examples (`ops.json`)

Paths use dot/bracket notation (same as web Config Studio). `--value` accepts JSON for objects.

```json
{
  "operations": [
    { "op": "set", "path": "name", "value": "my-workspace" },
    { "op": "enable", "path": "documentation" },
    { "op": "append", "path": "documentation" },
    { "op": "set", "path": "documentation[0]", "value": { "kind": "markdown", "path": "AGENTS.md" } },
    { "op": "enable", "path": "graph" },
    { "op": "append", "path": "graph.relationships" },
    {
      "op": "set",
      "path": "graph.relationships[0]",
      "value": {
        "id": "api-depends-infra",
        "from": { "project": "platform", "repo": "api" },
        "to": { "project": "infra", "repo": "terraform" },
        "type": "depends_on"
      }
    },
    { "op": "set", "path": "workspace.projects[0].dedupe.enabled", "value": false }
  ]
}
```

```bash
metagit config preview -c .metagit.yml --file ops.json
metagit config patch -c .metagit.yml --file ops.json --save
metagit config validate -c .metagit.yml
```

### App config vs manifest

| File | Scope | Edit via |
|------|-------|----------|
| `.metagit.yml` | Workspace manifest (projects, repos, docs, graph) | `metagit config …` + `metagit workspace …` |
| `metagit.config.yaml` | Tooling (paths, dedupe default, providers, profiles) | `metagit appconfig …` |

```bash
metagit appconfig show --format minimal-yaml
metagit appconfig patch --op set --path workspace.dedupe.enabled --value false --save
metagit config providers --show
```

### After every manifest edit

1. `metagit config validate -c .metagit.yml`
2. `metagit workspace list -c .metagit.yml --json` (sanity-check catalog)
3. If repos changed on disk: `metagit project sync` or `metagit project sync --hydrate`

### Graph relationships (suggest, apply, export)

| Task | Command |
|------|---------|
| First-time graph discovery (report only) | `metagit prompt workspace -k graph-discover -c .metagit.yml --text-only` |
| Suggest candidates from inferred deps | `metagit config graph suggest -c .metagit.yml --json` |
| Apply suggestions to manifest | `metagit config graph suggest -c .metagit.yml --apply` |
| Agent playbook (apply + ingest) | `metagit prompt workspace -k graph-maintain -c .metagit.yml --text-only` |
| MCP suggest / apply | `metagit_suggest_graph_relationships` / `metagit_apply_graph_relationships` |
| Full export bundle (JSON) | `metagit config graph export -c .metagit.yml --json` |
| MCP tool_calls only | `metagit config graph export -c .metagit.yml --format tool-calls` |
| Ingest overlay into GitNexus | `./skills/metagit-gitnexus/scripts/ingest-workspace-graph.sh -c .metagit.yml` |

See bundled `metagit-graph-maintain` skill for the full promote → validate → ingest loop. Overlay tables: `MetagitEntity`, `MetagitLink`.

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

Per-project dedupe override in `.metagit.yml` (overrides `workspace.dedupe.enabled` in `metagit.config.yaml` for that project only):

```yaml
workspace:
  projects:
    - name: local
      dedupe:
        enabled: false
      repos: []
```

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
metagit project sync --hydrate   # symlink mounts → full directory copies (per-file progress)

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

## Config and appconfig (reference)

See **Manifest editing fast map** above for day-to-day manifest work. Additional commands:

```bash
metagit config info -c .metagit.yml
metagit config example
metagit config schema
metagit appconfig validate
metagit appconfig get --name config.workspace.path
metagit appconfig tree --json
metagit appconfig preview --file ops.json
metagit appconfig patch --file ops.json --save
metagit config providers --show
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

Use topic skills when you need deeper playbooks (some mention MCP): `metagit-context-pack` (tiered packs, digest, objectives, approvals, repomix), `metagit-projects`, `metagit-workspace-scope`, `metagit-workspace-sync`, `metagit-config-refresh`. This skill is the **CLI-only** index and prompt reference.
