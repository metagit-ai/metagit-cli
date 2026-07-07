# Installation and usage guide

This guide covers practical ways to install and run Metagit locally, plus how to enable project skills for AI-agent workflows.

## Requirements

- Python 3.12+
- `uv`
- `git`

Optional:

- Docker (for container usage)
- `gitleaks` (for local security checks in QA workflows)

## Option 1: global CLI install with uv (recommended)

Install Metagit globally as a tool:

```bash
uv tool install metagit-cli
```

Upgrade later:

```bash
uv tool install -U metagit-cli
```

Or let Metagit upgrade itself (dry-run by default):

```bash
metagit version upgrade
metagit version upgrade --apply
```

Verify:

```bash
metagit version
metagit --help
```

## Shell tab completion

Metagit ships first-class shell completion for **zsh**, **bash**, and **fish**. Static commands and flags are completed automatically; when a `.metagit.yml` is present, **`--project`**, **`--repo`**, and repomix **`--profile`** values are completed from the manifest and bundled profiles.

Install (writes to the conventional user path):

```bash
metagit completion install --shell zsh
metagit completion install --shell bash
metagit completion install --shell fish
```

Print a script or one-line activation hint:

```bash
metagit completion show --shell zsh
metagit completion install --shell zsh --stdout
```

Verify the callback works:

```bash
metagit completion doctor
```

**zsh:** ensure the install path is on `fpath` before `compinit` (the install command prints the exact line). After upgrading metagit, re-run `completion install` if new subcommands were added.

## Option 2: install from source (local development)

Clone and bootstrap:

```bash
git clone https://github.com/metagit-ai/metagit-cli.git
cd metagit-cli
uv sync
```

Install as an editable local package:

```bash
uv pip install -e .
```

Build a wheel and install that wheel:

```bash
task build
uv tool install dist/metagit-*-py3-none-any.whl
```

## Option 3: container usage

Run via container image:

```bash
docker pull ghcr.io/metagit-ai/metagit-cli:latest
docker run --rm ghcr.io/metagit-ai/metagit-cli:latest --help
```

## First local use

In a target Git repository:

```bash
metagit init --list-templates          # bundled profiles (application, umbrella, hermes-orchestrator, metagit-rewrite, …)
metagit init ./my-coordinator --template hermes-orchestrator --create
metagit init ./rewrite-coordinator --template metagit-rewrite --create
metagit init --target ../hermes-control-plane --template hermes-orchestrator --no-prompt \
  --answers-file examples/hermes-orchestrator/answers.example.yml
metagit init --kind service --minimal  # any ProjectKind without a bundled template
```

This creates `.metagit.yml` and updates `.gitignore`.

Useful first checks:

```bash
metagit config validate
metagit info
metagit fmt
```

`metagit format` is an alias for `metagit fmt`. Formatting preserves YAML comments, injects a top-level `# yaml-language-server: $schema=…` directive, and uses two-space indentation. Use `--check` in CI to fail when YAML is not normalized; `--target metagit|appconfig|all` selects which file(s) to rewrite.

## Local MCP runtime usage

Start MCP runtime in current workspace:

```bash
metagit mcp serve
```

Run one-shot status snapshot:

```bash
metagit mcp serve --status-once
```

Pin a specific workspace root:

```bash
metagit mcp serve --root /path/to/workspace
```

## AI-agent skill setup for this project

If you cloned this repository and want skills available for local agent discovery:

```bash
task skills:sync
task generate:schema
```

One-shot combined:

```bash
task skills:sync generate:schema
```

This syncs project skills into `.cursor/skills/` and regenerates config schemas.

## Session closeout checks

Before push or hand-off:

```bash
task skills:sync generate:schema
task qa:prepush
```

## Troubleshooting

- If `metagit` fails after tool install, reinstall:
  - `uv tool install -U --reinstall metagit-cli`
- If command not found, ensure `uv` tool bin path is on `PATH`.
- If provider-backed features fail, configure API tokens in app config or environment:
  - `METAGIT_GITHUB_API_TOKEN`
  - `METAGIT_GITLAB_API_TOKEN`
