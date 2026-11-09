# ACCEPT BOOT-A3-215 — the A13 fix against 256 tests across 16 modules: no verdict changes

**A3-214 left the full suite unexamined because `unittest discover` exceeded 50 minutes. Selecting modules instead of discovering let
me cover 256 tests across 16 checker, chunk, emission and CLI modules — **every batch gives the same verdict with and without the
patch**.

Seed blob `f8f476198f`. Patch: `verification/fixtures/a3-a13-checker-fix.diff`, applied and reverted per batch.

## The three batches

| modules | tests | unpatched | patched | same |
|---|---|---|---|---|
| chunk/checked-contract/sectional/cross-chunk (9) | 128 | **OK** | **OK** | **yes** |
| a14/c23/emission/CLI (7) | 94 | **FAILED (failures=2)** | **FAILED (failures=2)** | **yes** |
| a13 budgets/nested-records/walls (3) | 34 | **FAILED (1 failure, 1 error)** | **FAILED (1 failure, 1 error)** | **yes** |
| **total** | **256** | | | |

## The five failures, all pre-existing

Every failure in the second and third batches exists **identically without the patch**:

- `test_long_identifier_parses_at_1280_and_stops_at_1536` — error (a13 budgets)
- `test_match_binding_preserves_nominal_list_type_shape` — failure (a13 nested records)
- `test_generated_c23_executes_source_backed_programs_under_clang_and_gcc` — failure (a14 c23)
- `test_recursive_native_calls_enforce_pep_depth` — failure (a14 c23)

The last two are the A13 failures this project has carried independently of this lane; the first two were already reported in A3-214. **I
did not diagnose any of them** and they are not attributable to the patch.

## What remains genuinely unexamined

Sixteen modules of forty candidates. The twenty-four I did not run include the sanitizer, bump-pool, list-record and real-lexer
modules. `unittest discover` over the whole suite still exceeds fifty minutes and has not been run.

So this is **not** "the full suite passes" — it is "16 modules, 256 tests, and no verdict changed". Those are different claims and I am
not going to let the second read as the first.

## Method note

My first attempt compared the raw output of the two batches and reported `identical: False`, because the timings differ (199.094s vs
196.854s). Comparing verdicts rather than the whole string gives the answer that matters. **A comparison that includes timing data will
always report a difference**, and I nearly treated that as a signal.

## Evidence the fix now rests on

| check | result |
|---|---|
| 31-line reproducer and reduced fixture build | yes (A3-213) |
| A4's compiler unchanged at 61,941 B | yes (A3-213) |
| 63-file corpus unchanged in every cell | yes (A3-214) |
| 256 tests, 16 modules, no verdict change | **yes (this receipt)** |
| full suite | **not run** |

REF GH #16. Extends `6731566152` (A3-214).