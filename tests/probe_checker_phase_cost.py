"""Campaign K K2: where do interpreter steps actually go, per phase?

Read-only measurement. Nothing here changes the checker, the 100,000-step tool
budget, the 1 MiB transport cap, or any diagnostic. It uses the two additive
accounting fields added to `pep_ocaml.ml` (`metrics.last_execute_steps`,
`metrics.execute_count`) so any peer can reproduce these numbers without
instrumenting a scratch worktree.

Phases measured, each a separate `tool_invoke` (so each is a separate `execute`
with its own 100,000-step budget in the real staged pipeline):

  parser-start / parser-step         -> parse phase (per invocation)
  pep-c23-checker (analyze_parsed)   -> typecheck + semantic fact admission
                                        (the checker is Pep source; its facts are
                                        admitted inside the same execute)

`open`/`open_bytes` are session operations, not executions, so they consume no
counted tool steps. Host transport cost is bytes and wall time, never steps.

Two ladders are measured:

  recpad-k        synthetic record/constructor shapes, the frozen 62/64/66-node
                  class the frozen Full-v2 gate row is built from
  real prefix T1+ the REAL compiler-owned lexer type closure prefixes
                  (LexToken -> LexCursor -> LexProgress), reused verbatim from
                  tests/test_c23_list_record_fields.py and
                  tests/test_a13_checker_budgets.py

Usage:
  python tests/probe_checker_phase_cost.py            # both ladders
  python tests/probe_checker_phase_cost.py --ladder 8 # deeper recpad ladder

Exit code is 0 when every measurement completed. A STEP_LIMIT observation is a
measurement, not a failure of this probe.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pep_c23
from pep_c23 import require, parse_target
from tests.chunk_helper import fields_map
from tests.test_a13_checker_budgets import cumulative_type_prefixes
from tests.test_c23_list_record_fields import lexer_type_block
from tests.test_checker_cost_profile import bundle_lines, enclosing, function_spans

NL = chr(10)


class CountingSession(pep_c23.Session):
    """Session that remembers the step cost of every tool invocation."""

    def __init__(self):
        super().__init__()
        self.steps = []

    def metrics(self):
        return super().send({"schemaVersion": 3, "op": "metrics"}).get("metrics", {})

    def send(self, payload):
        response = super().send(payload)
        if isinstance(payload, dict) and payload.get("op") == "tool_invoke":
            self.steps.append(self.metrics().get("last_execute_steps"))
        return response


def recpad(k):
    """recpad-k: k record types plus k constructors, the frozen 66-node class."""
    return "".join(
        f"type P{i} {{ x: Int }}{NL}fn mk{i}(v: Int) -> P{i} {{{NL}"
        f"  return P{i} {{ x: v }}{NL}}}{NL}" for i in range(k)).encode("utf-8")


def open_tools(session):
    """Register/validate/activate the compiler's own parse and check tools."""
    bundle = NL.join(path.read_text(encoding="utf-8") for path in pep_c23.SOURCES)
    opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                           "name": "pep-c23", "metadataOnly": True})
    require(opened, "outcome", "ok", "open compiler bundle")
    document, revision = opened["document"], opened["revision"]
    sample = session.send({"schemaVersion": 3, "op": "open_bytes",
                           "name": "validate", "bytes": []})
    target = {"document": sample["document"], "revision": sample["revision"],
              "entryFunctions": []}
    finished = pep_c23.parser_cursor_value(sample["document"], sample["revision"],
                                           done=True, lex_done=True, lex_stage="done")
    for tool, function, arguments, expected in [
            ("pep-c23-parser-start", "parser_start", [],
             pep_c23.parser_cursor_value(sample["document"], sample["revision"])),
            ("pep-c23-parser-step", "parser_step", [finished],
             pep_c23.parser_chunk_value(sample["document"], sample["revision"], finished)),
            ("pep-c23-checker", "analyze_parsed",
             [pep_c23.parser_progress(sample["document"], sample["revision"])],
             pep_c23.checker_report(sample["document"], sample["revision"]))]:
        session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                      "op": "tool_register", "tool": tool,
                      "document": document, "revision": revision,
                      "function": function})
        session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                      "op": "tool_validate", "tool": tool,
                      "document": document, "revision": revision,
                      "testVectors": [{"arguments": arguments,
                                       "expect": expected,
                                       "semanticTarget": target}]})
        session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                      "op": "tool_activate", "tool": tool,
                      "document": document, "revision": revision})
    return document, revision


def measure(session, tool_revision, label, source):
    """Parse + check one fixture, returning per-phase step counts."""
    opened = session.send({"schemaVersion": 3, "op": "open_bytes",
                           "name": label, "bytes": list(source)})
    require(opened, "outcome", "ok", f"open {label}")
    target = {"document": opened["document"], "revision": opened["revision"],
              "entryFunctions": []}
    session.steps = []
    parsed = parse_target(session, source, target, tool_revision)
    nodes = session.parser_measurements["parser_node_count"]
    parse_steps = sum(step for step in session.steps if step is not None)
    parse_calls = len(session.steps)
    session.steps = []
    check = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                          "op": "tool_invoke", "tool": "pep-c23-checker",
                          "arguments": [parsed],
                          "semanticTarget": {"document": opened["document"],
                                             "revision": opened["revision"],
                                             "entryFunctions": []}})
    check_steps = session.steps[-1] if session.steps else None
    expires_in = ""
    if check.get("outcome") == "ok":
        status = fields_map(check["result"])["status"]["value"]
        detail = status
    else:
        error = check.get("error", {})
        status = error.get("code")
        detail = status
        # The budget error names a line in the concatenated compiler bundle, so
        # the enclosing function identifies where the checker gave up.
        match = error.get("message", "")
        if " at " in match:
            location = match.rsplit(" at ", 1)[1].split(":")[0]
            try:
                hit = enclosing(function_spans(bundle_lines()), int(location))
                expires_in = hit[0] if hit else ""
            except ValueError:
                expires_in = ""
    return {"label": label, "nodes": nodes, "parse_steps": parse_steps,
            "parse_calls": parse_calls, "check_steps": check_steps,
            "status": status, "detail": detail, "expires_in": expires_in}


HEADER = (f"{'fixture':<12}{'nodes':>6}{'parse_steps':>12}{'parse_calls':>12}"
          f"{'check_steps':>12}  status")


def report(rows, session):
    for row in rows:
        extra = f" [expires in {row['expires_in']}]" if row["expires_in"] else ""
        print(f"{row['label']:<12}{row['nodes']:>6}{row['parse_steps']:>12}"
              f"{row['parse_calls']:>12}{str(row['check_steps']):>12}"
              f"  {row['detail']}{extra}")


def main(argv):
    depth = 6
    if "--ladder" in argv:
        depth = int(argv[argv.index("--ladder") + 1])
    session = CountingSession()
    try:
        _, tool_revision = open_tools(session)
        print(f"# tool_revision={tool_revision[:16]} tool_budget=100000")
        print("\n# synthetic ladder (recpad-k)")
        print(HEADER)
        rows = [measure(session, tool_revision, f"recpad{k}", recpad(k))
                for k in range(1, depth + 1)]
        report(rows, session)
        ok = [row for row in rows if row["status"] == "valid"]
        if len(ok) >= 2:
            per_node = [row["check_steps"] / row["nodes"] for row in ok]
            print("\ncheck steps/node on valid fixtures: "
                  + ", ".join("%.1f" % value for value in per_node))
            print("parse steps/node on all fixtures:   "
                  + ", ".join("%.2f" % (row["parse_steps"] / max(row["nodes"], 1))
                              for row in rows))
        print("\n# real compiler-owned workload (real lexer type closure prefixes)")
        print(HEADER)
        real = [measure(session, tool_revision, label, (text + NL).encode("utf-8"))
                for label, text in cumulative_type_prefixes(lexer_type_block()).items()]
        report(real, session)
        limited = [row for row in rows + real
                   if row["status"] == "PEP_RUNTIME_STEP_LIMIT"]
        print(f"\nstep-limited fixtures: {len(limited)}"
              f"; steps consumed on those: {sorted({row['check_steps'] for row in limited})}")
        print(f"execute_count={session.metrics().get('execute_count')}")
    finally:
        session.process.stdin.close()
        session.process.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
