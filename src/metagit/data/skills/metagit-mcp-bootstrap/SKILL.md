---
name: metagit-mcp-bootstrap
description: Use when generating or refining local .metagit.yml files using deterministic discovery plus MCP sampling.
---

# Metagit MCP Bootstrap Skill

Use this skill to create a local `.metagit.yml` using discovery-driven prompts and MCP sampling.

## Purpose

Generate schema-compliant `.metagit.yml` files with high contextual quality while preserving safety and explicit user control.

## Local Script Wrapper (Use First)

Use this token-efficient wrapper for local bootstrap tasks:
- `./scripts/bootstrap-config.zsh [root_path] [force]`

Behavior:
- Writes `.metagit.yml` when missing
- Validates via Metagit config models
- Returns a compact status line for agents

## Workflow

1. Gather deterministic discovery data from the target repository:
   - source language/framework indicators
   - package/lock/build files
   - Dockerfiles and CI workflows
   - terraform files and module usage
2. Build a strict prompt package:
   - output format contract: valid YAML only
   - required schema fields and constraints
   - extracted discovery evidence
3. If sampling is supported, call `sampling/createMessage`.
4. Validate generated YAML with Metagit config models.
5. Retry with validation feedback up to a fixed max attempt count.
6. Return draft output and write only on explicit confirmation.

## Output Modes

- **Plan-only mode**: return prompt + discovery summary if sampling unavailable.
- **Draft mode**: return `.metagit.generated.yml` content.
- **Confirmed write mode**: write to `.metagit.yml` only with explicit parameter (`confirm_write=true`).

## Quality Bar

- Preserve discovered evidence in structured fields.
- Include workspace project and related repo entries where detectable.
- Avoid invented repositories or unverifiable dependencies.

## Safety Rules

- Never overwrite `.metagit.yml` silently.
- Never emit secrets in cleartext.
- Prefer placeholders for credentials or tokens.
