---
name: metagit-release-audit
description: Mandatory before calling work complete when the session changed repo files. Runs format, lint, tests, integration tests, and optional security via task qa:prepush. Use before push, release, or hand-off.
---

# Auditing Release Readiness

Use this skill **whenever** your session added or edited tracked files in this repository and you are about to hand off or say the task is done—not only "release" workflows. Read-only Q&A with no writes can skip it.

## Workflow

1. Run the pre-push quality gate.
2. Capture failing stage logs and iterate fixes.
3. Re-run until all required checks pass.
4. Return a short readiness summary.

## Commands

- `task qa:prepush`
- `task qa:prepush:loop -- 3` (optional bounded retry loop)

## Output Contract

Return:
- pass/fail status by stage
- unresolved blockers (if any)
- push readiness recommendation

## Safety

- Do not claim readiness unless checks are actually green.
