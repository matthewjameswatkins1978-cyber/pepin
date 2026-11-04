# Mission report — PEP-WB-A3-20261104-B (independent adversarial verification)

**Date:** 2026-11-04 · **Agent 3** · **Branch** `codex/bootstrap-agent3-verification` · **Head at close** `d6d925cc98d99407d9ab6878c64587d06466d68a`
**Status:** all five priorities delivered. Candidate under test is **red** (one gate), and three genuine defects are with their owners. Nothing in this report is a milestone acceptance claim.

## PASS / FAIL / SKIP by priority

| # | priority | result | evidence |
|---|---|---|---|
| **1** | Frozen Full-v2 on integrated candidate **`c69e15d`** after ancestry + instrument verification | **PASS (run executed, verdict FAIL 14/15)** | `ACCEPT-c69e15d-FAIL.md`. Ancestry: `8396b63` → emitter `e0e49e5` → A1 `0c5f12b`/`97e420b`; A2 `b37532a` outside by routing. Instrument: runner `b464e00e…`, probe `688042d7…`, manifest 13/13, v1 archived — verified **before** the run. Gate 15 **`NOT OBSERVED=3 PROVEN=0`** (`b93284e4…`, `6d8ad056…`, `32a35f73…`); sole red gate 5 (`regression=PEP_RUNTIME_STEP_LIMIT`, 66-node row, ≈6 % over budget); no gate skipped. |
| **2** | Re-run duplicate-declaration counterexample + existing semantic matrices | **PASS (all three unchanged)** | `dup_decl_minimiser.py` 81-byte flip, seed `PEP_DUPLICATE_TYPE`; `staged_metamorphic_matrix.py` 13 cells 12/1; `staged_partial_provenance.py` 9 cells 8/0/1. |
| **3** | Challenge A1's BindingPool (cross-chunk identities, shadowing, stale facts) | **FAIL (three findings)** | `BINDING-POOL-ATTACKS-c69e15d.md`: stale binding fact flips a verdict; `add()` cannot report a conflict; `facts()` aliases internals. |
| **4** | Attack A2's cross-chunk calls with invalid/forged inputs | **PASS with one structural finding** | `SEAM-CROSS-CHUNK-ATTACKS.md`: 7 cases, 0 falsified — missing callee, forged arity, forged name refused; emitter refuses a foreign-document report (`PEP_STALE_REVISION`) while emitting for the matching one. Structural: callee facts carry no document/revision. |
| **5** | Verify newly pushed repairs and native execution claims | **PASS with two divergences** | `A2-NATIVE-CLAIMS-ea0bc9a.md`: A2's suite 18/18 OK with native tests executed; my own emit → strict clang+gcc → run matches the interpreter (`42\n`) on the canonical idiom; divergences: entry-return print, and `say(<expression>)` refused at emit. |

## Genuine defects reported to owners (with minimal reproductions)

| # | defect | owner | severity | state |
|---|---|---|---|---|
| 1 | **Duplicate type declarations** — order-dependent and one order accepts a program the seed rejects (`PEP_DUPLICATE_TYPE`); 81-byte counterexample, `external_records:2532` hardcodes `duplicateType:false`, first-match lookup | **A1** | soundness (staged) | **open**, reproduces at `c69e15d` and A1's head |
| 2 | **Binding facts carry no document/revision** — a stale binding fact flips a verdict (`valid` where seed says `invalid`); guard covers `externalTypes` only | **A1** | soundness (staged) | **open** (new this mission) |
| 3 | **`BindingPool.add()` cannot distinguish a conflict from a duplicate** (both return 0) and silently keeps the first type/mutability; `facts()` returns the pool's own dicts | **A1** | contract/API | **open** (new) |
| 4 | **Callee facts carry no identity** — a self-consistent forged `CheckedFunction`/`ResolvedSignature` set is indistinguishable | **A1** (same schema fix as #2) | soundness (staged) | **open** (new) |
| 5 | **Native output **and** `say` grammar**: wrapper always prints the entry return (so native ≠ interpreter outside the canonical idiom), and `say(<expression>)` is refused — corpus examples cannot be emitted natively | **A2** | semantic/coverage | **open**, owner question raised (convention vs semantics) |

Defects #2, #3 and #4 are one **class**: only `ResolvedTypeDecl` carries `document`/`revision`, so only type
facts can be provenance-guarded. One schema change plus one ingress guard fixes all three.

## What would change the verdict

- Gate 5: ≈4 fewer effective nodes or ≈6 % fewer steps per node on the boolean-chain row (measured band:
  62 pass / 64 refuse on the A1 line).
- Defects #2/#4: identity fields on `BindingFact`, `CheckedFunction`, `ResolvedSignature` and reuse of the
  existing `PEP_STALE_REVISION` guard at ingress. Then my probes show the difference directly — they are
  written to fail before and pass after.
- Defect #1: carry `decl.duplicateType` through `external_records` and refuse repeated names.
- Defect #5: document the wrapper print as a run-and-report convention (or remove it), and lower
  `say(<Int expression>)`.

## Boundaries held

No builder file modified; nothing merged or cherry-picked; no budget, limit, gate or frozen instrument
changed (manifest 13/13 and both v1 blobs verified in-run); scratch merge trees were local, never pushed and
not treated as candidates; A1 remains integrator and Current Status writer.

## Next verification target

On A1's next pushed **integrated successor** (or a repair SHA for defects #1/#2/#4): verify ancestry and
baseline-v2 instrument identity, then run, in order — the unchanged **Full-v2**, `dup_decl_minimiser`,
`staged_metamorphic_matrix`, `staged_partial_provenance`, `binding_pool_attacks`, and
`seam_cross_chunk_attacks` — and post the SHA-bound verdict. On A2's next native change: re-run
`a2_native_output_check` and the bounded-emission suite at the exact pin.
