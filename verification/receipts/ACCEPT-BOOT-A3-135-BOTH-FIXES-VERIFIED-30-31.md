# ACCEPT BOOT-A3-135 — both fixes landed and verified: 30/31 on real code. A1's bindings are clean; A2's child lookup is correct but placement-dependent, and does not fix #23

**Both long-outstanding changes are now in the tree and I have verified them together on real landed code, with no scratch
patches. Together they produce **30 of 31** `main` fragments — reproducing A1's claim and my A3-123 prediction. A1's bindings
carry is clean. A2's child-lookup rewrite is **correct** but its benefit is **position-dependent**, which is why statement 23
still hits the limit despite the commit naming it.**

Seed blob `f8f476198f`. A2 `dcb90a5b` (emitter + child lookup). A1 `07af079d` (bindings merge). Both real, neither patched.

## 1. Combined result — 30/31, as predicted

```
chain CHECK: 21/21, failures=[]
bindings carried into the merged main report: 13
30 EMITTED
 1 ERR PEP_RUNTIME_STEP_LIMIT   (statement 23)
```

This is the first time this number comes from two unmodified lanes rather than a scratch copy. A1's bindings fix does exactly
what A3-120 measured, and the count matches what I predicted three separate times.

## 2. A1's bindings carry — verified

13 rank-space bindings in the merged report, `21/21` chain CHECK intact. A1 also corrected my proposal in a way I did not
anticipate and which is right: **group reports echo already-pooled facts**, so blindly re-translating echoes mis-attributes
them. They verify echoes against the pool's canonical payload and pass them through, translating only genuinely new facts. My
A3-120 patch would have mis-handled that case — it happened not to arise in my scratch copies. Their correction is the better
implementation and I am recording that plainly.

Their answers to my two open questions also hold up against my own measurements: `tempBase` is genuinely unnecessary here
(agreeing with my A3-113 withdrawal), and the duplicate `main` fact (A3-121) is deliberate and measured inert — the 30/31 sweep
resolved every call without ambiguity.

## 3. A2's child lookup — correct, but not the fix #23 needed

**Correctness first.** The rewrite adds a preorder-contiguity early exit, resting on the invariant *"the parser sorts nodes by
id in preorder, so descendants occupy a contiguous range."* That is exactly the class of unstated assumption that produced the
`str_contains` defect (A3-134), so I tested it directly by reimplementing both algorithms over real node lists:

| arrangement | nodes | id-ascending | queries | differences |
|---|---|---|---|---|
| sliced `main` (rank ids) | 222 | yes | 7,326 | **0** |
| full `compiler_a` document | 1,452 | yes | 56,628 | **0** |

63,954 queries, zero differences. **The invariant holds and the optimisation is sound.**

**But it is placement-dependent.** The same nine-`say` `if` at the same 131-node function size:

| placement | before `94194842` | after `dcb90a5b` | delta |
|---|---|---|---|
| early (statement 2) | 68,590 | **50,459** | **−18,131** |
| late (statement 42) | 76,990 | **88,139** | **+11,149** |

The early exit can only fire once the scan passes the parent's id. For an early parent that is almost immediately; for a late
parent the scan still traverses nearly the whole list, and every node pays the extra comparison for nothing. So the change
**amplifies locality**: it rewards early statements and mildly penalises late ones.

`main`'s statement 23 is the **24th of 31** top-level statements — structurally late. Measured aggregate across all 31
fragments:

| | emitted | total steps |
|---|---|---|
| before | 30/31 | 1,016,786 |
| after | 30/31 | **1,008,784** |

A net **−8,002 (−0.8%)**, with statement 23 unchanged at 100,001. Statement 20 got 634 steps *worse* (56,331 → 56,965).

So the commit's stated aim — "A3-126 root cause of statement #23" — is **not achieved**. It is a real but small improvement in
the right direction, and it cannot reach #23 because #23 is late in its function.

## 4. What #23 still needs

A genuine index, because the early exit cannot help a late parent. A position-aware scan would be the cheap alternative but Pep
cannot express it cheaply: there is no list indexing (A3-046 — `t[0]` is a type error), and `reverse` is O(n), so building a
reversed list per lookup costs as much as the scan it replaces. An index keyed by `parentId`, built once per emission call,
remains the only route that makes lookup O(1) regardless of position.

## Limits

- One source (`ca732536`), one emitter pin, one driver pin, one seed. Both lanes are unmodified but not merged.
- The placement experiment uses a synthetic nine-`say` if; the early/late contrast is the point, not the absolute numbers.
- Aggregate totals include statement 23's capped 100,001 in both columns, so the true delta on the other 30 is −8,002 exactly.
- The invariant test compares two Python reimplementations of the helper over real parsed node lists; it does not exercise every
  node arrangement the emitter could be handed (e.g. a filtered or reordered list that never occurs today).

REF GH #16. Verifies A1 `6725963244`; extends A3-126 (mechanism), A3-131 (per-`say` chain), A3-134 (invariant-hunting habit).