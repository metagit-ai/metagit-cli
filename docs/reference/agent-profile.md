# Agent profile (`agent_profile`)

<!-- modality:agent_profile_apply -->

Structured, inheritable agent posture in `.metagit.yml` — skills, MCP servers, rules, and vendor targets **by id only** (never inline payloads). Materialize into repo clones with `metagit agent apply`.

Registry: [Modality feature registry](modality-feature-registry.md#feature-matrix).

## Schema

Optional `agent_profile` on **workspace**, **project**, and **repo** (`ProjectPath`):

```yaml
workspace:
  agent_profile:
    skills: [metagit-cli, metagit-context-pack]
    mcp: [metagit]
    rules: []
    vendors: [claude_code, cursor]
    tier: full
    inherit: true
  projects:
    - name: platform
      agent_profile:
        skills: [metagit-release-audit]
        inherit: true
      repos:
        - name: api
          agent_profile:
            tier: full
            skills: [metagit-workspace-scope]
            inherit: false
```

| Field | Purpose |
|-------|---------|
| `tier` | Label (e.g. `full`); wins over `tags.agent_tier` when set |
| `skills` | Bundled skill ids (`metagit skills list`) |
| `mcp` | MCP server ids (bundled catalog; `metagit` today) |
| `rules` | Bundled rule ids under `data/agent-rules/` when present |
| `vendors` | Limit apply to these runtimes; empty = all supported vendors |
| `inherit` | Merge parent scope (default `true`); `false` = verbatim profile |

**Inheritance:** workspace → project → repo. Child merges lists and overrides `tier`; `inherit: false` replaces the merged profile.

## CLI

| Command | Purpose |
|---------|---------|
| `metagit agent profile show -p <project> -n <repo>` | Merged effective profile (`--json`) |
| `metagit agent apply --vendor <v> [--project] [--repo] [--tag k=v]` | Install skills/MCP/rules into matching repo clones |
| `metagit agent apply --dry-run` | Plan without writes |
| `metagit config validate -c .metagit.yml` | Validates catalog ids for every declared profile |

```bash
metagit agent profile show -p platform -n api --json
metagit agent apply --vendor claude_code --project platform --repo api --dry-run
metagit agent apply --vendor cursor --tag agent_tier=full
```

Apply runs in each target **repo clone path** (workspace index), not the manifest root.

## Dispatch integration

<!-- modality:dispatch_profile_capabilities -->

`metagit agent dispatch-plan` JSON may include:

- `required_profile_skills` — from merged repo profile
- `missing_profile_skills` — bundled skills not yet assumed installed
- `profile_apply_command` — suggested `metagit agent apply …` when skills are required

See [Metagit agent](metagit-agent.md#dispatch-plan-overseer-handoff).

## Editing via config patch

```bash
metagit config patch -c .metagit.yml \
  --op set --path workspace.projects[0].repos[0].agent_profile.skills \
  --value '["metagit-cli"]' --save
metagit config validate -c .metagit.yml
```

## MCP / Web

CLI-only in v0.13.x. MCP `metagit_agent_dispatch_plan` includes profile capability hints; dedicated apply/profile MCP tools are future scope.

## Related skills

- `metagit-cli` — command cheat sheet
- `metagit-control-center` — apply before subagent dispatch when `profile_apply_command` is set
