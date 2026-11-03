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

fn scan_probe_comment(offset: Int) -> ScanComment {
  return scan_comment_at(source_bytes(), offset)
}

fn scan_probe_hole(offset: Int) -> ScanHole {
  return scan_hole_at(source_bytes(), offset)
}

fn scan_probe_utf8() -> ScanUtf8 {
  return scan_utf8_valid(source_bytes())
}

fn scan_probe_pos(offset: Int) -> ScanPos {
  return scan_position_at(source_bytes(), offset)
}

fn scan_probe_kind(offset: Int) -> ScanKind {
  return scan_classify(source_bytes(), offset)
}

fn lex_probe() -> LexResult {
  return lex_source(source_bytes())
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
        cls._register("pep-scan-comment", "scan_probe_comment", [typed("Int", 0)],
                      typed_record_value("ScanComment", [
                          ("status", typed("Str", "unsupported")),
                          ("diagnostic", typed("Str",
                                               "Pep scan found no comment at the end of the source")),
                          ("byteLength", typed("Int", "0")),
                          ("nextOffset", typed("Int", "0")),
                      ]))
        cls._register("pep-scan-hole", "scan_probe_hole", [typed("Int", 0)],
                      typed_record_value("ScanHole", [
                          ("status", typed("Str", "unsupported")),
                          ("diagnostic", typed("Str",
                                               "Pep scan found no hole marker at the end of the source")),
                          ("name", typed("Str", "")),
                          ("byteLength", typed("Int", "0")),
                          ("nextOffset", typed("Int", "0")),
                      ]))
        cls._register("pep-scan-utf8", "scan_probe_utf8", [],
                      typed_record_value("ScanUtf8", [
                          ("valid", typed("Bool", True)),
                          ("errorOffset", typed("Int", "-1")),
                      ]))
        cls._register("pep-scan-pos", "scan_probe_pos", [typed("Int", 0)],
                      typed_record_value("ScanPos", [
                          ("status", typed("Str", "ok")),
                          ("diagnostic", typed("Str", "")),
                          ("line", typed("Int", "1")),
                          ("column", typed("Int", "1")),
                      ]))
        cls._register("pep-scan-kind", "scan_probe_kind", [typed("Int", 0)],
                      typed_record_value("ScanKind", [
                          ("status", typed("Str", "ok")),
                          ("diagnostic", typed("Str", "")),
                          ("kind", typed("Str", "eof")),
                          ("byteLength", typed("Int", "0")),
                          ("nextOffset", typed("Int", "0")),
                      ]))
        cls._register("pep-lex", "lex_probe", [],
                      typed_record_value("LexResult", [
                          ("status", typed("Str", "ok")),
                          ("errorCode", typed("Str", "")),
                          ("sourceBytes", typed("Int", "0")),
                          ("errorStart", typed("Int", "-1")),
                          ("errorEnd", typed("Int", "-1")),
                          ("errorLine", typed("Int", "-1")),
                          ("errorColumn", typed("Int", "-1")),
                          ("tokens", {"type": "List[LexToken]", "value": [
                              typed_record_value("LexToken", [
                                  ("kind", typed("Str", "eof")),
                                  ("text", typed("Str", "")),
                                  ("integerValue", typed("Int", "0")),
                                  ("stringParts", {"type": "List[Str]", "value": []}),
                                  ("startByte", typed("Int", "0")),
                                  ("endByte", typed("Int", "0")),
                                  ("line", typed("Int", "1")),
                                  ("column", typed("Int", "1")),
                              ])
                          ]}),
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
        raw = payload if isinstance(payload, bytes) else payload.encode("utf-8")
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

    def test_unescaped_newline_refuses_with_its_own_diagnostic(self):
        """Split from the EOF case because the seed reports PEP_NEWLINE_IN_STRING here and
        PEP_UNTERMINATED_STRING there -- the driver maps diagnostics onto those codes."""
        status, parts, _, _, diagnostic = self._string_at('"abc\ndef"')
        self.assertEqual(status, "unsupported")
        self.assertIn("newline", diagnostic)
        _, _, _, _, eof_diagnostic = self._string_at('"abc')
        self.assertIn("unterminated", eof_diagnostic)

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


    def _comment_at(self, payload, offset=0):
        fields = self._invoke("pep-scan-comment", payload, [typed("Int", offset)])
        return (fields["status"]["value"], int(fields["byteLength"]["value"]),
                int(fields["nextOffset"]["value"]), fields["diagnostic"]["value"])

    def _hole_at(self, payload, offset=0):
        fields = self._invoke("pep-scan-hole", payload, [typed("Int", offset)])
        return (fields["status"]["value"], fields["name"]["value"],
                int(fields["byteLength"]["value"]), int(fields["nextOffset"]["value"]),
                fields["diagnostic"]["value"])

    def _utf8(self, payload):
        fields = self._invoke("pep-scan-utf8", payload, [])
        return (fields["valid"]["value"], int(fields["errorOffset"]["value"]))

    def _pos(self, payload, offset=0):
        fields = self._invoke("pep-scan-pos", payload, [typed("Int", offset)])
        return (fields["status"]["value"], int(fields["line"]["value"]),
                int(fields["column"]["value"]), fields["diagnostic"]["value"])

    def _kind(self, payload, offset=0):
        fields = self._invoke("pep-scan-kind", payload, [typed("Int", offset)])
        return (fields["status"]["value"], fields["kind"]["value"],
                int(fields["byteLength"]["value"]), int(fields["nextOffset"]["value"]),
                fields["diagnostic"]["value"])

    def test_comment_runs_to_the_newline_and_leaves_it(self):
        # Measured: a full-line comment before `let a = 1;` puts that statement at line 2 column 1.
        status, byte_length, next_offset, _ = self._comment_at("# trailing words")
        self.assertEqual((status, byte_length, next_offset), ("ok", 16, 16))
        status, byte_length, next_offset, _ = self._comment_at("// ab\ncd")
        self.assertEqual((status, byte_length, next_offset), ("ok", 5, 5), "stops AT the newline")
        status, _, _, diagnostic = self._comment_at("plain")
        self.assertEqual(status, "unsupported")
        self.assertIn("no comment", diagnostic)

    def test_double_slash_is_a_comment_but_a_lone_slash_is_division(self):
        # Measured: `let a = 6 / 2;` checks valid, so a single slash must classify as a symbol.
        status, kind, byte_length, _, _ = self._kind("// x")
        self.assertEqual((status, kind, byte_length), ("ok", "comment", 4))
        status, kind, byte_length, next_offset, _ = self._kind("/")
        self.assertEqual((status, kind, byte_length, next_offset), ("ok", "symbol", 1, 1))

    def test_hole_scanning_matches_the_seed_shapes(self):
        # Measured against check --json: bare `?` is a 1-byte unnamed hole; `?name` spans 5 bytes;
        # `?9` is a 1-byte bare hole followed by the number 9.
        status, name, byte_length, _, _ = self._hole_at("?")
        self.assertEqual((status, name, byte_length), ("ok", "", 1))
        status, name, byte_length, _, _ = self._hole_at("?name")
        self.assertEqual((status, name, byte_length), ("ok", "name", 5))
        status, name, byte_length, _, _ = self._hole_at("?9")
        self.assertEqual((status, name, byte_length), ("ok", "", 1), "a digit does not join the name")
        status, name, byte_length, _, _ = self._hole_at("?_x9")
        self.assertEqual((status, name, byte_length), ("ok", "_x9", 4))
        status, _, _, _, diagnostic = self._hole_at("x")
        self.assertEqual(status, "unsupported")
        self.assertIn("no hole marker", diagnostic)

    def test_utf8_validation_reproduces_the_seed_offsets(self):
        # Measured PEP_INVALID_UTF8 offsets for these exact byte strings: 15, 16, 15, 15, and a
        # truncated lead at end of source reports at its own offset (3), all via pep.ps1 check.
        pre = b"let a = [1, 2, "
        self.assertEqual(self._utf8(pre + b"\x80" + b"];"), (False, 15),
                         "raw continuation byte at its own offset")
        self.assertEqual(self._utf8(pre + b"\xc3" + b"];"), (False, 16),
                         "non-continuation after a lead reports at that byte")
        self.assertEqual(self._utf8(pre + b"\xc0\x80" + b"];"), (False, 15), "overlong at the lead")
        self.assertEqual(self._utf8(pre + b"\xf8\x88\x80\x80\x80" + b"];"), (False, 15),
                         "width-0 lead at the lead")
        self.assertEqual(self._utf8(pre + b"\xed\xa0\x80" + b"];"), (False, 15),
                         "UTF-16 surrogate sequence reported at its lead")
        self.assertEqual(self._utf8(b"abc\xc3"), (False, 3), "truncated lead at end of source")
        self.assertEqual(self._utf8(pre + b"\xc3\xa9" + b"];"), (True, -1), "valid e-acute passes")
        self.assertEqual(self._utf8(b""), (True, -1))

    def test_position_tracking_matches_measured_seed_spans(self):
        crlf = "let a = 1\r\nlet b = <;"
        cr = "let a = 1\rlet b = <;"
        # Measured: the same error byte reports line 2 column 9 under CRLF but line 1 column 20
        # under a lone CR -- only byte 10 starts a line.
        self.assertEqual(self._pos(crlf, 19), ("ok", 2, 9, ""))
        self.assertEqual(self._pos(cr, 19), ("ok", 1, 20, ""))
        # Measured EOF spans: `let a =` errors at line 1 column 8; `let a =\n` at line 2 column 1.
        self.assertEqual(self._pos("let a =", 7), ("ok", 1, 8, ""))
        self.assertEqual(self._pos("let a =\n", 8), ("ok", 2, 1, ""))
        self.assertEqual(self._pos("", 0), ("ok", 1, 1, ""))
        status, _, _, diagnostic = self._pos("x", -1)
        self.assertEqual(status, "unsupported")
        self.assertIn("negative", diagnostic)

    def test_classify_ladder_names_every_input_class(self):
        cases = [
            ("  x", 0, "space", 2, "ok"),
            ("  x", 2, "identifier", 1, "ok"),
            ("123", 0, "integer", 3, "ok"),
            ("99999999999999999999", 0, "integer", 0, "unsupported"),
            ('"s"', 0, "string", 3, "ok"),
            ("?h", 0, "hole", 2, "ok"),
            ("<=", 0, "symbol", 2, "ok"),
            ("@", 0, "unexpected", 0, "unsupported"),
            ("# c", 0, "comment", 3, "ok"),
            ("", 0, "eof", 0, "ok"),
        ]
        for payload, offset, expected_kind, expected_length, expected_status in cases:
            with self.subTest(payload=payload, offset=offset):
                status, kind, byte_length, _, _ = self._kind(payload, offset)
                self.assertEqual((status, kind, byte_length),
                                 (expected_status, expected_kind, expected_length))


    def _lex(self, payload):
        fields = self._invoke("pep-lex", payload, [])
        tokens = []
        for item in fields["tokens"]["value"]:
            entry = {field["name"]: field["value"] for field in item["fields"]}
            parts = [part["value"] for part in entry["stringParts"]["value"]]
            tokens.append((entry["kind"]["value"], entry["text"]["value"],
                           int(entry["integerValue"]["value"]), parts,
                           int(entry["startByte"]["value"]), int(entry["endByte"]["value"]),
                           int(entry["line"]["value"]), int(entry["column"]["value"])))
        return (fields["status"]["value"], fields["errorCode"]["value"],
                int(fields["sourceBytes"]["value"]), int(fields["errorStart"]["value"]),
                int(fields["errorEnd"]["value"]), int(fields["errorLine"]["value"]),
                int(fields["errorColumn"]["value"]), tokens)

    def test_driver_tokenises_a_real_statement_with_positions(self):
        status, code, source_bytes, error_start, _, _, _, tokens = self._lex("let a = 1;")
        self.assertEqual((status, code), ("ok", ""))
        self.assertEqual(source_bytes, 10)
        self.assertEqual(error_start, -1, "a clean run reports no error position")
        self.assertEqual([(k, t, v, s, e, l, c) for k, t, v, _, s, e, l, c in tokens],
                         [("identifier", "let", 0, 0, 3, 1, 1),
                          ("identifier", "a", 0, 4, 5, 1, 5),
                          ("symbol", "=", 0, 6, 7, 1, 7),
                          ("integer", "", 1, 8, 9, 1, 9),
                          ("symbol", ";", 0, 9, 10, 1, 10),
                          ("eof", "", 0, 10, 10, 1, 11)])

    def test_driver_token_shapes_match_the_canonical_lexer(self):
        """Canonical semantics from examples/pep_lexer.pep: integers and strings carry text \"\",
        a bare `_` word is a hole, comments emit no token, and string fragments carry the ordered
        NUL (the canonical lexer prepends \"\\0\" the same way)."""
        payload = 'x _ = "s\\0" ?n # gone\n99'
        status, code, _, _, _, _, _, tokens = self._lex(payload)
        self.assertEqual((status, code), ("ok", ""))
        self.assertEqual([t[0] for t in tokens],
                         ["identifier", "hole", "symbol", "string", "hole", "integer", "eof"])
        self.assertEqual(tokens[1], ("hole", "", 0, [], 2, 3, 1, 3), "bare `_` has no name")
        self.assertEqual(tokens[3], ("string", "", 0, ["s", "\x00"], 6, 11, 1, 7))
        self.assertEqual(tokens[4], ("hole", "n", 0, [], 12, 14, 1, 13))
        self.assertEqual(tokens[5], ("integer", "", 99, [], 22, 24, 2, 1),
                         "value in integerValue, text stays empty, line 2 after the comment")
        self.assertEqual(tokens[6], ("eof", "", 0, [], 24, 24, 2, 3))

    def test_driver_reports_explicit_seed_error_codes(self):
        status, code, _, start, end, line, column, tokens = self._lex("@")
        self.assertEqual((status, code), ("error", "PEP_UNEXPECTED_CHARACTER"))
        self.assertEqual((start, end, line, column, tokens), (0, 0, 1, 1, []))

        status, code, _, start, _, _, _, tokens = self._lex('"abc')
        self.assertEqual((status, code), ("error", "PEP_UNTERMINATED_STRING"))
        self.assertEqual((start, tokens), (0, []))

        status, code, _, start, _, _, _, _ = self._lex('"a\nb"')
        self.assertEqual((status, code), ("error", "PEP_NEWLINE_IN_STRING"))
        self.assertEqual(start, 0, "string errors report from the token start, like the seed")

        status, code, _, start, end, _, _, _ = self._lex('"bad\\q"')
        self.assertEqual((status, code), ("error", "PEP_INVALID_ESCAPE"))

        status, code, _, start, end, _, _, _ = self._lex("99999999999999999999")
        self.assertEqual((status, code), ("error", "PEP_INT_LITERAL_RANGE"))
        self.assertEqual((start, end), (0, 18))

        status, code, _, start, end, line, column, _ = self._lex(b"let a = \x80;")
        self.assertEqual((status, code), ("error", "PEP_INVALID_UTF8"))
        self.assertEqual((start, end, line, column), (8, 9, 1, 9))

    def test_driver_empty_source_returns_only_eof(self):
        status, code, source_bytes, _, _, _, _, tokens = self._lex("")
        self.assertEqual((status, code, source_bytes), ("ok", "", 0))
        self.assertEqual(tokens, [("eof", "", 0, [], 0, 0, 1, 1)])

    def test_driver_multiline_positions_follow_only_lf(self):
        """Measured seed rule: only byte 10 starts a line -- `a\r\nb\rc` puts b at line 2 column 1
        and keeps c on line 2 (a lone CR only advances the column)."""
        _, _, _, _, _, _, _, tokens = self._lex("a\r\nb\rc")
        self.assertEqual([(t[0], t[4], t[5], t[6], t[7]) for t in tokens],
                         [("identifier", 0, 1, 1, 1),
                          ("identifier", 3, 4, 2, 1),
                          ("identifier", 5, 6, 2, 3),
                          ("eof", 6, 6, 2, 4)])


if __name__ == "__main__":
    unittest.main()
