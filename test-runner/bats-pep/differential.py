"""Same-input differential: the Pep-written exit_code oracle vs the Rust runtime.

Both sides judge the *same* inputs:
  (mode=equals|not_equals, configured value, step executed, observed exit code)

The Rust side is the real framework: a Bat whose attack step exits with the chosen
code and whose oracle is `exit_code`. The Pep side is `oracle.pep` executed by
Pep's own interpreter. Verdicts must agree.

Spec-validation cases are compared too: exactly one of `equals`/`not_equals` is
required by the reference, so a spec with both (or neither) must be rejected --
the framework says INVALID at spec-check time, the Pep oracle returns INVALID.

Condition composition is compared as well: the reference `eval` treats `all`,
`any` and `not` as Kleene three-valued logic, `all: []` / `any: []` as
Undetermined rather than vacuously true, and it validates every node before
evaluating any of them. Those are semantics, not plumbing, so they are measured
against the real framework rather than asserted.

Usage: python differential.py [--repo <clean repo>] [--tb <terrorbats.exe>]
Exit 0 when every case agrees, 1 on any disagreement, 2 if the harness cannot run.
"""
import argparse
import json
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
PEP = REPO / "pep.ps1"
ORACLE = REPO / "test-runner" / "bats-pep" / "oracle.pep"

# (id, use_equals, equals_value, use_not_equals, not_equals_value, executed, exit, expected)
CASES = [
    ("equals-1-exit-1", True, 1, False, 0, True, 1, "PROVEN"),
    ("equals-1-exit-0", True, 1, False, 0, True, 0, "NOT OBSERVED"),
    ("not_equals-0-exit-0", False, 0, True, 0, True, 0, "NOT OBSERVED"),
    ("not_equals-0-exit-2", False, 0, True, 0, True, 2, "PROVEN"),
    ("equals-7-exit-3", True, 7, False, 0, True, 3, "NOT OBSERVED"),
]

# A supervised process killed before it exits produces no exit code. The reference
# must then answer Undetermined for an exit_code condition -- a crash or kill is
# never a falsification -- and the Pep oracle must answer INCONCLUSIVE for the same
# recorded inputs (executed, no exit code).
PROCESS_TEMPLATE = """version: terrorbat/v1
id: pep-diff-process-no-exit-code
claim:
  text: A killed supervised process yields no exit code, so the claim is undetermined.
requires: [process.start, process.kill]
attack:
  run:
    - adapter: process
      action: start
      handle: sleeper
      program: pwsh
      args: ["-NoProfile", "-Command", "Start-Sleep -Seconds 30"]
      stdin: piped
    - adapter: process
      action: kill
      handle: sleeper
      timeout_ms: 5000
oracle:
  all:
    - type: exit_code
      step: run:0
      equals: 1
evidence:
  capture: [stdout, stderr]
timeout:
  run: 120s
  total: 180s
"""

BAT_TEMPLATE = """version: terrorbat/v1
id: pep-diff-{ident}
claim:
  text: Differential probe for the Pep-written exit_code oracle.
requires: [process.spawn]
attack:
  run:
    - adapter: command
      action: run
      program: pwsh
      args: ["-NoProfile", "-Command", "exit {exit_code}"]
oracle:
  all:
    - type: exit_code
      step: run:0
      {mode}: {value}
evidence:
  capture: [stdout, stderr]
timeout:
  run: 60s
  total: 120s
"""

# Composition probes need only a stable attack step; the oracle shape is the
# variable under test. The attack exits 1, so `equals: 1` fires and `equals: 0`
# does not, which makes every Kleene case expressible from two leaf conditions.
SPEC_TEMPLATE = """version: terrorbat/v1
id: {ident}
claim:
  text: Composition differential probe for the Pep-written oracle.
requires: [process.spawn]
attack:
  run:
    - adapter: command
      action: run
      program: pwsh
      args: ["-NoProfile", "-Command", "exit 1"]
oracle:
{oracle_body}
evidence:
  capture: [stdout, stderr]
timeout:
  run: 60s
  total: 120s
"""

# (id, Rust oracle body, equivalent Pep expression, expected verdict)
#
# The Pep expression is evaluated over the SAME leaf judgements the Rust spec
# makes, so a disagreement is a disagreement about composition semantics and not
# about whether the two sides were fed different inputs.
COMPOSITION_CASES = [
    ("comp-all-empty", "  all: []", "compose_all([])", "INCONCLUSIVE"),
    ("comp-any-empty", "  any: []", "compose_any([])", "INCONCLUSIVE"),
    ("comp-all-proven-notobs",
     "  all:\n"
     "    - type: exit_code\n      step: run:0\n      equals: 1\n"
     "    - type: exit_code\n      step: run:0\n      equals: 0",
     "compose_all([judge(EqualsMode(1), ObservedExit(1)),"
     " judge(EqualsMode(0), ObservedExit(1))])",
     "NOT OBSERVED"),
    ("comp-any-notobs-proven",
     "  any:\n"
     "    - type: exit_code\n      step: run:0\n      equals: 0\n"
     "    - type: exit_code\n      step: run:0\n      equals: 1",
     "compose_any([judge(EqualsMode(0), ObservedExit(1)),"
     " judge(EqualsMode(1), ObservedExit(1))])",
     "PROVEN"),
    ("comp-not-proven",
     "  not:\n    type: exit_code\n    step: run:0\n    equals: 1",
     "compose_not(judge(EqualsMode(1), ObservedExit(1)))",
     "NOT OBSERVED"),
    ("comp-not-notobs",
     "  not:\n    type: exit_code\n    step: run:0\n    equals: 0",
     "compose_not(judge(EqualsMode(0), ObservedExit(1)))",
     "PROVEN"),
    # One malformed child invalidates the whole tree: the reference validates
    # every node before evaluating any of them.
    ("comp-all-invalid-child",
     "  all:\n"
     "    - type: exit_code\n      step: run:0\n      equals: 1\n"
     "    - type: exit_code\n      step: run:0\n      equals: 1\n"
     "      not_equals: 0",
     "compose_all([judge(EqualsMode(1), ObservedExit(1)),"
     " judge(BothModes(1, 0), ObservedExit(1))])",
     "INVALID"),
    # An unparseable child is equally fatal, and equally fatal inside `any`.
    ("comp-any-unknown-child",
     "  any:\n"
     "    - type: exit_code\n      step: run:0\n      equals: 1\n"
     "    - type: nonsense_condition\n      thing: x",
     "compose_any([judge(EqualsMode(1), ObservedExit(1)),"
     " judge(BothModes(1, 0), ObservedExit(1))])",
     "INVALID"),
    # A step that never executed is Undetermined and survives composition as
    # Undetermined, never as a falsification.
    ("comp-all-absent-step",
     "  all:\n"
     "    - type: exit_code\n      step: run:0\n      equals: 1\n"
     "    - type: exit_code\n      step: run:9\n      equals: 1",
     "compose_all([judge(EqualsMode(1), ObservedExit(1)),"
     ' judge(EqualsMode(1), AbsentExit("step did not execute"))])',
     "INCONCLUSIVE"),
]
# The reference records one ConditionOutcome per leaf, labelled by `describe(cond)`.
# Those labels are the receipt's judgement trail, so the trail is comparable data
# rather than presentation: the Pep engine must produce the same leaf labels and the
# same per-leaf results, not merely the same composed verdict.
RESULT_LABEL = {
    "Falsified": "PROVEN",
    "NotFalsified": "NOT OBSERVED",
    "Undetermined": "INCONCLUSIVE",
}

# (id, Rust oracle body, equivalent Pep expression over the same labelled leaves)
TRAIL_CASES = [
    ("trail-all-mixed",
     "  all:\n"
     "    - type: exit_code\n      step: run:0\n      equals: 1\n"
     "    - type: exit_code\n      step: run:0\n      equals: 0",
     'evaluate_all([outcome("exit_code run:0 equals 1",'
     ' judge(EqualsMode(1), ObservedExit(1))),'
     ' outcome("exit_code run:0 equals 0",'
     ' judge(EqualsMode(0), ObservedExit(1)))])'),
    ("trail-all-proven",
     "  all:\n"
     "    - type: exit_code\n      step: run:0\n      equals: 1\n"
     "    - type: exit_code\n      step: run:0\n      equals: 1",
     'evaluate_all([outcome("exit_code run:0 equals 1",'
     ' judge(EqualsMode(1), ObservedExit(1))),'
     ' outcome("exit_code run:0 equals 1",'
     ' judge(EqualsMode(1), ObservedExit(1)))])'),
    ("trail-any",
     "  any:\n"
     "    - type: exit_code\n      step: run:0\n      equals: 0\n"
     "    - type: exit_code\n      step: run:0\n      equals: 1",
     'evaluate_any([outcome("exit_code run:0 equals 0",'
     ' judge(EqualsMode(0), ObservedExit(1))),'
     ' outcome("exit_code run:0 equals 1",'
     ' judge(EqualsMode(1), ObservedExit(1)))])'),
    ("trail-not",
     "  not:\n    type: exit_code\n    step: run:0\n    equals: 0",
     'evaluate_not(outcome("exit_code run:0 equals 0",'
     ' judge(EqualsMode(0), ObservedExit(1))))'),
    ("trail-all-empty", "  all: []", "evaluate_all([])"),
    ("trail-all-absent-step",
     "  all:\n"
     "    - type: exit_code\n      step: run:0\n      equals: 1\n"
     "    - type: exit_code\n      step: run:9\n      equals: 1",
     'evaluate_all([outcome("exit_code run:0 equals 1",'
     ' judge(EqualsMode(1), ObservedExit(1))),'
     ' outcome("exit_code run:9 equals 1",'
     ' judge(EqualsMode(1), AbsentExit("step did not execute")))])'),
]

def pep_leaf(equals_value):
    """The Pep expression for one exit_code leaf, labelled as Rust describes it."""
    return ('LeafNode(outcome("exit_code run:0 equals %d", '
            "judge(EqualsMode(%d), ObservedExit(1))))" % (equals_value, equals_value))


# Nested trees, added to the trail comparison rather than given a new harness: leaf
# order, leaf labels and per-leaf results must all match. These are the cases that
# prove the engine combines child RESULTS and not flattened leaf verdicts --
# flattening `all[not(equals 0), equals 1]` would answer NOT OBSERVED, while the
# reference answers PROVEN.
TRAIL_CASES += [
    ("nest-not-in-all",
     "  all:\n"
     "    - not:\n"
     "        type: exit_code\n"
     "        step: run:0\n"
     "        equals: 0\n"
     "    - type: exit_code\n      step: run:0\n      equals: 1",
     "evaluate_tree(AllNode([NotNode(%s), %s]))" % (pep_leaf(0), pep_leaf(1))),
    ("nest-not-of-all",
     "  not:\n"
     "    all:\n"
     "      - type: exit_code\n        step: run:0\n        equals: 1\n"
     "      - type: exit_code\n        step: run:0\n        equals: 1",
     "evaluate_tree(NotNode(AllNode([%s, %s])))" % (pep_leaf(1), pep_leaf(1))),
    ("nest-all-with-any",
     "  all:\n"
     "    - any:\n"
     "        - type: exit_code\n          step: run:0\n          equals: 0\n"
     "        - type: exit_code\n          step: run:0\n          equals: 1\n"
     "    - type: exit_code\n      step: run:0\n      equals: 1",
     "evaluate_tree(AllNode([AnyNode([%s, %s]), %s]))" % (
         pep_leaf(0), pep_leaf(1), pep_leaf(1))),
    ("nest-not-in-any",
     "  any:\n"
     "    - not:\n"
     "        type: exit_code\n"
     "        step: run:0\n"
     "        equals: 1\n"
     "    - type: exit_code\n      step: run:0\n      equals: 0",
     "evaluate_tree(AnyNode([NotNode(%s), %s]))" % (pep_leaf(1), pep_leaf(0))),
]
def step_oracle(step_ref, equals_value=1):
    """An exit_code condition over an arbitrary step reference."""
    return ("  all:\n"
            "    - type: exit_code\n"
            "      step: %s\n"
            "      equals: %d" % (step_ref, equals_value))


# The attack step always exits 1, so `equals: 1` fires on `run:0` and only the step
# reference varies. These are verdict-only comparisons: an INVALID spec is never
# evaluated, so it has no trail to compare.
#
# `step: bogus:0` is the interesting one. It is tempting to model an unknown phase as
# the reference's defensive "bad step reference" Undetermined branch inside
# `eval_condition`, but `validate_condition` calls `parse_step_ref` first, so the
# spec is rejected as INVALID before evaluation. Measured, not assumed.
PEP_RUN0 = 'EvidenceStep { phase: "run", index: 0, exit: ObservedExit(1) }'

STEPREF_CASES = [
    ("stepref-resolves", "run:0", PEP_RUN0, "run", 0, "PROVEN"),
    ("stepref-not-executed", "run:9", PEP_RUN0, "run", 9, "INCONCLUSIVE"),
    ("stepref-wrong-phase", "setup:0", PEP_RUN0, "setup", 0, "INCONCLUSIVE"),
    ("stepref-bad-phase", "bogus:0", PEP_RUN0, "bogus", 0, "INVALID"),
]
# `evidence_present` dispatch. The runner always captures git state, so the three
# known kinds are present in every ordinary run; the measured reachable contrast is
# kind-known (PROVEN) versus kind-unknown (INCONCLUSIVE, not INVALID — this condition
# has no `validate_condition` rule). The absent-capture branch is modelled from the
# source's `is_some()` and is covered by the self-test, not by this differential,
# because no ordinary spec run can produce it.
EVIDENCE_CASES = [
    ("ev-git-diff", "git_diff", "PROVEN"),
    ("ev-git-status", "git_status", "PROVEN"),
    ("ev-base-snapshot", "base_snapshot", "PROVEN"),
    ("ev-unknown-kind", "bogus", "INCONCLUSIVE"),
]
# file_exists / file_absent. The worktree view is supplied as recorded evidence, the
# same way steps are, because this engine judges records rather than touching disk. The
# runner is pointed at a clean clone, so `.git` is present and `no-such-file.txt` is not;
# `../outside.txt` is refused by `resolve_in_worktree` and is Undetermined, which is the
# case that stops a broken path from looking like a clean negative result.
WORKTREE_VIEW = ('WorktreeView { present_paths: [".git", "README.md"], '
                 'rejected_paths: ["../outside.txt", "C:/Windows/system.ini"] }')

FILE_CASES = [
    ("fx-exists", "file_exists", ".git", "PROVEN"),
    ("fx-missing", "file_exists", "no-such-file.txt", "NOT OBSERVED"),
    ("fx-absent-exists", "file_absent", ".git", "NOT OBSERVED"),
    ("fx-absent-missing", "file_absent", "no-such-file.txt", "PROVEN"),
    ("fx-rejected", "file_exists", "../outside.txt", "INCONCLUSIVE"),
]


def rust_verdict(tb, repo, workdir, ident, mode, value, exit_code):
    bat = workdir / ("%s.yaml" % ident)
    bat.write_text(BAT_TEMPLATE.format(ident=ident, mode=mode, value=value,
                                       exit_code=exit_code), encoding="utf-8")
    proc = subprocess.run([str(tb), "run", "--repo", str(repo), str(bat), "--json"],
                          text=True, capture_output=True, timeout=600)
    try:
        doc = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return "HARNESS-ERROR", (proc.stdout or proc.stderr)[:200]
    return doc.get("verdict", "?"), doc.get("receipt_id", "")


def rust_run_verdict(tb, repo, workdir, ident, body):
    """Run a spec and return its verdict.

    Measured: `spec check` accepts a spec with both/neither exit_code modes; the
    reference rejects it at RUN time with verdict INVALID and `status: Invalid`
    ("oracle not evaluated"). So the validation comparison must go through a run,
    not through spec-checking — an earlier version of this driver compared the
    wrong phase and reported a false disagreement.
    """
    bat = workdir / ("%s.yaml" % ident)
    bat.write_text(body, encoding="utf-8")
    proc = subprocess.run([str(tb), "run", "--repo", str(repo), str(bat), "--json"],
                          text=True, capture_output=True, timeout=600)
    try:
        doc = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return "HARNESS-ERROR", (proc.stdout or proc.stderr)[:200]
    return doc.get("verdict", "?"), doc.get("receipt_id", "")


def pep_verdict(composed, use_equals, equals_value, use_not_equals,
                not_equals_value, executed, exit_code):
    """Judge the same inputs with the typed Pep oracle.

    The six scalars are gone: the mode is a tagged union and missing evidence is
    `AbsentExit(...)`. A malformed mode is representable here (`BothModes`/`NoMode`)
    instead of being encoded as two contradictory booleans.
    """
    if use_equals and use_not_equals:
        mode = "BothModes(%d, %d)" % (equals_value, not_equals_value)
    elif use_equals:
        mode = "EqualsMode(%d)" % equals_value
    elif use_not_equals:
        mode = "NotEqualsMode(%d)" % not_equals_value
    else:
        mode = 'NoMode("none set")'
    absent = (not executed) or str(exit_code) == "pep_no_exit_code()"
    observed = ('AbsentExit("no exit code")' if absent
                else "ObservedExit(%d)" % int(exit_code))
    return pep_expression(composed, "judge(%s, %s)" % (mode, observed))


def pep_expression(composed, expr):
    """Run one Pep expression on top of the oracle library and return its label.

    The label comes from the oracle's own `verdict_label`, so the comparison is
    against Pep's judgement and not against a Python re-implementation of it.
    """
    source = ORACLE.read_text(encoding="utf-8") + "\nsay(verdict_label(%s))\n" % expr
    composed.write_text(source, encoding="utf-8", newline="\n")
    proc = subprocess.run(["pwsh", "-NoProfile", "-File", str(PEP), "run", str(composed)],
                          text=True, capture_output=True, timeout=600)
    return (proc.stdout or "").strip()

def pep_trail(composed, expr):
    """Return (result label, [(condition, label), ...]) from the Pep evaluation."""
    source = ORACLE.read_text(encoding="utf-8") + "\nsay_trail(%s)\n" % expr
    composed.write_text(source, encoding="utf-8", newline="\n")
    proc = subprocess.run(["pwsh", "-NoProfile", "-File", str(PEP), "run", str(composed)],
                          text=True, capture_output=True, timeout=600)
    lines = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
    result, trail, i = "?", [], 0
    while i < len(lines):
        if lines[i] == "RESULT":
            result = lines[i + 1]
            i += 2
        elif lines[i] == "LEAF":
            trail.append((lines[i + 1], lines[i + 2]))
            i += 3
        else:
            i += 1
    return result, trail


def rust_trail(tb, repo, workdir, ident, oracle_body):
    """Return (result label, [(condition, label), ...]) from the reference receipt.

    The receipt's `oracle.conditions` is the reference's own judgement trail, so it
    is read as data. An INVALID spec is never evaluated and therefore has no trail.
    """
    body = SPEC_TEMPLATE.format(ident=ident, oracle_body=oracle_body)
    bat = workdir / ("%s.yaml" % ident)
    bat.write_text(body, encoding="utf-8")
    proc = subprocess.run([str(tb), "run", "--repo", str(repo), str(bat), "--json"],
                          text=True, capture_output=True, timeout=600)
    try:
        doc = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return ("HARNESS-ERROR", []), (proc.stdout or proc.stderr)[:200]
    oracle = doc.get("oracle")
    if not oracle:
        return ("NO-TRAIL", []), doc.get("receipt_id", "")
    trail = [(c.get("condition", ""), RESULT_LABEL.get(c.get("result"), "?"))
             for c in oracle.get("conditions", [])]
    return (RESULT_LABEL.get(oracle.get("result"), "?"), trail), doc.get("receipt_id", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=r"D:\Projects\wt-bats-clean")
    ap.add_argument("--tb", default=r"D:\Projects\The-Terror-Bats\target\release\terrorbats.exe")
    args = ap.parse_args()
    tb, repo = pathlib.Path(args.tb), pathlib.Path(args.repo)
    if not tb.is_file():
        print("HARNESS-ERROR framework not found at %s" % tb)
        return 2
    if not (repo / ".git").exists():
        print("HARNESS-ERROR clean repo not found at %s" % repo)
        return 2

    mismatches = 0
    with tempfile.TemporaryDirectory() as tmp:
        workdir = pathlib.Path(tmp)
        composed = workdir / "composed.pep"
        for ident, use_eq, eq, use_ne, ne, executed, code, expected in CASES:
            mode = "equals" if use_eq else "not_equals"
            value = eq if use_eq else ne
            rust, receipt = rust_verdict(tb, repo, workdir, ident, mode, value, code)
            pep = pep_verdict(composed, use_eq, eq, use_ne, ne, executed, code)
            agree = rust == pep == expected
            mismatches += 0 if agree else 1
            print("CASE %-22s rust=%-13s pep=%-13s expected=%-13s %s" % (
                ident, rust, pep, expected, "AGREE" if agree else "DISAGREE"))
            if receipt:
                print("     rust_receipt=%s" % receipt)

        # Spec-validation equivalence: both / neither modes must be rejected.
        invalid_specs = {
            "spec-both": BAT_TEMPLATE.format(ident="spec-both", mode="equals", value=1,
                                             exit_code=1).replace(
                "      equals: 1\n", "      equals: 1\n      not_equals: 0\n"),
            "spec-neither": BAT_TEMPLATE.format(ident="spec-neither", mode="equals",
                                                value=1, exit_code=1).replace(
                "      equals: 1\n", ""),
        }
        for ident, body in invalid_specs.items():
            rust, receipt = rust_run_verdict(tb, repo, workdir, ident, body)
            pep = pep_verdict(composed, ident == "spec-both", 1,
                              True, 0, True, 1) if ident == "spec-both" else \
                pep_verdict(composed, False, 0, False, 0, True, 1)
            agree = rust == "INVALID" and pep == "INVALID"
            mismatches += 0 if agree else 1
            print("CASE %-22s rust=%-13s pep=%-13s expected=%-13s %s" % (
                ident, rust, pep, "INVALID", "AGREE" if agree else "DISAGREE"))
            if receipt:
                print("     rust_receipt=%s" % receipt)

        # No-exit-code path: the step is killed before it exits, so it has no exit
        # code. Both sides must answer "undetermined", never a falsification.
        rust, receipt = rust_run_verdict(tb, repo, workdir,
                                         "process-no-exit-code", PROCESS_TEMPLATE)
        pep = pep_verdict(composed, True, 1, False, 0, True, "pep_no_exit_code()")
        agree = rust == pep == "INCONCLUSIVE"
        mismatches += 0 if agree else 1
        print("CASE %-22s rust=%-13s pep=%-13s expected=%-13s %s" % (
            "process-no-exit-code", rust, pep, "INCONCLUSIVE",
            "AGREE" if agree else "DISAGREE"))
        if receipt:
            print("     rust_receipt=%s" % receipt)

        # Composition differential: all / any / not, empty combinators, and the
        # validate-before-evaluate rule that makes one malformed child fatal.
        for ident, oracle_body, pep_expr, expected in COMPOSITION_CASES:
            body = SPEC_TEMPLATE.format(ident=ident, oracle_body=oracle_body)
            rust, receipt = rust_run_verdict(tb, repo, workdir, ident, body)
            pep = pep_expression(composed, pep_expr)
            agree = rust == pep == expected
            mismatches += 0 if agree else 1
            print("CASE %-22s rust=%-13s pep=%-13s expected=%-13s %s" % (
                ident, rust, pep, expected, "AGREE" if agree else "DISAGREE"))
            if receipt:
                print("     rust_receipt=%s" % receipt)

        # Judgement-trail differential: the receipt's per-leaf conditions are the
        # reference's own trail, so both sides must report the same leaf labels, the
        # same per-leaf results, and the same composed result.
        for ident, oracle_body, pep_expr in TRAIL_CASES:
            (rust_result, rust_rows), receipt = rust_trail(
                tb, repo, workdir, ident, oracle_body)
            pep_result, pep_rows = pep_trail(composed, pep_expr)
            agree = rust_result == pep_result and rust_rows == pep_rows
            mismatches += 0 if agree else 1
            print("CASE %-22s rust=%-13s pep=%-13s leaves=%d %s" % (
                ident, rust_result, pep_result, len(rust_rows),
                "AGREE" if agree else "DISAGREE"))
            if not agree:
                print("     rust_leaves=%r" % (rust_rows,))
                print("     pep_leaves =%r" % (pep_rows,))
            if receipt:
                print("     rust_receipt=%s" % receipt)

        # Step-reference differential: the three distinct ways a step yields no
        # verdict, plus the one way it yields evidence.
        for ident, step_ref, steps_expr, phase, index, expected in STEPREF_CASES:
            body = SPEC_TEMPLATE.format(ident=ident,
                                       oracle_body=step_oracle(step_ref))
            rust, receipt = rust_run_verdict(tb, repo, workdir, ident, body)
            pep = pep_expression(composed, 'judge_step_ref(EqualsMode(1), [%s], "%s", %d)'
                                 % (steps_expr, phase, index))
            agree = rust == pep == expected
            mismatches += 0 if agree else 1
            print("CASE %-22s rust=%-13s pep=%-13s expected=%-13s %s" % (
                ident, rust, pep, expected, "AGREE" if agree else "DISAGREE"))
            if receipt:
                print("     rust_receipt=%s" % receipt)

        # evidence_present differential.
        for ident, kind, expected in EVIDENCE_CASES:
            body = SPEC_TEMPLATE.format(
                ident=ident,
                oracle_body="  all:\n"
                            "    - type: evidence_present\n"
                            "      kind: %s" % kind)
            rust, receipt = rust_run_verdict(tb, repo, workdir, ident, body)
            pep = pep_expression(
                composed, 'judge_evidence_present("%s", all_captures())' % kind)
            agree = rust == pep == expected
            mismatches += 0 if agree else 1
            print("CASE %-22s rust=%-13s pep=%-13s expected=%-13s %s" % (
                ident, rust, pep, expected, "AGREE" if agree else "DISAGREE"))
            if receipt:
                print("     rust_receipt=%s" % receipt)

        # file_exists / file_absent differential.
        for ident, kind, path, expected in FILE_CASES:
            body = SPEC_TEMPLATE.format(
                ident=ident,
                oracle_body="  all:\n"
                            "    - type: %s\n"
                            "      path: \"%s\"" % (kind, path))
            rust, receipt = rust_run_verdict(tb, repo, workdir, ident, body)
            pep = pep_expression(
                composed, 'judge_%s("%s", %s)' % (kind, path, WORKTREE_VIEW))
            agree = rust == pep == expected
            mismatches += 0 if agree else 1
            print("CASE %-22s rust=%-13s pep=%-13s expected=%-13s %s" % (
                ident, rust, pep, expected, "AGREE" if agree else "DISAGREE"))
            if receipt:
                print("     rust_receipt=%s" % receipt)

    total = (len(CASES) + 3 + len(COMPOSITION_CASES) + len(TRAIL_CASES)
             + len(STEPREF_CASES) + len(EVIDENCE_CASES) + len(FILE_CASES))
    print("SUMMARY cases=%d mismatches=%d" % (total, mismatches))
    return 0 if mismatches == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
