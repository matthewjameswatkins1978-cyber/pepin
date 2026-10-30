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

### Regression sweep at `e9abcd7`, and the size of the two remaining gaps

Full sweep on the newest Agent 1 head, clean tree, no builder files touched:

| suite | result | time |
| --- | --- | --- |
| `tests.test_a13` (pinned differential) | **76/76 OK** | 257.8s |
| `tests.test_a12` | 23/23 OK | 26.7s |
| `tests.test_a13_nested_records` | 13/13 OK | 36.2s |
| `tests.test_a14_c23` (native, clang + gcc) | 11/11 OK | 56.4s |
| `tests.test_c23_cli` | 6/6 OK | 15.6s |

129 tests, all green. No regression from `e9abcd7`.

**Gap 1 — `SourceBytes` lowering does not exist for target programs.** The
emitter contains `source_bytes()` and `byte_length(source)` at lines 808-809,
but those are the *emitter's own* Pep source running inside the tool, not
lowering support for a target program. Anyone grepping the emitter for these
names will find hits and conclude support exists; it does not. A
`byte_length(source_bytes())` target therefore falls into the generic gate at
line 2016 (`if !target.found || extraArgument.found`) and reports "calls require
a known target and at most three arguments". Adding support means wiring
`source_bytes`/`byte_length`/`byte_at` into the call-lowering path plus a
`SourceBytes` runtime representation.

**Gap 2 — `List` record fields are one mapper away.**
`pep_c23_c_record_field_type` (line 501) maps scalar Int/Bool, `Str` →
`pep_str`, and named records → "record"; anything else returns `""`, which the
construction path turns into "record fields require Int, Bool, or a preceding
record declaration". A `List[Int]` field is a list-kind type, so it falls
through. Extending that mapper plus the record struct emission is a bounded
change, but it is the gate standing between Lucy AST records and native
emission.

### Reference oracle for `utf8_check` — found, and verified on multi-byte input

The blocker reported earlier ("`source_bytes()` is gated to a v2 semanticTarget,
so `pep.ps1 run` cannot serve as the oracle") is real but **not** the end of the
matter. `describe` lists the session operations and there is no `run` among them
(`open`, `open_bytes`, `query`, `inspect`, `apply_edit`, `fill_hole`,
`tool_register`, `tool_validate`, `tool_activate`, `tool_list`, `tool_invoke`,
`metrics`). `source_bytes()` is supplied only inside a **tool invocation**
(`pep_ocaml.ml:901-903`, `1725`, `1804`). So the reference path is to call
Lucy's own function *as a tool* against a semanticTarget.

Verified recipe, all four steps observed working:

1. `open_bytes` the tool document: `type Utf8Check` + `fn utf8_check` verbatim,
   plus an entry function taking the offset as an argument, e.g.
   `fn width_at(offset: Int) -> Utf8Check { return utf8_check(source_bytes(),
   offset, byte_length(source_bytes())) }`.
2. `open_bytes` the target document — the revision whose bytes `source_bytes()`
   will see.
3. `tool_validate` with `testVectors[{arguments, expect, semanticTarget}]`,
   where `expect` is a typed record and `semanticTarget` is
   `{document, revision, entryFunctions: []}` for the target. Validation compares
   real execution against `expect`, so it is itself a revision-pinned oracle.
4. `tool_register` → `tool_activate` → `tool_invoke` with the same arguments and
   semanticTarget, returning a typed `Utf8Check`.

Results observed:

| case | result |
| --- | --- |
| target beginning `f`, offset 0 | `{"type":"Int","value":"1"}`, `Validated` |
| target `fn main() -> Int { say("café") }`, offset 28 (lead byte 0xC3) | `Utf8Check { width: 2, invalidOffset: -1 }`, `Validated` |

So Lucy's real `utf8_check` can be reference-executed deterministically against
a pinned revision, including multi-byte sequences, without `pep.ps1 run` and
without any compiler change. That is the testing route for Agent 2 — and it also
shows Lucy's own functions are already callable as tools over host-authorised
source bytes, which is a step toward the self-hosting loop rather than merely a
test convenience.

## Post-merge verification at `fd5c5d5` — milestone reached, two regressions found

Agent 1 landed `fd5c5d5` "Integrate verified lexer classifier C23 slice": it took
Agent 2's emitter byte-identically (blob `9573c227…`), added the slice test, and
updated the `test_c23_cli` exemplar. Post-merge sweep, clean worktree:

| suite | result |
| --- | --- |
| `tests.test_c23_real_lexer_classifiers` | **OK — 1 test, 15.8s** |
| `tests.test_c23_cli` | 6/6 OK |
| `tests.test_a13` (pinned differential) | 76/76 OK (260.7s) |
| `tests.test_a12` / `test_a13_nested_records` | 23/23, 13/13 OK |
| `tests.test_a14_c23` | **11 tests, 2 FAILURES** |
| `tests.test_c23_str_contains` | ModuleNotFoundError — not carried by the merge |

**The milestone is real:** the ASCII-classifier slice now passes on a single
branch, unassisted. That is the claim the packet made prematurely two turns ago,
now true and verified.

### Regression 1 — unbounded parameter recursion is no longer rejected before lowering

A/B on the same programs, pre-merge versus post-merge:

| program | `e9abcd7` (pre-merge) | `fd5c5d5` (post-merge) |
| --- | --- | --- |
| `fn loop() -> Int { return loop() }` (zero-arg) | rejected: "…; recursive calls are unsupported" | rejected, recursion clause **gone** |
| `fn loop(value: Int) -> Int { return loop(value) }` (parameter) | rejected: "one-parameter calls require one argument and a call-free target expression" | **emitted**, then the C compiler fails |

Post-merge, the parameter case emits C and clang rejects it:

```
error: all paths through this function will call itself [-Werror,-Winfinite-recursion]
```

Because Pepin compiles with `-Werror`, that surfaces as a raw C compiler error
rather than a Pep diagnostic. No bad binary is produced — the compile fails — but
the contract that the emitter rejects unsupported constructs before native
lowering is broken, and the message is no longer Pep's. The `test_a14_c23`
recursion guard is therefore a legitimate test, not a stale one.

### Regression 2 (minor) — diagnostic precision for zero-argument recursion

The zero-arg case is still rejected, but the message no longer mentions
recursion: it now reads "zero-argument calls require a call-free scalar result,
safe record construction, or direct recursive-union constructor result". A
compiler author reading that is told about zero-argument calls, not the actual
problem.

### Stale exemplar in a second file

`tests/test_a14_c23.py:335` still asserts that `return length([1, 2])` is
unsupported. That program is now supported **and correct** (prints `2`, matching
the interpreter). The integrator applied this fix to `test_c23_cli.py` but not to
`test_a14_c23.py`, which carried the same assumption.

### Also missing from the merge

Agent 2's `tests/test_c23_str_contains.py` was not carried across, so its
short-circuit tests do not run on the integrated line. Absence, not failure — but
the integration took the emitter without the tests that guard it.

**Recommended fixes, in order:** put Agent 1's recursion guard back on the merged
line (or port it into the Agent 2 emitter); restore the recursion clause in the
zero-argument diagnostic; update the `test_a14_c23.py:335` exemplar; carry
`test_c23_str_contains.py`. None applied here — they are builder-owned files.

## Lean 4 proof validation — independently reproduced (Agent 3)

The peer verification lane landed `a41d967` claiming a passing Lean 4 kernel
check (`MODEL_PROVED`, value-copy model DEC-001). Since "continue Lean 4 proof
validation" sits in this lane's acceptance, it was reproduced rather than
restated.

| check | command | result |
| --- | --- | --- |
| build | `lake build` | exit 0, "Build completed successfully (5 jobs)", 3.9s |
| positive model | `lake env lean Verification/AliasedCounterexample.lean` | exit 0 |
| **negative control** | `lake env lean BrokenVariant.lean` | **exit 1, "Type mismatch"** — proof checking is real, not skipped |
| token scan | `sorry` / `admit` / `native_decide` / leading `axiom` | 4 hits, **all documentation prose** ("do NOT add `sorry`/`admit`", "No `sorry`, `admit`, `axiom`, or `native_decide`"); 0 in code; 0 axiom declarations |
| axioms | `#print axioms` on `idx_upd_same`, `idx_upd_other`, `editOrig_copy`, `edit_takes_effect`, `copy_preserved`, `pepDecEq` | every one: **`[propext]` only** |

Toolchain: `leanprover/lean4:v4.35.0` in `~/.elan/toolchains`, via elan 4.2.4
from the official `leanprover/elan` release (scoop manifest hash `fad2e980…`).
No Defender detections during the install or the builds; protection on, no
exclusions.

**Scope caveat, which matters more than the label:** `MODEL_PROVED` covers the
*model*, not the implementation. Correspondence between the Lean model and real
Pep execution remains `TESTED` (OCaml interpreter probes), not proved. The
negative control stays valuable precisely because the analogous property fails
under shared-backing semantics.

So the Lean strand of this lane's acceptance now has independent evidence, and
the toolchain blocker recorded earlier in this report is genuinely resolved —
resolved by the #22 clearance, not by weakening a control.

## Adversarial differential on short-circuit lowering (Agent 3)

Independent harness at `fd5c5d5`: for each program, compare the Pep interpreter
(`pep.ps1 run`) against the emitted native binary (`pep.ps1 run-c23`), using a
trap function (checked division by zero) so that evaluating the wrong side is
observable.

**Short-circuit semantics for literals are correct.** All four literal cases
agree, including the ones that must trap:

| program | interpreter | native |
| --- | --- | --- |
| `true \|\| trap()` | `1` | `1` |
| `false \|\| trap()` | trap | trap |
| `false && trap()` | `0` | `0` |
| `true && trap()` | trap | trap |

So nothing is eagerly evaluated. The lowering is not broken — it is **partial**,
and the partiality is shape-dependent in a way that looks accidental:

| expression shape | native |
| --- | --- |
| `identity(true) == true \|\| bomb()` | **agrees** |
| `identity(true) == true \|\| identity(false) == true` | **agrees** |
| `identity(true) \|\| bomb()` | **agrees** |
| `identity(true) \|\| identity(false)` | **agrees** |
| `p1(66) \|\| p2(66)` (one-param calls) | **agrees** |
| `yes() \|\| no()` (all zero-arg) | **unsupported** |
| `true \|\| yes()` (literal + zero-arg) | **unsupported** |
| `yes() == true \|\| bomb()` (zero-arg as `==` target) | **unsupported** |
| `(yes() == true) \|\| (no() == true)` | **unsupported** |

**The rule:** a zero-argument Boolean call can appear as an operand of `&&`/`||`
only if a *parameterised* call also appears in the same expression. An expression
composed only of zero-argument calls, or a zero-argument call compared with `==`,
or a literal beside a zero-argument call, is rejected as unsupported. That
enabling condition is incidental rather than principled, and it matters: Lucy's
own lexer composes zero-argument helpers such as `lexer_start()`.

**Why Agent 2's own test did not catch this.** Their test is genuine — it emits
and compiles under clang and gcc — but its shape is
`identity(false) == true && bomb() || identity(true) == true || bomb()`, which
contains parameterised calls throughout. I reproduced that exact shape and it
agrees. It is simply not representative of plain helper composition, so the gap
is outside what the test covers.

**Two errors of mine, recorded rather than hidden.** Four probes in my first pass
used `1 < 2`; Pep has no `<` operator (`PEP_UNEXPECTED_CHARACTER: Unexpected
character '<'`), so those cases were invalid programs and their "divergence" was
my mistake, not the compiler's. Separately, that pass showed the C23 path
reporting `Pep C23 parser AST node ids are not exactly 0..n-1` and later
`Pep C23 emission inputs do not match the authorised source revision` for an
unparseable program, instead of the parse error itself — a diagnostic-quality
note for the emitter owner, not a correctness bug.

## Exhaustive classifier differential — semantics verified, native sweep blocked by the emitter budget (Agent 3)

The accepted slice samples five byte values. This attempts the whole domain: a Pep
`while` loop over 0..255 accumulating a checksum per classifier, compared across
three independent computations — a Python model of the classifier semantics, the
Pep interpreter, and the emitted native binary.

**Interpreter and Python agree exactly, over all 256 values:**

| classifier | Python model | interpreter |
| --- | --- | --- |
| `ascii_letter` | 5010 | 5010 |
| `ascii_digit` | 535 | 535 |
| `ascii_continue` | 5545 | 5545 |

That is a stronger statement about the classifiers than the five-case slice makes.

**The native arm cannot run it.** Every variant fails with:

```
Pep C23 error: emit checked source: expected outcome='ok', received
{'error': {'code': 'PEP_RUNTIME_STEP_LIMIT',
           'message': 'Execution step budget exceeded at 7630:12'}}
```

Three things follow, each measured rather than inferred:

1. **The wall has moved from the checker to the emitter.** The failing call is
   `emit checked source` — the emitter tool invocation — not the checker. Agent 1's
   bounded staging did its job; at this size the emitter stage is now the binding
   constraint.
2. **It is source-complexity dependent, not trip-count dependent.** The identical
   ~512-byte program with `i <= 3`, `15`, `63` and `255` all fail with the same
   code. A three-iteration loop does not help, so this is AST cost, not runtime
   work. A minimal `while` program alone (three lines) emits fine.
3. **Consequence for the milestone:** the ASCII-classifier closure cannot yet be
   verified exhaustively for native execution, and the reason is the stage budget
   rather than a missing language feature. That is worth stating explicitly next
   to any "native-verified" claim.

**A separate quirk found while isolating:** `var` plus assignment with no loop is
rejected ("functions require local bindings and supported loops followed by one
return"), while the same `var` inside a `while` is accepted. Mutable binding thus
appears to require a surrounding supported loop — harmless, but surprising enough
to be worth documenting for whoever writes Lucy's stateful functions.

## Loop-body support, and why `utf8_check` is further away than the budget (Agent 3)

**Correction to the section above.** I recorded the exhaustive native sweep as
blocked by the emitter step budget. That was only half right: my first harness
also used an unsupported loop-body form, and in the larger variant the budget
error *masked* it. With a supported body form the budget still binds, so both
limits are real, but the construct limit had to be separated out first.

Measured loop-body support at `fd5c5d5`:

| loop body | native |
| --- | --- |
| `total = total + (i + 1)` (plain assignment) | **OK** (returns 10) |
| `let n = i + 1` then assignment | **unsupported** — "while bodies support assignments, returns, and assignment-only conditionals" |
| `if 1 <= i { total = total + i } else { }` | **unsupported** — "loop conditionals require non-empty assignment branches" |

So the emitter's loop bodies accept assignments, returns, and conditionals whose
*both* branches assign. A `let` inside a loop is not a supported form.

### What that means for the next component

Lucy's `utf8_check` uses exactly the unsupported shape:

```
while !(width <= j) {
  let next = byte_at(source, offset + j)
  if !(128 <= next) || !(next <= 191) { return Utf8Check { ... } } else { }
  codepoint = codepoint * 64 + next - 128
  j = j + 1
}
```

I reproduced that shape with the `SourceBytes` call stubbed to a plain integer
expression, and it is rejected with the same message. **Therefore `SourceBytes`
lowering alone will not make `utf8_check` emittable.** Either the emitter must
support `let` inside loop bodies — the language-preserving fix — or `utf8_check`
must be restructured to hoist the binding (`var next = 0` outside, assignment
inside), which changes Lucy's own source and should be a conscious decision, not a
workaround invented to please the compiler.

### Diagnostic note, second occurrence

This is the second time a construct limitation has been hidden behind a budget
error in a large program: the same masking happened earlier with the checker. It
is a argument for finishing the labelling work across every stage — see the note
below on the emitter being the one stage still unlabelled.

## Agent 2 `770efa0` verified, and the merge target state is green (Agent 3)

Agent 2's newest push adds `test_lucy_utf8_check_boolean_ranges_lower_natively`,
which extracts the exact boolean range predicates from Lucy's lexer (blob-pinned
to `12bd93a1…`), builds them as standalone functions, and diffs interpreter
against native over thirteen boundary cases: continuation bytes 127/128/191/192;
the overlong minimum at 2048; the maximum codepoint 1114111; and the surrogate
edges 55295/55296/57343/57344.

I checked its expected table against Unicode semantics independently and all
thirteen cases are correct — including the surrogate-range rejections, which are
the easiest part of that function to get subtly wrong. The test is genuine and it
emits and compiles natively.

**But the two branches are complementary rather than equivalent:**

| file | Agent 2 `770efa0` | integrated `fd5c5d5` |
| --- | --- | --- |
| `tests/pep_c23_emitter.pep` | `9573c227` | `9573c227` (identical) |
| `tests/pep_checker_a13.pep` | `9d36b948` | `dc5d7fff` |
| `examples/pep_parser.pep` | `4dd5d2a3` | `ca1d94ce` |
| `pep_c23.py` | `103a4223` | `aab2689f` |

So Agent 2's tests sit on a branch whose bundled checker predates Agent 1's work,
and three of the seven skip there with an explicit guard ("the bundled checker
predates Agent 1's str_contains contract"). On the integrated branch the test file
is absent entirely, so zero of those seven run at all.

**Verified merge-target state.** Taking `fd5c5d5` and adding only
`tests/test_c23_str_contains.py` from `770efa0`:

```
Ran 7 tests in 24.8s
OK
```

Seven of seven pass with **zero skips** — including the three that cannot run on
either branch alone. That state exists on no branch today, and it is what a
correct merge produces. Concretely: carry Agent 2's test file onto the integrated
line; no emitter change is required.

**The loop gap is unchanged.** That new test deliberately exercises the predicates
*outside* the loop, so `utf8_check` as written still cannot emit — its loop body
contains `let next = byte_at(...)`, which the emitter rejects. The predicate work
is genuine progress and the right decomposition, but the component remains gated
on loop-body `let` support (or a deliberate rewrite of Lucy's source).

## Reconciliation with the peer verification lane on the A14 delta (Agent 3)

The peer lane published `verification/receipts/FINDING-a14-stale-expectations-fd5c5d5.md`
at `06eb77e`, covering the same 11/11 → 9/11 delta I reported. We agree on the
facts and differ only in emphasis, so recording both readings rather than
defending mine:

**Where I corroborate them independently.** Their claim that
`test_a13 + test_a13_nested_records + test_c23_cli` is 95/95 at `fd5c5d5` matches
my own runs at that head (76 + 13 + 6, all green). Their `emitter.pep` pin
`4B129FA8…` matches mine. Their reading that `length([1, 2])` is now correctly
emitted and returns `2` matches my compile-and-run.

**Where they went further than I did.** They verified the parameterised
recursion rejection on **gcc** as well (`-Werror=infinite-recursion`); I had only
checked clang. That strengthens the fail-closed argument and I am adopting their
datum.

**Where I still think my framing adds something.** Their verdict is "stale test
expectations, not safety regressions", and on safety that is correct: no binary is
produced, and their three-layer model (emit-time for zero-arg, C-compile-time via
strict warnings, runtime `PEP_RUNTIME_CALL_DEPTH`) is a fair description. My
narrower point is about the *diagnostic layer*: pre-merge, parameterised
recursion was rejected **at emit time with a Pep diagnostic**; post-merge a Pep
user sees a raw C compiler error. The outcome is fail-closed either way, but the
error surface moved out of Pep. That is worth either restoring or documenting
deliberately, so that a `-Winfinite-recursion` line is not later mistaken for a
codegen bug.

**On their suggested fix.** They propose updating the assertion to pin the new
capability (emit and execute to `2`), which is better than my earlier suggestion
of swapping in a still-unsupported exemplar (`length(append([1], 2))`, verified
unsupported): pinning new behaviour tests more than avoiding it. Both are
compatible — pin the positive case, and keep a separate unsupported exemplar for
the fail-closed path.

## The `utf8_check` rewrite route is measured, and it is not cheap (Agent 3)

Last turn I suggested that hoisting `next` out of the loop would be a cheap way to
unblock `utf8_check` without touching the emitter. That suggestion does not
survive measurement. Two variants, with `byte_at` replaced by a deterministic
stand-in so the loop shape itself is exercised:

| variant | native | reason |
| --- | --- | --- |
| hoist the binding: `var next = 0` outside, `next = next_byte(...)` inside | **unsupported** | "loop conditionals require non-empty assignment branches" |
| additionally replace `else { }` with `else { bad = 0 }` | **step limit** | got past every construct check, then `PEP_RUNTIME_STEP_LIMIT` at emit |

Both produce `586` under the interpreter, so the semantics are right and the
failures are purely compiler-side.

So a source-level rewrite of `utf8_check` would need **two** restructurings —
hoisting the binding *and* replacing the `else { }` guard with an assignment — and
would then still hit the emitter's step budget. That is no longer a workaround,
it is three separate pieces of work disguised as one.

**Corrected recommendation:** treat this as an emitter track rather than a source
rewrite. In order: (1) support `let` inside loop bodies, (2) allow loop
conditionals whose branch is a `return` rather than only an assignment, (3) bring
the emitter's step cost down enough that a real function fits. Only after all
three does `utf8_check` become emittable, with `SourceBytes` lowering as a fourth
dependency on top.

## Sanitizer check: the emitted C is UB-free, and the one UB-prone case is refused (Agent 3)

Output correctness is already covered by the builder suites. This asks a different
question: does the generated C rely on undefined behaviour that merely happens to
work? Every case below was emitted, compiled with
`-fsanitize=undefined -fno-sanitize-recover=all` (so any UB aborts rather than
warns), and run.

| program | result under UBSan |
| --- | --- |
| `return 42` | clean, prints `42` |
| `9223372036854775807 + 1` | Pep's own `PEP_RUNTIME_OVERFLOW` trap — no UBSan report |
| `0 - 9223372036854775807 - 2` | `PEP_RUNTIME_OVERFLOW` — no UBSan report |
| `9223372036854775807 * 2` | `PEP_RUNTIME_OVERFLOW` — no UBSan report |
| `1 / 0` | `PEP_RUNTIME_DIVISION_BY_ZERO` — no UBSan report |
| while-loop accumulation to 385 | clean |

**No sanitizer report fired anywhere.** Checked arithmetic is doing real work
rather than catching UB after the fact, which is the claim the backend makes and
now has independent evidence for.

The one case that *is* C-level UB — `INT64_MIN / -1` — is **refused at emit time**
with "Pep C23 rejects two fallible operands because C operand evaluation order is
unspecified". That is a good design decision rather than a gap: the single UB-prone
construct is rejected before lowering instead of being relied upon.

Scope: UBSan only (AddressSanitizer was not exercised), and seven programs is a
sample rather than a proof. But it is a different axis from everything else
reported here, and it is the first evidence that the checker's arithmetic contract
survives into the generated C.

## Sanitizers extended to the wider backend, and AddressSanitizer results (Agent 3)

Following the arithmetic-only UBSan check above, the same treatment across the
wider generated C — records, lists, strings, recursion, and the classifier slice:

| program | UBSan | AddressSanitizer | output |
| --- | --- | --- | --- |
| record field access | clean | clean | `42` |
| `length([1, 2])` | clean | clean | `2` |
| `str_contains` hit / miss | clean | clean | `1` / `0` |
| bounded recursion (`countdown(10)`) | clean | clean | `42` |
| classifier slice | clean | clean | `42` |

**Twelve distinct emitted programs, no sanitizer report of any kind.** Records,
lists, string search and recursion all produce C that is both memory-safe and
free of undefined behaviour on the paths exercised.

**Practical note for anyone repeating this.** An AddressSanitizer binary built
here fails at start with exit `3221225781` (`0xC0000135`, DLL not found) unless
`clang_rt.asan_dynamic-x86_64.dll` is beside the executable or on `PATH` — it lives
in `…/llvm/current/lib/clang/23/lib/windows/`. That is a toolchain packaging
detail, not a defect in the emitted C, and it is easy to misread as an ASan
failure if you only look at the exit code.

**Merge recipe re-checked.** With Agent 2 newest tests (`77aa6b9`), `fd5c5d5` plus
`tests/test_c23_str_contains.py` from that head now runs **9 tests, OK, zero
skips**. The recipe keeps holding as the test file grows.

## Full-suite baseline at `b27b247` — all fifteen modules (Agent 3)

Agent 1's `b27b247` ("Chunk A13 binding collection under fixed budget") chunks
binding collection and raises the checker's step envelope. Verified against it:

**The emitter is still the wall, not the checker.** The exhaustive classifier
differential still fails with `PEP_RUNTIME_STEP_LIMIT` at the *`emit checked
source`* stage, exactly as at `fd5c5d5`. So the chunking did what it claimed for
the checker and did not move the emitter ceiling — consistent with the
stage-attribution reported earlier.

**Loop-body support is unchanged** at this head: `let` inside `while` still
rejected, `else { }` still requires an assignment branch, and the `utf8_check`
loop shape is still unsupported.

**Every test module in the repository, run at this head:**

| module | tests | result |
| --- | --- | --- |
| `test_a6` / `test_a7` / `test_a8` | 13 / 5 / 5 | OK |
| `test_a10` / `test_a11` | 9 / 7 | OK |
| `test_a12` | 23 | OK |
| `test_a13` | **78** | OK (289 s) |
| `test_a13_nested_records` | 13 | OK |
| `test_a14_c23` | 11 | **2 FAIL** (both known) |
| `test_c23_cli` | 6 | OK |
| `test_c23_driver_validation` | 10 | OK |
| `test_c23_real_lexer_classifiers` | 1 | OK |
| `test_cli` | 47 | OK |
| `test_textbuf_native` | 22 | **1 FAIL** (known arena CRLF) |
| `test_moonbit_cli` | 11 | OK |

261 tests, 3 failures, and all three are previously identified: the recursion
diagnostic wording and the stale `length([1, 2])` exemplar in `test_a14_c23`, plus
the pre-existing `test_arena_demo_builds_and_runs` CRLF expectation recorded at the
start of this report.

**No regression from the chunking.** `test_a13` grew from 76 to 78 tests, all
passing, including the new chunked-path cases. No Defender detections across the
whole sweep.

This is the first complete fifteen-module baseline at a post-merge head, so future
pushes can be diffed against it rather than re-litigated.

## Two updates: the recursion reading corrected, and the merge recipe now needs the emitter (Agent 3)

### The recursion finding, corrected in the peer's favour

The peer lane's `1910025` refined this and they are right. I reproduced their A/B
myself:

| arm | result |
| --- | --- |
| interpreter | exit 1, `PEP_RUNTIME_CALL_DEPTH` |
| strict (`-Werror`) | compile fails `-Winfinite-recursion`, no binary produced |
| lenient (no `-Werror`) | compiles, runs, exit 1, **`PEP_RUNTIME_CALL_DEPTH`** |
| lenient + `-Wno-infinite-recursion` | same |

So the emitted code for unbounded parameter recursion is **semantically correct**:
under lenient flags it traps with exactly the interpreter's code. My earlier
phrasing — that the emitter's rejection contract was "broken" — overstated it. The
accurate statement is narrower: emit-time rejection with a Pep diagnostic was lost,
the generated code is right, and under project flags a compile-time guard catches
it before a binary exists. The A14 expectation is stale about *where* rejection
happens, not about whether the program is safe.

### Agent 2 has moved the emitter, and the merge recipe changed with it

`46c5af6` ("Exercise Lucy string stage guards natively") is **not** test-only:
`tests/pep_c23_emitter.pep` moved from blob `9573c227` to `8493e9d3`, adding Str
comparison and binary-operation lowering.

That breaks the previous recipe. `fd5c5d5` plus only the newest *test file* now
fails 2 of 11 with "Pep C23 Str comparison and binary operations are not yet
lowered", because the integrated emitter predates the feature.

The correct merge target is both files from `46c5af6`:

| state | result |
| --- | --- |
| `fd5c5d5` + `46c5af6` emitter (blob `8493e9d3`) + `46c5af6` tests | **11 tests, OK, zero skips** |
| accepted classifier slice, same emitter | 1 test, OK |
| `test_a14_c23`, same emitter | 11 tests, 2 known failures (unchanged) |

On Agent 2 own branch the suite is 11 tests with 3 skipped; combined with Agent 1
checker the skips disappear and everything passes.

**Practical consequence for the integrator:** the "carry the test file across"
recipe is finished. The next integration must take `tests/pep_c23_emitter.pep` and
`tests/test_c23_str_contains.py` together from `46c5af6`, on top of Agent 1 line.

## Str comparison lowering: supported, with one principled refusal (Agent 3)

Re-probing Str behaviour against the newest emitter (blob `8493e9d3`, from Agent 2
`784050c`) on Agent 1 `eb8f7c0`. My first pass read as "Str comparison
unsupported" and that was misleading, so the shape was bisected properly:

| comparison form | result |
| --- | --- |
| `left == right` (both variables) | **emits** |
| `left == "a"` / `"a" == right` (one literal) | **emits** |
| `left != right` (variables) | **emits** |
| `"a" == "a"` (both literals) | unsupported — "rejects two fallible Str comparison operands because C operand evaluation order is unspecified" |
| `"a" != "b"` (both literals) | unsupported, same reason |

So Str comparison lowering works. The single refusal is **both operands literal**,
and the reason is principled rather than arbitrary: with two potentially trapping
operands in a context where C leaves evaluation order unspecified, the emitter
declines rather than picking an order silently. That is the same rule that rejects
`INT64_MIN / -1` and the "two fallible operands" cases in the arithmetic path.

Worth noting for whoever documents this: the same underlying restriction surfaces
with **two different messages** depending on context — a conditional-return
function whose `if` condition is a Str comparison reports "functions require local
bindings and supported loops followed by one return", while `let same: Bool = "a"
== "a"` reports the fallible-operands message. A user hitting the first would not
guess it was about Str comparison at all.

**Merge target re-verified** with Agent 2 newest tests (`784050c`):

| state | result |
| --- | --- |
| `eb8f7c0` + `8493e9d3` emitter + `784050c` tests | **12 tests, OK, zero skips** |
| same tree, `test_c23_cli` | 6/6 OK — the `"a" == "a"` exemplar is still refused, so no third merge-breaker |
| same tree, accepted classifier slice | 1 test, OK |
| same tree, `test_a14_c23` | 11 tests, 2 known failures (unchanged) |
| same tree, `test_a12` | 23/23 OK |

## What actually blocks emitting Lucy's lexer — a counted inventory (Agent 3)

The exotic gaps I had been probing turn out to be the least of it. Counting the
constructs in `examples/pep_lexer.pep` (494 lines) against measured emitter
support:

| construct | sites in the lexer | emitter | verdict |
| --- | --- | --- | --- |
| `let` inside a `while` body | **13** (across 4 loops; lines 73, 220, 226, 241, 257, 267 …) | **unsupported** | the main blocker |
| empty `else { }` branch | **35** | **unsupported in every context tested** | pervasive blocker |
| `SourceBytes` access (`byte_at`, `source_bytes`) | many | unsupported | required for byte handling |
| zero-argument call inside `\|\|`/`&&` | 1 function exists (`lexer_start`), **0** boolean-context uses | unsupported | **not blocking** |
| Str literal compared to Str literal | 0 | unsupported | **not blocking** |

The empty-`else` measurement matters because I had previously only seen it fail
inside a loop. It fails everywhere:

| probe | result |
| --- | --- |
| `if 1 <= 2 { return 1 } else { }` in a function body | unsupported — "functions require local bindings and supported loops followed by one return" |
| `if 1 <= 2 { x = 5 } else { }` in a function body | unsupported, same message |
| `if i == 0 { return 9 } else { }` inside a `while` | unsupported — "loop conditionals require non-empty assignment branches" |

So Pep's habitual `else { }` idiom — 35 sites in this one file — is currently
unemittable regardless of context.

**Reprioritisation this implies.** The zero-argument composition gap I reported
earlier is real and still present after two emitter revisions (`9573c227` then
`8493e9d3`), but Lucy's lexer contains exactly one zero-argument function and never
uses it in a boolean context. It is therefore **not** on the critical path, and
Agent 2 should not prioritise it over loop-body `let` and empty-`else` support,
which between them account for 48 syntactic sites in a single real file.

The honest summary of distance: the accepted slice passes because it is written in
the narrow dialect the emitter accepts. Lucy's actual lexer is written in a
different dialect — `let` inside loops and `else { }` throughout — and closing that
stylistic gap matters far more than adding further expression forms.

## Straight-line boundary extension blocked, and budget-masking caught a third time (Agent 3)

Tried to widen the accepted slice's native coverage from five sampled bytes toward
the real boundaries (0/47/48/57/58/64/65/90/91/94/95/96/97/122/123/127/128/255)
using straight-line code rather than a loop, to avoid the `let`-in-loop wall. It
does not work, and the reason is instructive.

The accumulator shape itself is unsupported, independent of size:

| program | result |
| --- | --- |
| `var total = 7` then `return total` | **emits** |
| `if 1 <= 2 { return helper(1) } else { return helper(0) }` | **emits** |
| `var total = 0`, then `if c { total = total + 1 } else { total = total + 0 }`, then `return total` | **unsupported** — "functions require local bindings and supported loops followed by one return" |

So mutating a local inside a conditional requires a surrounding supported loop. A
plain `var` with a return is fine; a conditional-return without `var` is fine; the
combination is not.

**And when the classifier closure is present, that construct limitation is not what
you see.** With the same program plus the three classifier functions, every size
from 2 statements (240 bytes) upward reports `STEP_LIMIT[emitter]` instead — the
budget error fires before the construct check. That is the third independent
occurrence of this masking (checker earlier, loop bodies earlier, emitter now), and
it is the strongest argument yet for reordering: a compiler author told "step
budget exceeded" will go and optimise, when the actual answer is "this shape is not
supported".

**Correction to my own ladder.** A first version of this probe compared
"with closure" against "without closure", but the without-closure variant
references `ascii_continue` and so fails for an undefined function — that column was
meaningless, not evidence. The valid comparison is the self-contained table above.

Consequence for the slice claim: native coverage stays at the five sampled byte
values. Widening it needs either the construct (`var` in a conditional) or a
straight-line form the emitter accepts, and neither exists today.

## Correcting my own recommendation: the budget cannot be "reordered" (Agent 3)

Last turn I suggested the construct check should run before the budget check. Reading
the mechanism shows that advice was incoherent, so it is withdrawn.

The budget is not a gate in a sequence of checks. It is consumed by the interpreter
loop that evaluates the emitter itself (`pep_ocaml.ml` at `eb8f7c0`):

```
830  let execute ?(step_limit=1_000_000) ... =
832    let remaining_steps = ref step_limit in
834      decr remaining_steps;
835      if !remaining_steps < 0 then runtime "PEP_RUNTIME_STEP_LIMIT" "Execution step budget exceeded" sp
```

and the emitter is a 3,141-line Pep program run through exactly that path
(`tool_step_budget = 100_000`, line 1377). There is no checklist to order: the
analysis simply stops wherever it happens to be, which is why every observed failure
carries a position inside the emitter bundle (`2441:26`, `7630:12`, …).

**So the "masking" is a reporting problem, not an ordering bug.** A
`PEP_RUNTIME_STEP_LIMIT` from the emitter says nothing about the program under
analysis — it says the analysis ran out of steps. That is a meaningful correction to
how my three observations should be read, and it changes what is worth doing:

1. **Reporting (cheap, honest):** `pep_c23.py` could map an emitter-stage
   `PEP_RUNTIME_STEP_LIMIT` to an explicitly inconclusive outcome — "analysis
   incomplete" — rather than surfacing it as the program's verdict. Today a caller
   cannot distinguish "this program is unsupported" from "I gave up part-way", and
   neither can a reader of the issue thread.
2. **Cost:** reduce the emitter's per-node work, the same direction Agent 1 has been
   taking the checker, which is the durable fix.
3. **Budget:** raising it is tempting and is explicitly not the plan (#20). Note that
   it would only convert a misleading error into a later, possibly still-misleading
   one, since cost grows with program size.

Nothing about the observed facts changes — the accumulator shape really is
unsupported, `let`-in-loop and empty-`else` really are unsupported, and the budgets
really do bite before those diagnoses surface. What changes is the causal story and
therefore the fix.

## Baseline moved to `eb8f7c0` — 262 tests, same three known failures (Agent 3)

Agent 1's second chunking round ("Chunk staged A13 binding type inference") is also
non-regressive. Full fifteen-module sweep at the new head, clean worktree:

| module | tests | result |
| --- | --- | --- |
| `test_a6` / `test_a7` / `test_a8` | 13 / 5 / 5 | OK |
| `test_a10` / `test_a11` | 9 / 7 | OK |
| `test_a12` | 23 | OK |
| `test_a13` | **79** | OK (310 s) |
| `test_a13_nested_records` | 13 | OK |
| `test_a14_c23` | 11 | **2 FAIL** (known) |
| `test_c23_cli` | 6 | OK |
| `test_c23_driver_validation` | 10 | OK |
| `test_c23_real_lexer_classifiers` | 1 | OK |
| `test_textbuf_native` | 22 | **1 FAIL** (known arena CRLF) |
| `test_moonbit_cli` | 11 | OK |
| `test_cli` | 47 | OK |

**262 tests** (up one, `test_a13` 78 → 79 with the new chunked-path case), and the
same three previously identified failures. Nothing new broke; the second chunking
round cost nothing measurable in test time either (310 s versus 289 s for a
one-test-larger suite).

**Also checked as part of this round:** the emitter-stage budget failure is *still*
reported by a bare `require(emitted, "outcome", "ok", "emit checked source")` at
`pep_c23.py:629`. So the inconclusive-outcome remedy proposed above has not landed
yet, and emitter budget errors still read as program verdicts.

## SourceBytes lowering has started landing (Agent 3)

Agent 2's `7bfb819` ("Lower checked SourceBytes length to C23") moves the emitter to
blob `23ef2b19` and adds `byte_length` lowering via a `pep_byte_length` runtime
helper that checks a null data pointer with non-zero length and a length beyond
`INT64_MAX`. Its suite runs **14 tests, OK, zero skips** on the combined target
(`eb8f7c0` plus that emitter and tests).

Measured support now, with `SourceBytes` as a function parameter:

| form | result |
| --- | --- |
| `byte_length(source)` | **emits** |
| `byte_at(source, 0)` | **emits** |
| `byte_slice(source, 0, 1)` | unsupported — "calls require a known target and at most three arguments" |
| `utf8_slice(source, 0, 1)` returning `Str` | unsupported — "functions require supported parameters and scalar or record results" |
| `byte_length(source_bytes())` (the original blocker) | unsupported — **now with a specific message**: "byte_length currently requires a direct SourceBytes parameter" |

That last row is real progress in its own right: the generic "calls require a known
target" message became a precise statement of what the lowering needs.

### What still stands between here and `utf8_check`

The remaining obstruction is a function-shape rule, not `SourceBytes`:

| function body | result |
| --- | --- |
| `let x = byte_at(source, o)` then `return x` | **emits** |
| `if f(66) { return 1 } else { return 0 }` where `f` is a Pep function | **emits** |
| `let x = byte_at(source, o)` then `if x <= 127 { return 1 } else { return 0 }` | unsupported |
| `if byte_at(source, o) <= 127 { return 1 } else { return 0 }` | unsupported |
| `let v = byte_at(...)`, `let small = v <= 127`, then `if small { ... }` | unsupported |

So a conditional-return body tolerates a user-function call in the condition but not
a builtin, and not a local binding alongside it — and hoisting the builtin into
`let` does not help. The accepted slice passes because its condition is a
user-function call with no bindings.

**The actionable problem here is the diagnostic, not the restriction.** All four
failing shapes return the identical "functions require local bindings and supported
loops followed by one return". A compiler author cannot tell from that message
whether the issue is the builtin, the binding, the conditional, or the
combination — and I could not separate them by reading either. This is the second
concrete instance of the reporting theme: distinct causes collapsing into one
message, which then reads as a program verdict.

## Newest heads together: `f7efa23` + `7bfb819` (Agent 3)

Agent 1's third chunking round (blob `f7efa23`, "Reduce staged checker composition
costs") with Agent 2's newest emitter and tests (`7bfb819`, emitter blob
`23ef2b19`):

| suite | result |
| --- | --- |
| `test_a13` | **80 tests OK** (305 s) — grew from 79 |
| `test_a12` | 23/23 OK |
| `test_c23_str_contains` | **14/14 OK**, zero skips |
| `test_c23_real_lexer_classifiers` | 1/1 OK |
| `test_c23_cli` | 6/6 OK |
| `test_a14_c23` | 11 tests, the **same 2 known failures** |

135 tests across those six suites with only the two known `test_a14_c23`
expectations failing. The third chunking round is non-regressive, and the newer
emitter adds no new failure to the accepted line — which is the specific thing worth
checking before an integration.

**The emitter wall still does not move.** The 18-value straight-line boundary
program still fails at the `emit checked source` stage, exactly as at `eb8f7c0` and
`b27b247`. That is consistent with the chunking work targeting the *checker*: the
checker stage passes, the emitter stage does not. Third chunking round, third time
the emitter is the binding constraint.

## Chunk size is a trade-off, not a free win: measured crossover (Agent 3)

Agent 1's `d83ac67` ("Increase staged checker analysis chunk size") passes every
test suite, but it moves the checker's capacity in a mid-size band. Reproduced three
times on both heads, same programs:

| statements | bytes | `f7efa23` (smaller chunk) | `d83ac67` (larger chunk) |
| --- | --- | --- | --- |
| 13–17 | 1330–1628 | fails at **emitter** | fails at **emitter** |
| **18–19** | **1701–1774** | fails at **emitter** (checker **succeeds**) | fails at **checker** |
| 20 | 1847 | fails at **checker** | fails at **checker** |

So between roughly 1,700 and 1,800 bytes the larger chunk makes the *checker* fail on
programs it previously checked successfully. The mechanism is straightforward: a
bigger chunk does more work inside a single tool invocation, and the per-invocation
budget is fixed at 100,000 steps, so per-call cost rises with chunk size. The
benefit — fewer invocations for very large programs — does not help this band.

This is not a test regression: `test_a13` is **80/80 OK** at `d83ac67` (322 s,
against 305 s at `f7efa23`), `test_a12` 23/23, `test_c23_str_contains` 14/14 zero
skips, `test_c23_cli` 6/6, slice 1/1, and `test_a14_c23` keeps exactly its two known
failures. The cost is invisible to the suite and visible only when measuring capacity
directly.

**Recommendation:** treat chunk size as a knob with an optimum rather than a
monotonic improvement, and measure capacity (largest program the checker completes)
alongside wall time when changing it. If the goal is to check larger programs, the
per-invocation budget and the chunk size have to move together, or the chunk must be
made cheaper per node.

## `39a487f` clears the `utf8_check` construct barrier — and exposes an integration surface (Agent 3)

Agent 2's `39a487f` ("Lower byte locals and conditionals inside C23 loops") addresses
exactly the two blockers this report ranked highest. Measured against it (A1
`d83ac67` plus emitter blob `e806ee66`):

| probe | before | now |
| --- | --- | --- |
| `let` inside a `while` whose initializer is `byte_at(...)` | unsupported | **accepted** — reaches the emitter stage |
| `let` inside a `while` with an arithmetic initializer | unsupported | unsupported, but with a **specific** message: "while-local lets currently require a byte_at initializer" |
| empty `else { }` at top level | unsupported | **emits** |
| Lucy's real `utf8_check` loop shape (verbatim, `byte_at` initializer) | unsupported | **accepted**, fails only on `PEP_RUNTIME_STEP_LIMIT` |
| full `utf8_check` function as written in the lexer | unsupported | **accepted**, fails only on `PEP_RUNTIME_STEP_LIMIT` |

So the construct barrier in front of `utf8_check` is effectively gone: the function as
Lucy writes it now passes every emission check and stops at the step budget. Combined
with the earlier `byte_length`/`byte_at` lowering, the remaining obstacle for that
component is budget, not language.

This also retires much of the blocker inventory above: of the 48 sites counted, the
13 `let`-in-loop and 35 empty-`else` sites are no longer categorical blocks — assuming
their initialisers are `byte_at`-shaped, which for the lexer's byte readers they are.

### Integration surface this exposes

Agent 2's branch carries two test modules that do not exist on Agent 1's line:
`test_c23_collections.py` (129 tests) and `test_c23_nested_record_emission.py` (41
tests). Carried onto the integrated tree with their emitter, they do not pass:

| module | on A1 `d83ac67` + A2 emitter | on A2's own branch `8e076e2` |
| --- | --- | --- |
| `test_c23_collections` | **2 failures, 91 errors** | did not finish within 40 minutes |
| `test_c23_nested_record_emission` | **6 errors**, 0 skipped | 1 error, 5 skipped |

Every failure I inspected is `PEP_RUNTIME_STEP_LIMIT` at the **emitter** stage, not a
missing feature. The skips vanishing is itself informative: they were guarded by
"the bundled checker predates Agent 1's contract", so the newer checker makes five
more tests actually run — and several of those then exhaust the emitter budget.

**Hypothesis, not established:** `test_c23_collections` probably *passes* on Agent 2's
branch and is simply slow (129 native compile-and-run cases), whereas on the combined
tree most cases abort in ~2 s at the emitter budget. That would mean the suites are
not broken but the emitter budget cannot carry them once the newer checker's output is
in play. I did not complete that measurement — the run exceeded a 40-minute cap — so it
is a hypothesis with evidence pointing at it, not a finding.

**What this means for integration:** merging Agent 2 fully would bring a large red
surface whose cause is the emitter stage budget, not the feature work. That is the same
wall this report has now measured from four directions (two chunking rounds, the
boundary ladder, the utf8_check probes). Whoever integrates should expect it and
should not read those 91 errors as regressions in the collections feature.

## Inconclusive reporting landed, and the collections failures are now attributed cross-lane (Agent 3)

Two things closed this round.

### The inconclusive-outcome recommendation was implemented, and it works

Commit `e603e79` "Report compiler tool budget limits as inconclusive" adds
`analysis_status` to the tool-budget error. Verified end to end — the full
`utf8_check` probe now reports:

```
analysis_status=INCONCLUSIVE; stage=emitter; code=PEP_RUNTIME_STEP_LIMIT;
target_document=doc-3; target_revision=sha256:40fc0efacff5287…
```

That is precisely the distinction this report asked for two rounds ago: a caller can
now tell "this program is not supported" from "the analysis ran out of steps", and
the message no longer reads as a verdict on the program. Credit to whoever picked it
up; the earlier "bare require at pep_c23.py:629" is gone.

### The collections failures are confirmed cross-lane, not a feature regression

Last round I flagged as a *hypothesis* that `test_c23_collections` passes on Agent 2's
branch and fails only when combined. That is now measured rather than hypothesised.

Three tests that fail on the combined tree (`7bfa690` + emitter `b3b7330e`):

| test | combined tree | Agent 2's own branch `edbe3b6` |
| --- | --- | --- |
| `test_pep_list_sum_overflow_matches_interpreter_runtime_code` | error | **OK, 5.4 s** |
| `test_pep_list_product_overflow_matches_interpreter_runtime_code` | error | **OK, 5.3 s** |
| `test_pep_written_all_equal_helper_matches_interpreter_on_clang_and_gcc` | error | **OK, 15.8 s** |

Same emitter file in both trees (blob `b3b7330e`). The differences are Agent 1's
checker and Agent 1's driver. So the failures are caused by the **combination**: with
Agent 1's checker output, Agent 2's emitter exceeds its 100,000-step budget on these
programs; with Agent 2's own (older) checker it fits.

That also explains the earlier 40-minute timeout: on Agent 2's branch these tests do
real native compile-and-run work (5–16 s each, so ~10–35 min for 129 tests), whereas on
the combined tree most abort in ~2 s at the budget.

**Integration consequence, stated plainly:** merging Agent 2's emitter onto Agent 1's
line will turn roughly 91 collections tests red, and the cause is the emitter's step
budget against the newer checker's output — not the collections work. Whoever performs
the merge should either reduce the emitter's per-node cost, revisit the per-invocation
budget, or expect to integrate in stages with that suite quarantined until then.
No changes were made to the accepted release. No compiler source was modified
for the delivered result: the budget and construct experiments were run on
temporary local edits and reverted (`git status` clean, patched `pep.exe`
deleted) before this report.
