---
name: optimize-agent-access
description: Run the metagit-agent-access skill or subagent to scaffold llms.txt, AGENTS.md, and hidden HTML agent blocks.
triggers:
  - "agent access"
  - "llms.txt"
  - "optimize agent"
  - "agent-access"
last_updated: 2026-05-22
---

# Optimize agent access

## When

User wants minimal-token agent onboarding for a repo (this repo or another).

## Steps

1. Read skill: `src/metagit/data/skills/metagit-agent-access/SKILL.md`
2. Run audit:
   ```bash
   src/metagit/data/skills/metagit-agent-access/scripts/optimize-agent-access.sh . --json
   ```
3. Apply scaffolds when safe:
   ```bash
   src/metagit/data/skills/metagit-agent-access/scripts/optimize-agent-access.sh . --apply --json
   ```
4. For large gaps, dispatch subagent with `subagent-prompt.md` from the skill directory.

## Verify

- `llms.txt`, `AGENTS.md` exist
- `rg 'agent-access:start' README.md`
- Human README diff stays minimal

## Reference

- Skill: `metagit-agent-access`
- Patterns: `reference.md` in skill folder
