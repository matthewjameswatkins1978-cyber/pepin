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

## Sketch (fits the native subset — INFERRED lowerable, not compiled here)

```pep
fn band(score: Int) -> Int {
  let top = if score >= 90 { 4 } else { 0 }
  let mid = if score >= 80 { 3 } else { 0 }
  let low = if score >= 70 { 2 } else { 0 }
  return top + mid + low + 1
}
fn main() -> Int {
  let probe = band(85)
  return probe
}
```

Band mapping: ≥90→5? No — arithmetic: score 95 → 4+3+2+1 = 10; 85 → 0+3+2+1
= 6; 75 → 0+0+2+1 = 3; 60 → 0+0+0+1 = 1. Distinct outputs per band (10/6/3/1)
— single-Int encoding keeps the `main() -> Int` native contract (E2-B3).
All forms used are in-bounds: Int literals, `>=` comparisons (emitter lowers
comparisons inline), if-expressions (ternary), `+` (checked `pep_add`),
direct lets + one return. No Str, no records, no calls beyond one pure
callee (call-free body → no evaluation-order hazard).

## Accepted premises (ESTABLISHED)

Seed: `if` conditions require Bool (A3 set 8 TESTED); `>=` on Ints valid;
checked `+` traps overflow (`PEP_RUNTIME_OVERFLOW`); `run` executes `main`?
NO — entry divergence (B4-R2, A3-F1): seed `run` executes TOP-LEVEL
statements, native executes `main`. The sketch therefore needs a top-level
`say(int_text(band(85)))` line for the seed path alongside `main` for the
native path — the divergence is DOCUMENTED in the program, not hidden.

## Acceptance (two positives, two negatives, human usefulness)

- **P1:** `pep.ps1 run` prints the top-level band value for 85 (seed oracle).
- **P2:** `build-c23` + Clang + GCC print identical `main` values for
  boundary inputs 90/89/80/79/70/69 (6/6 agree — the actual conformance
  payload; a human reads grade bands off it).
- **N1:** `band(true)` refused at check with `PEP_TYPE_MISMATCH`
  (fail-closed, demonstrates the subset edge).
- **N2:** literal `9223372036854775808` refused at check (Int64 static range,
  A3 set 6 TESTED) — no silent wrap anywhere.
- **Usefulness:** a teacher pastes 6 scores, gets 6 bands, identical on all
  three backends. Small, real, and its agreement property is load-bearing
  for Road 1 (first program whose cross-backend equality is the test).

## What A2 needs (nothing new) / what is missing

Nothing new: the sketch stays inside the CURRENT emitter subset by
construction — that is the design criterion. Missing for a bigger version:
Str output of band names (needs R1 `str_concat`, G-A4-1) and list-of-scores
input (needs native List, A2 lane). Both are explicit follow-ups, not
blockers.

## Status labels

CONTRACT (not code): sketch + 6-case acceptance a builder or A3 can execute
as-is. No lane blocked. Next: G-A4-5 (language-interaction boundary) or
G-A4-2 if A1 Q1 lands — workshop-next at handoff.
