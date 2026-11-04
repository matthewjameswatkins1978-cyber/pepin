"""G-A3-5: real canonical-lexer fn ascii_digit through seed vs native (Clang/GCC).

ascii_digit is verbatim from examples/pep_lexer.pep (canonical lexer, A2 tree):
a one-expression boolean-chain body -- the same expression class as the 66n/S2
critical path, but tiny enough to isolate native parity from checker budgets.

Positive: native file (fn + final-if main returning 1/0) -> emit_c -> strict
Clang/GCC build -> run; seed file (same fn + top-level if/say) -> pep.exe run.
Parity: native stdout == seed stdout + emitter return-echo line (A2's method).
Two programs (true-case byte 53, false-case byte 65).
Negative: say(bool) on checker-valid input -> exact emitter refusal boundary.

Usage: python native_parity_ascii_digit.py <a2-worktree>
Exit 0 = parity holds both compilers + negative refuses; 1 = mismatch/blocker.
"""
import json
import pathlib
import subprocess
import sys

A2ROOT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(A2ROOT))
OUT = A2ROOT / "_build" / "a3-g55"
OUT.mkdir(parents=True, exist_ok=True)

import pep_c23  # noqa: E402

FN = ("fn ascii_digit(byte: Int) -> Bool {\n"
      "  return 48 <= byte && byte <= 57\n"
      "}\n")
CASES = {"T": 53, "F": 65}


def emit_c(source):
    return pep_c23.emit(source.encode("utf-8"))


def normalize(raw):
    return raw.replace(b"\r\n", b"\n")


def build_and_run(compiler_name, c_source, stem):
    compiler = pep_c23.compiler_path(compiler_name)
    c_path = OUT / f"{stem}.c"
    exe_path = OUT / f"{stem}.exe"
    c_path.write_text(c_source, encoding="utf-8", newline="\n")
    built = subprocess.run([str(compiler), "-std=c23", "-Wall", "-Wextra", "-Wpedantic",
                            "-Werror", "-O2", str(c_path), "-o", str(exe_path)],
                           capture_output=True, text=True, check=False,
                           cwd=str(A2ROOT))
    if built.returncode:
        return None, f"BUILD-FAIL {built.stderr[:300]}"
    ran = subprocess.run([str(exe_path)], capture_output=True, check=False,
                         cwd=str(A2ROOT))
    return (normalize(ran.stdout), ran.returncode), None


def seed_exe():
    exe = A2ROOT / "_build" / "ocaml" / "pep.exe"
    if not exe.exists():
        subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                        "-File", str(A2ROOT / "pep.ps1"), "describe"],
                       capture_output=True, check=True, timeout=300, cwd=str(A2ROOT))
    return exe


def seed_run(source, stem):
    path = OUT / f"{stem}.pep"
    path.write_text(source, encoding="utf-8", newline="\n")
    ran = subprocess.run([str(seed_exe()), "run", str(path)], capture_output=True,
                         check=False, cwd=str(A2ROOT))
    if ran.returncode:
        return None, f"SEED-FAIL rc={ran.returncode} {ran.stderr.decode('utf-8', 'replace')[:300]}"
    return normalize(ran.stdout), None


def main():
    failures = 0
    for tag, byte in CASES.items():
        native_source = (FN + "fn main() -> Int {\n"
                         f"  if (ascii_digit({byte})) {{ return 1 }} else {{ return 0 }}\n"
                         "}\n")
        seed_source = (FN + f"let r = if (ascii_digit({byte})) {{ 1 }} "
                       "else { 0 };\n" + "say(int_text(r));\n")
        try:
            c_source = emit_c(native_source)
        except ValueError as err:
            print(f"[{tag}] EMIT-REFUSAL (earlier-stage blocker): {str(err)[:300]}")
            failures += 1
            continue
        seed_bytes, err = seed_run(seed_source, f"digit_seed_{tag}")
        if err:
            print(f"[{tag}] {err}")
            failures += 1
            continue
        expect = (b"1\n" if tag == "T" else b"0\n")
        if seed_bytes != expect:
            print(f"[{tag}] SEED-SURPRISE seed={seed_bytes!r} want={expect!r}")
            failures += 1
            continue
        want_ret = b"1\n" if tag == "T" else b"0\n"
        for compiler in ("clang", "gcc"):
            got, err = build_and_run(compiler, c_source, f"digit_{tag}_{compiler}")
            if err:
                print(f"[{tag}/{compiler}] {err}")
                failures += 1
                continue
            stdout, _ = got
            # Entry-point difference (stated): native carries no say calls, so its
            # stdout is the return echo only; the seed prints via say. Parity is
            # same VALUE on both sides: native == echo and seed == echo.
            if stdout == want_ret and seed_bytes == want_ret:
                print(f"[{tag}/{compiler}] PARITY value={stdout!r} both sides")
            else:
                print(f"[{tag}/{compiler}] MISMATCH native={stdout!r} "
                      f"seed={seed_bytes!r} want={want_ret!r}")
                failures += 1
    # Negative: say of a Bool. The CHECKER refuses (PEP_TYPE_MISMATCH) before
    # the emitter runs -- corrected framing: checker-layer boundary, fail-closed.
    neg_source = FN + "fn main() -> Int {\n  say(ascii_digit(53))\n  return 0\n}\n"
    try:
        emit_c(neg_source)
        print("[NEG say-bool] EMITTED (no refusal -- finding)")
        failures += 1
    except ValueError:
        path = OUT / "neg_say_bool.pep"
        path.write_text(neg_source, encoding="utf-8", newline="\n")
        done = subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(A2ROOT / "pep.ps1"),
             "check", str(path), "--json"], capture_output=True, text=True,
            encoding="utf-8", errors="replace", cwd=str(A2ROOT))
        try:
            payload = json.loads(done.stdout.strip())
            codes = [d.get("code") for d in payload.get("diagnostics") or []]
        except ValueError:
            payload, codes = {}, ["NON_JSON"]
        if payload.get("status") == "invalid" and "PEP_TYPE_MISMATCH" in codes:
            print("[NEG say-bool] REFUSED at checker: invalid/PEP_TYPE_MISMATCH")
        else:
            print(f"[NEG say-bool] refusal differs: "
                  f"{payload.get('status')} {codes}")
            failures += 1
    print(f"SUMMARY failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
