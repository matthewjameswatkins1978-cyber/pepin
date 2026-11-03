# Minimal host-defect repros at `8396b63` — IDX3 / STALE1 / CD3 all reproduce, now one command for A1

**Date:** 2026-11-03 · **Lane:** Agent 3 independent verification (LUCY-20261103-012 "reconstruct minimal reproducible IDX3/STALE1 and CD3 ... hand exact repro and expected codes to A1") · **Evidence label:** `TESTED`
**Pin:** `codex/checker-emitter-integration` @ **`8396b63b34da75e3e17c1f49b5e1b2c5126ccd19`**, worktree `D:\Projects\wt-a3-int-8396b63` (clean, unchanged by these runs)
**My HEAD:** `codex/bootstrap-agent3-verification` · worktree clean at start
**Instrument:** `verification/repros/repro_host_defects.py` (new, standalone; no Terror Bats, no probe framework, no writes to the target worktree)
**Handoff document for the owner:** `verification/repros/A1-HOST-DEFECT-HANDOFF.md`

## Why a second instrument

The three defects were already SHA-bound in `INDEX-CACHE-adversarial-05add76.md` and
`CHUNK-DIAGNOSTIC-PRESERVATION-05add76.md`, and the frozen pack re-proved them at `8396b63`.
That is good acceptance evidence but a poor **repair** artifact: the owner had to read a probe
harness to find one case. This receipt records the reduction to three ~20-line cases, each with an
exact expected refusal code instead of "any refusal", so a repair can be judged without reading any
of my other code.

## Runs (each command run separately, exit codes as reported)

```powershell
python verification\repros\repro_host_defects.py D:\Projects\wt-a3-int-8396b63 IDX3     # exit 1
python verification\repros\repro_host_defects.py D:\Projects\wt-a3-int-8396b63 STALE1   # exit 1
python verification\repros\repro_host_defects.py D:\Projects\wt-a3-int-8396b63 CD3      # exit 1
```

| case | expected | measured at `8396b63` | verdict |
|---|---|---|---|
| **IDX3** duplicate child edge | refusal at `DocumentIndex` construction with `CHUNK_DUPLICATE_NODE` (or declared `CHUNK_DUPLICATE_EDGE`) | `ACCEPTED (index built over duplicate edge)` | **DEFECT** |
| **STALE1** crossed provenance | `outcome=error` with a declared stale/provenance code | `outcome=ok`, report `revision` = **rev2**, `syntaxNodeCount=0` | **DEFECT** |
| **CD3** message parity | same message for identical `(code, span)` | code `PEP_UNKNOWN_TYPE` span `11–18` on both paths; whole `"Unknown type 'Nope'"` vs chunked `"Record field type is outside the implemented checker subset"` | **DEFECT** |

Exit 1 in all three cases is the *reproduction* result, not a harness failure; the script returns 2
and prints `HARNESS_ERROR` for anything that is not a verdict (verified: an earlier draft of this
session's A2 probe hit exactly that path and was repaired rather than reported).

Consistency with the frozen record: identical code and span, identical wording, identical
`syntaxNodeCount=0` shape as `INDEX-CACHE-adversarial-05add76.md` and
`CHUNK-DIAGNOSTIC-PRESERVATION-05add76.md`. Nothing was re-scoped or re-worded to make the
reproduction easier.

## Expected-code decisions handed over (not imposed)

- **IDX3** — prefer `CHUNK_DUPLICATE_NODE` (existing identity class, no new contract surface);
  a new declared `CHUNK_DUPLICATE_EDGE` in `pep_chunk_contract.py`'s `refusals` tuple is equally
  acceptable. The repro accepts either and still reports `MISMATCH` for an undeclared code, so a
  fail-open repair cannot pass as a complete one.
- **STALE1** — `PEP_SEMANTIC_TARGET_STALE` suggested; `PEP_TOOL_STALE_REVISION`,
  `PEP_STALE_REVISION`, `CHUNK_STALE_REVISION`, `PEP_SEMANTIC_TARGET_MISMATCH` also accepted.
  The anchor is the published `"crossRevisionReuse": false`, so the refusal must exist somewhere;
  only its name and stage are the owner's call.
- **CD3** — an owner decision, not a code: align the Pep-written messages with the seed, or declare
  message text outside the A13 guarantee. I will not narrow the guarantee myself; on a documented
  decision I downgrade CD3 to a dated observation inside the probe (verification-owned change).

## Non-vacuity

The STALE1 case asserts its own control first: the **matching** rev1-args/rev1-target invoke must
return `ok` before the crossed pair is judged, so "tools broken" cannot read as a defect. CD3
asserts exactly one diagnostic on each path before comparing, and aborts on any chunk reporting a
span outside its own node intervals. IDX3 is a pure index construction with no host involvement.

## Boundaries

Builder files untouched (`pep_ocaml.ml`, `pep_chunk_contract.py`, `tests/pep_checker_a13.pep` all
read-only here). No bat, manifest, frozen runner, budget, limit or gate expectation changed. New
write-side files: `verification/repros/repro_host_defects.py`,
`verification/repros/A1-HOST-DEFECT-HANDOFF.md`, this receipt, and `INDEX.md`'s entry.

## Next action

Reported to A1 on #16 with the handoff document. Acceptance of any repair stays with the unchanged
instruments: the repro exiting 0 **and** the two unchanged pack children flipping `PROVEN` →
`NOT OBSERVED` on A1's pushed tree; the frozen Full gate runs only on a pushed combined successor
of `8396b63`.
