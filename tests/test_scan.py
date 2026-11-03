"""stdlib/scan.pep: byte-level integer scanning over SourceBytes, through the tool host.

`SourceBytes` values exist only in a host-authorised v2 semantic-target context, so these cases run as
registered tools with the payload document as the target -- the same route the span probe uses. The
cases are the ones that break a naive scanner: leading zeros, a trailing space, a non-digit, an offset
past the end, and a digit run that overflows Int.
"""

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, typed, typed_record_value  # noqa: E402

SCAN = ROOT / "stdlib" / "scan.pep"

PROBES = """
fn scan_probe_at(offset: Int) -> ScanInt {
  return scan_int_at(source_bytes(), offset)
}

fn scan_probe_after_space(offset: Int) -> ScanInt {
  return scan_int_after_space(source_bytes(), offset)
}

fn scan_probe_sum() -> ScanSum {
  return scan_int_sum(source_bytes())
}
"""


def scan_int_record(status, diagnostic, value, next_offset):
    return typed_record_value("ScanInt", [
        ("status", typed("Str", status)),
        ("diagnostic", typed("Str", diagnostic)),
        ("value", typed("Int", str(value))),
        ("nextOffset", typed("Int", str(next_offset))),
    ])


def scan_sum_record(status, diagnostic, count, total):
    return typed_record_value("ScanSum", [
        ("status", typed("Str", status)),
        ("diagnostic", typed("Str", diagnostic)),
        ("count", typed("Int", str(count))),
        ("total", typed("Int", str(total))),
    ])


class ScanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = Session()
        opened = cls.session.send({"schemaVersion": 3, "op": "open",
                                   "source": SCAN.read_text(encoding="utf-8") + PROBES,
                                   "name": "pep-scan", "metadataOnly": True})
        require(opened, "outcome", "ok", "open scan module")
        require(opened, "status", "valid", "check scan module")
        cls.document = opened["document"]
        cls.revision = opened["revision"]
        sample = cls.session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": "validate", "bytes": []})
        require(sample, "outcome", "ok", "open validation source")
        cls.target_spec = {"document": sample["document"], "revision": sample["revision"],
                           "entryFunctions": []}
        cls._register("pep-scan-at", "scan_probe_at", [typed("Int", 0)],
                      scan_int_record("unsupported",
                                      "Pep scan found no digits at the end of the source", 0, 0))
        cls._register("pep-scan-space", "scan_probe_after_space", [typed("Int", 0)],
                      scan_int_record("unsupported",
                                      "Pep scan found no digits at the end of the source", 0, 0))
        cls._register("pep-scan-sum", "scan_probe_sum", [],
                      scan_sum_record("ok", "", 0, 0))

    @classmethod
    def _register(cls, tool, function, arguments, expect):
        document, revision = cls.document, cls.revision
        registered = cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                       "op": "tool_register", "tool": tool, "document": document,
                                       "revision": revision, "function": function})
        require(registered, "status", "Registered", f"register {tool}")
        validated = cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_validate", "tool": tool, "document": document,
                                      "revision": revision,
                                      "testVectors": [{"arguments": arguments, "expect": expect,
                                                       "semanticTarget": cls.target_spec}]})
        require(validated, "status", "Validated", f"validate {tool}")
        activated = cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_activate", "tool": tool, "document": document,
                                      "revision": revision})
        require(activated, "status", "Active", f"activate {tool}")

    @classmethod
    def tearDownClass(cls):
        cls.session.close()

    def _invoke(self, tool, payload, arguments):
        raw = payload.encode("utf-8")
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                    "name": f"payload-{len(raw)}", "bytes": list(raw)})
        require(target, "outcome", "ok", "open payload")
        response = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_invoke", "tool": tool,
                                      "arguments": arguments,
                                      "semanticTarget": {"document": target["document"],
                                                         "revision": target["revision"],
                                                         "entryFunctions": []}})
        require(response, "outcome", "ok", f"invoke {tool}")
        return {item["name"]: item["value"] for item in response["result"]["fields"]}

    def _int_at(self, payload, offset=0):
        fields = self._invoke("pep-scan-at", payload, [typed("Int", offset)])
        return (fields["status"]["value"], int(fields["value"]["value"]),
                int(fields["nextOffset"]["value"]), fields["diagnostic"]["value"])

    def test_scan_reads_digits_and_reports_the_next_offset(self):
        status, value, next_offset, _ = self._int_at("42rest")
        self.assertEqual((status, value, next_offset), ("ok", 42, 2))

    def test_leading_zeros_do_not_change_the_value(self):
        status, value, next_offset, _ = self._int_at("0042")
        self.assertEqual((status, value, next_offset), ("ok", 42, 4))

    def test_non_digit_refuses_instead_of_returning_zero(self):
        status, value, _, diagnostic = self._int_at("abc")
        self.assertEqual(status, "unsupported")
        self.assertIn("non-digit", diagnostic)

    def test_offset_past_the_end_refuses(self):
        status, _, _, diagnostic = self._int_at("42", 9)
        self.assertEqual(status, "unsupported")
        self.assertIn("past the end", diagnostic)

    def test_overflowing_digit_run_refuses(self):
        status, _, _, diagnostic = self._int_at("12345678901234567890")
        self.assertEqual(status, "unsupported")
        self.assertIn("too large", diagnostic)

    def test_sum_skips_space_and_tolerates_trailing_whitespace(self):
        fields = self._invoke("pep-scan-sum", "42 7 \n", [])
        self.assertEqual(fields["status"]["value"], "ok")
        self.assertEqual(int(fields["count"]["value"]), 2)
        self.assertEqual(int(fields["total"]["value"]), 49)

    def test_sum_refuses_on_a_non_digit_run(self):
        fields = self._invoke("pep-scan-sum", "1 2 x", [])
        self.assertEqual(fields["status"]["value"], "unsupported")
        self.assertEqual(int(fields["total"]["value"]), 3, "the scan stops at the failure site")

    def test_after_space_skips_leading_whitespace(self):
        fields = self._invoke("pep-scan-space", "  17", [typed("Int", 0)])
        self.assertEqual(fields["status"]["value"], "ok")
        self.assertEqual(int(fields["value"]["value"]), 17)
        self.assertEqual(int(fields["nextOffset"]["value"]), 4)


if __name__ == "__main__":
    unittest.main()
