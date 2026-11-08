"""A1 sectional-emit translation proof (LUCY-20261107-014 transport slice).

A two-function program: `main` is force-checked as per-statement bound-chunks
(2 groups) and the merged host-side report is used to emit the `function-unit`
for the whole-`main` slice. The `let`-bound cross-chunk call
(`callee(41)`) can only lower through the checker's ResolvedCall facts, whose
syntaxIds live in per-group id spaces — so emission proves the host merge
translates group-space ids back into slice space.

Covers the merge machinery; the 11 fallible-operand and 8 known-target
refusals on real compiler-A source are emitter-semantics for A2's lane and
are deliberately NOT pinned here.
"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pep_c23
import pep_sectional
from pep_c23 import Session, parse_target
from tests.test_chunk_typed import host_builtins

SRC = (b"fn callee(a: Int) -> Int { return a + 1 }\n"
       b"fn main() -> Int { let x = callee(41) return x }\n")


class SectionalEmitTranslationTests(unittest.TestCase):
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
                                   "name": "sectional-emit-proof",
                                   "bytes": list(SRC)})
        assert target.get("outcome") == "ok", target
        cls.sem = {"document": target["document"],
                   "revision": target["revision"], "entryFunctions": []}
        cls.target = target
        sample = cls.session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": "validate", "bytes": []})
        pep_sectional.register_sectional_tools(
            cls.session, cls.tool_document, cls.tool_revision, sample, pep_c23)

    @classmethod
    def tearDownClass(cls):
        cls.session.close()

    def test_chain_merged_report_emits_cross_chunk_call(self):
        parsed = parse_target(self.session, SRC, self.target, self.tool_revision)
        host = host_builtins(self.target["document"], self.target["revision"])
        checked = pep_sectional.check_program(
            self.session, self.sem, parsed, self.tool_revision, self.target,
            host, force_chain={"main"})
        self.assertEqual(checked["failures"], [])
        self.assertEqual(checked["stats"]["main"]["mode"], "chain-2")
        order, slices, reports = (checked["order"], checked["slices"],
                                  checked["reports"])
        # whole-file functions recipe: every slice carries all callees
        merged_names = set()
        for fld in reports["main"]["fields"]:
            if fld["name"] == "functions":
                for ent in fld["value"]["value"]:
                    for g in ent["fields"]:
                        if g["name"] == "name":
                            merged_names.add(g["value"]["value"])
        self.assertTrue({"callee", "main"} <= merged_names, merged_names)
        for name in order:
            status, diagnostic, parts, _ = pep_sectional.emit_unit(
                self.session, self.sem, slices[name], reports[name], 0)
            self.assertEqual(status, "emitted", f"{name}: {diagnostic}")
            if name == "main":
                text = "".join(parts)
        self.assertIn("pep_fn_main", text)
        # the let-bound cross-chunk call lowered through the translated facts
        self.assertIn("pep_fn_callee", text)


if __name__ == "__main__":
    unittest.main()
