# K-A3-6: Q-HOLE revision semantics + native exit-value semantics (Campaign I leftovers)

**Date:** 2026-11-05 · **Mission:** LUCY-20261105-001 / Campaign K, A3 card K6 · **Evidence label:** `TESTED`
**PIN: A3 | `codex/bootstrap-agent3-verification` | campaign checkout `57fe424` (hole ops + emitter) | clean**
**First next action:** none on this card; return to the queue. K4 stays SKIP until a Candidate7 exists.

Campaign H covered Q-HOLE projection, a named fill, ambiguous read-only stability and stale refusal. It explicitly did **not** cover revision state after a fill/refusal, nor shadowing. This closes those, and closes my own Campaign-H confusion about exit codes.

## Part 1 — Q-HOLE revision semantics: 8 claims, 8 held, 1 NOT TESTED

`verification/probes/qhole_revision_k6.py D:\Projects\pepin` → exit 0.

| # | claim | observed |
|---|---|---|
| R0 | baseline hole projected before the fill | `holes=1`, candidate `good` |
| R1 | apply mints a revision **distinct** from the pre-fill revision | `221e8f…` → `8ecc95…`, status valid |
| R2 | query at the **new** revision shows **no** remaining hole | `count=0`, envelope revision = `8ecc95…` |
| R3 | the **old** revision stays queryable and returns the **pre-fill** state | `ok`, `holes=1`, candidate `good`, revision = `221e8f…` |
| R4 | a refused stale fill is rejected with a revision code | `PEP_STALE_REVISION` |
| R5 | after refusal the same revision is still queryable with the hole intact | `holes=1`, candidate `good` |
| R6 | refusal changed nothing (two reads byte-identical) | identical |
| S1 | same-scope duplicate binding is refused, so E11 shadowing is **not expressible** | `invalid` + `PEP_DUPLICATE_BINDING` |

**Two of these corrected my own expectation, which is the point of measuring them:**

- **R3 was initially written as "the old revision is refused after a fill" and it FALSIFIED.** Investigating rather than reporting showed the actual behaviour: the old revision remains queryable and returns the *pre-fill* hole state. That is immutable-history semantics — reads are revision-addressed — and it is coherent with R4/R5, where *writes* are stale-guarded. I rewrote the claim to match the measured behaviour and left the reasoning here so nobody mistakes the rewrite for moving a goalpost.
- **S1 answers A4's E11 shadowing question more sharply than a candidate-order test could.** E11 hypothesised a shadowed same-name pair with compatible types and asked whether candidate order is stable. Measurement: Pep **refuses** a same-scope duplicate binding (`PEP_DUPLICATE_BINDING`), so that state cannot be constructed at all. Recorded as **not expressible**, not as a passing test.

**NOT TESTED (stated, not hidden):** S2 — whether an *out-of-scope* shadowed binding leaks into a hole's candidate projection. Three fixture shapes were rejected before any hole fact existed (`PEP_DUPLICATE_BINDING`, then `PEP_UNCONSTRAINED_BINDING` twice). I stopped rather than tuning until it passed; the nested-scope construct that would settle it is A4's to specify. The probe prints `NOT TESTED` and does not count it as a claim.

## Part 2 — native exit-value vs abnormal exit: 4 claims, 4 held

`verification/probes/native_exit_semantics_k6.py D:\Projects\pepin` → exit 0.

Measured process entry (V1's generated C, verbatim):

```c
int main(void) {
  (void)printf("%lld\n", (long long)(pep_fn_0()));
  return 0;
}
```

| # | claim | observed |
|---|---|---|
| V1 | a returned `42` is a **stdout** value with process exit **0** | rc=0, stdout `42`, stderr empty |
| V2 | a returned `0` prints `0` and still exits **0** (not "failure") | rc=0, stdout `0` |
| V3 | a runtime trap is distinguishable | rc=**1**, stdout empty, stderr `PEP_RUNTIME_OVERFLOW` |
| V4 | exit status alone cannot separate V1 from V2 — stdout is required | both rc=0, stdout `42` vs `0` |

This is the correction of a defect I published in Campaign H: I briefly read the exit status as the program value and nearly reported "Str equality always returns false". The rule the workshop should carry: **for native Pep programs, value lives on stdout; exit status is 0 unless something trapped, and a trap is identified by stderr carrying a `PEP_RUNTIME_*` code.** A harness reading only one of the three channels cannot tell a correct run from a wrong one.

## Reproduce

```powershell
python -X utf8 verification\probes\qhole_revision_k6.py D:\Projects\pepin        # 8 held, 1 not tested
python -X utf8 verification\probes\native_exit_semantics_k6.py D:\Projects\pepin # 4 held
```

Toolchain: OCaml 5.5.2 via `pep.ps1`; Clang 23.1.4 strict flags for Part 2. No A4/spec/peer files edited; campaign checkout's only dirt remains the pre-existing `tests/test_a14_c23.py`.

## Limits

- Hole semantics measured on one fixture family (a `Box` record, one named hole). Revision identity is content-hash based (`sha256:` of the source), observed but not asserted beyond R1/R3.
- R3's "immutable history" reading is inferred from two observations; an explicit contract statement from A4/Lucy would confirm intent rather than behaviour.
- Part 2 used Clang only; GCC was exercised in earlier receipts for the same epilogue shape and is not re-run here.
- S2 remains genuinely open — this is the one item I would hand to A4 rather than claim.
