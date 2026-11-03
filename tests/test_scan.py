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

fn scan_probe_sym(offset: Int) -> ScanSym {
  return scan_sym_at(source_bytes(), offset)
}

fn scan_probe_sym_count() -> ScanSymCount {
  return scan_sym_count(source_bytes())
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
        cls._register("pep-scan-sym", "scan_probe_sym", [typed("Int", 0)],
                      typed_record_value("ScanSym", [
                          ("status", typed("Str", "unsupported")),
                          ("diagnostic", typed("Str",
                                               "Pep scan found no symbol at the end of the source")),
                          ("text", typed("Str", "")),
                          ("byteLength", typed("Int", "0")),
                          ("nextOffset", typed("Int", "0")),
                      ]))
        cls._register("pep-scan-sym-count", "scan_probe_sym_count", [],
                      typed_record_value("ScanSymCount", [
                          ("status", typed("Str", "ok")),
                          ("diagnostic", typed("Str", "")),
                          ("count", typed("Int", "0")),
                          ("offset", typed("Int", "0")),
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

    def test_nul_escape_emits_an_ordered_fragment_and_still_counts(self):
        """Measured: seed `say("a\\0b")` emits `61 00 62`, so the NUL belongs to the decoded value.
        The scanner now emits it as its own ordered fragment -- the seed decodes the source escape
        `\\0` to a one-byte NUL string -- while `nulCount` stays as a cross-check total."""
        fields = self._string_fields('"a\\0b"')
        self.assertEqual(fields["status"], "ok", fields["diagnostic"])
        self.assertEqual(fields["parts"], ["a", "\x00", "b"])
        self.assertEqual(fields["nulCount"], 1)
        self.assertEqual(fields["byteLength"], 6,
                         'source "a\\\\0b" is six bytes: quote, a, backslash, 0, b, quote')

    def test_nul_position_is_distinguishable(self):
        """The defect this slice closes: count-only NULs made `\\0ab` and `ab\\0` return identical
        fields. Measured seed `say` outputs are `00 61 62` and `61 62 00`."""
        leading = self._string_fields('"\\0ab"')
        trailing = self._string_fields('"ab\\0"')
        middle = self._string_fields('"a\\0b"')
        self.assertEqual(leading["parts"], ["\x00", "ab"])
        self.assertEqual(trailing["parts"], ["ab", "\x00"])
        self.assertEqual(middle["parts"], ["a", "\x00", "b"])
        self.assertNotEqual(leading["parts"], trailing["parts"])
        self.assertEqual(leading["nulCount"], 1)
        self.assertEqual(trailing["nulCount"], 1)

    def test_multiple_nuls_keep_every_fragment_in_order(self):
        # Seed `say("a\\0\\0b")` emits `61 00 00 62`.
        fields = self._string_fields('"a\\0\\0b"')
        self.assertEqual(fields["parts"], ["a", "\x00", "\x00", "b"])
        self.assertEqual(fields["nulCount"], 2)
        self.assertEqual(fields["byteLength"], 8)

    def test_mixed_unicode_and_escapes_decode_like_the_seed(self):
        # Seed `say("é\\0中")` emits `c3 a9 00 e4 b8 ad`; multibyte runs stay whole fragments and
        # the width is bytes, not characters.
        fields = self._string_fields('"é\\0中"')
        self.assertEqual(fields["parts"], ["é", "\x00", "中"])
        self.assertEqual(fields["byteLength"], 9, "quote + e-acute (2) + backslash 0 (2) + CJK (3) + quote")

        # Seed `say("a\\n\\t\\\\\\"\\0b")` emits `61 0a 09 5c 22 00 62`: seven ordered fragments.
        fields = self._string_fields('"a\\n\\t\\\\\\"\\0b"')
        self.assertEqual(fields["parts"], ["a", "\n", "\t", "\\", "\"", "\x00", "b"])
        self.assertEqual(fields["byteLength"], 14)
        self.assertEqual(fields["nulCount"], 1)

    def test_joined_fragments_reproduce_the_seed_say_bytes(self):
        """Round trip against the oracle: joining the ordered fragments must equal the exact bytes
        the OCaml seed printed for the same literal (recorded from `pep.ps1 run` probes)."""
        cases = [
            ('"a\\0b"', bytes([0x61, 0x00, 0x62])),
            ('"\\0ab"', bytes([0x00, 0x61, 0x62])),
            ('"ab\\0"', bytes([0x61, 0x62, 0x00])),
            ('"a\\0\\0b"', bytes([0x61, 0x00, 0x00, 0x62])),
            ('"é\\0中"', bytes([0xc3, 0xa9, 0x00, 0xe4, 0xb8, 0xad])),
            ('"a\\n\\t\\\\\\"\\0b"', bytes([0x61, 0x0a, 0x09, 0x5c, 0x22, 0x00, 0x62])),
            ('"\\\\0"', bytes([0x5c, 0x30])),
        ]
        for payload, expected in cases:
            with self.subTest(payload=payload):
                fields = self._string_fields(payload)
                self.assertEqual(fields["status"], "ok", fields["diagnostic"])
                self.assertEqual("".join(fields["parts"]).encode("utf-8"), expected)

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


    def _sym_at(self, payload, offset=0):
        fields = self._invoke("pep-scan-sym", payload, [typed("Int", offset)])
        return (fields["status"]["value"], fields["text"]["value"],
                int(fields["byteLength"]["value"]), int(fields["nextOffset"]["value"]),
                fields["diagnostic"]["value"])

    def _sym_tokens(self, payload):
        """Consume symbols the way a driver would: skip ASCII space and scan until a refusal.

        Returns the token texts and the offset of the first refusing byte, or (tokens, None) when
        the payload was fully consumed."""
        offset = 0
        tokens = []
        while True:
            while offset < len(payload) and payload[offset] in " \t\r\n":
                offset += 1
            if offset >= len(payload):
                return tokens, None
            status, text, byte_length, next_offset, _ = self._sym_at(payload, offset)
            if status != "ok":
                return tokens, offset
            tokens.append(text)
            offset = next_offset

    def test_two_byte_forms_take_exactly_two_bytes(self):
        for text in ("<=", "==", "!=", "&&", "||", "->", "=>"):
            status, scanned, byte_length, next_offset, _ = self._sym_at(text)
            self.assertEqual((status, scanned, byte_length, next_offset), ("ok", text, 2, 2), text)

    def test_lone_angle_brackets_refuse_like_the_seed(self):
        """Measured against the OCaml seed: `let a = 1 < 2;` fails PEP_UNEXPECTED_CHARACTER at the
        `<`, because `<` and `>` are not in the seed's single-byte symbol list."""
        for char in ("<", ">"):
            status, text, byte_length, next_offset, diagnostic = self._sym_at(char)
            self.assertEqual(status, "unsupported", char)
            self.assertEqual((text, byte_length, next_offset), (char, 0, 0), char)
            self.assertIn("unexpected character", diagnostic, char)

    def test_every_single_byte_symbol_is_accepted(self):
        for char in "(){}[],:;+-*/=.|&!":
            status, scanned, byte_length, next_offset, _ = self._sym_at(char)
            self.assertEqual((status, scanned, byte_length, next_offset), ("ok", char, 1, 1), char)

    def test_maximal_munch_follows_the_seed_precedence(self):
        tokens, refused_at = self._sym_tokens("<==")
        self.assertEqual((tokens, refused_at), (["<=", "="], None),
                         "the pair wins, then the lone = is a single symbol")

        tokens, refused_at = self._sym_tokens("!==")
        self.assertEqual((tokens, refused_at), (["!=", "="], None),
                         "the !+= pair wins first, then the trailing = has no partner and is a single symbol")

        tokens, refused_at = self._sym_tokens("==> ")
        self.assertEqual((tokens, refused_at), (["=="], 2),
                         "the pair consumes two bytes and the lone > refuses exactly at offset 2")

        tokens, refused_at = self._sym_tokens("->> ")
        self.assertEqual((tokens, refused_at), (["->"], 2))

        tokens, refused_at = self._sym_tokens("!= >")
        self.assertEqual((tokens, refused_at), (["!="], 3))

    def test_unexpected_characters_refuse_at_their_own_offset(self):
        # `?` refusing here is the boundary with the hole scanner (the seed turns it into a Hole
        # token), not a claim that `?` is invalid Pep.
        for char in ("`", "@", "%", "^", "~", "?"):
            status, text, byte_length, next_offset, diagnostic = self._sym_at(" " + char, 1)
            self.assertEqual(status, "unsupported", char)
            self.assertEqual((text, byte_length, next_offset), (char, 0, 1), char)
            self.assertIn("unexpected character", diagnostic, char)

    def test_multibyte_unexpected_character_is_named_without_splitting(self):
        """A one-byte slice of `é` would raise PEP_RUNTIME_BYTE_BOUNDARY, so the refusal names the
        whole character instead of splitting it across a UTF-8 sequence."""
        status, text, byte_length, next_offset, diagnostic = self._sym_at("é")
        self.assertEqual(status, "unsupported")
        self.assertEqual((text, byte_length, next_offset), ("é", 0, 0))
        self.assertIn("unexpected character", diagnostic)

    def test_symbol_scan_bounds_refuse_before_reading(self):
        status, _, _, _, diagnostic = self._sym_at("()", -1)
        self.assertEqual(status, "unsupported")
        self.assertIn("negative", diagnostic)
        status, _, _, _, diagnostic = self._sym_at("()", 5)
        self.assertIn("past the end", diagnostic)
        status, _, _, _, diagnostic = self._sym_at("()", 2)
        self.assertIn("no symbol at the end", diagnostic)

    def test_symbol_count_consumer_stops_at_the_first_non_symbol(self):
        fields = self._invoke("pep-scan-sym-count", "( , [ ] )", [])
        self.assertEqual(fields["status"]["value"], "ok")
        self.assertEqual(int(fields["count"]["value"]), 5)

        fields = self._invoke("pep-scan-sym-count", "( x )", [])
        self.assertEqual(fields["status"]["value"], "unsupported")
        self.assertEqual(int(fields["count"]["value"]), 1, "one symbol before the refusal")
        self.assertEqual(int(fields["offset"]["value"]), 2, "and it names the refusing offset")


if __name__ == "__main__":
    unittest.main()
