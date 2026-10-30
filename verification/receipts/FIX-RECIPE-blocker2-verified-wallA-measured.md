# VERIFIED FIX RECIPE for blocker 2 — and Wall A measured through it (2026-10-30)

All experiments ran in scratch (patch → measure → `git checkout --`),
nothing committed to any builder branch; final state reverts verified
clean. Detached worktree: A1 `7628d6d` + A2 `26be4be` files.

## Root cause — corrected for BOTH lanes (including my own earlier statement)

The `PEP_TOOL_ARGUMENT_COUNT` diagnosis was right (stale one-arg
vector), but **the follow-on `PEP_TOOL_ARGUMENT_TYPE` is NOT in arg1**
— as the report lane's withdrawn "one-line fix" section suspected a
type defect, but located it in the wrong place. The defect is in the
**expect constructions and the step list argument**:

| # | stale piece (pep_c23.py) | evidence |
|---|---|---|
| 1 | L604 checker-start vector missing 2nd arg | `[empty_parsed]` → `ARGUMENT_COUNT`; `[empty_parsed, typed("Int","0")]` passes count |
| 2 | L605/L608 **expects** built by `checker_cursor_value` carry FlatAstNode-era nested types (declared `CheckerCursor.nodes : List[CheckerNode]`) | **V1/V2 decisive probe: identical args, identical 15 top-level field names — pep_c23 expect → Rejected `ARGUMENT_TYPE`; a13's `checker_cursor` expect → `Validated`** |
| 3 | L607 checker-step second arg `typed_list("FlatAstNode")` | `List[FlatAstNode]` → `ARGUMENT_TYPE`; `List[CheckerNode]` → **`Validated`** |
| 4 | L608 step expect — same stale cursor construction as (2) | fixed with a13-style cursor; E2E then passes step |

**Proof arg1 was never the problem:** `analyze_parsed([empty_parsed])`
validates in the *same loop* with the *same value* (raw probe:
parser-start/step/checker all `Validated`, checker-start rejected) —
and the report's three candidates all varied arg1 while keeping the
stale expect, so all three predictably failed.

## The recipe (tested end-to-end)

1. L604: `[empty_parsed]` → `[empty_parsed, typed("Int", "0")]`
2. checker-start expect: `checker_cursor_value(sample…)` → a13-style
   `checker_cursor(sample["document"], "", empty_parsed, "validation")`
   (mirror of `tests/test_a13.py:84-97,100+` — updated with the
   CheckerNode refactor)
3. L607: `typed_list("FlatAstNode")` → `typed_list("CheckerNode", [])`
4. step expect: same a13-style cursor (`"functions"` phase)
5. construct both cursors once after `empty_checked` (helper import or
   mirrored builder)

**Result: `pep_c23.emit(b"fn main() -> Int { return 42 }")` → `emit OK,
4379 bytes`** — the first end-to-end staged emit on this state since
`d64ea2a`.

## Wall A — MEASURED for the first time through a working validate path

Suites under the scratch fix (27 tests, one run, then reverted):

| suite | result |
|---|---|
| `test_c23_str_contains` (18) | **ALL PASS** — SourceBytes/records/strings native included |
| `test_c23_cli` (8) | **ALL PASS** — incl. `run-c23` compile+exec both compilers |
| `test_c23_real_lexer_classifiers` | **5 errors — `PEP_RUNTIME_STEP_LIMIT`** (staged path, emit stage) |

**Verdict:** with validate repaired, the ONLY remaining emit blocker is
**Wall A — the classifier closure's staged emit cost** — exactly the
original `7bfb819..8e076e2` regression, now isolated behind a green
harness with no masking layers left. str/cli passing proves the cost
problem is specific to the classifier-shaped closure, not general.

## Corrections recorded

- **Mine (round 13):** "fix is precisely scoped: supply the Int chunk
  argument" — incomplete; count fix alone lands on the type wall.
- **Report lane (6425bd4):** "the vector needs a properly formed
  ParserProgress first argument" — **wrong locus**: arg1 was always
  valid; the type defect lives in the *expect* (and step list type).
  Their honest self-withdrawal made this checkable; the V1/V2 probe
  settles it.
- **Both lanes' gate suggestion stands and is now complete:** bundle
  validity smoke + `pep_c23.emit` smoke together cover all three layers
  (bundle / validate / emit cost).

Replay: corpus/`replay.py`/base untouched — **161/161** current.
