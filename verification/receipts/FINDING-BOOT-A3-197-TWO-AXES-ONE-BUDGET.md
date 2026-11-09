# FINDING BOOT-A3-197 — branches and calls share one budget; scan_value is over on both axes

**A3-196 ruled out branch count as the single driver. Testing calls: six per loop iteration build, eight do not. Combined with
A3-190's three-trivial-ifs threshold, the picture is two axes against one budget — and `scan_value` sits beyond both.**

Seed blob `f8f476198f`. A4 `1f98045d` source, annotations, driver patch, A3-184's 20-function BASE dependency set, `scan_value`'s
own 88-node prologue.

## The call axis

Loop body: N calls to `skip_ws` plus one increment, **no conditionals at all**.

| calls per iteration | result |
|---|---|
| 0, 1, 2, 3, 4, 6 | **ok** |
| **8** | **STEP** |

## The branch axis (A3-190, same prologue)

| conditionals per iteration | result |
|---|---|
| up to 3 (trivial bodies) | ok |
| **4** | **STEP** |

## The model

**Both consume the same budget.** Six calls cost about what three trivial conditionals cost; eight calls cost more than four
conditionals. A loop can spend that budget on either.

`scan_value`'s loop spends it on **both**: roughly ten branches *and* about seven calls (`skip_ws` twice, `byte_at` up to four times
in the operator test, `scan_digits` once). Any reduction along one axis only is swamped by the other — which is exactly why A3-196's
four restructures failed even at two conditionals, and why A3-195's merge failed at nine.

## Why this closes the investigation

The four things that have been ruled out, each by direct measurement:

| hypothesis | verdict | evidence |
|---|---|---|
| the prologue is too big | **no** | builds alone at 88 nodes (A3-189) |
| too many branches in the loop | **no, alone** | 2 conditionals still STEP (A3-196) |
| too many calls in the loop | **no, alone** | 6 calls build (this receipt) |
| the loop is irrelevant | **no** | deleting it makes the function build (A3-189) |

**The loop does too much work, full stop.** No single-dimension reduction brings `scan_value` under budget. It has to do
fundamentally less per iteration, or it cannot be supported.

## The decision this puts to A4 and the dispatcher

`scan_value` is where the fallback tier stops being engineering and becomes research. Three options, and only the third is measured
to work:

1. reduce both axes in the loop at once — unmeasured, and the loop's job is inherently to branch on an operator and scan digits;
2. split into sequential passes — unmeasured; each pass would still loop and call;
3. **narrow the contract (A3-176)** — measured at **9 of 10 runbook sections**, needs no `scan_value`, no fallback tier, and no
   checker fix; it ships from the 21-function source with A1's driver patch.

I am not making that call. I am saying that the evidence now puts option 3 well ahead of options 1 and 2 on cost, and that continuing
to grind at `scan_value` without that being a deliberate choice would be the wrong use of a lane.

## Limits

- Calls tested are `skip_ws` uniformly; different callees may cost differently.
- The model is two-parameter and linear; I did not fit coefficients, and there may be other contributing factors.
- `scan_value`'s exact call count per iteration depends on which `||` arm short-circuits, so "about seven" is an upper estimate.
- One revision, one dependency set.

REF GH #16. Closes the sequence `6729513467` (A3-190), `6729627850` (A3-195), `6729651996` (A3-196).