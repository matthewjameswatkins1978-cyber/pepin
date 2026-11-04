# G-A3-5: real canonical-lexer `ascii_digit` — native parity both compilers + checker negative

**Date:** 2026-11-04 · **Mission:** LUCY-20261104-013 / Campaign G A3 G-A3-5 · **Evidence label:** `TESTED`
**Target:** `ascii_digit`, verbatim from `examples/pep_lexer.pep` (canonical lexer, A2 tree `59cde2f`): `return 48 <= byte && byte <= 57` — a one-expression boolean-chain body, same expression class as the 66n/S2 critical path, isolated from checker budgets by tininess.
**Instrument (new, this commit):** `verification/probes/native_parity_ascii_digit.py` (positive T/F × Clang/GCC + say-Bool negative; needs an A2 worktree arg for host/seed/toolchains).
**Toolchains (live):** Clang 23.1.4, GCC 16.2.0, seed rebuilt via opam pepin-5.5.2.
REF: A2 BOOT-A2-20261104-020 (say method mirrored); GH #16 (this session, to be posted).

## Result: PARITY 4/4, negative refused at the checker

- True case (byte 53) / false case (byte 65), native final-if mains → strict Clang AND GCC build clean, run echoes `1` / `0`; seed (same fn + top-level let/if-expr/say) prints `1` / `0`. **Same value both sides, all four cells.** Entry-point difference handled by A2's method (native echo vs seed say — values compared, channels stated).
- Negative `say(ascii_digit(53))`: checker refuses `invalid/PEP_TYPE_MISMATCH` ("Expected Str but found Bool") before the emitter runs — corrected framing (checker-layer boundary, fail-closed), not an emitter refusal.

## Incidental measured findings (for owners, not defects in this slice)

1. Seed top-level `if` STATEMENT is refused (`PEP_PARSE_EXPRESSION: Expected an expression`); `if` as EXPRESSION (`let r = if (c) {1} else {0}`) is valid. Oracle shaped accordingly (A4 entry-divergence context).
2. `powershell.exe` (5.1) CANNOT run `pep.ps1 check` on this machine (`Get-FileHash` unrecognized); `pwsh` 7.6.9 works. A2's test files hardcode `powershell.exe` — their `describe`/seed path evidently worked (seed exe got built), but any `check` subprocess through that binary fails. Driver uses `pwsh`; A2 may want the same one-word change. No A2 files touched.

## Reproduce

```powershell
python -X utf8 verification\probes\native_parity_ascii_digit.py D:\Projects\wt-a3-a2-59cde2f  # exit 0
```

## Limits

One function, two bytes, one negative — a spot vertical, not a lexer proof. No builder files touched (A2 worktree used read-only + ignored scratch, left clean); no master/CURRENT/manifest/budget changes.
