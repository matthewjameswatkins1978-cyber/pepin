# B4 Cycle-5 — Audit: A1 `9ad7d95` Binding-Fact Admission vs B4-R1/R3 + A3 Forged Claims

**Assignment:** LUCY-20261104-008, A4 task 2. **Branch:** `spec/agent4-spec-lab`
**Pins (source-read this slice, no execution):** A1 `9ad7d95`
(`fix(staged): source-attested binding facts`); parent contract `f4eb231`;
integration `81398fa`; A3 `0e94029` (O1c/O1b/A1b + S4/O4/G3 shapes, reported).
No implementation changed; audit only.

## 1. What A1 built (verified by diff-read of `9ad7d95`)

- `BindingFact` gains `(document, revision)`, stamped at production in
  `collect_bindings` (both arms) and carried through `infer_binding_types`
  (`tests/pep_checker_a13.pep` +25/-13 lines). Production-side stamping =
  the exact option B4-R1 §5 recommended ("one place, prefer production").
- Ingress guard in `analyze_chunk_typed_bound`: every external binding whose
  stamp differs from the target is refused with reused `PEP_STALE_REVISION`
  (no new code family — B4-AUTH-02 verbatim).
- `BindingPool(document, revision)` (`pep_chunk_contract.py` +102/-38):
  admits only same-revision attested facts; malformed / stale-foreign /
  conflicting admissions **raise `ValueError`**; identical re-admission
  dedupes silently; `_seen` maps identity-key → semantic payload
  (chunk-local ids excluded, correct per B4-AUTH-05); `facts()` deep-copies.
- No-bypass (source-read): the unbounded `analyze_chunk_typed` passes an
  EMPTY binding list; the only non-empty path into
  `analyze_chunk_inner_bound` is the guarded `_bound`. One ingress, guarded.
- A1's own code comment cites "A4 authority-vs-labels distinction" and states
  same-revision stamps are consistency, not authenticity — the B4-R1 position
  adopted explicitly, including the downstream-observation clause.

## 2. Obligation-by-obligation verdict

| B4-R1/R3 obligation | Verdict at `9ad7d95` |
|---|---|
| AUTH-01 identity on facts (bindings) | CLOSED — production-stamped `(document, revision)` |
| AUTH-02 same staleness guard, reused code | CLOSED — `PEP_STALE_REVISION`, single guarded ingress |
| AUTH-03 no silent conflict resolution | CLOSED — raise on conflict; silent path is identical-re-admission only (dedupe, not resolution) |
| AUTH-04 no pool-state aliasing | CLOSED — `facts()` returns `copy.deepcopy` |
| AUTH-05 renumbered ids are transport keys | CONSISTENT-BY-CONSTRUCTION — pool keys on source-anchored identity, never on chunk-local ids (inferred, not probe-tested) |
| R3: no PKI / second resolver / re-verification | HONORED — zero new machinery beyond one identity pair + one guard + one collision-relevant raise |
| B4-R3 R-ID-1 (supply-time fn-name collision check) | OPEN — diff touches no `find_function`/external-vs-local path; A1's disclosed residual stands |
| AUTH-01 for `CheckedFunction`/`ResolvedSignature` | OPEN — callee facts still carry no identity; S4/O4 self-consistent forgeries still admissible by design |

## 3. Residuals (stated, not defects in this fix)

- **Same-revision forgeries pass admission by design** (A1 states it; B4-R1
  §1 predicts it). Closure depends on the checker's downstream observation —
  which is exactly what T-AUTH-5 / the callee-identity work must now pin.
- **Interface break is real and A1-flagged:** `BindingPool()` requires
  `(document, revision)`; `add()` raises instead of returning silent 0. A3's
  `binding_pool_attacks` MUST be adapted (constructor scope + expect-raises)
  before the `81398fa` gate — running the old probe verbatim will error on
  construction, which proves nothing about the fix.
- **Evidence status:** all green counts (4+4 new tests, `utf8_check` 21/21,
  staged 55/55, A13+nested 72/72, `test_a14_c23` 10/11 with one A/B-proven
  pre-existing failure) are BUILDER-REPORTED at `9ad7d95`. Independent gate
  at `81398fa` is pending A3 — this audit changes no test status.

## 4. Test handoff to Agent 3 (adapts, not repeats, B4-R1 T-AUTH)

- T-ADM-1: adapt `binding_pool_attacks` to new constructor + expect-raises;
  O1c/O1b must now refuse `PEP_STALE_REVISION`; A1b must raise (not silent 0).
- T-ADM-2: identical re-admission still dedupes silently (no raise) —
  locks the dedupe-vs-conflict line.
- T-ADM-3: mutated egress fact does not affect a later chunk (deepcopy lock).
- T-ADM-4: S4/O4-shape same-revision forgery STILL ACCEPTED at admission
  (expected — documents the residual, does not fail the fix); file as the
  standing callee-identity obligation for R-ID-1 follow-up.

## 5. Status labels

AUDIT (not implementation): fix is conditionally complete — all five binding
obligations closed with the minimal mechanism B4-R1 specified, callee side
explicitly untouched. PROPOSED: T-ADM-1..4. REPORTED: A3 S/O/G shapes (cited,
not rerun); A1 green counts (builder-reported). UNKNOWN: `81398fa` gate
outcome; R-ID-1 landing SHA. Next A4 (queue task 3): rules→SHAs→oracle
evidence matrix — do NOT merge into this audit.
