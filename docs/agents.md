# Metagit for AI agents

Compact guide for agents told to install and use **Metagit** across Git repositories. Prefer these commands over reading full repo trees.

> PyPI package: **`metagit-cli`** (not `metagit`).

## Install

```bash
uv tool install metagit-cli
export METAGIT_AGENT_MODE=true   # non-interactive CLI (no fuzzy finder / prompts)
metagit version
```

Optional — install bundled playbooks into your agent host:

```bash
metagit skills list
metagit skills install --scope user --target openclaw   # or claude_code, hermes, …
metagit mcp install --scope user --target openclaw      # MCP server registration
```

## Session start (do this first)

Run from the **umbrella repo** that contains `.metagit.yml` (workspace manifest):

```bash
metagit context pack --tier 2 --json
metagit prompt workspace --kind session-start --text-only
```

| Tier | Command | Tokens (typical) | Contents |
|------|---------|------------------|----------|
| 0 | `context pack --tier 0` | ~100–400 | Workspace map: projects, repos, clone status |
| 1 | `context pack --tier 1` | +200–600/repo | Tier 0 + repo cards (git, stack hints, health) |
| 2 | `context pack --tier 2` | +digest | Tier 1 + changes since last session |

Escalate tiers only when needed. Use `--project` / `--repo` to narrow tier 1/2.

## Core CLI (agent mode)

| Goal | Command |
|------|---------|
| Find a managed repo | `metagit search "<query>" --json` |
| Workspace catalog | `metagit workspace list --json` |
| Validate manifest | `metagit config validate` |
| Safe sync (fetch-first) | `metagit project sync` |
| Scoped repo snapshot | `metagit context repomix --profile bugfix-local --project P --repo R` |
| Record objective | `echo '{"id":"…","status":"in_progress","title":"…","repos":[]}' \| metagit context objective set` |
| List pending approvals | `metagit context approval list --json` |

Set `--definition path/to/.metagit.yml` when not in the manifest repo root.

## Prompt kinds (`metagit prompt list`)

| Kind | Scope | Use when |
|------|-------|----------|
| `session-start` | workspace | Bootstrap checklist after context pack |
| `context-pack` | workspace, project, repo | Tier 0→2 escalation guidance |
| `sync-safe` | all | Before fetch/pull/clone |
| `catalog-edit` | workspace, project | Before adding projects/repos |
| `repo-enrich` | repo | Detect metadata into manifest |
| `subagent-handoff` | project, repo | Delegate single-repo work |

```bash
metagit prompt workspace --kind context-pack --text-only
metagit prompt project --kind sync-safe --project myproj --text-only
```

## MCP vs CLI

| Use CLI when | Use MCP when |
|--------------|--------------|
| Shell / subprocess agent | IDE host with MCP (Cursor, Claude Desktop, OpenClaw) |
| `METAGIT_AGENT_MODE=true` | Gate active (valid `.metagit.yml` in workspace) |

Key MCP tools (when gate **ACTIVE**): `metagit_context_pack`, `metagit_repo_search`, `metagit_workspace_health_check`, `metagit_workspace_sync`, `metagit_objective_list`, `metagit_approval_request`.

Start MCP: `metagit mcp serve` (stdio). Install config: `metagit mcp install --scope user`.

## Skills catalog

Install once; skills are short playbooks (when to use which command):

| Skill | Use when |
|-------|----------|
| `metagit-context-pack` | Tiered context packs, digest, objectives, approvals, repomix; Hermes session bootstrap |
| `metagit-cli` | All CLI-only workflows (this doc expanded) |
| `metagit-workspace-scope` | Session start, workspace boundaries |
| `metagit-control-center` | Ongoing multi-repo coordination |
| `metagit-workspace-sync` | Guarded sync |
| `metagit-upstream-scan` | Error may originate in another managed repo |
| `metagit-projects` | Before creating new project folders |
| `metagit-agent-access` | On-demand: optimize **any** repo for minimal-token agent onboarding |

Full table: [Skills](skills.md).

## Optimize a target repo (on demand)

Use the **`metagit-agent-access`** skill when a repository needs agent-friendly metadata without bloating human docs:

```bash
# Audit gaps (llms.txt, AGENTS.md, hidden README HTML comment)
skills/metagit-agent-access/scripts/optimize-agent-access.sh /path/to/repo --json

# Scaffold missing artifacts from templates
skills/metagit-agent-access/scripts/optimize-agent-access.sh /path/to/repo --apply --json
```

For large or unfamiliar repos, dispatch the subagent prompt in `skills/metagit-agent-access/subagent-prompt.md` (returns JSON summary only — no full file dumps in chat).

Hidden marker convention in README:

```html
<!-- agent-access:start
install: ...
session_start: ...
refs: llms.txt, AGENTS.md
agent-access:end -->
```

## Single-repo first run

Inside any Git repo without a manifest:

```bash
metagit init          # safe to re-run when .metagit.yml already exists and is valid
metagit config validate
```

Re-running `init` on a valid manifest exits 0 with “Already initialized” and does not overwrite. Use `--force` only when you intend to replace the file (blocked in agent mode without removing it first).

Catalog adds support **`--ensure`** (auto-enabled in agent mode): re-run succeeds with `operation: noop` when the project/repo already exists with matching url/path. MCP/API default `ensure: true`.

## Human ↔ agent shared state

- **Objectives** — `.metagit/sessions/objectives.json`; CLI `metagit context objective …`
- **Approvals** — mutating ops queue; `metagit context approval …`
- **Web UI** (local): `metagit web serve` → objectives/approvals at `/v3/ops/*`

## What metagit is not

Not a Git client, SBOM tool, or full-repo packer. For whole-repo dumps use `metagit context repomix` with a profile, not raw `repomix` on the entire tree.

## More

- [Terminology](terminology.md) — workspace / project / repo
- [CLI reference](cli_reference.md)
- [Hermes multi-repo IaC](hermes-iac-workspace-guide.md)
- Site: <https://metagit-ai.github.io/metagit-cli/>
