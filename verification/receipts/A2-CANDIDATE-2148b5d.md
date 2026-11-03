# A2 candidate `2148b5d` — gate battery: header/main bounded claim VERIFIED, bounded emission unregressed, CR3 still open

**Date:** 2026-11-03 · **Lane:** Agent 3 independent verification (integration-lead cycle) · **Evidence label:** `TESTED`
**Candidate:** `codex/a2-bounded-emission` @ `2148b5dde8ef0ab5af13c1c78382ed39271e110d`
(clean pinned worktree `D:\Projects\wt-a3-a2b-2148b5d`; parent `6fa3c84`; diff touches only
`tests/pep_c23_emitter.pep` +20/−1 and `tests/test_c23_bounded_emission.py` +25).
**Not this candidate:** A1 P1 fix (A1 still `05add76`, 0 commits) and A2's CR3 repair
(declaration_check untouched by this diff).

## Gate battery (unchanged instruments, blobs verified against the frozen manifest)

| gate | result at `2148b5d` |
|---|---|
| `tests.test_c23_bounded_emission` | **17/17 OK (10.1s)** (16→17: new header/main test) |
| `probe_integration_case.py --case all` ×3 | **byte-identical**, bundle `bb42fef83975b30ee3cc3970a923a8f9300ad7c5f3338e02aaef2ab5236b75d2`; **discriminating table unchanged**: lexer-chunk 55n / regression 66n die in checker, **synthetic-12 = valid + unit emitted + whole STEP_LIMIT**, synthetic-8 green → bounded-beats-whole **unregressed** |
| `probe_c23_sections --sizes 8` | all green + `byte_identity: match` |
| `probe_c23_sections --sizes 12` | **NEW: `header` emitted (4,558 B) and `main` emitted (83 B) — both were `PEP_RUNTIME_STEP_LIMIT` at `6fa3c84`**; `all` still `PEP_RUNTIME_STEP_LIMIT`; units 0..12 still emit → **A2's claim "header and main stop assembling every function body" verified at the ladder point where it previously failed** |
| `declaration_emittability_agreement` | **exit 1, `claim_falsified=1`** — CR3 (UNION_EMPTY first-refusal text) **still open in this candidate** (expected: diff does not touch `declaration_check`) — A2's separate action-4 debt |
| `bounded_emitter_attacks` | exit 0, **5/0** |
| `prereq_closure_attacks` | exit 0, **8/0** |
| `per_unit_cost_baseline` | exit 0, `byte_identity=True`, ratio **0.96** (wall-clock band across SHAs is 0.63–0.96 at N=2 — noise-dominated at 1–2 ms; the invariant held is byte identity, not the point ratio) |

## Observations (recorded, not defects)

1. **Instrument gap in `probe_c23_sections`:** at `--sizes 16` the probe **crashes with a
   traceback** (`require(checked…)` raises on `PEP_RUNTIME_STEP_LIMIT at 3674:5`) instead of
   reporting the checker-stage failure — the same graceful-reporting class A2 fixed for
   whole-emission refusals in `cbdce20`, still missing on the *checker* path. Their
   `probe_integration_case` handles it correctly (`check=PEP_RUNTIME_STEP_LIMIT`). Minor,
   instrument-only; the underlying 16-function checker limit is the known A1-boundary
   (unchanged; position `3674:5` matches A2's earlier citation).
2. **Governance timing note (for Lucy/A2, measurement only):** `LUCY-20261103-001` (00:46)
   instructs keeping `header/main/whole` documented as O(program); this candidate (00:48,
   minutes later, plausibly in-flight work) makes **header/main** succeed at size12 where
   they previously failed. Whole still fails (`all` step-limited) so *whole-program* O(program)
   documentation stands; whether the header/main documentation line updates is Lucy/A2's
   call — recorded, not adjudicated.

## Candidate-level status (integration lead)

- **This candidate is verified for its own claim** (header/main no longer assemble every
  body at measured ladder points 8/12; bounded-emission regression set green).
- **Mission acceptance still BLOCKED on the other two legs:** P1/`d158044` + discriminating
  checker cases (A1 fix absent) and CR3 agreement (exit 1 here). No whole-program or
  constant-cost claim is made; passing units ≠ passing the program (stated per mission).
- **Recommendation remains HOLD** until an A1 fix SHA and an A2 CR3 SHA land and the
  combined coexistence set runs.

## Reproduction

```powershell
python -m unittest tests.test_c23_bounded_emission            # 17/17
python tests\probe_integration_case.py --case all             # x3, bundle bb42fef8…
python tests\probe_c23_sections.py --sizes 8,12               # 12: header/main emitted, all STEP_LIMIT
python tests\probe_c23_sections.py --sizes 16                 # KNOWN: probe traceback at checker stage (observation 1)
python verification\probes\declaration_emittability_agreement.py <wt>   # exit 1 (CR3 open)
```
