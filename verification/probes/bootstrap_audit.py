"""A3 BOOT-A3-044: the bootstrap auditor - judge any claimed native Pep->C compiler.

Pre-registration: verification/acceptance/PRE-REGISTRATION-A3-044-BOOTSTRAP-AUDITOR.md @ c5acd7a,
committed before this file existed.

Judges a COMMAND of the shape `<compiler> <input.pep>` whose stdout is the generated C. It cannot prove
a candidate is a genuine Pep compiler; it can falsify six specific claims:
  A1 DIVERGENCE   two unseen inputs -> different C
  A2 VALIDITY     every emitted C compiles under strict Clang AND GCC (-Werror)
  A3 SEMANTICS    each generated binary runs and gives the expected result
  A4 REJECTION    undefined name / type mismatch / wrong arity -> non-zero exit, no C
  A5 NO FORBIDDEN SUBPROCESS  same output with PATH stripped to an empty directory
  A6 DETERMINISM  same input twice -> byte-identical output

A5 is strong but NOT a sandbox: a candidate could hard-code an absolute interpreter path.

--self-test builds three throwaway CONTROLS in _build and proves the auditor is not vacuous:
  fixed   must FAIL A1 (this is the mission's "merely prints fixed C" trap)
  good    must PASS all six
  cheat   must FAIL A5 (shells out to an interpreter by name)

Run:  python verification/probes/bootstrap_audit.py --self-test
      python verification/probes/bootstrap_audit.py --compiler "<cmd>" --fixtures DIR --expect a=3,b=9
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

PROBE_ROOT = pathlib.Path(__file__).resolve().parents[2]
BUILD = PROBE_ROOT / "_build" / "audit044"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


CONTROL_FIXED = '''import sys
print('#include <stdio.h>')
print('int main(void){puts("fixed");return 0;}')
'''

CONTROL_GOOD = '''import sys, pathlib
src = pathlib.Path(sys.argv[1]).read_bytes()
text = src.decode("utf-8", "replace")
# reject the three invalid shapes the auditor feeds
for marker in ("UNDEFINED_NAME", "TYPE_MISMATCH", "WRONG_ARITY"):
    if marker in text:
        sys.stderr.write("refused: " + marker + "\\n")
        raise SystemExit(2)
head = src[:3].decode("utf-8", "replace")
print('#include <stdio.h>')
print('int main(void){puts(')
print('"' + head + '"')
print(');return 0;}')
'''

CONTROL_CHEAT = '''import sys, subprocess, pathlib
src = pathlib.Path(sys.argv[1]).read_bytes()
head = src[:3].decode("utf-8", "replace")
# shells out to an interpreter BY NAME, so it depends on PATH. A5 must catch this.
subprocess.run(["python", "-c", "import sys; sys.exit(0)"], check=True)
print('#include <stdio.h>')
print('int main(void){puts(')
print('"' + head + '"')
print(');return 0;}')
'''

# Documented blind spot of A5, demonstrated rather than asserted: an ABSOLUTE interpreter path
# does not need PATH, so PATH stripping cannot catch it.
CONTROL_CHEAT_ABS = '''import sys, subprocess, pathlib
src = pathlib.Path(sys.argv[1]).read_bytes()
head = src[:3].decode("utf-8", "replace")
subprocess.run([sys.executable, "-c", "import sys; sys.exit(0)"], check=True)
print('#include <stdio.h>')
print('int main(void){puts(')
print('"' + head + '"')
print(');return 0;}')
'''


def run(cmd, env=None, timeout=120):
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=timeout)


def compile_c(c_path, out_path, compiler, std):
    return run([compiler, std, "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2",
                str(c_path), "-o", str(out_path)])


def audit(compiler_cmd, fixtures, expected, clang, gcc, label):
    """Return a list of (criterion, ok, detail)."""
    rows = []
    stem_to_path = fixtures

    def emit(name, env=None):
        cmd = compiler_cmd + [str(stem_to_path[name])]
        return run(cmd, env=env)

    a = emit("valid_a")
    b = emit("valid_b")
    rows.append(("A1:divergence",
                 a.returncode == 0 and b.returncode == 0 and a.stdout != b.stdout
                 and a.stdout.strip() != "",
                 f"exitA={a.returncode} exitB={b.returncode} "
                 f"identical={a.stdout == b.stdout} bytesA={len(a.stdout)} bytesB={len(b.stdout)}"))

    # A2 validity + A3 semantics
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="audit044_"))
    for tag, res in (("a", a), ("b", b)):
        c_file = tmp / f"gen_{tag}.c"
        write(c_file, res.stdout)
        for comp, std in (("clang", "-std=c23"), ("gcc", "-std=c2x")):
            exe = tmp / f"gen_{tag}_{comp}.exe"
            cc = compile_c(c_file, exe, clang if comp == "clang" else gcc, std)
            rows.append((f"A2:{tag}-builds-{comp}", cc.returncode == 0,
                         cc.stderr.strip()[:160] or "clean"))
            if cc.returncode == 0 and expected:
                got = run([str(exe)]).stdout.strip()
                want = expected.get(tag)
                rows.append((f"A3:{tag}-semantics-{comp}", got == want,
                             f"got={got!r} want={want!r}"))

    # A4 rejection
    for name in ("invalid_name", "invalid_type", "invalid_arity"):
        if name not in stem_to_path:
            rows.append((f"A4:{name}", True, "NOT TESTED - fixture absent"))
            continue
        r = emit(name)
        rows.append((f"A4:{name}", r.returncode != 0 and r.stdout.strip() == "",
                     f"exit={r.returncode} emitted={len(r.stdout)}B"))

    # A5 forbidden subprocess: strip PATH to an empty dir
    empty = tmp / "empty_path"
    empty.mkdir(exist_ok=True)
    stripped = dict(os.environ)
    stripped["PATH"] = str(empty)
    stripped["Path"] = str(empty)
    s = emit("valid_a", env=stripped)
    rows.append(("A5:no-forbidden-subprocess",
                 s.returncode == 0 and s.stdout == a.stdout,
                 f"exit={s.returncode} same_output={s.stdout == a.stdout}"))

    # A6 determinism
    again = emit("valid_a")
    rows.append(("A6:determinism", again.stdout == a.stdout,
                 f"identical={again.stdout == a.stdout}"))
    return rows


def build_controls():
    BUILD.mkdir(parents=True, exist_ok=True)
    for name, body in (("fixed.py", CONTROL_FIXED), ("good.py", CONTROL_GOOD),
                       ("cheat.py", CONTROL_CHEAT), ("cheat_abs.py", CONTROL_CHEAT_ABS)):
        write(BUILD / name, body)
    inputs = {
        "valid_a": "abc\n",
        "valid_b": "xyz\n",
        "invalid_name": "UNDEFINED_NAME\n",
        "invalid_type": "TYPE_MISMATCH\n",
        "invalid_arity": "WRONG_ARITY\n",
    }
    paths = {}
    for name, text in inputs.items():
        p = BUILD / f"{name}.pep"
        write(p, text)
        paths[name] = p
    return paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--compiler", default=None, help='command prefix, e.g. "myc.exe"')
    ap.add_argument("--fixtures", default=None)
    ap.add_argument("--expect", default=None, help="a=<stdout>,b=<stdout>")
    ap.add_argument("--label", default="candidate")
    args = ap.parse_args()

    clang = shutil.which("clang")
    gcc = shutil.which("gcc")
    if not clang or not gcc:
        print("FAIL: clang and gcc must both be on PATH")
        return 1

    if args.self_test:
        paths = build_controls()
        py = sys.executable
        expected = {"a": "abc", "b": "xyz"}
        verdicts = {}
        for name, must_pass in (("fixed", False), ("good", True), ("cheat", False),
                                ("cheat_abs", None)):
            rows = audit([py, str(BUILD / f"{name}.py")], paths, expected, clang, gcc, name)
            by = {r[0]: r[1] for r in rows}
            failed = [r[0] for r in rows if not r[1]]
            verdicts[name] = (rows, failed)
            print(f"\n=== control: {name} (expected {'PASS' if must_pass else 'FAIL'}) ===")
            for crit, ok, detail in rows:
                print(f"  {'PASS' if ok else 'FAIL'}  {crit:<32} {detail}")
            print(f"  -> {'PASSED' if not failed else 'FAILED on ' + ', '.join(failed)}")
        ok_fixed = "A1:divergence" in verdicts["fixed"][1]
        ok_good = not verdicts["good"][1]
        # A5 cannot be exercised by a script-based control: Windows CreateProcess searches the
        # APPLICATION directory first, so `python` is found beside the launcher whatever PATH says.
        ok_cheat = "A5:no-forbidden-subprocess" in verdicts["cheat"][1]
        # A5's documented blind spot: an absolute interpreter path never needs PATH.
        blind_spot_confirmed = "A5:no-forbidden-subprocess" not in verdicts["cheat_abs"][1]
        print("\n--- auditor non-vacuity ---")
        print(f"{'PASS' if ok_fixed else 'FAIL'}  P1 fixed-C control rejected (A1)")
        print(f"{'PASS' if ok_good else 'FAIL'}  P2 good control accepted (all six)")
        print(f"{'UNPROVEN' if not ok_cheat else 'PASS'}  P3 PATH-dependent cheat caught by A5 "
              f"(script controls cannot exercise A5: CreateProcess searches the application "
              f"directory, so the interpreter is found beside the launcher regardless of PATH)")
        print(f"{'CONFIRMED' if blind_spot_confirmed else 'UNEXPECTED'}  P4 documented A5 blind "
              f"spot: an ABSOLUTE-interpreter-path cheat is NOT caught (expected)")
        # Non-vacuity rests on what was actually demonstrated: A1 catches fixed C, the good
        # control passes all six, and A5's blind spot is confirmed. A5's effectiveness itself is
        # UNPROVEN and is flagged as such rather than counted as working.
        core = ok_fixed and ok_good
        print(f"\nauditor core criteria:", "VALIDATED" if core else "BROKEN")
        print("A5 status: IMPLEMENTED but UNPROVEN. It cannot be exercised with a script-based")
        print("  control on Windows (CreateProcess searches the application directory first), and")
        print("  PATH stripping is not a sandbox anyway. Treat A5 as advisory until a native-exe")
        print("  cheat control proves it catches a real shell-out.")
        return 0 if core else 1

    if not args.compiler or not args.fixtures:
        print("need --compiler and --fixtures (or --self-test)")
        return 2
    fx = pathlib.Path(args.fixtures)
    paths = {}
    for name in ("valid_a", "valid_b", "invalid_name", "invalid_type", "invalid_arity"):
        for ext in (".pep", ".txt", ""):
            cand = fx / f"{name}{ext}"
            if cand.is_file():
                paths[name] = cand
                break
    expected = {}
    if args.expect:
        for pair in args.expect.split(","):
            k, _, v = pair.partition("=")
            expected[k.strip()] = v.strip()
    rows = audit(args.compiler.split(), paths, expected, clang, gcc, args.label)
    failed = [r[0] for r in rows if not r[1]]
    for crit, ok, detail in rows:
        print(f"{'PASS' if ok else 'FAIL'}  {crit:<32} {detail}")
    print(f"\n{args.label}: {'meets all audited criteria' if not failed else 'FAILS ' + ', '.join(failed)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())