// First real Pep-written Terror Bats oracle — the `exit_code` falsification
// condition, judged in ordinary Pep.
//
// Reference contract, read from The-Terror-Bats @ d5e6404 (src/oracle.rs):
//
//   Condition::ExitCode { step, equals?, not_equals? }
//   * validation: exactly one of `equals` / `not_equals`, otherwise the Bat is
//     INVALID ("exit_code requires exactly one of `equals` or `not_equals`")
//   * bad step reference        -> Undetermined
//   * step did not execute      -> Undetermined
//   * step produced no exit code -> Undetermined   (a crash/timeout is never a
//                                                    falsification)
//   * fired = (exit == equals) for `equals`, (exit != not_equals) for `not_equals`
//   * fired ? Falsified : NotFalsified
//
// Verdict codes are Ints so this stays inside currently supported Pep:
//   0 Falsified      -> the claim is refuted (Rust label FALSIFIED / PROVEN)
//   1 NotFalsified   -> this attack did not refute it (NOT OBSERVED; not a
//                       certificate)
//   2 Undetermined   -> evidence unavailable (INCONCLUSIVE)
//   3 Invalid        -> malformed experiment (INVALID)
//
// PEP_NO_EXIT_CODE stands in for "the step produced no exit code", because Pep has
// no option type yet. It is far outside any real exit status range and is checked
// before any comparison, so it can never be mistaken for evidence.

fn pep_no_exit_code() -> Int {
  return -999999999
}

fn verdict_label(code: Int) -> Str {
  if code == 0 { return "PROVEN" } else { }
  if code == 1 { return "NOT OBSERVED" } else { }
  if code == 2 { return "INCONCLUSIVE" } else { }
  if code == 3 { return "INVALID" } else { }
  return "UNKNOWN"
}

// One falsification condition, judged from recorded observations.
//   use_equals/equals_value and use_not_equals/not_equals_value are the two
//   mutually exclusive comparison modes; step_executed says whether the step ran;
//   observed_exit is its exit code, or pep_no_exit_code() when there was none.
fn exit_code_verdict(use_equals: Bool, equals_value: Int,
                     use_not_equals: Bool, not_equals_value: Int,
                     step_executed: Bool, observed_exit: Int) -> Int {
  // Validation precedes observation: a malformed experiment cannot be judged,
  // and must never look like evidence about the claim.
  if use_equals {
    if use_not_equals { return 3 } else { }
  } else {
    if !use_not_equals { return 3 } else { }
  }
  // Missing evidence is undetermined, never a falsification.
  if !step_executed { return 2 } else { }
  if observed_exit == pep_no_exit_code() { return 2 } else { }
  if use_equals {
    if observed_exit == equals_value { return 0 } else { return 1 }
  } else { }
  if observed_exit != not_equals_value { return 0 } else { return 1 }
}
