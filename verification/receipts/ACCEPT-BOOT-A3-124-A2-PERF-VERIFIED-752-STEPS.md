# ACCEPT BOOT-A3-124 — A2's prepend+reverse saves exactly 752 steps on the targeted shape; statement 23 is unchanged and needs ~3x

**A2's `cf09930e` perf commit is real, correctly scoped and measurable: it removes **exactly 752 steps** from each of the five
single-`say` if-blocks in `main` and changes nothing else. It does not touch statement 23, which remains at the limit. So the
fix is a genuine improvement whose headroom (0.75% of budget) is far short of what #23 needs.**

Seed blob `f8f476198f`. Emitter `651d9124` → `cf09930e`. Driver A1 `9bf18699`.

## A/B of the perf commit, per statement

Same source, same driver, same seed; only the emitter pin differs.

| stmt | `651d9124` | `cf09930e` | delta |
|---|---|---|---|
| 24 `if err == 1 { say("ERR shape") }` | 32,495 | 31,743 | **−752** |
| 25 `if err == 2 { say("ERR literal") }` | 32,841 | 32,089 | **−752** |
| 26 `if err == 3 { say("ERR junk") }` | 33,077 | 32,325 | **−752** |
| 27 `if err == 4 { say("ERR longlit") }` | 33,445 | 32,693 | **−752** |
| 28 `if err == 5 { say("ERR unsupported") }` | 33,835 | 33,083 | **−752** |
| **23** `if err == 0 { say(…) ×6 }` | **100,001 LIMIT** | **100,001 LIMIT** | **0** |
| all 26 other statements | — | — | **0** |

An identical 752-step saving on all five, and zero change everywhere else. That is the signature of a fix that addresses
precisely the code path it names — the if-branch body assembly — and nothing adjacent. Credit where due: it is hard to land a
perf change with that clean a footprint.

## Why it is not enough

752 steps is **0.75%** of the 100,000 budget. Statement 23 is a *single* top-level statement of **37 nodes** that already
exceeds the budget, so it needs a reduction of at least a third, not three quarters of one percent. The sibling if-blocks give
the scale: one `say` inside an if costs ~31,700 steps. #23 holds six says plus the same if overhead, and if the cost were
merely additive it would land near 40,000 — it does not, so something in #23's lowering is superlinear in the number of
branch statements.

I have not isolated that superlinearity. The if-branch lowering scans `for branchStatement in nodes` — every node of the
function — for each if, and recurses per nested statement; on a 42-node branch list inside a 222-node function that is a
plausible source, but I have not measured it and will not claim it.

## A separate gap found while checking this

**`say` is not supported as a top-level statement fragment.** Measured directly:

```
WHOLE-FUNCTION with say(int_text(40)):   EMITTED
FRAGMENT [0,1) of that say statement:    unsupported
    "Pep C23 statement fragment does not support this statement kind"
```

Nested `say` **is** supported — statements 24–28 are ifs containing a `say` and they emit — so the gap is specific to a `say`
appearing as a direct top-level statement of the function. `compiler_a.pep` does not have that shape (its says are nested in
`main`'s if, and A4's census finds string literals in `main` only), so this does not block M-1. It would block any future
program that prints at function top level, and it is cheap to state now rather than discover later.

## Full per-statement profile at `cf09930e`

Useful for anyone planning the remaining work — 18 emit, 12 refuse for the known bindings/assignment reasons, 1 is over
budget:

```
 0:6111  1:6813  2:6903  3:6993  4:7083  5:22778  6:30597*  7:31129*  8:33840
 9:45969* 10:34308 11:48104* 12:33943* 13:34962 14:51095* 15:52467* 16:6767
17:28708* 18:39826* 19:6925 20:30070* 21:36770 22:29204* 23:100001! 24–28:~32k
29:29259* 30:12275        (* refused for bindings/assignment, ! over budget)
```

Worst *emitting* fragment is 51,095 — so fragments generally have headroom; #23 is the outlier by a factor of two.

## Limits

- One source, one driver pin, one seed. The 752-step figure is this exact shape (one `say` in an if); a different branch body
  would save a different amount.
- Step counts are absolute readings of `metrics.last_execute_steps` after each `tool_invoke`, which A3-099 validated as
  per-invocation and repeatable.
- I did not measure A2's own test suite, only the emit behaviour on `compiler_a.pep`.
- Both pins measured with A1's merge unchanged, so statements 6–22 carry the known bindings refusals; that does not affect the
  step comparison, which is per-statement and independent.

REF GH #16. Emitter A2 `651d9124` → `cf09930e`; driver A1 `9bf18699`. Verification: A3.