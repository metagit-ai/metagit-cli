# Skills surface

<!-- modality:skills_surface -->

Inventory **on-disk** agent skills and **declared** `agent_profile.skills` across workspace, project, and repo scopes so agents can see which skill paths apply to an umbrella vs a surgical derived project.

## Why

Umbrella projects and individual repos often ship different skills (`.cursor/skills`, `.claude/skills`, `.agents/skills`, …). Declared `agent_profile` layers add another set. This surface merges both into a ladder for onboarding and derived working sets.

Phase 2 (not implemented): stack-based **suggest** into `agent_profile` (autoskills-inspired UX; no vendored third-party registry).

## CLI

```bash
metagit skills surface --json
metagit skills surface -p surgical
metagit skills surface -p portfolio -r api --json
```

## MCP

`metagit_skills_surface` — optional `project_name`, `repo_name`.

## Entry shape

| Field | Meaning |
|-------|---------|
| `skill_id` | Directory / catalog id |
| `scope` | `workspace` \| `project` \| `repo` |
| `source` | `on_disk` \| `declared` \| `both` |
| `path` | On-disk skill directory when present |
| `vendor` | Detected vendor root (cursor, claude_code, …) |
| `project` / `repo` | Set for project/repo scopes |

## Related

- [Agent profile](agent-profile.md)
- [Derived projects](derived-projects.md)
- [Skills install](../skills.md)
