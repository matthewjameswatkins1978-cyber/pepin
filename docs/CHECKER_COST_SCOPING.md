# Checker per-node cost: structural-index scoping

Status: measurement and scoping only. No checker or host change is proposed as
already-approved work here; this note records what a per-node cost fix would
actually require before any of it is written.

Revision measured: `0437a75` on `codex/p1-checker-cost-fix`.
Limits under measurement: 100,000 steps, 1 MiB JSONL message, 65,536-byte
source open.

## Why this exists

Staged checking already covers whole real modules under unchanged limits
(`stdlib/collections.pep`: 107 of 107 top-level functions; `examples/pep_lexer.pep`
partly). The remaining failure class is per-node cost: the whole-program check
still expires at 62–66 nodes, and `lexer_step` has no split that passes.

## What the profile says

- The 66-node budget expires inside `record_declaration()` (bundle `2527:43`).
- Ablating that function does **not** raise the ceiling. The site migrates:
  `union_declaration` (66) → `child_at` (88) → `lookup_node` (110) →
  `type_shape_at` (132) → `collect_bindings` (176) → `collect_functions` (220) →
  `count_children` (264).
- Wall-clock stays flat while steps explode (log-log slope 0.79; 4–30 ms across
  44–726 nodes). The budget is consumed by step-counted list traversal, not by
  compute time.

So there is no single hot lookup. Cost is spread across the whole scan family,
and the scanners are called from inside per-node inference loops
(`infer_expression_type_at`, `expression_type_shape`,
`infer_expression_type_and_shape`, `type_analysis`).

## Census (measured)

| quantity | value |
|---|---|
| functions in the checker | 122 |
| whole-list scanners | 24 |
| direct callers of scanners (frontier) | 48 |
| call sites into the scan family | 203 |
| functions that would need an index parameter | 54 |
| call sites that would have to pass it | 221 |

Grouped by key:

| key shape | scanners | call sites |
|---|---|---|
| id-keyed (`lookup_node` only) | 1 | 31 |
| name/kind-keyed | 23 | 172 |

Largest name-keyed sites: `child_at` 71, `count_children` 21, `type_shape_at` 18,
`is_constructor` 13, `record_declaration` 12.

## Options, with the diff each implies

### A. Thread a precomputed index through the analysis

54 signature changes plus 221 call-site edits across a 773-line `type_analysis`.
This is the largest diff and the one most likely to perturb diagnostic output —
and diagnostic parity is an acceptance item. Not started.

### B. Host capability for indexed / associative node access

`lookup_node` alone is id-keyed, and flat AST ids are dense `0..n-1` and
ascending (verified 2030/2030 on `pep_lexer.pep`). A host primitive returning the
node at a given id would make those 31 call sites O(1) with a one-line body
change and no signature churn.

That covers **31 of 203** scan call sites (15%). The remaining 172 are keyed on
`(parentId, role, childIndex)` or `(kind, text)`, which needs an associative
structure, not positional access.

### C. Accept the current ceiling

Staged verification continues to cover real modules; whole-program checking of
programs beyond ~62 nodes stays unavailable.

## The constraint that decides between B and A

Pep has no list indexing and no map/dictionary. A hand-rolled index in Pep is a
`List[...]` searched by the same linear scan it was meant to replace, and binary
search is impossible without positional access. **So no in-Pep structural index
can beat O(n).** Per-node cost work therefore depends on a host data-structure
capability, not on a checker refactor.

That makes this a language/host surface decision, not a local optimisation, and
it should be taken deliberately rather than slipped in while chasing a fixture.

## Upper-bound measurement: no lookup primitive can lift this ceiling

If per-node cost were lookup-bound, replacing every whole-list name/id lookup
would raise the ceiling. It does not.

Stubbing `lookup_node`, `record_declaration`, `union_declaration`,
`variant_declaration` and `is_constructor` to constant returns (diagnostic only,
never shipped) still leaves the 66-node program over budget, and the failure site
moves well away from the lookup family:

| program | nodes | expires in (all lookups stubbed) |
|---|---|---|
| recpad-6 | 66 | `is_expression_kind` |
| recpad-8 | 88 | `empty_node` |
| recpad-10 | 110 | `resolve_all_records` |
| recpad-12 | 132 | `type_shape_at` |
| recpad-16 | 176 | `collect_bindings` |
| recpad-20 | 220 | `collect_functions` |
| recpad-24 | 264 | `count_children` |

Caveat, stated honestly: each stub still constructs a `NodeLookup` record and
calls `empty_node()`, so this is not a perfect "free" model. It is nonetheless
decisive in direction: removing the five most expensive scanners neither lifts
the ceiling nor keeps the failure in that family.

### What the new site shows

`is_expression_kind` is a disjunction chain of ~20 string comparisons
(`kind == "integer" || kind == "boolean" || ...`). The interpreter ticks per
evaluated expression, so every `||` alternative costs a tick, and this runs for
every expression node. That is representative of the real shape of the cost:
many small per-node predicate chains, not one expensive scan.

### Conclusion, and the decision this forces

Host primitives are **not** the fix, and none were added. Two further reasons:

- host builtins are deliberately charged per element of work (`reverse` ticks per
  head, `byte_slice` ticks per byte), so a positional lookup over a list would
  either tick per element (no gain) or break the accounting model (gaming the
  budget);
- even granting a genuinely free lookup family, the ceiling holds.

So whole-program checking beyond ~62 nodes is an **analysis-architecture**
question: reduce the number of interpreted expressions per node (predicate
chains, repeated passes, per-node record construction) rather than add
capabilities. That is a design decision to be taken explicitly, not something to
be discovered by attrition against fixtures.

### Sensitivity test: the predicate chain is not the cost

`is_expression_kind` was the next candidate: 13 string comparisons, and the
interpreter ticks per evaluated expression, so roughly 26 ticks per call.

Two measurements, both on the 55/66-node boundary (k=5 is 55 nodes and valid,
k=6 is 66 nodes and over budget):

| variant | k=4 | k=5 | k=6 | k=7 |
|---|---|---|---|---|
| baseline (1x chain) | valid | valid | STEP_LIMIT | STEP_LIMIT |
| doubled chain (2x) | valid | valid | STEP_LIMIT | STEP_LIMIT |
| quadrupled chain (4x) | valid | valid | STEP_LIMIT | STEP_LIMIT |

The doubled and quadrupled disjunctions are logically identical to the original,
so the only change is ~78 extra interpreted ticks per call. **Nothing moves.**

A stubbed `return true` variant was also tried and is not usable as evidence: it
changes semantics, causes every node to be treated as an expression, and makes
the ceiling *worse* (55 nodes then fails). Semantics-changing ablations distort
cost in both directions and cannot bound a contribution.

### What that tells us

At one call site and ~26 ticks per call, the predicate is on the order of 1,700
ticks for a 66-node program — about 2% of a 100,000-step budget. Quadrupling it
adds 5% and still does not cross a boundary. So collapsing this chain is not
worth a checker change, and is not the lever.

The measured picture is consistent across every experiment so far: cost is
**diffuse**, spread over many small per-node operations and repeated passes at
roughly 1,500 ticks per node. Optimising any single predicate, lookup or helper
does not move the ceiling. The lever has to be the number of interpreted
operations per node — fewer passes, or fewer per-node constructions — and that is
an analysis-architecture change, not a micro-optimisation.
### Correction: full-coverage attribution, and two negative prototypes

The first profile dump listed only the 60 hottest lines (74.3% of ticks). Widening
the dump to all 505 lines gives a complete picture, and the shares shift:

| function | ticks | share |
|---|---|---|
| `type_analysis` | 14,470 | 14.5% |
| `child_at` | 14,028 | 14.0% |
| `type_shape_at` | 13,538 | 13.5% |
| `tree_is_valid` | 7,062 | 7.1% |
| `record_declaration` | 5,752 | 5.8% |
| `lookup_node` | 5,256 | 5.3% |

The top three are about 42% of the budget. Full-coverage totals: **849 full
node-list scans, 12.9 per node** (the earlier 752/11.4 figure came from the
partial dump and is superseded).

### Where the cost is *not*

Ticks at the **call sites** of the scanning helpers total only **1.2%** of the
budget (child_at 0.3%, record_declaration 0.3%, type_shape_at 0.2%). Calling a
helper is cheap; the scan inside it is what is billed. So the lever is the number
of calls, never the cost of a call.

### Prototype 1: `if_expression` child lookups — no effect

Replacing the two `child_at` calls for an `if_expression` (then, else) with a
single `children_of` pass left the profile untouched, because **recpad-6 contains
no `if_expression` nodes**. A local optimisation on a path the fixture never
executes cannot move the ceiling. Recorded so the same dead end is not repeated.

### Prototype 2: guarding `declared_binding_type` — no effect

`declared_binding_type` scans for an `annotation` child on any non-parameter node,
although only `let` and `var` can carry that role. Adding a kind guard is
semantically safe (the role only exists for those kinds) — and produced a
**byte-identical profile** (849 scans, child_at 14,028 ticks). So that path is
not dynamically hot either; the wasted scans are real but rare.

Both prototypes were measurement-only in the scratch worktree and are reverted.

### What is still unknown

Which callers produce `child_at`'s ~200 scans is **not** attributable from
line-ticks, because the call itself costs one tick. Attribution needs per-call
counts keyed by function, not per-line ticks. Until that exists, further
reductions would be guesses — and two guesses have now been measured as
worthless.

## Recommendation

The inference so far is replaced by a direct measurement. A scratch worktree at
`377ce9b` (`D:/Projects/wt-a1-profile`, deliberately not committed) instruments
`tick` to record ticks per source line and dumps the histogram when the budget
expires. Nothing in the mission worktree is instrumented.

One 66-node check consumes the full 100,001 steps across 505 distinct checker
lines. Ticks by enclosing function (top entries; the dump covers the 60 hottest
lines, 74.3% of all ticks, so these are lower bounds):

| function | ticks | share |
|---|---|---|
| `child_at` | 13,836 | 13.8% |
| `type_shape_at` | 12,732 | 12.7% |
| `type_analysis` | 8,462 | 8.5% |
| `record_declaration` | 5,752 | 5.8% |
| `lookup_node` | 5,256 | 5.3% |
| `tree_is_valid` | 5,178 | 5.2% |
| `collect_bindings` | 3,093 | 3.1% |
| `count_children` | 2,880 | 2.9% |
| `is_expression_kind` | 2,560 | 2.6% |
| `is_constructor` | 2,320 | 2.3% |

`is_expression_kind` at 2.6% independently confirms the earlier sensitivity
result that it is not worth changing.

### The number that defines the architecture decision

Each scan-loop condition costs roughly one tick per node, so dividing by the
66 nodes gives the number of full node-list scans:

| line | function | ticks | ≈ full scans |
|---|---|---|---|
| 2454 | `child_at` | 12,086 | 183 |
| 2430 | `type_shape_at` | 8,378 | 127 |
| 2527 | `record_declaration` | 5,752 | 87 |
| 2444 | `lookup_node` | 5,256 | 80 |
| 2431 | `type_shape_at` | 3,249 | 49 |
| 2449 | `count_children` | 2,880 | 44 |
| 2523 | `is_constructor` | 2,320 | 35 |

**Total: roughly 752 full scans of the node list — 11.4 scans per node** for a
66-node program.

Caveat, stated honestly: pass counts assume one tick per loop iteration, so they
are approximations; the ordering and order of magnitude are solid, the exact
figures are not.

### What this settles

The cost is not one slow helper but **~11 full passes per node**, each answering
a single question (find the k-th child, find a node by id, find a declaration by
name, count children). Lifting the ceiling therefore requires answering those
questions in far fewer passes — precomputing per-node facts once — which needs
indexed access the language does not have.

That is the architecture decision, and it now has a number attached: reduce ~11
passes per node toward 1, or accept the current whole-program ceiling while
continuing to use staged checking for real modules.

## Recommendation

Do not add lookup primitives. The staged path remains the supported route for
real modules (107 of 107 functions in `stdlib/collections.pep`), and lifting the
whole-program ceiling needs a deliberate decision on analysis architecture:

1. collapse the per-node predicate chains (`is_expression_kind` and peers) into
   a single comparison or a precomputed classification;
2. reduce the number of full passes over `nodes` per analysis;
3. only then re-measure the ceiling and decide whether further work is warranted.

Each step must show a before/after ceiling measurement on recpad-6, so progress
is evidence rather than assertion.
