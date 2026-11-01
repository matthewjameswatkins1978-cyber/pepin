# Native C23 closure for compiler A — N0 baseline (1 November 2026)

Mission `LUCY-20261101-004`, Agent 2 (A2-NATIVE). This is the N0 deliverable: pinned
heads, the real compile path by stage, and the exact backend-only blockers ranked by
their use in the canonical sources.

## Pinned heads

| ref | SHA | note |
| --- | --- | --- |
| A2 working branch `codex/a2-list-record-fields` | `2aa298bdebf07536ed7633bb4300e7c00db65b39` | this report |
| A1 integration `codex/checker-emitter-integration` | `845d5936fa1c0d86309da3889a2f90385b1b8578` | contains A2 `b9e26df`; **not** `37e8c1a` or later |
| A1 checker lane `codex/checker-step-budget` | `2e6800e2d98b94b3dc70ea9ca970760d6aba22c1` | not merged into integration at time of writing |

**Integration dependency:** A1 should pin A2 `2aa298b` (which contains `37e8c1a`,
`d986773` and the prepend/reverse slice) before treating native recursion or list
updates as integrated. `845d593` predates all three.

## The real compile path, by stage

Nothing here is inferred; each row is where the current code actually executes.

| stage | implementation | invoked by | state |
| --- | --- | --- | --- |
| seed front end | `pep_ocaml.ml` (OCaml 5.5.2) | `pep.ps1 session --jsonl`, a JSONL request/response loop | working; owns parsing and the semantic oracle |
| Pep-written parser | `examples/pep_parser.pep` | staged as `pep-c23-parser-start` / `-parser-step` tool invocations | working; produces `FlatAstNode` chunks |
| Pep-written checker | `tests/pep_checker_a13.pep` | staged as the `pep-c23-checker` tool invocation | working but step-budget bound on compiler-sized sources |
| Pep-written emitter | `tests/pep_c23_emitter.pep` | one-shot `pep-c23-emitter` invocation returning C23 source parts | working; this lane |
| host orchestration | `pep_c23.py` (Python) | CLI and tests | orchestrates stages and the 1 MiB / 100k guards; contains no semantic compiler |
| native compiler | Clang 23.1.4, MinGW GCC 16.2.0 | `-std=c23 -Wall -Wextra -Wpedantic -Werror -O2` | working for the subset the emitter covers |
| native runtime | `runtime/pep_arena/{pep_arena.h,pep_arena.c}` plus helpers inlined into the generated C | linked by the build recipe | working; explicit lifetime, sticky failure codes |

So the honest stage description today is: **Pep compiler source is executed by the
OCaml seed, checked by a Pep-written checker, and emitted to C23 by a Pep-written
emitter**; a standalone native compiler A (no OCaml/Python semantic stage during its
normal operation) does not exist yet.

## The dominant measured blocker: emitter cost per function-body statement

Chasing why six arena-backed list updates tripped the emitter budget produced the
answer, and it is not about list updates at all. A function that assigns a plain
`Int` six times inside a `while` body emits; seven assignments exceed the emitter's
fixed 100k-step per-invocation budget:

```
fn main() -> Int {
  var acc = 0
  var guard = 0
  while guard <= 0 {
    acc = acc + 1        // 1..6 of these emit
    ...                  // 7 of them: PEP_RUNTIME_STEP_LIMIT
    guard = guard + 1
  }
  return acc
}
```

List updates hit the same wall at five instead of six, which is the same boundary
seen from a slightly more expensive statement. **So the limiting factor for real
compiler bodies is the emitter's per-statement cost, not any missing feature.**
Lucy's `lexer_step` contains dozens of statements; no amount of feature work makes
it compile while roughly six statements exhaust the budget.

This is pinned by a test in `tests/test_c23_list_updates.py` so the boundary is
recorded, not hidden, and so that whoever reduces the cost is told to re-measure and
re-pin deliberately. No cap was raised.

Likely cause to investigate next, not yet proven: each statement's lowering performs
several full traversals of the node list (`pep_c23_child`, `pep_c23_mutable_list_binding`,
`pep_c23_count_children`, ...), so cost grows with statements times nodes with a
large constant. That is the first thing a dedicated emitter-cost slice should measure
before changing anything.

## Backend-only blockers, ranked by use in the canonical sources

Counted in `examples/pep_lexer.pep` and `examples/pep_parser.pep`. "Measured" means I
ran the emitter on the construct and recorded the outcome.

| # | blocker | uses (lexer / parser) | state |
| --- | --- | --- | --- |
| 1 | `prepend` / `reverse` | 16+2 / 24+19 | **partial**: `List[Int]`, `List[Bool]` now lower natively via arena-backed helpers; `List[Str]` and `List[record]` refused |
| 2 | mutable `List[Str]` and `List[record]` bindings | lexer state (`stringPartsReversed`, `tokens`) | measured: refused (`prepend/reverse currently require an Int or Bool list binding`). This is the gate on blocker 1's remaining half |
| 3 | `utf8_slice` | 6 / 0 | measured: `calls require a known target` — no C23 representation |
| 4 | calls with 1-3 arguments and a parameter-referencing result | pervasive | measured: fixed-slot path requires a call-free or conditional result; pinned by test. 4-8 arguments use the general ordered path |
| 5 | list fields are block-lifetime views | lexer records | by design; an owned/arena list-field representation is the follow-up |

Not yet measured (do not treat as facts): `at(...)` indexing, `match` over record
payloads in parser bodies, and anything that requires the checker to reach it first.

## Measured checker divergence: `List[record]` mutable bindings

Attempting blocker 1's record half produced a finding that belongs to the checker
lane, not the backend. This program is **valid** to the OCaml oracle and is
**rejected by the Pep-written checker**, so the emitter never runs:

```
type P { x: Int }
fn main() -> Int {
  var points: List[P] = []
  return length(points)
}
```

- `pep.ps1 check` (OCaml): `status: valid`.
- the staged Pep-written checker used by `pep_c23.emit` returns non-valid, so
  emission stops with `Pep C23 emission requires a valid Pep checker report`.

The same happens with `points = reverse(points)` and with
`points = prepend(points, P { x: 1 })`, and it happens for the length-only program,
so it is the *binding* that diverges, not the update.

Consequence for this lane: `List[record]` mutable bindings — the lexer's `tokens`
accumulator — cannot be reached natively until that divergence is fixed. I built and
then **reverted** the matching emitter support rather than ship unreachable,
unexercised lowering code; it goes back in when the checker reaches such a program.

This is worth fixing early: `tokens: List[LexToken]` is the lexer's main output
accumulator, and the divergence is visible on an eleven-line program with no
templates, no loops and no emitter involvement.

## First native unit

The smallest real unit that could run natively once blockers 1 and 2 are closed is
`make_token` with its `stringParts` parameter forwarded into a `List[Str]` field —
the emitter side of that shape already exists; only `List[Str]` list *updates* are
missing. `make_cursor` and `make_progress` additionally need `List[record]` updates.

Immediate evidence-backed order of work:
1. mutable `List[Str]` bindings plus `prepend`/`reverse` (unblocks `make_token`'s body);
2. mutable `List[record]` bindings (unblocks `tokens` in `lexer_step`);
3. `utf8_slice` (6 uses, needed for token text);
4. the bounded checked-AST handoff with A1 (N4), since checker scale is the other half.

## Ownership

A2 owns: `tests/pep_c23_emitter.pep`, `tests/test_c23_*.py` for the C23 emitter,
and generated-C runtime helpers inlined by the emitter. A2 does not touch
`tests/pep_checker_a13.pep`, `pep_c23.py`, the host adapter, the integration branch
or the campaign checkout's uncommitted `tests/test_a14_c23.py`.

## Method discipline carried forward

Every slice diffs failing **subtest lines** against the pinned parent, isolated and
sequential. Whole-suite totals taken while other suites run concurrently have
already disagreed with isolated measurement in both directions and are not used as
evidence.
