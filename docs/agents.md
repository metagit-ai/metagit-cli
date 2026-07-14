# Metagit for AI agents

Compact guide for agents told to install and use **Metagit** across Git repositories. Prefer these commands over reading full repo trees.

> PyPI package: **`metagit-cli`** (not `metagit`).

## Install

```bash
uv tool install metagit-cli
export METAGIT_AGENT_MODE=true   # non-interactive CLI (no fuzzy finder / prompts)
metagit version
metagit version check --json
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
| Search file contents (workspace) | `metagit workspace grep "<query>" --json` |
| Ripgrep / grep backend status | `metagit workspace grep info --json` |
| Workspace catalog | `metagit workspace list --json` |
| Validate manifest | `metagit config validate` |
| Safe sync (fetch-first) | `metagit project sync` |
| Scoped repo snapshot | `metagit context repomix --profile bugfix-local --project P --repo R` |
| Record objective | `echo '{"id":"…","status":"in_progress","title":"…","repos":[]}' \| metagit context objective set` |
| Update objective (merge) | `echo '{"id":"…","status":"in_progress","notes":"progress"}' \| metagit context objective set` — title/repos optional when id exists |
| Request approval (CLI) | `echo '{"action":"repo_sync","requested_by":"agent","payload":{}}' \| metagit context approval request` |
| List pending approvals | `metagit context approval list --json` |
| Installed vs latest release | `metagit version check --json` |
| Self-update (dry-run) | `metagit version upgrade --json` |
| Self-update (apply) | `metagit version upgrade --apply --json` |
| Agent profile (merged) | `metagit agent profile show -p P -n R --json` |
| Materialize agent posture | `metagit agent apply --vendor claude_code -p P -n R` |
| Campaign list / status | `metagit campaign list` / `metagit campaign status --slug <s>` |
| Campaign create / expand | `metagit campaign new …` / `metagit campaign expand --slug <s>` |
| Semantic ownership | `metagit semantic declare` · `metagit semantic owners` · `metagit semantic conflicts` |
| Merge orchestration | `metagit merge enqueue` · `metagit merge integrate` · `metagit merge status` |
| Agent scheduler | `metagit schedule next` · `metagit schedule status` · `metagit schedule policy show` |
| Agent OS (composition) | `metagit aos status` · `metagit aos doctor` · `metagit aos next` (`coord` alias) |
| Local Atlas | `metagit atlas init` · `metagit atlas generate` · `metagit atlas validate` · `metagit atlas query` |
| Derived surgical project | `metagit project derived create -n NAME --from P/R` · `refresh` · `include` · `exclude` |
| Skills surface (inventory) | `metagit skills surface --json` |

<!-- modality:agent_profile_apply -->
<!-- modality:native_campaigns -->
<!-- modality:objective_mr_approval_binding -->
<!-- modality:coordination_events_scope -->
<!-- modality:semantic_ownership -->
<!-- modality:merge_orchestrator -->
<!-- modality:agent_scheduler -->
<!-- modality:aos_status -->
<!-- modality:atlas_local -->
<!-- modality:derived_projects -->
<!-- modality:skills_surface -->

Set `--definition path/to/.metagit.yml` when not in the manifest repo root.

Agent profile and campaigns: [reference/agent-profile.md](reference/agent-profile.md), [reference/campaigns.md](reference/campaigns.md). Derived projects: [reference/derived-projects.md](reference/derived-projects.md). Skills surface: [reference/skills-surface.md](reference/skills-surface.md). Local repository Atlas: [reference/atlas.md](reference/atlas.md). Master index: [reference/modality-feature-registry.md](reference/modality-feature-registry.md).

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

Key MCP tools (when gate **ACTIVE**): `metagit_context_pack`, `metagit_session_begin`, `metagit_repo_search`, `metagit_workspace_search`, `metagit_workspace_grep_info`, `metagit_workspace_discover`, `metagit_workspace_health_check`, `metagit_workspace_sync`, `metagit_objective_list`, `metagit_approval_request`, `metagit_semantic_declare`, `metagit_semantic_query`, `metagit_semantic_owners`, `metagit_semantic_conflicts`, `metagit_semantic_ingest`.

**MCP resources (read-only, token-efficient):** `metagit://catalog` → `workspace/map` → `prompt/workspace/session-start?instructions=0` → `session/meta`; drill into `project/{name}/summary`, `repo/{p}/{r}/card`, `objectives`, `approvals/pending`, `session/digest/summary` when scoped. MCP **`prompts/list`** + **`prompts/get`** mirror prompt resources. Install skill `metagit-mcp-resources`. Spec: [reference/mcp-layered-resources-spec.md](reference/mcp-layered-resources-spec.md).

`metagit_version_check` and `metagit_version_upgrade` are available even when the workspace gate is inactive. Use `version check` (or `metagit_version_check`) to compare against the latest GitHub release and PyPI. Use `version upgrade` (or `metagit_version_upgrade` with `apply: true`) to run the detected package-manager upgrade (`uv tool upgrade metagit-cli` by default). Upgrades default to dry-run; pass `--apply` or `apply: true` explicitly.

Start MCP: `metagit mcp serve` (stdio). Install config: `metagit mcp install --scope user`.

### Shared coordination state (multi-agent)

Objectives, handoffs, approvals, and the events feed use the same backend as the CLI.
When several agents must share one queue, configure the **MCP server process** (not
just the IDE shell):

```bash
export METAGIT_STATE_URL=https://coordinator.example.com:8787
export METAGIT_STATE_TOKEN='…'
metagit mcp serve --root /path/to/manifest-root
```

Verify: `resources/read` → `metagit://gate/status` → `state_backend.backend` is `http`.

| MCP tool | Purpose |
|----------|---------|
| `metagit_objective_list` / `metagit_objective_upsert` / `metagit_objective_edit` | Objectives |
| `metagit_approval_request` / `metagit_approval_list` / `metagit_approval_resolve` | Approvals |
| `metagit_handoff_list` / `metagit_handoff_create` / `metagit_handoff_claim` / `metagit_handoff_complete` | Handoffs |
| `metagit_events` | Event poll (optional `since` ISO cursor) |

Resources: `metagit://objectives`, `approvals/pending`, `handoffs/open`, `events/recent?since=`.

Skill: **`metagit-sharing-state`**. Docs: [Sharing state across a team](reference/sharing-state.md).

## Workspace content grep (not manifest search)

Search **on-disk files** in managed repos. Always excludes `node_modules`, `.venv`, and similar scaffold paths.

| Goal | CLI | MCP | HTTP (`metagit api serve`) |
|------|-----|-----|----------------------------|
| Content search | `metagit workspace grep "QUERY" --json` | `metagit_workspace_search` | `GET /v2/workspace/grep?q=…` |
| Scoped to project | `--project NAME` | (filter via `repos` selectors) | `?project=NAME` |
| Scoped to repo | `--repo NAME` | `repos: ["project/repo"]` | `?repo=NAME` |
| Ripgrep status | `metagit workspace grep info --json` | `metagit_workspace_grep_info` | `GET /v2/workspace/grep/info` |
| List files by intent | — | `metagit_workspace_discover` | — |

Do **not** use `metagit search` for file contents — that command searches `.metagit.yml` metadata only.

Install skill: `metagit-workspace-grep` (see [Skills](skills.md)). Examples: `metagit workspace grep --help`.

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

- **Objectives** — `.metagit/sessions/objectives.json` (local default); CLI `metagit context objective …`
- **Approvals** — mutating ops queue; `metagit context approval …`
- **Handoffs** — `.metagit/sessions/handoffs.json`; CLI `metagit context handoff …`
- **Web UI** (local): `metagit web serve` → objectives/approvals at `/v3/ops/*`

### Handoffs and leases

<!-- modality:handoff_lease_heartbeat -->

```bash
metagit context handoff claim --id <id> --by agent-1 --ttl 30m
metagit context handoff heartbeat --id <id> --by agent-1 --ttl 30m
metagit context events --campaign <slug> --json
metagit context events --objective <id> --since "2026-07-06T00:00:00Z" --json
```

Expired claims auto-release when listing handoffs. Objectives may carry `mr_url` and `approval_id` for campaign rollups (`modality:objective_mr_approval_binding`).

### Agent Coordination Layer (ACL)

<!-- modality:acl_branch -->
<!-- modality:acl_lease -->
<!-- modality:acl_worktree -->
<!-- modality:acl_claim -->
<!-- modality:acl_manifest -->

For isolated agent checkouts, branch leases, and advisory file claims, see
[Agent coordination (ACL)](reference/agent-coordination.md) and skill
**`metagit-agent-coordination`**. ACL branch leases are
**distinct** from handoff claim TTL leases above.

```bash
metagit branch allocate --repository project/repo --agent-id agent-1 --task-id 412
metagit lease acquire --repository project/repo --agent-id agent-1 --task-id 412 --allocate
metagit worktree create --repository project/repo --agent-id agent-1 --task-id 412 --branch agent/412
metagit claim declare --repository project/repo --agent-id agent-1 --pattern 'src/*'
metagit context events --json   # includes source=acl lifecycle events
```

### Task Graph & Intent (RFC-0008)

<!-- modality:task_graph -->

Expand objectives into a DAG of executable nodes, compute ready sets, and store
optional ACL command hints. See [Task graph](reference/task-graph.md).

```bash
metagit task create --title "Ship auth" --goal "…" --json
metagit task expand --graph-id … --from-outline outline.txt
metagit task ready --json
metagit task complete --node-id …
metagit task bind-acl --node-id … --agent-id agent-1 --json
metagit context events --json   # includes source=taskgraph
```

### Context Compiler (RFC-0009)

<!-- modality:context_compile -->

Compile a budgeted context artifact for a project/repo (optionally bound to a
task node). See [Context compiler](reference/context-compiler.md).

```bash
metagit context compile --project P --repo R --tier 1 --budget 8000 --json
metagit context compile --project P --repo R --task-id NODE --graph-id G --json
```

### Semantic Ownership (RFC-0010)

Declare concept-level ownership for repository paths, resolve path owners, and
surface advisory claim hints without replacing Git or GitNexus. See
[Semantic ownership](reference/semantic-ownership.md).

```bash
metagit semantic declare --concept Authentication --repository project/repo --pattern 'src/auth/**' --json
metagit semantic owners --repository project/repo --path src/auth/token.py --json
metagit semantic conflicts --repository project/repo --json
metagit semantic ingest --json
```

### Sharing state across machines (remote backend)

When multiple agents or humans must see the **same** objectives, handoffs, and
approvals, configure a shared ops server instead of per-machine JSON files:

```bash
export METAGIT_STATE_URL=https://coordinator.example.com:8787
export METAGIT_STATE_TOKEN='…'
# CLI / MCP commands unchanged — stores use RemoteHttpBackend automatically
metagit context objective list --json
```

Run `metagit web serve` on the coordinator host; set the same `state.url` in app
config on every client. Repo clones remain local; only coordination documents are
centralized.

See [Sharing state across a team](reference/sharing-state.md) for architecture
diagram, HTTP contract (`ETag` / `If-Match`), and troubleshooting.

## What metagit is not

Not a Git client, SBOM tool, or full-repo packer. For whole-repo dumps use `metagit context repomix` with a profile, not raw `repomix` on the entire tree.

## More

- [Terminology](terminology.md) — workspace / project / repo
- [CLI reference](cli_reference.md)
- [Hermes multi-repo IaC](hermes-iac-workspace-guide.md)
- Site: <https://metagit-ai.github.io/metagit-cli/>
