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

// ---------------------------------------------------------------------------
// Condition composition
// ---------------------------------------------------------------------------
//
// Reference contract, read from The-Terror-Bats @ d5e6404 (src/oracle.rs),
// `eval` over OracleResult (Falsified | NotFalsified | Undetermined):
//   * `all: []` and `any: []` are Undetermined ("empty combinator: nothing to
//     judge"). An empty conjunction is NOT vacuously true here.
//   * `all` is Kleene AND: NotFalsified wins, then Undetermined, then Falsified.
//   * `any` is Kleene OR: Falsified wins, then Undetermined, then NotFalsified.
//   * `not` swaps Falsified/NotFalsified and leaves Undetermined alone.
//   * `parse` validates every node before `evaluate` runs, so one malformed
//     sub-condition makes the whole spec invalid and nothing is evaluated.
//     Composition therefore propagates Invalid and never composes it into a
//     judgement. A malformed experiment stays malformed inside an `all`.

// A found reason, so "absent" is a case instead of an empty-string sentinel.
type Found = NotFound() | FoundReason(Str)

fn found_absent(found: Found) -> Bool {
  return match found {
    NotFound() => true
    FoundReason(why) => false
  }
}

fn found_present(found: Found) -> Bool {
  return match found {
    NotFound() => false
    FoundReason(why) => true
  }
}

fn found_reason(found: Found) -> Str {
  return match found {
    NotFound() => "none"
    FoundReason(why) => why
  }
}

// Decision rank inside one combinator, lowest first. `all` resolves by
// 0 = Invalid, 1 = NotObserved, 2 = Inconclusive, 3 = Proven. `any` resolves by
// 0 = Invalid, 3 = Proven, 2 = Inconclusive, 1 = NotObserved. The ranks are one
// shared encoding; each composer queries only the ranks it must distinguish.
fn rank(verdict: Verdict) -> Int {
  return match verdict {
    Invalid(why) => 0
    NotObserved(why) => 1
    Inconclusive(why) => 2
    Proven(why) => 3
  }
}

// The first verdict carrying `wanted` rank, so a composed verdict can quote the
// reason of the child that actually decided it. First-wins keeps the result
// deterministic and order-describing rather than order-inventing.
fn first_of_rank(verdicts: List[Verdict], wanted: Int) -> Found {
  var found = NotFound()
  for verdict in verdicts {
    if found_absent(found) && rank(verdict) == wanted {
      found = FoundReason(verdict_reason(verdict))
    } else {
    }
  }
  return found
}

// Kleene AND. Assignment order is priority order: least decisive first, so the
// most decisive finding is the one that survives.
fn compose_all(verdicts: List[Verdict]) -> Verdict {
  var verdict = Proven("every condition was falsified")
  if length(verdicts) == 0 {
    verdict = Inconclusive("empty combinator: nothing to judge")
  } else {
  }
  if found_present(first_of_rank(verdicts, 2)) {
    verdict = Inconclusive("at least one condition was undetermined")
  } else {
  }
  if found_present(first_of_rank(verdicts, 1)) {
    verdict = NotObserved("at least one condition was not falsified")
  } else {
  }
  if found_present(first_of_rank(verdicts, 0)) {
    verdict = Invalid(found_reason(first_of_rank(verdicts, 0)))
  } else {
  }
  return verdict
}

// Kleene OR, same construction with the OR precedence.
fn compose_any(verdicts: List[Verdict]) -> Verdict {
  var verdict = NotObserved("no condition was falsified")
  if length(verdicts) == 0 {
    verdict = Inconclusive("empty combinator: nothing to judge")
  } else {
  }
  if found_present(first_of_rank(verdicts, 2)) {
    verdict = Inconclusive("no condition was falsified and at least one was undetermined")
  } else {
  }
  if found_present(first_of_rank(verdicts, 3)) {
    verdict = Proven("at least one condition was falsified")
  } else {
  }
  if found_present(first_of_rank(verdicts, 0)) {
    verdict = Invalid(found_reason(first_of_rank(verdicts, 0)))
  } else {
  }
  return verdict
}

// Negation: only a judgement flips. Missing evidence stays missing, and a
// malformed sub-spec stays malformed — negation is not a way to rescue either.
fn compose_not(verdict: Verdict) -> Verdict {
  return match verdict {
    Proven(why) => NotObserved("the negated condition was falsified")
    NotObserved(why) => Proven("the negated condition was not falsified")
    Inconclusive(why) => Inconclusive(why)
    Invalid(why) => Invalid(why)
  }
}

// ---------------------------------------------------------------------------
// Judgement trail
// ---------------------------------------------------------------------------
//
// Reference contract, The-Terror-Bats @ d5e6404 (src/oracle.rs):
//   struct ConditionOutcome { condition: String, result: OracleResult, note: Option<String> }
//   struct OracleEvaluation { result: OracleResult, conditions: Vec<ConditionOutcome> }
//
// `eval` records one outcome per LEAF it actually evaluated. A combinator does not
// record itself, with one exception: an empty `all`/`any` records a synthetic
// outcome ("all: []", Undetermined, "empty combinator: nothing to judge"), because
// otherwise no leaf exists to explain the verdict. This mirrors that exactly, so a
// result can show its own reasoning instead of only asserting a label.

// One judged leaf: what was looked at, and what that leaf said.
type ConditionOutcome { label: Str, verdict: Verdict }

// A composed result together with the trail that produced it.
type Evaluation { result: Verdict, trail: List[ConditionOutcome] }

fn outcome(label: Str, verdict: Verdict) -> ConditionOutcome {
  return ConditionOutcome { label: label, verdict: verdict }
}

// The leaf verdicts of a trail, in order, so composition reads exactly the
// evidence the trail reports rather than a parallel copy of it.
fn verdicts_of(trail: List[ConditionOutcome]) -> List[Verdict] {
  var verdicts: List[Verdict] = []
  for entry in trail {
    verdicts = append(verdicts, entry.verdict)
  }
  return verdicts
}

// The reference's synthetic outcome for a combinator with no children.
fn empty_combinator(label: Str) -> ConditionOutcome {
  return outcome(label, Inconclusive("empty combinator: nothing to judge"))
}

fn evaluate_all(trail: List[ConditionOutcome]) -> Evaluation {
  var recorded = trail
  var result = compose_all(verdicts_of(trail))
  if length(trail) == 0 {
    recorded = [empty_combinator("all: []")]
    result = Inconclusive("empty combinator: nothing to judge")
  } else {
  }
  return Evaluation { result: result, trail: recorded }
}

fn evaluate_any(trail: List[ConditionOutcome]) -> Evaluation {
  var recorded = trail
  var result = compose_any(verdicts_of(trail))
  if length(trail) == 0 {
    recorded = [empty_combinator("any: []")]
    result = Inconclusive("empty combinator: nothing to judge")
  } else {
  }
  return Evaluation { result: result, trail: recorded }
}

// `not` negates a judgement. The leaf it negates is still the recorded evidence,
// so the trail keeps the leaf's own verdict and only the composed result inverts —
// the same split the reference makes between what was seen and what was concluded.
fn evaluate_not(negated: ConditionOutcome) -> Evaluation {
  return Evaluation { result: compose_not(negated.verdict), trail: [negated] }
}

fn result_of(evaluation: Evaluation) -> Verdict {
  return evaluation.result
}

fn trail_size(evaluation: Evaluation) -> Int {
  return length(evaluation.trail)
}

// Human-readable explanation: the composed verdict, then every leaf in order.
fn explain(evaluation: Evaluation) -> Unit {
  say(verdict_label(evaluation.result))
  say(verdict_reason(evaluation.result))
  for entry in evaluation.trail {
    say(entry.label)
    say(verdict_label(entry.verdict))
    say(verdict_reason(entry.verdict))
  }
}

// Machine-readable trail, one record per line so a differential can consume it
// positionally without string formatting (Pep has no Str concatenation).
//
//   RESULT <verdict label>
//   LEAF <condition label> <verdict label>   (repeated, in order)
//
// The labels use the reference's own `describe(cond)` wording, so a Pep trail and
// a Rust receipt trail are directly comparable rather than merely similar.
fn say_trail(evaluation: Evaluation) -> Unit {
  say("RESULT")
  say(verdict_label(evaluation.result))
  for entry in evaluation.trail {
    say("LEAF")
    say(entry.label)
    say(verdict_label(entry.verdict))
  }
}
