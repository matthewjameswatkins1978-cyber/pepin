# FINISH K4 — record-result blocker, seed-tested + runnable A2 handoff

TESTED at seed (`57fe424` campaign tree, `pep.ps1`, `_build/k4/`, ignored
scratch). No native run claimed — native execution is A2/A3's lane.

## P1 (positive, L3-verbatim + driver): PASS

`p1_record_return.pep`: `check --json` → **valid**, zero diagnostics.
`run` → exit 0; oracle probe (top-level `say`, same file shape as H1 P1)
prints `2/1/4/8`: advance_position(1,1,10)→(2,1),
advance_position(4,7,65)→(4,8). Seed semantics of the real lexer
function confirmed on the exact bytes, including the newline branch.

## P2 (negative, L4-shape type error): REFUSED correctly

`p2_record_mismatch.pep` (`text: 0` against `text: Str`): `check` →
**invalid**, `PEP_TYPE_MISMATCH`, "Expected Str but found Int", exit 1.
The field-type gate fires on record construction as required — a
record-return path built on this gate does not launder.

## What this decides

K4's falsifier (record returns already lower) did NOT trigger — the
RECORD_PROGRAM fixture still covers only params+literals, and P1 is the
first record-returning program through the seed gate in my lane. The
candidate stands UNFALSIFIED: function-result records remain the one
primitive gap, marginal 3 lexer functions (L3/L5 now, L4 next).

## Runnable A2 handoff (exact, no reconstruction needed)

1. Seed baseline (both green above, rerun to confirm):
   `.\pep.ps1 check _build/k4/p1_record_return.pep --json` (expect valid)
   `.\pep.ps1 check _build/k4/p2_record_mismatch.pep --json` (expect
   PEP_TYPE_MISMATCH)
2. Native attempt, A2's lane at `123d8b3` + A1 `727f8af` (or current A1
   head if the re-pin has moved): drive P1 through the seam probe's
   chunk path (4-chunk shape or staged single), emit header/units/
   epilogue, strict Clang+GCC, seed oracle `2/1/4/8`.
3. Branch the outcome IN ADVANCE (either routes correctly):
   - lowers → L3/L5 reachable; F3's conditional rule was Str-specific.
     Next: L4 shape (Str fields + list args).
   - refuses with the conditional-return diagnostic → the ONE rule
     blocking the lexer header is named; that diagnostic (not a new
     primitive) is A2's next slice.
   - refuses with anything else → new finding; report verbatim.
4. Limits: <1 KB programs, unchanged 100k steps, both compilers + seed
   oracle. No baseline suite.

Falsifier of THIS doc: any seed-run output above that does not
reproduce (`2/1/4/8`, exit 0; P2 `PEP_TYPE_MISMATCH`, exit 1).
