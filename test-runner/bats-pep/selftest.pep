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
// 10 evidence-record       judge_step over EvidenceStep{exit: ObservedExit(1)}
//                                                                       -> PROVEN
// 11 evidence-record-absent judge_step over EvidenceStep{exit: AbsentExit(...)}
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
show(judge_step(EqualsMode(1), EvidenceStep { index: 0, exit: ObservedExit(1) }))
show(judge_step(EqualsMode(1), EvidenceStep { index: 0, exit: AbsentExit("process killed") }))

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
