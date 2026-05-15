# Metagit Skills (source tree)

Agent skills live under `skills/<name>/SKILL.md`. The same content is bundled in `src/metagit/data/skills/` for PyPI installs.

## End users

Install globally and deploy skills with the CLI (see [docs/skills.md](../docs/skills.md)):

```bash
uv tool install -U metagit-cli
metagit skills install --scope user --target openclaw --target hermes
```

## Developers in this repository

```bash
task skills:validate
task skills:sync    # mirror into .cursor/skills/
```

When adding or changing a skill, update both `skills/` and `src/metagit/data/skills/`.

## Included skills

- `ongoing-project-management` — reuse or register workspace projects/repos before creating folders
- `discovering-workspace-scope` — session start scope discovery
- `metagit-control-center` — multi-repo control center
- `syncing-workspace-repositories` — guarded sync workflows
- `refreshing-project-config` — `.metagit.yml` bootstrap and refresh
- `triaging-upstream-blockers` / `metagit-upstream-discovery` — cross-repo blockers
- `planning-repo-impact` / `coordinating-multi-repo-implementation` — multi-repo implementation
- `running-gitnexus-analysis` — GitNexus indexing
- `auditing-release-readiness` — pre-push QA

Open each `SKILL.md` for full workflows.
