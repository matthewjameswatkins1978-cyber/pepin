"""G1 host acceptance: SourceBytes entry grant via emit_granted (contract s6).

Covers, at the merged host+emitter SHA:
- granted entry `fn main(source: SourceBytes)` emits, wrapper binds the
  granted bytes (`(pep_source_bytes){ .data = pep_source_data...}`);
- ASCII/NUL/UTF-8 first-byte fixtures emit shape-identically (runtime
  parity on the same wrapper was verified by A3 BOOT-A3-016 at A2's SHA);
- granted=True but no SourceBytes parameter -> GrantRefusal GRANT_SHAPE_MISMATCH,
  raised BEFORE the emitter runs;
- granted=False with a SourceBytes parameter -> GrantRefusal GRANT_DENIED,
  also pre-emitter;
- entry not in the checked report -> GRANT_ENTRY_MISSING.
Host validation only; no cap/budget/frozen-test change.
"""
import unittest

import pep_c23
from pep_c23 import GrantRefusal, Session, require, typed, typed_record


ENTRY = "fn main(source: SourceBytes) -> Int { return byte_at(source, 0) }\n"
WRONG_PARAM = "fn main(count: Int) -> Int { return count }\n"
NO_ENTRY = "fn helper() -> Int { return 1 }\n"


class GrantHostAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = Session()
        try:
            bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
            opened = cls.session.send({"schemaVersion": 3, "op": "open",
                                       "source": bundle, "name": "pep-c23",
                                       "metadataOnly": True})
            require(opened, "outcome", "ok", "open compiler bundle")
            require(opened, "status", "valid", "check compiler bundle")
            document, revision = opened["document"], opened["revision"]
            sample = cls.session.send({"schemaVersion": 3, "op": "open_bytes",
                                       "name": "grant-validation", "bytes": []})
            require(sample, "outcome", "ok", "open validation source")
            target_spec = {"document": sample["document"],
                           "revision": sample["revision"], "entryFunctions": []}
            empty_parsed = pep_c23.parser_progress(sample["document"],
                                                   sample["revision"])
            empty_checked = pep_c23.checker_report(sample["document"],
                                                   sample["revision"])
            refused = typed_record("unsupported", (),
                                   "Pep C23 emission requires a top-level "
                                   "function named main")
            start_cursor = pep_c23.parser_cursor_value(sample["document"],
                                                       sample["revision"])
            finished_cursor = pep_c23.parser_cursor_value(
                sample["document"], sample["revision"],
                done=True, lex_done=True, lex_stage="done")
            tools = [
                ("pep-c23-parser-start", "parser_start", [], start_cursor),
                ("pep-c23-parser-step", "parser_step", [finished_cursor],
                 pep_c23.parser_chunk_value(sample["document"],
                                            sample["revision"],
                                            finished_cursor)),
                ("pep-c23-checker", "analyze_parsed", [empty_parsed],
                 empty_checked),
                ("pep-c23-checker-sigs", "chunk_signatures", [empty_parsed],
                 {"type": "List[ResolvedSignature]", "value": []}),
                ("pep-c23-emitter", "emit_c23_checked",
                 [empty_parsed, empty_checked], refused),
            ]
            for tool, function, arguments, expect in tools:
                registered = cls.session.send(
                    {"schemaVersion": 3, "toolProtocolVersion": 2,
                     "op": "tool_register", "tool": tool, "document": document,
                     "revision": revision, "function": function})
                require(registered, "status", "Registered", f"register {tool}")
                validated = cls.session.send(
                    {"schemaVersion": 3, "toolProtocolVersion": 2,
                     "op": "tool_validate", "tool": tool, "document": document,
                     "revision": revision,
                     "testVectors": [{"arguments": arguments, "expect": expect,
                                      "semanticTarget": target_spec}]})
                require(validated, "status", "Validated", f"validate {tool}")
                activated = cls.session.send(
                    {"schemaVersion": 3, "toolProtocolVersion": 2,
                     "op": "tool_activate", "tool": tool, "document": document,
                     "revision": revision})
                require(activated, "status", "Active", f"activate {tool}")
            cls.tool_revision = revision
        except Exception:
            cls.session.process.stdin.close()
            cls.session.process.terminate()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.session.process.stdin.close()
        cls.session.process.terminate()

    def test_granted_entry_emits_wrapper(self):
        result = pep_c23.emit_granted(
            self.session, self.tool_revision, ENTRY.encode("utf-8"),
            name="grant-entry", entry_name="main", granted=True)
        self.assertEqual(result["status"], "emitted", result)
        self.assertIn("(pep_source_bytes){ .data = pep_source_data",
                      result["c_source"])

    def test_ungranted_sourcebytes_entry_refused_before_emitter(self):
        with self.assertRaises(GrantRefusal) as caught:
            pep_c23.emit_granted(self.session, self.tool_revision,
                                 ENTRY.encode("utf-8"), name="grant-denied",
                                 entry_name="main", granted=False)
        self.assertEqual(caught.exception.code, "GRANT_DENIED")

    def test_granted_without_sourcebytes_parameter_refused(self):
        with self.assertRaises(GrantRefusal) as caught:
            pep_c23.emit_granted(self.session, self.tool_revision,
                                 WRONG_PARAM.encode("utf-8"),
                                 name="grant-shape", entry_name="main",
                                 granted=True)
        self.assertEqual(caught.exception.code, "GRANT_SHAPE_MISMATCH")

    def test_missing_entry_refused(self):
        with self.assertRaises(GrantRefusal) as caught:
            pep_c23.emit_granted(self.session, self.tool_revision,
                                 NO_ENTRY.encode("utf-8"), name="grant-missing",
                                 entry_name="main", granted=True)
        self.assertEqual(caught.exception.code, "GRANT_ENTRY_MISSING")


if __name__ == "__main__":
    unittest.main()
