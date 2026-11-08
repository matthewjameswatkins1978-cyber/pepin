# ACCEPT BOOT-A3-147 — find_brace's last three are 5-conjunct conditions; 3-conjunct ones emit. A4 predicted this exactly.

**Pruning the declaration set from 50 to 42 nodes does not close `find_brace` 14–16 — they still exceed the budget. But reading
the actual statements shows why, and it is not a cost-tuning problem: they are **five-conjunct** `&&` conditions, while the
three-conjunct ones in the same function now emit. That is precisely the limit A4's `EXPECTED.md` predicted.**

Seed blob `f8f476198f`. A2 `e07e278f`. A1 host `07af079d`. Per-statement narrowing as in A3-146.

## The statements, from `compiler_a.pep`

```pep
if e0 == 0 && err == 1 && is_str3(source, o) == 1 {                 // 3 conjuncts  -> EMITS
if e0 == 0 && err == 5 && is_str3(source, o) == 1 &&
   is_ws_at(source, o + 3) == 0 && expect_byte(source, o + 3, 123) == 0 {   // 5 conjuncts -> LIMIT
if err == 0 && expect_byte(source, o, 123) == 123 {                 // 2 conjuncts  -> EMITS
```

Measured at narrowed node counts:

| statement | conjuncts | narrowed nodes | steps | outcome |
|---|---|---|---|---|
| `find_brace` #19 | 2 | 30 | 25,126 | emits |
| `find_brace` #11–13 | 3 | 33 | 36,634 | emits |
| `find_brace` #14–16 | **5** | 42 (pruned) / 50 (full decls) | **100,001** | **LIMIT** |
| `main` #23 | 1 | 85 | 61,572 | emits |

## This corroborates A4's own prediction

A4's `EXPECTED.md` lists as **refusal candidate #1**: *"`is_main4` 5-conjunct `&&` (proven max is 3 in A1's `is_fn_at`)"* — and
its stated fallback ladder is *"split long-`&&` into 3-byte atoms"*.

Measured on real code: **three conjuncts emit, five do not, in the same function, at comparable narrowed sizes.** The predicted
maximum is the observed maximum. And `is_main4` itself — the specific function A4 named — does emit, because its five conjuncts
were rewritten as four `byte_at` comparisons plus a length guard, a shape that fits.

So the remedy for `find_brace` 14–16 is A4's documented one: **split the five-conjunct conditions**, not an emitter change and
not an index. That is a source decision in A4's lane.

## What pruning established

Referenced-name pruning took the declaration contribution from 17 nodes to 9 (50 → 42 nodes total) and changed the outcome not
at all: still `PEP_RUNTIME_STEP_LIMIT`. So the declaration set is not the lever here — the conjunction depth is. Worth recording
because it is the opposite of the intuition that smaller input is always cheaper: at 42 nodes the statement is already lean, and
the cost is coming from the expression's shape.

## A harness failure I am not going to paper over

I tried to measure this synthetically — N conjuncts of cross-chunk calls in a generated function — and could not get it right in
this turn. First it used `is_digit`, which is a `compiler_a` function rather than a seed builtin, so the seed rejected the
program. Then, with a defined helper, my `functionIndex` selected the helper rather than the target function, giving
`statement fragment range is out of bounds` in ~80 steps. Both were my errors, not the emitter's.

The finding above does not depend on that experiment: it comes from `compiler_a.pep`'s own statements, measured at three
conjunction depths. I would rather state the synthetic attempt failed than present a fourth guessed number.

## Standing state

- **`main`: 31/31** statements emit by narrowing (A3-146). Unchanged.
- **`find_brace`: 21/24**; the three failures are 5-conjunct conditions.
- **All 21 functions**: 10 emit as whole units, 9 emit every fragment, `find_brace` 21/24, `main` 31/31. So **19 functions are
  fully assemblable and `main` is too** — a complete compiler A needs only `find_brace`'s three statements, which is a source
  rewrite in A4's lane.

## Limits

- One source, one emitter pin, one driver pin, one seed; mixed lanes.
- Conjunct count and node count both differ across the compared statements, so the correlation is observed, not isolated. The
  decision-relevant fact is simply that 5-conjunct conditions fail where 2- and 3-conjunct ones succeed.
- Not yet tested: whether splitting a 5-conjunct condition into a 3-conjunct plus a nested 2-conjunct emits. That is the change
  A4 would make, and it is testable as soon as such source exists.
- Still **no M-1 claim**.

REF GH #16. Parent: `6726440672` (A3-146). Corroborates A4's `EXPECTED.md` refusal candidate #1.