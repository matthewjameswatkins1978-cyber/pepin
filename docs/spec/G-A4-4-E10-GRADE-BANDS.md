# G-A4-4 (E10) — Smallest Real Useful App: Triple-Backend Grade Bands

**Campaign G, Agent 4 card 4.** Fits CURRENT seed `57fe424` + emitter subset
(E2-B3: Int-only, lets+return, if-expression ternary, comparisons). No
implementation; sketch + acceptance only. Labels: ESTABLISHED / INFERRED.

## Why this app

A grade-band classifier is small but NOT a toy: its value is being the first
Pep program that must agree across THREE backends (seed interpreter, Clang,
GCC) on boundary values — a conformance anchor A3's native lane can adopt
verbatim. It exercises exactly the emitter's strongest path (comparisons +
ternary + checked arithmetic) and the checker's boundary diagnostics, with a
human-readable decision procedure (letter-grade bands) as the payload.

## Sketch (CORRECTED 2026-11-04 — as-written form does NOT lower; see below)

```pep
fn band(score: Int) -> Int {
  let g70 = if score <= 69 { 0 } else { 2 }
  let g80 = if score <= 79 { 0 } else { 3 }
  let g90 = if score <= 89 { 0 } else { 4 }
  return g70 + g80 + g90 + 1
}
fn main() -> Int {
  let probe = band(85)
  return probe
}
say(int_text(band(85)))
say(int_text(band(95)))
say(int_text(band(60)))
```

CORRECTIONS (independent review 2026-11-04; A3 adapted receipt
ACCEPT-GRADEBAND @ `1de76b62`): (1) the original sketch used `>=`, which the
seed does not lex (`PEP_UNEXPECTED_CHARACTER`; only `<=`/`==`/`!=`/`<`/`&&`/`||`
per seed source — the `<=` form above is PROVEN: A4 ran it, seed outputs
6/10/1). (2) Even the `<=` form does NOT lower as written: `return
g70+g80+g90+1` (lets + arithmetic) is REFUSED at emission — A3's adapted
native version restructures the mapping as nested if-expressions (same
10/6/3/1 outputs), and filed the refusal plus its misattributed diagnostic
("one/two-parameter calls require …", a call-site message on pure
arithmetic) to A2 as an open boundary finding. The "fits the native subset"
claim is therefore WITHDRAWN for the as-written form; it holds for A3's
adapted form, which is the live contract — cite the receipt, not this sketch,
for native work.

Band mapping (unchanged): 95 → 10; 85 → 6; 75 → 3; 60 → 1. Single-Int
encoding keeps the `main() -> Int` native contract (E2-B3). No Str, no
records. Calls: one pure callee (call-free body → no evaluation-order
hazard) — plus the noted lets+arithmetic emission gap.

## Accepted premises (ESTABLISHED)

Seed: `if` conditions require Bool (A3 set 8 TESTED); `>=` does NOT exist
(correction — only `<=`/`<`/`==`/`!=` per seed lexer); checked `+` traps
overflow (`PEP_RUNTIME_OVERFLOW`); `run` executes `main`?
NO — entry divergence (B4-R2, A3-F1): seed `run` executes TOP-LEVEL
statements, native executes `main`. The sketch therefore needs a top-level
`say(int_text(band(85)))` line for the seed path alongside `main` for the
native path — the divergence is DOCUMENTED in the program, not hidden.

## Acceptance (two positives, two negatives, human usefulness)

- **P1:** `pep.ps1 run` prints the top-level band value for 85 (seed oracle).
- **P2:** `build-c23` + Clang + GCC print identical values for boundary
  inputs 90/89/80/79/70/69 (A3 adapted: 7 inputs incl. 85, 14 parity cells
  + N1/N2 — PASSED). Oracle rule (correction 2026-11-04, from A3's own
  H-V5c probe-bug lesson): assert STDOUT text AND exit 0 — the C epilogue
  always returns 0, so exit code alone cannot distinguish value-output from
  harness failure (cf. E4-N-T4-2).
- **N1:** `band(true)` refused at check with `PEP_TYPE_MISMATCH`
  (fail-closed, demonstrates the subset edge).
- **N2:** literal `9223372036854775808` refused at check (Int64 static range,
  A3 set 6 TESTED) — no silent wrap anywhere.
- **Usefulness:** a teacher pastes 6 scores, gets 6 bands, identical on all
  three backends. Small, real, and its agreement property is load-bearing
  for Road 1 (first program whose cross-backend equality is the test).

## What A2 needs (corrected) / what is missing

CORRECTION: the as-written sketch is NOT inside the current emitter subset
(lets+arithmetic return refused; `>=` absent). Two open items for A2's lane:
(1) lets+arithmetic lowering (or an explicit decision that nested-if is the
canonical form — currently undocumented); (2) the misattributed refusal
diagnostic A3 filed. Missing for a bigger version: Str output of band names
(R1 LANDED at 2ad750b — recheck; list-of-scores input needs native List).
Both are explicit follow-ups, not blockers.

## Status labels

CONTRACT STATUS 2026-11-04: SUPERSEDED as written — the live contract is
A3's adapted ACCEPT-GRADEBAND receipt (same mapping, nested-if native form,
7×2 + N1/N2 green). This sketch remains the seed-oracle reference (ran
6/10/1). No lane blocked. Next: G-A4-5 (language-interaction boundary) or
G-A4-2 if A1 Q1 lands — workshop-next at handoff. Correction pass applied
(sketch operators, emission fit, oracle rule, A2 follow-ups).
