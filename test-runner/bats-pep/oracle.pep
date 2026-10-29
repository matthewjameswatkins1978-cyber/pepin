// Pep-written Terror Bats oracle — typed observations, reasons and verdicts.
//
// Second slice: the six scalar parameters are gone. A parsed comparison mode is a
// tagged union (a malformed mode is an explicit case, not two Bools that can
// contradict), missing evidence is `AbsentExit(reason)` rather than a sentinel
// integer, and the verdict is a union carrying a short reason instead of an Int code.
//
// Reference contract, read from The-Terror-Bats @ d5e6404 (src/oracle.rs):
//   Condition::ExitCode { step, equals?, not_equals? }
//   * exactly one of `equals` / `not_equals`, else the spec is INVALID
//   * bad step reference / step did not execute / no exit code -> Undetermined
//     (a crash or kill is never a falsification)
//   * fired = (code == equals) or (code != not_equals)
//   * fired ? Falsified : NotFalsified
// Labels: Falsified -> PROVEN, NotFalsified -> NOT OBSERVED (never a certificate),
//         Undetermined -> INCONCLUSIVE, malformed spec -> INVALID.
//
// Grammar and checker rules measured on this base, each reported to Agent 1 with a
// minimal case because every one of them cost real time to discover:
//   1. A nullary constructor is DECLARED with empty parentheses — `NoMode()` — but
//      `type T = A(Int) | B` is rejected outright (PEP_PARSE_EXPECTED "Expected '('").
//   2. A BARE nullary pattern is treated as a binding, i.e. irrefutable: a match on
//      `Proven` followed by `NotObserved` is rejected with PEP_UNREACHABLE_MATCH_ARM
//      ("Match arm follows an irrefutable pattern"). So nullary constructors cannot
//      be distinguished in a match at all — which is why every alternative here
//      carries a payload and every arm is a refutable constructor pattern.
//   3. Match arms are newline-separated; two arms on one line parse as one.
//   4. A match arm body is an expression, not a block: `AbsentExit(why) => X`, never
//      `AbsentExit(why) => { return X }`.

// A comparison mode as it comes out of a spec. `BothModes`/`NoMode` stay
// representable so a malformed spec is judged Invalid instead of being coerced into
// one of the valid modes. `NoMode` carries a reason because a payload keeps the
// pattern refutable (rule 2).
type Mode = EqualsMode(Int) | NotEqualsMode(Int) | BothModes(Int, Int) | NoMode(Str)

// What was recorded for a step. `AbsentExit(reason)` means the step produced no exit
// code — unexecuted, killed, or timed out. That is evidence of absence, and the
// reason says which, but it is never evidence about the claim.
type ExitObservation = ObservedExit(Int) | AbsentExit(Str)

// One recorded evidence step, so the oracle reads an evidence record rather than a
// loose argument list.
type EvidenceStep { index: Int, exit: ExitObservation }

type Verdict = Proven(Str) | NotObserved(Str) | Inconclusive(Str) | Invalid(Str)

fn verdict_label(verdict: Verdict) -> Str {
  return match verdict {
    Proven(why) => "PROVEN"
    NotObserved(why) => "NOT OBSERVED"
    Inconclusive(why) => "INCONCLUSIVE"
    Invalid(why) => "INVALID"
  }
}

// The reason a verdict carries, so a result can explain itself without string
// concatenation (Pep has none yet — a documented dependency).
fn verdict_reason(verdict: Verdict) -> Str {
  return match verdict {
    Proven(why) => why
    NotObserved(why) => why
    Inconclusive(why) => why
    Invalid(why) => why
  }
}

// Missing evidence is undetermined before any comparison happens.
fn judge_equals(expected: Int, observed: ExitObservation) -> Verdict {
  return match observed {
    AbsentExit(why) => Inconclusive("no exit code recorded")
    ObservedExit(code) => if code == expected {
      Proven("exit code equals the configured value")
    } else {
      NotObserved("exit code differs from the configured value")
    }
  }
}

fn judge_not_equals(unexpected: Int, observed: ExitObservation) -> Verdict {
  return match observed {
    AbsentExit(why) => Inconclusive("no exit code recorded")
    ObservedExit(code) => if code != unexpected {
      Proven("exit code differs from the excluded value")
    } else {
      NotObserved("exit code equals the excluded value")
    }
  }
}

// Validation precedes observation: a malformed mode can never be judged as evidence
// about the claim, even when the observation itself is missing.
fn judge(mode: Mode, observed: ExitObservation) -> Verdict {
  return match mode {
    BothModes(equals_value, not_equals_value) =>
      Invalid("both equals and not_equals were specified")
    NoMode(why) => Invalid("neither equals nor not_equals was specified")
    EqualsMode(value) => judge_equals(value, observed)
    NotEqualsMode(value) => judge_not_equals(value, observed)
  }
}

// The same judgement over a recorded evidence step.
fn judge_step(mode: Mode, step: EvidenceStep) -> Verdict {
  return judge(mode, step.exit)
}
