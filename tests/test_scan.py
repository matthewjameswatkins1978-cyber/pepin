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

fn scan_probe_ident(offset: Int) -> ScanIdent {
  return scan_ident_at(source_bytes(), offset)
}

fn scan_probe_ident_count() -> ScanCount {
  return scan_ident_count(source_bytes())
}

fn scan_probe_string(offset: Int) -> ScanString {
  return scan_string_at(source_bytes(), offset)
}
"""


def scan_int_record(status, diagnostic, value, next_offset):
    return typed_record_value("ScanInt", [
        ("status", typed("Str", status)),
        ("diagnostic", typed("Str", diagnostic)),
        ("value", typed("Int", str(value))),
        ("nextOffset", typed("Int", str(next_offset))),
    ])


def scan_ident_record(status, diagnostic, text, byte_length, next_offset):
    return typed_record_value("ScanIdent", [
        ("status", typed("Str", status)),
        ("diagnostic", typed("Str", diagnostic)),
        ("text", typed("Str", text)),
        ("byteLength", typed("Int", str(byte_length))),
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
        cls._register("pep-scan-ident", "scan_probe_ident", [typed("Int", 0)],
                      scan_ident_record("unsupported",
                                        "Pep scan found no identifier at the end of the source", "", 0, 0))
        cls._register("pep-scan-ident-count", "scan_probe_ident_count", [],
                      typed_record_value("ScanCount", [
                          ("status", typed("Str", "ok")),
                          ("diagnostic", typed("Str", "")),
                          ("count", typed("Int", "0")),
                          ("offset", typed("Int", "0")),
                      ]))
        cls._register("pep-scan-string", "scan_probe_string", [typed("Int", 0)],
                      typed_record_value("ScanString", [
                          ("status", typed("Str", "unsupported")),
                          ("diagnostic", typed("Str",
                                               "Pep scan found no string literal at the end of the source")),
                          ("parts", {"type": "List[Str]", "value": []}),
                          ("byteLength", typed("Int", "0")),
                          ("nextOffset", typed("Int", "0")),
                          ("nulCount", typed("Int", "0")),
                      ]))

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


    def _ident_at(self, payload, offset=0):
        fields = self._invoke("pep-scan-ident", payload, [typed("Int", offset)])
        return (fields["status"]["value"], fields["text"]["value"],
                int(fields["byteLength"]["value"]), int(fields["nextOffset"]["value"]),
                fields["diagnostic"]["value"])

    def test_identifier_scan_returns_text_width_and_offset(self):
        status, text, byte_length, next_offset, _ = self._ident_at("alpha_1 beta")
        self.assertEqual((status, text, byte_length, next_offset), ("ok", "alpha_1", 7, 7))

    def test_identifier_count_skips_space_and_refuses_on_a_digit_start(self):
        fields = self._invoke("pep-scan-ident-count", "alpha beta_2 gamma", [])
        self.assertEqual(fields["status"]["value"], "ok")
        self.assertEqual(int(fields["count"]["value"]), 3)

        refused = self._invoke("pep-scan-ident-count", "alpha 9beta", [])
        self.assertEqual(refused["status"]["value"], "unsupported")
        self.assertEqual(int(refused["count"]["value"]), 1, "the count reports how far scanning got")
        self.assertEqual(int(refused["offset"]["value"]), 6, "and it names the refusing offset")

    def test_identifier_start_must_be_ascii_or_underscore(self):
        status, _, _, _, diagnostic = self._ident_at("é")
        self.assertEqual(status, "unsupported")
        self.assertIn("non-identifier start byte", diagnostic)


    def _string_fields(self, payload, offset=0):
        fields = self._invoke("pep-scan-string", payload, [typed("Int", offset)])
        return {
            "status": fields["status"]["value"],
            "parts": [part["value"] for part in fields["parts"]["value"]],
            "byteLength": int(fields["byteLength"]["value"]),
            "nextOffset": int(fields["nextOffset"]["value"]),
            "nulCount": int(fields["nulCount"]["value"]),
            "diagnostic": fields["diagnostic"]["value"],
        }

    def _string_at(self, payload, offset=0):
        fields = self._invoke("pep-scan-string", payload, [typed("Int", offset)])
        return (fields["status"]["value"],
                [part["value"] for part in fields["parts"]["value"]],
                int(fields["byteLength"]["value"]),
                int(fields["nextOffset"]["value"]),
                fields["diagnostic"]["value"])

    def test_string_literal_returns_parts_width_and_next_offset(self):
        status, parts, byte_length, next_offset, _ = self._string_at('"abc" tail')
        self.assertEqual((status, parts, byte_length, next_offset), ("ok", ["abc"], 5, 5))

    def test_escapes_decode_to_their_real_characters(self):
        status, parts, byte_length, next_offset, _ = self._string_at('"a\\nb\\\\c\\"d"')
        self.assertEqual(status, "ok")
        self.assertEqual(parts, ["a", "\n", "b", "\\", "c", "\"", "d"])
        self.assertEqual(byte_length, len('"a\\nb\\\\c\\"d"'))
        self.assertEqual(next_offset, byte_length)

    def test_multi_byte_body_is_one_fragment_with_a_byte_length(self):
        payload = '"é"'
        status, parts, byte_length, next_offset, _ = self._string_at(payload)
        self.assertEqual((status, parts), ("ok", ["é"]))
        self.assertEqual(byte_length, 4, "quote + two UTF-8 bytes + quote")
        self.assertEqual(next_offset, 4)

    def test_unterminated_literal_refuses(self):
        status, parts, _, _, diagnostic = self._string_at('"abc')
        self.assertEqual(status, "unsupported")
        self.assertEqual(parts, [])
        self.assertIn("unterminated", diagnostic)

    def test_unescaped_newline_refuses_as_unterminated(self):
        status, _, _, _, diagnostic = self._string_at('"abc\ndef"')
        self.assertEqual(status, "unsupported")
        self.assertIn("unterminated", diagnostic)

    def test_unknown_escape_refuses_instead_of_passing_through(self):
        status, parts, _, _, diagnostic = self._string_at('"bad\\q"')
        self.assertEqual(status, "unsupported")
        self.assertEqual(parts, [])
        self.assertIn("unsupported string escape", diagnostic)

    def test_nul_escape_is_accepted_and_counted_not_dropped(self):
        """The OCaml seed accepts `\\0` and emits a NUL byte (verified by running it), so refusing it
        would make this scanner reject valid programs. Pep source cannot WRITE a NUL fragment, so the
        escape is accepted, contributes no fragment, and is counted for the caller to materialise."""
        fields = self._string_fields('"a\\0b"')
        self.assertEqual(fields["status"], "ok", fields["diagnostic"])
        self.assertEqual(fields["parts"], ["a", "b"])
        self.assertEqual(fields["nulCount"], 1)
        self.assertEqual(fields["byteLength"], 6,
                         'source "a\\\\0b" is six bytes: quote, a, backslash, 0, b, quote')

    def test_int64_max_is_accepted_and_max_plus_one_refuses(self):
        """Guarding the multiply rejected legal Int64 max; the last digit is what must be bounded."""
        status, value, next_offset, _ = self._int_at("9223372036854775807")
        self.assertEqual((status, value, next_offset), ("ok", 9223372036854775807, 19))

        status, _, _, diagnostic = self._int_at("9223372036854775808")
        self.assertEqual(status, "unsupported")
        self.assertIn("too large", diagnostic)

    def test_negative_offsets_refuse_instead_of_raising_from_byte_at(self):
        int_status, _, _, int_diagnostic = self._int_at("42", -1)
        self.assertEqual(int_status, "unsupported")
        self.assertIn("negative", int_diagnostic)

        ident_fields = self._invoke("pep-scan-ident", "abc", [typed("Int", -1)])
        self.assertEqual(ident_fields["status"]["value"], "unsupported")
        self.assertIn("negative", ident_fields["diagnostic"]["value"])

        string_fields = self._string_fields('"abc"', -1)
        self.assertEqual(string_fields["status"], "unsupported")
        self.assertIn("negative", string_fields["diagnostic"])


if __name__ == "__main__":
    unittest.main()
