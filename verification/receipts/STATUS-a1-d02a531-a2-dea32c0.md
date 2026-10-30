# Status round — A1 `d02a531` / A2 `dea32c0` (2026-10-30)

## 1. Bundle still broken — emitter integration not yet landed

| state | bundle | diagnostic |
|---|---|---|
| A1 `d02a531` own (3 commits after my finding) | **invalid** | `PEP_TYPE_MISMATCH: Expected FlatAstNode but found CheckerNode @ line 5054` (was 5041 — moved with checker growth) |
| combined `d02a531` + A2 `dea32c0` emitter | **invalid** | identical |
| A2 `dea32c0` own (control) | **valid** | — |

A1's three commits (`05f1d77`, `877a705`, `d02a531`) are further
checker binding/name-chunk cost work; the emitter blob on A1's line is
still `9573c227…` — no integration yet. **All emit verification on any
A1-checker state remains blocked** (a14/classifier/combined), and Wall
A stays unmeasurable.

## 2. A2 `dea32c0`: claims verified, own a14 regressed 3 → 4 (deterministic)

Claims **true where made**: nested module **47 tests OK, 5 skips**
(exact), str_contains 16 OK (3 skipped), focused record-return tests
1/1 (interpreter vs clang/gcc stdout parity as stated).

But their own `test_a14_c23` went **3 → 4**: `test_generated_c23_executes_source_backed_programs_under_clang_and_gcc`
fails again (emit-stage `PEP_RUNTIME_STEP_LIMIT @ 7665:55`; rerun
confirms 4 — not flaky). Program ladder on the a14 path at this head:

| program | result |
|---|---|
| `return 42`, `answer()` | emitted |
| `countdown(0)` / `(6)` / `(99)` | **all STEP_LIMIT @ 7665:55** |

The record/conditional-lowering commits pushed the whole countdown
class back over the a14 shared budget.

## 3. Oscillation pattern — Wall B swings, staged path does not

a14-path (all-in-one `emit_c23`) countdown boundary across emitter
work cycles:

| head | boundary on a14 path | staged path (same program) |
|---|---|---|
| `f184580` (loop-work cycle) | all fail (0…511) | passes |
| `7b69964` (cost-reduction) | ≤99 pass, ≥100 fail | passes |
| `dea32c0` (record/conditional work) | **all fail (0…99+)** | passes (measured through `7b69964`; emitter-only cost for countdown stayed under 100k everywhere tested) |

Every emitter feature cycle re-crosses the a14 shared budget; every
cost-reduction round pulls it back. The staged path never oscillates.
**This is the empirical argument for the Wall B contract decision** —
a14's all-in-one budget makes green/red a function of unrelated feature
work, while staged emit stays a stable signal.

## 4. A1 checker suites at `d02a531` (clean)

a13 + nested **98/98 OK** (grew 97→98) — their binding-chunk cost work
keeps its own suites green, consistent with every prior round: A1's
claims hold within suites that don't touch the emitter.

## Blocker map (unchanged, with aging)

1. **First-order:** bundle `CheckerNode`↔`FlatAstNode` integration
   (open since `d64ea2a`, now 4 builder commits old) — blocks all emit
   verification.
2. **Wall A** (staged closure cost): unmeasurable until (1).
3. **Wall B** (a14 all-in-one contract): decision open; oscillation
   evidence above.

Replay: corpus/`replay.py`/base untouched — **161/161** current.
