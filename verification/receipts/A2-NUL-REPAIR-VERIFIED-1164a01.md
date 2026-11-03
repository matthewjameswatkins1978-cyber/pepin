# A2 escaped-NUL repair verified at `1164a01` — position now lossless, no regression in the symbol scanner

**Date:** 2026-11-03 · **Lane:** Agent 3 independent verification (PEP-A3-SUSTAINED-013 slice 5: recheck a resolved defect without rewriting the acceptance criterion) · **Evidence label:** `TESTED`
**Repaired pin:** `codex/a2-bounded-emission` @ **`1164a01d1ac9aed1bc048c872d7f439c3c1bbdf6`** ("fix(stdlib): lossless ordered NUL fragments in string scanning")
**Unrepaired pins for contrast:** `68e72bf` and `9d4ab42`
**Instruments:** `verification/probes/a2_scanner_differential.py` and `a2_symbol_differential.py` — the **same** claims, run unchanged against both pins.

## Result — one criterion, two pins, opposite verdicts

| claim | at `68e72bf` (before) | at `1164a01` (after) |
|---|---|---|
| **S1** Int64 max accepted, exact value | HELD | HELD |
| **S2** max+1 refused, seed agreement | HELD | HELD |
| **S3** negative offsets refuse without raising | HELD | HELD |
| **S4** escape-set parity, decoded bytes exact | **FALSIFIED** — `\0`: `parts` `""` ≠ seed `00` | **HELD** — 6 accepted, 2 refused, bytes exact |
| **S5** escaped-NUL **position** distinguishable | **FALSIFIED** — `"\0ab"` and `"ab\0"` identical | **HELD** — `"\0ab"` → parts `["\u0000","ab"]`; `"ab\0"` differs |
| summary | `claim_falsified=2` | **`claim_falsified=0`** |

Symbol scanner re-run at the repaired pin: **P1–P5 all HELD** (`claim_falsified=0`) — the NUL work did
not disturb the byte-set parity, the seven two-byte forms, the no-over-munch boundary, whole-character
Unicode refusals, or EOF/CRLF separators.

## What "lossless" was checked to mean

The scanner now emits the NUL as an ordered fragment rather than only counting it:

- `"\0ab"` → `parts = ["\0", "ab"]`, `nulCount = 1`, `byteLength = 6` (literal source width), seed
  decoded bytes `00 61 62`;
- `"ab\0"` → a different `parts` sequence for the same `nulCount`, seed bytes `61 62 00`;
- `"\0"` → `parts = ["\0"]`, matching the seed's single `00` byte exactly.

So NUL **content, count and position** are all recoverable from the scanner's output, which is the
condition the earlier receipts named before the repair. The residual limitation that a Pep `Str`
*value* cannot contain a NUL is a language property, not a scanner omission, and is no longer
conflated with it.

## Criterion integrity (what changed and why it is not a relaxation)

S4 previously compared the scanner's `parts` against the seed's decoded bytes **with the NULs
stripped**, because the old scanner could not carry a NUL at all. After the repair that comparison is
wrong in the *strict* direction, so it now demands exact byte parity **including** the NUL. This
tightens the claim; it cannot make an unrepaired scanner pass — demonstrated by the identical
instrument still falsifying `68e72bf` on the same run.

S5's `expect`/`outcome` plumbing was corrected in the process: the harness compared a descriptive
`expect` string against a short `outcome` token, so a *distinguishable* (i.e. repaired) result was
initially printed as `FALSIFIED` while carrying the `HELD` label. That is the fourth instance of the
same helper-shaped mistake in this session (a string comparison standing in for a boolean), now
recorded as a pattern rather than a one-off: every case must compare canonical tokens, and a verdict
must be derivable from a boolean, not from prose equality.

## Honest scope

- Scanner/tool layer only; no emission, no native build, no execution.
- Two pins, one pass each; `1164a01` was measured after its push, not before it existed.
- The probe's NUL cases remain four fixtures (`"\0ab"`, `"ab\0"`, `"\0"`, embedded NUL byte via
  caller-materialised bytes) — not an exhaustive exploration of interleaved NULs; an interleaved
  case (`"a\0b\0c"`) is now cheap to add if A2 wants the stronger statement.

## Reproduce

```powershell
python verification\probes\a2_scanner_differential.py D:\Projects\wt-a3-a2-1164a01   # exit 0
python verification\probes\a2_scanner_differential.py D:\Projects\wt-a3-a2-68e72bf   # exit 1 (S4/S5)
python verification\probes\a2_symbol_differential.py  D:\Projects\wt-a3-a2-1164a01   # exit 0
```

## Next action

Reported to A2 on #16 as the repair verification. The symbol scanner's regression set (P1–P5, S1–S4)
is green at `1164a01`; if a token-stream driver lands, the next slice is a full token-stream
differential (names, numbers, strings with NULs, comments, holes, operators) against the reference
lexer on real sources.
