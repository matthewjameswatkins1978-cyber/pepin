# First Pep-written Terror Bats oracle

A real Terror Bats judgement written in ordinary Pep: the `exit_code`
falsification condition, evaluated by Pep's own checker and interpreter.

This is not a wrapper and not a reimplementation of the framework in another
language. It is the smallest honest kernel of "Terror Bats in Pep": given recorded
observations, decide whether the claim was falsified, with the same verdict
semantics as the Rust reference.

## Reference contract pinned, not guessed

Read from The-Terror-Bats `@ d5e6404` (`src/oracle.rs`):

```rust
Condition::ExitCode { step, equals: Option<i64>, not_equals: Option<i64> }
```

| Reference behaviour | Source |
| --- | --- |
| exactly one of `equals` / `not_equals`, else INVALID | `validate`: "exit_code requires exactly one of `equals` or `not_equals`" |
| bad step reference → Undetermined | `eval_condition` |
| step did not execute → Undetermined | `eval_condition` |
| step produced no exit code → Undetermined (a crash is never a falsification) | `eval_condition` |
| `fired = (code == equals)` / `fired = (code != not_equals)` | `eval_condition` |
| `fired ? Falsified : NotFalsified` | `OracleResult` |

Verdict labels in the reference and here: `Falsified` → **PROVEN**,
`NotFalsified` → **NOT OBSERVED** (never a certificate), `Undetermined` →
**INCONCLUSIVE**, malformed spec → **INVALID**.

## The Pep implementation (typed)

`oracle.pep` — ordinary functions over typed values, no host process spawning, no
imports, and no sentinel:

```pep
type Mode = EqualsMode(Int) | NotEqualsMode(Int) | BothModes(Int, Int) | NoMode(Str)
type ExitObservation = ObservedExit(Int) | AbsentExit(Str)
type EvidenceStep { index: Int, exit: ExitObservation }
type Verdict = Proven(Str) | NotObserved(Str) | Inconclusive(Str) | Invalid(Str)
```

- `judge(mode, observation)` — validation first (a malformed mode is `Invalid`,
  never evidence about the claim), then `AbsentExit` is `Inconclusive`, then the
  reference's fired/not-fired rule.
- `judge_step(mode, step)` — the same judgement over a recorded evidence record.
- `verdict_label(verdict)` / `verdict_reason(verdict)` — the label and the reason a
  verdict carries, so a result explains itself.

Missing evidence is now an explicit `AbsentExit(reason)` case instead of a sentinel
integer, and a malformed specification is a representable `BothModes`/`NoMode`
instead of two booleans that could contradict each other.

## Condition composition

`OracleExpr::All` / `Any` / `Not` are Kleene three-valued logic in the reference,
not boolean logic, and an empty conjunction is **not** vacuously true. The Pep
engine now reproduces that shape over its own typed verdicts:

```pep
type Found = NotFound() | FoundReason(Str)
fn compose_all(verdicts: List[Verdict]) -> Verdict
fn compose_any(verdicts: List[Verdict]) -> Verdict
fn compose_not(verdict: Verdict) -> Verdict
```

| Rule | Reference (`src/oracle.rs`) | Here |
| --- | --- | --- |
| `all` | NotFalsified wins, then Undetermined, then Falsified | `NotObserved` > `Inconclusive` > `Proven` |
| `any` | Falsified wins, then Undetermined, then NotFalsified | `Proven` > `Inconclusive` > `NotObserved` |
| `not` | swaps Falsified/NotFalsified, leaves Undetermined | swaps `Proven`/`NotObserved`, leaves `Inconclusive` |
| `all: []` / `any: []` | Undetermined, "empty combinator: nothing to judge" | `Inconclusive("empty combinator: nothing to judge")` |
| malformed child | `validate` runs on every node before `evaluate`, so nothing is evaluated | the child's `Invalid` propagates carrying its own reason |

Composition is written as assignment in priority order — least decisive first, most
decisive last — so the surviving verdict is the most decisive finding and no
`if`-nesting is needed. `Invalid` is assigned last because a malformed experiment
must never be composed into a judgement, the same principle as case 9.

Because each component is an ordinary function, composition composes: `compose_not`
of `compose_all` of any list of `judge(...)` results is just a call.

## Run it

```powershell
cd test-runner/bats-pep
.\..\..\pep.ps1 check oracle.pep --json          # status valid, 0 diagnostics
# selftest calls run at top level because the interpreter does not call fn main
$lib = Get-Content oracle.pep -Raw; $st = Get-Content selftest.pep -Raw
New-Item -ItemType Directory -Force -Path ..\..\_build | Out-Null
[IO.File]::WriteAllText("$PWD\..\..\_build\composed.pep", $lib + "`n" + $st, [Text.UTF8Encoding]::new($false))
.\..\..\pep.ps1 run ..\..\_build\composed.pep
```

Observed (29 cases; each prints its verdict label then its reason):

| # | Inputs | Verdict |
| --- | --- | --- |
| 1 | `EqualsMode(1)`, `ObservedExit(1)` | PROVEN |
| 2 | `EqualsMode(1)`, `ObservedExit(0)` | NOT OBSERVED |
| 3 | `NotEqualsMode(0)`, `ObservedExit(0)` | NOT OBSERVED |
| 4 | `NotEqualsMode(0)`, `ObservedExit(2)` | PROVEN |
| 5 | `EqualsMode(7)`, `ObservedExit(3)` | NOT OBSERVED |
| 6 | `BothModes(1, 0)`, `ObservedExit(1)` | INVALID |
| 7 | `NoMode(...)`, `ObservedExit(1)` | INVALID |
| 8 | `EqualsMode(1)`, `AbsentExit(...)` | INCONCLUSIVE |
| 9 | `BothModes(1, 0)`, `AbsentExit(...)` | INVALID (validation outranks missing evidence) |
| 10 | `judge_step` over `EvidenceStep{exit: ObservedExit(1)}` | PROVEN |
| 11 | `judge_step` over `EvidenceStep{exit: AbsentExit(...)}` | INCONCLUSIVE |
| 12 | `compose_all([Proven])` | PROVEN |
| 13 | `compose_all([Proven, Proven])` | PROVEN |
| 14 | `compose_all([Proven, NotObserved])` | NOT OBSERVED |
| 15 | `compose_all([Proven, Inconclusive])` | INCONCLUSIVE |
| 16 | `compose_all([Inconclusive, NotObserved])` | NOT OBSERVED |
| 17 | `compose_all([])` | INCONCLUSIVE (empty combinator) |
| 18 | `compose_all([Proven, Invalid(...)])` | INVALID (child's own reason survives) |
| 19 | `compose_any([NotObserved, Proven])` | PROVEN |
| 20 | `compose_any([NotObserved, NotObserved])` | NOT OBSERVED |
| 21 | `compose_any([NotObserved, Inconclusive])` | INCONCLUSIVE |
| 22 | `compose_any([Inconclusive, Proven])` | PROVEN |
| 23 | `compose_any([])` | INCONCLUSIVE (empty combinator) |
| 24 | `compose_any([Proven, Invalid(...)])` | INVALID |
| 25 | `compose_not(Proven)` | NOT OBSERVED |
| 26 | `compose_not(NotObserved)` | PROVEN |
| 27 | `compose_not(Inconclusive)` | INCONCLUSIVE |
| 28 | `compose_not(Invalid)` | INVALID |
| 29 | `compose_all` over two real `judge(...)` verdicts | NOT OBSERVED |

Case 9 is the vacuity guard: a malformed experiment must never be reported as
merely inconclusive, and case 5/6 are the infrastructure guard: missing evidence
must never be reported as a falsification.

An earlier draft of this table expected NOT OBSERVED for `equals 0, exit 0`; that
expectation was wrong, because `equals` fires when the code equals the configured
value. The table was corrected, not the oracle — recorded here because a wrong
expectation is indistinguishable from a wrong implementation until it is checked.

## Grammar and checker rules measured here (for Agent 1, minimal repros)

Each of these cost real time, so each is recorded with the smallest case that shows
it:

1. **Nullary constructors ARE matchable — with `B()`.** An earlier revision of this
   file claimed they were not. That was wrong, and Agent 1 confirmed the actual
   grammar: `B()` is a nullary constructor pattern while bare `B` is a binding.
   Measured here: `type Found = NotFound() | FoundReason(Str)` with
   `match f { NotFound() => "none"` / `FoundReason(r) => r }` is accepted and
   behaves correctly, so `compose_*` uses `NotFound()` patterns. What *is* true is
   that a bare `B` arm is an irrefutable catch-all, so any arm after it is rejected
   with `PEP_UNREACHABLE_MATCH_ARM: Match arm follows an irrefutable pattern`.
2. **A nullary constructor must be declared with empty parentheses.** `type T = A(Int) | B`
   fails with `PEP_PARSE_EXPECTED: Expected '('`.
3. **Match arms are newline-separated, and arm bodies are expressions.** Two arms on
   one line parse as one; `P(why) => { return "X" }` fails with
   `PEP_PARSE_EXPRESSION: Expected an expression` where the `{` starts.

4. **`if` requires an `else`, even an empty one.** `if c { ... }` followed by a new
   line is rejected with `PEP_PARSE_ELSE: Expected else after if block`. `else { }`
   with an empty body is accepted, and that is what the composition loops use.
5. **There are no ordering comparisons.** `<` is not a token at all
   (`PEP_UNEXPECTED_CHARACTER: Unexpected character '<'`), and `>` / `>=` are absent
   from the operator table. Available: `<=`, `==`, `!=`, `&&`, `||`, `+`, `-`, `*`,
   `/`. A loop counter must therefore be driven by `==`, `!=` or `<=`.
6. **A match arm body cannot be an assignment.** `P(w) => acc = found` fails with
   `PEP_PARSE_PATTERN: Expected a constructor pattern, binding, or wildcard` — a
   different error from the `{ ... }` case in rule 3. Assign in an enclosing `if`
   block around a `match` that returns a value.7. **`var` may hold a union and be reassigned across its cases.** `var acc =
   NotFound()` then `acc = FoundReason(...)` type-checks, and `for x in xs` over a
   `List[Union]` binds each element at the union type.

## Language dependencies found (for Agent 1, reproducible)

1. **No `Str` concatenation.** `"a" + b` is `PEP_TYPE_MISMATCH: Expected Int but
   found Str`, so a verdict message cannot be composed inline; the self-test emits
   positional lines instead. This is the main blocker for human-readable verdicts.
2. **No generic option type.** There is no `Option[T]`, but a dedicated union per
   absence is the honest substitute and it works: `AbsentExit(reason)` for a
   missing exit code, and `NotFound()` / `FoundReason(r)` for a searched-for value.
   No sentinel is needed.
3. **The interpreter does not call `fn main`.** Top-level statements execute, so a
   library entry point cannot be exercised by the interpreter today; the self-test
   is therefore top-level calls rather than a `main`.
4. **No `Str` → bytes, so `text_contains` still cannot be implemented.** This is a
   measured wall, not a guess:

   | Attempt | Result |
   | --- | --- |
   | `byte_length("abc")` | `PEP_TYPE_MISMATCH: Expected SourceBytes but found Str` |
   | `byte_length(s)` for a `s: Str` parameter | `PEP_TYPE_MISMATCH: Expected SourceBytes but found Str` |
   | `length("abc")` | `PEP_LIST_EXPECTED: Builtin 'length' expects a List, found Str` |
   | `contains("abcdef", "cd")` | `PEP_LIST_EXPECTED: Builtin 'contains' expects a List, found Str` |
   | `byte_length(source_bytes())` | checks, but `PEP_RUNTIME_SOURCE_CONTEXT: source_bytes is available only for a host-authorised v2 semanticTarget` |

   `byte_at`, `byte_slice` and `utf8_slice` all take `SourceBytes`, and the only
   producer of `SourceBytes` is `source_bytes()`, which reads the program's **own**
   source under a host-authorised v2 semanticTarget. `contains` is list membership
   with scalar element equality, not substring search. `Str` supports `==` and `!=`
   and nothing else.

   **The precise missing primitive** is either
   - `str_bytes(s: Str) -> SourceBytes`, after which `byte_length` / `byte_at`
     suffice for a byte-window substring search; or
   - `str_contains(haystack: Str, needle: Str) -> Bool` directly.

   Until one exists, `text_contains`'s judgement is not attempted: it is neither
   approximated nor delegated to Python. Composition over the conditions that *are*
   expressible is what shipped instead.

## Same-input differential against the Rust runtime

`differential.py` judges the *same* inputs twice: once with a real framework Bat
whose attack step exits with the chosen code, and once with `oracle.pep` under
Pep's interpreter. Run with `--repo <clean clone>` (default
`D:\Projects\wt-bats-clean`).

| Case | Rust runtime | Pep oracle | Expected |
| --- | --- | --- | --- |
| `equals 1`, exit 1 | PROVEN | PROVEN | PROVEN |
| `equals 1`, exit 0 | NOT OBSERVED | NOT OBSERVED | NOT OBSERVED |
| `not_equals 0`, exit 0 | NOT OBSERVED | NOT OBSERVED | NOT OBSERVED |
| `not_equals 0`, exit 2 | PROVEN | PROVEN | PROVEN |
| `equals 7`, exit 3 | NOT OBSERVED | NOT OBSERVED | NOT OBSERVED |
| both modes set | INVALID | INVALID | INVALID |
| neither mode set | INVALID | INVALID | INVALID |
| supervised process killed before exit | INCONCLUSIVE | INCONCLUSIVE | INCONCLUSIVE |
| `all: []` | INCONCLUSIVE | INCONCLUSIVE | INCONCLUSIVE |
| `any: []` | INCONCLUSIVE | INCONCLUSIVE | INCONCLUSIVE |
| `all` fired + not fired | NOT OBSERVED | NOT OBSERVED | NOT OBSERVED |
| `any` not fired + fired | PROVEN | PROVEN | PROVEN |
| `not` fired | NOT OBSERVED | NOT OBSERVED | NOT OBSERVED |
| `not` not fired | PROVEN | PROVEN | PROVEN |
| `all` with a malformed child | INVALID | INVALID | INVALID |
| `any` with an unparseable child | INVALID | INVALID | INVALID |
| `all` with an unexecuted step (`run:9`) | INCONCLUSIVE | INCONCLUSIVE | INCONCLUSIVE |

`SUMMARY cases=17 mismatches=0`.

One measurement worth recording: `terrorbats spec check` **accepts** a spec whose
`exit_code` sets both modes; the reference rejects it at **run** time with verdict
`INVALID` and `status: Invalid` ("oracle not evaluated"). The differential first
compared the wrong phase and reported a false disagreement. Validating the
validation-phase assumption is part of the work.

The "step produced no exit code" path is now compared at runtime too: the Bat
starts a supervised `Start-Sleep` process and kills it before it exits, so the step
has no exit code. The reference answers Undetermined and the Pep oracle answers
INCONCLUSIVE for the same recorded inputs (executed, no exit code). A kill or crash
is never a falsification on either side.

## Not claimed

- No process/Git host adapters, no receipts, no `pep bats` CLI, no native C23
  integration. Those are explicitly out of scope for this first kernel.
- `text_contains` is **not** implemented, because Pep cannot yet read the bytes of
  a `Str`. The precise missing primitive is recorded above rather than worked
  around.
- The differential covers the *expressible* slice. Process/Git host adapters,
  receipt generation and a `pep bats` CLI remain out of scope for this mission.
