# ACCEPT BOOT-A3-045 — flattening does NOT fit: one conditional per loop body is the ceiling

**Verdict: my decision-relevant prediction is FALSIFIED. Flattening a state machine does not buy a fit.**
The ceiling is far lower than "44 nodes": it is **one conditional per loop body**.

Pre-registered at `055a6f1`, with Q2 as my own falsifier.

## Measured — constant `while !(byte_length(source) <= o) { <BODY> o = o + 1 }`, exact step counts

| var | body | nodes | steps | status |
|---|---|---|---|---|
| Q1 | **one** sequential `if/else` | 34 | **66,577** | emitted |
| Q2 | **two** sequential `if/else` | 48 | **≥100,001** | **refused** (emission budget) |
| Q3 | **three** sequential `if/else` | 62 | — | **refused by the CHECKER** — `PEP_RUNTIME_STEP_LIMIT at 2454:8` |
| Q4 | nested depth-2 (control) | 44 | ≥100,001 | refused (reproduces BOOT-A3-028/038) |

## Why this matters more than any previous cost measurement

I hypothesised that sequential chains would be cheaper than nesting, because nesting appeared to add a
cost term *per level*. **That was wrong.** Two sequential conditionals in one loop body already exceed
the emission budget, and three cannot even be **checked**.

So the constraint is not a node count. It is:

> **A function that emits today can contain at most ONE conditional inside a loop body.**

A lexer, parser or type checker needs many classifications per iteration. **No amount of restructuring
into sequential branches gets a real compiler-shaped function under the budget.** Combined with
BOOT-A3-043 (`utf8_slice` is not a lowered builtin, so `Str` construction is separately blocked), the
seed cannot currently emit anything resembling a compiler.

Two layers bite: emission at 48 nodes, and the **checker** at 62 nodes — so it is not only the emitter.

## The constructive number for A2

At 48 nodes, BOOT-A3-033's fit predicts `381·48 + 35.68·48² = 18,288 + 82,207 = 100,495` — landing
almost exactly on the 100,000 boundary, which is what Q2 measured. **The quadratic term is the whole
problem**: removing it would cost **~18,300** at 48 nodes, i.e. a **5.4× margin** under the same cap.

That converts "the emitter is too expensive" into a single, quantified target with a known success
criterion: make emission cost **~linear** in node count, and a two- or three-conditional loop body fits
without touching the cap.

## What this changes for route selection

- Route S (small Pep bootstrap) is **blocked at seed → A** until lowering cost drops. A deliberately
  tiny compiler A still needs a lexer loop, and a lexer loop needs more than one classification.
- Route R's "narrow optimisation" is therefore **not optional overhead** — it is the prerequisite both
  routes share. My D-route said R was not a shortcut; this is stronger: **R's fix is on S's critical
  path too.**
- No spike should be judged as evidence of self-hosting capability until it can emit such a function.

## Honest limits

- Cost probe only: nothing compiled or run. These are emitter/checker step counts.
- One family (one `while`, `if/else` statements over `byte_at`), one seed build, one machine.
- I did not test `else if` chains specifically (they are nested by construction, so I expect them to be at
  least as expensive, but **I have not measured it**).
- I did not test a dispatch-table lexer (arithmetic lookup instead of branches). That would need
  `List`/indexing in the compiler's own source, which I have not established is emittable — **unmeasured,
  and it is the one structural alternative I would still investigate** before declaring lexing impossible.

## Reproduce

```powershell
git worktree add --detach <t> 86ff953
cd <t>; pwsh -NoProfile -File ./pep.ps1 run examples/hello.pep
$env:PEPIN_GATE_ROOT = '<t>'
python verification/probes/flatten_vs_nest_045.py
```

## Scope

A3 changed only `verification/**`. No edits to A1's checker/contract, A2's emitter, A4's app. Cap
unchanged; no `CURRENT`, manifest, frozen-gate, master or release change.

REF: GH #16 (BOOT-A3-045).