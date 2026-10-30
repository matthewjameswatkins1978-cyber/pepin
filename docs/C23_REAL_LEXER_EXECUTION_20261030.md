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

No changes were made to the accepted release. No compiler source was modified
for the delivered result: the budget and construct experiments were run on
temporary local edits and reverted (`git status` clean, patched `pep.exe`
deleted) before this report.
