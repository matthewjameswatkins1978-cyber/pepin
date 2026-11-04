"""Independent native check for A2's say() lowering claim (priority 5), two programs.

A) the canonical pattern the corpus uses: a function computes, a TOP-LEVEL say prints it.
B) say inside a function body, where the Pep interpreter prints nothing.

For each: emit C through the project's emitter, compile strictly with clang and gcc, run,
and compare against the interpreter's own output for the same source. No A2 test harness
is used.
"""
import json
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402

PROGRAMS = {
    "canonical_top_level_say": (
        "fn answer() -> Int {\n    return 20 + 22\n}\n\n"
        "fn main() -> Int {\n    return answer()\n}\n\n"
        "say(int_text(main()))\n"),
    "say_inside_function": (
        "fn main() -> Int {\n    say(\"in-main\")\n    return 0\n}\n"),
}


def run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", **kwargs)


result = {"repo": str(REPO), "programs": {}}
overall_ok = True

with tempfile.TemporaryDirectory(prefix="a3-native-") as folder:
    work = pathlib.Path(folder)
    for name, source in PROGRAMS.items():
        entry = {"source": source}
        pep_file = work / f"{name}.pep"
        pep_file.write_text(source, encoding="utf-8", newline="\n")
        interp = run(["pwsh", "-NoProfile", "-File", str(REPO / "pep.ps1"), "run",
                      str(pep_file)], cwd=str(REPO))
        entry["interpreter"] = {"exit": interp.returncode, "stdout": interp.stdout}
        try:
            c_source = pep_c23.emit(source.encode("utf-8"))
        except BaseException as error:  # noqa: BLE001
            entry["emit"] = {"error": f"{type(error).__name__}: {error}"}
            result["programs"][name] = entry
            overall_ok = False
            continue
        entry["emit"] = {"bytes": len(c_source)}
        c_path = work / f"{name}.c"
        c_path.write_text(c_source, encoding="utf-8", newline="\n")
        for compiler, flags in (("clang", ["-std=c23"]), ("gcc", ["-std=c2x"])):
            exe = work / f"{name}-{compiler}.exe"
            built = run([compiler, *flags, "-Wall", "-Wextra", "-Wpedantic", "-O1",
                         str(c_path), "-o", str(exe)])
            record = {"build_exit": built.returncode,
                      "build_stderr": built.stderr[-400:]}
            if built.returncode == 0:
                ran = run([str(exe)])
                record.update({"run_exit": ran.returncode, "stdout": ran.stdout})
                record["matches_interpreter"] = ran.stdout == interp.stdout
            entry[compiler] = record
            if record.get("build_exit") != 0 or record.get("run_exit") != 0:
                overall_ok = False
        result["programs"][name] = entry

print(json.dumps(result, indent=2))
canonical = result["programs"]["canonical_top_level_say"]
inside = result["programs"]["say_inside_function"]
canonical_ok = all(canonical.get(c, {}).get("matches_interpreter") for c in ("clang", "gcc"))
inside_native = {c: inside.get(c, {}).get("stdout") for c in ("clang", "gcc")}
print("SUMMARY",
      "canonical_matches=" + str(bool(canonical_ok)),
      "interpreter_in_main=" + repr(inside.get("interpreter", {}).get("stdout")),
      "native_in_main=" + repr(inside_native))
raise SystemExit(0 if canonical_ok else 1)
