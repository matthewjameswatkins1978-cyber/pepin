"""A1 sectional driver product test (LUCY-20261107-014 transport slice).

Uses the product orchestration in `pep_sectional` (not probe scripts):
a two-function program is checked sectionally, emitted per section, and
reassembled as header + prototypes + units + epilogue. The reassembly must
be byte-identical to the one-shot `emit_c23_checked` output on the same
input, proving the host assembly rule independently of A2's suite.
"""
import pathlib
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

CLANG = pathlib.Path(r"C:\Users\Matmus\scoop\apps\llvm\current\bin\clang.exe")


def _normalize_locals(text):
    """Alpha-equivalence: remapped slices renumber locals/params per chunk,
    so compare programs modulo pep_local_N / pep_arg_N numbering."""
    mapping = {}
    counter = [0]

    def repl(match):
        key = match.group(0)
        if key not in mapping:
            mapping[key] = "pep_%s_N%d" % (match.group(1), counter[0])
            counter[0] += 1
        return mapping[key]

    return re.sub(r"pep_(local|arg)_\d+", repl, text)

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pep_c23
import pep_sectional
from pep_c23 import Session, parse_target
from tests.chunk_helper import fields_map
from tests.test_chunk_typed import host_builtins

SRC = (b"fn callee(a: Int) -> Int { return a + 1 }\n"
       b"fn main() -> Int { let x = callee(41) return x }\n")


class SectionalDriverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = Session()
        bundle_text = "\n".join(
            p.read_text(encoding="utf-8")
            for p in [pathlib.Path(x) for x in pep_c23.SOURCES])
        bundle = cls.session.send({"schemaVersion": 3, "op": "open",
                                   "source": bundle_text, "name": "pep-c23",
                                   "metadataOnly": True})
        cls.tool_revision = bundle["revision"]
        cls.tool_document = bundle["document"]
        target = cls.session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": "sectional-driver", "bytes": list(SRC)})
        assert target.get("outcome") == "ok", target
        cls.sem = {"document": target["document"],
                   "revision": target["revision"], "entryFunctions": []}
        cls.target = target
        sample = cls.session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": "validate", "bytes": []})
        pep_sectional.register_sectional_tools(
            cls.session, cls.tool_document, cls.tool_revision, sample, pep_c23)
        empty_pp = pep_c23.parser_progress(sample["document"], sample["revision"])
        empty_checked = pep_c23.checker_report(sample["document"], sample["revision"])
        refused = pep_c23.typed_record(
            "unsupported", (),
            "Pep C23 emission requires a top-level function named main")
        cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                          "op": "tool_register", "tool": "pep-c23-emitter",
                          "document": cls.tool_document,
                          "revision": cls.tool_revision,
                          "function": "emit_c23_checked"})
        cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                          "op": "tool_validate", "tool": "pep-c23-emitter",
                          "document": cls.tool_document,
                          "revision": cls.tool_revision,
                          "testVectors": [{"arguments": [empty_pp, empty_checked],
                                           "expect": refused,
                                           "semanticTarget": {
                                               "document": sample["document"],
                                               "revision": sample["revision"],
                                               "entryFunctions": []}}]})
        cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                          "op": "tool_activate", "tool": "pep-c23-emitter",
                          "document": cls.tool_document,
                          "revision": cls.tool_revision})
        empty_parsed = pep_c23.parser_progress(sample["document"], sample["revision"])
        empty_rpt = pep_c23.checker_report(sample["document"], sample["revision"])
        cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                          "op": "tool_register", "tool": "pep-c23-checker",
                          "document": cls.tool_document,
                          "revision": cls.tool_revision,
                          "function": "analyze_parsed"})
        cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                          "op": "tool_validate", "tool": "pep-c23-checker",
                          "document": cls.tool_document,
                          "revision": cls.tool_revision,
                          "testVectors": [{"arguments": [empty_parsed],
                                           "expect": empty_rpt,
                                           "semanticTarget": {
                                               "document": sample["document"],
                                               "revision": sample["revision"],
                                               "entryFunctions": []}}]})
        cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                          "op": "tool_activate", "tool": "pep-c23-checker",
                          "document": cls.tool_document,
                          "revision": cls.tool_revision})

    @classmethod
    def tearDownClass(cls):
        cls.session.close()

    def test_sectional_reassembly_matches_one_shot(self):
        parsed = parse_target(self.session, SRC, self.target, self.tool_revision)
        host = host_builtins(self.target["document"], self.target["revision"])
        checked = pep_sectional.check_program(
            self.session, self.sem, parsed, self.tool_revision, self.target, host)
        self.assertEqual(checked["failures"], [])
        self.assertEqual(sorted(checked["order"]), ["callee", "main"])
        order, slices, reports = (checked["order"], checked["slices"],
                                  checked["reports"])
        # one-shot reference on the same input (small enough to cross whole):
        # analyze_parsed then emit_c23_checked, compared byte-for-byte.
        whole = self.session.send(
            {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
             "tool": "pep-c23-checker", "arguments": [parsed],
             "semanticTarget": self.sem})
        self.assertEqual(whole.get("outcome"), "ok", whole)
        whole_checked = whole["result"]
        whole_emit = self.session.send(
            {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
             "tool": "pep-c23-emitter", "arguments": [parsed, whole_checked],
             "semanticTarget": self.sem})
        self.assertEqual(whole_emit.get("outcome"), "ok", whole_emit)
        whole_fields = {item["name"]: item["value"]
                        for item in whole_emit["result"]["fields"]}
        self.assertEqual(whole_fields["status"]["value"], "emitted",
                         whole_fields["diagnostic"]["value"])
        whole_parts = [p["value"] for p in whole_fields["sourceParts"]["value"]]
        # sectional assembly: header(slice0) + prototypes(rest) + units + main
        status, diag, header, _ = pep_sectional.emit_section(
            self.session, self.sem, slices[order[0]], reports[order[0]], "header")
        self.assertEqual(status, "emitted", diag)
        rebuilt = list(header)
        for name in order[1:]:
            status, diag, protos, _ = pep_sectional.emit_section(
                self.session, self.sem, slices[name], reports[name], "prototypes")
            self.assertEqual(status, "emitted", diag)
            rebuilt.extend(protos)
        for name in order:
            status, diag, parts, _ = pep_sectional.emit_unit(
                self.session, self.sem, slices[name], reports[name], 0)
            self.assertEqual(status, "emitted", diag)
            rebuilt.extend(parts)
        status, diag, epilogue, _ = pep_sectional.emit_section(
            self.session, self.sem, slices["main"], reports["main"], "main")
        self.assertEqual(status, "emitted", diag)
        rebuilt.extend(epilogue)
        text = "".join(rebuilt)
        self.assertIn("pep_fn_callee", text)
        self.assertIn("pep_fn_main", text)
        self.assertEqual(_normalize_locals(text),
                         _normalize_locals("".join(whole_parts)),
                         "sectional assembly must equal one-shot output "
                         "modulo per-slice local renumbering")


    def test_emit_sectional_flag_matches_one_shot(self):
        one = pep_c23.emit(SRC)
        two = pep_c23.emit(SRC, sectional=True)
        self.assertEqual(_normalize_locals(two), _normalize_locals(one))

    @unittest.skipUnless(CLANG.is_file(), "Clang not installed at scoop path")
    def test_cli_sectional_build_and_run(self):
        with tempfile.TemporaryDirectory(prefix="pep-a1-sectional-") as tmp:
            src = pathlib.Path(tmp) / "twofn.pep"
            src.write_bytes(SRC)
            exe = pathlib.Path(tmp) / "twofn.exe"
            rc = pep_c23.main(["build-c23", str(src), "-o", str(exe),
                               "--sectional", "--compiler", str(CLANG)])
            self.assertEqual(rc, 0)
            self.assertTrue(exe.is_file())
            run = subprocess.run([str(exe)], capture_output=True, text=True,
                                   check=False)
            self.assertEqual(run.returncode, 0)
            self.assertEqual(run.stdout, "42\n")


if __name__ == "__main__":
    unittest.main()
