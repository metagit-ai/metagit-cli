# metagit-cli: Routing Engine + Run Ledger — Implementation Spec

**Date:** 2026-08-10
**Target repo:** `metagit-cli` (the user's personal repo — NOT modified by the SRAM agent)
**Target version:** 0.28.0 (additive; nothing here breaks 0.27.x)
**For:** a remote/headless coding agent (Cursor, Claude Code, or the user) working *in* metagit-cli
**Companion docs (in the SRAM umbrella, for context only — do not require them to implement):**
`docs/proposals/2026-08-10-intent-action-routing-graph-design.md` (why) and
`…-plan.md` (the consumer-side wiring)

---

## 0. Read this first — what you are building and why it belongs here

metagit already carries most of an agent-routing cockpit: vendor-portable agent definitions
(`metagit agent`), layered instruction composition (`AgentInstructionsResolver`: file → workspace →
project → repo), bounded context retrieval (`metagit context pack`, `metagit prompt`), and an
objective ledger whose model *already* has `acceptance`, `mr_url`, and `approval_id`.

Two things are missing, and they are the two ends of the same loop:

1. **An intent → action router.** Given a natural-language ask ("rotate the expired certificate"),
   deterministically return *which class of work this is* and *what machinery should handle it* —
   with no model call. metagit can compose context for a known target but cannot answer "what kind
   of request is this?"
2. **An evidence loop.** Nothing records how a class of work went last time, so nothing can decide
   that a class has become routine enough to execute as code.

This was measured in a real deployment (the SRAM ITOps umbrella, ~100 repos) before being specced:
of 13 delegated agent dispatches, **0 recorded which request class, ticket, or objective they
served** — the routing decision was discarded at the moment of dispatch. Of 82 objectives marked
`done`, **0 had an `mr_url`, 0 an `approval_id`, 0 a `human_note`**. The fields existed; nothing
filled them. So "how did this go last time?" was unanswerable, and every request — however routine —
got full model judgment.

**The engine goes in metagit because it is generic.** Storage paths are config-driven; the *content*
(the class catalog, the run records) stays in each consuming repo. One engine, many catalogs.

---

## 1. Concepts

| Concept | Meaning |
|---|---|
| **Class** | A recurring kind of request. Has trigger phrasings, an owning skill, a lane, gates, an expected artifact. |
| **Lane** | *Where* work executes (venue). Existing metagit/consumer concept. Promotion never changes lane. |
| **Tier** | *How much judgment* the work needs: `deterministic` → `skilled` → `novel`. This is the new axis, and it is what promotion moves. |
| **Run** | One execution of a class. Git-tracked. Carries the outcome and evidence. |
| **Promotion** | Automatic tier change driven by run evidence. Bidirectional. |

**Tier semantics:**

- `deterministic` — a proven, idempotent workflow. Executes via a named `executor` verb with **no
  model call at all**.
- `skilled` — a known procedure; assemble the skill + context and let an agent execute it.
- `novel` — unproven or unrecognized; full agent judgment.

**THE SAFETY INVARIANT (non-negotiable, must be enforced in code + tested):**

> A class whose work **mutates state** can NEVER reach `deterministic`. Its ceiling is `skilled`,
> permanently, regardless of how many clean runs it accumulates.

This is what makes automatic promotion defensible: auto-promotion only ever removes the model from
*idempotent reads, reports, and audits*. It mirrors the read/write boundary that mature agent
deployments already enforce for autonomous operation. **Do not add a config flag that disables this.**

---

## 2. Configuration

Additive block in `.metagit.yml`. All paths are **repo-relative and config-driven** — never hardcode
a catalog location in the engine.

```yaml
routing:
  catalog: knowledge/requests/entries     # dir of class records (*.yml, one per class)
  runs:    knowledge/requests/runs        # dir of run records   (*.yml, one per execution)
  id_prefix: REQ                          # class id prefix; run ids embed the class id
  policy:
    promote_after_clean: 5                # consecutive clean runs to move up one tier
    demote_on: [bounced, noop]            # any of these demotes immediately
    retain_success_days: 60               # landed runs older than this may be rolled up
```

Add a `RoutingConfig` pydantic model to `metagit/core/config/models.py` and hang it off the root
config as `routing: Optional[RoutingConfig] = None`. When absent, every `route`/`run`/`lane` command
must fail with a clear, actionable message (`"no routing.catalog configured — add a routing: block
to .metagit.yml"`), not a traceback.

**Storage note — deliberate divergence from `ObjectiveStore`.** Objectives live in a single
`.metagit/sessions/objectives.json`. Classes and runs must be **one file per record in a
git-tracked directory** instead, for three reasons: (a) concurrent agents appending to one JSON file
conflict — this is an observed failure, not hypothetical; (b) a routing graph must survive a fresh CI
clone, and `.metagit/` is typically gitignored; (c) per-record files make each run independently
reviewable in a diff. Reuse the `StateToken` optimistic-concurrency pattern per file.

---

## 3. Data models

Add to `metagit/core/routing/models.py` (new package `metagit/core/routing/`).

```python
Tier = Literal["deterministic", "skilled", "novel"]
Outcome = Literal["landed", "bounced", "noop", "abandoned"]
PromotionState = Literal["stable", "ready-needs-executor"]  # plus "demoted:<outcome>" free-form


class RequestClass(BaseModel):
    """A recurring kind of request: the intent → action mapping."""

    id: str                                  # e.g. REQ-CERT-ROTATION
    title: str
    triggers: list[str] = Field(default_factory=list, max_length=12)
    skill: Optional[str] = None              # owning skill/procedure name
    lane: Optional[str] = None               # execution venue (consumer-defined vocabulary)
    artifact: Optional[str] = None           # what lands when this is done
    gates: list[str] = Field(default_factory=list)
    tier: Tier = "novel"                     # managed by `lane eval`; new classes start novel
    mutates: bool = True                     # conservative default; see the safety invariant
    executor: Optional[str] = None           # command for tier=deterministic
    promotion_state: str = "stable"
    evidence: Optional[ClassEvidence] = None # DERIVED — regenerated by `lane eval`, never authored
    notes: Optional[str] = None              # hand-curated recurring-mistake warning
    updated: Optional[str] = None


class ClassEvidence(BaseModel):
    """Derived roll-up of a class's run history. Never hand-edited."""

    runs_landed: int = 0
    runs_bounced: int = 0
    runs_noop: int = 0
    clean_streak: int = 0
    last_run: Optional[str] = None
    failure_modes: list[str] = Field(default_factory=list)


class RunDispatch(BaseModel):
    session_id: Optional[str] = None
    branch: Optional[str] = None
    workdir: Optional[str] = None
    doctrine_chars: Optional[int] = None     # was governing context actually injected?


class RunEvidence(BaseModel):
    gates_run: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    steering_turns: Optional[int] = None     # mid-run human corrections ⇒ class underspecified
    digest: Optional[str] = None             # path to a harvested transcript digest


class RunArtifact(BaseModel):
    mr_url: Optional[str] = None
    merged_at: Optional[str] = None


class Run(BaseModel):
    """One execution of a class. Append-only evidence."""

    id: str                                  # RUN-<YYYYMMDD>-<HHMMSS>-<CLASS_ID>
    cls: str = Field(alias="class")          # `class` is a Python keyword — alias it
    tier: Tier
    lane: Optional[str] = None
    actor: str                               # who executed: agent+model, or a human handle
    objective: Optional[str] = None          # objective / ticket id this served
    dispatch: RunDispatch = Field(default_factory=RunDispatch)
    outcome: Optional[Outcome] = None        # None ⇒ still OPEN (legal, not an error)
    artifact: RunArtifact = Field(default_factory=RunArtifact)
    evidence: RunEvidence = Field(default_factory=RunEvidence)
    opened: str
    closed: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)
```

### The outcome taxonomy — `noop` is load-bearing

| Outcome | Meaning | Effect on promotion |
|---|---|---|
| `landed` | artifact merged / report published | counts toward the clean streak |
| `bounced` | review requested changes, CI failed, gates rejected it | **demotes immediately** |
| `noop` | the execution produced nothing (auth failure, malformed prompt, budget exhausted before work) | **demotes**; never counts as clean |
| `abandoned` | superseded or intentionally dropped | neutral — excluded from all counts |

`noop` exists because **4 of 13 audited dispatches were zero-cost no-ops that the tooling reported as
successful.** Agent CLIs commonly report `subtype: "success"` for a run that did nothing (e.g. an
unauthenticated session returning "Not logged in"). A tier system that counted those as clean runs
would promote a class on evidence that nothing ever executed. Detect it from *cost/turns/files-touched
being empty*, never from a success flag alone.

---

## 4. Command surface

New noun `route` plus `run` and `lane`, following the existing `cli/commands/<noun>.py` +
`core/<domain>/<x>_service.py` + `<x>_store.py` layering. Every command supports `--json` via the
existing `cli/json_output.py` helper, and uses `cli/exit_codes.py`.

```bash
# ── ROUTER (read-only, no model, the hot path) ────────────────────────────────
metagit route query "<natural language ask>" [--limit N] [--json]
metagit route list [--tier deterministic|skilled|novel] [--json]
metagit route show --id REQ-X [--json]          # card + run history + tier + promotion state

# ── RUN LEDGER ────────────────────────────────────────────────────────────────
metagit run open  --class REQ-X --actor <who> [--tier T] [--lane L] [--objective ID]
                  [--session-id S] [--branch B] [--workdir W] [--doctrine-chars N]
metagit run close --id RUN-... --outcome landed|bounced|noop|abandoned
                  [--mr-url URL] [--gate G]... [--evidence-file PATH]
metagit run list  [--class REQ-X] [--outcome O] [--open] [--json]

# ── PROMOTION POLICY ──────────────────────────────────────────────────────────
metagit lane eval [--id REQ-X] [--dry-run] [--json]
```

**`route query` is the hot path and must stay cheap and deterministic.** Token-overlap scoring
against `triggers` with a stopword list; no embeddings, no model call. Return ranked classes with:
id, title, confidence, skill, lane, artifact, gates, **tier**, **executor** (when
`tier=deterministic`), **evidence counts**, **promotion_state**, and any **`notes`**. On a miss,
exit non-zero and tell the caller to catalogue the class if it recurs — a miss is itself signal.

**`run close` must refuse to modify an already-closed run.** Runs are append-only evidence; a
corrected outcome is a *new* run, not an edited one. Return a clear error, not a silent overwrite.

---

## 5. The promotion algorithm

Implement as a **pure function** in `core/routing/promotion.py` so the policy is unit-testable with
no filesystem:

```python
def evaluate(cls: RequestClass, runs: list[Run], policy: RoutingPolicy) -> ClassEvidence | tuple:
    """Return the (tier, promotion_state, evidence) a class's run history justifies."""
```

```
TIERS is ordered most-deterministic first: ["deterministic", "skilled", "novel"]
A LOWER index is a HIGHER tier.

max_tier ← "skilled" if cls.mutates else "deterministic"      # THE SAFETY CEILING
tier     ← cls.tier
state    ← "stable"

closed  ← [r for r in runs if r.outcome is not None]
ordered ← closed sorted by id (ids are timestamp-ordered)

# Walk BACKWARD from the newest closed run:
#   - "abandoned" is skipped entirely (neutral)
#   - a demoting outcome stops the walk
#   - "landed" extends the streak
streak ← 0 ; bad ← None
for r in reversed(ordered):
    if r.outcome == "abandoned":       continue
    if r.outcome in policy.demote_on:  bad ← r.outcome ; break
    if r.outcome == "landed":          streak ← streak + 1

if bad is not None:
    tier  ← one tier DOWN from current (clamped to "novel")
    state ← f"demoted:{bad}"
elif streak >= policy.promote_after_clean:
    target ← one tier UP from current, clamped so index >= index(max_tier)
    if target == "deterministic" and not cls.executor:
        state ← "ready-needs-executor"      # tier UNCHANGED — see below
    else:
        tier ← target

evidence ← counts of landed / bounced / noop, the streak, and the newest run's date
```

### `ready-needs-executor` — the most important state in this design

Automatic promotion **cannot fabricate a deterministic executor**; a human has to write the verb. So
when a non-mutating class earns `deterministic` but has no `executor`, the engine must **not** promote
it and must **not** silently do nothing. It records `promotion_state = "ready-needs-executor"` and
leaves the tier alone.

The set of classes in that state is exactly: *"work that has proven itself repeatable and is waiting
to be automated."* **That queue is the system's automation backlog, ranked by demonstrated
frequency.** Surface it prominently:

```bash
metagit route list --ready          # classes that have earned deterministic but lack an executor
```

This is the "growing guide" property: the system tells its operators where the next automation win
is, derived from evidence rather than intuition.

### Why demotion is automatic too

Promotion without automatic demotion is a ratchet that only tightens — strictly worse than no
promotion, because a class that silently degrades keeps executing with no model oversight. One
`bounced` or `noop` drops the tier immediately; recovery requires a fresh clean streak. Cheap to
recover, expensive to ignore.

---

## 6. Files to create / modify

| Path | Action | Responsibility |
|---|---|---|
| `metagit/core/routing/__init__.py` | create | package marker |
| `metagit/core/routing/models.py` | create | `RequestClass`, `Run`, `ClassEvidence`, `RunDispatch`, `RunEvidence`, `RunArtifact`, `Tier`, `Outcome` |
| `metagit/core/routing/class_store.py` | create | one-file-per-class YAML read/write; `StateToken` concurrency |
| `metagit/core/routing/run_store.py` | create | one-file-per-run YAML read/write; `open_run_for(class_id)` |
| `metagit/core/routing/router.py` | create | trigger tokenization + scoring (`score(cls, query) -> (float, why)`) |
| `metagit/core/routing/promotion.py` | create | the pure `evaluate()` policy function |
| `metagit/core/routing/routing_service.py` | create | orchestration consumed by CLI **and** MCP |
| `metagit/cli/commands/route.py` | create | `route query|list|show` |
| `metagit/cli/commands/run.py` | create | `run open|close|list` |
| `metagit/cli/commands/lane.py` | create | `lane eval` |
| `metagit/cli/main.py` | modify | register the three new command groups |
| `metagit/core/config/models.py` | modify | `RoutingConfig` + `RoutingPolicy`; `routing:` on the root model |
| `metagit/core/mcp/…` | modify | expose `metagit_route_query` + `metagit_lane_eval` for parity with existing MCP tooling |
| `tests/core/routing/test_promotion.py` | create | the policy tests below |
| `tests/core/routing/test_router.py` | create | scoring/ranking tests |
| `tests/cli/test_route_cmd.py` | create | CLI + `--json` shape tests |

---

## 7. Required tests

These encode the properties that matter. **Do not ship without them.**

```python
def test_mutating_class_never_reaches_deterministic():
    """THE safety invariant. Auto-promotion is only defensible because of this."""
    cls = RequestClass(id="REQ-X", title="t", mutates=True, tier="skilled")
    runs = [landed_run() for _ in range(20)]
    tier, _, _ = evaluate(cls, runs, default_policy())
    assert tier == "skilled"


def test_deterministic_requires_an_executor():
    cls = RequestClass(id="REQ-X", title="t", mutates=False, tier="skilled", executor=None)
    tier, state, _ = evaluate(cls, [landed_run() for _ in range(5)], default_policy())
    assert tier == "skilled"
    assert state == "ready-needs-executor"


def test_nonmutating_with_executor_promotes():
    cls = RequestClass(id="REQ-X", title="t", mutates=False, tier="skilled", executor="run-report")
    tier, _, _ = evaluate(cls, [landed_run() for _ in range(5)], default_policy())
    assert tier == "deterministic"


def test_single_bounce_demotes_immediately():
    cls = RequestClass(id="REQ-X", title="t", mutates=False, tier="deterministic", executor="x")
    tier, state, _ = evaluate(cls, [landed_run(), bounced_run()], default_policy())
    assert tier == "skilled"
    assert state.startswith("demoted:")


def test_noop_never_counts_as_clean():
    cls = RequestClass(id="REQ-X", title="t", mutates=False, tier="skilled", executor="x")
    runs = [landed_run() for _ in range(4)] + [noop_run()]
    tier, _, _ = evaluate(cls, runs, default_policy())
    assert tier == "novel"


def test_abandoned_is_neutral():
    cls = RequestClass(id="REQ-X", title="t", mutates=True, tier="novel")
    runs = [landed_run() for _ in range(5)] + [abandoned_run()]
    tier, _, _ = evaluate(cls, runs, default_policy())
    assert tier == "skilled", "abandoned must neither break nor extend a streak"


def test_open_run_has_no_outcome_and_that_is_legal():
    r = Run(id="RUN-20260810-120000-REQ-X", **{"class": "REQ-X"},
            tier="skilled", actor="t", opened="2026-08-10T12:00:00Z")
    assert r.outcome is None


def test_close_refuses_to_rewrite_a_closed_run():
    ...  # service-level: closing twice must error, not overwrite


def test_route_query_returns_no_match_nonzero():
    """A routing miss is signal, not a soft success."""
    ...


def test_runs_dir_is_not_inside_a_gitignored_path():
    """Evidence must survive a fresh clone."""
    ...
```

---

## 8. Reference implementation

A working version of the ledger + policy exists in the SRAM umbrella and is the source these
semantics were validated against. Port the *semantics*, not the code (it is stdlib+ruamel, not
pydantic):

- `scripts/requests/runs.py` — run store, outcome taxonomy, `open_run_for`, `reconcile`
- `scripts/requests/requests.py` — `eval_class()` (the pure policy function), `load_runs_for()`,
  the `validate_entry` tier invariants
- `knowledge/requests/entries/REQ-*.yml` — 11 real class records to test the router against

Ask the user for read access to those files if useful; they are not required to implement this spec.

## 9. Out of scope for this change

- No model-based classification. The router is token-overlap scoring, by design: in the audited
  deployment every routing failure was a *retrieval* failure (a workflow that existed but was
  untracked/invisible, or a card nobody consulted), never a classification failure. A smarter router
  would have fixed none of them.
- No automatic *creation* of classes. Cataloguing a new class stays a human/agent authoring act.
- No retention/rollup of old run records yet. Add it once real volume exists; premature rollup
  discards the evidence the policy depends on.
- No changes to `objective`, `approval`, or `handoff` stores. A future change may link a `Run` to an
  objective by populating the objective's already-present `mr_url` — deliberately deferred.
