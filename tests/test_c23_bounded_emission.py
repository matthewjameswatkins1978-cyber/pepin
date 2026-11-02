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
            ("pep-c23-bounded-unit", "emit_c23_function_unit_bounded",
             [empty_parsed, empty_checked, typed("Int", 0)], refused_bounded_unit()),
            ("pep-c23-prerequisites", "pep_c23_unit_prerequisites",
             [pep_c23.typed_list("FlatAstNode", []), typed("Int", 0)], empty_prerequisites()),
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

    def _bounded_unit(self, parsed, checked, semantic, index):
        response = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_invoke", "tool": "pep-c23-bounded-unit",
                                      "arguments": [parsed, checked, typed("Int", index)],
                                      "semanticTarget": semantic})
        require(response, "outcome", "ok", f"bounded unit {index}")
        fields = {item["name"]: item["value"] for item in response["result"]["fields"]}
        return {
            "status": fields["status"]["value"],
            "diagnostic": fields["diagnostic"]["value"],
            "parts": [part["value"] for part in fields["sourceParts"]["value"]],
            "kinds": [item["value"] for item in fields["prerequisiteKinds"]["value"]],
            "ids": [int(item["value"]) for item in fields["prerequisiteIds"]["value"]],
            "requiresArena": fields["requiresArena"]["value"],
        }

    def test_bounded_unit_reports_declared_type_prerequisites(self):
        """A record-typed signature names its declaration as a prerequisite fact."""
        parsed, checked, semantic = self._prepare(RECORD_PARAMETER, "record-prerequisite")
        unit = self._bounded_unit(parsed, checked, semantic, 0)
        self.assertEqual(unit["status"], "emitted", unit["diagnostic"])
        self.assertEqual(unit["kinds"], ["record_declaration"])
        self.assertEqual(len(unit["ids"]), 1)
        # Provenance is source-backed: the id is the one the emitted text refers to.
        self.assertIn(f"pep_record_{unit['ids'][0]}", "".join(unit["parts"]))

    def test_bounded_unit_has_no_prerequisites_for_scalars(self):
        parsed, checked, semantic = self._prepare(SCALAR_ONLY, "scalar-prerequisite")
        unit = self._bounded_unit(parsed, checked, semantic, 0)
        self.assertEqual(unit["status"], "emitted", unit["diagnostic"])
        self.assertEqual(unit["kinds"], [])
        self.assertEqual(unit["ids"], [])

    def test_bounded_unit_text_equals_the_section_unit(self):
        """The bounded entry adds prerequisite facts, never different bytes."""
        parsed, checked, semantic = self._prepare(SUPPORTED, "bounded-text")
        for index in range(3):
            section_status, section_diagnostic, section_parts = self._unit(
                parsed, checked, semantic, index)
            self.assertEqual(section_status, "emitted", section_diagnostic)
            bounded = self._bounded_unit(parsed, checked, semantic, index)
            self.assertEqual(bounded["status"], "emitted", bounded["diagnostic"])
            self.assertEqual(bounded["parts"], section_parts)
        out_of_range = self._bounded_unit(parsed, checked, semantic, 3)
        self.assertEqual(out_of_range["status"], "unsupported")
        self.assertIn("index is out of range", out_of_range["diagnostic"])

    @staticmethod
    def _function_node_id(nodes, index):
        """The prerequisite entry point takes a source node id, not a positional index."""
        seen = 0
        for node in nodes:
            fields = {item["name"]: item["value"] for item in node["fields"]}
            if int(fields["parentId"]["value"]) == -1 and fields["kind"]["value"] == "function":
                if seen == index:
                    return int(fields["id"]["value"])
                seen += 1
        raise AssertionError(f"no top-level function at index {index}")

    def _prerequisites(self, parsed, semantic, index):
        fields = pep_c23.typed_fields(parsed, "ParserProgress", "parser progress")
        nodes = pep_c23.typed_field_value(fields, "nodes", "List[FlatAstNode]", "parser progress")
        nodes_argument = {"type": "List[FlatAstNode]", "value": nodes}
        response = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_invoke", "tool": "pep-c23-prerequisites",
                                      "arguments": [nodes_argument,
                                                    typed("Int", self._function_node_id(nodes, index))],
                                      "semanticTarget": semantic})
        require(response, "outcome", "ok", "unit prerequisites")
        result = {item["name"]: item["value"] for item in response["result"]["fields"]}
        return {
            "status": result["status"]["value"],
            "diagnostic": result["diagnostic"]["value"],
            "kinds": [item["value"] for item in result["kinds"]["value"]],
            "ids": [int(item["value"]) for item in result["nodeIds"]["value"]],
        }

    def test_prerequisite_closure_includes_nested_declaration(self):
        """Direct references are not enough: `Outer` names `Inner` in its own field list."""
        parsed, _checked, semantic = self._prepare(NESTED_RECORD, "nested-closure")
        closure = self._prerequisites(parsed, semantic, 0)
        self.assertEqual(closure["status"], "ok", closure["diagnostic"])
        self.assertEqual(len(closure["ids"]), 2)
        self.assertEqual(len(set(closure["ids"])), 2)
        self.assertEqual(closure["kinds"], ["record_declaration", "record_declaration"])


RECORD_PARAMETER = ("type Point { x: Int y: Int }\n"
                    "fn use_point(p: Point) -> Int { return p.x }\n"
                    "fn main() -> Int { return 0 }\n")

# `Outer` names `Inner` in its own field list, so a closure must report both declarations.
NESTED_RECORD = ("type Inner { value: Int }\n"
                 "type Outer { inner: Inner }\n"
                 "fn use_outer(o: Outer) -> Int { return 0 }\n"
                 "fn main() -> Int { return 0 }\n")

# `value` is the first top-level function, so index 0 selects a scalar-only signature.
SCALAR_ONLY = ("fn scalar(value: Int) -> Int { return value }\n"
               "fn main() -> Int { return 0 }\n")


def empty_prerequisites():
    """The expected record for a prerequisite query over an empty node list."""
    return pep_c23.typed_record_value("PepC23UnitPrerequisites", [
        ("status", typed("Str", "ok")),
        ("diagnostic", typed("Str", "")),
        ("kinds", pep_c23.typed_list("Str")),
        ("nodeIds", pep_c23.typed_list("Int")),
    ])


def refused_bounded_unit():
    """The expected refusal record for a bounded-unit request against an empty program."""
    return pep_c23.typed_record_value("PepC23BoundedUnit", [
        ("status", typed("Str", "unsupported")),
        ("diagnostic", typed("Str", "Pep C23 function unit index is out of range")),
        ("sourceParts", pep_c23.typed_list("Str")),
        ("prerequisiteKinds", pep_c23.typed_list("Str")),
        ("prerequisiteIds", pep_c23.typed_list("Int")),
        ("requiresArena", typed("Bool", False)),
    ])


if __name__ == "__main__":
    unittest.main()
