// Self-test for the typed Pep-written exit_code oracle.
//
// Calls run at top level because Pep's interpreter executes top-level statements
// and does not call `fn main` (measured in this lane).
//
// Two verdict labels per case: the label, then the reason the verdict carries, so
// a failure shows *why* as well as what. Order is fixed so the differential script
// can compare positionally.
//
//  1 equals-matches        judge(EqualsMode(1), ObservedExit(1))        -> PROVEN
//  2 equals-no-match       judge(EqualsMode(1), ObservedExit(0))        -> NOT OBSERVED
//  3 not-equals-no-match   judge(NotEqualsMode(0), ObservedExit(0))     -> NOT OBSERVED
//  4 not-equals-matches    judge(NotEqualsMode(0), ObservedExit(2))     -> PROVEN
//  5 equals-other-code     judge(EqualsMode(7), ObservedExit(3))        -> NOT OBSERVED
//  6 both-modes            judge(BothModes(1, 0), ObservedExit(1))      -> INVALID
//  7 no-mode               judge(NoMode("none set"), ObservedExit(1))   -> INVALID
//  8 absent-evidence       judge(EqualsMode(1), AbsentExit("killed"))   -> INCONCLUSIVE
//  9 invalid-beats-absence judge(BothModes(1, 0), AbsentExit("killed")) -> INVALID
// 10 evidence-record       judge_step over EvidenceStep{phase:"run", exit: ObservedExit(1)}
//                                                                       -> PROVEN
// 11 evidence-record-absent judge_step over EvidenceStep{phase:"run", exit: AbsentExit(...)}
//                                                                       -> INCONCLUSIVE
//
// Composition (Rust `OracleExpr::All` / `Any` / `Not`, Kleene three-valued logic):
// 12 all-single-proven      compose_all([Proven])                        -> PROVEN
// 13 all-both-proven        compose_all([Proven, Proven])                -> PROVEN
// 14 all-not-observed-wins  compose_all([Proven, NotObserved])           -> NOT OBSERVED
// 15 all-inconclusive       compose_all([Proven, Inconclusive])          -> INCONCLUSIVE
// 16 all-notobs-beats-unk   compose_all([Inconclusive, NotObserved])     -> NOT OBSERVED
// 17 all-empty              compose_all([])                              -> INCONCLUSIVE
// 18 all-invalid-propagates compose_all([Proven, Invalid(...)])          -> INVALID
// 19 any-proven-wins        compose_any([NotObserved, Proven])           -> PROVEN
// 20 any-none-proven        compose_any([NotObserved, NotObserved])      -> NOT OBSERVED
// 21 any-inconclusive       compose_any([NotObserved, Inconclusive])     -> INCONCLUSIVE
// 22 any-proven-beats-unk   compose_any([Inconclusive, Proven])          -> PROVEN
// 23 any-empty              compose_any([])                              -> INCONCLUSIVE
// 24 any-invalid-propagates compose_any([Proven, Invalid(...)])          -> INVALID
// 25 not-proven             compose_not(Proven)                          -> NOT OBSERVED
// 26 not-not-observed       compose_not(NotObserved)                     -> PROVEN
// 27 not-inconclusive       compose_not(Inconclusive)                    -> INCONCLUSIVE
// 28 not-invalid            compose_not(Invalid)                         -> INVALID
// 29 all-over-real-judgement compose_all([judge(EqualsMode(1), ObservedExit(1)),
//                                          judge(NotEqualsMode(0), ObservedExit(0))])
//                                                                        -> NOT OBSERVED
//
// Case 9 is the vacuity guard: validation outranks missing evidence, so a malformed
// specification is never reported as merely inconclusive. Cases 10-11 exercise the
// record type, i.e. the oracle reading an evidence record.

fn show(verdict: Verdict) -> Unit {
  say(verdict_label(verdict))
  say(verdict_reason(verdict))
}

show(judge(EqualsMode(1), ObservedExit(1)))
show(judge(EqualsMode(1), ObservedExit(0)))
show(judge(NotEqualsMode(0), ObservedExit(0)))
show(judge(NotEqualsMode(0), ObservedExit(2)))
show(judge(EqualsMode(7), ObservedExit(3)))
show(judge(BothModes(1, 0), ObservedExit(1)))
show(judge(NoMode("none set"), ObservedExit(1)))
show(judge(EqualsMode(1), AbsentExit("process killed")))
show(judge(BothModes(1, 0), AbsentExit("process killed")))
show(judge_step(EqualsMode(1), EvidenceStep { phase: "run", index: 0, exit: ObservedExit(1) }))
show(judge_step(EqualsMode(1), EvidenceStep { phase: "run", index: 0, exit: AbsentExit("process killed") }))

// Composition cases. An invalid child keeps its own validation message through the
// composition, so cases 18 and 24 print the child's reason, not a generic one.
show(compose_all([Proven("only condition")]))
show(compose_all([Proven("first"), Proven("second")]))
show(compose_all([Proven("falsified"), NotObserved("not falsified")]))
show(compose_all([Proven("falsified"), Inconclusive("no exit code recorded")]))
show(compose_all([Inconclusive("no exit code recorded"), NotObserved("not falsified")]))
show(compose_all([]))
show(compose_all([Proven("falsified"), Invalid("both equals and not_equals were specified")]))
show(compose_any([NotObserved("not falsified"), Proven("falsified")]))
show(compose_any([NotObserved("first"), NotObserved("second")]))
show(compose_any([NotObserved("not falsified"), Inconclusive("no exit code recorded")]))
show(compose_any([Inconclusive("no exit code recorded"), Proven("falsified")]))
show(compose_any([]))
show(compose_any([Proven("falsified"), Invalid("neither equals nor not_equals was specified")]))
show(compose_not(Proven("falsified")))
show(compose_not(NotObserved("not falsified")))
show(compose_not(Inconclusive("no exit code recorded")))
show(compose_not(Invalid("both equals and not_equals were specified")))

// Composition over the real exit_code engine, not over hand-written verdicts.
show(compose_all([judge(EqualsMode(1), ObservedExit(1)), judge(NotEqualsMode(0), ObservedExit(0))]))

// --- Judgement trail (Rust ConditionOutcome / OracleEvaluation) ---
//
// 30 trail-all-proven      evaluate_all over two Proven leaves       -> PROVEN
// 31 trail-all-mixed       Proven + NotObserved                     -> NOT OBSERVED
// 32 trail-any-proven      NotObserved + Proven                     -> PROVEN
// 33 trail-all-empty       evaluate_all([])                         -> INCONCLUSIVE
// 34 trail-not             evaluate_not(Proven leaf)                -> NOT OBSERVED
// 35 trail-invalid-child   Proven + Invalid child                   -> INVALID//
// Then the trail sizes (2 for a two-leaf evaluation, 1 for the synthetic empty
// combinator outcome) and one full explanation, so the trail itself is visible.
show(result_of(evaluate_all([outcome("exit_code run:0 equals 1", judge(EqualsMode(1), ObservedExit(1))), outcome("exit_code run:0 equals 1 again", judge(EqualsMode(1), ObservedExit(1)))])))
show(result_of(evaluate_all([outcome("exit_code run:0 equals 1", judge(EqualsMode(1), ObservedExit(1))), outcome("exit_code run:0 equals 2", judge(EqualsMode(2), ObservedExit(1)))])))
show(result_of(evaluate_any([outcome("exit_code run:0 equals 2", judge(EqualsMode(2), ObservedExit(1))), outcome("exit_code run:0 equals 1", judge(EqualsMode(1), ObservedExit(1)))])))
show(result_of(evaluate_all([])))
show(result_of(evaluate_not(outcome("exit_code run:0 equals 1", judge(EqualsMode(1), ObservedExit(1))))))
show(result_of(evaluate_all([outcome("exit_code run:0 equals 1", judge(EqualsMode(1), ObservedExit(1))), outcome("exit_code run:0 both modes", judge(BothModes(1, 0), ObservedExit(1)))])))
say(int_text(trail_size(evaluate_all([outcome("a", judge(EqualsMode(1), ObservedExit(1))), outcome("b", judge(EqualsMode(1), ObservedExit(1)))]))))
say(int_text(trail_size(evaluate_all([]))))
explain(evaluate_all([outcome("exit_code run:0 equals 1", judge(EqualsMode(1), ObservedExit(1))), outcome("exit_code run:0 equals 2", judge(EqualsMode(2), ObservedExit(1)))]))

// --- Recursive oracle expression (Rust OracleExpr trees) ---
//
// 36 tree-leaf          evaluate_tree(LeafNode(Proven leaf))    -> PROVEN
// 37 tree-not-in-all    all[not(equals 0), equals 1]            -> PROVEN
// 38 tree-not-of-all    not(all[equals 1, equals 1])            -> NOT OBSERVED
// 39 tree-all-with-any  all[any[equals 0, equals 1], equals 1]  -> PROVEN
// 40 tree-not-in-any    any[not(equals 1), equals 0]            -> NOT OBSERVED
// 41 tree-all-empty     evaluate_tree(AllNode([]))              -> INCONCLUSIVE
//
// Case 37 is the discriminating case: composing the flattened leaf verdicts would
// answer NOT OBSERVED, and the reference answers PROVEN. Nesting must combine
// child results, not leaves.
show(result_of(evaluate_tree(LeafNode(outcome("exit_code run:0 equals 1", judge(EqualsMode(1), ObservedExit(1)))))))
show(result_of(evaluate_tree(AllNode([NotNode(LeafNode(outcome("exit_code run:0 equals 0", judge(EqualsMode(0), ObservedExit(1))))), LeafNode(outcome("exit_code run:0 equals 1", judge(EqualsMode(1), ObservedExit(1))))]))))
show(result_of(evaluate_tree(NotNode(AllNode([LeafNode(outcome("exit_code run:0 equals 1", judge(EqualsMode(1), ObservedExit(1)))), LeafNode(outcome("exit_code run:0 equals 1", judge(EqualsMode(1), ObservedExit(1))))])))))
show(result_of(evaluate_tree(AllNode([AnyNode([LeafNode(outcome("exit_code run:0 equals 0", judge(EqualsMode(0), ObservedExit(1)))), LeafNode(outcome("exit_code run:0 equals 1", judge(EqualsMode(1), ObservedExit(1))))]), LeafNode(outcome("exit_code run:0 equals 1", judge(EqualsMode(1), ObservedExit(1))))]))))
show(result_of(evaluate_tree(AnyNode([NotNode(LeafNode(outcome("exit_code run:0 equals 1", judge(EqualsMode(1), ObservedExit(1))))), LeafNode(outcome("exit_code run:0 equals 0", judge(EqualsMode(0), ObservedExit(1))))]))))
show(result_of(evaluate_tree(AllNode([]))))
say(int_text(trail_size(evaluate_tree(AllNode([AnyNode([LeafNode(outcome("exit_code run:0 equals 0", judge(EqualsMode(0), ObservedExit(1)))), LeafNode(outcome("exit_code run:0 equals 1", judge(EqualsMode(1), ObservedExit(1))))]), LeafNode(outcome("exit_code run:0 equals 1", judge(EqualsMode(1), ObservedExit(1))))])))))

// --- Multi-step evidence and step-reference resolution ---
//
// The reference has three separate reasons a step yields no verdict, and only two of
// them are evidence problems: a malformed reference is validation (INVALID, measured),
// an unrecorded step is Undetermined, and a recorded step without an exit code is
// Undetermined with a different note.
//
// 42 ref-resolved-fires       run:0 exit 1, equals 1              -> PROVEN
// 43 ref-resolved-misses      run:0 exit 1, equals 0              -> NOT OBSERVED
// 44 ref-not-executed         run:9 against [run:0]               -> INCONCLUSIVE
// 45 ref-bad-phase            phase "bogus"                       -> INVALID
// 46 ref-wrong-phase          setup:0 against [run:0]             -> INCONCLUSIVE
// 47 ref-no-exit-code         run:0 present, AbsentExit           -> INCONCLUSIVE
// 48 ref-selects-by-index     [run:0 exit 1, run:1 exit 2], run:1 -> PROVEN
// 49 ref-invalid-beats-missing BothModes with an empty step list  -> INVALID
//
// Case 46 is the phase guard and case 48 the index guard: a resolver that matched on
// index alone, or on presence alone, would answer PROVEN for one of them.
show(judge_step_ref(EqualsMode(1), [EvidenceStep { phase: "run", index: 0, exit: ObservedExit(1) }], "run", 0))
show(judge_step_ref(EqualsMode(0), [EvidenceStep { phase: "run", index: 0, exit: ObservedExit(1) }], "run", 0))
show(judge_step_ref(EqualsMode(1), [EvidenceStep { phase: "run", index: 0, exit: ObservedExit(1) }], "run", 9))
show(judge_step_ref(EqualsMode(1), [EvidenceStep { phase: "run", index: 0, exit: ObservedExit(1) }], "bogus", 0))
show(judge_step_ref(EqualsMode(1), [EvidenceStep { phase: "run", index: 0, exit: ObservedExit(1) }], "setup", 0))
show(judge_step_ref(EqualsMode(1), [EvidenceStep { phase: "run", index: 0, exit: AbsentExit("process killed") }], "run", 0))
show(judge_step_ref(EqualsMode(2), [EvidenceStep { phase: "run", index: 0, exit: ObservedExit(1) }, EvidenceStep { phase: "run", index: 1, exit: ObservedExit(2) }], "run", 1))
show(judge_step_ref(BothModes(1, 0), [], "run", 9))

// --- Condition: evidence_present ---
//
// 50 ev-present-git-diff     git_diff, all captures present   -> PROVEN
// 51 ev-absent-git-diff      git_diff, nothing captured       -> NOT OBSERVED
// 52 ev-present-git-status   git_status, all present          -> PROVEN
// 53 ev-absent-snapshot      base_snapshot, nothing captured  -> NOT OBSERVED
// 54 ev-unknown-kind         kind "bogus"                     -> INCONCLUSIVE
// 55 ev-dispatch-per-kind    git_diff absent, others present   -> NOT OBSERVED
//
// Case 54 is the measured surprise: unlike a malformed step reference, an unknown
// evidence kind has no validate_condition rule, so it is Undetermined at evaluation
// and not INVALID. Case 55 guards the dispatch: an implementation that asked "is any
// capture present" would answer PROVEN there.
show(judge_evidence_present("git_diff", all_captures()))
show(judge_evidence_present("git_diff", no_captures()))
show(judge_evidence_present("git_status", all_captures()))
show(judge_evidence_present("base_snapshot", no_captures()))
show(judge_evidence_present("bogus", all_captures()))
show(judge_evidence_present("git_diff", Captures { git_diff: CaptureAbsent(), git_status: CapturePresent(), base_snapshot: CapturePresent() }))

// --- Conditions: file_exists and file_absent ---
//
// 56 file-exists-present     file_exists ".git"             -> PROVEN
// 57 file-exists-missing     file_exists "no-such-file.txt" -> NOT OBSERVED
// 58 file-absent-present     file_absent ".git"             -> NOT OBSERVED
// 59 file-absent-missing     file_absent "no-such-file.txt" -> PROVEN
// 60 file-exists-rejected    file_exists "../outside.txt"   -> INCONCLUSIVE
// 61 file-absent-rejected    file_absent absolute path      -> INCONCLUSIVE
//
// Cases 60-61 are the infrastructure guard for this condition: a path the resolver
// refused is Undetermined, never a clean negative result. Measured on the framework,
// where both a `..` escape and an absolute path answer INCONCLUSIVE.
fn repo_view() -> WorktreeView {
  return WorktreeView { present_paths: [".git", "README.md"], rejected_paths: ["../outside.txt", "C:/Windows/system.ini"] }
}
show(judge_file_exists(".git", repo_view()))
show(judge_file_exists("no-such-file.txt", repo_view()))
show(judge_file_absent(".git", repo_view()))
show(judge_file_absent("no-such-file.txt", repo_view()))
show(judge_file_exists("../outside.txt", repo_view()))
show(judge_file_absent("C:/Windows/system.ini", repo_view()))

// --- Evidence-driven trees: the four condition types composed ---
//
// 62 evtree-mixed-all       exit + evidence + file_exists + file_absent -> PROVEN
// 63 evtree-mixed-missing   exit fires, file_exists misses             -> NOT OBSERVED
// 64 evtree-any             one missing, one present                   -> PROVEN
// 65 evtree-not             negated file_exists                        -> NOT OBSERVED
// 66 evtree-all-empty       no children                                -> INCONCLUSIVE
// 67 evtree-trail-size      the mixed tree trail                      -> 4
//
// Labels are the reference describe(cond) wording, supplied because Pep has no string
// concatenation; the verdicts are decided in Pep from the evidence record.
fn sample_changes() -> WorktreeChanges {
  return WorktreeChanges { changed_paths: ["tracked.txt"], untracked_paths: ["fresh.txt"] }
}
fn sample_evidence() -> RunEvidence {
  return RunEvidence {
    steps: [EvidenceStep { phase: "run", index: 0, exit: ObservedExit(1) }],
    captures: all_captures(),
    worktree: WorktreeView { present_paths: [".git", "README.md"], rejected_paths: ["../outside.txt"] },
    changes: ChangeStatusRecorded(sample_changes())
  }
}
fn leaf_exit() -> EvidenceExpr {
  return ConditionLeaf("exit_code run:0 equals 1", ExitCodeCondition(EqualsMode(1), "run", 0))
}
fn leaf_evidence() -> EvidenceExpr {
  return ConditionLeaf("evidence_present git_diff", EvidencePresentCondition("git_diff"))
}
fn leaf_exists() -> EvidenceExpr {
  return ConditionLeaf("file_exists .git", FileExistsCondition(".git"))
}
fn leaf_exists_missing() -> EvidenceExpr {
  return ConditionLeaf("file_exists no-such-file.txt", FileExistsCondition("no-such-file.txt"))
}
fn leaf_absent_missing() -> EvidenceExpr {
  return ConditionLeaf("file_absent no-such-file.txt", FileAbsentCondition("no-such-file.txt"))
}
fn mixed_tree() -> EvidenceExpr {
  return AllOf([leaf_exit(), leaf_evidence(), leaf_exists(), leaf_absent_missing()])
}
show(result_of(evaluate_evidence_tree(mixed_tree(), sample_evidence())))
show(result_of(evaluate_evidence_tree(AllOf([leaf_exit(), leaf_exists_missing()]), sample_evidence())))
show(result_of(evaluate_evidence_tree(AnyOf([leaf_exists_missing(), leaf_exists()]), sample_evidence())))
show(result_of(evaluate_evidence_tree(NotOf(leaf_exists()), sample_evidence())))
show(result_of(evaluate_evidence_tree(AllOf([]), sample_evidence())))
say(int_text(trail_size(evaluate_evidence_tree(mixed_tree(), sample_evidence()))))

// --- Conditions: path_changed and path_unchanged ---
//
// 68 path-changed-tracked    path_changed "tracked.txt"   -> PROVEN
// 69 path-changed-untracked  path_changed "fresh.txt"     -> PROVEN
// 70 path-changed-clean      path_changed "nothing.txt"   -> NOT OBSERVED
// 71 path-unchanged-clean    path_unchanged "nothing.txt" -> PROVEN
// 72 path-unchanged-changed  path_unchanged "tracked.txt" -> NOT OBSERVED
// 73 path-missing-status     no git status capture       -> INCONCLUSIVE
//
// Case 69 is the one worth naming: an untracked file counts as changed in the
// reference (it merges the untracked list into the same judgement), so a model that
// only read tracked modifications would answer NOT OBSERVED there.
show(judge_path_changed("tracked.txt", ChangeStatusRecorded(sample_changes())))
show(judge_path_changed("fresh.txt", ChangeStatusRecorded(sample_changes())))
show(judge_path_changed("nothing.txt", ChangeStatusRecorded(sample_changes())))
show(judge_path_unchanged("nothing.txt", ChangeStatusRecorded(sample_changes())))
show(judge_path_unchanged("tracked.txt", ChangeStatusRecorded(sample_changes())))
show(judge_path_changed("anything.txt", ChangeStatusMissing()))

// --- Source-selector validation (the decidable half of text_contains) ---
//
// 74 src-path-only        path, readable file              -> INCONCLUSIVE
// 75 src-step-only        step, default stream             -> INCONCLUSIVE
// 76 src-step-stderr      step + stream stderr             -> INCONCLUSIVE
// 77 src-none             no source at all                 -> INVALID
// 78 src-two-sources      path + evidence                  -> INVALID
// 79 src-stream-no-step   path + stream                    -> INVALID
// 80 src-bad-stream       step + stream "bogus"            -> INVALID
// 81 src-bad-phase        step phase "bogus"               -> INVALID
//
// Cases 74-76 are valid specifications, and Pep answers INCONCLUSIVE for them rather
// than guessing a verdict: the byte search needs str_bytes(Str) -> SourceBytes. Cases
// 77-81 are judged exactly as the reference judges them, because they are
// specification errors and validation needs no string bytes at all.
fn sel_path_only() -> SourceSelector {
  return SourceSelector { path: FieldPresent("README.md"), evidence: FieldAbsent(), step: NoStepSource(), stream: FieldAbsent() }
}
fn sel_step_only() -> SourceSelector {
  return SourceSelector { path: FieldAbsent(), evidence: FieldAbsent(), step: StepAt("run", 0), stream: FieldAbsent() }
}
fn sel_step_stderr() -> SourceSelector {
  return SourceSelector { path: FieldAbsent(), evidence: FieldAbsent(), step: StepAt("run", 0), stream: FieldPresent("stderr") }
}
fn sel_none() -> SourceSelector {
  return SourceSelector { path: FieldAbsent(), evidence: FieldAbsent(), step: NoStepSource(), stream: FieldAbsent() }
}
fn sel_two_sources() -> SourceSelector {
  return SourceSelector { path: FieldPresent("README.md"), evidence: FieldPresent("ev"), step: NoStepSource(), stream: FieldAbsent() }
}
fn sel_stream_no_step() -> SourceSelector {
  return SourceSelector { path: FieldPresent("README.md"), evidence: FieldAbsent(), step: NoStepSource(), stream: FieldPresent("stdout") }
}
fn sel_bad_stream() -> SourceSelector {
  return SourceSelector { path: FieldAbsent(), evidence: FieldAbsent(), step: StepAt("run", 0), stream: FieldPresent("bogus") }
}
fn sel_bad_phase() -> SourceSelector {
  return SourceSelector { path: FieldAbsent(), evidence: FieldAbsent(), step: StepAt("bogus", 0), stream: FieldAbsent() }
}
show(judge_source_only(sel_path_only()))
show(judge_source_only(sel_step_only()))
show(judge_source_only(sel_step_stderr()))
show(judge_source_only(sel_none()))
show(judge_source_only(sel_two_sources()))
show(judge_source_only(sel_stream_no_step()))
show(judge_source_only(sel_bad_stream()))
show(judge_source_only(sel_bad_phase()))

// --- Condition: text_contains, decided as far as it can be ---
//
// 82 tc-empty-needle        readable source, needle ""      -> PROVEN
// 83 tc-nonempty-needle     readable source, needle "ref"   -> INCONCLUSIVE
// 84 tc-empty-unloadable    unloadable source, needle ""    -> INCONCLUSIVE
// 85 tc-step-empty          step source, needle ""          -> PROVEN
// 86 tc-invalid-source      malformed source, needle ""     -> INVALID
// 87 tc-vacuity             malformed source + failed load  -> INVALID
//
// Case 84 is the ordering guard and the reason this is not simply "empty needle always
// wins": the reference loads the source before it tests the needle, so an unloadable
// source is Undetermined even for a needle that matches anything. Case 87 is the
// vacuity guard: a malformed specification outranks both the needle rule and the load
// failure.
show(judge_text_contains(sel_path_only(), "", SourceLoaded()))
show(judge_text_contains(sel_path_only(), "ref", SourceLoaded()))
show(judge_text_contains(sel_path_only(), "", SourceUnavailable("cannot read the source")))
show(judge_text_contains(sel_step_only(), "", SourceLoaded()))
show(judge_text_contains(sel_two_sources(), "", SourceLoaded()))
show(judge_text_contains(sel_none(), "ref", SourceUnavailable("cannot read the source")))
