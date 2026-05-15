# Metagit Skills Install Guide

This file explains how to clone this project and enable the included local skills.

## 1) Clone the repository

```bash
git clone https://github.com/metagit-ai/metagit-cli.git
cd metagit-cli
```

## 2) Install project dependencies

```bash
uv sync
```

## 3) Sync skills into local editor skill discovery paths

Run this from the repository root:

```bash
task skills:sync
```

This mirrors `skills/*` into `.cursor/skills/*` for local agent discovery.

## Included skills

The project ships practical metagit-focused skills under `skills/`, including:

- ongoing project and workspace management (OpenClaw / Hermes)
- workspace scope discovery
- workspace sync workflows
- upstream blocker triage
- repo impact planning
- GitNexus analysis automation
- `.metagit.yml` refresh/bootstrap workflows
- release readiness audit workflows
- multi-repo implementation coordination

Open any `skills/<skill-name>/SKILL.md` file for details and usage guidance.
