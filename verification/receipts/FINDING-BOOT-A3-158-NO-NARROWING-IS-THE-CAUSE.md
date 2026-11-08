# FINDING BOOT-A3-158 — find_brace fails because the driver does not narrow; and it corrects my own A3-157

**Six controlled experiments through the real product path. The decisive one is in A1's own code: `build_fragmented_function`
passes the whole function slice and the whole report to every fragment, with the comment *"No narrowing: measured 30/31 on full
sliced progress."* That 30/31 was `main`. A3-146 measured that narrowing is what took `main` from 30/31 to **31/31** and gave
`find_brace` **21/24**; without it this candidate stops at statement **11**. My A3-157 conclusion — call-site multiplicity — is
wrong and is withdrawn.**

Seed blob `f8f476198f`. Candidate `b039fc5` + A4 `81dca2f4` in disposable worktree `D:\Projects\wt-a3-cand`; every experiment
reverted, worktree clean.

## The cause, in A1's source

```python
def build_fragmented_function(session, sem, sl, rep, name, sig_entry):
    """…whole sliced progress + whole merged report, rank-space ids throughout:
    no narrowing, no remap — measured 30/31 on the integrated tree."""
    ...
    for pos in range(len(order)):
        status, diag, parts, _ = emit_fragment(
            session, sem, sl, rep, 0, pos, 1)          # <-- whole slice, every fragment
```

and in `build_c23`:

```python
# function statement-by-statement through the fragment entry.
# (No narrowing: measured 30/31 on full sliced progress.)
```

Every fragment is emitted against the **whole** function's node list. So each fragment pays a full scan of find_brace's
~290 nodes — which is exactly the quantity A3-146 showed can be cut to a handful of nodes per fragment.

**Contrast, same emitter, same source, one variable:**

| driver | `main` | `find_brace` |
|---|---|---|
| no narrowing (this candidate) | 30/31 | **stops at statement 11** |
| per-statement narrowing (A3-146/147) | **31/31** | **21/24** |

## The six experiments

All through `python pep_c23.py build-c23 … --sectional`, one variable at a time.

| # | change | result | falsifies |
|---|---|---|---|
| 1 | apply A3-148 Bool-local to the three 5-conjunct conditions | still stmt 11 | that conjunct depth in *those* statements was the issue |
| 2 | swap statements 10 and 11 | refusal moved 11 → **10** | position as an independent driver |
| 3 | rename the callee in stmt 11 (`is_str3` → `is_int3`) | still stmt 11 | callee identity |
| 4 | rename the callee in stmt 10 (`is_int3` → `is_str3`) | still stmt 11 | callee identity (reverse direction) |
| 5 | give `is_int3` a second call site | refusal at **11** (the duplicate) | my own A3-157 claim |
| 6 | reduce all three `err = 5` dispatches from 3 conjuncts to 2 | refusal moved 11 → **13** | — |

Experiment 6 shows conjunct count still matters **at the margin**: 3-conjunct forms fail at ~10–11, 2-conjunct ones survive to
~12–13. So the budget is crossed by *accumulated per-fragment scanning cost*, and a fragment's own size decides exactly where.

Also tested: **removing the three 5-conjunct statements entirely** did **not** help — still statement 11. So the cost depends on
what precedes a fragment, not on the function's total size. That is precisely the shape of "every fragment scans the whole node
list": deleting nodes *after* the failing statement changes nothing, while shrinking the per-fragment scan changes everything.

## The correction I owe

**A3-157 said the driver was callee call-site multiplicity, and recommended A2 index call facts per callee. That is wrong.**
Experiment 5 appeared to support it, but experiments 3 and 4 show renaming the callee changes nothing, and the refactor test
(recording which type word matched so each matcher is called once) moved the wall from 11 to 12 **only because it added four
statements**, not because it removed calls. I should have run the rename test before publishing. Withdrawn.

## What this means per lane

**A1 — the fix is yours, and it is the one A3-146 already measured.** In `build_fragmented_function`, per fragment pass a
`ParserProgress` narrowed to `{function node} ∪ {parameter subtrees} ∪ {var/let declaration subtrees} ∪ {target statement}`,
keeping `syntaxNodeCount` consistent, and compute the target's **position in the narrowed list** rather than assuming 0 — that
trap made my own first attempt emit a declaration while reporting success. `declared` for the carried-binding check must still
come from the full node set.

**A4 — you cannot fix this in source.**
Rewrite, reordering and call-multiplicity reduction all moved the wall by at most two statements. Structure changes only shift the
crossing point.

**A2 — not your seam,** contrary to A3-157. No emitter index change is needed to explain this.

## Limits

- Six experiments on one function at one revision; `main` was not re-measured here, its 31/31 figure is A3-146's.
- I did not implement the narrowing patch — that is A1's file and I do not certify my own fixes. The recipe is A3-146's, already
  measured there.
- Steps remain uninstrumented; "statement 11" is the observed crossing, not a step count.
- Gate verdict unchanged: compiler A cannot build at `b039fc5`+`81dca2f4`, and both epilogue defects remain.

REF GH #16. Corrects `6728237464` (A3-157). Related: A3-146 (the narrowing recipe), `6728167310` (A3-156).