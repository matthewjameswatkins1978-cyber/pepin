"""Same-input differential: the Pep-written exit_code oracle vs the Rust runtime.

Both sides judge the *same* inputs:
  (mode=equals|not_equals, configured value, step executed, observed exit code)

The Rust side is the real framework: a Bat whose attack step exits with the chosen
code and whose oracle is `exit_code`. The Pep side is `oracle.pep` executed by
Pep's own interpreter. Verdicts must agree.

Spec-validation cases are compared too: exactly one of `equals`/`not_equals` is
required by the reference, so a spec with both (or neither) must be rejected --
the framework says INVALID at spec-check time, the Pep oracle returns INVALID.

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
    bools = ("true" if use_equals else "false", str(equals_value),
             "true" if use_not_equals else "false", str(not_equals_value),
             "true" if executed else "false", str(exit_code))
    source = ORACLE.read_text(encoding="utf-8") + (
        "\nsay(verdict_label(exit_code_verdict(%s)))\n" % ", ".join(bools))
    composed.write_text(source, encoding="utf-8", newline="\n")
    proc = subprocess.run(["pwsh", "-NoProfile", "-File", str(PEP), "run", str(composed)],
                          text=True, capture_output=True, timeout=600)
    return (proc.stdout or "").strip()


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

    print("SUMMARY cases=%d mismatches=%d" % (len(CASES) + 2, mismatches))
    return 0 if mismatches == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
