# Add a built-in `metagit prompt` kind

When adding a new operational prompt for agents:

1. Extend `PromptKind` in `src/metagit/core/prompt/models.py` (Literal union).
2. In `src/metagit/core/prompt/catalog.py`:
   - Append a `PromptCatalogEntry` to `_CATALOG` (title, description, `scopes`).
   - Add the kind to `_SCOPE_KINDS` for each allowed scope.
   - Add non-empty `template_body` text in the `templates` dict (unless the kind is `instructions`, which returns early).
   - If the prompt should gain focus labels at project or repo scope, extend the existing `scope == "project"` / `scope == "repo"` suffix blocks in `template_body`.
3. Add or extend tests in `tests/core/prompt/test_prompt_service.py` (catalog lists the kind; `PromptService().emit(...)` for at least one scope).
4. Update `.mex/ROUTER.md` **Working** bullet for `metagit prompt` if the new kind is user-facing.

CLI `metagit prompt workspace|project|repo` picks kinds from `kinds_for_scope` automatically; no separate enum in the Click layer.
