# E10 grade bands adopted (adapted): triple-backend parity 7×2 + N1/N2

**Date:** 2026-11-04 · **Mission:** Campaign G A3 (A4 E10 adoption note, AGENT4-20261104-023) · **Evidence label:** `TESTED`
**Contract:** A4 `G-A4-4-E10-GRADE-BANDS.md` @ `spec/agent4-spec-lab@aa54339` (read-only). ADOPTED with two adaptations (below); acceptance values preserved exactly (10/6/3/1).
**Pins:** native/seed via A2 `codex/a2-bounded-emission@0229e60` detached (clean; ignored `_build/` only); seed host opam pepin-5.5.2; Clang 23.1.4 + GCC 16.2.0 strict (`-std=c23/-c2x -Wall -Wextra -Wpedantic -Werror -O2`).
**Instrument (new, this commit):** `verification/probes/gradeband_parity.py` (7 scores × 2 compilers + N1/N2; A2-tree arg).
REF: GH #16 (this session, to be posted).

## Result: exit 0 — 14 parity cells + 2 negatives

| score | 90 | 89 | 80 | 79 | 70 | 69 | 85 | N1 | N2 |
|---|---|---|---|---|---|---|---|---|---|
| Clang | 10 | 6 | 6 | 3 | 3 | 1 | 6 | — | — |
| GCC | 10 | 6 | 6 | 3 | 3 | 1 | 6 | — | — |
| seed | 10 | 6 | 6 | 3 | 3 | 1 | 6 | invalid/TYPE_MISMATCH | invalid/INT_LITERAL_RANGE |

Seed files use top-level `let r = if…` + `say(int_text(r))` (if-STATEMENT refused at top level, if-EXPRESSION valid — measured G-A3-5); native files use final-if/return mains; values compared with the stated entry-point difference.

## Adaptations (contract does not execute as written — for A4 to correct the doc)

1. **`>=` is absent from Pep.** The sketch's `score >= 90` fails at parse (`PEP_UNEXPECTED_CHARACTER: Unexpected character '>'` — lone `>` refuses per A2's scanner work). Rewritten with `<=` (same semantics; `ascii_digit` precedent). A4's sketch needs the same one-character-class fix.
2. **Lets + arithmetic return does not lower.** `return top + mid + low + 1` (and even `return top + mid`, `return x + 1` over let-bound names) is refused — while bare `return top`, param arithmetic (`return a + 1`), and literal arithmetic all emit. Same 10/6/3/1 mapping restructured as nested if-expressions emits clean. Bisected shapes table in probe docstring/history.

## Finding for A2 (capability boundary + wrong message — no repair attempted)

Arithmetic over let-bound LOCALS is refused while the same operations over parameters/literals lower — asymmetric in a way that reads unintended (locals work bare, just not inside `+`). And every such refusal carries a MISATTRIBUTED diagnostic ("one/two-parameter calls require ... call-free ..." — a call-site rule message for a pure-arithmetic shape). Minimal repros: `return x + 1` (let-bound x) vs `return a + 1` (param) at `0229e60`. Fail-closed throughout (no unsoundness); message + boundary are the report.

## Reproduce

```powershell
python -X utf8 verification\probes\gradeband_parity.py D:\Projects\wt-a3-a2-0229e60  # exit 0
```

## Limits

One app, seven inputs, two negatives — the adopted boundary set, not a language proof. N1/N2 assert checker refusal (not native). No builder/spec files touched; A2 tree read-only + ignored scratch, left clean; no master/CURRENT/manifest/budget changes.
