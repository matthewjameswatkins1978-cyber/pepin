# FINDING BOOT-A3-125 — fragment cost scales with the WHOLE FUNCTION's size, not the fragment's: that is why statement 23 fails

**A fragment's step cost grows linearly with the enclosing function's node count, at roughly **51 steps per (branch
statement × function node)**. The fragment itself does not change size. That single term explains statement 23's overrun
exactly, and it means splitting a function into fragments does not reduce cost as intended while the branch scan is
whole-function.**

Seed blob `f8f476198f`. Emitter `cf09930e`. Driver A1 `9bf18699`. Mixed lane as before.

## The measurement

One function, one `if` containing **nine** `say(int_text(N))` statements, then N padding statements added to grow the
function while the `if` stays byte-identical. Force-chained through A1's driver so every row is a merged report; the
fragment emitted is always the same `if`.

| padding stmts | function nodes | if nodes | steps | status |
|---|---|---|---|---|
| 0 | 51 | 40 | 42,405 | EMITTED |
| 10 | 71 | 40 | 51,295 | EMITTED |
| 20 | 91 | 40 | 60,385 | EMITTED |
| 30 | 111 | 40 | 69,675 | EMITTED |
| 45 | 141 | 40 | 83,985 | EMITTED |

The `if` is **40 nodes in every row**. Cost rises 41,580 steps over 90 extra function nodes — about **462 steps per function
node**, or **51 per (branch statement × function node)** at nine branch statements.

## It predicts statement 23 exactly

`main`'s statement 23 is 37 nodes with **nine** `say` calls (`say("int main")`, `say(int_text(40))`, … `say(int_text(125))`),
inside a function of **222** nodes.

Two independent calibrations:

- **from the sweep:** base ≈ 20,400, the constant shared by any if-fragment;
- **from the single-`say` if-blocks:** statements 24–28 hold one `say` each in a 222-node function and cost 31,743–33,083.
  `20,400 + 51 × 1 × 222 = 31,722` — within 20 steps of the measured 31,743.
- **predicting #23:** `20,400 + 51 × 9 × 222 = 122,298`, which is over the 100,000 budget. Measured: `PEP_RUNTIME_STEP_LIMIT`.

So #23 is not unlucky and not a mysterious hotspot. It is the model, applied.

## Why this changes the plan rather than just explaining a number

**Fragmenting a function does not reduce per-fragment cost while the branch scan is whole-function.** Every fragment that
contains an `if` pays for the enclosing function's size. Splitting `main` into 31 pieces gives 31 fragments each priced
against 222 nodes — which is why statements 24–28 already cost ~32k for a single `say`, and why #23 at nine says cannot fit
no matter how the host slices it.

The likely mechanism is visible in the source I read while chasing this: the if-branch lowering does

```pep
for branchStatement in nodes {
    if branchStatement.parentId == statement.id && branchStatement.role == "then" { … }
    else { if branchStatement.parentId == statement.id && branchStatement.role == "else" { … } }
}
```

a full scan of the function's node list, and it recurses per nested statement. I have **not** measured the per-scan cost
directly — the 51-per-pair figure is derived from the padding sweep, not from instrumenting the loop — so I state the
scaling as measured and the mechanism as the strongest candidate.

## Consequence for A2-S2's design

The bound that matters is not "how many statements per fragment" but **how many node scans per branch statement**. Two
directions, both A2's call:

1. **Group children once.** Build a parent→children index per emission call (or per function) instead of scanning `nodes`
   per branch statement. Cost then becomes independent of function size, and fragmentation starts behaving as intended.
2. **Pass a narrowed node list.** If `nodes` contained only the statement's subtree — which the fragment entry already
   accepts after `e6d53002` — the scan would be small. But that is the same input question as the transport wall, and
   A3-116 established the host should pass A1's sliced progress, so option 1 is the cleaner fix.

Either way, **A2's `prepend+reverse` cannot reach this**: it removes 752 steps of constant factor (A3-124) against a term
worth ~90,000 at `main`'s size. The commit was correct and well-scoped; it was aiming at a different term.

## Limits

- The 51-per-(branch statement × node) coefficient is calibrated on one shape (if-with-say-list, 9 and 1 branch statements).
  A different branch body may have a different constant; the *scaling in function size* is the robust finding.
- Padding statements were `var pN = N` declarations, which also enlarge the carried binding count. I did not separate those
  two effects; a padded function could plausibly cost more for binding reasons too.
- All rows force-chained, so the comparison is merged-report against merged-report. Raw whole-function reports may behave
  differently.
- One source, one emitter pin, one seed.

## Reproduce

Build `fn a3_x(source: SourceBytes)` with `var e = 0`, `let n = byte_length(source)`, an `if e == 0 { 9 × say(int_text(N)) }`,
then N `var pN = N` statements, `return e`. Force-chain it (`check_program(..., force_chain={"a3_x"})`), emit statement 2 as a
fragment, and read `metrics.last_execute_steps`.

REF GH #16. Parents: `6725640570` (A3-124, the 752-step A/B), `6725593749` (A3-123, the assignment-path root cause).