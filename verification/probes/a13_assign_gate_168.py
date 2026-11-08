"""A3 BOOT-A3-168: regression gate for the A13 assignment-target checker defect.

A3-163..167 established that the sectional checker rejects a program it should accept:
pep_checker_a13.pep L1933 emits "Assignment target has no supported concrete type" for a
binding assigned inside a loop and copied after it, when an earlier conditional introduced
another binding. The one-shot checker calls the same source valid, so this bug is invisible
to `pep.ps1 check` and to A13's existing 66 tests.

The reduced fixture in verification/fixtures/ reproduces it in 31 lines. This gate runs it
through the real product path and fails while the defect is present, so the defect stays
tracked mechanically instead of living in a paragraph. It flips to PASS when A1 fixes the
checker, with no edit needed here.

The control fixture differs by a single deleted line and must pass, which keeps the gate
honest: a change that breaks everything cannot look like a fix.

Env: PEPIN_CA_ROOT - repository whose pep_c23.py and checker to use (falls back to
PEPIN_GATE_ROOT, then the repo containing this probe).

Exit: 0 both cases behave, 1 defect present, 3 cannot run.
"""
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parents[1]
FIXTURES = HERE / "fixtures"
REPRO = FIXTURES / "a13-assign-target-reduced.pep"
CONTROL = FIXTURES / "a13-assign-target-reduced-control.pep"
MARK = "PEP_A13_TYPE_UNSUPPORTED"


def build(root, source, out):
    r = subprocess.run([sys.executable, str(root / "pep_c23.py"), "build-c23",
                        str(source), "--sectional", "--output", str(out)],
                       capture_output=True, text=True, timeout=3600, cwd=str(root))
    return r.returncode, (r.stderr or r.stdout or "")


def main():
    root = pathlib.Path(os.environ.get("PEPIN_CA_ROOT")
                        or os.environ.get("PEPIN_GATE_ROOT")
                        or HERE.parent).resolve()
    if not (root / "pep_c23.py").is_file():
        print(f"A13 GATE: CANNOT RUN - no pep_c23.py under {root}")
        return 3
    # The defect lives in the bound-chunk sectional path. A tree without it (an older
    # pin has no pep_sectional.py at all) silently "passes" and that green would be a
    # lie, so refuse to measure rather than report a pass we cannot support.
    sectional = root / "pep_sectional.py"
    if not sectional.is_file() or "bound-chunk" not in sectional.read_text(
            encoding="utf-8", errors="replace"):
        print(f"A13 GATE: CANNOT RUN - {root} has no bound-chunk sectional path, so this")
        print("  defect cannot manifest there. Point PEPIN_CA_ROOT at a tree that has it.")
        return 3
    for f in (REPRO, CONTROL):
        if not f.is_file():
            print(f"A13 GATE: CANNOT RUN - missing fixture {f.name}")
            return 3
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="a3a13"))
    rc_r, out_r = build(root, REPRO, tmp / "repro.exe")
    rc_c, out_c = build(root, CONTROL, tmp / "control.exe")

    defect = MARK in out_r
    control_clean = MARK not in out_c

    print(f"  repro   ({REPRO.name})   A13 rejection present: {defect}")
    print(f"  control ({CONTROL.name}) A13 rejection absent:  {control_clean}")
    if defect:
        line = [l for l in out_r.strip().splitlines() if MARK in l]
        print(f"  {line[-1].strip()[:88] if line else ''}")
        print("  A13 GATE: FAIL - the sectional checker rejects a program the one-shot")
        print("  checker calls valid. Owning fix: pep_checker_a13.pep L1933 / A1.")
        return 1
    if not control_clean:
        print("  A13 GATE: FAIL - the control also rejects, so this gate cannot distinguish")
        print("  a checker fix from a checker break. Inspect before trusting a green run.")
        return 1
    print("  A13 GATE: PASS - reducer accepted, control accepted")
    return 0


if __name__ == "__main__":
    sys.exit(main())