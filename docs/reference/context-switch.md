# Context switch

<!-- modality:context_switch -->

Single entry point for mid-session agent bootstrap into a workspace project (optional repo). Composes the lean `ProjectContextService` switch with a scoped context pack, prompt, and objective.

## CLI

```bash
# Shell-evalable exports on stdout; pack JSON + prompt on stderr
eval "$(metagit context switch attune)"
eval "$(metagit context switch attune attune)"

# Structured envelope
metagit context switch attune --json
metagit context switch attune attune --tier 1 --json

# Opt out of bootstrap pieces
metagit context switch attune --no-pack --no-prompt --no-objective --json
```

| Flag | Default | Meaning |
|------|---------|---------|
| `--tier` | `2` | Pack tier when packing |
| `--no-pack` / `--no-prompt` / `--no-objective` | off | Skip that bootstrap piece |
| `--prompt-kind` | `context-switch` | Or `session-start` |
| `--json` | off | Full `ContextSwitchResult` on stdout |

Default stdout is only `export KEY=value` lines (safe for `eval`). Pack and prompt go to stderr.

## Objective pause/resume ergonomics

<!-- modality:context_resume_status_tracking -->

Use these commands to capture quick handoff notes and resume the right objective with minimal typing:

```bash
metagit context pause --title "Paused for handoff" --repo demo/svc --left-off "completed parser" --next "wire CLI"
metagit context resume --format detailed
metagit context resume "demo/svc" --json
```

Resume scoring is deterministic:

1. Prefer objectives with `status=in_progress`.
2. Break ties by latest `updated_at`, then `created_at`, then id.
3. Optional filter matches id, title, repos, human notes, and agent notes.

For status/note updates without full JSON payload replacement:

```bash
metagit context objective set --id obj-123 --status in_progress --left-off "tests green" --next "open PR" --blockers "none" --human-notes "handoff"
metagit context objective edit --id obj-123 --field human_notes --value "Waiting on review"
metagit context objective edit --id obj-123 --field status --value done
```

MCP parity: `metagit_context_resume` returns the same selected objective JSON as CLI `context resume --json`.

Helper script example: [examples/resume-project.sh](https://github.com/metagit-ai/metagit-cli/blob/main/examples/resume-project.sh)

## Prompt

```bash
metagit prompt workspace -k context-switch --text-only
```

Cold session open still uses `session-start`. Mid-session switches use `context-switch`.

## MCP

- **`metagit_context_switch`** — full bootstrap (pack + prompt + objective + env). Args: `project_name` (required), `repo_name`, `tier`, `include_pack`, `include_prompt`, `include_objective`, `prompt_kind`.
- **`metagit_project_context_switch`** — lean switch only (unchanged).

## Env exports

From lean switch:

- `METAGIT_WORKSPACE_ROOT`
- `METAGIT_PROJECT`
- `METAGIT_PROJECT_REPOS`
- safe manifest `variables[]`

Bootstrap additions:

- `METAGIT_AGENT_MODE=true`
- Tag-derived keys (below)
- `METAGIT_WORKING_DIR` from tag or suggested cwd / first repo path

## Tag conventions

Project or repo `tags` (repo wins when a primary repo is selected):

| Tag | Env |
|-----|-----|
| `hermes_profile` | `METAGIT_HERMES_PROFILE` |
| `working_dir` | `METAGIT_WORKING_DIR` |
| `default_task_namespace` | `METAGIT_DEFAULT_TASK_NAMESPACE` |

These are documentation conventions only — not a hard schema break.

## Related

- Design: `docs/superpowers/specs/2026-08-03-context-switch-design.md`
- Human nav shortcut: `metagit nav` / `navigate` (separate feature)
- Lean MCP project context: `docs` / skill guidance for `metagit_project_context_switch`
