---
name: auditing-release-readiness
description: Audit local release readiness by running formatting, linting, tests, and security checks with concise failure-focused output. Use before push, release, or hand-off.
---

# Auditing Release Readiness

Use this skill at the end of a coding session.

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
