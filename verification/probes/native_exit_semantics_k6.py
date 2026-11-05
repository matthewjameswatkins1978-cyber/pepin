"""Campaign K / A3 K6: native process exit-value vs abnormal exit.

This closes a confusion I published in Campaign H: I read process exit codes as program values
and briefly believed Str equality was broken. The emitted C epilogue is

    int main(void) { (void)printf("%lld\n", (long long)(pep_fn_main())); return 0; }

so the PROGRAM value is stdout and the PROCESS status is 0 unless something genuinely traps.
This probe pins that distinction with three programs:

  V1 main returns 42        -> stdout "42", exit 0        (value is not the exit status)
  V2 main returns 0         -> stdout "0",  exit 0        (a zero value is not "failure")
  V3 runtime overflow trap  -> nonzero exit + a runtime trap line on stderr (abnormal)

Claim 4: a harness that reads exit codes alone cannot tell V1 from V2, and a harness that reads
stdout alone cannot tell V1 from a trap. Only (exit status AND stdout AND stderr) is enough.

Usage: python native_exit_semantics_k6.py <tree>
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(sys.argv[1]).resolve()
OUT = ROOT / "_build" / "a3-k6"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
import pep_c23  # noqa: E402

CASES = {
    "V1-returns-42": 'fn main() -> Int {\n  return 42\n}\n',
    "V2-returns-0": 'fn main() -> Int {\n  return 0\n}\n',
    "V3-overflow-trap": ('fn main() -> Int {\n'
                         '  let big = 9223372036854775807\n'
                         '  return big + 1\n'
                         '}\n'),
}
RESULTS = []


def record(case, ok, detail):
    RESULTS.append((case, ok))
    print(f"{'HELD    ' if ok else 'FALSIFIED'} {case} :: {detail}")


def emit(source, stem):
    try:
        return pep_c23.emit(source.encode("utf-8")), None
    except Exception as err:  # noqa: BLE001
        return None, str(err)[:150]


def build_run(c_source, stem, compiler="clang"):
    c_path = OUT / f"{stem}.c"
    exe = OUT / f"{stem}.exe"
    c_path.write_text(c_source, encoding="utf-8", newline="\n")
    built = subprocess.run([str(pep_c23.compiler_path(compiler)), "-std=c23", "-Wall",
                            "-Wextra", "-Wpedantic", "-Werror", "-O2", str(c_path),
                            "-o", str(exe)], capture_output=True, text=True,
                           check=False, cwd=str(ROOT))
    if built.returncode:
        return None, f"C-BUILD {built.stderr.strip()[:120]}"
    done = subprocess.run([str(exe)], capture_output=True, cwd=str(ROOT), check=False)
    return (done.returncode,
            done.stdout.decode("utf-8", "replace").replace("\r\n", "\n").strip(),
            done.stderr.decode("utf-8", "replace").strip()), None


def main():
    print(f"TREE {ROOT}")
    observed = {}
    for label, source in CASES.items():
        c_source, err = emit(source, label)
        if err:
            print(f"{label} EMIT-REFUSED {err}")
            observed[label] = None
            continue
        got, build_err = build_run(c_source, label)
        if build_err:
            print(f"{label} {build_err}")
            observed[label] = None
            continue
        rc, out, errtxt = got
        observed[label] = {"rc": rc, "stdout": out, "stderr": errtxt[:90]}
        print(f"{label} rc={rc} stdout={out!r} stderr={errtxt.splitlines()[:1]}")
        # Epilogue excerpt, printed once as mechanism evidence.
        if label == "V1-returns-42":
            # Function naming differs across branches (pep_fn_main vs pep_fn_0), so match the
            # shape rather than a name: the process entry only PRINTS the value and returns 0.
            lines = c_source.split("\n")
            entry = next((i for i, ln in enumerate(lines) if ln.startswith("int main(void)")), None)
            tail = lines[entry:entry + 4] if entry is not None else []
            print("   epilogue: " + " | ".join(ln.strip() for ln in tail)[:150])

    v1, v2, v3 = (observed.get(k) for k in ("V1-returns-42", "V2-returns-0",
                                            "V3-overflow-trap"))
    record("V1 a returned 42 is a STDOUT value with process exit 0",
           bool(v1) and v1["rc"] == 0 and v1["stdout"] == "42",
           f"{v1}")
    record("V2 a returned 0 prints 0 and still exits 0 (not 'failure')",
           bool(v2) and v2["rc"] == 0 and v2["stdout"] == "0",
           f"{v2}")
    record("V3 a runtime trap is distinguishable (nonzero exit and/or stderr trap line)",
           bool(v3) and (v3["rc"] != 0 or "PEP_RUNTIME" in v3["stderr"]),
           f"{v3}")
    record("exit status alone cannot separate V1 from V2 (both 0) — stdout is required",
           bool(v1) and bool(v2) and v1["rc"] == v2["rc"] == 0
           and v1["stdout"] != v2["stdout"],
           f"rc V1/V2 = {v1['rc'] if v1 else '?'}/{v2['rc'] if v2 else '?'}, "
           f"stdout {v1['stdout'] if v1 else '?'}/{v2['stdout'] if v2 else '?'}")

    held = sum(1 for _, ok in RESULTS if ok)
    print(f"SUMMARY claims={len(RESULTS)} held={held} falsified={len(RESULTS) - held}")
    return 0 if held == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
