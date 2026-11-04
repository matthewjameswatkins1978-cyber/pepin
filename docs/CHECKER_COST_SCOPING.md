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

## Decision evidence: how far can helper-level work possibly move the ceiling?

The planned prototype (an O(1) `child_at` behind a host builtin) was abandoned
mid-build. It needs either a new builtin registered across five checker sites
(`known_builtin`, return-type resolution, arity, two parameter-type rules) or
correct runtime record field ids for a hand-built `NodeLookup`; the first is too
much checker surgery for a measurement, and the second failed at
`PEP_RUNTIME_MISSING_FIELD` because field ids are not the positional 0/1 assumed.
Rather than keep fighting the plumbing, the same question is answerable from
measurements already taken.

### The arithmetic

- Budget: 100,000 steps.
- k=5 is 55 nodes and **valid**, so average per-node cost is at most
  100,000 / 55 ≈ **1,818 steps per node**.
- k=6 is 66 nodes and **fails**, consistent with cost growing superlinearly.

Measured shares of the 66-node budget:

| group | share |
|---|---|
| `child_at` | 14.0% |
| `type_shape_at` | 13.5% |
| `tree_is_valid` | 7.1% |
| `record_declaration` | 5.8% |
| `lookup_node` | 5.3% |
| `collect_bindings` | 3.8% |
| `count_children` | 2.9% |
| **all scanning helpers** | **≈ 52%** |

### What each option could buy

| intervention | steps freed at 66 nodes | ceiling equivalent |
|---|---|---|
| free `child_at` alone | ~14,000 | ~62 → ~70 nodes |
| free every scanning helper | ~52,000 | ~62 → ~90 nodes |
| free 90% of all cost | ~90,000 | ~62 → ~600 nodes |

Real modules are **2,030 nodes** (`pep_lexer.pep`) and **2,901 nodes**
(`collections.pep`), and the checker itself is larger still.

### Conclusion

Even removing **every** whole-list scanner — which is the most generous possible
outcome of indexed access — moves the ceiling from ~62 to ~90 nodes. That is a
45× shortfall against a real module. So **indexed node access is not the fix**,
and the language/host capability question does not need to be decided on this
evidence.

The per-node constant itself (≈1,800 steps per node) has to fall by roughly 50×
to make whole-program checking of real modules possible. That is a change in
asymptotic behaviour — fewer interpreted operations per node — not a faster
lookup. Cross-checking: staged checking already achieves the goal by bounding the
*number of nodes per unit* instead, which is why it covers 107/107 functions of a
2,901-node module today.
## Recommendation

The arithmetic above settles the open question: indexed or associative node
access is **not** the fix. Even freeing every whole-list scanner — the most
generous possible outcome — moves the ceiling from ~62 to ~90 nodes against real
modules of 2,030–2,901 nodes. The language/host capability question therefore
does not need to be decided on this evidence, and no primitive is proposed.

What remains is one of two honest positions:

1. **Accept the current whole-program ceiling** and keep staged checking as the
   supported route for real Pep modules. This is what already works: 107/107
   top-level functions of a 2,901-node module, with byte-identical ingress for
   modules above the per-open cap. Staging bounds *nodes per unit* instead of
   lowering per-node cost.
2. **Treat whole-program checking at this scale as an architecture change** worth
   doing deliberately: the per-node constant (≈1,800 steps per node) must fall by
   roughly 50×, which means far fewer interpreted operations per node — a
   restructured analysis, not a faster lookup, and not a local optimisation.

Accepting (1) is not a failure state: the mission's "credible route through
larger real Pep modules" is satisfied by staging plus ingress. The whole-program
66-node gate remains genuinely unmet, and that should be stated as such rather
than papered over.

Any future attempt must:

- show a before/after ceiling measurement on recpad-6;
- check the call graph first, to confirm the target is on the executed path (one
  prototype failed purely because recpad-6 never enters `if_expression` code);
- be semantics-preserving — stubbed ablations distort cost in both directions and
  have twice produced misleading results.
