# Validate documentation links

Use when adding or changing links in `README.md` or `docs/**/*.md`.

## Local

```bash
task docs:links
```

Requires [lychee](https://github.com/lycheeverse/lychee): `brew install lychee` or `cargo install lychee --locked`.

Config: `lychee.toml` (scopes markdown only; skips generated `docs/llm*.txt` and localhost URLs).

## CI

Ubuntu job in `.github/workflows/test.yaml` runs `lychee-action` on every push and pull request.

## README vs docs home page

`README.md` and `docs/index.md` are **separate files** (not a symlink). Relative paths differ:

| Asset / page | README (repo root) | docs/index.md (MkDocs) |
|--------------|-------------------|-------------------------|
| Logo | `docs/inc/metagit_logo_dark.png` | `inc/metagit_logo_dark.png` |
| Skills | `docs/skills.md` | `skills.md` |
| Hermes IaC guide | `docs/hermes-iac-workspace-guide.md` | `hermes-iac-workspace-guide.md` |
| License | `./LICENSE.md` | GitHub URL (outside MkDocs tree) |

When editing marketing copy shared between both, update both files and run `task docs:links`.
