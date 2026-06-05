---
name: agent-access-optimizer
description: |
  Optimizes agent onboarding artifacts (llms.txt, AGENTS.md) for one repo.
model: inherit
tools: Read, Write, Edit, Grep, Glob, Skill
skills:
  - metagit-agent-access
---

{{ include "body" }}
