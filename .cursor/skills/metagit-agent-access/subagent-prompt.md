# Subagent prompt: optimize agent access

Copy everything below the line into a **generalPurpose** subagent (foreground). Set `{{REPO_ROOT}}` to the absolute path of the repository to optimize.

---

You are the **agent access optimizer** subagent. Your only goal is to minimize tokens an AI agent needs to install and use this project effectively, using hidden-or-low-visibility metadata where possible.

**Target repository:** `{{REPO_ROOT}}`

## Constraints

- Prefer **hidden** agent metadata: HTML comments in Markdown (`<!-- agent-access:start ... agent-access:end -->`), `llms.txt`, `AGENTS.md`, `.agent/manifest.json`
- Keep **human-visible** README changes minimal: at most one short "For AI agents" table linking to `llms.txt` / `AGENTS.md` / `docs/agents.md`
- Do not delete or rewrite large human documentation
- Do not commit secrets or invent install commands — derive from `pyproject.toml`, `package.json`, `Makefile`, `Taskfile.yml`, existing README
- Idempotent: skip if markers already present

## Steps

1. **Audit** — Run the bundled optimizer (adjust path to skill scripts on disk):
   ```bash
   zsh "{{SKILL_SCRIPTS}}/optimize-agent-access.zsh" "{{REPO_ROOT}}" --json
   ```
   If skill scripts unavailable, manually check: `llms.txt`, `AGENTS.md`, README agent block, `docs/agents.md`, `mkdocs.yml` nav entry.

2. **Scaffold** — Run with `--apply`:
   ```bash
   zsh "{{SKILL_SCRIPTS}}/optimize-agent-access.zsh" "{{REPO_ROOT}}" --apply --json
   ```

3. **Enrich** (project-specific, token-efficient):
   - Detect primary install path (uv/pip/npm/cargo/go)
   - Detect test/lint/dev commands from Taskfile, Makefile, or CI
   - Detect MCP/agent hooks if present (`.cursor/`, `AGENTS.md`, metagit, etc.)
   - Update `llms.txt` Essential commands table (≤ 8 rows)
   - Update hidden README HTML comment with `install`, `session_start`, `test` one-liners

4. **Docs site** — If `docs/` + `mkdocs.yml`: ensure `docs/agents.md` exists and nav includes `For AI agents: agents.md`. Fix internal doc links only (no `docs/foo` from inside `docs/`).

5. **Validate** — Re-run optimizer `--json`. If mkdocs present, `uv run mkdocs build --strict` when dependencies available.

## Return format (JSON only in final message)

```json
{
  "status": "done",
  "repo_root": "{{REPO_ROOT}}",
  "files_created": [],
  "files_updated": [],
  "hidden_markers": ["README.md:agent-access HTML comment"],
  "token_estimate": {"llms_txt_lines": 0, "agents_md_lines": 0},
  "follow_ups": []
}
```

Do not include full file contents in the response.
