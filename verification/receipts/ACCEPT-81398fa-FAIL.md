# Integrated candidate `81398fa` — Full-v2 **FAIL 14/15**, stale-binding repair **verified closed**, kind-crossing hole unchanged

**Date:** 2026-11-04 · **Mission:** LUCY-20261104-008 Queue C, A3 item 1 (gate CANDIDATE-5) · **Evidence label:** `TESTED`
**Candidate:** `codex/checker-emitter-integration` @ **`81398fa92fa34e623d680cc07f65c0e34172a27b`** — "Merge codex/p1-checker-cost-fix: source-attested binding facts (INTEGRATED-CANDIDATE-5)"
**Ancestry:** CANDIDATE-4 `cdbd742` + `codex/p1-checker-cost-fix@9ad7d95` (true merge of 3 A1-owned files, no B3 sweep).
**Tree:** `D:\Projects\wt-a3-int-81398fa` (detached, clean) · **Instrument:** `verification/**` on `codex/bootstrap-agent3-verification` @ this commit (runner `b464e00e…`, probe `688042d7…`, v1 `e5cad4df`/`e819607c`; manifest verified 13/13 at run time)
**Does NOT contain `ea0bc9a`** — A2's lane absent (as routed; nothing here tests native execution).

## Verdict: FAIL 14/15 — sole red gate is the 66-node row, unchanged by either repair

Full gate (`run_acceptance_gates.ps1 -Mode Full`): frozen-manifest ok, baseline-v2 ok, pack parse ok, combined emitter suites **53 tests OK**, stage probe x3 byte-identical, synthetic-12 ok, synthetic-8 ok, 7 probes ok (0 falsified), pack run ok (`NOT_OBSERV`ED-type exit 0 path). Red: discriminating rows `lexer=valid regression=PEP_RUNTIME_STEP_LIMIT`. `first_fail = discriminating rows`. No gate skipped.

Row-level (`exact_node_ladder.py`): **62 nodes ok / 64 nodes PEP_RUNTIME_STEP_LIMIT** — identical band to `cdbd742`. Both repairs cost the row nothing and move it nothing.

## Repair #2 (stale `BindingFact`) — **VERIFIED CLOSED**

A1 `9ad7d95`: `BindingFact` carries `document`/`revision`; `analyze_chunk_typed_bound` entry loop returns `invalid_report(..., "PEP_STALE_REVISION", ...)` for foreign/stale bindings; host `BindingPool(document, revision)` raises `ValueError` on stale/foreign/malformed/conflicting admissions, dedupes identical re-admissions, `facts()` deep-copies. Same-revision forgery remains a disclosed residual by design (labels ≠ authenticity; A4 authority-vs-labels).

`binding_pool_attacks.py` (interface-aware v2, this commit): **15/15 HELD, 0 falsified** at `81398fa` —
A1/A1b/A2/A3/A4/A5/A6 pool-unit claims held; B0/B1/B2/B3/B4 transport claims held;
**O1b** rev1 facts vs rev2 chunk → `invalid` + `PEP_STALE_REVISION` diagnostic;
**O1c** stale-fact reuse → `invalid` + `PEP_STALE_REVISION`, never believed.
Control at OLD pin `cdbd742`: interface detected OLD, **3 falsified** (A1b indistinguishable, O1b accepted-stale `valid`, O1c `with_stale=valid without=invalid seed=invalid`) — the exact fail-open A1 fixed. No false green.

Envelope note (the calibration in this commit): A1's refusal is `invalid_report` with the diagnostic code, **not** a tool-level `REFUSED:PEP_STALE_REVISION`. The probe now asserts `status=invalid` **and** the `PEP_STALE_REVISION` code (extracted from report diagnostics), strictly stronger than accepting any `invalid`. Prior WIP expected the REFUSED envelope; that expectation was wrong, not the candidate.

## Repair #1 (duplicate type declaration) — still closed

`dup_decl_minimiser.py`: **no flip reproduced** (81/111/114-byte fixtures all `invalid` both orders, seed `PEP_DUPLICATE_TYPE`); control M2 order-stable. `staged_metamorphic_matrix.py`: **13/13**. `staged_partial_provenance.py`: **9 cells 8 pass 0 fail 1 observed** (unchanged).

## Residual (open #1, unchanged): kind-crossing duplicate

`dup_decl_cross_chunk.py`: **9 claims, 2 falsified** — X3 (record then union namesake) and X6 (union then record) staged `valid` vs seed `invalid/PEP_DUPLICATE_TYPE`; X1/X2/X4/X5 held; X7 observation unchanged (`facts=0`, union-param body `PEP_UNKNOWN_TYPE`). Same mechanism as at `cdbd742` (only records resolve to external facts). Fix shape stands: emit union declarations as external type facts.

## Composition with A2's lane — not re-run this slice

Prior slice established seam 7/0 with the residual present in the scratch merge; A2 has not pushed a new cross-chunk result since (`ea0bc9a` unchanged), so Queue C A3 item 3 has no new artifact to check. Seam probe at `81398fa` alone: **7 cases, 0 falsified**.

## Reproduce

```powershell
pwsh -NoProfile -File verification\tools\run_acceptance_gates.ps1 -Mode Full -VerifyRoot <this-worktree> `
  -CombinedWorktree D:\Projects\wt-a3-int-81398fa -OutJson _build\accept-81398fa.json
python -X utf8 verification\probes\binding_pool_attacks.py  D:\Projects\wt-a3-int-81398fa
python -X utf8 verification\probes\dup_decl_minimiser.py     D:\Projects\wt-a3-int-81398fa
python -X utf8 verification\probes\staged_metamorphic_matrix.py D:\Projects\wt-a3-int-81398fa
python -X utf8 verification\probes\staged_partial_provenance.py D:\Projects\wt-a3-int-81398fa
python -X utf8 verification\probes\dup_decl_cross_chunk.py   D:\Projects\wt-a3-int-81398fa
python -X utf8 verification\probes\seam_cross_chunk_attacks.py D:\Projects\wt-a3-int-81398fa
python -X utf8 verification\probes\exact_node_ladder.py      D:\Projects\wt-a3-int-81398fa
```

## Limits

No native C23 build/run (Defender hold; `ea0bc9a` not in candidate). Same-revision forgery residual by design. The 66-node row needs ≈4 effective nodes of per-node budget. No master/CURRENT/manifest/budget changes. Builder receipts cited by SHA only; all verdicts above are independently measured in this session.
