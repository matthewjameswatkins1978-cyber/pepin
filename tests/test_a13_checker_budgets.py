"""Checker step-budget boundaries on real lexer type closures (A1-1).

Uses the REAL C23 pipeline stages (pep_c23: host-driven staged parse,
then ONE analyze_parsed invocation under the unchanged 100k step
budget), so every boundary here is the exact production failure mode,
not a synthetic harness artifact.

Current pins (to be flipped to valid by the A1-2 repair):
- T5 (SourcePosition..LexProgress closure): PEP_RUNTIME_STEP_LIMIT
- R32 (32 trivial records): PEP_RUNTIME_STEP_LIMIT

Stable asserts regardless of repair: every fixture is OCaml-valid
(semantic acceptance, not a budget artifact) and T1-T4/R8/R16 check
valid today.

Do NOT raise any budget to make these pass; a passing boundary must
come from cheaper checking.
"""
import json
import pathlib
import subprocess
import unittest

from pep_c23 import Session, require, parse_target
import pep_c23
from tests.test_c23_list_record_fields import lexer_type_block

ROOT = pathlib.Path(__file__).resolve().parents[1]
NL = chr(10)


def cumulative_type_prefixes(block_text):
    blocks, current = [], []
    for line in block_text.split(NL):
        if (line.startswith("type ") or line.startswith("fn ")) and current:
            blocks.append(NL.join(current))
            current = [line]
        else:
            current.append(line)
    blocks.append(NL.join(current))
    type_blocks = [b for b in blocks if b.startswith("type ")]
    out, acc = {}, ""
    for i, b in enumerate(type_blocks):
        acc = (acc + NL + b).strip() + NL
        out[f"T{i + 1}"] = acc
    return out


def ocaml_check(source):
    with open(ROOT / "_build" / "budget_target.pep", "w",
              encoding="utf-8", newline="\n") as fh:
        fh.write(source)
    proc = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"), "check",
         str(ROOT / "_build" / "budget_target.pep"), "--json"],
        cwd=ROOT, text=True, capture_output=True, check=False)
    return json.loads(proc.stdout).get("status")


class CheckerBudgetBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = Session()
        bundle = NL.join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = cls.session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                                    "name": "pep-c23", "metadataOnly": True})
        require(opened, "outcome", "ok", "open compiler bundle")
        cls.tool_revision = opened["revision"]
        tool_document = opened["document"]
        sample = cls.session.send({"schemaVersion": 3, "op": "open_bytes",
                                    "name": "validate", "bytes": []})
        target_spec = {"document": sample["document"], "revision": sample["revision"],
                       "entryFunctions": []}
        start_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"])
        finished_cursor = pep_c23.parser_cursor_value(
            sample["document"], sample["revision"],
            done=True, lex_done=True, lex_stage="done")
        for tool, function, arguments, expected in [
                ("pep-c23-parser-start", "parser_start", [], start_cursor),
                ("pep-c23-parser-step", "parser_step", [finished_cursor],
                 pep_c23.parser_chunk_value(sample["document"], sample["revision"],
                                            finished_cursor)),
                ("pep-c23-checker", "analyze_parsed",
                 [pep_c23.parser_progress(sample["document"], sample["revision"])],
                 pep_c23.checker_report(sample["document"], sample["revision"]))]:
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_register",
                              "tool": tool, "document": tool_document,
                              "revision": cls.tool_revision, "function": function})
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_validate",
                              "tool": tool, "document": tool_document,
                              "revision": cls.tool_revision,
                              "testVectors": [{"arguments": arguments, "expect": expected,
                                                "semanticTarget": target_spec}]})
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_activate",
                              "tool": tool, "document": tool_document,
                              "revision": cls.tool_revision})
        prefixes = cumulative_type_prefixes(lexer_type_block())
        cls.fixtures = dict(prefixes)
        for n in (8, 16, 32, 48, 96):
            cls.fixtures[f"R{n}"] = (
                NL.join(f"type R{i} {{ f: Int }}" for i in range(n)) + NL)

    @classmethod
    def tearDownClass(cls):
        cls.session.process.stdin.close()
        cls.session.process.terminate()

    def invoke_checker(self, source):
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                    "name": "boundary-target",
                                    "bytes": list(source.encode("utf-8"))})
        self.assertEqual(target.get("outcome"), "ok", target)
        semantic_target = {"document": target["document"], "revision": target["revision"],
                           "entryFunctions": []}
        parsed = parse_target(self.session, source.encode("utf-8"), target, self.tool_revision)
        return self.session.send(
            {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
             "tool": "pep-c23-checker", "arguments": [parsed],
             "semanticTarget": semantic_target})

    def assert_ocaml_valid(self, source):
        self.assertEqual(ocaml_check(source), "valid",
                         "OCaml oracle must accept the fixture (else it is not a budget boundary)")

    def report_status(self, result):
        self.assertEqual(result.get("outcome"), "ok", result)
        fields = {item["name"]: item["value"] for item in result["result"]["fields"]}
        status = fields["status"]
        return status["value"] if isinstance(status, dict) else status

    def test_small_closures_check_valid(self):
        for label in ("T1", "T2", "T3", "T4", "R8", "R16"):
            with self.subTest(fixture=label):
                source = self.fixtures[label]
                self.assert_ocaml_valid(source)
                self.assertEqual(self.report_status(self.invoke_checker(source)), "valid")

    def test_lexprogress_closure_checks_valid(self):
        # A2's production failure (A2N-20261031-002), repaired by the
        # single-pass record-field resolution: the real LexToken/LexCursor/
        # LexProgress closure now checks valid under the unchanged 100k budget.
        source = self.fixtures["T5"]
        self.assert_ocaml_valid(source)
        result = self.invoke_checker(source)
        self.assertEqual(result.get("outcome"), "ok", result)
        self.assertEqual(self.report_status(result), "valid")

    def test_real_function_body_hits_step_budget(self):
        # Next frontier (A1-5): real function bodies with conditional logic
        # (stdlib collections shape) still exceed the unchanged budget.
        # Bisection: params/lets/plain-for pass; the if-expression with a
        # compound boolean condition is the cliff. Flip to valid when the
        # expression-inference path is staged or memoized.
        source = ("fn list_int_min_between(values: List[Int], lower: Int, upper: Int, fallback: Int) -> Int {\n"
                  "  var found = false\n"
                  "  var minimum = fallback\n"
                  "  for item in values {\n"
                  "    minimum = if lower <= item && item <= upper && (!found || item <= minimum) { item } else { minimum }\n"
                  "    found = found || (lower <= item && item <= upper)\n"
                  "  }\n"
                  "  return minimum\n"
                  "}\n"
                  "fn main() -> Int {\n"
                  "  return list_int_min_between([1, 2, 3], 1, 3, 9)\n"
                  "}\n")
        self.assert_ocaml_valid(source)
        result = self.invoke_checker(source)
        self.assertEqual(result.get("outcome"), "error", result)
        self.assertEqual(result.get("error", {}).get("code"), "PEP_RUNTIME_STEP_LIMIT")

    def test_real_make_token_checks_valid(self):
        # Structural win (d158044): the real 8-parameter make_token
        # constructor with 8-field record construction now checks valid
        # via resolved-record field consults (was PEP_RUNTIME_STEP_LIMIT).
        decl = ("type LexToken {\n  kind: Str, text: Str, integerValue: Int, stringParts: List[Str],\n"
                "  startByte: Int, endByte: Int, line: Int, column: Int\n}\n")
        params = ", ".join(["kind: Str", "text: Str", "integerValue: Int", "stringParts: List[Str]",
                              "startByte: Int", "endByte: Int", "line: Int", "column: Int"])
        args = ", ".join(["kind: kind", "text: text", "integerValue: integerValue",
                            "stringParts: stringParts", "startByte: startByte", "endByte: endByte",
                            "line: line", "column: column"])
        source = decl + f"fn make_token({params}) -> LexToken {{\n  return LexToken {{ {args} }}\n}}\n"
        self.assert_ocaml_valid(source)
        result = self.invoke_checker(source)
        self.assertEqual(result.get("outcome"), "ok", result)
        self.assertEqual(self.report_status(result), "valid")

    def test_sixteen_literal_args_hit_step_budget(self):
        # Documented frontier: 16-argument calls exceed the unchanged
        # 100k budget (per-arg signature + inference scans); 8 args fit.
        # Flip to valid when call-arg checking is staged or memoized.
        params = ", ".join(f"p{i}: Int" for i in range(16))
        args = ", ".join(str(i) for i in range(16))
        source = (f"fn f16({params}) -> Int {{\n  return 0\n}}\n"
                  f"fn main() -> Int {{\n  return f16({args})\n}}\n")
        self.assert_ocaml_valid(source)
        result = self.invoke_checker(source)
        self.assertEqual(result.get("outcome"), "error", result)
        self.assertEqual(result.get("error", {}).get("code"), "PEP_RUNTIME_STEP_LIMIT")

    def test_thirty_two_records_check_valid(self):
        # Scale pin flipped by the global single-pass record resolution:
        # 32 trivial records now check valid under the unchanged budget.
        source = self.fixtures["R32"]
        self.assert_ocaml_valid(source)
        result = self.invoke_checker(source)
        self.assertEqual(result.get("outcome"), "ok", result)
        self.assertEqual(self.report_status(result), "valid")

    def test_make_token_constructor_hits_step_budget(self):
        # A2's key reproducer (native make_token): 8-param constructor with
        # List field + record construction. Declaration alone checks valid;
        # the full constructor exceeds the unchanged budget.
        # Flip to valid when per-construct check cost drops further.
        mk = ("type LexToken { kind: Str, text: Str, integerValue: Int, "
              "stringParts: List[Str], startByte: Int, endByte: Int, line: Int, column: Int }\n"
              "fn make_token(kind: Str, text: Str, integerValue: Int, stringParts: List[Str], startByte: Int, endByte: Int, line: Int, column: Int) -> LexToken {\n"
              "  return LexToken { kind: kind, text: text, integerValue: integerValue, stringParts: stringParts, startByte: startByte, endByte: endByte, line: line, column: column }\n"
              "}\n"
              "fn main() -> Int { let t = make_token(\"s\", \"hi\", 7, [\"ab\", \"cd\"], 3, 9, 1, 4) return length(t.stringParts) }\n")
        self.assert_ocaml_valid(mk)
        result = self.invoke_checker(mk)
        self.assertEqual(result.get("outcome"), "error", result)
        self.assertEqual(result.get("error", {}).get("code"), "PEP_RUNTIME_STEP_LIMIT")

    def test_large_scales_hit_step_budget(self):
        # Documented frontier: 48+ trivial records still exceed the
        # unchanged 100k budget. Flip each to a valid-assertion when the
        # next composition repair lands it.
        for label in ("R48", "R96"):
            with self.subTest(fixture=label):
                source = self.fixtures[label]
                self.assert_ocaml_valid(source)
                result = self.invoke_checker(source)
                self.assertEqual(result.get("outcome"), "error", result)
                self.assertEqual(result.get("error", {}).get("code"), "PEP_RUNTIME_STEP_LIMIT")

    def test_nominal_empty_list_with_annotation_checks_valid(self):
        # A2 divergence (bc324100): OCaml-valid mutable List[record]
        # binding was rejected with PEP_EMPTY_LIST_NEEDS_TYPE. The empty
        # list inherits a concrete list type from a list-shaped annotation,
        # including nominal element types. All three use shapes pass.
        decl = "type P { x: Int }\n"
        for label, body in (
            ("length", "  var points: List[P] = []\n  return length(points)\n"),
            ("reverse", "  var points: List[P] = []\n  return length(reverse(points))\n"),
            ("prepend", "  var points: List[P] = []\n  points = prepend(points, P { x: 1 })\n  return length(points)\n"),
        ):
            with self.subTest(use=label):
                source = decl + "fn main() -> Int {\n" + body + "}\n"
                self.assert_ocaml_valid(source)
                result = self.invoke_checker(source)
                self.assertEqual(result.get("outcome"), "ok", result)
                self.assertEqual(self.report_status(result), "valid")


if __name__ == "__main__":
    unittest.main()
