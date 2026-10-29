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

## Run it

```powershell
cd test-runner/bats-pep
.\..\..\pep.ps1 check oracle.pep --json          # status valid, 0 diagnostics
# selftest calls run at top level because the interpreter does not call fn main
$lib = Get-Content oracle.pep -Raw; $st = Get-Content selftest.pep -Raw
[IO.File]::WriteAllText("$PWD\_composed.pep", $lib + "`n" + $st, [Text.UTF8Encoding]::new($false))
.\..\..\pep.ps1 run _composed.pep
```

Observed (11 cases; each prints its verdict label then its reason):

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

1. **A bare nullary pattern is a binding, not a constructor.** `type T = A(Int) | B()`
   then `match x { A(n) => n` / `B => 0 }` is **accepted** but `B` is an irrefutable
   catch-all — and a third arm after it is rejected with
   `PEP_UNREACHABLE_MATCH_ARM: Match arm follows an irrefutable pattern`. So a nullary
   constructor cannot be distinguished in a match at all. This oracle therefore gives
   every alternative a payload (`Proven(Str)`, `AbsentExit(Str)`), which makes each
   arm a refutable constructor pattern.
2. **A nullary constructor must be declared with empty parentheses.** `type T = A(Int) | B`
   fails with `PEP_PARSE_EXPECTED: Expected '('`.
3. **Match arms are newline-separated, and arm bodies are expressions.** Two arms on
   one line parse as one; `P(why) => { return "X" }` fails with
   `PEP_PARSE_EXPRESSION: Expected an expression` where the `{` starts.

## Language dependencies found (for Agent 1, reproducible)

1. **No `Str` concatenation.** `"a" + b` is `PEP_TYPE_MISMATCH: Expected Int but
   found Str`, so a verdict message cannot be composed inline; the self-test emits
   positional lines instead. This is the main blocker for human-readable verdicts.
2. **No option type.** "No exit code" needs a sentinel because there is no
   `Option[Int]`. Records and tagged unions exist, so a `Present/Absent` union
   would be the honest modelling choice — worth trying in a later slice rather than
   inventing anything.
3. **The interpreter does not call `fn main`.** Top-level statements execute, so a
   library entry point cannot be exercised by the interpreter today; the self-test
   is therefore top-level calls rather than a `main`.

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

`SUMMARY cases=8 mismatches=0`.

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
- The differential covers the *expressible* slice. Process/Git host adapters,
  receipt generation and a `pep bats` CLI remain out of scope for this mission.
