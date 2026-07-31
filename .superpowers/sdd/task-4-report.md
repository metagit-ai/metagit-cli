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
