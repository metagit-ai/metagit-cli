# Metagit

Metagit gives you situational awareness across Git repositories. It helps multi-repo projects feel manageable by keeping stack details, generated artifacts, dependencies, and related metadata in one place.

## About

This tool works well for scenarios like:

1. At-a-glance view of a project's technical stacks, languages, external dependencies, and generated artifacts.
2. Switching between many Git projects during the day without losing context.
3. Isolating outside dependencies that weaken the security and dependability of your software delivery pipelines.
4. Automated documentation of a code's provenance.
5. Helping new contributors get from onboarding to first commit faster.

Metagit is designed for developers, SREs, and AI agents who work across connected repositories. It tracks the dependencies and project relationships that are easy to miss when you only look at one repo at a time.

## Quick start

Install or upgrade the CLI globally with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install metagit-cli
uv tool install -U metagit-cli   # upgrade later
metagit version
```

> Use the PyPI package name **`metagit-cli`**. The `metagit` package on PyPI is a different project.

Install bundled agent skills (OpenClaw, Hermes, Claude Code, and others):

```bash
metagit skills list
metagit skills install --scope user --target openclaw --target hermes
```

Use `--scope project` when installing into a specific umbrella repository checkout. See [Skills](docs/skills.md) for targets, MCP install, and the project-management skill for agents.

## Audience

This tool targets:

- DevOps Engineers
- Polyglot developers
- New team members
- Project Managers
- SREs
- Solution Engineers
- AI Agents (more to come!)

## Metagit is NOT...

### ...an SBOM tool

SBOM output is often thousands of lines and includes full transitive dependency trees. That level of detail is usually too heavy for day-to-day situational awareness and agent context. Metagit may read SBOM manifests as an input in the future, but it is not trying to replace SBOM tooling.

Metagit uses common project files (for example `go.mod`, `package.json`, and `requirements.txt`) for detection and validation boundaries. These are used to identify stack composition, not to provide exhaustive version intelligence.

### ...a Git client

Despite the name, this still relies on Git and your existing hosting platform.

## ...a full project packer

Metagit intentionally focuses on the highest-value project signals. It does not package full repositories. If you need full-project packing, use [repomix](https://github.com/yamadashy/repomix/tree/main).

### Why brevity?

One of the core goals is reducing cognitive load when understanding project relationships. A practical side effect is lower token usage for automated AI workflows.

## How It Works

Metagit stores project configuration metadata in `.metagit.yml` inside the repository. That file follows a schema that the CLI can validate and read.

If you use Metagit for dozens of repositories (an umbrella workspace), you can edit the config manually or refresh it with heuristics and AI-assisted workflows.

## Modes

Metagit supports several operating modes:

### Workspace Mode

This is the first planned open-source CLI mode.

In this mode, you group related repositories into one workspace that you can open in VS Code or access individually from the terminal.

> **AKA** Multi-repo as Monorepo

You use one top-level umbrella project with a single metagit definition file that tracks related repositories and local target folders. You can then sync that workspace locally.

The metagit configuration file is committed to version control as its own project artifact.

**Managed repo lookup:** Use `metagit search` / `metagit find` for quick CLI lookup of repos declared in `.metagit.yml` (with optional tags and JSON output). MCP clients can call `metagit_repo_search`, and `metagit api serve` exposes the same search and resolve behavior over a small local JSON HTTP API for agents and scripts.

This mode is useful for:

- Creating umbrella projects for new team members of a multi-repo project
- Individual power users that need to quickly pivot between several project repositories that comprise a larger team effort
- Keeping loosely coupled Git projects grouped without relying on submodules

## Metadata Mode

This mode uses the same config file as workspace mode, with additional metadata such as primary language, frameworks, and other context you want available when entering a repo.

Configuring this by hand for one project is simple. Doing it across dozens or thousands of repos is not. Metagit uses detection heuristics to automate as much as possible and can use AI workflows where deterministic code is not enough.

> **Note**: AI-assisted detection should be monitored and converted into deterministic logic over time.

In this mode, Metagit helps answer questions like:

- What other projects are related to this project?
- What application and development stacks does this project use?
- What external dependencies exist for this project?
- What artifacts does this project create?
- What branch strategy is employed?
- What version strategy is employed?

> **External dependencies** are a common source of pipeline instability.

## Install

Global install and skill setup are covered in [Quick start](#quick-start) above.

### Local first-run

Inside any Git repository:

```bash
metagit init
```

That creates `.metagit.yml` and updates `.gitignore`.

## Skills

Bundled skills ship with the package and install via `metagit skills install` (see [docs/skills.md](docs/skills.md)). For development in this repository, `skills/` is the source tree; run `task skills:sync` to mirror into `.cursor/skills/`.

## Documentation

For installation guidance, detailed usage, including full CLI command surface, local MCP runtime setup, API-oriented flows, and advanced examples, use the documentation site:

- [Documentation](https://metagit-ai.github.io/metagit-cli/)

## License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE.md) file for details.
