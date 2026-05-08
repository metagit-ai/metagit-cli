---
name: metagit-upstream-discovery
description: Use when a coding agent encounters likely upstream blockers and must find related workspace repositories, files, and probable root causes.
---

# Metagit Upstream Discovery Skill

Use this skill when the current repo does not appear to contain the full fix and related repositories may hold the source issue.

## Supported Use Cases

- Missing Terraform input in a shared module
- Docker base image/version mismatch across repos
- Shared infrastructure definitions causing local failures
- CI pipeline breakages tied to upstream templates/workflows

## Local Script Wrapper (Use First)

Use this token-efficient wrapper for upstream discovery tasks:
- `./scripts/upstream-scan.zsh [root_path] "<query>" [preset] [max_results]`

Output format:
- compact status line
- top ranked repo hints (`hint`)
- top search file hits (`hit`)

## Workflow

1. Read workspace repository map from active `.metagit.yml`.
2. Run `metagit_workspace_index` to verify repo availability and sync state.
3. Use `metagit_workspace_search` with category preset (`terraform`, `docker`, `infra`, `ci`).
4. Use `metagit_upstream_hints` to rank candidate repositories and files.
5. Return a concise action plan:
   - top candidate repos
   - likely files/definitions
   - whether sync is needed before deeper analysis

## Search Strategy

- Start narrow with issue-specific terms (error, module, variable, image tag).
- Expand to broader shared terms if no hits.
- Prefer repositories referenced by workspace metadata before searching unknown repos.

## Output Contract

Return:
- ranked candidates with rationale
- suggested next file openings
- confidence level and unresolved assumptions

## Safety Rules

- Restrict search to configured workspace repositories.
- Cap result size and duration.
- Keep this workflow read-only unless an explicit sync action is requested.
