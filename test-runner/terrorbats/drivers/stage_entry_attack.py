"""Affirmative stage oracle for the C23 pipeline.

Why this exists
---------------
"stderr does not contain PEP_RUNTIME_STEP_LIMIT" is not proof that a parser
repair worked: the string can be absent because a *later* stage failed, because
the run crashed, or because a different code path ran. This driver asks a
stronger question — **which stage did the pipeline actually reach, and what is the
evidence for that?** — and reports it per fixture.

Stages, in order, each with the affirmative evidence that distinguishes it:
  parser          the parse tool returned (any outcome) — evidenced by the
                  response operation or by a post-parse failure
  checker         "check parsed source" was invoked, or parse metrics show a
                  completed parse followed by a non-parse error
  emitter         an `unsupported` refusal came from the emitter, or C was emitted
  c-compiler      a compiler diagnostic names the generated .c file / -Werror
  executed        the built executable ran and printed the expected value

Attacks
-------
1. `parser-completion-affirmative`: every previously parse-blocked fixture must
   now show affirmative post-parser evidence. A fixture still failing *in the
   parser* with the step limit is a VIOLATION of the mission claim.
2. `invalid-source-never-advances`: a deliberately invalid program must not be
   reported as reaching emitter/compiler/execution.
3. `success-requires-execution`: "built" without a runnable executable that
   produces the expected value is not success.
4. `stage-evidence-per-fixture`: the per-fixture stage + evidence, printed so a
   reader can check the claim instead of trusting a verdict.

Exit codes: 0 all held, 1 any violation, 2 harness could not run.
"""
import json
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
PEP = REPO / "pep.ps1"
FIXTURES = REPO / "test-runner" / "terrorbats" / "fixtures"

# fixture -> expected stdout if it ever executes successfully, else None
CASE_FIXTURES = {
    "control_int_abs.pep": "7",
    "composed_int_gcd.pep": "6",
    "composed_int_is_even.pep": "true",
    "composed_int_clamp_negative.pep": "0",
}
INVALID_FIXTURE = None  # written on the fly


def report(name, expect, observed, ok, detail=""):
    print("ATTACK %s | expect=%s | observed=%s | %s" % (
        name, expect, observed, "HOLD" if ok else "VIOLATED"))
    if detail:
        print("DETAIL %s | %s" % (name, str(detail)[:400].replace("\n", " ")))


def build(source_path, exe_name):
    """Run the real C23 pipeline. Returns exit code, stderr, exe path."""
    exe = REPO / exe_name
    if exe.exists():
        exe.unlink()
    proc = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(PEP), "build-c23", str(source_path),
         "--output", str(exe)],
        cwd=str(REPO), text=True, capture_output=True, timeout=1800)
    return proc.returncode, (proc.stderr or "") + (proc.stdout or ""), exe


def classify(exit_code, text, exe, expected):
    """Return (stage, parser_complete, evidence) from real observations."""
    if exit_code == 0 and exe.exists():
        if expected is None:
            return "executed", True, "exit 0 and executable produced"
        run = subprocess.run([str(exe)], text=True, capture_output=True, timeout=300)
        actual = (run.stdout or "").strip()
        if actual == expected:
            return "executed", True, "exit 0, executable printed %r" % actual
        return ("c-compiler", True,
                "exit 0 but executable printed %r, expected %r" % (actual, expected))
    text = text or ""
    if "PEP_RUNTIME_STEP_LIMIT" in text:
        metrics = re.search(r"'metrics': \{[^}]*\}", text)
        if "check parsed source" in text:
            return "checker", True, "check phase hit the step limit; %s" % (
                metrics.group(0) if metrics else "no metrics")
        if "parse source" in text:
            return "parser", False, "parse phase hit the step limit; %s" % (
                metrics.group(0) if metrics else "no metrics")
        return "unknown", False, "step limit at an unidentified phase"
    if "Pep C23 unsupported:" in text:
        reason = text.split("Pep C23 unsupported:", 1)[1].strip().splitlines()[0]
        if "valid Pep checker report" in reason:
            # The emitter refused *because* the checker rejected the program, so
            # the pipeline stopped at the checker boundary. Classifying this as an
            # emitter stage made an invalid program look like it advanced too far.
            return "checker", True, "rejected at the checker boundary: %s" % reason[:120]
        return "emitter", True, "emitter refused: %s" % reason[:120]
    if re.search(r"\.c:\d+:\d+: (error|warning)", text) or "-Werror" in text:
        first = next((line for line in text.splitlines()
                      if re.search(r"\.c:\d+:\d+:", line)), "compiler diagnostic")
        return "c-compiler", True, "compiler rejected emitted C: %s" % first[:160]
    if "Pep C23 error:" in text:
        return "unknown", False, "pipeline error: %s" % text.strip().splitlines()[-1][:160]
    return "unknown", False, "unrecognised outcome (exit %s)" % exit_code


def main():
    violations = 0
    results = {}
    for name, expected in CASE_FIXTURES.items():
        path = FIXTURES / name
        if not path.is_file():
            print("HARNESS-ERROR missing fixture %s" % name)
            return 2
        exit_code, text, exe = build(path, "tb-stage-%s.exe" % path.stem)
        stage, parser_complete, evidence = classify(exit_code, text, exe, expected)
        results[name] = {"stage": stage, "parser_complete": parser_complete,
                         "exit": exit_code, "evidence": evidence}

    # 1. affirmative parser completion for every previously blocked fixture
    blocked = [name for name in CASE_FIXTURES if name != "control_int_abs.pep"]
    failing = [name for name in blocked if not results[name]["parser_complete"]]
    ok = not failing
    report("parser-completion-affirmative",
           "every previously parse-blocked fixture shows post-parser evidence",
           "checked=%d still_parse_blocked=%d" % (len(blocked), len(failing)),
           ok, {name: results[name]["stage"] + " / " + results[name]["evidence"]
                for name in failing})
    violations += 0 if ok else 1

    # 2. an invalid program must never advance past the parser/checker
    invalid = REPO / "tb-invalid-source.pep"
    invalid.write_text("fn main() -> Int { return 1 % 2 }\n", encoding="utf-8",
                       newline="\n")
    try:
        exit_code, text, exe = build(invalid, "tb-stage-invalid.exe")
        stage, parser_complete, evidence = classify(exit_code, text, exe, None)
        ok = stage in ("parser", "checker") and not exe.exists()
        report("invalid-source-never-advances",
               "stage stays at parser/checker and no executable is produced",
               "stage=%s exit=%s exe=%s" % (stage, exit_code, exe.exists()),
               ok, evidence)
        violations += 0 if ok else 1
    finally:
        if invalid.exists():
            invalid.unlink()

    # 3. success must mean execution, not merely a build exit code
    control = results["control_int_abs.pep"]
    ok = control["stage"] == "executed"
    report("success-requires-execution",
           "the supported control reaches the executed stage with the expected value",
           "stage=%s evidence=%s" % (control["stage"], control["evidence"]), ok)
    violations += 0 if ok else 1

    # 4. stage evidence per fixture, so the claim is checkable
    print("ATTACK stage-evidence-per-fixture | expect=observable stage per fixture | "
          "observed=%s" % json.dumps({k: v["stage"] for k, v in results.items()}))
    for name, row in results.items():
        print("STAGE %s | %s | exit=%s | %s" % (name, row["stage"], row["exit"],
                                                row["evidence"]))
    print("SUMMARY attacks=3 violated=%d fixtures=%d" % (violations, len(results)))
    return 0 if violations == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
