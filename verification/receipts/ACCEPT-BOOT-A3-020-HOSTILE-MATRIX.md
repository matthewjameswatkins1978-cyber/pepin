# BOOT-A3-020: minimum hostile test matrix BEFORE sourceGrant/Option-A integration (Agent 3)

**Seat:** Agent 3, per LUCY-20261106-006 item 3 (A3 → A1 AND A2). Review-only; no builder
edits. Every row below is MEASURED (receipt cited) on a published SHA — no hypothetical cases.

## Matrix (required hostile case → covering probe → measured result → gap)

| # | Required hostile case | Covering probe (A3-run, unmodified) | Measured result | Gap |
|---|---|---|---|---|
| H1 | missing grant / target | `probe_source_grant_entry.py` neg-no-grant (A3 BOOT-A3-016 @ `935c331`) | `PEP_RUNTIME_SOURCE_CONTEXT`, exit 1 | none |
| H2 | foreign target bytes | `source_ingress_negative` G3 (BOOT-A3-005 @ `6dce37d`); K1 B1 (BOOT-A3-002) | refused w/ provenance code; `PEP_STALE_REVISION` | none |
| H3 | stale revision | `source_ingress_negative` G1/G2 (BOOT-A3-005); K1 B2; pooled hostile suite (A3 BOOT-A3-012) | refused (`STALE_REVISION` / `A13_PARSER_BUDGET`); pool propagates fail-closed | none |
| H4 | forged same-target fact | K1 A3 param admitted (BOOT-A3-002); K1b result/arity refused (BOOT-A3-006); K1c carried-used refused (BOOT-A3-008, on candidate too BOOT-A3-018) | split: param ADMITTED (residual, disclosed); result/arity/used-carried REFUSED | residual open by design — content binding is the priced fix, never claimed |
| H5 | no ambient bytes | grant probe neg-source_bytes-call + seed-oracle SKIP analysis (BOOT-A3-016) | call refused ("no resolved call fact"); seed refuses ambient (`SOURCE_CONTEXT`); only v2-grant path grants | full seed-vs-native equality on granted bytes awaits A1's v2-grant run path (residual, stated) |
| H6 | missing-return semantic residual | disclosed in draft §Terminality + module docstring (A3 BOOT-A3-010 review); A1 trial 1019234 context | whole-check absent-return diagnostic NOT reproduced by slices | **no A3 probe asserts the boundary behaviorally** — accepted as disclosed residual; re-gate will re-check it if the plan-tier integration claims otherwise |
| H7 | wrong field type / span | K4 P2 (`PEP_TYPE_MISMATCH`, exact span, BOOT-A3-004); mc-seam neg (L29 C13, BOOT-A3-017); pooled suite first_refusal surfacing (BOOT-A3-012) | all refuse with named codes and pinned spans | A4's doc absolute offsets off by 28 (footnote BOOT-A3-017) — cosmetic, A4 to amend |

## Standing review inputs (unchanged, now matrix-anchored)

- sourceGrant draft: ENDORSED as designed pending integration proof; re-gate checklist
  (BOOT-A3-013) armed for A1's feature SHA. H5 residual is the one to close there.
- Option A amendment: ENDORSED with both conditions satisfied and re-verified
  (BOOT-A3-007/010/012); H4 residual is the disclosed inheritance, not a blocker.
- Frozen Full-v2 rows are never relabeled; new integration SHA gets a fresh full gate.

## Reproduce

All rows re-runnable from their cited receipts against the pinned SHAs therein.
`
