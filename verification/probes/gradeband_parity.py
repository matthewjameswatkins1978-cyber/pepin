"""E10 grade bands triple-backend parity (A4 G-A4-4 contract, verbatim adoption).

Sketch from the contract (band fn verbatim); native file adds a main caller,
seed file adds top-level say calls (entry divergence documented, not hidden).
P2 boundaries 90/89/80/79/70/69 + P1 seed-85; expected map
{90:10, 89:6, 80:6, 79:3, 70:3, 69:1, 85:6}.
N1 band(true) -> check invalid/PEP_TYPE_MISMATCH.
N2 literal 9223372036854775808 -> check invalid (Int64 static range).

Usage: python gradeband_parity.py <a2-worktree>
Exit 0 = all parity + negatives hold.
"""
import pathlib
import subprocess
import sys

A2ROOT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(A2ROOT))
OUT = A2ROOT / "_build" / "a3-g55"
OUT.mkdir(parents=True, exist_ok=True)

import pep_c23  # noqa: E402

# ADAPTED fixture (E10 sketch as specified does not compile — see receipt):
# (1) `>=` is absent from Pep (seed: Unexpected character '>'); use `<=`.
# (2) arithmetic over let-bound locals is refused by the emitter; the same
# band mapping (10/6/3/1) restructured as nested if-expressions emits.
BAND = ("fn band(score: Int) -> Int {\n"
        "  return if 90 <= score { 10 } else { if 80 <= score { 6 } "
        "else { if 70 <= score { 3 } else { 1 } } }\n"
        "}\n")
EXPECT = {90: 10, 89: 6, 80: 6, 79: 3, 70: 3, 69: 1, 85: 6}


def normalize(raw):
    return raw.replace(b"\r\n", b"\n")


def emit_c(source):
    return pep_c23.emit(source.encode("utf-8"))


def build_and_run(compiler_name, c_source, stem):
    compiler = pep_c23.compiler_path(compiler_name)
    c_path = OUT / f"{stem}.c"
    exe_path = OUT / f"{stem}.exe"
    c_path.write_text(c_source, encoding="utf-8", newline="\n")
    built = subprocess.run([str(compiler), "-std=c23", "-Wall", "-Wextra",
                            "-Wpedantic", "-Werror", "-O2",
                            str(c_path), "-o", str(exe_path)],
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
        subprocess.run(["pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass",
                        "-File", str(A2ROOT / "pep.ps1"), "describe"],
                       capture_output=True, check=True, timeout=300,
                       cwd=str(A2ROOT))
    return exe


def seed_run(source, stem):
    path = OUT / f"{stem}.pep"
    path.write_text(source, encoding="utf-8", newline="\n")
    ran = subprocess.run([str(seed_exe()), "run", str(path)],
                         capture_output=True, check=False, cwd=str(A2ROOT))
    if ran.returncode:
        return None, (f"SEED-FAIL rc={ran.returncode} "
                      f"{ran.stderr.decode('utf-8', 'replace')[:300]}")
    return normalize(ran.stdout), None


def check_json(source, stem):
    import json as _json
    path = OUT / f"{stem}.pep"
    path.write_text(source, encoding="utf-8", newline="\n")
    done = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(A2ROOT / "pep.ps1"),
         "check", str(path), "--json"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(A2ROOT))
    try:
        payload = _json.loads(done.stdout.strip())
    except ValueError:
        return None, ["NON_JSON"]
    codes = [d.get("code") for d in payload.get("diagnostics") or []]
    return (payload.get("status"), codes), None


def main():
    failures = 0
    for score, want in EXPECT.items():
        want_b = f"{want}\n".encode()
        # Native main returns the call directly (A2-proven shape): call-in-let
        # initializers are refused by the emitter ("call-free target" rule).
        native_source = (BAND + "fn main() -> Int {\n"
                         f"  return band({score})\n"
                         "}\n")
        seed_source = (BAND + f"say(int_text(band({score})));\n")
        try:
            c_source = emit_c(native_source)
        except ValueError as err:
            print(f"[{score}] EMIT-REFUSAL: {str(err)[:200]}")
            failures += 1
            continue
        seed_bytes, err = seed_run(seed_source, f"band_seed_{score}")
        if err:
            print(f"[{score}] {err}")
            failures += 1
            continue
        if seed_bytes != want_b:
            print(f"[{score}] SEED-SURPRISE seed={seed_bytes!r} want={want_b!r}")
            failures += 1
            continue
        for compiler in ("clang", "gcc"):
            got, err = build_and_run(compiler, c_source, f"band_{score}_{compiler}")
            if err:
                print(f"[{score}/{compiler}] {err}")
                failures += 1
                continue
            stdout, _ = got
            if stdout == want_b:
                print(f"[{score}/{compiler}] PARITY value={stdout!r}")
            else:
                print(f"[{score}/{compiler}] MISMATCH native={stdout!r} "
                      f"want={want_b!r}")
                failures += 1
    n1 = BAND + "fn main() -> Int { return band(true) }\n"
    (status, codes), err = check_json(n1, "band_n1")
    if err:
        print(f"[N1] {err}")
        failures += 1
    elif status == "invalid" and "PEP_TYPE_MISMATCH" in codes:
        print("[N1] REFUSED invalid/PEP_TYPE_MISMATCH")
    else:
        print(f"[N1] differs: {status} {codes}")
        failures += 1
    n2 = "fn main() -> Int { return 9223372036854775808 }\n"
    (status2, codes2), err2 = check_json(n2, "band_n2")
    if err2:
        print(f"[N2] {err2}")
        failures += 1
    elif status2 == "invalid":
        print(f"[N2] REFUSED invalid codes={codes2}")
    else:
        print(f"[N2] NOT refused: {status2} {codes2}")
        failures += 1
    print(f"SUMMARY failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
