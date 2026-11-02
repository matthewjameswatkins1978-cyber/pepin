"""The bounded-emitter property: a function unit must depend on its own function only.

`docs/C23_BOUNDED_EMITTER_CONTRACT.md` accepted sectional emission, and the 2 November
packet made the remaining requirement explicit: a `function-unit` request must not pay
for the rest of the program. Before this slice the entry point built the whole program
(headers, every typedef, every prototype, every other function body, the epilogue) and
then sliced one function out of the accumulator, so a unit request cost the same as
whole-program emission.

These tests pin the property in a way that does not depend on wall-clock timing:

* a unit request on a program whose *other* function cannot be lowered still emits the
  requested unit -- if the request lowered its peers, it would fail closed with theirs;
* header + every unit + epilogue reassembles to the one-shot output byte for byte;
* an out-of-range index fails closed rather than inventing a unit.

Timing and scaling are measured outside the suite (`tests/probe_c23_sections.py`); they are
evidence for reviewers, not assertions, because a wall-clock ratio is not stable enough to
gate a merge.
"""

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target, typed, typed_record  # noqa: E402

SUPPORTED = ("fn helper_first() -> Int { return 1 }\n"
             "fn helper_second() -> Int { return 2 }\n"
             "fn main() -> Int { return helper_first() }\n")

# `bad` is accepted by the checker but has no C23 lowering (Str result).
MIXED = ("fn good() -> Int { return 1 }\n"
         "fn bad() -> Str { return \"a\" }\n"
         "fn main() -> Int { return good() }\n")


def emission_of(response):
    fields = {item["name"]: item["value"] for item in response["result"]["fields"]}
    status = fields["status"]["value"]
    parts = [part["value"] for part in fields["sourceParts"]["value"]]
    return status, fields["diagnostic"]["value"], parts


class BoundedEmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = Session()
        bundle = "\n".join(path.read_text(encoding="utf-8") for path in pep_c23.SOURCES)
        opened = cls.session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                                   "name": "pep-c23-emitter", "metadataOnly": True})
        require(opened, "outcome", "ok", "open compiler bundle")
        require(opened, "status", "valid", "check compiler bundle")
        cls.tool_document = opened["document"]
        cls.tool_revision = opened["revision"]
        cls.sample = cls.session.send({"schemaVersion": 3, "op": "open_bytes",
                                       "name": "stage-validation", "bytes": []})
        require(cls.sample, "outcome", "ok", "open validation source")
        cls._register()

    @classmethod
    def _register(cls):
        document, revision = cls.tool_document, cls.tool_revision
        sample_document = cls.sample["document"]
        sample_revision = cls.sample["revision"]
        target_spec = {"document": sample_document, "revision": sample_revision,
                       "entryFunctions": []}
        empty_parsed = pep_c23.parser_progress(sample_document, sample_revision)
        empty_checked = pep_c23.checker_report(sample_document, sample_revision)
        refused = typed_record("unsupported", (),
                               "Pep C23 emission requires a top-level function named main")
        start_cursor = pep_c23.parser_cursor_value(sample_document, sample_revision)
        finished_cursor = pep_c23.parser_cursor_value(sample_document, sample_revision,
                                                      done=True, lex_done=True, lex_stage="done")
        tools = [
            ("pep-c23-parser-start", "parser_start", [], start_cursor),
            ("pep-c23-parser-step", "parser_step", [finished_cursor],
             pep_c23.parser_chunk_value(sample_document, sample_revision, finished_cursor)),
            ("pep-c23-checker", "analyze_parsed", [empty_parsed], empty_checked),
            ("pep-c23-emitter", "emit_c23_checked", [empty_parsed, empty_checked], refused),
            ("pep-c23-section", "emit_c23_section",
             [empty_parsed, empty_checked, typed("Str", "header")], refused),
            ("pep-c23-unit", "emit_c23_function_unit",
             [empty_parsed, empty_checked, typed("Int", 0)], refused),
        ]
        for tool, function, arguments, expect in tools:
            registered = cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                           "op": "tool_register", "tool": tool,
                                           "document": document, "revision": revision,
                                           "function": function})
            require(registered, "status", "Registered", f"register {tool}")
            validated = cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                          "op": "tool_validate", "tool": tool,
                                          "document": document, "revision": revision,
                                          "testVectors": [{"arguments": arguments, "expect": expect,
                                                           "semanticTarget": target_spec}]})
            require(validated, "status", "Validated", f"validate {tool}")
            activated = cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                          "op": "tool_activate", "tool": tool,
                                          "document": document, "revision": revision})
            require(activated, "status", "Active", f"activate {tool}")

    @classmethod
    def tearDownClass(cls):
        cls.session.close()

    def _prepare(self, source, name):
        payload = source.encode("utf-8")
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                    "name": name, "bytes": list(payload)})
        require(target, "outcome", "ok", "open target")
        semantic = {"document": target["document"], "revision": target["revision"],
                    "entryFunctions": []}
        parsed = parse_target(self.session, payload, target, self.tool_revision)
        checked = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                     "op": "tool_invoke", "tool": "pep-c23-checker",
                                     "arguments": [parsed], "semanticTarget": semantic})
        require(checked, "outcome", "ok", "check target")
        return parsed, checked["result"], semantic

    def _section(self, parsed, checked, semantic, part):
        response = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_invoke", "tool": "pep-c23-section",
                                      "arguments": [parsed, checked, typed("Str", part)],
                                      "semanticTarget": semantic})
        require(response, "outcome", "ok", f"section {part}")
        return emission_of(response)

    def _unit(self, parsed, checked, semantic, index):
        response = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_invoke", "tool": "pep-c23-unit",
                                      "arguments": [parsed, checked, typed("Int", index)],
                                      "semanticTarget": semantic})
        require(response, "outcome", "ok", f"unit {index}")
        return emission_of(response)

    def test_unit_does_not_lower_peer_functions(self):
        """The bounded property: a peer that cannot be lowered must not block this unit."""
        parsed, checked, semantic = self._prepare(MIXED, "mixed")
        whole = self._section(parsed, checked, semantic, "all")
        self.assertEqual(whole[0], "unsupported")
        self.assertIn("scalar or record results", whole[1])

        status, diagnostic, parts = self._unit(parsed, checked, semantic, 0)
        self.assertEqual(status, "emitted", diagnostic)
        emitted = "".join(parts)
        self.assertIn("int64_t pep_fn_", emitted)

        # The unsupported peer reports its own diagnostic, and nothing else does.
        peer_status, peer_diagnostic, peer_parts = self._unit(parsed, checked, semantic, 1)
        self.assertEqual(peer_status, "unsupported")
        self.assertIn("scalar or record results", peer_diagnostic)
        self.assertEqual(peer_parts, [])

    def test_sections_reassemble_to_the_one_shot_output(self):
        parsed, checked, semantic = self._prepare(SUPPORTED, "supported")
        status, diagnostic, whole = self._section(parsed, checked, semantic, "all")
        self.assertEqual(status, "emitted", diagnostic)
        header_status, header_diagnostic, header = self._section(parsed, checked, semantic, "header")
        self.assertEqual(header_status, "emitted", header_diagnostic)
        main_status, main_diagnostic, epilogue = self._section(parsed, checked, semantic, "main")
        self.assertEqual(main_status, "emitted", main_diagnostic)

        rebuilt = list(header)
        for index in range(3):
            unit_status, unit_diagnostic, unit = self._unit(parsed, checked, semantic, index)
            self.assertEqual(unit_status, "emitted", unit_diagnostic)
            rebuilt.extend(unit)
        rebuilt.extend(epilogue)
        self.assertEqual(rebuilt, whole)

    def test_out_of_range_unit_fails_closed(self):
        parsed, checked, semantic = self._prepare(SUPPORTED, "supported-range")
        status, diagnostic, parts = self._unit(parsed, checked, semantic, 3)
        self.assertEqual(status, "unsupported")
        self.assertIn("index is out of range", diagnostic)
        self.assertEqual(parts, [])


if __name__ == "__main__":
    unittest.main()
