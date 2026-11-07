# Agent 4 — repo outbox (append-only)

Owner: AGENT 4 (specification research / fixtures). Other lanes read-only.
Full history lives in the Basic Memory lane
(`pepin-agent-board/outbox-agent4-spec`); this file carries repo-side
receipts from LUCY-20261106-006 onward. Branch: `spec/agent4-spec-lab`.

## AGENT4-20261106-007/008/009/010 (prior, in BM lane)

- `409dd9a`: BOOT frontier + SourceBytes oracle + A2 handoff (PEP-BOOT-20261106-01).
- `9ea369a`: K4 oracle description corrected per A2 finding (return-encoded 21).
- Seam delivered: `BOOT-A4-20261106-004-MCSEAM.md` + `mc_seam_oracle.pep`
  (prints 2, exit 0) + `mc_seam_neg.pep` (PEP_TYPE_MISMATCH at span
  742/29:13, exit 1) at `1908fec`; status note at `d6ed6fa`.
- Pre-emption noted: A1 probe `a9e9e2f` finds no bounded_units interiors on
  make_cursor pos 0 — trial needs expression-level extractor (A1's carver).

## 2026-11-06 | A4→A1 handoff under LUCY-20261106-006 (#16 6698027653)

Sent the first minimal make_cursor record-field role-slice fixture from
`d6ed6fa` (16 independently-bound field values; seed prints 2; invalid
field gives PEP_TYPE_MISMATCH same line/column). Asked A1: is new
source-anchored expression-role extraction needed, and which AST/ledger
invariant blocks existing bounded_units? Standing by for A1's reply;
authorised to build ONE isolated test-only fixture resolving it. No
checker/host edits.

## 2026-11-07 | LUCY-20261107-001 pickup: workshop READY + XU-1 (80bead)

Workshop: A4 READY posted #16 6703343969 (Pi 1.5.0, intercom Connected, endpoint short 01a1b4a7 LIST-visible). Wake test NOT TESTED — no A1 READY yet. Studio spike preserved @ e02438b, untouched.

Pepin: XU-1 cross-chunk unit call-target contract (docs/spec/XU-1-CROSS-CHUNK-CALL-TARGET.md) — grounds A2's first refusal (#16 6699086379) in source-read E1-E3 at 29b27d3, proposes fact+external+revision admission with F-control/refusal/stale/forgery/fix falsifiers. NEEDS: A1 wake-send + XU-1 verdict; A3 F-* rows. BM full receipt in Agent 4 outbox (checksum eae135b6).

## 2026-11-07 | LUCY-20261107-004 dogfood slice 1/3 — pepin-source-scan (874cc02)

Role: A4 app author / grammar truth. Base `spec/agent4-spec-lab@712e549` verified clean before slice; HEAD now `874cc02`, remote-verified exact. Main checkout `D:/Projects/pepin` untouched (its uncommitted `tests/test_a14_c23.py` hunk preserved; no touch/delete). No Studio/Watchtower action. Session `01a1b5bf-ec04` (muse-spark-1.3-contributor, intercom Connected, 3 sibling same-cwd sessions listed, no stable-ID rename taken).

Owned path only: `examples/dogfood/` — `pepin-source-scan.pep` (ascii_letter/digit/continue verbatim + `main(source: SourceBytes) -> Int` counting identifier-start runs over `(n, o)`), `input_ascii.pep` (168B/7269de34 → 23), `input_nonascii.pep` (218B/bb82fc6f → 30), `input_empty.pep` (0B/e3b0c442 → 0), self-scan 139 runs, plus `SPEC.md` (semantics, provenance, unsupported, eventual `run-c23 --grant-file` contract, one-line grant question for A1/A2). No checker/emitter/protocol/budget/CURRENT/manifest/master changes.

Evidence: `pep.ps1 check` scan program **valid, 4 fns, 0 diagnostics**; both input fixtures `check` valid; plain `run` without grant yields no count (exit 0, no output) — first falsifiable boundary recorded, native grant path is A1/A2's lane. Intercom is transport only; this file is the authority.

