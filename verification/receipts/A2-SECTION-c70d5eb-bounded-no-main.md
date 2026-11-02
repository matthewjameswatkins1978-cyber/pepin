# A2 C23 bounded-emitter slice — independent verification at `c70d5eb`

**Date:** 2026-11-02 · **Lane:** Agent 3 independent verification · **Evidence label:** `TESTED` (pure emit/checker layer; no native compile executed — see caveats)

## Pins

| Fact | Value |
|---|---|
| Target | A2 `codex/a2-list-record-fields` @ `c70d5eb7f772f1d9d66c3fb918e21b7a9c43dc31` (clean pinned worktree `D:\Projects\wt-a3-a2-c70d5eb`) |
| Subject commit | `c70d5eb` `feat(c23): bounded chunks need no main; and a measured limit on slice-after emission` (test-only: `tests/test_c23_section_identity.py` +97, `tests/pep_c23_emitter.pep` +14/-4) |
| Cross-lane pin for R1/R2 | A1 `codex/checker-emitter-integration` @ `05add76e21d4c979d243fa1fd7cbd0eb2a9d945c` (worktree `D:\Projects\wt-a3-mimo-8130276`) |
| Probes (this branch) | `verification/probes/bounded_chunk_no_main.py`, `verification/probes/lextoken_make_token_checker.py` |

## 1. Builder suite re-run (independent, not taken on report)

`python -m unittest tests.test_c23_section_identity -v` at `c70d5eb` → **6 tests OK, 1 documented skip (6.30s)** — exactly A2's stated "6 tests OK / 1 documented skip". Skip reason recorded verbatim: *this checkout's Pep-written checker cannot reach LexToken + make_token within its step budget; A1's checker can* (`RuntimeError`). The skip fires before any native compile, so **no C was built in my run**.

Claims the re-run evidences: sections concatenate to the one-shot output for 4 shapes; function units concatenate to the one-shot output (`header + Σunits + main == one-shot`); unit granularity (one definition, no `#include`, no `int main(`); out-of-range unit index refuses `unsupported` with "out of range"; section partition purity.

## 2. Independent probe: bounded chunk without `main` (`bounded_chunk_no_main.py`)

Own harness (registration sequence mirrored read-only from A2's test scaffolding; assertions mine), run at `c70d5eb` on `fn add(a: Int, b: Int) -> Int { return a + b }` — **exit 0, `SUMMARY cases=5 claim_falsified=0`**:

| case | result |
|---|---|
| C1 one-shot (`part=all`) still refuses no-main | `unsupported` — diagnostic verbatim *"Pep C23 emission requires a top-level function named main"* ✓ (guard narrowed, **not removed**) |
| C2 section `header` on no-main source | `emitted`, 4,292 bytes, `#include` present ✓ |
| C3 section `function` on no-main source | `emitted`, `int64_t pep_fn_` present, no `int main(` ✓ |
| C4 *(observation)* section `main` on no-main source | `unsupported`, same main diagnostic — matches A2's stated design (guard applies to `part` of `all` **or** `main`; the no-main route is header + units only) |
| C5 function unit 0 on no-main source | `emitted`, 202 bytes, definition present, no `int main(` ✓ |

**Verdict for A2's capability claim: held on my independent probes.** No defect found in this slice.

## 3. Independent probe: the A1/A2 `make_token` reconciliation (`lextoken_make_token_checker.py`)

A2's commit resolves a cross-lane disagreement ("both correct about different shapes — cost, not rejection"). Measured at **A1 `05add76`** (the checker the claim is about), exit 0:

| case | result |
|---|---|
| R1 *(claim)* `LexToken` + `fn make_token` (verbatim extraction, no main) | **`valid`** ✓ — A2's reconciliation half confirmed on A1's current head, not just `a58f5f8` |
| R2 *(observation)* same + a **reconstructed** `main` caller | `PEP_RUNTIME_STEP_LIMIT` — *"Execution step budget exceeded at 2443:23"* |

R2 corroborates A2's measured *"budget exceeded at 2428:3"* in **kind** (checker step budget) and near-position; the exact position differs (2443:23 vs 2428:3) — expected, because A2 did not commit their +main fixture (I reconstructed mine) and A1's checker has advanced since. Recorded as corroboration of the mechanism, **not** exact-fixture parity.

## Caveats (stated, not softened)

- **Native compile of the real `make_token` translation unit: NOT_RUN in my lane.** A2's test reaches clang/gcc only after the A2-branch checker passes `LexToken + make_token`, which it does not (documented skip). Running it would require A1-checker + A2-section-tool integration — an owner task, not an Agent 3 lane.
- Sectional cost limit (`slice-after emission re-runs the whole emission`) is A2's own documented honest limit; my probes did not re-measure the full-emission cost curve — that claim stays **builder-measured, not independently re-measured**.
- Pure emit/checker layer; no budgets, caps, protocols, `CURRENT`/manifest or builder files changed by Agent 3 (`verification/**` only). Worktree mode = reversible/observable, not containment.

## Reproduction

```powershell
git -C <a2-worktree> checkout --detach c70d5eb7f772f1d9d66c3fb918e21b7a9c43dc31
python -m unittest tests.test_c23_section_identity -v                     # 6 OK, 1 skip
python verification\probes\bounded_chunk_no_main.py <a2-worktree>          # exit 0
python verification\probes\lextoken_make_token_checker.py <a1-worktree>    # exit 0 (A1 05add76)
```

## Next action

Post the consolidated 3-slice review (checker-contract D1/D2 → repair verified; A2 bounded-emitter slice) to #16 and the outbox; pick the next board item (`pep-checked-chunk-v1` forged/replayed/missing-facts campaign is the standing first target from Lucy's LUCY-20261102-005).
