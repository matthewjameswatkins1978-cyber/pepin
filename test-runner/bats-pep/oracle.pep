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
// ---------------------------------------------------------------------------
// Condition: evidence_present
// ---------------------------------------------------------------------------
//
// Reference contract, The-Terror-Bats @ d5e6404 (src/oracle.rs):
//
//   Condition::EvidencePresent { kind } =>
//     present = match kind {
//       "git_diff"      => captures.git_diff.is_some(),
//       "git_status"    => captures.git_status.is_some(),
//       "base_snapshot" => captures.base_snapshot.is_some(),
//       other           => Undetermined("unknown evidence kind `{other}`"),
//     }
//     present ? Falsified : NotFalsified
//
// `evidence_present` has no rule in `validate_condition`, so an unknown kind is an
// *evaluation* problem, not a spec problem: measured against the framework,
// `kind: bogus` yields verdict INCONCLUSIVE, not INVALID. That is the opposite of
// the step-reference finding above and the reason each condition is measured rather
// than generalised.
//
// Measured caveat: the runner always captures git state, so `git_diff`,
// `git_status` and `base_snapshot` are present in every ordinary run (verified with
// `capture: []`, which does not disable them). The absence branch below is therefore
// modelled from the source's `is_some()` but is not reachable through an ordinary
// spec run. It is kept because absence is representable in the reference's type, and
// a model that cannot express it would be a weaker model.

// Whether one capture exists in the run's evidence store.
type Capture = CaptureAbsent() | CapturePresent()

type Captures { git_diff: Capture, git_status: Capture, base_snapshot: Capture }

fn capture_present(capture: Capture) -> Bool {
  return match capture {
    CaptureAbsent() => false
    CapturePresent() => true
  }
}

fn presence_verdict(capture: Capture) -> Verdict {
  if capture_present(capture) {
    return Proven("the requested evidence was captured")
  } else {
    return NotObserved("the requested evidence was not captured")
  }
}

// Dispatch is on the kind name, so the verdict depends on that specific capture and
// not on whether any capture at all is present.
fn judge_evidence_present(kind: Str, captures: Captures) -> Verdict {
  var verdict = Inconclusive("unknown evidence kind")
  if kind == "git_diff" {
    verdict = presence_verdict(captures.git_diff)
  } else {
  }
  if kind == "git_status" {
    verdict = presence_verdict(captures.git_status)
  } else {
  }
  if kind == "base_snapshot" {
    verdict = presence_verdict(captures.base_snapshot)
  } else {
  }
  return verdict
}

// Convenience for a run that captured everything, which is what a real run does.
fn all_captures() -> Captures {
  return Captures {
    git_diff: CapturePresent(),
    git_status: CapturePresent(),
    base_snapshot: CapturePresent()
  }
}

fn no_captures() -> Captures {
  return Captures {
    git_diff: CaptureAbsent(),
    git_status: CaptureAbsent(),
    base_snapshot: CaptureAbsent()
  }
}

fn say_trail(evaluation: Evaluation) -> Unit {
  say("RESULT")
  say(verdict_label(evaluation.result))
  for entry in evaluation.trail {
    say("LEAF")
    say(entry.label)
    say(verdict_label(entry.verdict))
  }
}

// ---------------------------------------------------------------------------
// Conditions: file_exists and file_absent
// ---------------------------------------------------------------------------
//
// Reference contract, The-Terror-Bats @ d5e6404 (src/oracle.rs):
//
//   Condition::FileExists { path } => match resolve_in_worktree(ctx.worktree, path) {
//       Ok(p) => if p.exists() { Falsified } else { NotFalsified },
//       Err(e) => (Undetermined, Some(e.to_string())),
//   }
//   Condition::FileAbsent { path } => the inverse polarity, same resolve step.
//
// Three outcomes are reachable, measured against the framework:
//
//   file_exists ".git"              -> PROVEN
//   file_exists "no-such-file.txt"  -> NOT OBSERVED
//   file_absent ".git"              -> NOT OBSERVED
//   file_absent "no-such-file.txt"  -> PROVEN
//   file_exists "../outside.txt"    -> INCONCLUSIVE   (escapes the worktree)
//   file_exists "C:/Windows/..."    -> INCONCLUSIVE   (absolute)
//
// The judgement runs over a RECORDED view of the worktree, not the live filesystem,
// for the same reason the exit-code condition runs over recorded steps: this engine
// judges evidence, it does not perform the run. A driver supplies what it observed —
// which worktree-relative paths were present, and which paths its resolver refused —
// and Pep decides the verdict from those facts alone.
//
// Explicitly not expressible, and therefore not attempted: `resolve_in_worktree`
// normalisation itself (rejecting `..` escapes, absolutising, symlink policy). Pep has
// no string manipulation, so a path is either worktree-relative already or it arrives
// in `rejected_paths` as a host fact.

// What a run recorded about the worktree. `rejected_paths` exists because a path the
// resolver refused is a distinct outcome from a path that was checked and not found —
// the reference reports the former as Undetermined and the latter as NotFalsified, and
// collapsing them would turn a broken experiment into a clean negative result.
type WorktreeView { present_paths: List[Str], rejected_paths: List[Str] }

fn path_rejected(view: WorktreeView, path: Str) -> Bool {
  return contains(view.rejected_paths, path)
}

fn path_present(view: WorktreeView, path: Str) -> Bool {
  return contains(view.present_paths, path)
}

fn judge_file_exists(path: Str, view: WorktreeView) -> Verdict {
  if path_rejected(view, path) {
    return Inconclusive("the path is not representable inside the worktree")
  } else {
  }
  if path_present(view, path) {
    return Proven("the path exists in the worktree")
  } else {
    return NotObserved("the path does not exist in the worktree")
  }
}

fn judge_file_absent(path: Str, view: WorktreeView) -> Verdict {
  if path_rejected(view, path) {
    return Inconclusive("the path is not representable inside the worktree")
  } else {
  }
  if path_present(view, path) {
    return NotObserved("the path exists in the worktree")
  } else {
    return Proven("the path does not exist in the worktree")
  }
}

// ---------------------------------------------------------------------------
// Evidence-driven oracle trees: the four conditions composed together
// ---------------------------------------------------------------------------
//
// Up to here the tree judged leaves that had already been judged. This section judges
// *conditions* against run evidence, so one oracle can mix condition types — which is
// what a real bat does.
//
// Reference contract: `OracleExpr` leaves are `Condition` values and `eval` resolves
// each against `EvalCtx`. Measured example (exit 1, clean clone):
//
//   all: [exit_code run:0 equals 1, evidence_present git_diff,
//         file_exists .git, file_absent no-such-file.txt]
//   -> PROVEN, four leaves, in exactly that order
//
// `EvidenceExpr` is a second tree type rather than a fifth case on `OracleExpr`.
// A leaf here is a condition still to be judged, not a finished judgement, and
// without generics on this base one parameterised tree cannot be both. Keeping them
// apart also keeps `evaluate_tree`'s contract exactly as it was: it never has to
// answer a node it has no evidence for.

// A condition that has not been judged yet.
type Condition =
  ExitCodeCondition(Mode, Str, Int) |
  EvidencePresentCondition(Str) |
  FileExistsCondition(Str) |
  FileAbsentCondition(Str) |
  PathChangedCondition(Str) |
  PathUnchangedCondition(Str) |
  TextContainsCondition(SourceSelector, Str, SourceContent)

// What a run recorded about worktree changes. The reference derives this from
// `git status --porcelain` plus its untracked list, matching a path against the
// column-3 entry, rename targets ("old -> new"), and untracked paths. The status-line
// parsing is string slicing Pep cannot do, so a driver supplies the already-extracted
// path sets and Pep decides the verdict.
type WorktreeChanges { changed_paths: List[Str], untracked_paths: List[Str] }

// A missing `git_status` capture is Undetermined, not a negative result: the
// reference returns "git status capture missing" rather than pretending the path did
// not change.
type ChangeEvidence = ChangeStatusMissing() | ChangeStatusRecorded(WorktreeChanges)

fn path_is_changed(changes: WorktreeChanges, path: Str) -> Bool {
  if contains(changes.changed_paths, path) {
    return true
  } else {
  }
  return contains(changes.untracked_paths, path)
}

fn judge_path_changed(path: Str, evidence: ChangeEvidence) -> Verdict {
  return match evidence {
    ChangeStatusMissing() => Inconclusive("git status capture missing")
    ChangeStatusRecorded(changes) => if path_is_changed(changes, path) {
      Proven("the path changed")
    } else {
      NotObserved("the path did not change")
    }
  }
}

fn judge_path_unchanged(path: Str, evidence: ChangeEvidence) -> Verdict {
  return match evidence {
    ChangeStatusMissing() => Inconclusive("git status capture missing")
    ChangeStatusRecorded(changes) => if path_is_changed(changes, path) {
      NotObserved("the path changed")
    } else {
      Proven("the path did not change")
    }
  }
}

// Everything an evidence-driven tree may read.
type RunEvidence {
  steps: List[EvidenceStep],
  captures: Captures,
  worktree: WorktreeView,
  changes: ChangeEvidence
}
// The condition's own name. The reference's `describe(cond)` also renders the
// arguments ("exit_code run:0 equals 1"), which needs string concatenation Pep does
// not have; a caller that wants that label supplies it to `ConditionLeaf`.
fn condition_name(condition: Condition) -> Str {
  return match condition {
    ExitCodeCondition(mode, phase, index) => "exit_code"
    EvidencePresentCondition(kind) => "evidence_present"
    FileExistsCondition(path) => "file_exists"
    FileAbsentCondition(path) => "file_absent"
    PathChangedCondition(path) => "path_changed"
    PathUnchangedCondition(path) => "path_unchanged"
    TextContainsCondition(selector, needle, availability) => "text_contains"
  }
}

fn evaluate_condition(condition: Condition, evidence: RunEvidence) -> Verdict {
  return match condition {
    ExitCodeCondition(mode, phase, index) =>
      judge_step_ref(mode, evidence.steps, phase, index)
    EvidencePresentCondition(kind) => judge_evidence_present(kind, evidence.captures)
    FileExistsCondition(path) => judge_file_exists(path, evidence.worktree)
    FileAbsentCondition(path) => judge_file_absent(path, evidence.worktree)
    PathChangedCondition(path) => judge_path_changed(path, evidence.changes)
    PathUnchangedCondition(path) => judge_path_unchanged(path, evidence.changes)
    TextContainsCondition(selector, needle, content) =>
      judge_text_contains(selector, needle, content)
  }
}

// An oracle tree whose leaves are conditions rather than finished judgements.
type EvidenceExpr =
  ConditionLeaf(Str, Condition) |
  AllOf(List[EvidenceExpr]) |
  AnyOf(List[EvidenceExpr]) |
  NotOf(EvidenceExpr)

fn judge_leaf(label: Str, condition: Condition, evidence: RunEvidence) -> Evaluation {
  var verdict = evaluate_condition(condition, evidence)
  return Evaluation { result: verdict, trail: [outcome(label, verdict)] }
}

fn evaluate_evidence_tree(expr: EvidenceExpr, evidence: RunEvidence) -> Evaluation {
  return match expr {
    ConditionLeaf(label, condition) => judge_leaf(label, condition, evidence)
    AllOf(children) => evaluate_evidence_all(children, evidence)
    AnyOf(children) => evaluate_evidence_any(children, evidence)
    NotOf(child) => evaluate_evidence_not(child, evidence)
  }
}

fn evaluate_evidence_not(child: EvidenceExpr, evidence: RunEvidence) -> Evaluation {
  var judged = evaluate_evidence_tree(child, evidence)
  return Evaluation { result: compose_not(judged.result), trail: judged.trail }
}

fn evaluate_evidence_all(children: List[EvidenceExpr], evidence: RunEvidence) -> Evaluation {
  var results: List[Verdict] = []
  var trail: List[ConditionOutcome] = []
  for child in children {
    var judged = evaluate_evidence_tree(child, evidence)
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

fn evaluate_evidence_any(children: List[EvidenceExpr], evidence: RunEvidence) -> Evaluation {
  var results: List[Verdict] = []
  var trail: List[ConditionOutcome] = []
  for child in children {
    var judged = evaluate_evidence_tree(child, evidence)
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

// ---------------------------------------------------------------------------
// Source-selector validation: the decidable half of text_contains
// ---------------------------------------------------------------------------
//
// Reference contract, The-Terror-Bats @ d5e6404 (src/oracle.rs):
//
//   DataSourceFlat::resolve()  — exactly one of `path`, `evidence`, or `step`
//                                (+ optional `stream`, allowed only with `step`)
//   validate_source()          — for a step source: parse_step_ref, then require
//                                stream ∈ {stdout, stderr}
//
// `text_contains`, `text_matches` and `json_value_equals` all call `validate_source`
// before reading a single byte, so a malformed source is a *specification* problem
// and is judged here exactly as the reference judges it. Measured against the
// framework:
//
//   path + evidence          -> INVALID
//   path + step              -> INVALID
//   path + stream            -> INVALID
//   no source at all         -> INVALID
//   step + stream: bogus     -> INVALID
//   step + stream: stderr    -> accepted
//   path, readable           -> PROVEN / NOT OBSERVED (the search itself)
//   path, present but unreadable -> INCONCLUSIVE
//
// That last row is the reason this section exists: a *valid* source whose bytes
// cannot be read is Undetermined, not Invalid, so validation and reading are
// genuinely different phases.
//
// The step reference arrives already split into phase and index, because Pep cannot
// slice a string. Everything after the split — phase name, stream name — is judged
// here. The byte search itself is the one branch Pep cannot take yet, and it says so
// rather than guessing.

// A spec field that may be present or absent.
type SourceField = FieldAbsent() | FieldPresent(Str)

// A step source, already split by the driver: phase name plus index.
type StepSource = NoStepSource() | StepAt(Str, Int)

// The flat source selector of a spec.
type SourceSelector {
  path: SourceField,
  evidence: SourceField,
  step: StepSource,
  stream: SourceField
}

type SourceValidation = SourceShapeValid() | SourceRejected(Str)

fn field_present(field: SourceField) -> Bool {
  return match field {
    FieldAbsent() => false
    FieldPresent(value) => true
  }
}

fn has_step_source(step: StepSource) -> Bool {
  return match step {
    NoStepSource() => false
    StepAt(phase, index) => true
  }
}

fn step_phase(step: StepSource) -> Str {
  return match step {
    NoStepSource() => ""
    StepAt(phase, index) => phase
  }
}

fn source_shape_count(selector: SourceSelector) -> Int {
  var count = 0
  if field_present(selector.path) { count = count + 1 } else { }
  if field_present(selector.evidence) { count = count + 1 } else { }
  if has_step_source(selector.step) { count = count + 1 } else { }
  return count
}

fn stream_allowed(selector: SourceSelector) -> Bool {
  return match selector.stream {
    FieldAbsent() => true
    FieldPresent(value) => if value == "stdout" {
      true
    } else {
      value == "stderr"
    }
  }
}

// The reference's order: resolve the shape, then validate the step reference, then the
// stream. A malformed source is Rejected with the reference's own wording.
fn validate_source(selector: SourceSelector) -> SourceValidation {
  if source_shape_count(selector) == 1 {
  } else {
    return SourceRejected("condition source needs exactly one of path, evidence, or step")
  }
  if field_present(selector.stream) {
    if has_step_source(selector.step) {
    } else {
      return SourceRejected("condition source needs exactly one of path, evidence, or step")
    }
  } else {
  }
  if has_step_source(selector.step) {
    if is_known_phase(step_phase(selector.step)) {
    } else {
      return SourceRejected("bad step reference: unknown phase")
    }
    if stream_allowed(selector) {
    } else {
      return SourceRejected("stream must be `stdout` or `stderr`")
    }
  } else {
  }
  return SourceShapeValid()
}

// What Pep can decide about a `text_contains`-shaped condition today. A malformed
// source gets the reference's own INVALID verdict; a well-formed source is honestly
// INCONCLUSIVE, because the byte search needs a primitive Pep does not have. When
// `str_bytes` or `str_contains` lands, only the second branch changes.
fn judge_source_only(selector: SourceSelector) -> Verdict {
  return match validate_source(selector) {
    SourceRejected(reason) => Invalid(reason)
    SourceShapeValid() => Inconclusive("substring search needs str_bytes(Str) -> SourceBytes")
  }
}

// ---------------------------------------------------------------------------
// Condition: text_contains, decided as far as it can be
// ---------------------------------------------------------------------------
//
// Reference contract, The-Terror-Bats @ d5e6404 (src/oracle.rs):
//   eval_condition for TextContains:
//     1. load_source(source)  — a load failure is Undetermined, note carries the error
//     2. contains_substring(bytes, needle) — and an EMPTY needle returns true
//
// Measured, in exactly that order:
//
//   readable path,    needle ""          -> PROVEN       (empty needle always present)
//   readable path,    needle "zzz-..."   -> NOT OBSERVED (the search itself)
//   unreadable path,  needle ""          -> INCONCLUSIVE (load fails BEFORE the test)
//   step source,      needle ""          -> PROVEN
//
// The third row is the ordering that matters. An empty needle does not rescue an
// unloadable source, because the reference loads before it searches — so "always true"
// is a fact about a needle, never a licence to skip a failed load.
//
// With this, text_contains is decided correctly for every input except a non-empty
// needle over a readable source, which is the single branch that needs
// `str_bytes(Str) -> SourceBytes`.

// What a capture actually contains, as the driver recorded it.
//
// This distinction is the point of the type, not a detail. `Condition::TextContains` in
// the reference byte-searches a `&[u8]` haystack with `needle.as_bytes()`, so it answers
// for *any* captured bytes. Pep's `str_contains` takes two `Str` values, so it can only
// search a capture that decoded as UTF-8.
//
// The honest model therefore separates three cases rather than collapsing them:
//   valid UTF-8 text   -> searchable here, and the answer must match the reference
//   present, not UTF-8 -> a real capability boundary: reported Inconclusive, never
//                         decoded lossily, because a lossy decode could turn a genuine
//                         falsification into a miss (or vice versa) and silently invent
//                         a verdict the reference did not reach
//   absent/unreadable  -> Inconclusive, and it outranks the needle (load before search)
type SourceContent =
  SourceContentText(Str) |
  SourceContentNotUtf8(Str) |
  SourceContentUnavailable(Str)

// The reference's order, made explicit: load, then search. An unavailable capture is
// Undetermined even for an empty needle, because the load happens first.
fn judge_source_content(needle: Str, content: SourceContent) -> Verdict {
  return match content {
    SourceContentUnavailable(why) => Inconclusive(why)
    SourceContentNotUtf8(why) => Inconclusive(why)
    SourceContentText(text) => if str_contains(text, needle) {
      Proven("the needle is present in the source text")
    } else {
      NotObserved("the needle is absent from the source text")
    }
  }
}


fn judge_text_contains(
  selector: SourceSelector,
  needle: Str,
  content: SourceContent
) -> Verdict {
  return match validate_source(selector) {
    SourceRejected(reason) => Invalid(reason)
    SourceShapeValid() => judge_source_content(needle, content)
  }
}
