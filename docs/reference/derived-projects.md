# Derived projects

<!-- modality:derived_projects -->

Create a **derived** workspace project inside the same umbrella `.metagit.yml`: a frozen surgical subset of repos from other projects, with separate sync mounts and refreshable identity.

## Why

Agents often need a temporary working set across repos owned by different umbrella projects without duplicating the whole catalog or standing up a second workspace. Derived projects keep the parent manifest as the source of truth while giving a named, syncable subset.

## Behavior

| Concern | Rule |
|---------|------|
| Placement | Same umbrella `.metagit.yml` (`workspace.projects[]`) |
| Membership | Frozen at create; change only via `include` / `exclude` |
| Identity | `url` / `path` / `ref` / source_* / overlapping tags refresh from `derived_from` |
| Sync | `metagit project sync --project <derived>` → `{sync}/{derived}/{repo}` |
| Dedupe | Create enables per-project `dedupe.enabled` by default so mounts can share `_canonical` |

## Schema

```yaml
workspace:
  projects:
    - name: surgical
      derived:
        enabled: true
        sources:
          - project: portfolio
            repos: [api]
      dedupe:
        enabled: true
      repos:
        - name: api
          url: https://github.com/example/api.git
          derived_from:
            project: portfolio
            repo: api
```

## CLI

```bash
metagit project derived create -n surgical \
  --from portfolio/api --from local/notes \
  --description "Agent working set"

metagit project -p surgical derived refresh
metagit project -p surgical derived include --from portfolio/web
metagit project -p surgical derived exclude --repo notes
metagit project -p surgical sync
```

## MCP

- `metagit_project_derived_create` — `name`, `selections[]`, optional description / `enable_dedupe`
- `metagit_project_derived_refresh` — `project_name`, optional `repos[]`
- `metagit_project_derived_include` — `project_name`, `selection` (`project/repo`)
- `metagit_project_derived_exclude` — `project_name`, `repo_name`

## Agent workflow

1. Context pack / search the umbrella SoT
2. `metagit project derived create … --from project/repo …`
3. Optional project-level `agent_profile` vs per-repo profiles
4. `metagit project sync --project <derived>`
5. Use ACL worktrees on those mounts for concurrent agents
6. `metagit skills surface -p <derived>` to see skill paths for the working set

## Related

- [Agent profile](agent-profile.md) — declared skills/MCP per scope
- [Skills surface](skills-surface.md) — on-disk + declared inventory
- Example: `examples/derived-workspace/.metagit.yml`
