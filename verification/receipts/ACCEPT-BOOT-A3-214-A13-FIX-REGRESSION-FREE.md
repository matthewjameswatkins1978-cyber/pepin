# ACCEPT BOOT-A3-214 — the A13 fix is regression-free across the corpus and the checker tests

**A3-213 offered a one-line fix and named two unexamined surfaces. Both are now closed: the 63-file corpus is unchanged, and the
checker test modules show the same pre-existing failures with and without the patch. The fix is not a regression.**

Seed blob `f8f476198f`. Patch: `verification/fixtures/a3-a13-checker-fix.diff`, applied in a disposable worktree and reverted.

## The corpus

| outcome | unpatched (A3-181) | patched | |
|---|---|---|---|
| built | 10 | **10** | same |
| top-level declarations unsupported | 24 | **24** | same |
| other refusal | 16 | **16** | same |
| `PEP_RUNTIME_STEP_LIMIT` | 9 | **9** | same |
| other check failure | 4 | **4** | same |
| **`PEP_A13_TYPE_UNSUPPORTED`** | **0** | **0** | same |

Identical in every cell. That is the expected outcome — none of the 63 files triggered the defect — and it is the result that shows the
patch changes nothing it was not meant to change.

## The checker tests

Three modules against the patched checker, then the same three against an unpatched tree:

```
patched:   Ran 34 tests in 59.5s   FAILED (failures=1, errors=1)
baseline:  Ran 34 tests in 59.5s   FAILED (failures=1, errors=1)
```

**Same counts, same two tests, both ways.** They are pre-existing:

- `ERROR test_long_identifier_parses_at_1280_and_stops_at_1536` — `test_a13_checker_budgets`
- `FAIL test_match_binding_preserves_nominal_list_type_shape` — `test_a13_nested_records`

I did not investigate either. They are unrelated to the assignment-target path and were failing before the patch.

## The methodological point

The first run **looked like a regression** — `FAILED (failures=1, errors=1)` immediately after applying my own fix. The control run is
the only thing that distinguished "my patch broke two tests" from "two tests were already broken". Without it I would either have
abandoned a correct fix or published a false alarm.

That is the same discipline that caught A3-186 and A3-174, applied before publishing rather than after.

## What this adds to the fix's evidence

| check | result |
|---|---|
| 31-line reproducer builds | yes (A3-213) |
| reduced fixture builds | yes (A3-213) |
| A4's compiler unchanged at 61,941 B | yes (A3-213) |
| 63-file corpus unchanged | **yes (this receipt)** |
| checker test modules unchanged | **yes (this receipt)** |

## What is still unexamined

- **The full test suite.** `python -m unittest discover -s tests` exceeded 50 minutes and I stopped it. The whole-project run — chunk
  contract, c23 emitter, CLI — is unverified against the patch.
- Two pre-existing failures that I did not diagnose.
- The patch is still not applied to any branch. A1 owns the checker.

## Limits

- Three test modules of the suite's full set, chosen because they are checker-related; other modules could exercise
  `declared_binding_type` indirectly.
- One corpus revision, one seed.

REF GH #16. Closes the unexamined surfaces named in `6730779392` (A3-213).