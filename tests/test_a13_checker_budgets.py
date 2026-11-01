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
        for n in (8, 16, 32):
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

    def test_thirty_two_records_hit_step_budget(self):
        # Scale pin: 32 trivial one-field records exceed the unchanged budget.
        source = self.fixtures["R32"]
        self.assert_ocaml_valid(source)
        result = self.invoke_checker(source)
        self.assertEqual(result.get("outcome"), "error", result)
        self.assertEqual(result.get("error", {}).get("code"), "PEP_RUNTIME_STEP_LIMIT")


if __name__ == "__main__":
    unittest.main()
