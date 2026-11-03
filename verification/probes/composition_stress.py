"""Composition stress: short but demanding Pep programs through three stages, with
the first failing stage named exactly (missions PEP-A3-SUSTAINED-013 slice 4).

For each fixture the probe records, in order:

  1. front end   `pep.ps1 check --json`  — the OCaml seed's lex/parse/check verdict.
  2. execution   `pep.ps1 run`           — the seed interpreter (exit code + code).
  3. Pep-written `pep_c23.emit`          — parser -> checker -> C23 emitter, the
                                           A->B path that matters for self-hosting.

Classification of the first failing stage (never conflated):
  FIXTURE_INVALID       the seed rejects the fixture: my fixture is wrong, not the
                        compiler (reported as a harness error, exit 2).
  VALID_BLOCKED_BUDGET  the seed runs it, but a Pep-written stage refuses on the
                        fixed 100,000-step budget.
  UNSUPPORTED_BACKEND   the emitter refuses a construct it does not implement.
  SEMANTIC_DISAGREEMENT the Pep-written checker refuses what the seed accepts.
  INCORRECT_DIAGNOSTIC  a stage fails with a code that does not describe the cause.
  EMITTED               all three stages pass (native compile is NOT run here).

Composition axes: nested records, cross-function calls, list pipelines, token
lists, unions with recursive match, boolean chains, multi-token source.

Every fixture defines `main` because the C23 emitter requires a top-level `main`;
without it the emitter stage answers a fixture-design question instead of a
compiler question.

Exit codes: 0 = every fixture reached EMITTED, 1 = a fixture stopped at a failing
stage, 2 = harness error including an invalid fixture.
Usage: python composition_stress.py <pinned-worktree> [fixture ...]
"""
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ARGS = [item for item in sys.argv[1:] if not item.startswith("-")]
REPO = pathlib.Path(ARGS[0] if ARGS else ".").resolve()
WANTED = ARGS[1:] or None
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402

PEP_PS1 = REPO / "pep.ps1"
CODE_RE = re.compile(r"PEP_[A-Z_]+")

FIXTURES = {
    "nested_records": """type Inner {
    a: Int
    b: Int
}

type Outer {
    inner: Inner
    tag: Str
}

fn score(outer: Outer) -> Int {
    return outer.inner.a + outer.inner.b
}

fn main() -> Int {
    let nested = Outer {
        inner: Inner {
            a: 20,
            b: 22
        },
        tag: "pep"
    }
    say(int_text(score(nested)))
    return 0
}
""",
    "list_pipeline": """fn total(values: List[Int]) -> Int {
    var running = 0
    for value in values {
        running = running + value
    }
    return running
}

fn main() -> Int {
    let base: List[Int] = [1, 2]
    let extended = append(base, 3)
    let reversed = reverse(extended)
    say(int_text(total(reversed)))
    say(int_text(length(extended)))
    return 0
}
""",
    "token_lists": """fn classify(tags: List[Str]) -> Int {
    var count = 0
    for tag in tags {
        if tag == "let" {
            count = count + 1
        } else {
            if contains(tags, "fn") {
                count = count + 2
            } else {
                count = count + 100
            }
        }
    }
    return count
}

fn main() -> Int {
    let tags: List[Str] = ["fn", "let", "let", "return"]
    say(int_text(classify(tags)))
    return 0
}
""",
    "union_match": """type Expr = Number(Int) | Add(Expr, Expr) | Scale(Expr, Int)

fn evaluate(expression: Expr) -> Int {
    return match expression {
        Number(value) => value
        Add(left, right) => evaluate(left) + evaluate(right)
        Scale(inner, factor) => evaluate(inner) * factor
    }
}

fn main() -> Int {
    let program = Add(Number(10), Scale(Add(Number(5), Number(7)), 2))
    say(int_text(evaluate(program)))
    return 0
}
""",
    "multi_function": """type Pair {
    left: Int
    right: Int
}

fn combine(pair: Pair) -> Int {
    return pair.left * 10 + pair.right
}

fn twice(value: Int) -> Int {
    return combine(Pair {
        left: value,
        right: value
    })
}

fn guarded(value: Int) -> Int {
    if (0 <= value && value <= 100) || value == 1000 {
        return value
    } else {
        return 0
    }
}

fn main() -> Int {
    say(int_text(twice(3) + combine(Pair {
        left: 1,
        right: 2
    }) + guarded(1000)))
    return 0
}
""",
    "multi_token_source": """type Token = Word(Str) | Number(Int)

fn width(token: Token) -> Int {
    return match token {
        Word(text) => 1
        Number(value) => if value == 0 { 0 } else { 1 }
    }
}

fn widths(tokens: List[Token]) -> Int {
    var total = 0
    for token in tokens {
        total = total + width(token)
    }
    return total
}

fn main() -> Int {
    let lexed: List[Token] = [Word("let"), Word("x"), Number(0), Word("return")]
    say(int_text(widths(lexed)))
    return 0
}
""",
}


def seed_check(path):
    done = subprocess.run(["pwsh", "-NoProfile", "-File", str(PEP_PS1), "check",
                           str(path), "--json"],
                          cwd=str(REPO), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    try:
        payload = json.loads(done.stdout.strip())
    except json.JSONDecodeError:
        raise RuntimeError(f"seed check returned non-JSON (exit {done.returncode}): "
                           f"{done.stdout[:200]}{done.stderr[:200]}")
    return {"status": payload.get("status"),
            "codes": [item.get("code") for item in payload.get("diagnostics") or []],
            "messages": [item.get("message") for item in payload.get("diagnostics") or []]}


def seed_run(path):
    done = subprocess.run(["pwsh", "-NoProfile", "-File", str(PEP_PS1), "run", str(path)],
                          cwd=str(REPO), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    codes = sorted(set(CODE_RE.findall((done.stderr or "") + (done.stdout or ""))))
    return {"exit": done.returncode, "codes": codes,
            "stderr": (done.stderr or "").strip().splitlines()[:2]}


def pep_pipeline(source_bytes):
    """Pep-written parser -> checker -> emitter, with the failing stage named."""
    measurements = {}
    try:
        emitted = pep_c23.emit(source_bytes, measurements)
        return {"state": "emitted", "c_bytes": len(emitted),
                "checker_status": measurements.get("checker_status"),
                "metrics": measurements.get("session_metrics")}
    except ValueError as error:          # emitter returned a non-emitted status
        return {"state": "emitter_refused", "diagnostic": str(error),
                "checker_status": measurements.get("checker_status"),
                "emitter_status": measurements.get("emitter_status"),
                "metrics": measurements.get("session_metrics")}
    except RuntimeError as error:        # a stage was refused by the host
        stage_error = measurements.get("checker_stage_error") or {}
        code = stage_error.get("code") if isinstance(stage_error, dict) else None
        stage = "checker" if "checker_stage_error" in measurements else "parser_or_host"
        return {"state": "stage_error", "stage": stage, "code": code,
                "detail": str(error)[:300],
                "metrics": measurements.get("session_metrics")}


def classify(front, run, pipeline):
    if front["status"] != "valid":
        return "FIXTURE_INVALID", front["codes"]
    if run["exit"] != 0:
        code = run["codes"][0] if run["codes"] else "NO_CODE"
        if "STEP_LIMIT" in code or "BUDGET" in code:
            return "VALID_BLOCKED_BUDGET", f"seed interpreter {code}"
        return "SEMANTIC_DISAGREEMENT", f"seed interpreter refused {code}"
    if pipeline["state"] == "emitted":
        return "EMITTED", f"C source {pipeline['c_bytes']} bytes"
    if pipeline["state"] == "stage_error":
        code = pipeline.get("code") or "NO_CODE"
        stage = pipeline.get("stage")
        if "STEP_LIMIT" in code:
            return "VALID_BLOCKED_BUDGET", f"Pep-written {stage} stage {code}"
        return "INCORRECT_DIAGNOSTIC", f"Pep-written {stage} stage {code}"
    diagnostic = pipeline.get("diagnostic") or ""
    checker_status = pipeline.get("checker_status")
    if "checker report" in diagnostic and checker_status not in (None, "valid"):
        return ("SEMANTIC_DISAGREEMENT",
                f"Pep-written checker status={checker_status!r} while the seed says valid")
    if diagnostic.startswith("Pep C23 "):
        # The emitter words its subset limits as "Pep C23 <construct> require(s) ...",
        # which is a precise documented-subset refusal, not a wrong diagnostic.
        return "UNSUPPORTED_BACKEND", diagnostic[:200]
    if "unsupported" in diagnostic.lower() or "not supported" in diagnostic.lower():
        return "UNSUPPORTED_BACKEND", diagnostic[:200]
    return "INCORRECT_DIAGNOSTIC", diagnostic[:200]


def main():
    print(f"REPO={REPO}")
    names = [name for name in FIXTURES if WANTED is None or name in WANTED]
    rows, failures = [], []
    with tempfile.TemporaryDirectory(prefix="a3-compose-") as folder:
        for name in names:
            source = FIXTURES[name]
            path = pathlib.Path(folder) / f"{name}.pep"
            path.write_text(source, encoding="utf-8", newline="\n")
            front = seed_check(path)
            if front["status"] != "valid":
                rows.append({"fixture": name, "seed_status": front["status"],
                             "seed_codes": front["codes"],
                             "seed_messages": front["messages"], "verdict": "FIXTURE_INVALID",
                             "detail": "fail-fast: a bad fixture is a harness error"})
                print(f"[{name}] FIXTURE_INVALID — {front['codes']} {front['messages']}")
                print("\n" + json.dumps(rows, indent=2, sort_keys=True))
                print("HARNESS_ERROR a fixture is not valid Pep; fix the fixture before "
                      "reading any verdict from it")
                return 2
            run = seed_run(path)
            pipeline = pep_pipeline(source.encode("utf-8"))
            verdict, detail = classify(front, run, pipeline)
            rows.append({"fixture": name, "seed_status": front["status"],
                         "seed_codes": front["codes"], "run": run,
                         "pipeline": pipeline, "verdict": verdict, "detail": detail})
            print(f"[{name}] {verdict} — {detail}")
            if verdict != "EMITTED":
                failures.append(f"{name}: {verdict} — {detail}")
    print("\n" + json.dumps(rows, indent=2, sort_keys=True))
    summary = {}
    for row in rows:
        summary[row["verdict"]] = summary.get(row["verdict"], 0) + 1
    print(f"SUMMARY fixtures={len(rows)} " +
          " ".join(f"{key}={value}" for key, value in sorted(summary.items())))
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as error:
        import traceback
        traceback.print_exc()
        print(f"HARNESS_ERROR {type(error).__name__}: {error}")
        sys.exit(2)
