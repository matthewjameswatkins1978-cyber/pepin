# XU-1: cross-chunk unit call-target admission contract

STATUS: PROPOSED (spec only). No implementation, no freeze, no builder edits.
REF: LUCY-20261107-001 (A4 Pepin resume slice); A2 first-refusal receipt #16 6699086379;
     A2 `codex/a2-bounded-emission@29b27d3`; A1 `codex/a1-typed-bound-pipeline@a7d3ee1`.
BRANCH: `spec/agent4-spec-lab`. Pins verified live by fetch 2026-11-07 (both SHAs match dispatch).

## 1. ESTABLISHED (source-read at 29b27d3, no execution by A4)

E1. A unit call lowers only when `pep_c23_function(nodes, name)` finds the callee in the
    SAME node list (`tests/pep_c23_emitter.pep`, `let target = pep_c23_function(nodes,
    value.text)`; `fn pep_c23_function(nodes: List[FlatAstNode], name: Str)` is a
    same-list name scan).
E2. When the scan misses, the emitter returns
    `pep_c23_unsupported("Pep C23 calls require a known target")` (line ~2855); a second
    gate checks the result type (scalar/Str/record/union, line ~2871).
E3. In a chunked unit only one function's nodes are present, so a cross-chunk callee name
    is absent BY CONSTRUCTION — the refusal is structural, not a missing-fact accident.
    A2's report confirms the chunk report DID carry two RESOLVED call facts for exactly
    those calls (`calleeId` 9000/9001, `syntaxId` 6/8) with matching `semid` externals,
    and the emitter still refused: **the emitter never consults call facts**.

## 2. REPORTED (builder-tested, A4 labels INFERRED until rerun)

R1 (A2 #16 6699086379): chunked check of all 4 lexer+main functions valid (10–29 nodes
each, at A1 a7d3ee1); units `ascii_letter`, `ascii_digit` emit; unit `ascii_continue`
(2 cross-chunk calls) refuses with the E2 diagnostic. Probe:
`python tests/probe_grant_lexer_chunked.py` at A1 a7d3ee1.

## 3. Proposed rule XU-1 (for A2 to accept/adapt/reject; A1 facts unchanged)

A unit emitter invoked on chunk C with externals E MUST resolve a call target by the
first matching route, in order:
  (a) same-chunk syntax nodes (E1 behaviour, UNCHANGED — no regression allowance);
  (b) the chunk report's resolved call fact for that call site (by `syntaxId`) PLUS an
      external in E whose identity matches the fact's `calleeId`, whose revision equals
      C's revision, and whose declared signature the call satisfies;
  (c) otherwise refuse with the E2 diagnostic (fail-closed preserved).

Explicit non-goals: no assembly/linking design, no checker change, no budget change,
no new wire fields, no same-document trust weakening (K1 authority-vs-labels model
stands: facts are claims about ANOTHER document, so route (b) trusts fact+external
AGREEMENT, never a fact alone).

## 4. Falsifiers (A3-adoptable; all runnable at 29b27d3 + a7d3ee1)

- F-control (must PASS before and after): same-chunk call unit emits.
- F-refusal-preserved (must refuse pre- AND post-fix): cross-chunk call with NO resolved
  fact, or with externals whose `semid` does not match, refuses "known target".
- F-stale: report revision != chunk revision with otherwise matching facts refuses
  (stale guard, cf. T-QH-3 precedent).
- F-forgery: a `calleeId` naming a same-chunk function whose bytes differ from the
  external's declared body must NOT be trusted over syntax (fact alone is insufficient).
- F-fix (post-fix only): `ascii_continue` unit with matching facts+externals+revision
  emits; `probe_grant_lexer_chunked.py` advances past the FIRST REFUSAL to the next
  refusing layer (assembly/compile), which is then named separately — NOT claimed here.

## 5. Open questions (not decisions)

Q1. Exact identity key for fact-external agreement (`calleeId`+revision sufficient, or
    also a content digest per N-T3-1 obligation?).
Q2. Where the revision-equality check lives (host driver vs Pep unit) — host-owned per
    grant-v1 precedent, but unstated here.
Q3. Whether route (b) needs a per-call-site opt-in flag while experimental.

NEXT: A2 — adopt/adapt/reject with one probe run; A3 — take F-* as gate rows if useful.
A4 takes no further build; this closes the LUCY-20261107-001 Pepin slice.
