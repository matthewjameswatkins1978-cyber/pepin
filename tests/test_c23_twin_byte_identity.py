"""Byte-identity gate for the checked statement twin chain.

`emit_c23_function_unit` routes statement-level expression sites (while/if conditions,
loop assignments) through the checked twin chain (`pep_c23_function_definition_chunked`)
added at 689c38a, while the one-shot `emit_c23_checked` output is produced by the plain
walkers. For every whole program the plain path supports, the bounded assembly

    header + unit(0) + ... + unit(n-1) + epilogue

must equal the one-shot output byte for byte. That is the twins' equality gate: it holds
only while the twins are byte-identical copies of the plain walkers with their expression
sites merely rerouted. A divergence here means the twin chain (or a future twin edit)
changed emission semantics in a way the one-shot path would not show.

The existing `test_c23_section_identity.PROGRAMS` cover scalars, calls, records and string
comparison, but no while/if/for statement shapes — exactly the new surface the twin chain
added. This module pins those shapes, plus loops with same-chunk calls in guards and
bodies.

Grammar note, checked against this seed before use: bare `<`/`>` are NOT in the
expression grammar (`PEP_UNEXPECTED_CHARACTER` on `count < 5`); `<=` and `!=` are; a
statement-level `if` must carry an `else` (`PEP_PARSE_ELSE`). Each PROGRAM shape is
verified `valid` by `pep.ps1 check` before being pinned here.

This module drives the staged pipeline directly (parser tool, checker tool, both emitter
tools) rather than through `pep_c23.emit`, for the same reason as the section module:
the entry points under test are additional, not host-registered.
"""

import pathlib
import unittest

import pep_c23
from pep_c23 import Session, require, typed, typed_record

ROOT = pathlib.Path(__file__).resolve().parents[1]

PROGRAMS = {
    # while body assignment + call-site arithmetic in the loop body
    "while-countdown": ("fn step(a: Int) -> Int { return a + 1 }\n"
                        "fn main() -> Int {\n"
                        "  var count = 0\n"
                        "  while count <= 4 {\n"
                        "    count = step(count)\n"
                        "  }\n"
                        "  return count\n"
                        "}\n"),
    # assignment inside both if-statement branches, a call nested in the else branch
    "if-branch-call": ("fn pick(o: Bool) -> Int { return if o { 1 } else { 2 } }\n"
                       "fn main() -> Int {\n"
                       "  var result = 0\n"
                       "  var flag = true\n"
                       "  if flag {\n"
                       "    flag = false\n"
                       "  } else {\n"
                       "    result = pick(false)\n"
                       "  }\n"
                       "  return result + pick(flag)\n"
                       "}\n"),
    # for-in over a list, calls in the loop body, accumulator update
    "for-accumulator": ("fn triple(v: Int) -> Int { return v * 3 }\n"
                        "fn main() -> Int {\n"
                        "  var acc = 0\n"
                        "  for item in [1, 2, 7] {\n"
                        "    acc = triple(item) + acc\n"
                        "  }\n"
                        "  return acc\n"
                        "}\n"),
    # a helper call is the loop guard expression itself; `!=` terminates because
    # floor division of 1 is 0, so decay reaches 0 exactly
    "call-guard-loop": ("fn remaining(t: Int) -> Bool { return t != 0 }\n"
                        "fn decay(t: Int) -> Int { return t / 2 }\n"
                        "fn main() -> Int {\n"
                        "  var t = 40\n"
                        "  while remaining(t) {\n"
                        "    t = decay(t)\n"
                        "  }\n"
                        "  return t\n"
                        "}\n"),
}


class TwinChainByteIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = Session()
        bundle = "\n".join(path.read_text(encoding="utf-8") for path in pep_c23.SOURCES)
        opened = cls.session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                                   "name": "a2-twin-identity", "metadataOnly": True})
        require(opened, "outcome", "ok", "open compiler bundle")
        require(opened, "status", "valid", "check compiler bundle")
        cls.tool_document = opened["document"]
        cls.tool_revision = opened["revision"]

        empty = cls.session.send({"schemaVersion": 3, "op": "open_bytes", "name": "t", "bytes": []})
        require(empty, "outcome", "ok", "open empty target")
        target_spec = {"document": empty["document"], "revision": empty["revision"],
                       "entryFunctions": []}
        empty_parsed = pep_c23.parser_progress(empty["document"], empty["revision"])
        empty_checked = pep_c23.checker_report(empty["document"], empty["revision"])
        start_cursor = pep_c23.parser_cursor_value(empty["document"], empty["revision"])
        finished_cursor = pep_c23.parser_cursor_value(empty["document"], empty["revision"],
                                                      done=True, lex_done=True, lex_stage="done")
        unsupported = typed_record("unsupported", (),
                                   "Pep C23 emission requires a top-level function named main")
        registrations = [
            ("pep-c23-parser-start", "parser_start", [], start_cursor),
            ("pep-c23-parser-step", "parser_step", [finished_cursor],
             pep_c23.parser_chunk_value(empty["document"], empty["revision"], finished_cursor)),
            ("pep-c23-checker", "analyze_parsed", [empty_parsed], empty_checked),
            ("pep-c23-emitter", "emit_c23_checked", [empty_parsed, empty_checked], unsupported),
            ("pep-c23-section", "emit_c23_section",
             [empty_parsed, empty_checked, typed("Str", "header")], unsupported),
            ("pep-c23-function-unit", "emit_c23_function_unit",
             [empty_parsed, empty_checked, typed("Int", 0)], unsupported),
        ]
        for tool, function, arguments, expected in registrations:
            registered = cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                           "op": "tool_register", "tool": tool,
                                           "document": cls.tool_document,
                                           "revision": cls.tool_revision, "function": function})
            require(registered, "status", "Registered", f"register {tool}")
            validated = cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                          "op": "tool_validate", "tool": tool,
                                          "document": cls.tool_document,
                                          "revision": cls.tool_revision,
                                          "testVectors": [{"arguments": arguments,
                                                           "expect": expected,
                                                           "semanticTarget": target_spec}]})
            require(validated, "status", "Validated", f"validate {tool}")
            activated = cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                          "op": "tool_activate", "tool": tool,
                                          "document": cls.tool_document,
                                          "revision": cls.tool_revision})
            require(activated, "status", "Active", f"activate {tool}")

    @classmethod
    def tearDownClass(cls):
        cls.session.process.stdin.close()
        cls.session.process.terminate()

    def emit_units(self, source_text):
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                    "name": "target", "bytes": list(source_text.encode("utf-8"))})
        require(target, "outcome", "ok", "open target")
        semantic_target = {"document": target["document"], "revision": target["revision"],
                           "entryFunctions": []}
        parsed = pep_c23.parse_target(self.session, source_text.encode("utf-8"), target,
                                      self.tool_revision)
        checked = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                     "op": "tool_invoke", "tool": "pep-c23-checker",
                                     "arguments": [parsed], "semanticTarget": semantic_target})
        require(checked, "outcome", "ok", "check target")

        def emit_fields(tool, arguments):
            response = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                          "op": "tool_invoke", "tool": tool,
                                          "arguments": arguments,
                                          "semanticTarget": semantic_target})
            require(response, "outcome", "ok", f"invoke {tool}")
            fields = {item["name"]: item["value"] for item in response["result"]["fields"]}
            return (fields["status"]["value"], fields["diagnostic"]["value"],
                    "".join(part["value"] for part in fields["sourceParts"]["value"]))

        def emit_with(tool, arguments):
            status, diagnostic, text = emit_fields(tool, arguments)
            self.assertEqual(status, "emitted", diagnostic)
            return text

        one_shot = emit_with("pep-c23-emitter", [parsed, checked["result"]])
        sections = [emit_with("pep-c23-section", [parsed, checked["result"], typed("Str", part)])
                    for part in ("header", "function", "main")]
        units = []
        for index in range(self.function_count(source_text)):
            response = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                          "op": "tool_invoke", "tool": "pep-c23-function-unit",
                                          "arguments": [parsed, checked["result"],
                                                        typed("Int", index)],
                                          "semanticTarget": semantic_target})
            require(response, "outcome", "ok", f"emit unit {index}")
            fields = {item["name"]: item["value"] for item in response["result"]["fields"]}
            self.assertEqual(fields["status"]["value"], "emitted",
                             f"unit {index} refused: {fields['diagnostic']['value']}")
            units.append("".join(part["value"] for part in fields["sourceParts"]["value"]))
        return one_shot, sections, units

    def function_count(self, source_text):
        return sum(1 for line in source_text.split("\n") if line.startswith("fn "))

    def test_twin_units_concatenate_to_the_one_shot_output(self):
        """The twins' equality gate on the statement-level shapes they were added for."""
        for name, source in PROGRAMS.items():
            with self.subTest(program=name):
                one_shot, sections, units = self.emit_units(source)
                header, _, epilogue = sections
                self.assertEqual(self.function_count(source), len(units))
                self.assertEqual(header + "".join(units) + epilogue, one_shot)

    def test_statement_shapes_are_actually_supported_by_the_one_shot_path(self):
        """Guard against a vacuous pass: both paths must really emit, not both refuse."""
        for name, source in PROGRAMS.items():
            with self.subTest(program=name):
                one_shot, sections, units = self.emit_units(source)
                self.assertIn("int main(", one_shot)
                self.assertNotIn("unsupported", one_shot)
                self.assertTrue(all("pep_fn_" in unit for unit in units))


if __name__ == "__main__":
    unittest.main()
