# Native C23 lowering of `List`-valued record fields — 31 October 2026

Agent 2 (second current agent). Branch `codex/a2-list-record-fields`, based on
`codex/c23-chunked-parser@26be4be` ("Test short-circuit calls on both operands"), the tip of the
existing record/union C23 emitter line. No compiler redesign, no new language semantics.

Toolchain for every native result below: Clang 23.1.4 and MinGW GCC 16.2.0, both invoked as
`-std=c23 -Wall -Wextra -Wpedantic -Werror -O2`. Reference execution is Pep's own interpreter via
`pwsh pep.ps1 run`. Windows Defender settings and the excluded Clang empty-literal vector are
untouched.

## What was actually blocked

The earlier classification is confirmed and one detail is corrected.

| fact | status |
| --- | --- |
| checker accepts `List`-valued record fields | **confirmed** — `type Box { xs: List[Int] }`, `Outer { items: List[Inner] }` and all five real lexer declarations report `status: valid` |
| interpreter executes them | **confirmed** — `Box { xs: [1, 2] }` and `Outer { items: [...] }` both return `2` through `length` |
| emitter refuses them | **confirmed at 26be4be** — `Pep C23 record fields require Int, Bool, or a preceding record declaration` |
| the refusal is an *emitter* gap, not a language question | **confirmed** |
| `LexProgress` is "rejected at the checker" | **corrected** — it is *not* rejected; it is checker-valid. The earlier report's isolated probe simply omitted `LexToken`/`LexCursor`, so the checker correctly reported `PEP_UNKNOWN_TYPE`. Its real blocker is the checker's fixed 100k step budget on the complete closure (see below). |

So three of Lucy's real lexer record declarations — `LexToken` (`stringParts: List[Str]`),
`LexCursor` (`stringPartsReversed: List[Str]`) and `LexProgress` (`tokens: List[LexToken]`) — were
unrepresentable in the emitted language, while `SourcePosition` and `Utf8Check` were fine.

## What changed

All changes are in `tests/pep_c23_emitter.pep` (the Pep-written emitter), plus a new focused test
module. No host driver, checker, parser or runtime file changed.

1. `pep_c23_c_list_field_type_parts` classifies a `type_list` record field against its element type
   and returns the existing by-value C struct name:
   `List[Int]` → `pep_list_int`, `List[Bool]` → `pep_list_bool`,
   `List[Str]` → `pep_list_str` (new typedef — `List[Str]` had **no** C representation),
   `List[record]` → `pep_list_record_<id>`. The existing "preceding record declaration" ordering
   guard is preserved for record elements, so forward references still fail closed.
2. `pep_c23_c_record_field_type` recognises `type_list` and returns a `list` marker so the
   construction and parameter-shape checks treat list fields as supported rather than unknown.
3. `pep_c23_list_field_value` / `pep_c23_list_field_element` lower list-literal field values to
   `(pep_list_x){ .data = (const T[]){ ... }, .length = n }`, with `NULL`/`0` for `[]`. Element lowering is
   per element kind: `Str` reuses `pep_c23_string_literal`, `Int`/`Bool` require literal elements,
   records reuse `pep_c23_expression`. This deliberately reuses the emitter's established list
   convention rather than introducing an owned buffer.
4. Record declaration emission emits the list C type parts instead of refusing.
5. `length(x.field)` where the field is list-typed lowers to `pep_checked_length(<projection>.length)`.
6. `pep_c23_expression_may_fail` now classifies `string` as infallible and a `list` literal by its
   elements only. This is a correctness fix, not a relaxation: a string literal emits static bytes
   (`(pep_str){ .data = (const unsigned char[]){ 120, 121 }, .length = 2 }`) with no runtime failure
   path, and a list literal can only fail through its elements. Without it, a record mixing one
   `Str` field with one `List` field was rejected by the conservative C-evaluation-order guard.
   Two genuinely fallible fields (`calculate()`, `calculate()`) still fail closed.

### Representation and lifetime

Fields are by-value descriptors (`{ const T *data; size_t length; }`) pointing at compound literals
with **the enclosing block's lifetime** — exactly the convention the emitter already uses for list
*parameters*. A list field therefore must be consumed inside the block that constructs the record.
This is consistent with existing emitter behaviour, and it is safe by construction because
forwarding a projection into another list field is still refused (see the negative tests). An owned
or arena-backed representation is the natural follow-up if list fields must escape their block.

## Measured increase on Lucy's real lexer

Census over the five real record declarations in `examples/pep_lexer.pep`, each emitted with its
dependency closure (`LexProgress` needs `LexToken` + `LexCursor`):

| declaration | parent 26be4be | this branch |
| --- | --- | --- |
| `SourcePosition` | emitted | emitted |
| `Utf8Check` | emitted | emitted |
| `LexToken` (`stringParts: List[Str]`) | **emitter-refused** | **emitted** (4,734 B) |
| `LexCursor` (`stringPartsReversed: List[Str]`) | **emitter-refused** | **emitted** (4,904 B) |
| `LexProgress` (`tokens: List[LexToken]`) | checker step budget | checker step budget |
| **individually emittable** | **2 / 5** | **4 / 5** |
| **emitter-refused** | **2** | **0** |

This census is pinned as a test (`test_real_lexer_type_declaration_census`), so the number cannot
silently regress or inflate.

Beyond emitting, Lucy's real declarations now *execute*: `test_real_lexer_token_type_compiles_and_runs_natively`
extracts the `LexToken` declaration verbatim from `examples/pep_lexer.pep`, constructs a token whose
`stringParts` is a real `List[Str]`, projects it and returns `length(token.stringParts)` — compiled
by Clang and GCC and compared byte-for-byte with the interpreter's stdout.

## Native evidence (interpreter vs Clang vs GCC)

New module `tests/test_c23_list_record_fields.py`: **15 tests, 14 pass, 1 documented skip.**

| case | result |
| --- | --- |
| `Box { xs: List[Int] }` with `[1,2,3]`, `length` = 3 | clang ok, gcc ok, interpreter ok |
| `Box { xs: [] }`, `length` = 0 (`NULL`/`0`) | clang ok, gcc ok, interpreter ok |
| `Parts { parts: List[Str] }`, `length` = 2 | clang ok, gcc ok, interpreter ok |
| `Flags { bits: List[Bool] }`, `length` = 3 | clang ok, gcc ok, interpreter ok |
| `Outer { items: List[Inner] }`, `length` = 2 | clang ok, gcc ok, interpreter ok |
| mixed `Str` + `List[Str]` + `Int` record, `count + length` = 8 | clang ok, gcc ok, interpreter ok |
| real `LexToken` with `stringParts: ["ab","cd"]` | clang ok, gcc ok, interpreter ok |

Boundary and negative cases that must keep failing closed, and do:

- `Box { xs: [1 + 2] }` → `List[Int] record field values currently require integer literal elements`.
- `type Outer { items: List[Inner] }` before `Inner` → `record fields require ... a preceding record declaration`.
- Forward scalar record field (`Box { point: Point }` before `Point`) → same message (guard preserved).
- Two genuinely fallible fields → `record construction rejects multiple fallible field expressions`.
- Forwarding one field's list projection into another list field (`Pair { left: box.xs, ... }`) →
  `list record field values currently require a list literal`.
- Complete real type closure → either emits or stops with `PEP_RUNTIME_STEP_LIMIT`; never invalid C.

## Regression evidence, with pre-existing failures distinguished

| suite | this branch | parent 26be4be |
| --- | --- | --- |
| `tests.test_c23_list_record_fields` (new) | 15 tests, 14 pass, 1 skip | n/a |
| `tests.test_c23_nested_record_emission` + `tests.test_c23_str_contains` | **65 tests OK, 8 skipped** | 47 tests OK, 5 skipped (nested-record only) |
| `tests.test_c23_cli` | **15 / 15 OK** | — |
| `tests.test_a14_c23` | **4 failures** | **4 failures, identical test set and identical failure reasons** |
| `tests.test_c23_collections` | not green | not green — see below |

`tests.test_a14_c23` fails at both revisions on the same four tests
(`test_generated_c23_executes_source_backed_programs_under_clang_and_gcc`,
`test_recursive_call_is_rejected_before_native_lowering`,
`test_recursive_native_calls_enforce_pep_depth`,
`test_unsupported_valid_program_is_reported_without_c_output`), with the same assertions and the
same observed values — including `'emitted' != 'unsupported'`, which is a stale expectation, not a
regression. These are inherited from the parent commit and are **not** caused by this change.

`tests.test_c23_collections` is a pre-existing budget problem, measured rather than assumed. A
representative method (`test_pep_written_int_min_between_matches_interpreter_on_clang_and_gcc`) was
run on both trees and fails identically: **14/14 subtests, all at the `check parsed source` stage,
at the same step offsets** (3975/3981/2605/2441/3610). The emitter is never reached, so my change
cannot be the cause. The same class of failure is what the earlier handoff recorded as "its emitter
cannot emit the accepted slice for budget reasons".

## What remains blocked, and the next dependency

Ranked by what the evidence actually says, not by message text:

1. **Pep-written checker step budget (now the first-order blocker).** The complete real lexer type
   closure `{LexToken, LexCursor, LexProgress}` fails `check` with
   `PEP_RUNTIME_STEP_LIMIT: Execution step budget exceeded at 3413:8` at the unchanged 100,000
   step per-invocation limit. `{LexToken, LexCursor}` alone emits; adding `LexProgress` (11 fields,
   one `List[LexToken]`, one `LexCursor`) trips it. Most of `tests.test_c23_collections` fails here
   too, upstream of the emitter. This is a checker-cost dependency; no emitter change can move it
   and no budget was raised.
2. **Function parameter/argument arity (unchanged).** `make_token` takes 8 parameters,
   `make_cursor` 16, `make_progress` 11; the emitter supports at most three. So the three lexer
   constructors remain unemittable even though their record *types* now emit. Reproducer:
   `fn f(a: Int, b: Int, c: Int, d: Int) -> Int { return 0 }`.
3. **`lexer_step` checker envelope (unchanged).** Still outside the checker's reachable envelope.
4. **List field values must be list literals.** Forwarding a list parameter or a projection into a
   list field still fails closed. Natural next slice once (1) permits the source sizes involved.
5. **List fields are block-lifetime views.** Escaping a list field beyond its block would dangle, so
   the supported shapes are deliberately restricted; an owned/arena representation is the follow-up.

The single next dependency to unblock broader native lexer progress is **(1)**: the checker's
per-invocation cost on the complete lexer type closure. (2) is the immediate follow-up for the
constructors and is independent of it.

## Reproducing

```
python -m unittest tests.test_c23_list_record_fields -v
python -m unittest tests.test_c23_nested_record_emission tests.test_c23_str_contains tests.test_c23_cli
```

No `master`, `CURRENT.md`, manifest, milestone or release state was changed. The first current
agent's uncommitted `tests/test_a14_c23.py` edit in the campaign checkout was never touched: all
work happened in a separate worktree on `codex/a2-list-record-fields`.
