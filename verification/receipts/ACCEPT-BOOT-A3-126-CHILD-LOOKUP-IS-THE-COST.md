# ACCEPT BOOT-A3-126 — mechanism confirmed: `pep_c23_child` scans every node per lookup, and that single helper is the cost

**The measured law has a one-function cause. `pep_c23_child` is a linear scan of the function's entire node list for every
child lookup, so a fragment's cost is (child lookups) × (function nodes) × ~12 steps. Each `say(int_text(N))` makes about
3–4 such lookups. That is why statement 23 cannot fit, and it is one helper away from being fixed for every function at
once.**

Seed blob `f8f476198f`. Emitter `cf09930e`. Driver A1 `9bf18699`.

## The helper

```pep
fn pep_c23_child(nodes: List[FlatAstNode], parentId: Int, role: Str, wantedIndex: Int) -> PepC23NodeLookup {
  for node in nodes {
    if node.parentId == parentId && node.role == role && node.childIndex == wantedIndex {
      return PepC23NodeLookup { found: true, node: node }
    } else {}
  }
  return PepC23NodeLookup { found: false, node: pep_c23_empty_ast_node() }
}
```

One full scan per lookup, no index, no cache. Every expression and statement lowering calls it. Its sibling
`pep_c23_ordered_children` even carries a comment about avoiding a "count-plus-indexed-lookup loop" because it "measurably
inflates emitter step cost on large programs" — the same concern, addressed there and not here.

## The second dimension, measured at near-constant function size

Padding fixed at 85 statements, varying only the number of `say(int_text(N))` inside one `if`, force-chained:

| says | fn nodes | if nodes | steps | increment |
|---|---|---|---|---|
| 1 | 189 | 8 | 38,753 | — |
| 2 | 193 | 12 | 47,765 | 9,012 |
| 3 | 197 | 16 | 57,259 | 9,494 |
| 4 | 201 | 20 | 67,235 | 9,976 |
| 6 | 209 | 28 | 88,633 | 21,398 for two (≈10,699 each) |

Each extra `say(int_text(N))` costs **~9,000–10,700 steps** at this size. The increments creep upward because each say also
adds four nodes; netting that out with A3-125's ~462 steps/function-node leaves ≈7,200 steps per say attributable to the say
itself, i.e. **~36 steps per (say × function node)**.

With ~12 steps per node visit (a loop iteration with two field comparisons), that is **3–4 child lookups per `say`** —
say's argument, `int_text`'s argument, and the enclosing expression statement's value.

## The law, and statement 23

```
cost ≈ base + ~36…51 × (child lookups) × (function nodes)
```

For `main`'s statement 23 — nine `say` calls in a 222-node function — about 33 child lookups × 222 nodes × 12 ≈ 88,000, plus
a base near 20,400, gives ~108,000 against a 100,000 budget. Measured: `PEP_RUNTIME_STEP_LIMIT`. The padding sweep and the
say sweep together produce this from two independent directions, and A3-125's cross-check on statements 24–28 (predicted
31,722 vs measured 31,743) closes it.

## This explains more than statement 23

The same helper carries the whole-function emission cost too. `is_int3` — 41 nodes — costs 90,354 steps to emit, which is
~2,200 per node; that is not a per-node constant, it is ~180 child lookups × 41 nodes × 12. So the "expensive functions"
wall, the fragment wall, and statement 23 are **one cause**: a linear child lookup called from every lowering site.

## The fix, and why it is one change rather than many

Index children once per emission call — a `parentId → children` map, or a `(parentId, role) → ordered children` list — and
every `pep_c23_child` becomes O(1). The `× function nodes` factor then disappears entirely:

| shape | now | with an index |
|---|---|---|
| statement 23 | ~108,000 (refused) | ~few thousand |
| statements 24–28 | ~32,000 | ~2,000 |
| `is_int3` whole-function emit | 90,354 | ~2,000 |

That is a ~50× reduction at `main`'s size, and it grows with the program — which is exactly the wrong direction for a
self-hosting compiler that must read its own 9.6 KB source.

`pep_c23_ordered_children` already shows the pattern of a single pass; the change is to generalise it, not to invent an
index. It is A2's call, and it is the highest-leverage emitter change available: it removes the term that makes both
fragmentation and whole-function emission fail.

## What I did not measure

- The **12 steps per node visit** is inferred from the two sweeps, not instrumented inside the loop. The product law and the
  3–4 lookups per say are measured; the per-visit constant is derived.
- The coefficient varies by shape (36 at the say-sweep size, 51 at A3-125's), so I give a range rather than a constant.
- Padding statements were `var pN = N`, which also enlarge the carried binding count; I did not separate that from the node
  count.
- I did not attempt the index myself. `tests/pep_c23_emitter.pep` is A2's file and A3 does not author what it verifies.

## Reproduce

Build `fn a3_x(source: SourceBytes)` with `var e = 0`, `let n = byte_length(source)`, an `if e == 0 { N × say(int_text(k)) }`,
85 `var pK = K` statements, `return e`. Force-chain, emit the `if` as a fragment, read
`metrics.last_execute_steps`. Vary N with padding fixed, then vary padding with N fixed.

REF GH #16. Parents: `6725672583` (A3-125, the scaling law), `6725640570` (A3-124, the 752-step A/B).