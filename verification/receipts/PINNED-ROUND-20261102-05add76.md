# PINNED ROUND 2026-11-02 — full module inventory at A1 `05add76`

**Date:** 2026-11-02 · **Lane:** Agent 3 independent verification · **Evidence label:** `TESTED`
**Target:** A1 `codex/checker-emitter-integration` @ `05add76e21d4c979d243fa1fd7cbd0eb2a9d945c` (clean pinned worktree `D:\Projects\wt-a3-mimo-8130276`)
**Successor context:** `BASELINE-272-tests-46bf1c0` (that baseline deliberately excluded `test_c23_collections`, `test_closure_inventory` from the heavy batch etc.; this round is a full current-inventory, module counts drift with the builders' own suite edits — totals are stated as measured, not forced onto the old denominator).

## Results (every module run by Agent 3 at this head)

| module(s) | tests | result |
|---|---|---|
| `test_a6` `test_a7` `test_a8` `test_a10` `test_a11` `test_a12` | 59 | **OK** (66s) |
| `test_a13` + `test_a13_nested_records` | 72 | **OK** (224s) |
| `test_a13_checker_budgets` + `test_checked_chunk_contract` + `test_chunk_scalar_validation` | 59 | **OK** (16s) |
| `test_lexer_chunk_ledger` | 4 | **OK** (4s) |
| `test_checker_node_cost` | 2 | **OK** (1s) |
| `test_cli` | 45 | **OK** (50s) — source-verified: no native C in this module |
| `test_closure_inventory` + `test_moonbit_cli` | 12 | **OK** (32s) — closure ledger printed (T1–T5 `checked-valid`, all 9 full-closure functions step-limited/transport — whole-closure regime, distinct from body chunks) |
| `test_c23_arity` + `test_c23_nested_record_emission` | 59 | **OK**, 5 skipped (114s, native clang/gcc) |
| `test_c23_list_record_fields` | 18 | **OK** (27s, native) |
| `test_c23_cli` | 8 | **OK** (native) |
| `test_c23_str_contains` | 25 | 21 OK / 3 documented skips / **1 error = the reported `d158044` regression** |
| `test_a14_c23` | 11 | 2 failures = **exactly the documented stale-expectation pair** (`test_unsupported_valid_program_is_reported_without_c_output`, `test_recursive_call_is_rejected_before_native_lowering`), 0 new; the ae91bdc-era residue (`source_backed`/`depth`) is green here |
| `test_c23_collections` | 129 | **195 failing subtests** — see analysis below |

**Aggregate:** 503 tests executed at this head; failing records = 195 (collections) + 2 (a14 known) + 1 (the reported `d158044` regression) = **198, every one classified; 0 unexplained/undocumented failures; 0 wrong-answer failures observed.**

Not run (by scope): `benchmark_a11_lexer.py` (perf harness, not a test suite), Lean build (per security record), the A2-branch-only modules already covered earlier this session.

## `test_c23_collections` analysis (Wall A measurement at the integration head)

Run completed in 2,785s (`python -u -m unittest tests.test_c23_collections -v`). *(First invocation, without `-u`, terminated at 2,563s without a summary — process exit -1, cause not established; no Defender detections since 10/29 and disk headroom ample; the rerun above completed normally. Recorded, not hidden.)*

- **195 failing subtests = 178 `PEP_RUNTIME_STEP_LIMIT` (emit stage, e.g. bundle `8421:31`) + 17 `Pep C23 one-parameter calls require one argument and a call-free target expression`** (the known construct-refusal/misblame class from `CORROBORATE-var-callee-2x2-1b59613`).
- **Zero wrong-answer failures** — every failure is fail-closed (budget or refusal), consistent with the standing fail-closed characterization.
- **Total matches A2's corrected figure exactly** (Lucy's record: parent `26be4be` = 213 failing subtests; corrected A2 `74a332e` = 195, 18 repaired). Composition by code at their branch is not in my receipts, so the match is claimed at **total level only**.
- **Death-position map (all 178, exact bundle→file mapping):** **154 die inside `pep_checker_a13.pep`, 24 inside `pep_c23_emitter.pep`**, 46 distinct positions. Hottest lines are the O(n) node-scan helpers: `lookup_node` L72 (×44), `child_at` L82/L83, `count_children` L77 (checker); `pep_c23_direct_local` L1341 (×8, emitter). Only 13.5% of deaths are emitter-side.
- **Reading (corrected against the naive "emit-stage hotspot" expectation):** these are failures of the **all-in-one emit invocation**, whose shared budget is exhausted overwhelmingly **in checker-side node scans before emission proper** — the Wall B / two-path family, not a single emitter hotspot, at this head. Both walls therefore remain **open** at `05add76`: the shared-budget wall by 154 deaths, the emit-only wall by the 24 emitter deaths. Builder directions unchanged in kind: bucket/index nodes once (`lookup_node`/`child_at` fan-out is the measured hot family) and/or the a14 → staged-`emit_c23_checked` contract decision. Exhaustion-position caveat applied: positions are where the budget ran dry, not sole-causation proof.

## Honest scope

- Single head, sequential batches (no parallel CPU contention); times approximate.
- `NOT_RUN`: native compile of real `make_token` TU (integration-gated), Lean kernel check (security record), A2-branch module sets beyond those separately pinned (c70d5eb), `benchmark_a11_lexer`.
- Native clang/gcc compile+run executed inside the C23 modules under the #22 clearance record; nothing outside `verification/**` changed by Agent 3; no budgets/caps/protocols/`CURRENT`/manifest touched.

## Reproduction

```powershell
# per-batch commands in this receipt, all at the pinned checkout
python -m unittest tests.test_a6 tests.test_a7 tests.test_a8 tests.test_a10 tests.test_a11 tests.test_a12
python -m unittest tests.test_a13 tests.test_a13_nested_records
python -u -m unittest tests.test_c23_collections -v     # 195 failing subtests
python -m unittest tests.test_a14_c23                    # exactly 2 documented failures
```

## Next action

Carry the baseline + collections Wall-A confirmation into the next consolidated #16 review; keep polling for A1's `d158044` fix to re-run the standing regression bat.
