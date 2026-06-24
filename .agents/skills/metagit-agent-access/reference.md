# Agent access patterns (reference)

## Hidden HTML block in README

GitHub and most MD renderers **hide** HTML comments. Agents reading raw Markdown still see them.

```markdown
<!-- agent-access:start
project: my-app
install: uv tool install my-app
session_start: my-app --help
test: task test
lint: task lint
refs: llms.txt, AGENTS.md, docs/agents.md
agent-access:end -->
```

Rules:

- Single block near top of README (after H1 + one-line description)
- One line per key; no prose
- Parent agent-access optimizer must not duplicate blocks (`agent-access:start` is unique)

## llms.txt

Root-level index (~40–80 lines). Structure:

```
# Project name
> One sentence

## Install
(shell one-liner)

## Session start
(2–3 commands)

## Docs
- [AGENTS.md](AGENTS.md)
- [full guide](docs/agents.md)  # if exists

## Essential commands
| Goal | Command |
```

Spec: https://llmstxt.org/

## AGENTS.md

Agent-host convention (Cursor, Copilot, etc.). Structure:

1. **Agent quick reference** (install, session, command table) — 80–120 lines max
2. **Contributor / tooling section** (optional, below `---` or HTML marker)

For metagit-managed repos, include `METAGIT_AGENT_MODE` and `metagit context pack`.

## docs/agents.md

Published counterpart of AGENTS quick reference. Link from README with one line; full tables live here.

## .agent/manifest.json

Optional machine manifest (git-tracked or gitignored per project):

```json
{
  "schema": "metagit-agent-access/1",
  "install": "uv tool install my-app",
  "session": ["my-app --version"],
  "refs": ["llms.txt", "AGENTS.md"]
}
```

## Anti-patterns

- Duplicating full CLI reference in README (humans suffer, agents waste tokens)
- Agent instructions only in wiki/issues (not discoverable from repo root)
- Visible "AI AGENT PLEASE READ" banners (use comment + llms.txt instead)
- 500-line `llms.txt` (use profiles / link to docs)
