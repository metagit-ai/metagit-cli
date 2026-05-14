---
name: run-graphify-analysis
description: Run focused `graphify` analysis on a repo or subtree, especially when a full-repo graph would be too large or noisy.
triggers:
  - "graphify"
  - "knowledge graph"
  - "graph report"
edges:
  - target: "context/architecture.md"
    condition: "when naming communities or interpreting cross-command relationships"
  - target: "context/conventions.md"
    condition: "when verifying scaffold updates after the graph run"
last_updated: 2026-05-11
---

# Run Graphify Analysis

## Context
- Use this when a user invokes `/graphify` or asks for a repo knowledge graph.
- Start with corpus detection before committing to a full run; this repo has generated/docs-heavy areas that can drown out the interesting command and core logic relationships.
- Prefer focused subtrees when the corpus is over the graphify warning threshold or when the user only needs one part of the codebase.

## Steps
1. Resolve a stable `graphify` Python interpreter and write it to `graphify-out/.graphify_python`.
2. Run `graphify.detect` first and summarize the corpus by file type.
3. If the corpus is over the graphify threshold, show the busiest subdirectories and ask the user which subtree to analyze.
4. Run structural extraction for code files. If the selected scope is code-only, skip semantic subagents and continue with the AST-only flow.
5. Build the graph, cluster it, then label communities with plain-language names before exporting HTML.
6. If the corpus is large enough for benchmarking, run `graphify benchmark`.
7. Save manifest/cost data, clean temporary graphify files, and surface the report's God Nodes, Surprising Connections, and Suggested Questions.

## Gotchas
- `uv run --with graphifyy` can resolve to a temporary interpreter path; use the installed `graphify` tool's shebang-backed Python for multi-step runs.
- Full-repo runs can be skewed by generated assets like `site/assets/*`; detect first instead of assuming `.` is the right scope.
- Code-only runs still produce useful graph structure and avoid unnecessary semantic extraction cost.
- Community labels matter; leaving generic `Community N` names makes the report and `graph.html` much harder to navigate.

## Verify
- Confirm `graphify-out/graph.html`, `graphify-out/GRAPH_REPORT.md`, and `graphify-out/graph.json` exist in the processed directory.
- Confirm the report includes named communities instead of placeholder community labels.
- If benchmark ran, capture its reduction summary for the user.
- Confirm cleanup removed temp extraction files while preserving the final outputs.

## Debug
- If interpreter resolution breaks between steps, regenerate `graphify-out/.graphify_python` from the installed `graphify` binary.
- If the graph is empty, inspect the detect output first; the scope may contain unsupported files or only skipped content.
- If the corpus crosses the threshold, do not push through the full run blindly; narrow the scope and rerun.
- If community names look mixed or misleading, inspect the top labels per community from `graph.json` before regenerating the report.

## Update Scaffold
- [ ] Update `.mex/ROUTER.md` "Current Project State" if what's working/not built has changed
- [ ] Update any `.mex/context/` files that are now out of date
- [x] If this is a new task type without a pattern, create one in `.mex/patterns/` and add to `INDEX.md`
