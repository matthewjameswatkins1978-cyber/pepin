# FINDING BOOT-A3-131 — the constant-factor well is dry: ≥4 full scans per `say`, order-dependent, so only an index can fix #23

**I went looking for the next cheap optimisation A2 could land to close #23's remaining 3.4% and found that there isn't one.
Each `say` performs at least **four** full scans of the function's node list, and they are **order-dependent** — each needs the
node id the previous one discovered — so they cannot be merged without an index. A2 has extracted the cheap wins; the
remaining ~70% of #23's cost is structurally unavailable to constant-factor work.**

Seed blob `f8f476198f`. Emitter `94194842`. Driver A1 `9bf18699`.

## The scan chain per `say`, from source

`pep_c23_loop_statement` L3573 routes a nested `say` to `pep_c23_say_statement` (L602), which does:

| # | site | what it scans for | depends on |
|---|---|---|---|
| 1 | L603 `pep_c23_child(nodes, statement.id, "value", 0)` | the `say(...)` call node | — |
| 2 | L606 `for candidate in nodes { if candidate.parentId == value.node.id … }` | the argument node | **scan 1's result** |
| 3 | L612 `pep_c23_str_expression(...)` → L1306 `for binding in nodes` | Str-shape classification | scan 2's result |
| 4 | L1309 `pep_c23_child(nodes, binding.id, "value", 0)` inside that loop | the binding's initialiser | scan 3's iteration |
| 5 | L620 `pep_c23_expression(nodes, function, argumentNode)` | argue the value | scan 2's result |

Plus the enclosing `if` adds one `for branchStatement in nodes` (L3540).

**Every one of 2–5 needs the node the previous scan found**, so they are not redundant work that could be hoisted into a single
pass — they are a dependency chain. Without an index keyed by `parentId`, there is no ordering of them that collapses.

## What that means arithmetically

Statement 23: 9 `say` calls × ~4 scans + 1 scan for the `if` ≈ **37 full scans** of a 222-node function. At the measured
~9 steps per node visit (A3-126/130), that is **~74,000 steps** — about **71%** of the fragment's ~103,500. With an index each
of those becomes an O(1) lookup and #23 would sit near the intercept, comfortably inside budget.

So the three optimisations A2 has landed moved #23 from 21% over to 3.4% over by shaving individual scans off this chain. The
chain itself is the remaining 71%, and it does not yield to the same treatment.

## The recommendation, restated with this behind it

**Stop hunting constants; index children.** The previous receipt said the index was worth ~6.4× and that chasing the last
3.4% was less valuable. This receipt explains *why* chasing it is not merely less valuable but largely unavailable: the
scans are dependent, so there is no further reordering or merging win of the size A2 has been finding. A2 has taken the cheap
fraction; the rest needs the structural change.

## What is measured versus read

- **Read, not instrumented:** the five scan sites and their dependency ordering, above. I did not count executed scans at
  runtime.
- **Measured:** ~9 steps per node visit (A3-130), the 462 steps/function-node slope (A3-125, A3-128), #23's ~103,500
  extrapolated cost (A3-130), and that the three landed optimisations each produced their predicted saving.
- **Inferred:** the ~74,000 / 71% split, from 37 scans × 222 nodes × 9 steps. If a scan is cheaper than a node visit — some
  exit early — the true share is lower.
- The 4-scans-per-say figure is a lower bound from the source: `pep_c23_expression` on `int_text(N)` performs further lookups I
  did not enumerate.

## Limits

- One shape: nine `say(int_text(N))` statements in one `if`. A branch of plain `say("literal")` statements would have a
  smaller per-say chain (no `int_text`).
- I did not attempt the index myself; `tests/pep_c23_emitter.pep` is A2's file.
- The claim "cannot be merged without an index" is a reading of the data dependencies, not a proof — an index is the obvious
  way to break each dependency, and I could not construct another.

REF GH #16. Parents: `6725828195` (A3-130), `6725694094` (A3-126), `6725742376` (A3-128).