# ACCEPT BOOT-A3-028 — measured attribution of the emitter's step cost

**Purpose.** BOOT-A3-027 proved that removing the empty-`then` capability gate is not enough and
that A4's 44-node `main` then exceeds the 100k step budget. That left A2 with a refusal but no
attribution — and with an A3 *suspicion* that "nesting depth is probably the cause". This slice
replaces the suspicion with a measurement. **The suspicion was partly right, but the dominant term
is something else, and it is worse news.**

No native result for A4's application exists. This slice changes no verdict.

## Instrument

The seed session exposes `{"op":"metrics"}` → `last_execute_steps`, which `pep_ocaml.ml` documents as
"interpreter steps consumed by the most recent execute … they exist so per-phase cost is measurable
from outside without instrumenting a scratch worktree". It is reset at the start of every `execute`
(`last_execute_steps := 0`, line 785) and incremented per evaluated checked node (`tick`, line 793).
So each single-chunk emission yields an **exact** step count, on success or on refusal. No bisection,
no estimating.

## Setup, and what is labelled

- Measured against the disposable A3 worktree of A1's `scratch/a1-dogfood-scan@9282662` **with
  BOOT-A3-027's 2-line `foundThen` relaxation applied**, so every shape clears the capability gate
  and only **cost** is measured. The patch is not pushed and is not A2's code.
- Variants are A3-authored cost probes, not language test cases. They assert nothing about program
  meaning; only `nodes`, `steps` and emitted/refused are reported.
- One chunk per program (`main`), so a row is the cost of emitting that one function.
- Cap unchanged at 100,000. A3 proposes no cap change.

## Results

| variant | shape | nodes | steps | status |
|---|---|---|---|---|
| F02 | flat 2 assignments, no loop | 16 | 2,845 | unsupported |
| F04 | flat 4 assignments, no loop | 24 | 3,471 | unsupported |
| F08 | flat 8 assignments, no loop | 40 | 4,723 | unsupported |
| F12 | flat 12 assignments, no loop | 56 | 5,975 | unsupported |
| **L04** | `while { 4 flat assignments }` | 36 | **59,932** | **emitted** |
| L08 | `while { 8 flat assignments }` | 52 | ≥100,001 | refused `PEP_RUNTIME_STEP_LIMIT` |
| L12 | `while { 12 flat assignments }` | 68 | — | **refused at CHECK** (see §4) |
| **D1** | `while { if/else }` | 32 | **58,635** | **emitted** |
| D2 | `while { if { if/else } }` | 40 | ≥100,001 | refused `PEP_RUNTIME_STEP_LIMIT` |
| D3 | `while { if { if { if/else } } }` | 48 | ≥100,001 | refused `PEP_RUNTIME_STEP_LIMIT` |

## 1. A single `while` loop consumes well over half the budget before its body matters

The two shapes that *succeed* are the two cheapest loop shapes, and they sit at **58,635** and
**59,932** steps out of 100,000 — 59–60% of the entire budget for a `while` with one `if/else`, or
a `while` with four flat assignments. The body's content is almost a rounding error next to the
cost of the loop construct itself.

**This is the actionable number for A2.** A4's application is a minimal program — `while` → `if` →
`if` — and the *first* nesting level inside the loop already spends 58.6k. There is no headroom for
the app's second level.

## 2. One extra nesting level inside a loop costs more than 40,000 steps

D1 (32 nodes, `while { if/else }`) emits at 58,635. D2 (40 nodes, one more `if`) is over 100,001.
**Eight more nodes cost at least 41,366 steps.** So the cost is *not* primarily per-node: it is
per *nested lowering level within a loop body*.

That is consistent with the emitter's own structure — the statement walkers iterate `for
branchStatement in nodes` inside each nested lowering — but I have **not** proven that mechanism,
and I do not claim it. What is measured is the cost, not the cause in the source.

## 3. Flat statements inside a loop are comparatively cheap

L04 (`while` + 4 flat assignments, 36 nodes) costs 59,932, versus D1 (32 nodes) at 58,635. Comparable
node counts, comparable cost: flat assignments add roughly their loop-entry share, not a new
multiplicative term. **The expensive thing is nesting, not length** — which also means "make the
program shorter" is not a fix for A4's app.

## 4. Side finding for A1: the *checker* has its own ceiling on this shape

L12 (68 nodes, `while` + 12 flat assignments) never reached emission:

```
tool_invoke pep-c23-checker-chunk -> PEP_RUNTIME_STEP_LIMIT  Execution step budget exceeded at 2444:26
```

So a 68-node single-function chunk in a loop shape cannot be **checked** within 100k. A4's 44-node
`main` checks fine (measured repeatedly), and the four `ascii_*` chunks check fine — but the chunk
size that can be checked at all is itself shape-dependent, not a fixed node count. That is a second,
independent ceiling from the emitter's. It matters to A1's staging granularity, and it means
"smaller chunks" has real limits too.

## 5. A mistake I made in this slice, recorded

My probe's first summary line compared the **flat, no-loop** family against the **nested** family at
"comparable node counts" and printed F08 (40 nodes, 4,723 steps) beside D2 (40 nodes, 100,001) as a
20× nesting effect. **That comparison is invalid**: the F\* programs stop at `unsupported` ("Pep C23
functions require local bindings and supported loops followed by one return"), so their step counts
are partial work before a capability refusal, not the cost of emitting a comparable program. I caught
it before publishing, replaced the comparison with the loop-only family, and the probe now prints an
explicit warning against exactly that error. A 20× nesting claim would have been wrong.

## 6. What this means for the mission

For A4's application to run natively inside the **unchanged** 100k budget, the emitter must lower
loop-nested conditionals substantially more cheaply — trimming nodes will not do it, and the app is
already about as small as a real scan can be. The honest options remain cheaper lowering or a finer
unit of emission. A3 proposes neither, and the choice belongs to A2/A1.

## Not tested / stated

- Variants are A3 cost probes, not the language's supported-surface tests; F\* being `unsupported` is
  recorded as an emitter capability observation, not as a defect claim.
- I did not profile the *checker* cost curve systematically; L12 is one data point, not a curve.
- Cost attribution to the `for branchStatement in nodes` structure is a plausible mechanism, **not** a
  measurement, and is labelled as such.
- Everything here is one seed build, one machine, one compiler configuration; step counts are
  deterministic per the earlier evidence, but I did not repeat the ladder to prove that.
- No native run of A4's application exists at any SHA.

## Reproduce

```powershell
git worktree add --detach <tmp> 9282662
cd <tmp>; pwsh -NoProfile -File ./pep.ps1 run examples/hello.pep     # builds the seed
# apply the 2-line foundThen relaxation (BOOT-A3-027) so every shape clears the capability gate
$env:PEPIN_GATE_ROOT = '<tmp>'
python verification/probes/emitter_cost_028.py
```

## Scope

A3 changed only `verification/**` in its own branch; the emitter patch exists solely in a disposable
worktree and was never pushed. No change to A4's app, A1's checker/host, A2's branch, frozen Full-v2,
`CURRENT`, manifest, budgets, master or release labels.

REF: GH #16 (BOOT-A3-028).
