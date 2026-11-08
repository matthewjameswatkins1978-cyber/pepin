# ACCEPT BOOT-A3-130 — A2's builtin skip verified (saves 9 scans); `say` is not on that path, so #23 is now ~3.4% over, not fixed

**A2's `94194842` is a real and correctly scoped optimisation: skipping the union-variant scan for eight builtins removes nine full
node scans from a nine-`int_text` fragment, measured at **−4,095 steps at 51 nodes and −10,575 at 131**. But `say` is **not** on
that code path — adding it changes cost by 9 steps — so statement 23 is better but still over budget, by a much narrower
margin than before. My prediction that adding `say` would fix it was wrong.**

Seed blob `f8f476198f`. Emitter `3d9ac7d3` → `94194842`. Driver A1 `9bf18699`.

## The fix, verified

Nine `say(int_text(N))` statements inside one `if`, fragment emitted, force-chained:

| function nodes | before `94194842` | after | saving |
|---|---|---|---|
| 51 | 42,405 | **38,310** | −4,095 |
| 131 | 79,165 | **68,590** | −10,575 |

The saving scales with function size exactly as nine skipped scans should: 9 × 51 × ~9 ≈ 4,100 and 9 × 131 × ~9 ≈ 10,600. So
the commit removes one full node scan per `int_text` call, which is precisely what it says on the tin.

## My `say` hypothesis, disproved

The builtin list is `byte_length`, `byte_at`, `str_contains`, `str_concat`, `contains`, `length`, `utf8_slice`, `int_text` —
`say` is absent, and statement 23 makes nine `say` calls, so I predicted adding it would save another ~18,000 steps at `main`'s
size and bring #23 under budget.

I tested it in a scratch emitter with `say` added:

| function nodes | without `say` in the list | with `say` |
|---|---|---|
| 131 | 68,590 | **68,599** |
| 171 | — | 84,939 |
| 221 | LIMIT | **LIMIT** |

A 9-step difference is noise, and no size bracket changes outcome. **`say` does not reach that `node.kind == "call"` branch** —
it is lowered by its own statement path — so adding it to the list is inert. The prediction was reasonable from the source
shape and wrong in fact, which is why it was cheap to test before telling A2 to make the change.

## Where statement 23 now stands

Extrapolating the measured saving to `main`'s 222 nodes — 9 scans × 222 × ~9 ≈ **17,900** — the fragment goes from ~121,400 to
roughly **103,500 steps**. That is **about 3.4% over budget**, down from 21% over.

So the remaining gap is small, but it is not closed, and no single missing name closes it:

- the child index remains the structural fix (~6.4× at this size, A3-127);
- a targeted optimisation of the `say` statement path would need to recover only ~3,500 steps to unblock #23 as a stopgap,
  though it would not scale.

Worth saying plainly: **A2 has now landed three separate optimisations on this fragment** (`prepend+reverse` 752 steps,
the assignment fix, and this 17,900-step saving) and is 3.4% away. That is a good position, and the structural fix is
still worth doing rather than chasing the last 3.4% with more constants.

## Limits

- All figures are for a nine-`say`/nine-`int_text` fragment; other branch bodies scale the same way but with different constants.
- The 103,500 figure is an **extrapolation** from savings measured at 51 and 131 nodes; the fragment is capped at 100,001 so the
  post-fix cost at 222 nodes cannot be read directly.
- I did not verify that the eight listed names are all genuinely builtins with no union-constructor shadowing. If one of them
  could be a user union variant, skipping the scan there would be wrong — a risk for A2 to confirm, not something I checked.
- Scratch emitter removed; nothing written to A2's lane.

REF GH #16. Parents: `6725722100` (A3-127), `6725781947` (A3-129).