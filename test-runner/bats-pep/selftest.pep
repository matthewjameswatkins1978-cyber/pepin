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
