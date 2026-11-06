# DRAFT: Typed-bound chunk units — staged-checking contract amendment

**Status:** DRAFT for A3 / Matthew review — 2026-11-06 (A1, LUCY-20261106-004 slice)
**Not part of the accepted instrument.** The accepted contract remains
`docs/CHECKED_CHUNK_CONTRACT.md` (frozen Candidate6/Candidate7 semantics); nothing
here changes any shipped tool, budget, or test until explicitly accepted.
**Evidence base (measured, builder-run):**
`tests/probe_typed_bound_pipeline.py` @ `codex/a1-typed-bound-pipeline@04573c9`
(receipt `BOOT-A1-20261106-011`, outbox `AGENT1_OUTBOX.md` in
`codex/candidate7-20261105@d5a105a`), reusing `tests/test_chunk_typed.py`,
`tests/test_chained_bindings.py` and `pep_chunk_contract.py` machinery verbatim.

## 1. Problem

The canonical staged pipeline plans ONE chunk per function (declaration closure +
function subtree). Four real lexer functions do not fit that shape under the
unchanged 100k-step / 1 MiB budgets: `utf8_check` (step limit at 268n),
`make_progress`/`make_cursor` (step limit unscoped), `lexer_step` (transport).
The checker ALREADY accepts finer slices (`analyze_chunk_typed`,
`analyze_chunk_typed_bound`); the gap is that the *contract layer* has no record
kind meaning "this function is covered by a multi-unit decomposition", so a
decomposed function cannot count toward zero-uncovered coverage in the ledger.

## 2. New contract record: the typed-bound function unit

One **function unit record** (host-side, alongside `chunk_record`) per decomposed
function, with fields and refusals mirroring `ChunkLedger.accept` discipline:

- `entry`: function name; must resolve to one top-level function node of the
  target document/revision (provenance identical to external fact stamps).
- `units`: covering list of `(label, statement_range lo..hi, carried_statement_ranges,
  unit_status, unit_report_fingerprint)`.
  **Coverage completeness:** ascending statement ranges must exactly tile
  `0..N` where `N = len(index.statement_children(function_id))` — no gap, no
  overlap, else `UNIT_COVERAGE_MISMATCH`.
- `fact_provenance`: each unit's external facts and carried `BindingFact`s must be
  same-revision (existing `PEP_STALE_REVISION` gates) and **pool-renumbered**:
  carried bindings pooled through `contract.BindingPool(document, revision)`
  (dedupe by source identity; raw pooling is the measured 14/21 aliasing
  failure — `test_raw_pooling_aliases_bindings_and_loses_coverage`).
- `unit_status`: each unit's checker report status must be `"valid"` with an
  EMPTY diagnostics list; any other status ⇒ the record refuses
  (`UNIT_NOT_VALID`), and the recorded first-failing unit index is the
  first refusing layer.
- **Terminality (corrected by measurement, A1 2026-11-06):** the LAST unit
  must structurally close the body (`hi == total statement count`). Driving
  the checker itself with `expect_returns=True` on a squeezed terminal slice
  costs more and crossed the 100k-step ceiling for utf8_check's group 20
  (measured), so the record does NOT require checker-level terminality;
  the missing-return semantic residual is disclosed here rather than hidden:
  decomposition proves every present statement including the return (wrongly
  typed returns still diagnose — cf. the K4 P2 negative), but the
  whole-check's absent-return diagnostic is not reproduced by slices.
  Closing that residual is priced as a later sweep (whole-body
  `expect_returns` when affordable, or a terminal slice under a raised
  suitability analysis) — never by budget changes.
- Source identity: every unit slice consumes original-id subtrees via
  `index.subtree(...)` (header + statement subtrees), so line/span identity and
  byte offsets are untouched (same mechanism as existing statement units).

## 3. Ledger integration shape (minimum change)

`ChunkLedger` gains nothing structural: a decomposed function contributes its
function-unit record to the plan the way a chunk record does today; `complete()`
totality additionally requires one unit record (or one plain chunk record) per
planned function. Two concrete integration options for review:

- **Option A (additive):** new plan tier — `plan_chunks` emits function units for
  functions declared `decomposed` by the planner; `validate_chunk` accepts either
  record kind per position. Frozen tool set unchanged.
- **Option B (report-carried):** `emit_c23` consumes the union of unit reports as
  the function's CheckerReport-equivalent facts (statement groups carry the same
  original spans, so declaration-emittability agreement probes apply unchanged).

Option A is cheaper to review; B is what emitter consumption eventually needs.
**Recommendation:** accept A first; prototype B in a scratch before pinning.

### 3.1 Option A insertion points (exact symbols, `pep_chunk_contract.py`)

- `ChunkPlan` (L443): add an optional `decomposed` mapping
  `{position: FileName}` or a parallel `unit_positions` so
  `plan_ids(...)` can mark which positions are unit-backed; `describe()`
  gains the same field (machine-checkable, additive).
- `_plan` (L503): no change — the decomposition supplies the SAME node-id list
  (whole function subtree) for the marked position, so existing node-coverage
  invariants (`test_nodes_cover_the_document...`) hold unchanged.
- `chunk_record` (L570) / `validate_chunk` (L589): dispatch on the plan mark —
  a unit-backed position validates a SIGNED SUM of its unit reports instead of
  one report (each unit's report fingerprint + pool generation; totality via
  the section-2 tiling rule). First failing unit is preserved as
  `first_refusal` in the record.
- `ChunkLedger.accept/complete` (L671): unchanged for ordering;
  `complete()` totals exactly as today since each marked position still ends
  `valid`/`invalid`/`incomplete`.
- Provenance: unit reports keep the SAME document/revision Gates via the
  `bound-chunk` tool's existing `PEP_STALE_REVISION` ingress; no new host
  authority, no relaxed refusal.

## 4. What this closes (measured, unchanged budgets)

| function | route | evidence |
|---|---|---|
| `utf8_check` | bound statement groups, 21 units | 21/21 valid, 0 diagnostics; per-unit steps 15,896–89,918; 9 bindings carried |
| `lexer_start` | body-only typed chunk + host `semantic_snapshot` facts | valid (landslide pin already measured in `test_chunk_typed`) |
| `make_progress` (scoped) | body-only typed chunk + scope-fact closure | valid (unscoped stays STEP_LIMIT — the F1 measured trade; scoped is the production pattern) |

## 5. What this does NOT close (priced honestly)

- **`make_cursor`** — body is a SINGLE `return` statement (69-node giant record
  literal) — measured: `statements == 1`, and its bound group 0 refuses with
  `PEP_RUNTIME_STEP_LIMIT`. There is nothing for statement grouping to split, and
  `bounded_units` yields no interior for it (`block_children` of a return is
  empty). Needed mechanism: **expression-level staging** (sub-statement slice
  records) — new checker capability, priced separately; deliberate source
  restructuring of the accepted lexer is out of scope for this amendment.
- **`lexer_step`** — whole-body slice exceeds the 1 MiB transport cap; bound
  group 0 valid (11,704 steps) but group 1 hits the step ceiling; measured:
  the function has **36 top-level statements** and `bounded_units` yields
  **no interior unit at the failing statement** (`statement[1]` has no
  `body`-role children), so the existing one-level interior mechanism does not
  even engage there. Needed: statement-kind-aware **recursive staging** or a
  deliberate, separately-reviewed decomposition of the canonical function.
  Priced, not attempted in this slice.

## 6. Non-goals

No new language features; no `analyze_chunk` (frozen 3-arg tool) change; no
budget, transport-cap, or frozen-test edit; no doctored acceptance matrices
(Candidate6/7 66-node row stays recorded as measured RED). The amendment only
gives the contract layer a record kind for checker capability that already
exists and is measured green.

### 6.1 Inherited forgery residual (disclosed per A3 BOOT-A3-007 condition 2)

Carried bindings POOLED across units inherit the checker's stamp-consistency
boundary, independently confirmed by A3: a **same-target forged PARAMETER
type is admitted** (stamps are provenance labels, not proofs); forged
RESULT/ARITY are refused (A3 K1b: `PEP_TYPE_MISMATCH` /
`PEP_ARGUMENT_COUNT`). Pooling does not widen that admission — the hostile
pooled-carry gate (Condition 1) pins that manipulated pooled facts that are
USED surface-refuse at the checker and are recorded as the unit record's
first refusal, never silently laundered through the pool. Repairing the
admission itself is a checker-level K1-A3 residual, out of scope here.
