// Self-test for the Pep-written exit_code oracle.
//
// Calls run at top level because Pep's interpreter executes top-level statements
// and does not call `fn main` (measured earlier in this lane).
//
// One verdict label per line, in this fixed order, so the output is a positional
// vector a differential script can compare against the Rust reference (Pep has no
// string concatenation yet, so cases are identified by position and this table):
//
//   1 proven                  equals 1,     executed, exit 1        -> PROVEN
//   2 not-observed            equals 1,     executed, exit 0        -> NOT OBSERVED
//   3 not-observed-ne         not_equals 0, executed, exit 0        -> NOT OBSERVED
//   4 proven-ne               not_equals 0, executed, exit 2        -> PROVEN
//   5 inconclusive-noexec     equals 1,     NOT executed            -> INCONCLUSIVE
//   6 inconclusive-nocode     equals 1,     executed, no exit code  -> INCONCLUSIVE
//   7 invalid-both            both modes set                        -> INVALID
//   8 invalid-neither         neither mode set                      -> INVALID
//   9 invalid-beats-evidence  both modes set AND no exit code       -> INVALID
//
// Case 9 is the vacuity guard: validation must outrank missing evidence, so a
// malformed experiment can never be reported as merely inconclusive.

// Case 2 note: an earlier draft used `equals 0, exit 0` and expected NOT OBSERVED.
// That expectation was wrong — `equals` fires when the code equals the configured
// value, so 0 == 0 is a genuine falsification and PROVEN is correct there. The
// table was fixed, not the oracle.
say(verdict_label(exit_code_verdict(true, 1, false, 0, true, 1)))
say(verdict_label(exit_code_verdict(true, 1, false, 0, true, 0)))
say(verdict_label(exit_code_verdict(false, 0, true, 0, true, 0)))
say(verdict_label(exit_code_verdict(false, 0, true, 0, true, 2)))
say(verdict_label(exit_code_verdict(true, 1, false, 0, false, 1)))
say(verdict_label(exit_code_verdict(true, 1, false, 0, true, pep_no_exit_code())))
say(verdict_label(exit_code_verdict(true, 1, true, 0, true, 1)))
say(verdict_label(exit_code_verdict(false, 0, false, 0, true, 1)))
say(verdict_label(exit_code_verdict(true, 1, true, 0, true, pep_no_exit_code())))
