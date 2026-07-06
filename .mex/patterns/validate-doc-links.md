# Validate documentation links

Use when adding or changing links in `README.md` or `docs/**/*.md`.

## Local

```bash
task docs:links
```

Requires [lychee](https://github.com/lycheeverse/lychee): `brew install lychee` or `cargo install lychee --locked`.

Config: `lychee.toml` (scopes markdown only; skips generated `docs/llm*.txt` and localhost URLs).

## Pre-push (context-aware)

`task qa:prepush` runs lychee **only when** the diff touches `README.md`, `docs/**`, `lychee.toml`, `mkdocs.yml`, or doc generators (`scripts/modality-parity.yml`, `scripts/generate_modality_registry.py`, `scripts/check-doc-links.zsh`). Src-only changes skip the step. When triggered, lychee checks **only changed markdown files** (plus the generated modality registry when parity YAML changes); config-only triggers run the full README + `docs/**` scan.

Install lychee locally to exercise the step: `brew install lychee`. If lychee is missing, prepush prints `SKIP: doc_links` (use `--strict` to fail instead).

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

Links from `docs/**` to repo files outside the MkDocs tree (for example `scripts/modality-parity.yml`) must use GitHub blob URLs — `mkdocs build --strict` treats relative paths as internal doc links and fails CI.
