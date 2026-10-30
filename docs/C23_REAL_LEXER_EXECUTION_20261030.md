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
No changes were made to the accepted release. No compiler source was modified
for the delivered result: the budget and construct experiments were run on
temporary local edits and reverted (`git status` clean, patched `pep.exe`
deleted) before this report.
