---
name: metagit-agent-access
description: >-
  Optimize any repository for minimal-token agent onboarding — llms.txt, AGENTS.md,
  hidden HTML agent blocks, docs/agents.md. Use when asked to improve agentic access,
  agent metadata, llms.txt, or run the agent-access optimizer subagent on a project.
---

# Metagit agent access optimizer

On-demand workflow to make a **target repository** easy for AI agents to grasp with **minimal tokens**, using conventions that stay **out of the human reading path** where possible.

## When to use

- User asks to optimize agent access, agent onboarding, or `llms.txt`
- User wants hidden agent metadata in an existing project
- After adding major CLI/MCP features to a product repo (refresh agent surfaces)

Do **not** run proactively on every task.

## Execution modes

| Mode | When |
|------|------|
| **Script first** | Default — fast audit + scaffold |
| **Subagent** | Large/unknown repo or user wants full editorial pass |

### 1) Script (run first)

From the **target repository root** (not necessarily metagit-cli):

```bash
/path/to/metagit-agent-access/scripts/optimize-agent-access.sh [repo_root] [--apply] [--json]
```

Bundled with the package after `metagit skills install --skill metagit-agent-access`:

```bash
# Resolve bundled skill path (example layout)
SKILL_ROOT="$(python3 -c "import metagit, pathlib; print(pathlib.Path(metagit.__file__).parent / 'data/skills/metagit-agent-access')")"
"$SKILL_ROOT/scripts/optimize-agent-access.sh" . --apply --json
```

Flags:

- `--dry-run` (default): report gaps only
- `--apply`: create missing scaffolds from templates; inject README HTML comment if absent
- `--json`: machine-readable report on stdout

### 2) Subagent (on demand)

When the script report shows gaps the templates cannot fill, or the repo is non-trivial, dispatch a **generalPurpose** subagent (not background) with the prompt in [subagent-prompt.md](subagent-prompt.md).

Replace `{{REPO_ROOT}}` with the absolute target path. The subagent must:

1. Run the optimizer script with `--json`
2. Apply `--apply` if safe (no overwrite of human-authored agent sections without diff review)
3. Add/refine **hidden** metadata (HTML comments) before visible prose changes
4. Keep human-facing README diff minimal (one short pointer table max)
5. Return a JSON summary: `files_created`, `files_updated`, `token_estimate_llms_txt`, `follow_ups`

Parent agent: merge subagent summary; do not paste full generated files into chat.

## Artifacts (priority order)

| Artifact | Audience | Human visibility |
|----------|----------|------------------|
| `llms.txt` | LLM crawlers | Low ( convention ) |
| `AGENTS.md` | Agent hosts | Low ( agent convention ) |
| `<!-- agent-access:... -->` in README | Agents parsing raw MD | **Hidden** (HTML comment) |
| `docs/agents.md` | Docs site + agents | Medium ( link from README ) |
| `.agent/manifest.json` | Agents only | Hidden ( dot dir ) |

See [reference.md](reference.md) for formats.

## Quality bar

- **Token budget:** `llms.txt` ≤ 80 lines; `AGENTS.md` agent section ≤ 120 lines before project-specific content
- **No duplication:** `llms.txt` indexes; `AGENTS.md` quick reference; `docs/agents.md` full guide
- **Session block:** every artifact set includes install + 2–3 session-start commands
- **Idempotent:** re-run `--apply` must not duplicate HTML comment blocks or sections

## Metagit-specific extras

If target has `.metagit.yml`, include in generated session block:

```bash
export METAGIT_AGENT_MODE=true
metagit context pack --tier 2 --json
metagit skills install --scope user
```

## Verification

After `--apply`:

```bash
test -f llms.txt && test -f AGENTS.md
rg 'agent-access:start' README.md  # hidden block present
```

If `mkdocs.yml` exists, add `agents.md` to nav and run `mkdocs build --strict` when docs CI expects it.

## Additional resources

- [reference.md](reference.md) — hidden metadata patterns
- [subagent-prompt.md](subagent-prompt.md) — full subagent dispatch text
- [templates/](templates/) — scaffold files
