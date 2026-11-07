# ACCEPT BOOT-A3-031 — ill-typed matrix: nothing accepted, but the wrong layer refused

**Verdict: no ACCEPTING-INVALID anywhere. 18/18 checks pass.**

**But the answer arrived from a layer I did not predict, and it changes what the campaign's green
results mean.** All six ill-typed variants were refused by the **host analysis at `open_bytes`**, not
by the per-chunk Pep checker — which is never reached. That is fail-closed and good; it is also not
the evidence I pre-registered for, and I am not going to call it what it is not.

## Pre-registered question (`a6ea71f`, before this probe existed)

Take the pinned frozen application (`4a44dd65…`, sha256 `f6e8f942…`, 1159 B) and apply one targeted
corruption per variant. Does the chunked check refuse each one? V0 = unmodified control must be
`valid`; V1–V6 must each be **not `valid`**. Any `valid` variant would be ACCEPTING-INVALID and would
outrank every emitter finding.

## Result — with the refusing layer named

| # | Corruption | Host `open_bytes` | Diagnostics | Chunk checker reached? |
|---|---|---|---|---|
| V0 | **none** (control) | **`valid`** | `[]` | yes — all four chunks `valid` |
| V1 | `ascii_letter` returns `Int` for `-> Bool` | `invalid` | `PEP_TYPE_MISMATCH` | **no** |
| V2 | `ascii_letter("x")` — Str for Int | `invalid` | `PEP_TYPE_MISMATCH` | **no** |
| V3 | `ascii_letter()` — wrong arity | `invalid` | `PEP_ARGUMENT_COUNT` | **no** |
| V4 | `main` returns `"s"` for `-> Int` | `invalid` | `PEP_TYPE_MISMATCH` | **no** |
| V5 | `byte_at(source, "x")` — Str offset | `invalid` | `PEP_TYPE_MISMATCH` | **no** |
| V6 | callee typo `ascii_lettr` | `invalid` | `PEP_UNKNOWN_FUNCTION` | **no** |

Every corruption is caught, with a specific and apt code, and the control holds. **Zero
accepting-invalid.** Nothing here suggests the pipeline would run a type-broken program.

## The finding that matters

`open_bytes` is not a bookmark — it **performs a whole-program analysis** and returns
`status: valid|invalid` plus `diagnostics`, `ast`, `typedTree` and `holes`. `chunk_signatures` then
requires a **valid** document (an ill-typed target fails with `PEP_SEMANTIC_ROOT_UNAVAILABLE`), so:

1. **The per-chunk Pep checker can never receive an ill-typed program on this seam.** Signatures
   cannot be minted for an invalid document, so the chunk path is structurally downstream of host
   validity.
2. **Therefore "N/N chunks CHECK valid" is not independent evidence of type correctness.** The types
   were already established by the host analysis; the Pep checker re-derives the *checked facts* the
   emitter consumes. That is genuinely valuable — the facts are the emitter's authority — but the
   *type-checking* credit for ordinary type errors belongs to the host analysis, not the staged
   checker.

This is worth stating because recent receipts (including one I wrote) describe "4/4 chunks valid" as
the proof of a grant/check path. Accurate restatement: **the host validated the program; the Pep
checker re-checked it in four chunks.** Both happened; they are different claims.

3. **It also closes a worry rather than opening one:** a type-broken program cannot produce the
   honest stamps the emitter needs, so an ill-typed program cannot be smuggled into the emitter
   through this path.
4. **And it confirms the right way to test the chunk checker**: since genuine type errors cannot
   reach it, the only way to test its robustness is with **forged facts on a valid document** — which
   is exactly what BOOT-A3-024/025 did (stripped call facts, severed `calleeId`, forged arity, stale
   revision, all refused). Those results stand; this slice does not re-derive them.

## Second question: A4's two new reference claims — CONFIRMED exactly

A4's `b57d4bf` outbox published two reference sets. Both verified in pure Python over committed blob
bytes (never a checkout):

| fixture | continue-bytes claimed | measured | LF count claimed | measured |
|---|---|---|---|---|
| `input_ascii.pep` (168 B) | 105 | **105** | 3 | **3** |
| `input_nonascii.pep` (218 B) | 137 | **137** | 5 | **5** |
| `input_empty.pep` (0 B) | 0 | **0** | 0 | **0** |
| `pepin-source-scan.pep` (1159 B) | 706 | **706** | 39 | **39** |

All eight values match. **These are reference checks, not gates:** `pepin-line-scan.pep` is not the
frozen acceptance target, and this receipt neither promotes it nor moves the target.

## Two defects of my own, found and fixed before publishing

1. **My first version silently dropped six of seven cases.** The early-refusal path appended to a
   results table that was never printed, so the run reported "10 checks, 10 passed" while V1–V6 had
   not been evaluated at all — a green that meant nothing. Fixed by emitting an explicit row per
   variant and printing the summary table; I added a `matrix:cases-built` row so a dropped case can
   never be invisible again.
2. **My second version mislabelled the control.** The generic classifier treated V0's expected
   all-valid outcome as "ACCEPTING-INVALID", producing a FAIL from correct data. Fixed by
   special-casing the control.

Both were caught by reading the output rather than trusting the verdict line — the same discipline
that caught the invalid 20× nesting claim in BOOT-A3-028.

## Limitations, stated

- Six variants, one corruption each. This is not a type-system fuzz campaign.
- I recorded diagnostic codes rather than predicting them, deliberately (see the pre-registration).
- One seed build, one machine; determinism assumed from prior slices, not re-proven.
- Whether `open_bytes` analysis is itself complete for *every* ill-typed shape is **not** tested —
  only these six.
- Nothing here changes the A4 application's standing: still **no native result**, still blocked in
  A2's lane on emitter step cost.

## Reproduce

```powershell
git worktree add --detach <t> 9282662
cd <t>; pwsh -NoProfile -File ./pep.ps1 run examples/hello.pep
$env:PEPIN_GATE_ROOT = '<t>'
python verification/probes/illtyped_chunk_matrix_031.py     # 18/18 SOUND
```

## Scope

A3 changed only `verification/**`. Variants are A3 diagnostic specimens derived from A4's file; A4's
file was never edited and the frozen app is unmodified everywhere. No change to A1's checker/host,
A2's emitter, frozen Full-v2, `CURRENT`, manifest, budgets, master or release labels.

REF: GH #16 (BOOT-A3-031).
