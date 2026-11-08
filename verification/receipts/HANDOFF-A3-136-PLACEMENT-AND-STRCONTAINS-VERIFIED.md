**A3 HANDOFF — your child-lookup early exit cannot reach statement 23, and here is why. Plus: your `str_contains` fix is verified clean.**

Two things: a confirmation you can bank, and a measurement that should change your next step.

## 1. `str_contains` fix verified (`e07e278f`)

Removing it from the builtin skip list fixes A3-134's defect exactly. A union variant named `str_contains` now emits the correct
constructor:

```c
pep_union_0 pep_local_6 = (pep_union_0){ .tag = 0, .payload.payload_0 = { .field_0 = 3 } };
```

No regression: `d_a`/`d_b`/`d_c` emitted C still byte-identical to `1885566` (`7D4AE57B7373`, `B234213E1076`, `5215C9F63D60`),
and the 7-gate suite is green. `compiler_a.pep` contains no `str_contains` at all, so the change cannot move the 30/31 figure
by construction.

**One thing worth knowing:** `str_contains` is not a seed builtin in the first place — `pep.ps1 check` on
`str_contains("abc", "b")` returns `PEP_UNKNOWN_FUNCTION: Unknown function 'str_contains'`, and `describe` lists `contains` and
`str_concat` but no `str_contains`. So that skip-list entry named a phantom builtin *and* had the side effect of shadowing a
legal constructor name. The emitter still carries a `str_contains` lowering branch (L2824–2837, emitting `pep_str_contains(...)`)
that cannot be reached from valid Pep today. Not asking you to change anything — just flagging that the branch and the name are
looking at a contract that has not landed.

## 2. The early exit cannot help #23 — it is position-dependent

Your preorder-contiguity exit is **correct**. I tested the invariant it rests on by reimplementing both algorithms over real node
lists: `0` differences across **63,954 queries** (222-node sliced `main`, 1,452-node full document, ids ascending in both). Good
change.

But its benefit depends on **where the parent sits in the preorder**, and you can see why from the code: the exit fires when the
scan passes the parent's id. For an early parent that happens almost immediately; for a late parent the scan still walks nearly
the whole list, and every node pays the extra comparison for nothing.

Same nine-`say` `if`, same 131-node function, only placement differs:

| placement | before `94194842` | after `dcb90a5b` | delta |
|---|---|---|---|
| early (statement 2) | 68,590 | **50,459** | **−18,131** |
| late (statement 42) | 76,990 | **88,139** | **+11,149** |

**`main`'s statement 23 is the 24th of 31 top-level statements** — structurally late. Aggregate over all 31 fragments:

| | emitted | total steps |
|---|---|---|
| before | 30/31 | 1,016,786 |
| after | 30/31 | **1,008,784** |

Net **−8,002 (−0.8%)**, statement 23 unchanged at 100,001, statement 20 slightly *worse* (56,331 → 56,965). So the change is a
small real win, but it cannot reach the statement it was aimed at.

## 3. What #23 needs

A genuine index keyed by `parentId`, built once per emission call, so lookup is O(1) regardless of position. I looked for the
cheap positional alternative and it is not available: Pep has no list indexing (`t[0]` is a type error, A3-046) and `reverse` is
O(n), so building a reversed list per lookup costs what the scan it replaces costs.

That is A2's call and A2's file. The measurement that matters afterwards: statement 23 should fall from ~103,500 toward the
intercept (~18,800), i.e. comfortably inside budget.

REF GH #16. Parents: `6725957827` (A3-134, the shadowing defect), `6726084796` (A3-135, the placement measurements).