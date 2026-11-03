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
import shutil
import subprocess
import sys
import tempfile
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
        cls.temp = tempfile.TemporaryDirectory(prefix="pep-c23-bounded-")
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
            ("pep-c23-declarations-check", "pep_c23_unit_declarations_check",
             [pep_c23.typed_list("FlatAstNode", []), typed("Int", 0)], ok_declarations()),
            ("pep-c23-declaration-unit", "emit_c23_declaration_unit",
             [empty_parsed, empty_checked, typed("Int", 0)], refused_declaration_unit()),
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
        cls.temp.cleanup()

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

    def _declarations_check(self, parsed, semantic, index):
        fields = pep_c23.typed_fields(parsed, "ParserProgress", "parser progress")
        nodes = pep_c23.typed_field_value(fields, "nodes", "List[FlatAstNode]", "parser progress")
        response = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_invoke", "tool": "pep-c23-declarations-check",
                                      "arguments": [{"type": "List[FlatAstNode]", "value": nodes},
                                                    typed("Int", self._function_node_id(nodes, index))],
                                      "semanticTarget": semantic})
        require(response, "outcome", "ok", "declarations check")
        result = {item["name"]: item["value"] for item in response["result"]["fields"]}
        return {"status": result["status"]["value"], "diagnostic": result["diagnostic"]["value"]}

    def _declaration_unit(self, parsed, checked, semantic, node_id):
        response = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_invoke", "tool": "pep-c23-declaration-unit",
                                      "arguments": [parsed, checked, typed("Int", node_id)],
                                      "semanticTarget": semantic})
        require(response, "outcome", "ok", f"declaration unit {node_id}")
        return emission_of(response)

    @staticmethod
    def _declaration_node_ids(nodes):
        ids = []
        for node in nodes:
            fields = {item["name"]: item["value"] for item in node["fields"]}
            if int(fields["parentId"]["value"]) == -1 and fields["kind"]["value"] in (
                    "record_declaration", "union_declaration"):
                ids.append(int(fields["id"]["value"]))
        return ids

    def test_first_refusal_text_matches_emission_for_a_union_of_an_empty_record(self):
        """CR3: the check must relay the rule emission would actually report first.

        Emission lowers every record before any union, so a source with both an empty record and a
        union over it fails at the record. A closure-order walk reached the union first and reported
        its layout rule instead -- verdict right, explanation wrong, which is exactly what a caller
        would relay to a user.
        """
        parsed, checked, semantic = self._prepare(UNION_EMPTY, "union-empty")
        whole_status, whole_diagnostic, whole_parts = self._section(parsed, checked, semantic, "all")
        self.assertEqual(whole_status, "unsupported")
        self.assertIn("empty records", whole_diagnostic)
        self.assertEqual(whole_parts, [])

        check = self._declarations_check(parsed, semantic, 0)
        self.assertEqual(check["status"], "unsupported")
        self.assertEqual(check["diagnostic"], whole_diagnostic,
                         "the check must report the same first refusal as emission")

    def test_header_and_main_do_not_run_the_body_loop(self):
        """Deterministic form of the boundedness claim, without depending on the step budget.

        A program with an unsupported function body cannot be emitted whole, but its header (types
        and prototypes) and its epilogue do not depend on any body. If either still assembled the
        bodies first, both would fail closed with the body's diagnostic instead of emitting.
        """
        parsed, checked, semantic = self._prepare(MIXED, "section-boundedness")
        whole_status, whole_diagnostic, whole_parts = self._section(parsed, checked, semantic, "all")
        self.assertEqual(whole_status, "unsupported")
        self.assertIn("scalar or record results", whole_diagnostic)
        self.assertEqual(whole_parts, [])

        header_status, header_diagnostic, header_parts = self._section(parsed, checked, semantic, "header")
        self.assertEqual(header_status, "emitted", header_diagnostic)
        header_text = "".join(header_parts)
        self.assertIn("int64_t pep_fn_", header_text)
        self.assertTrue(header_text.endswith(";\n"), "a header ends at the last prototype")

        epilogue_status, epilogue_diagnostic, epilogue_parts = self._section(parsed, checked, semantic, "main")
        self.assertEqual(epilogue_status, "emitted", epilogue_diagnostic)
        epilogue_text = "".join(epilogue_parts)
        self.assertIn("int main(void)", epilogue_text)
        self.assertNotIn("int64_t pep_fn_", epilogue_text, "the epilogue is not the definitions")

    def test_declaration_unit_emits_one_declaration_without_the_header(self):
        """A caller needing one typedef must not have to take the whole header.

        The declaration unit's text has to be the same bytes the header contributes for that
        declaration, or assembling units plus declarations would drift from one-shot emission.
        """
        parsed, checked, semantic = self._prepare(UNION_AND_RECORD, "declaration-unit")
        header_status, header_diagnostic, header_parts = self._section(parsed, checked, semantic, "header")
        self.assertEqual(header_status, "emitted", header_diagnostic)
        header_text = "".join(header_parts)
        fields = pep_c23.typed_fields(parsed, "ParserProgress", "parser progress")
        nodes = pep_c23.typed_field_value(fields, "nodes", "List[FlatAstNode]", "parser progress")
        ids = self._declaration_node_ids(nodes)
        self.assertEqual(len(ids), 2, ids)

        for node_id in ids:
            status, diagnostic, parts = self._declaration_unit(parsed, checked, semantic, node_id)
            self.assertEqual(status, "emitted", diagnostic)
            text = "".join(parts)
            self.assertTrue(text.strip())
            self.assertIn(text, header_text, "declaration text must match the header bytes")
            self.assertLess(len(text), len(header_text), "a declaration is smaller than the header")

        function_id = self._function_node_id(nodes, 0)
        status, diagnostic, parts = self._declaration_unit(parsed, checked, semantic, function_id)
        self.assertEqual(status, "unsupported")
        self.assertIn("record or union declaration", diagnostic)
        self.assertEqual(parts, [])

        missing = self._declaration_unit(parsed, checked, semantic, 999999)
        self.assertEqual(missing[0], "unsupported")
        self.assertEqual(missing[2], [])

    def test_prerequisite_emittability_is_answerable_without_emitting(self):
        """A caller can decide whether a prerequisite lowers without running whole-program emission.

        This is the gap slice 3 left open. The empty record is the proof case: the checker accepts
        it, the emitter cannot lower it, and a caller holding only facts would assemble C that
        references a typedef nobody emits.
        """
        parsed, checked, semantic = self._prepare(RECORD_PARAMETER, "emittable-record")
        supported = self._declarations_check(parsed, semantic, 0)
        self.assertEqual(supported["status"], "ok", supported["diagnostic"])

        parsed, checked, semantic = self._prepare(EMPTY_RECORD, "unemittable-record")
        unsupported = self._declarations_check(parsed, semantic, 0)
        self.assertEqual(unsupported["status"], "unsupported")
        self.assertIn("empty records", unsupported["diagnostic"])

        closure = self._prerequisites(parsed, semantic, 0)
        self.assertEqual(closure["status"], "ok", closure["diagnostic"])
        self.assertEqual(closure["kinds"], ["record_declaration"])

        # The unit itself still emits: bounded emission is per function, so the fact that a
        # prerequisite cannot be lowered has to come from the check, not from the unit's status.
        unit = self._bounded_unit(parsed, checked, semantic, 0)
        self.assertEqual(unit["status"], "emitted", unit["diagnostic"])
        self.assertIn(f"pep_record_{closure['ids'][0]}", "".join(unit["parts"]))

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

    def test_reassembled_unit_output_compiles_and_runs_under_clang_and_gcc(self):
        """Byte identity is not the same claim as compilable output, so compile what a caller assembles.

        A chunked caller never sees the one-shot text: it concatenates header + units + epilogue.
        This compiles exactly that, under strict warnings-as-errors, runs it, and compares the result
        with the Pep interpreter reference for the same source.
        """
        compilers = [name for name in ("clang", "gcc") if shutil.which(name)]
        if not compilers:
            self.skipTest("no C23 compiler on PATH")

        parsed, checked, semantic = self._prepare(PARITY, "parity")
        whole_status, whole_diagnostic, whole = self._section(parsed, checked, semantic, "all")
        self.assertEqual(whole_status, "emitted", whole_diagnostic)
        header_status, header_diagnostic, header_parts = self._section(
            parsed, checked, semantic, "header")
        self.assertEqual(header_status, "emitted", header_diagnostic)
        epilogue_status, epilogue_diagnostic, epilogue_parts = self._section(
            parsed, checked, semantic, "main")
        self.assertEqual(epilogue_status, "emitted", epilogue_diagnostic)

        assembled = list(header_parts)
        for index in range(2):
            unit_status, unit_diagnostic, unit_parts = self._unit(parsed, checked, semantic, index)
            self.assertEqual(unit_status, "emitted", unit_diagnostic)
            assembled.extend(unit_parts)
        assembled.extend(epilogue_parts)
        self.assertEqual(assembled, whole, "assembled sections must equal one-shot emission")

        reference = self._interpreter_reference(PARITY)
        self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
        self.assertEqual(reference.stdout, "42\n")

        generated = pathlib.Path(self.temp.name) / "assembled.c"
        generated.write_text("".join(assembled), encoding="utf-8", newline="\n")
        for name in compilers:
            with self.subTest(compiler=name):
                executable = pathlib.Path(self.temp.name) / f"assembled-{name}.exe"
                built = subprocess.run(
                    [shutil.which(name), "-std=c23", "-Wall", "-Wextra", "-Wpedantic", "-Werror",
                     "-O2", str(generated), "-o", str(executable)],
                    text=True, capture_output=True, check=False)
                self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
                ran = subprocess.run([str(executable)], text=True, capture_output=True, check=False)
                self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
                self.assertEqual(ran.stdout, reference.stdout)

    def test_self_referential_union_closure_terminates(self):
        """A recursive union names itself: the closure must dedupe by identity, not by depth."""
        parsed, checked, semantic = self._prepare(RECURSIVE_UNION, "recursive-union")
        closure = self._prerequisites(parsed, semantic, 0)
        self.assertEqual(closure["status"], "ok", closure["diagnostic"])
        self.assertEqual(len(closure["ids"]), 1, closure)
        self.assertEqual(closure["kinds"], ["union_declaration"])
        # Whatever the emitter supports here, refusal must stay closed and explicit.
        unit = self._bounded_unit(parsed, checked, semantic, 0)
        if unit["status"] == "emitted":
            self.assertTrue("".join(unit["parts"]).strip())
        else:
            self.assertEqual(unit["parts"], [])
            self.assertNotEqual(unit["diagnostic"], "")

    def test_mutually_recursive_union_closure_reports_both_and_stops(self):
        parsed, checked, semantic = self._prepare(MUTUAL_UNION, "mutual-union")
        closure = self._prerequisites(parsed, semantic, 0)
        self.assertEqual(closure["status"], "ok", closure["diagnostic"])
        self.assertEqual(len(closure["ids"]), 2, closure)
        self.assertEqual(len(set(closure["ids"])), 2)
        self.assertEqual(closure["kinds"], ["union_declaration", "union_declaration"])

    def test_forward_declared_type_resolves_in_prerequisites(self):
        """Declaration order must not decide whether a prerequisite is found."""
        parsed, checked, semantic = self._prepare(FORWARD_TYPE, "forward-type")
        closure = self._prerequisites(parsed, semantic, 0)
        self.assertEqual(closure["status"], "ok", closure["diagnostic"])
        self.assertEqual(closure["kinds"], ["record_declaration"])
        self.assertEqual(len(closure["ids"]), 1)
        unit = self._bounded_unit(parsed, checked, semantic, 0)
        if unit["status"] == "emitted":
            self.assertIn(f"pep_record_{closure['ids'][0]}", "".join(unit["parts"]))

    def test_index_arguments_and_node_id_arguments_are_not_interchangeable(self):
        """Pin the two argument spaces: unit entries take a function index, prerequisites take a
        source node id. Passing an index where an id belongs selects a declaration silently."""
        parsed, _checked, semantic = self._prepare(RECORD_PARAMETER, "argument-spaces")
        closure = self._prerequisites(parsed, semantic, 0)
        self.assertEqual(closure["status"], "ok", closure["diagnostic"])
        self.assertEqual(closure["kinds"], ["record_declaration"])
        declaration_id = closure["ids"][0]
        function_id = self._function_node_id(
            pep_c23.typed_field_value(
                pep_c23.typed_fields(parsed, "ParserProgress", "parser progress"),
                "nodes", "List[FlatAstNode]", "parser progress"),
            0)
        self.assertNotEqual(declaration_id, function_id,
                            "the first declaration and the first function must be distinct nodes")

    def test_record_dependent_assembly_compiles_and_runs_natively(self):
        """The scalar case does not exercise typedefs or the arena; this one does.

        Strict flags are kept, and the arena include directory is added only when the assembly
        actually names the runtime header, so the test reports what it needed rather than passing
        because the compiler found something on its default path.
        """
        compilers = [name for name in ("clang", "gcc") if shutil.which(name)]
        if not compilers:
            self.skipTest("no C23 compiler on PATH")

        parsed, checked, semantic = self._prepare(RECORD_PROGRAM, "record-parity")
        whole_status, whole_diagnostic, whole = self._section(parsed, checked, semantic, "all")
        self.assertEqual(whole_status, "emitted", whole_diagnostic)
        header_status, header_diagnostic, header_parts = self._section(
            parsed, checked, semantic, "header")
        self.assertEqual(header_status, "emitted", header_diagnostic)
        epilogue_status, epilogue_diagnostic, epilogue_parts = self._section(
            parsed, checked, semantic, "main")
        self.assertEqual(epilogue_status, "emitted", epilogue_diagnostic)

        assembled = list(header_parts)
        requires_arena = False
        for index in range(2):
            unit_status, unit_diagnostic, unit_parts = self._unit(parsed, checked, semantic, index)
            self.assertEqual(unit_status, "emitted", unit_diagnostic)
            bounded = self._bounded_unit(parsed, checked, semantic, index)
            self.assertEqual(bounded["status"], "emitted", bounded["diagnostic"])
            requires_arena = requires_arena or bounded["requiresArena"]
            self.assertIn(f"pep_fn_", "".join(unit_parts))
            assembled.extend(unit_parts)
        assembled.extend(epilogue_parts)
        self.assertEqual(assembled, whole, "assembled sections must equal one-shot emission")

        text = "".join(assembled)
        self.assertIn("pep_record_", text, "this fixture must exercise a generated typedef")
        self.assertEqual("pep_arena.h" in text, requires_arena,
                         "requiresArena must agree with the emitted header set")

        reference = self._interpreter_reference(RECORD_PROGRAM)
        self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
        self.assertEqual(reference.stdout, "42\n")

        generated = pathlib.Path(self.temp.name) / "record-assembled.c"
        generated.write_text(text, encoding="utf-8", newline="\n")
        flags = ["-std=c23", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2"]
        if requires_arena:
            flags += ["-I", str(ROOT / "runtime" / "pep_arena")]
        for name in compilers:
            with self.subTest(compiler=name, requiresArena=requires_arena):
                executable = pathlib.Path(self.temp.name) / f"record-{name}.exe"
                built = subprocess.run([shutil.which(name)] + flags + [str(generated), "-o", str(executable)],
                                       text=True, capture_output=True, check=False)
                self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
                ran = subprocess.run([str(executable)], text=True, capture_output=True, check=False)
                self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
                self.assertEqual(ran.stdout, reference.stdout)

    def test_arena_dependent_assembly_compiles_and_runs_natively(self):
        """Records alone do not pull the runtime header; a mutable list does.

        This is the case where `requiresArena` is true, so the assembly names `pep_arena.h` and the
        compile needs an explicit include directory. Skipping it would leave the arena path
        unexercised while the scalar and record cases still looked green.
        """
        compilers = [name for name in ("clang", "gcc") if shutil.which(name)]
        if not compilers:
            self.skipTest("no C23 compiler on PATH")

        parsed, checked, semantic = self._prepare(ARENA_PROGRAM, "arena-parity")
        whole_status, whole_diagnostic, whole = self._section(parsed, checked, semantic, "all")
        self.assertEqual(whole_status, "emitted", whole_diagnostic)
        header = self._section(parsed, checked, semantic, "header")
        self.assertEqual(header[0], "emitted", header[1])
        epilogue = self._section(parsed, checked, semantic, "main")
        self.assertEqual(epilogue[0], "emitted", epilogue[1])
        unit = self._unit(parsed, checked, semantic, 0)
        self.assertEqual(unit[0], "emitted", unit[1])
        bounded = self._bounded_unit(parsed, checked, semantic, 0)
        self.assertEqual(bounded["status"], "emitted", bounded["diagnostic"])
        self.assertTrue(bounded["requiresArena"], "this fixture must require the arena")

        assembled = list(header[2]) + list(unit[2]) + list(epilogue[2])
        self.assertEqual(assembled, whole, "assembled sections must equal one-shot emission")
        text = "".join(assembled)
        self.assertIn("pep_arena.h", text)

        reference = self._interpreter_reference(ARENA_PROGRAM)
        self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
        self.assertEqual(reference.stdout, "4\n")

        generated = pathlib.Path(self.temp.name) / "arena-assembled.c"
        generated.write_text(text, encoding="utf-8", newline="\n")
        flags = ["-std=c23", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2",
                 "-I", str(ROOT / "runtime" / "pep_arena")]
        # The arena is a real runtime dependency, not a header-only convenience: an assembly that
        # requires it does not link until pep_arena.c is compiled alongside it.
        sources = [str(generated), str(ROOT / "runtime" / "pep_arena" / "pep_arena.c")]
        executed = []
        for name in compilers:
            with self.subTest(compiler=name):
                executable = pathlib.Path(self.temp.name) / f"arena-{name}.exe"
                built = subprocess.run([shutil.which(name)] + flags + sources + ["-o", str(executable)],
                                       text=True, capture_output=True, check=False)
                self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
                ran = subprocess.run([str(executable)], text=True, capture_output=True, check=False)
                self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
                self.assertEqual(ran.stdout, reference.stdout)
                executed.append(name)
        self.assertEqual(sorted(executed), sorted(compilers),
                         "every discovered compiler must actually run, not silently skip")

    def _interpreter_reference(self, source):
        """The same source run by the Pep interpreter, printed the way the generated C prints it."""
        path = pathlib.Path(self.temp.name) / "reference.pep"
        path.write_text(source + "\nsay(int_text(main()))\n", encoding="utf-8", newline="\n")
        return subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"), "run", str(path)],
            cwd=ROOT, text=True, capture_output=True, check=False)


RECORD_PARAMETER = ("type Point { x: Int y: Int }\n"
                    "fn use_point(p: Point) -> Int { return p.x }\n"
                    "fn main() -> Int { return 0 }\n")

# A self-referential union and a mutually recursive pair. Both close over themselves, so a
# closure that terminated by depth alone would loop; this pins that it terminates by identity.
RECURSIVE_UNION = ("type Expr = Number(Int) | Add(Expr, Expr)\n"
                   "fn depth(e: Expr) -> Int { return 0 }\n"
                   "fn main() -> Int { return 0 }\n")

MUTUAL_UNION = ("type Left = LeftEmpty(Int) | LeftWrap(Right)\n"
                "type Right = RightEmpty(Int) | RightWrap(Left)\n"
                "fn use_left(l: Left) -> Int { return 0 }\n"
                "fn main() -> Int { return 0 }\n")

# Exercises a generated typedef and, if the emitter says so, the arena include path.
RECORD_PROGRAM = ("type Point { x: Int y: Int }\n"
                  "fn total(p: Point) -> Int { return p.x + p.y }\n"
                  "fn main() -> Int {\n"
                  "  let point = Point { x: 19, y: 23 }\n"
                  "  return total(point)\n"
                  "}\n")

# Mutable list: requiresArena is true, so the assembly names the runtime header.
ARENA_PROGRAM = ("fn main() -> Int {\n"
                 "  var xs: List[Int] = [1, 2, 3]\n"
                 "  var guard = 0\n"
                 "  while guard <= 0 {\n"
                 "    xs = prepend(xs, 0)\n"
                 "    guard = guard + 1\n"
                 "  }\n"
                 "  return length(xs)\n"
                 "}\n")

# A declaration that appears after the function that names it.
FORWARD_TYPE = ("fn use_point(p: Point) -> Int { return 0 }\n"
                "type Point { x: Int y: Int }\n"
                "fn main() -> Int { return 0 }\n")

PARITY = ("fn increment(value: Int) -> Int { return value + 1 }\n"
          "fn main() -> Int { return increment(41) }\n")

# One record and one union: both are declarations whose text a caller may need individually.
UNION_AND_RECORD = ("type Point { x: Int y: Int }\n"
                    "type Flag = On(Int) | Off(Int)\n"
                    "fn use_point(p: Point) -> Int { return 0 }\n"
                    "fn main() -> Int { return 0 }\n")

# CR3: an empty record reached through a union. Emission refuses at the record (records are lowered
# before unions) while a closure-order walk blamed the union's layout instead.
UNION_EMPTY = ("type E2 { }\n"
               "type U = W(E2)\n"
               "fn use_u(value: U) -> Int { return 0 }\n"
               "fn main() -> Int { return 0 }\n")

# An empty record passes the checker but has no C23 lowering, so it is a prerequisite that cannot
# be emitted. A unit that merely names it in a signature still emits text referencing its typedef.
EMPTY_RECORD = ("type Empty { }\n"
                "fn use_empty(e: Empty) -> Int { return 0 }\n"
                "fn main() -> Int { return 0 }\n")

# `Outer` names `Inner` in its own field list, so a closure must report both declarations.
NESTED_RECORD = ("type Inner { value: Int }\n"
                 "type Outer { inner: Inner }\n"
                 "fn use_outer(o: Outer) -> Int { return 0 }\n"
                 "fn main() -> Int { return 0 }\n")

# `value` is the first top-level function, so index 0 selects a scalar-only signature.
SCALAR_ONLY = ("fn scalar(value: Int) -> Int { return value }\n"
               "fn main() -> Int { return 0 }\n")


def refused_declaration_unit():
    """The expected refusal for a declaration-unit request against an empty program."""
    return typed_record("unsupported", (),
                        "Pep C23 declaration unit requires a top-level declaration id")


def ok_declarations():
    """The expected record for a declarations check over an empty node list: nothing to refuse."""
    return pep_c23.typed_record_value("PepC23DeclarationCheck", [
        ("status", typed("Str", "ok")),
        ("diagnostic", typed("Str", "")),
    ])


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
