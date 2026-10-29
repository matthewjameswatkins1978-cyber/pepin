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

## The Pep implementation

`oracle.pep` — two ordinary functions, no host process spawning, no imports:

- `pep_no_exit_code()` — a sentinel for "no exit code", because Pep has no option
  type. Checked before any comparison, so it can never masquerade as evidence.
- `verdict_label(code)` — Int verdict code to the reference's label.
- `exit_code_verdict(...)` — validates first (a malformed experiment is never
  evidence about the claim), then treats missing evidence as `INCONCLUSIVE`, then
  applies the reference's fired/not-fired rule.

Verdict codes are Ints (`0` PROVEN, `1` NOT OBSERVED, `2` INCONCLUSIVE,
`3` INVALID) so the kernel stays inside currently supported Pep.

## Run it

```powershell
cd test-runner/bats-pep
.\..\..\pep.ps1 check oracle.pep --json          # status valid, 0 diagnostics
# selftest calls run at top level because the interpreter does not call fn main
$lib = Get-Content oracle.pep -Raw; $st = Get-Content selftest.pep -Raw
[IO.File]::WriteAllText("$PWD\_composed.pep", $lib + "`n" + $st, [Text.UTF8Encoding]::new($false))
.\..\..\pep.ps1 run _composed.pep
```

Observed (9 cases, one verdict per line):

| # | Inputs | Verdict |
| --- | --- | --- |
| 1 | `equals 1`, executed, exit 1 | PROVEN |
| 2 | `equals 1`, executed, exit 0 | NOT OBSERVED |
| 3 | `not_equals 0`, executed, exit 0 | NOT OBSERVED |
| 4 | `not_equals 0`, executed, exit 2 | PROVEN |
| 5 | `equals 1`, not executed | INCONCLUSIVE |
| 6 | `equals 1`, executed, no exit code | INCONCLUSIVE |
| 7 | both `equals` and `not_equals` set | INVALID |
| 8 | neither set | INVALID |
| 9 | both set **and** no exit code | INVALID (validation outranks missing evidence) |

Case 9 is the vacuity guard: a malformed experiment must never be reported as
merely inconclusive, and case 5/6 are the infrastructure guard: missing evidence
must never be reported as a falsification.

An earlier draft of this table expected NOT OBSERVED for `equals 0, exit 0`; that
expectation was wrong, because `equals` fires when the code equals the configured
value. The table was corrected, not the oracle — recorded here because a wrong
expectation is indistinguishable from a wrong implementation until it is checked.

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
