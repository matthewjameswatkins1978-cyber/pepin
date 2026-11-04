# Checker per-node cost: measurement and scoping

Status: measurement and scoping. No checker or host change is proposed here as
already-approved work. This note records what a per-node cost fix actually
requires, and which candidate fixes have been measured and rejected.

Revision measured: `0437a75` … `fd5380b` on `codex/p1-checker-cost-fix`.
Limits under measurement, unchanged throughout: 100,000 steps, 1 MiB JSONL
message, 65,536-byte source open.

## Why this exists

Staged checking already covers whole real modules under unchanged limits
(`stdlib/collections.pep`: 107 of 107 top-level functions; `examples/pep_lexer.pep`
mostly). The remaining failure class is per-node cost: the whole-program check
still expires at 62–66 nodes, and `lexer_step` has no split that passes.

## Census

| quantity | value |
|---|---|
| functions in the checker | 122 |
| whole-list scanners | 24 |
| direct callers of scanners (frontier) | 48 |
| call sites into the scan family | 203 |
| functions that would need an index parameter | 54 |
| call sites that would have to pass it | 221 |

Grouped by key shape:

| key shape | scanners | call sites |
|---|---|---|
| id-keyed (`lookup_node` only) | 1 | 31 |
| name/kind-keyed | 23 | 172 |

Largest name-keyed sites: `child_at` 71, `count_children` 21, `type_shape_at` 18,
`is_constructor` 13, `record_declaration` 12.

## Options, and the diff each implies

**A. Thread a precomputed index through the analysis.** 54 signature changes and
221 call-site edits across a 773-line `type_analysis`. Largest diff, highest risk
to diagnostic parity, which is itself an acceptance item. Not started.

**B. Host capability for indexed or associative node access.** `lookup_node` is
the only id-keyed scanner and flat AST ids are dense `0..n-1` and ascending
(verified 2030/2030 on `pep_lexer.pep`), so it would be O(1) with a one-line body
change. But that covers **31 of 203** call sites (15%); the other 172 are keyed
on `(parentId, role, childIndex)` or `(kind, text)`.

**C. Accept the current ceiling.** Staged verification covers real modules;
whole-program checking beyond ~62 nodes stays unavailable.

## The constraint that rules out an in-Pep index

Pep has no list indexing and no map/dictionary. A hand-rolled index is a
`List[...]` searched by the same linear scan it was meant to replace, and binary
search is impossible without positional access. **No in-Pep structural index can
beat O(n).** Any real fix therefore depends on a host or language-surface
capability, and should be taken deliberately.

## Upper bound: no lookup primitive can lift the ceiling

Stubbing `lookup_node`, `record_declaration`, `union_declaration`,
`variant_declaration` and `is_constructor` to constants (diagnostic only, never
shipped) still leaves the 66-node program over budget, and the failure leaves the
lookup family entirely:

| program | nodes | expires in (all lookups stubbed) |
|---|---|---|
| recpad-6 | 66 | `is_expression_kind` |
| recpad-8 | 88 | `empty_node` |
| recpad-10 | 110 | `resolve_all_records` |
| recpad-12 | 132 | `type_shape_at` |
| recpad-16 | 176 | `collect_bindings` |
| recpad-20 | 220 | `collect_functions` |
| recpad-24 | 264 | `count_children` |

Caveat: each stub still builds a `NodeLookup` and calls `empty_node()`, so this
is not a perfect "free" model. It is decisive in direction.

Two further reasons no host primitive was added: builtins are deliberately
charged per element of work (`reverse` ticks per head, `byte_slice` per byte), so
a positional lookup over a list would either tick per element with no gain or
break the accounting model; and even granting a free lookup family the ceiling
holds.

## Sensitivity test: the predicate chain is not the cost

`is_expression_kind` has 13 string comparisons and one call site. Duplicating the
disjunction is logically identical, so only ticks change. Boundary is k=5 (55
nodes, valid) / k=6 (66 nodes, over budget):

| variant | k=4 | k=5 | k=6 | k=7 |
|---|---|---|---|---|
| baseline 1x | valid | valid | STEP_LIMIT | STEP_LIMIT |
| doubled 2x | valid | valid | STEP_LIMIT | STEP_LIMIT |
| quadrupled 4x | valid | valid | STEP_LIMIT | STEP_LIMIT |

Nothing moves with ~78 extra ticks per call, so collapsing the chain is not the
lever and was not done. A stubbed `return true` variant was tried and **discarded
as evidence**: it changes semantics and makes the ceiling worse. Semantics-changing
ablations distort cost in both directions.

## Instrumented profile (ticks per source line)

A scratch worktree (`D:/Projects/wt-a1-profile`, detached, deliberately not
committed) instruments `tick` to record ticks per source line and dumps a
histogram when the budget expires. The mission worktree is never instrumented.

One 66-node check consumes all 100,001 steps across 505 checker lines, with
complete attribution:

| function | ticks | share |
|---|---|---|
| `type_analysis` | 14,470 | 14.5% |
| `child_at` | 14,028 | 14.0% |
| `type_shape_at` | 13,538 | 13.5% |
| `tree_is_valid` | 7,062 | 7.1% |
| `record_declaration` | 5,752 | 5.8% |
| `lookup_node` | 5,256 | 5.3% |
| `collect_bindings` | 3,798 | 3.8% |
| `scope_chain` | 3,684 | 3.7% |

Top three are about 42% of the budget. `is_expression_kind` measures 2.6%,
independently confirming the sensitivity result above.

*(An earlier 60-line dump produced a partial table — `child_at` 13.8%,
`type_shape_at` 12.7%, `type_analysis` 8.5% — and a "752 scans / 11.4 per node"
figure. Both are superseded by the full-coverage numbers below.)*

## Per-call call graph

Line ticks cannot attribute call counts (a call costs one tick), so the
interpreter was instrumented a second time to count caller→callee edges;
`callstack` already carries function names. One 66-node run produced 75 edges and
800 user-function calls before the budget expired.

Callers of `child_at` (48 calls):

| caller | calls | share |
|---|---|---|
| `declared_binding_type` | 17 | 35.4% |
| `type_analysis` | 15 | 31.2% |
| `declared_return_type` | 10 | 20.8% |
| `collect_functions` | 6 | 12.5% |

Callers of `type_shape_at` (33 calls):

| caller | calls | share |
|---|---|---|
| `type_name_at` | 27 | 81.8% |
| `collect_functions` | 6 | 18.2% |

Most-called functions overall: `empty_node` 82, `validation_parent` 54,
`fixed_child_index` 54, `is_expression_kind` 52, `child_at` 48,
`legacy_type_name` 45, `type_shape_at` 33, `list_element_type` 28,
`type_name_at` 27, `record_declaration` 26.

## Correction: pass counts were overstated

Dividing ticks by node count assumed one tick per loop iteration. The call graph
shows that is wrong: `child_at` costs 14,028 ticks for 48 calls, about **292 ticks
per call**, and each call inspects up to 66 nodes — roughly **4.4 ticks per node
inspected**.

So 849 is a count of *node inspections*, not full traversals; full traversals are
closer to **~200**. The ordering of hot functions is unaffected, but the earlier
"11–13 passes per node" was an overstatement.

## Prototypes measured and rejected

**`if_expression` child lookups.** Replacing the two `child_at` calls with one
`children_of` pass left the profile untouched: recpad-6 contains no
`if_expression` nodes, so the optimised path never executes.

**Guarding `declared_binding_type` to `let`/`var`.** That function scans for an
`annotation` child on any non-parameter node, though only `let`/`var` carry that
role. The guard is semantically safe and produced a **byte-identical profile**
(849 inspections, `child_at` 14,028 ticks). The waste is real but rare — the call
graph explains why: `declared_binding_type` is called only 17 times.

Both prototypes were measurement-only in the scratch worktree and are reverted.

## What is established

- Cost is **diffuse**: no single predicate, lookup or helper moves the ceiling,
  and two candidate reductions measured as worthless.
- **Call count**, not call cost, is the lever (call sites are 1.2% of ticks).
- The top structural targets are `type_name_at` driving 81.8% of `type_shape_at`
  walks, and `empty_node` as the most-called function (82 calls, 13-field record
  each, also the miss path of every failed lookup).
- Every one of those fixes needs a cached or indexed result, which the language
  cannot express.

## Recommendation

Do not continue micro-optimising against fixtures. Either:

1. take the language/host decision — indexed or associative node access — and
   measure the ceiling afterwards; or
2. accept the current whole-program ceiling and keep staged checking as the
   supported route for real modules.

Option 2 is what already works today and is what the mission's "credible route
through larger real Pep modules" acceptance item rests on. Option 1 is a design
decision with language-surface consequences and should be taken explicitly.

Either way, any future attempt must show a before/after ceiling measurement on
recpad-6, and must first check the call graph to confirm the target is actually
on the executed path.
