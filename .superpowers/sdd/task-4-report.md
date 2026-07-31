# Task 4 Report: LocalDocumentStore

## Status

Complete. Implemented and committed Task 4 only.

## Implementation

- Added `LocalDocumentStore` with flock-guarded JSON reads and writes, SHA-256
  content tokens, CAS `put`/`delete`, append, prefix listing, and `ref_for`.
- Preserved the legacy paths for objectives, handoffs, approvals, and events.
- Preserved the `handoffs` envelope for appends to
  `coord.handoffs/document`; generic appends use `items`.
- Registered the local backend in the shared contract while preserving the
  memory factory's ability to ignore `tmp_path`.
- Updated the changelog and `.mex/ROUTER.md` Task 4 state.

## TDD and Verification

- RED: `test_local_document_store.py` failed because
  `metagit.core.state.local_document` did not exist.
- GREEN: focused local tests passed: 5 passed.
- Contract registration exposed and drove the `list_prefix` identity behavior:
  1 failed, 9 passed before the fix.
- Final focused suite: 15 passed.
- `task qa:prepush`: passed all applicable format, lint, manifest, modality,
  changelog, unit, e2e, audit, Bandit, and gitleaks checks.

## Commit

- `323790d feat(state): add LocalDocumentStore with legacy coord paths`

## Concerns

- GitNexus impact and change detection could not run because the MCP runtime
  supports database storage version 40 while the current index is version 42.
  The required local index refresh is run separately as the final closeout step.

## Important Review Fixes

- Rejected unsafe namespaces and keys containing traversal markers, absolute
  paths, or path separators, and verified resolved generic and legacy paths
  stay within their intended roots.
- Replaced in-place truncating writes with same-directory temporary files,
  `fsync`, and atomic `os.replace` while retaining flock serialization.
- Made `coord.events/document` read-only for `put`, `append`, and `delete`;
  `get` continues to read an existing legacy events document.
- RED evidence: 9 focused cases failed before implementation (8 unsafe path
  cases and events `put`).
- GREEN evidence: requested focused suites passed, 24 tests total, including
  local atomic write round-trip behavior.

## Remaining Important Review Fixes

- `get()` now reads bytes once and derives both the parsed JSON body and
  SHA-256 CAS token from that single immutable snapshot.
- Removed module-level imports of `StateToken` from `state.base` and
  `SessionStore`; the local store resolves the configured sessions directory
  directly without importing context-dependent session models.
- Added a clean-process subprocess regression test for
  `LocalDocumentStore` import and a replacement-race regression test proving
  the returned body and token describe the same bytes.
- RED evidence: both new regressions failed before implementation (snapshot
  token mismatch and circular-import traceback).
- GREEN evidence: requested focused suites passed, 26 tests total, including
  the cold-import subprocess assertion.

## Empty and Dot Path Component Fix

- `_validate_component` now rejects empty string and `"."` for namespace and
  key before path resolution.
- Regression coverage: extended `test_invalid_document_ref_paths_are_rejected`
  and added `test_ref_for_rejects_empty_and_dot_components`.
- Focused suite: 24 passed (`tests/core/state/test_local_document_store.py`).

## Commit

- `fix(state): reject empty and dot path components in LocalDocumentStore`
