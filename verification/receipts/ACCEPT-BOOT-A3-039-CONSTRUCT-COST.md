# ACCEPT BOOT-A3-039 — construct-level cost, and three of my own checks corrected

**Verdict: 4/5 checks, 1 falsified prediction. Two of my five predictions were wrong or mis-designed,
and one check compared a budget bound again — all corrected in the probe before publishing.**

The usable output for A2 is a **ranked marginal cost per construct** on a constant envelope, plus an
honest statement of what this ladder cannot separate.

## Measured — constant `while !(byte_length(source) <= o) { BODY; o = o + 1 }` envelope

A1 `86ff953` tree, fresh worktree, seed built there. Nothing compiled or executed.

| var | adds | nodes | steps | vs V0 steps | per added node | status |
|---|---|---|---|---|---|---|
| V0 | baseline: one assignment | 24 | 29,725 | — | — | emitted |
| V1 | + three assignments | 40 | 72,317 | **+42,592** | **2,662/node** | emitted |
| V2 | + one flat `if/else` | 38 | 79,046 | **+49,321** | **3,523/node** | emitted |
| V3 | + nested `if` (depth 2) | 48 | ≥100,001 | ≥+70,276 | — | **refused** |
| V4 | + `if/else` with a different condition call | 37 | 74,017 | +44,292 | 3,407/node | emitted |
| V5 | + one extra local binding | 27 | 38,986 | **+9,261** | **3,087/node** | emitted |

## What is established

1. **Control flow is dearer per node than assignments** (P2 confirmed): an `if/else` costs
   **3,523/node** against **2,662/node** for assignments. If A2 optimises one lowering path, the
   conditional path is the better target.
2. **A local binding is *not* cheap per node** (3,087/node) — dearer than assignments and within 12%
   of a conditional. My pre-registered claim "an extra local costs less than a control-flow construct"
   was true only as a **total** (3 nodes vs 14), and is **not supported per node**. Declaration
   lowering is therefore also a candidate target, not a free addition.
3. **A two-level nested `if` inside a `while` crosses the budget at 48 nodes** (V3 refused). That is the
   frozen app's shape: its `main` has a nested `if` inside a `while` and is 44 nodes, so it sits
   between V2 (38 nodes, 79,046) and V3 (48 nodes, refused).
4. **Baseline cost:** `while` + one assignment + two locals = **29,725** at 24 nodes.

## What is NOT established — and two predictions of mine that were wrong

- **P1 falsified:** I predicted V0 in 18,000–26,000 and measured **29,725**. My band came from
  BOOT-A3-038's 20-id *window* (21,972) applied to a 24-node program — a mis-calibration, not a
  compiler surprise. BOOT-A3-033's own N=1 row was 29,725 at 24 nodes, which I should have used.
- **P3 not testable:** V3 **refused**, so "+20,955 steps" is a *lower bound* derived from the budget
  trip, not a measurement of nesting. My first version compared that bound to a `2×` threshold — the
  **same mistake I made in BOOT-A3-033 P3** and caught again only because I re-read the row. It now
  reports NOT TESTED.
- **P4 is confounded by my own design:** both V2 and V4 contain an `if/else`, so V4 does **not**
  isolate "a call". All that can be said is that two `if/else` variants differing in the condition's
  call differ by **5,029 steps** (79,046 vs 74,017) at one node's difference. **No claim about the
  cost of calls is made.**
- **Per-node comparisons are themselves confounded** by the quadratic term established in
  BOOT-A3-033: variants differ in size as well as construct, and cost per node *rises with size* on
  its own. The marginals above are honest at the sizes they were measured; they are not a clean
  decomposition of "construct" from "size". A proper isolation would need equal-node variants, which
  I did not build.
- No mechanism in A2's code was instrumented. Nothing here says *why* conditionals cost more.

## What A2 can do with it

Ranked, at these sizes: **conditional lowering (3,523/node) ≳ declaration lowering (3,087/node) >
assignment lowering (2,662/node)**. Combined with the quadratic term of BOOT-A3-033, the picture is
consistent with a per-node scan whose cost multiplies with the number of statement/conditional nodes
processed — but that remains an inference. The frozen app's `main` must shed roughly 15–20k steps to
fit the unchanged budget (BOOT-A3-038 measured the refusal at ≥100,001 with the same offset).

## Not tested

- No equal-node variants, so construct and size are not separated (stated above, not hidden).
- A local *inside* the loop body (only a function-level local was measured); the emitter may treat them
  differently.
- Deeper nesting than depth 2 — V3 already refuses, so higher depths cannot be measured as successes.
- Different call targets/arities; one family, one seed build, one machine.

## Reproduce

```powershell
git worktree add --detach <t> 86ff953
cd <t>; pwsh -NoProfile -File ./pep.ps1 run examples/hello.pep
$env:PEPIN_GATE_ROOT = '<t>'
python verification/probes/construct_cost_039.py     # 4/5; P1 falsified is reported, not hidden
```

## Scope

A3 changed only `verification/**`. A1's checker/contract, A2's emitter and A4's app were read, not
modified. Cap unchanged; no `CURRENT`, manifest, frozen-gate, master or release change.

REF: GH #16 (BOOT-A3-039).
