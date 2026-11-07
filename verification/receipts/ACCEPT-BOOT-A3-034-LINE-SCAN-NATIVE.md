# ACCEPT BOOT-A3-034 — line-scan runs natively: first end-to-end Pep application, A2's claim confirmed

**Verdict: PROVEN. 39/39 checks.** A2's claim in receipt 47 is accurate, and this is the **first
native end-to-end result for a Pep-authored dogfood application**: A4's `pepin-line-scan.pep`,
emitted from checked chunks, built with strict Clang **and** GCC in **both** assembly orders, and run
over **five genuinely different real files**, matching an independent reference on every one.

**Scope precision, before anything else.** This is A4's **second** program. The frozen acceptance
target `pepin-source-scan.pep` (blob `4a44dd65…`) **still has no native result at any SHA** — it
refuses on emission capacity (BOOT-A3-032/033). Nothing here promotes the second program or changes
the target.

## Pins

| Item | Value |
|---|---|
| A2 under test | `codex/a2-bounded-emission@4b70c61` (receipt 47) |
| Emitter blob | `3f5b958271b33f5c19111a09ae6bc0e60e4839ca` — **identical** at A2 `4b70c61` and A1 `4e325e0`, so gating on A1's integrated tree tests exactly A2's current emitter |
| App | `examples/dogfood/pepin-line-scan.pep` @ A4 `36934a6` |
| App bytes | **998**, sha256 `12d4b1ab34a0bd2f…`, blob `2e7235cc…` — **identical** at A4 `b57d4bf`, `0c73f99`, `36934a6` |
| Tree gated | fresh detached worktree at A1 `4e325e0`, seed built there |

## The gate

```
app:pinned                      998 B sha256=12d4b1ab…
chunk ascii_letter/digit/continue/main    all valid (24/12/10/30), zero diagnostics
emit:all                        emitted 4 units, epilogue carries pep_source_data
build: docorder×{clang,gcc}, protofirst×{clang,gcc}    all clean, -Werror
```

| file | bytes | expected LF | oracle | Clang d/p | GCC d/p |
|---|---|---|---|---|---|
| `input_ascii.pep` | 168 | 3 | 3 | 3/3 | 3/3 |
| `input_nonascii.pep` | 218 | 5 | 5 | 5/5 | 5/5 |
| `input_empty.pep` | 0 | 0 | 0 | 0/0 | 0/0 |
| `pepin-source-scan.pep` | 1159 | 39 | 39 | 39/39 | 39/39 |
| `pepin-line-scan.pep` (self) | 998 | 32 | 32 | 32/32 | 32/32 |

Plus: **metamorphic** — one binary over five files gives five distinct answers `3, 5, 0, 39, 32`
(a constant-printing build fails here); **missing file** → exit 1, stdout empty,
`PEP_RUNTIME_SOURCE_OPEN`; **no argv** → exit 1, stdout empty, `PEP_RUNTIME_SOURCE_CONTEXT`.

Five real files, not three, and the expected values come from **my own** measured reference
(BOOT-A3-031), measured before A2 made this claim.

## A mistake of mine, caught by the measurement

My first run FAILED on the self-scan row: I expected **39** and native printed **32**. The bug was
mine — 39 is the LF count of `pepin-source-scan.pep` (A4's fourth fixture), which I had carried
across to `pepin-line-scan.pep`. The line-scan file itself has 32 LF bytes, and my own oracle said
**32** while the native binary said **32**: the compiler was right and my expectation was wrong.

Corrected by using A4's four original fixtures (39 for `pepin-source-scan.pep`) **and** adding the
line-scan self-scan at 32 as a fifth, reference-derived case. The correction is recorded in the probe
source so the same slip cannot silently repeat.

## Testing my own cost model out of sample — it under-predicts, as warned

BOOT-A3-033 fitted `steps ≈ 380.75·n + 35.68·n²` on a **flat** family and explicitly warned it was a
lower bound for **nested** shapes. The line-scan `main` is nested (`while` → `if`), 30 nodes:

| | |
|---|---|
| Model prediction at n=30 | 43,538 steps |
| **Measured** | **51,009 steps** |
| Error | **+17.2% (actual higher)** |
| Budget headroom actually used | 51,009 / 100,000, **48,991 spare** |

So the fit **under-predicts nested programs by ~17%**, exactly the direction the caveat predicted.
The model is a lower bound, not a predictor, for nested shapes. Anyone using BOOT-A3-033's numbers to
plan should apply that correction.

It also quantifies why this program fits where the scan app does not: line-scan `main` = **30 nodes /
51,009 steps** (fits with half the budget spare); scan `main` = **44 nodes** and exceeded 100,000.
Fourteen nodes is the difference between a working application and a blocked one.

## What this does and does not establish

**Does:** a real Pep-authored application, expressed in the accepted subset, **runs natively** and
produces correct results over diverse real inputs, with the grant path exercised end to end, on two
strict compilers, in two assembly orders, against an independent reference, with fail-closed path
negatives.

**Does not:** meet the mission's acceptance target, which is the identifier-start-run inspector
(`pepin-source-scan.pep`). Does not promote A4's second program, does not touch `CURRENT`, manifest,
frozen gates, budgets, master or release labels, and does not certify the emitter generally — one
program passing is not a capability proof.

## Not tested

- The scan app still has no native run (capacity); its six A3 fixtures and A4's four remain gated by
  that refusal.
- Only this one program shape was exercised natively; no fuzzing of the emitter.
- A2's and A1's full suites were not run.
- One seed build, one machine; `-O2`, `-Werror`, `-std=c23` / `-std=c2x` only.

## Reproduce

```powershell
git worktree add --detach <t> 4e325e0
cd <t>; pwsh -NoProfile -File ./pep.ps1 run examples/hello.pep
$env:PEPIN_GATE_ROOT = '<t>'
python verification/probes/line_scan_gate_034.py     # 39/39 PROVEN
```

## Scope

A3 changed only `verification/**`. Peer trees were read-only detached worktrees; nothing pushed to any
peer branch. Cap unchanged.

REF: GH #16 (BOOT-A3-034).
