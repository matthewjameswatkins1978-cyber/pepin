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

// One recorded evidence step, addressed the way the reference addresses it: a phase
// name plus a zero-based index within that phase. The phase is a plain `Str` whose
// accepted values are checked by `is_known_phase` rather than a closed union,
// because a recorded step may legitimately carry a phase name this engine does not
// recognise — and that must be judgeable, not unrepresentable.
type EvidenceStep { phase: Str, index: Int, exit: ExitObservation }

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
// Multi-step evidence and step-reference resolution
// ---------------------------------------------------------------------------
//
// Reference contract, The-Terror-Bats @ d5e6404 (src/oracle.rs), `eval_condition`
// for `Condition::ExitCode`, in this exact order:
//   1. `parse_step_ref(step)`  — phase must be setup/run/oracle, index numeric
//   2. `find_step(steps, ...)` — first record with that phase and index
//   3. `record.exit_code`      — a record may exist and still have no exit code
//
// Only steps 2 and 3 are reachable as *evidence* problems. Step 1 is validation:
// measured against the framework, `step: bogus:0`, `step: run0` and `step: run:x`
// all yield verdict INVALID, not INCONCLUSIVE. So a malformed reference is judged
// Invalid alongside the other malformed-spec cases, and the defensive
// "bad step reference" Undetermined branch inside `eval_condition` is unreachable
// through ordinary spec parsing.
//
// The distinction this section adds is not cosmetic. `judge_step` takes a single
// step, so it cannot tell "this step never executed" from "this step ran and
// produced no exit code". Those are different facts about a run, and the reference
// reports them with different notes.

// The three phase names `parse_step_ref` accepts.
fn is_known_phase(phase: Str) -> Bool {
  var known = false
  if phase == "setup" { known = true } else { }
  if phase == "run" { known = true } else { }
  if phase == "oracle" { known = true } else { }
  return known
}

// A step that may or may not have been recorded.
type HeldStep = NoStepHeld() | StepHeld(EvidenceStep)

fn step_absent(held: HeldStep) -> Bool {
  return match held {
    NoStepHeld() => true
    StepHeld(record) => false
  }
}

// `find_step`: recorded steps are searched in order and the first match wins, which
// is the reference's `steps.iter().find(...)`.
fn find_step(steps: List[EvidenceStep], phase: Str, index: Int) -> HeldStep {
  var held = NoStepHeld()
  for step in steps {
    if step_absent(held) && step.phase == phase && step.index == index {
      held = StepHeld(step)
    } else {
    }
  }
  return held
}

// What reading a located step produced. A missing record and a record without an
// exit code stay distinct, because they are distinct evidence about the run.
type StepResolution =
  ResolvedExit(Int) |
  StepNotExecuted(Str) |
  StepHasNoExitCode(Str)

fn resolved_from_step(step: EvidenceStep) -> StepResolution {
  return match step.exit {
    ObservedExit(code) => ResolvedExit(code)
    AbsentExit(why) => StepHasNoExitCode(why)
  }
}

fn resolved_from(held: HeldStep) -> StepResolution {
  return match held {
    NoStepHeld() => StepNotExecuted("step did not execute")
    StepHeld(record) => resolved_from_step(record)
  }
}

// Steps 2 and 3 of the reference's order. Step 1 is judged as validation.
fn resolve_step(steps: List[EvidenceStep], phase: Str, index: Int) -> StepResolution {
  var held = find_step(steps, phase, index)
  if step_absent(held) {
    return StepNotExecuted("step did not execute")
  } else {
  }
  return resolved_from(held)
}

fn judge_resolution(mode: Mode, resolution: StepResolution) -> Verdict {
  if mode_is_valid(mode) {
    return judge_resolved(mode, resolution)
  } else {
    // A malformed mode outranks every evidence problem, exactly as in `judge`. The
    // observation is irrelevant on this path because the mode is rejected first.
    return judge(mode, AbsentExit("mode is malformed; evidence is irrelevant"))
  }
}

// Precondition: `mode` is a valid mode, so this only decides on evidence. The three
// resolutions keep their own reasons instead of collapsing into one generic note:
// "the step did not execute" and "the step produced no exit code" are different
// facts about a run, and a verdict that cannot tell them apart is a weaker verdict.
fn judge_resolved(mode: Mode, resolution: StepResolution) -> Verdict {
  return match resolution {
    ResolvedExit(code) => judge(mode, ObservedExit(code))
    StepNotExecuted(why) => Inconclusive(why)
    StepHasNoExitCode(why) => Inconclusive(why)
  }
}

fn mode_is_valid(mode: Mode) -> Bool {
  return match mode {
    EqualsMode(value) => true
    NotEqualsMode(value) => true
    BothModes(equals_value, not_equals_value) => false
    NoMode(why) => false
  }
}

// The whole `exit_code` condition over a multi-step evidence record: spec validation
// first (a malformed mode or a malformed reference is Invalid and is never rescued by
// missing evidence), then resolution, then the fired/not-fired rule.
fn judge_step_ref(mode: Mode, steps: List[EvidenceStep], phase: Str, index: Int) -> Verdict {
  if is_known_phase(phase) {
    return judge_resolution(mode, resolve_step(steps, phase, index))
  } else {
    return Invalid("bad step reference: unknown phase")
  }
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

// ---------------------------------------------------------------------------
// Recursive oracle expression
// ---------------------------------------------------------------------------
//
// Reference contract, The-Terror-Bats @ d5e6404 (src/oracle.rs):
//   enum OracleExpr { All(Vec<OracleExpr>), Any(Vec<OracleExpr>), Not(Box<OracleExpr>), Cond(Condition) }
//
// `eval` recurses. Two facts follow, and both were measured against the real
// framework before this code was written, because guessing either one produces a
// wrong oracle that still looks plausible:
//
//  1. A combinator combines its DIRECT CHILD RESULTS, not the flattened leaf
//     verdicts. Kleene AND/OR are associative so that difference is invisible for
//     pure nesting, but it is decisive once `not` is nested: `all[not(equals 0),
//     equals 1]` with exit 1 is PROVEN in the reference, while flattening the
//     leaves would compose NotFalsified AND Falsified and answer NOT OBSERVED.
//  2. The trail is depth-first, left to right: leaves only, in the order the
//     recursion reaches them. `not` records the child's leaves unchanged and
//     inverts only the result it returns.

type OracleExpr =
  LeafNode(ConditionOutcome) |
  AllNode(List[OracleExpr]) |
  AnyNode(List[OracleExpr]) |
  NotNode(OracleExpr)

fn concat_outcomes(first: List[ConditionOutcome], second: List[ConditionOutcome]) -> List[ConditionOutcome] {
  var joined = first
  for entry in second {
    joined = append(joined, entry)
  }
  return joined
}

fn evaluate_tree(expr: OracleExpr) -> Evaluation {
  return match expr {
    LeafNode(leaf) => Evaluation { result: leaf.verdict, trail: [leaf] }
    AllNode(children) => evaluate_tree_all(children)
    AnyNode(children) => evaluate_tree_any(children)
    NotNode(child) => evaluate_tree_not(child)
  }
}

// `not` inverts the judgement and leaves the evidence trail exactly as found.
fn evaluate_tree_not(child: OracleExpr) -> Evaluation {
  var judged = evaluate_tree(child)
  return Evaluation { result: compose_not(judged.result), trail: judged.trail }
}

fn evaluate_tree_all(children: List[OracleExpr]) -> Evaluation {
  var results: List[Verdict] = []
  var trail: List[ConditionOutcome] = []
  for child in children {
    var judged = evaluate_tree(child)
    results = append(results, judged.result)
    trail = concat_outcomes(trail, judged.trail)
  }
  var result = compose_all(results)
  if length(children) == 0 {
    trail = [empty_combinator("all: []")]
    result = Inconclusive("empty combinator: nothing to judge")
  } else {
  }
  return Evaluation { result: result, trail: trail }
}

fn evaluate_tree_any(children: List[OracleExpr]) -> Evaluation {
  var results: List[Verdict] = []
  var trail: List[ConditionOutcome] = []
  for child in children {
    var judged = evaluate_tree(child)
    results = append(results, judged.result)
    trail = concat_outcomes(trail, judged.trail)
  }
  var result = compose_any(results)
  if length(children) == 0 {
    trail = [empty_combinator("any: []")]
    result = Inconclusive("empty combinator: nothing to judge")
  } else {
  }
  return Evaluation { result: result, trail: trail }
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
