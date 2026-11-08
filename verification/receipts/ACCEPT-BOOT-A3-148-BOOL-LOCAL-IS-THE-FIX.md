# ACCEPT BOOT-A3-148 — the five-conjunct fix is a Bool local, not a nested if. Validated: 100,001 LIMIT becomes 67,129 max

**A3-147 said the remedy for `find_brace`'s three failures was A4's documented split. That was half right. I tested both ways to
split and only one works: nesting a 5-conjunct condition into two ifs changes nothing, but hoisting the first three conjuncts
into a `let` Bool and testing `p && <remaining>` makes every fragment fit — max **67,129 steps** where the flat form was
**100,001 LIMIT**.**

Seed blob `f8f476198f`. A2 `e07e278f`. A1 host `07af079d`. Synthetic mirror of the real shape, chained through A1's driver.
Scratch deleted.

## Growth curve first — the reason a single statement cannot hold five

Five conjuncts of a cross-chunk call, one statement, chain-checked:

| conjuncts | statement nodes | steps | outcome |
|---|---|---|---|
| 2 | 18 | 29,807 | emits |
| 3 | 26 | 57,476 | emits |
| 4 | 34 | 94,773 | emits |
| 5 | 42 | **100,001** | **LIMIT** |

Increments: +27,669 then +37,297 for +8 nodes each. Cost per node rises from 1,656 to 2,787 as depth grows, so this is
**superlinear (~n^1.7)**, not linear and not exponential. A 5-conjunct statement lands around 145,000 extrapolated — ~45% over.

## Three formulations of the same five conjuncts

| formulation | fragments | max fragment steps | outcome |
|---|---|---|---|
| flat in one `if` | 1 | 100,001 | **LIMIT** |
| nested `if a && b && c { if d && e { … } }` | 1 | 100,001 | **LIMIT** |
| **`let p = a && b && c` then `if p && d && e`** | **4** | **67,129** | **all emit** |

The nested form fails because nesting adds a node and the emitter re-lowers each level — total work is unchanged. The local
form works because the condition is genuinely split **across two statements**, so each of the two fragments carries at most
three conjuncts, and fragmentation does the rest:

```
stmt 0 var      ( 2 nodes):     1,492  EMITTED
stmt 1 let      (24 nodes):    67,129  EMITTED   <- three conjuncts
stmt 2 if       (20 nodes):    57,136  EMITTED   <- p && two conjuncts
stmt 3 return   ( 2 nodes):     2,928  EMITTED
```

## What this means for the campaign

`find_brace`'s three five-conjunct statements can be made to emit **without any emitter change**, by hoisting part of each
condition into a Bool local — a two-statement rewrite of each. Combined with A3-146's host-side node narrowing, that would give a
complete compiler A from today's code.

That is A4's lane (source) plus A1's lane (host node selection). Neither needs an emitter change, and neither needs the
`parentId` index that A3-131 recommended and A3-146 superseded.

## Correcting myself twice in three turns

- A3-131 said only an index could fix this. **Wrong** — narrowing the node list does it (A3-146).
- A3-147 said the five-conjunct failures needed A4's documented split. **Half right** — nesting does not work; only a Bool
  local does.

Both corrections came from testing the fix rather than recommending it. The pattern is consistent enough to be a rule: **when a
remedy is cheap to simulate, simulate it before recommending it.**

## Limits

- Synthetic: five conjuncts each calling one helper `a3_m(source, o+i) == 49`. `find_brace`'s real statements call three
  *different* matchers (`is_str3`, `is_ws_at`, `expect_byte`) with differing arities, so the real split may have a different cost
  profile. The mechanism is demonstrated; the exact numbers are not transferable.
- Chain-checked (`force_chain`) throughout, because 5-conjunct functions exceed the whole-function check budget too — which is a
  separate observation worth noting: **the checker also fails at this depth**, not just the emitter.
- Not tested: whether the `let` form's inferred Bool type interacts with `may_fail` rules on the remaining conjuncts.
- One seed, one emitter pin, one driver pin. Still **no M-1 claim**.

REF GH #16. Parents: `6726480702` (A3-147), `6726440672` (A3-146), `6725863459` (A3-131, superseded).