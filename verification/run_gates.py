#!/usr/bin/env python3
"""Run every A3 verification gate in one command (verification/probes).

The lane grew to eight separate probes, each with its own environment variable and
its own idea of "pass". That is ritual cost: anyone re-verifying has to remember
eight invocations, and a lane nobody re-runs is a lane that rots. This runs them all
and prints one table.

Every gate here is independently reproducible. None of them is the author's own
test: A4's oracle, A1's oracle and A1's merge are verified against live behaviour,
not against the author's assertions.

  python verification/run_gates.py                      # use $PEPIN_SEED_ROOT
  python verification/run_gates.py --seed D:/Projects/wt-a3-dbea
  python verification/run_gates.py --skip-merge --skip-divergence

Gates that need a peer worktree (A1's merge, A2's DIVERGENCE-2) report SKIP with the
variable to set, never a silent pass. Exit 0 only if every runnable gate passed.
"""
import argparse
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
PROBES = HERE / "probes"

# (label, script, extra args, env overrides, needs)
GATES = [
    ("A4 oracle replay (13 pins)",      "pep0_oracle_079.py",   [], {"PEPIN_SEED_ROOT": "seed"}, ("seed",)),
    ("A4 normative boundary (17)",       "pep0_boundary_088.py", [], {"PEPIN_SEED_ROOT": "seed"}, ("seed",)),
    ("A1 semantic oracle (23)",          "pep0_a1_oracle_093.py", [], {"PEPIN_SEED_ROOT": "seed"}, ("seed",)),
    ("A1 sectional merge (11 probes)",   "sectional_negatives_080.py", [], {"PEPIN_SECTIONAL_ROOT": "a1"}, ("a1",)),
    ("A2 DIVERGENCE-2 (16)",             "divergence_2_042.py",  [], {"PEPIN_GATE_ROOT": "a2"}, ("a2",)),
    ("M-1 gate calibration",             "verify_m1_081.py",     ["--selftest"], {}, ()),
    # Differential against an independent implementation: the seed's own evaluator.
    # Needs both a seed (to evaluate) and a gate (whose emitter lowers the C).
    ("Seed vs emitted differential (4)",  "seed_differential_106.py", [], {"PEPIN_SEED_ROOT": "seed",
                                                                    "PEPIN_GATE_ROOT": "a2"}, ("seed", "a2")),
]

# NOT in this list, by design: the A2 prepend+reverse differential. It compares emitted
# C bytes across TWO different pins (1885566 and bea071a), so it needs two A2 worktrees
# and a driver that diffs them; it cannot report pass/fail from one invocation. Run it
# explicitly (BOOT-A3-078):
#   PEPIN_GATE_ROOT=<pin1885566> PEPIN_APP_REL=<fixture> PEPIN_APP_REV=<sha> \
#     PEPIN_C_OUT=base.c python verification/probes/emit_any_049.py
#   ... repeat against <bea071a>, then compare base.c to tip.c with Get-FileHash.
# A 21-function emission table uses the same instrument with PEPIN_UNITS_ONLY=1.


def run(script, args, env, cwd):
    path = PROBES / script
    if not path.is_file():
        return None, f"missing {script}"
    full = dict(os.environ)
    full.update(env)
    for key in ("PEPIN_SEED_ROOT", "PEPIN_SECTIONAL_ROOT", "PEPIN_GATE_ROOT",
                "PEPIN_APP_REL", "PEPIN_APP_REV", "PEPIN_UNITS_ONLY", "PEPIN_C_OUT"):
        if key not in env:
            full.pop(key, None)
    proc = subprocess.run([sys.executable, str(path)] + args, cwd=str(cwd),
                          capture_output=True, text=True, check=False, env=full)
    lines = [line for line in (proc.stdout or "").strip().splitlines() if line.strip()]
    # Summary, not the last line: DIVERGENCE-2 prints the generated C after its
    # verdict, so "last line" reports a fragment of C instead of the result.
    markers = ("checks,", "REPRODUCES", "ORACLE REPLAY", "BOUNDARY EVIDENCE",
               "SELF-TEST", "probes,", "DIFFERENTIAL", "PARTIAL RESULT", "RESULT:")
    summary = next((line for line in reversed(lines)
                    if any(mark in line for mark in markers)), None)
    detail = summary or (lines[-1] if lines else (proc.stderr or "").strip()[:80])
    return proc.returncode, detail


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default=os.environ.get("PEPIN_SEED_ROOT", ""))
    parser.add_argument("--a1", default=os.environ.get("PEPIN_A1_ROOT", ""))
    parser.add_argument("--a2", default=os.environ.get("PEPIN_A2_ROOT", ""))
    parser.add_argument("--skip-merge", action="store_true")
    parser.add_argument("--skip-divergence", action="store_true")
    args = parser.parse_args()

    roots = {"seed": args.seed, "a1": args.a1, "a2": args.a2}
    rows, failed, skipped = [], 0, 0

    for label, script, extra, envmap, needs in GATES:
        if script == "divergence_2_042.py" and args.skip_divergence:
            rows.append((label, "SKIP", "--skip-divergence")); skipped += 1; continue
        if script == "sectional_negatives_080.py" and args.skip_merge:
            rows.append((label, "SKIP", "--skip-merge")); skipped += 1; continue
        if script == "emit_any_049.py":
            # Differential needs an app + revision; it is driven explicitly, not here.
            rows.append((label, "SKIP", "run emit_any_049.py directly with PEPIN_APP_*"))
            skipped += 1
            continue
        missing = [n for n in needs if not roots.get(n)]
        if missing:
            var = {"seed": "PEPIN_SEED_ROOT / --seed", "a1": "PEPIN_A1_ROOT / --a1",
                   "a2": "PEPIN_A2_ROOT / --a2"}
            rows.append((label, "SKIP", f"needs {' '.join(var[m] for m in missing)}"))
            skipped += 1
            continue
        env = {}
        for key, root_name in envmap.items():
            env[key] = roots[root_name]
        code, detail = run(script, extra, env, HERE.parent)
        if code is None:
            rows.append((label, "SKIP", detail)); skipped += 1
        elif code == 0:
            rows.append((label, "PASS", detail))
        else:
            rows.append((label, "FAIL", detail)); failed += 1

    width = max(len(r[0]) for r in rows) + 2
    print(f"{'gate'.ljust(width)}result  detail")
    print("-" * (width + 50))
    for label, result, detail in rows:
        print(f"{label.ljust(width)}{result:<8}{detail[:70]}")
    ran = len(rows) - skipped
    print(f"\n{ran} gate(s) ran, {failed} failed, {skipped} skipped")
    if skipped:
        print("Skipped gates are NOT passes. Set the root variable to run them.")
    # Never let "green" imply coverage it did not have. A run with skips is PARTIAL.
    if failed:
        verdict = f"{failed} FAILING"
    elif skipped:
        verdict = f"PARTIAL - {ran} ran, {skipped} skipped (not a full pass)"
    else:
        verdict = "ALL GREEN - every gate ran"
    print("A3 GATES: " + verdict)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())