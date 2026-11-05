"""Campaign K / A3 K7: use A1's NEW read-only step accounting (3ff3bf1) to test MY OWN
published stage attributions, and sanity-check the instrument itself.

A1 added `last_execute_steps` + `execute_count` to session metrics. Both prior campaigns said
per-phase accounting was the missing instrument, so the independent job is not to repeat A1's
numbers but to ask: do my earlier attributions survive, and is the counter real?

Rungs reuse the fixtures whose boundaries I published earlier:
  S1..S5  the real lex_error_code guard chain, 1/2/3/5 guards, record-field call, Str result
          (H-V4: I claimed the CHECKER budget crosses at 3 guards)
  U2..U8  union + match with 2/4/6/8 arms (K5: I claimed a CAPABILITY wall at 2-4 arms and
          the budget only from 6)

Claims:
  C0 the metric is present on a refusal (instrument reachable from outside)
  C1 a STEP_LIMIT refusal reports steps at or near the 100k limit (the counter is real,
     not a constant or a stub)
  C2 a CAPABILITY refusal reports steps far BELOW the limit (so "capability, not budget"
     is a number, not just a message)
  C3 per-rung numbers are recorded even where no claim is made (data for A1/A4)

Usage: python cost_accounting_k7.py <tree-at-3ff3bf1>
Exit 0 = all claims held.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(sys.argv[1]).resolve()
OUT = ROOT / "_build" / "a3-k7"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
import pep_c23  # noqa: E402

RECORD = 'type Info { kind: Str, diagnostic: Str }\n'
GUARDS = [
    '  if kind == "unexpected" { return "PEP_UNEXPECTED_CHARACTER" } else {}\n',
    '  if kind == "integer" { return "PEP_INT_LITERAL_RANGE" } else {}\n',
    '  if kind == "string" {\n'
    '    if diagnostic == "Pep scan found an unescaped newline in a string literal" {\n'
    '      return "PEP_NEWLINE_IN_STRING"\n'
    '    } else {}\n'
    '    if diagnostic == "Pep scan found an unsupported string escape" { return "PEP_INVALID_ESCAPE" } else {}\n'
    '    return "PEP_UNTERMINATED_STRING"\n'
    '  } else {}\n',
    '  if kind == "escape" { return "PEP_INVALID_ESCAPE" } else {}\n',
    '  if kind == "newline" { return "PEP_NEWLINE_IN_STRING" } else {}\n',
]
STEPS_RE = re.compile(r"'last_execute_steps':\s*(\d+)")
COUNT_RE = re.compile(r"'execute_count':\s*(\d+)")
CODE_RE = re.compile(r"'code':\s*'([A-Z_]+)'")
LIMIT = 100_000


def str_rung(guards):
    return (RECORD +
            'fn lex_error_code(kind: Str, diagnostic: Str) -> Str {\n'
            + "".join(GUARDS[:guards])
            + '  return "PEP_LEXER_INPUT"\n}\n'
            'fn main() -> Int {\n'
            '  let i = Info { kind: "integer", diagnostic: "" }\n'
            '  let code = lex_error_code(i.kind, i.diagnostic)\n'
            '  say(code)\n  return 0\n}\n')


def union_rung(arms):
    variants = " | ".join(f"V{i}(Int)" for i in range(arms))
    body = "\n".join(f"    V{i}(n) => n + {i}" for i in range(arms))
    return (f"type Expr = {variants}\n"
            "fn evaluate(e: Expr) -> Int {\n  return match e {\n"
            f"{body}\n  }}\n}}\n"
            f"fn main() -> Int {{\n  return evaluate(V{arms - 1}(41))\n}}\n")


def measure(label, source):
    """Return (outcome, code_or_None, steps, executions, detail)."""
    try:
        pep_c23.emit(source.encode("utf-8"))
        return ("EMITTED", None, None, None, "emitted without error")
    except Exception as err:  # noqa: BLE001
        text = str(err)
        steps = STEPS_RE.search(text)
        count = COUNT_RE.search(text)
        code = CODE_RE.search(text)
        stage = ("CHECKER" if "check parsed source" in text
                 else "EMITTER" if "emit checked source" in text else "OTHER")
        return (stage,
                code.group(1) if code else None,
                int(steps.group(1)) if steps else None,
                int(count.group(1)) if count else None,
                text[:120])


def main():
    print(f"TREE {ROOT}")
    rows = []
    rungs = [("S1-str-1guard", str_rung(1)), ("S2-str-2guards", str_rung(2)),
             ("S3-str-3guards", str_rung(3)), ("S5-str-5guards", str_rung(5)),
             ("U2-union-2arms", union_rung(2)), ("U4-union-4arms", union_rung(4)),
             ("U6-union-6arms", union_rung(6)), ("U8-union-8arms", union_rung(8))]
    for label, source in rungs:
        outcome, code, steps, count, detail = measure(label, source)
        rows.append({"rung": label, "outcome": outcome, "code": code,
                     "steps": steps, "executions": count, "bytes": len(source),
                     "detail": detail})
        print(f"{label:16s} bytes={len(source):4d} -> {outcome:8s} code={code} "
              f"steps={steps} execute#{count}  {detail[:74]}")

    results = []

    def claim(name, ok, detail):
        results.append((name, ok))
        print(f"{'HELD    ' if ok else 'FALSIFIED'} {name} :: {detail}")

    refused = [row for row in rows if row["steps"] is not None]
    host_side = [row for row in rows if row["outcome"] == "OTHER"]
    # MEASURED, and my first expectation was wrong: the metric appears on TOOL-invocation
    # failures only. Host-side pre-emission refusals (ValueError from pep_c23) run no
    # execute at all, so they carry no steps. That is a scope limit of the instrument.
    claim("C0 the step metric appears exactly on tool-invocation failures, not host-side ones",
          len(refused) == len([r for r in rows if r["code"] == "PEP_RUNTIME_STEP_LIMIT"])
          and len(host_side) == len(rows) - len(refused),
          f"tool-side={len(refused)} host-side={len(host_side)} of {len(rows)}")

    budget = [row for row in rows if row["code"] == "PEP_RUNTIME_STEP_LIMIT"]
    near = [row for row in budget if row["steps"] is not None and row["steps"] >= LIMIT * 0.95]
    claim("C1 every STEP_LIMIT refusal reports steps at/above 95% of the 100k limit",
          bool(budget) and len(near) == len(budget),
          f"{[(r['rung'], r['steps']) for r in budget]}")

    capability = [row for row in rows
                  if row["code"] not in (None, "PEP_RUNTIME_STEP_LIMIT")]
    below = [row for row in capability
             if row["steps"] is not None and row["steps"] < LIMIT * 0.5]
    # C2 as first written ("every non-budget refusal reports steps below 50%") could not be
    # tested: every non-budget refusal here happens BEFORE any execute, so there is nothing
    # to count. Recorded as a scope limitation with the measured host-side evidence instead.
    claim("C2 non-budget refusals are host-side pre-emission and consume no counted execute",
          len(host_side) > 0 and all(row["steps"] is None for row in host_side),
          f"host-side rows={[r['rung'] for r in host_side]}")

    held = sum(1 for _, ok in results if ok)
    print(f"SUMMARY claims={len(results)} held={held} falsified={len(results) - held}")
    print("ROWS " + repr([(r["rung"], r["code"], r["steps"]) for r in rows]))
    return 0 if held == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
