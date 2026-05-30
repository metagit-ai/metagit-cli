# Hermes orchestrator workspace

Use this guide when a **Hermes** controller agent should act as the DevOps and project-management
entrypoint for a portfolio of repositories and local publish paths. Metagit holds the manifest;
Hermes holds the objective across projects.

For Terraform-heavy estates, also read [Hermes & org IaC guide](hermes-iac-workspace-guide.md).

## Quick start

1. Create or choose an umbrella coordinator repository.
2. Initialize from the bundled template (interactive prompts or an answers file):

```bash
metagit init --list-templates
metagit init ./hermes-control-plane --create --template hermes-orchestrator
# non-interactive:
metagit init --target ./hermes-control-plane --create --template hermes-orchestrator \
  --answers-file examples/hermes-orchestrator/answers.example.yml \
  --no-prompt
```

   Or copy [examples/hermes-orchestrator/.metagit.yml](https://github.com/metagit-ai/metagit-cli/blob/main/examples/hermes-orchestrator/.metagit.yml)
   manually and adjust projects, repos, and instructions.

3. Enable workspace dedupe in app config when the same URL appears in multiple projects:

```yaml
config:
  workspace:
    path: ./.metagit
    dedupe:
      enabled: true
      scope: workspace
```

4. Validate and sync:

```bash
metagit config validate
metagit project sync --project portfolio
metagit project sync --project local
```

5. Serve MCP for Hermes:

```bash
metagit mcp serve --root /path/to/coordinator
```

## Hermes session bootstrap

Wire metagit into every Hermes objective **before the first tool call**. Inject output into
system context, a pre-turn shell hook, or the opening user message.

```bash
export METAGIT_AGENT_MODE=true
metagit context pack --tier 2 --json -c .metagit.yml
metagit prompt workspace -k session-start --text-only -c .metagit.yml
metagit prompt workspace -k context-pack --text-only -c .metagit.yml   # optional tier guide
```

| Trigger | Command |
|---------|---------|
| Session / objective open | Tier 2 pack + `session-start` prompt |
| Token-tight open | Tier 0 pack + `session-start` prompt |
| Subagent to one repo | Tier 1 pack with `--project`/`--repo` + `subagent-handoff` prompt |
| MCP-connected Hermes | `metagit_context_pack` tier 2 instead of CLI pack |

Full playbook: bundled **`metagit-context-pack`** skill. Install with
`metagit skills install --skill metagit-context-pack --target hermes`.

## Multi-instance workspaces (Syncthing)

When multiple machines share a coordinator repo via Syncthing:

- Designate **one agent** as manifest writer for `.metagit.yml` catalog edits.
- Only the session-owning agent runs `metagit context pack --tier 2` (updates session boundary).
- After sync idle: `metagit config validate` then tier 0/1 pack before trusting scope.
- Run `metagit project sync` locally on each machine — clones are not synced by Syncthing.

See **`metagit-context-pack`** for conflict zones and stale-sync detection.

## Projects in the example manifest

| Project | Purpose |
|---------|---------|
| `portfolio` | Git-backed services and applications |
| `local` | Non-git `path` repos for static sites and local publish workflows |
| `platform` | Optional IaC / shared infra (empty until you add repos) |

The `local` project is the pattern for “publish a folder on disk” without a remote. Each entry
uses `path` + `sync: true`; metagit symlinks into `workspace.path` (or a canonical store when
dedupe is enabled).

## Controller responsibilities

The root `agent_instructions` in the example manifest define the controller loop:

- Orient with workspace status and health.
- Search before creating directories or clones.
- Register work in `.metagit.yml` and validate.
- Switch project context; delegate single-repo work to subagents.
- Sync conservatively (fetch by default).
- Keep descriptions and per-repo instructions accurate.

## Template apply

To copy helper files into an existing synced project folder:

```bash
metagit mcp serve --root /path/to/coordinator
# Tool: metagit_project_template_apply
#   template: hermes-orchestrator
#   target_projects: ["portfolio"]
#   dry_run: true
```

Or use the MCP tool from your agent host with `confirm_apply` when ready.

## Related docs

- [Hermes & org IaC guide](hermes-iac-workspace-guide.md) — Terraform / module rollout patterns
- [Configuration exemplar](reference/metagit-config.md) — full `.metagit.yml` field reference sample
- [Skills](skills.md) — `metagit-projects`, `metagit-control-center`, workspace sync skills
