---
name: metagit-bootstrap
description: Use when generating or refining local .metagit.yml files using deterministic discovery plus MCP sampling or CLI-only fallbacks.
---

# Metagit MCP Bootstrap Skill

Use this skill to create a local `.metagit.yml` using discovery-driven prompts and MCP sampling.

## Purpose

Generate schema-compliant `.metagit.yml` files with high contextual quality while preserving safety and explicit user control.

## Bundled scripts (optional)

Helper scripts require the full skill tree or the PyPI package copy. Hermes `skill_manage`
(SKILL.md only) does **not** include `scripts/`.

```bash
SKILL_ROOT="$(python3 -c "import metagit, pathlib; print(pathlib.Path(metagit.__file__).parent / 'data/skills/metagit-bootstrap')")"
"$SKILL_ROOT/scripts/bootstrap-config.sh" [root_path] [force]
```

Behavior:
- Writes `.metagit.yml` when missing (minimal application scaffold)
- Validates via Metagit config models
- Returns a compact status line for agents

## Execution modes

| Mode | When |
|------|------|
| **CLI-only** | Shell agent, no MCP host, Hermes without sampling |
| **MCP sampling** | Host supports `sampling/createMessage` |
| **Plan-only** | Sampling unavailable; return draft for human/agent review |

## CLI-only fallback (no MCP sampling)

Use this path when `sampling/createMessage` is unavailable — common in CLI-only agent
sessions or Hermes installs without MCP sampling.

1. **Discover evidence** from the target repository:

```bash
export METAGIT_AGENT_MODE=true
metagit detect repository -p . -o json
metagit detect repo -p . -o yaml
metagit detect project -p . -o yaml
metagit detect repo_map -p . -o json
```

2. **Minimal manifest** when none exists:

```bash
metagit init --kind application --no-prompt
# or: "$SKILL_ROOT/scripts/bootstrap-config.sh" .
metagit config validate -c .metagit.yml
```

3. **Richer draft** — agent composes YAML from detect output + schema reference:

```bash
metagit config example          # full annotated exemplar
metagit config tree -c .metagit.yml --json   # after minimal init
```

Write draft to `.metagit.generated.yml`, validate, then promote on confirmation:

```bash
metagit config validate -c .metagit.generated.yml
mv .metagit.generated.yml .metagit.yml   # only after explicit operator approval
metagit config validate -c .metagit.yml
```

4. **Incremental refinement** on an existing manifest:

```bash
metagit config show -c .metagit.yml --json
metagit config patch -c .metagit.yml --op set --path <path> --value <json> --save
metagit prompt repo -p P -n R -k repo-enrich --text-only   # merge detect into catalog
```

Never call MCP-only bootstrap tools from CLI-only sessions. Do not overwrite `.metagit.yml`
without explicit confirmation.

## MCP sampling workflow

When sampling **is** supported:

1. Gather deterministic discovery data from the target repository:
   - source language/framework indicators
   - package/lock/build files
   - Dockerfiles and CI workflows
   - terraform files and module usage
2. Build a strict prompt package:
   - output format contract: valid YAML only
   - required schema fields and constraints
   - extracted discovery evidence
3. Call `sampling/createMessage`.
4. Validate generated YAML with Metagit config models.
5. Retry with validation feedback up to a fixed max attempt count.
6. Return draft output and write only on explicit confirmation.

## Output Modes

- **Plan-only mode**: return prompt + discovery summary if sampling unavailable.
- **Draft mode**: return `.metagit.generated.yml` content.
- **Confirmed write mode**: write to `.metagit.yml` only with explicit parameter (`confirm_write=true`).

## Quality Bar

- Preserve discovered evidence in structured fields.
- Include workspace project and related repo entries where detectable.
- Avoid invented repositories or unverifiable dependencies.

## Safety Rules

- Never overwrite `.metagit.yml` silently.
- Never emit secrets in cleartext.
- Prefer placeholders for credentials or tokens.
