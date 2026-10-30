# C23 real-lexer native slice — first execution report

Test under review: `tests/test_c23_real_lexer_classifiers.py` at commit `c1a9f8a`
(branch `codex/real-lexer-native-first-slice-20261030`).
Executed 2026-10-30T01:44Z on the Windows host, no Defender exclusion in force,
RTP and tamper protection enabled, signatures 1.463.30.0, clang 23.1.4
(MSVC target) and MinGW GCC 16.2.0.

## Result: the test fails, and it is a real compiler limitation — not a test defect

```
python -m unittest tests.test_c23_real_lexer_classifiers -v
Ran 1 test in 12.654s
FAILED (errors=5)
```

All five byte cases error identically inside `pep_c23.emit()`, at the checker
stage:

```
check parsed source: expected outcome='ok', received
{'outcome': 'error', 'operation': 'tool_invoke',
 'error': {'code': 'PEP_RUNTIME_STEP_LIMIT',
           'message': 'Execution step budget exceeded at 2441:26'},
 'metrics': {'parse_count': 3, 'typecheck_count': 3, 'cache_hits': 0}}
```

What did pass before the failure is worth stating: the lexer source blob pin
(`12bd93a1dfc5dba3b1cab49abefffed5e406b17d`, CRLF-normalised) is **correct**, and
the **reference interpreter executed the real three-function closure correctly**
for all five cases (`ascii_continue(65)`, `57`, `95` → `42`; `64`, `128` → `0`).
So Lucy's classifiers behave as intended under the interpreted path today.

## Two layered limitations

### 1. Shipped behaviour: an opaque step-budget wall

The Pep-written A13 checker runs as an interpreter tool with
`tool_step_budget = 100_000` (`pep_ocaml.ml:1288`) and, where the default applies,
`step_limit = 1_000_000` (`pep_ocaml.ml:771`). It exhausts that budget while
executing its own code — the reported position `2441:26` is inside the
concatenated tool document (lexer + parser + checker + emitter), not inside the
program being checked.

Measured ceiling, bisected with synthetic sources built from trivial
`fn fN() -> Int { return N }` functions plus `main`:

| top-level functions | source bytes | result |
| --- | --- | --- |
| 3 | 87 | OK |
| 5 | 143 | OK |
| 7 | 199 | OK |
| 9 | 255 | OK |
| 13 | 371 | `PEP_RUNTIME_STEP_LIMIT` |

So the checkable source ceiling is roughly **300–400 bytes**. The real classifier
closure plus harness is ~470 bytes. Lucy's `examples/pep_lexer.pep` is 19,425
bytes.

Raising either budget alone changes nothing (tool budget to 8 M, default to 10 M
— no effect, same error, same position). Raising **both** to 20 M does not make
the test pass either; it unmasks the second limitation.

### 2. The limitation the budget was hiding

With both budgets at 20 M, the emitter returns a substantive diagnostic instead:

```
Pep C23 functions require local bindings and supported loops followed by one return
Pep C23 one-parameter calls require one argument and a call-free target expression
```

Bisect of constructs (identical budgets, same host):

| variant | program shape | result |
| --- | --- | --- |
| V4 | `fn c(b) -> Bool { return a(b) }`, main calls `c` | **OK** — one call in a return is supported |
| V5 | `ascii_letter` + `main` with `if/else` returns | **OK** |
| V3 | `fn c(b) -> Bool { return a(b) || a(b) }` | **FAIL** "one-parameter calls require one argument and a call-free target expression" |
| V6 | real `ascii_letter` + `ascii_digit` + `ascii_continue` | **FAIL** "functions require local bindings and supported loops followed by one return" |
| V1 | full real closure + `if/else` main | **FAIL** (same as V6) |

The blocking construct is one line of Lucy's actual lexer:

```
fn ascii_continue(byte: Int) -> Bool {
  return ascii_letter(byte) || ascii_digit(byte)
}
```

The C23 emitter supports a **single** function call in a return expression, but
not calls used as operands of `||` (or `&&`). `ascii_letter` and `ascii_digit`
are individually emittable; `ascii_continue`, which composes them, is not.

## What this means

- The slice is doing its job: a 12-line extraction of real compiler source
  exposed a limitation that no synthetic demonstration program would have found.
- The limitation is in **C23 emission of short-circuit expressions containing
  calls**, not in the lexer logic (interpreter agrees with expectation) and not
  in character classification arithmetic (`ascii_letter` alone emits fine).
- The budget failure is a **diagnostic quality problem in its own right**: real
  compiler source produces `PEP_RUNTIME_STEP_LIMIT at 2441:26`, which points at
  the checker's own document and tells a compiler author nothing about the
  actual `||`-of-calls limitation.

## Recommended next actions, in order

1. **Extend the emitter to support calls as `&&`/`||` operands** rather than
   restructuring the test. Rewriting Lucy's lexer to avoid `a(x) || b(x)` would be
   fitting the compiler to the test, which is backwards for a self-hosting goal.
2. **Make the ceiling honest.** Either raise the checker's tool budgets enough to
   reach real diagnostics, or report the exhausted-budget case with the *source*
   position and a "checker budget" code rather than a bare step error. Current
   behaviour reports a limit inside the checker as if it were a property of the
   program under check.
3. Re-run this test unchanged after (1). The blob pin means it will still be
   evidence for exactly the same lexer source.
4. Then move to `utf8_check`, as planned — but expect the same `||`-of-calls
   shape, since the lexer uses it throughout.

No changes were made to the accepted release.

## Follow-up — verified against both builder heads (Agent 3)

After this report was pushed, the same test was carried unchanged into each
builder head. The slice **passes only where two branches are combined**:

| head | checker | emitter | slice |
| --- | --- | --- | --- |
| `c1a9f8a` (test only) | `PEP_RUNTIME_STEP_LIMIT` | not reached | FAIL x5 |
| `codex/c23-chunked-parser@cb6a710` | `PEP_RUNTIME_STEP_LIMIT` | would pass | FAIL x5 |
| `codex/agent1-compiler-integration@3ec4679` | passes | rejects | FAIL x5 |
| `3ec4679` + `cb6a710` emitter file | passes | passes | **PASS** |

Both halves of the diagnosis above are now independently confirmed:

- **The `||`-of-calls limiter is fixed** by `cb6a710` on an unchanged budget.
  My own isolated probes (`a(b) || a(b)`, `a(b) && a(b)`, `a(b) || d(b)`) emit
  successfully there.
- **The step-budget wall is cleared for this slice** by Agent 1 bounded checker
  staging at `3ec4679`; the failure moves on to the emitter instead.

So "native-verified" is legitimate only for the combination. Evidence pins and
the exact integration instruction are recorded on issue #20.

## Next-component probe — `utf8_check` under the combined state (Agent 3)

Extracted `type Utf8Check` plus `fn utf8_check` verbatim from
`examples/pep_lexer.pep` (87 lines, 2,825 bytes) and drove it from a harness
calling `utf8_check(source_bytes(), 0, byte_length(source_bytes()))` — exactly
how the lexer consumes its own input. Run against `3ec4679` + the `cb6a710`
emitter (the combination that passes the classifier slice). Two blockers, both
concrete:

1. **`source_bytes()` is gated to a v2 semanticTarget.** The reference path
   `pep.ps1 run` refuses with `PEP_RUNTIME_SOURCE_CONTEXT: source_bytes is
   available only for a host-authorised v2 semanticTarget`. So the reference
   oracle used by the classifier slice (run in the interpreter, compare stdout)
   **cannot** be used for `utf8_check`; its reference must come from the
   semantic-target machinery.
2. **The staged checker still exhausts its budget at this size.** `emit` fails
   with `PEP_RUNTIME_STEP_LIMIT` on the 2.8 KB block in the combined state, with
   the 100,000-step budget unchanged.

### Correction to the ceiling characterisation above

The earlier section described the wall as "roughly 300-400 bytes of source".
That was a byte-based extrapolation from a ladder of uniformly shaped trivial
functions, where bytes and node count were confounded. Measured more carefully,
byte size is a **poor** proxy:

| sample | shape | bytes | combined state |
| --- | --- | --- | --- |
| real classifier slice | 4 functions | 470 | **passes** |
| trivial ladder | 9 functions | 255 | passes |
| trivial ladder | 17 functions | 491 | fails `PEP_RUNTIME_STEP_LIMIT` |
| `utf8_check` block | 1 dense function | 2,825 | fails `PEP_RUNTIME_STEP_LIMIT` |

The binding quantity is AST/expression complexity rather than source bytes, and
the true ceiling sits between these samples. It should be measured in nodes per
phase rather than inferred from bytes — which is Agent 1 territory, and is what
`checker_start/step` continuation billing exists to make possible.

## Agent 1 `e9abcd7` — diagnostic labelling verified, and a merge-breaker found (Agent 3)

Agent 1 head moved to `e9abcd7` ("Label compiler checker budget failures
accurately"). Verified against it:

- **The real-lexer slice still passes** in combination with the `cb6a710` emitter.
- **The budget diagnostic is now honest.** The `utf8_check` block no longer
  produces a bare step error; it raises `PepCompilerToolBudgetError` with
  `stage=checker`, `compiler_tool=pep-c23-checker-start`,
  `compiler_bundle_revision=sha256:8fb1d285…`,
  `compiler_bundle_location=compiler-bundle:2709:40`, and an explicit
  `target_source_span=unavailable`. That is the labelling this report asked for,
  and it correctly declines to pretend the budget was exhausted in the target.
- **`tests/test_c23_cli` passes 6/6 on clean `e9abcd7`** and fails **5/6** with
  the Agent 2 emitter applied — an integration interaction, not a defect in
  either branch on its own.

### The merge-breaker, and its one-line fix

`tests/test_c23_cli.py:106-110` asserts that `fn main() -> Int { return
length([1, 2]) }` is **unsupported** (expects exit 2 and "Pep C23 unsupported:").
With the `cb6a710` emitter that program is now **supported and correct**:
`run-c23` compiles, runs and prints `2`, matching the interpreter. So the test
fails with `0 != 2` after a merge purely because the exemplar is stale.

Verified in the same combined tree, these are still unsupported, with their exact
messages:

| program | combined state |
| --- | --- |
| `return length(append([1], 2))` | unsupported — "length lowering requires a direct integer list literal or immediate…" |
| `return byte_length(source_bytes())` | unsupported — "calls require a known target and at most three arguments" |
| `type Box { xs: List[Int] }` | unsupported — "record fields require Int, Bool, or a preceding record declaration" |

**Recommendation:** when merging Agent 2 onto Agent 1, change the exemplar at
line 106 to `length(append([1], 2))`. Same feature area, same test intent,
minimal churn, and it stays unsupported for a documented reason.

The last two rows are not test trivia — they are the two constructs that block
the next Lucy components. `byte_length(source_bytes())` blocks a natural
`utf8_check` harness, and `List`-typed record fields block Lucy AST shapes such
as token lists.

### A false alarm I raised and then disproved

I initially probed `contains("abc", "b")` and saw the emitter fail with "requires
a valid Pep checker report", which looked like an emitter defect. It is not:
`contains` is the **List** builtin, and the checker correctly rejects the Str
argument with `PEP_LIST_EXPECTED: Builtin 'contains' expects a List, found Str`.
The emitter message was accurate. The Str builtin is `str_contains`. My probe was
wrong, not the compiler.

No changes were made to the accepted release. No compiler source was modified
for the delivered result: the budget and construct experiments were run on
temporary local edits and reverted (`git status` clean, patched `pep.exe`
deleted) before this report.
