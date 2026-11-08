# H2 — Next Native Compiler Vertical: `known_builtin` (+2 negatives)

**Campaign H, H2 (SECOND).** Builds on H1 blockers; avoids `ascii_digit`,
`make_token`, grade bands (adopted). One choice + two negatives with
falsifiers. No implementation; the vertical is specified to run, not run
here (seed-driver native path is tool-blocked on this host — H1-P7; A2's
harness is the execution lane). Labels: ESTABLISHED / INFERRED.

## Candidate A — CHOSEN: `known_builtin` native recognizer

**Routine (real, verbatim @ 2ad750b:148):**
`known_builtin(name: Str) -> Bool` — a 13-way `||` chain over Str equality.
P1-class simplicity with a REAL checker dependency (gates every builtin
call site: 387 E8-counted uses).

**Vertical program** (fits A2-58fc9bf named capabilities — INFERRED from fn
names, to be falsified by the run):
```pep
fn known_builtin(name: Str) -> Bool {
  return name == "say" || name == "int_text" || name == "length" || name == "append" || name == "prepend" || name == "reverse" || name == "source_bytes" || name == "byte_length" || name == "byte_at" || name == "byte_slice" || name == "utf8_slice" || name == "contains" || name == "str_concat"
}
fn main() -> Int {
  let a = if known_builtin("length") { 1 } else { 0 }
  let b = if known_builtin("nope") { 1 } else { 0 }
  return a + b
}
```
Expected: seed `run` prints nothing (no top-level say — add one for the
oracle if desired: `say(int_text(...))` ×2 → `1/0`); native `main` returns 1
(`a=1, b=0`); Clang == GCC == seed.

**Dependency graph (complete, tiny):** Str literal (`pep_c23_string_literal`)
→ Str param (`pep_c23_str_parameter`) → `==` on Str → call (≤1 arg, known
target) → if-expression → Int arith → main. Zero records, zero lists, zero
loops, zero recursion, zero SourceBytes. Transitive closure: 1 fn + 1 main.

**OUTCOME 2026-11-04 — prediction FALSIFIED by A3 H-V5c (ACCEPT-H-V5C-KNOWN-BUILTIN @ `08e1e8b`, TESTED):** the full vertical does NOT reach
lowering — the checker tool invocation REFUSES first (`PEP_RUNTIME_STEP_LIMIT`
at seed-`run` scale; budget precedes lowering). The predicted "Str `==`"
first blocker is WRONG. And the isolated form PASSES: A3's reduced
`is_named` probe (`name == "say"`) goes 4/4 across seed/Clang/GCC, with C
emitting a correct length-then-byte comparison (`pep_str_equal`). So:
(1) Str equality needs NO A2 fix — recorded as a positive result, and the
falsifier worked exactly as designed (it named the true next block, just not
the predicted one); (2) the gate that matters is the CHECKER BUDGET on the
full 13-way function, not the emitter. H2's experiment is therefore CONSUMED:
do not re-run the full vertical as specified — the reduced isolated form is
already green, and the remaining question (why the 13-way chain trips the
budget) belongs to G-A4-2/A1-per-phase-accounting, not to lowering.

## Candidate B — NEGATIVE: `insert_sorted`/`quick_sort_nodes` native

Too dependent TODAY: needs native `List[FlatAstNode]` (13-field records with
Str fields), list construction (`prepend`/`reverse` at runtime), and
RECURSION (quick_sort calls itself — emitter refuses recursion, status at
58fc9bf UNKNOWN but seed-B3 refused). Three independent missing capabilities;
bundling them into one vertical proves nothing per-failure.
REVISIT when: native record-lists mature (R3-adjacent) AND a
recursion-or-iteration decision exists. Not now.

## Candidate C — NEGATIVE: `lexer_step` native

Blocked on TWO H1 roots: SourceBytes ingress (no grant model — H5 decision
pending) AND loop-state lowering (`while` + mutable cursor; A2's
`pep_c23_loop_statement` is unprobed). A vertical that needs a normative
decision first is a bad vertical. REVISIT after H5.

## Handoff (5–10 lines for A2/A3)

1. A2: run Candidate-A program through your bounded-emission harness
   (verbatim `known_builtin` @ 2ad750b:148 + `main` above); report
   emitted/refused + code, Clang+GCC outputs vs seed `1/0`-equivalent.
2. If refused: the refusing gate (Str-`==`? Str-param? literal?) IS the
   finding — file the code, no fix demanded.
3. A3: seed oracle `run` gives the expected values; adopt as native anchor
   iff green on both toolchains (your call).
4. Do NOT bundle B or C into this probe; they are documented negatives.
5. A4 needs nothing back except the refusal code (feeds H3 totals).

## Status labels

DECISION SUPERSEDED 2026-11-04 by A3 H-V5c: the vertical ran, the predicted
blocker was falsified (budget precedes lowering), the reduced form is green
4/4. No builder rewrite, no new framework. H3's "cheapest experiment" line
is rewritten accordingly (see H3 addendum) — the next measurement is budget
attribution, not gate location. Candidates B/C negatives STAND (unaffected
by H-V5c). Correction pass applied; falsifier credit to the design: the
probe found the TRUE first blocker (budget), which is what falsifiers are for.
