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

## Recommendation

Take B in two measured steps, smallest first:

1. positional access, to convert `lookup_node` (31 sites) from O(n) to O(1), and
   measure whether the 66-node ceiling moves at all;
2. only if that is insufficient, an associative capability for the 172
   name/kind-keyed sites.

Each step must show a before/after ceiling measurement. If step 1 alone does not
move the ceiling — plausible, given the ablation showed migration between
scanners — then the honest conclusion is that whole-program checking at this
scale needs a different analysis architecture, not more primitives, and that is a
design decision to be taken explicitly.
