# A1 handoff — minimal repros + expected codes for the three open product defects

**Date:** 2026-11-03 · **From:** Agent 3 (independent verification, LUCY-20261103-012) ·
**To:** Agent 1 (owner: host `pep_ocaml.ml`, chunk contract `pep_chunk_contract.py`, Pep-written checker `tests/pep_checker_a13.pep`), cc Lucy / Matthew
**Pinned candidate measured:** `codex/checker-emitter-integration` @ **`8396b63b34da75e3e17c1f49b5e1b2c5126ccd19`**
**Evidence label:** `TESTED` (every "ACTUAL" line below is a live run, not a reading)
**Agent 3 instruments unchanged:** frozen acceptance runner blob `e5cad4df`, every bat spec, every fixed gate expectation. This document and the two scripts are additive instruments, not gate changes.

LUCY-012 assigns the product repair to A1 and the instruments to A3. These are the smallest repros I can hand over: one script, one command, no Terror Bats, no probe framework, no edits to your tree.

## The single command

```powershell
# read-only: runs against your pinned worktree, changes nothing in it
python verification\repros\repro_host_defects.py <your-pinned-worktree>
# optional case filter
python verification\repros\repro_host_defects.py <your-pinned-worktree> IDX3 STALE1 CD3
```

Exit codes: `0` every expectation holds (defect absent — this is the pass condition), `1` at least one defect reproduced or expectation mismatched, `2` harness error (never reported as a verdict). Script: `verification/repros/repro_host_defects.py` (Agent 3 owned; safe to run at any pin).

## IDX3 — duplicate child edge accepted by `DocumentIndex`

- **Where:** `pep_chunk_contract.py`, `DocumentIndex.__init__`.
- **Repro:** two distinct siblings with identical `(parentId=0, role="statement", childIndex=0)`; index construction succeeds and plans/chunks can be built over it.
- **Measured at `8396b63`:** `ACCEPTED (index built over duplicate edge)`.
- **Why it is not cosmetic:** `(parent, role, childIndex)` is treated as a child key downstream (`child_at`, `count_children`, emitter fixed-slot routing). An ambiguous edge leaves "which child?" unanswerable while every existing identity check still passes. The contract's provable-piece rule already excludes two children with one edge identity in an authoritative parse.
- **EXPECTED (my handoff, owner may choose the naming):** refusal at index construction with **`CHUNK_DUPLICATE_NODE`** — same identity class, no new contract surface — **or** a newly declared **`CHUNK_DUPLICATE_EDGE`** added to the contract's `refusals` tuple and its doc. The repro accepts either.
- **Do not** renumber or silently drop a node to make the edge unique; the refusal is the guarantee.

## STALE1 — crossed provenance answered with a mislabelled empty report

- **Where:** host `pep_ocaml.ml` `session_semantic_target` / `tool_invoke` (provenance between `arguments` and `semanticTarget`).
- **Repro:** open a target, parse it (rev1), invoke `pep-c23-checker` with rev1-derived `arguments` and a matching rev1 `semanticTarget` (control: `ok`), advance the target with `apply_edit` to rev2, then invoke again with the **same rev1 arguments** under `{"revision": rev2}`.
- **Measured at `8396b63`:** `outcome=ok`, report `revision` = rev2, `syntaxNodeCount=0` — contentless analysis wearing the target's revision label. A consumer caching by `report.revision` stores a 0-node "rev2" result. That is the cache-poisoning shape, and it is the reason the CACHE1–3 claims matter.
- **Anchor:** `describe` publishes `"crossRevisionReuse": false`; the same-revision controls (CACHE1–3) and the matching-pair control pass, so this is a missing refusal, not a broken tools surface.
- **EXPECTED:** refusal (`outcome=error`) with a declared stale/provenance code. Suggested **`PEP_SEMANTIC_TARGET_STALE`** (declared in the session `describe` refusal inventory and the schema docs) — `PEP_TOOL_STALE_REVISION`, `PEP_STALE_REVISION`, `CHUNK_STALE_REVISION` or `PEP_SEMANTIC_TARGET_MISMATCH` are accepted by the repro. Either shape is fine: (a) refuse the crossed pair before the tool runs, or (b) refuse at the point the analysed data's revision is compared with the target revision. What must not survive is `ok` + a report labelled with the target revision.
- **Also expected (non-vacuity, already true):** a consistent pre-edit pair (args and target both rev1) stays invokable, and a fresh rev2 reparse answers correctly.

## CD3 — message parity between whole-source and chunked diagnostics (decision needed)

- **Where:** Pep-written checker messages, `tests/pep_checker_a13.pep` (e.g. `:1725` "Binding annotation is outside the implemented primitive checker subset", `:1740` "Record field type is outside the implemented checker subset") versus seed wording in `pep_ocaml.ml:413` (`Unknown type '<name>'`).
- **Repro (one fixture, `type Box { f: Nope }`):** same diagnostic, same code, same UTF-8 byte span.
- **Measured at `8396b63`:** code `PEP_UNKNOWN_TYPE`, span `11–18` on both paths;
  whole-source `"Unknown type 'Nope'"` vs chunked `"Record field type is outside the implemented checker subset"`. Codes and spans (the roadmap A13 standard) are preserved; only the wording differs, in 3/3 earlier fixtures.
- **Why I do not just relax it:** two of the three chunked messages are *subset-limitation* phrasings carried under a definite-condition code. In those fixtures the code is provably right (the seed proves the type genuinely unknown), so the wording conflates "cannot check" with "is unknown".
- **EXPECTED — one of two owner decisions, both acceptable to me:**
  - **(a) align** the chunked messages with the seed for the same `(code, span)`; the probe and pack child then pass unchanged; or
  - **(b) declare** message text outside the A13 guarantee for the chunk-contract path in the schema/docs. Then tell me so, and **I** downgrade CD3 to a dated observation inside `verification/probes/chunk_diagnostic_preservation.py` (verification-owned change, recorded in this branch's receipts). The pack child then passes on identity only.
- I will not change the bat or the probe's claim unilaterally: the manifest is mine, but the guarantee's scope is not mine to narrow.

## How a repair gets verified (unchanged instruments)

1. `python verification\repros\repro_host_defects.py <your-pinned-worktree>` → exit 0.
2. Unchanged pack children on your pinned tree:
   ```powershell
   terrorbats run verification\bats\index-cache-claims.yaml --repo <your-pinned-worktree> --json
   terrorbats run verification\bats\chunk-diagnostic-claims.yaml --repo <your-pinned-worktree> --json
   ```
   Expect `NOT OBSERVED` (currently `PROVEN` → `receipt:sha256:05c449d1…` and `9f572465…` on `8396b63`).
3. The frozen Full gate (`verification/tools/run_acceptance_gates.ps1 -Mode Full`) is run only on a **pushed combined successor of `8396b63`**; the 66n expectation is unmoved and the runner blob stays `e5cad4df`. A3 announces the SHA-bound verdict on #16.

## Boundaries I kept

- No builder file was edited, and no builder path was touched by these instruments.
- No bat, manifest, runner, budget, limit or gate expectation changed.
- Write side of this handoff: `verification/repros/**`, `verification/receipts/**`, `verification/probes/a2_scanner_differential.py` only (Agent 3 owned).
