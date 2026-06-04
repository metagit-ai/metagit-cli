# Metagit™

<!-- agent-entrypoint:
intent: executable-tool
primary_workflow: usage-first
install: uv tool install -U metagit-cli

bootstrap:
  - export METAGIT_AGENT_MODE=true
  - metagit context pack --tier 2 --json

authoritative:
  - ../AGENTS.md
  - ./agents.md
  - ../llms.txt

usage:
  - ../README.md#quick-start
-->
<div align="center">
<a href="https://metagit-ai.github.io/metagit-cli/">
<img src="inc/metagit_logo_dark.png" width="520" alt="Metagit™ logo">
</a>
</div>

<p align="center">
    <a href="https://github.com/metagit-ai/metagit-cli/releases/latest">
        <img src="https://img.shields.io/github/v/release/metagit-ai/metagit-cli?color=blue&label=Latest%20Release" alt="Latest Release">
    </a>
    <a href="https://github.com/metagit-ai/metagit-cli/blob/main/LICENSE.md">
        <img src="https://img.shields.io/badge/License-MIT-ffffff?labelColor=d4eaf7&color=2e6cc4" alt="License: Apache 2.0">
    </a>
    <a href="https://deepwiki.com/metagit-ai/metagit-cli">
        <img alt="Ask DeepWiki" src="https://deepwiki.com/badge.svg">
    </a>
    <img src="https://img.shields.io/badge/status-stable-green.svg" alt="Status: Stable">
    <img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python 3.12+">
    <img src="https://github.com/metagit-ai/metagit-cli/actions/workflows/test.yaml/badge.svg" alt="Tests">
    <img src="https://github.com/metagit-ai/metagit-cli/actions/workflows/docker.yaml/badge.svg" alt="Build">
</p>

Metagit gives you situational awareness across Git repositories. It helps multi-repo projects feel manageable, discoverable, and cohesive. It captures cross-repository relationships and project knowledge in easy to understand version controlled manifests.

## About

This tool works well for scenarios like:

1. At-a-glance view of a project's technical stacks, languages, external dependencies, and generated artifacts.
2. Switching between many Git projects during the day without losing context.
3. Isolating outside dependencies that weaken the security and dependability of your software delivery pipelines.
4. Automated documentation of a code's provenance.
5. Helping new contributors get from onboarding to first commit faster.

Metagit is designed for developers, SREs, and AI agents who work across loosely connected repositories. It tracks the dependencies and project relationships that are easy to miss when you only look at one repo at a time.

## Quick start

```bash
uv tool install -U metagit-cli
metagit version
metagit completion install --shell zsh   # optional tab completion
```

> **NOTE** - Use the PyPI package name **`metagit-cli`** NOT `metagit`!

Inside any Git repository, initialize a metagit manifest:

```bash
metagit init
```

That creates `.metagit.yml` and updates or adds a `.gitignore` for `.metagit/` (synced git repos).


## Skills

Install bundled agent skills (OpenClaw, Hermes, Claude Code, and others):

```bash
metagit skills list
metagit skills install --scope user --target openclaw --target hermes

# or, using vercel's skills registry (preferred)
npx skills add metagit-ai/metagit-cli
```

Use `--scope project` when installing into a specific umbrella repository checkout. See [Skills](skills.md) for targets, MCP install, and the project-management skill for agents.

## Agent guides

- [Hermes agents and organization-wide IaC](hermes-iac-workspace-guide.md) — illustrated workflow for using Metagit as a control plane across Terraform, policy, and module repositories (controller + subagents, layered `agent_instructions`, MCP tools).

## Documentation

For installation guidance, detailed usage, including full CLI command surface, local MCP runtime setup, API-oriented flows, and advanced examples, use the documentation site:

- [Documentation](https://metagit-ai.github.io/metagit-cli/)

## License

This project is licensed under the MIT License. See the [LICENSE](https://github.com/metagit-ai/metagit-cli/blob/main/LICENSE.md) file for details.

## Trademark

MetaGit™ is an open-source project.

MetaGit and the MetaGit logo are trademarks of Zachary Loeber.
