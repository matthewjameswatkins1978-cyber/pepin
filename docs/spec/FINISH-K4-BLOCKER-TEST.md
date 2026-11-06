# FINISH K4 — record-result blocker, seed-tested + runnable A2 handoff

TESTED at seed (`57fe424` campaign tree, `pep.ps1`, `_build/k4/`, ignored
scratch). No native run claimed — native execution is A2/A3's lane.

## P1 (positive, L3-verbatim + driver): PASS

`p1_record_return.pep`: `check --json` → **valid**, zero diagnostics.
`run` → exit 0 with no stdout; the oracle is return-encoded (`p.line * 10 +
`p.column` = 21 for advance_position(1,1,10)→(2,1)), not printed.
CORRECTION 2026-11-06 (A2 BOOT-A2-20261106-03, measured at `727f8af` and
`57fe424`): the earlier "prints `2/1/4/8`" phrasing does not reproduce —
the committed fixture contains no `say`, and a naive `say(a.line)`
reconstruction is `PEP_TYPE_MISMATCH` (`say` takes `Str`). The
(4,7,65)→(4,8) case is not in the committed fixture; A2's committed probe
prints `2\n1\n4\n8\n` via `say(int_text(...))`. The fixture carries a
local verbatim copy of the L3 logic, not the real lexer function.
Values confirmed; call-shape claim retracted.

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

Falsifier of THIS doc: `check` on the committed fixtures not returning
valid/exit 0 with return-encoded 21 for P1, or anything but `PEP_TYPE_MISMATCH`
exit 1 for P2; or an A2 probe run contradicting the branched handoff outcomes.
