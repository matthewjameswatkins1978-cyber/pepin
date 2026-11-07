"""Parser error contract: a failed parse must REPORT, never crash the driver.

Regression net for 98b4147. Before that commit ``parser_finish_step``
returned no nodes on failure, so the function root id reserved by
``parser_function_header_chunk`` was never emitted. When the failing
function was not the first top-level node this left an *interior* id hole
and ``parse_target``'s contiguity guard raised

    RuntimeError: Pep C23 parser AST node ids are not contiguous

instead of returning ``status=invalid``/``incomplete`` with a diagnostic.
Seven of the nine shapes below crashed the driver that way; a failing
first function only worked by accident, because its hole was leading and
the guard compares against the minimum id.

Contract pinned here:
  1. ``parse_target`` never raises on a bad source;
  2. every failure carries a non-empty ``PEP_*`` code and a span inside
     the source;
  3. ids are contiguous from 0 for success *and* failure;
  4. every ``fn`` declaration has exactly one ``kind=function`` root node,
     even when its body fails to parse (the 98b4147 placeholder).

Shape expectations also record what the grammar does *not* accept, so a
future grammar extension shows up as an intentional test change:
statement-level ``match`` with arms and int-literal patterns are outside
the accepted boundary (``match`` is an A4 *expression* form).
"""
import pathlib
import unittest

import pep_c23
from pep_c23 import Session, parse_target, require
from tests import probe_integration_case as pic
from tests.chunk_helper import fields_map

ROOT = pathlib.Path(__file__).resolve().parents[1]

OPT = "type Opt = Some(Int) | None()\n"

# name -> (source, expected status, expected code)
ERROR_SHAPES = {
    "bad_fn_alone": ("fn f() -> Int { return 1 + }\n",
                     "invalid", "PEP_PARSE_EXPRESSION"),
    "record_then_bad_fn": ("type S { a: Int }\n"
                           "fn f() -> Int { return 1 + }\n",
                           "invalid", "PEP_PARSE_EXPRESSION"),
    "good_fn_then_bad_fn": ("fn ok() -> Int { return 1 }\n"
                            "fn f() -> Int { return 1 + }\n",
                            "invalid", "PEP_PARSE_EXPRESSION"),
    "record_good_then_bad": ("type S { a: Int }\n"
                             "fn ok() -> Int { return 1 }\n"
                             "fn f() -> Int { return 1 + }\n",
                             "invalid", "PEP_PARSE_EXPRESSION"),
    "union_then_bad_fn": (OPT + "fn f() -> Int { return 1 + }\n",
                          "invalid", "PEP_PARSE_EXPRESSION"),
    "union_then_bad_arm": (OPT + "fn f(o: Opt) -> Int {\n"
                           "  return match o {\n"
                           "    Some(x) => x\n"
                           "    None() =>\n"
                           "  }\n"
                           "}\n",
                           "invalid", "PEP_PARSE_EXPRESSION"),
    "record_then_missing_brace": ("type S { a: Int }\n"
                                  "fn f() -> Int { return 1\n",
                                  "incomplete", "PEP_PARSE_EXPECTED"),
    "stmt_match_with_arms": (OPT + "fn f(o: Opt) -> Int {\n"
                             "  var r = 0\n"
                             "  match o {\n"
                             "    Some(x) => { r = x }\n"
                             "    None() => { r = 0 }\n"
                             "  }\n"
                             "  return r\n"
                             "}\n",
                             "invalid", "PEP_PARSE_EXPRESSION"),
    "int_literal_pattern": ("fn f(v: Int) -> Int {\n"
                            "  return match v {\n"
                            "    1 => 10\n"
                            "    _ => 0\n"
                            "  }\n"
                            "}\n",
                            "invalid", "PEP_PARSE_PATTERN"),
    # Frame-reserving constructs: PEP_PARSE_ELSE / PEP_PARSE_EXPECTED are
    # *inside* an open if/while frame, so the error chunk must also emit the
    # in-flight frame roots. Before 752667e these shapes left interior holes
    # (ids 8 and 14 in the first one) and the host raised 'not contiguous'.
    "if_no_else_nested": ("fn main(source: SourceBytes) -> Int {\n"
                          "  var n = 0\n"
                          "  var o = 0\n"
                          "  while !(byte_length(source) <= o) {\n"
                          "    if byte_at(source, o) == 97 {\n"
                          "      n = n + 1\n"
                          "    }\n"
                          "    o = o + 1\n"
                          "  }\n"
                          "  say(int_text(n))\n"
                          "  return 0\n"
                          "}\n",
                          "invalid", "PEP_PARSE_ELSE"),
    "if_missing_body_brace": ("fn main() -> Int {\n"
                              "  if 1 == 1 {\n"
                              "    return 1\n"
                              "  else {\n"
                              "    return 0\n"
                              "}\n",
                              "invalid", "PEP_PARSE_EXPECTED"),
}

# Unknown type names are a checker error: the parser must accept them.
VALID_SHAPES = {
    "record_then_bad_annotation": ("type S { a: Int }\n"
                                   "fn f() -> Int {\n"
                                   "  let x: Nope = 1\n"
                                   "  return x\n"
                                   "}\n"),
    "record_decl": "type S { a: Int, b: Int }\nfn main() -> Int { return 1 }\n",
    "union_decl": ("type S { a: Int }\n"
                   "type U = A1(Int, S) | A2(Int, S) | A3()\n"
                   "fn main() -> Int { return 1 }\n"),
    "return_match": ("type Opt = Some(Int) | None()\n"
                     "fn f(o: Opt) -> Int {\n"
                     "  return match o {\n"
                     "    Some(x) => x\n"
                     "    None() => 0\n"
                     "  }\n"
                     "}\n"),
}


class ParserErrorContractTests(unittest.TestCase):
    """Every bad source reports; every function has one root node."""

    @classmethod
    def setUpClass(cls):
        cls.session = Session()
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = cls.session.send({"schemaVersion": 3, "op": "open",
                                   "source": bundle, "name": "pep-c23-emitter",
                                   "metadataOnly": True})
        require(opened, "outcome", "ok", "open compiler bundle")
        require(opened, "status", "valid", "compiler bundle")
        cls.tool_revision = opened["revision"]
        cls.tool_document = opened["document"]
        # The tool host is the compiler bundle for every subject below, so it is
        # registered once; only the subject document changes per shape.
        sample = cls.session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": "error-contract-sample", "bytes": []})
        require(sample, "outcome", "ok", "open registration sample")
        pic.register(cls.session, cls.tool_document, cls.tool_revision,
                     sample["document"], sample["revision"])

    @classmethod
    def tearDownClass(cls):
        cls.session.close()

    def parse(self, source):
        """Parse one source through the real driver, returning the fields."""
        payload = source.encode("utf-8")
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                    "name": "error-contract",
                                    "bytes": list(payload)})
        require(target, "outcome", "ok", "open error-contract subject")
        parsed = parse_target(self.session, payload, target,
                              self.tool_revision)
        fields = fields_map(parsed)
        nodes = fields["nodes"]["value"]
        return payload, fields, [fields_map(node) for node in nodes]

    def assert_one_root_per_function(self, source, node_fields):
        expected = source.count("fn ")
        roots = [node for node in node_fields
                 if node["kind"]["value"] == "function"
                 and int(node["parentId"]["value"]) == -1]
        self.assertEqual(
            len(roots), expected,
            f"expected one function root per declaration ({expected}), "
            f"got {len(roots)}: {[(r['text']['value'], r['id']['value']) for r in roots]}")

    def assert_contiguous_from_zero(self, node_fields):
        ids = sorted(int(node["id"]["value"]) for node in node_fields)
        self.assertEqual(ids, list(range(len(ids))),
                         f"ids are not contiguous from 0: {ids}")

    def test_error_shapes_report_and_never_raise(self):
        for name, (source, want_status, want_code) in ERROR_SHAPES.items():
            with self.subTest(shape=name):
                try:
                    payload, fields, node_fields = self.parse(source)
                except RuntimeError as error:
                    self.fail(f"{name}: driver raised instead of reporting: {error}")
                self.assertEqual(fields["status"]["value"], want_status,
                                 f"{name}: status")
                self.assertEqual(fields["errorCode"]["value"], want_code,
                                 f"{name}: code")
                self.assertEqual(fields["done"]["value"], True, f"{name}: done")
                start = int(fields["errorStart"]["value"])
                end = int(fields["errorEnd"]["value"])
                self.assertTrue(0 <= start <= end <= len(payload),
                                f"{name}: error span {start}..{end} outside source")
                self.assertGreaterEqual(int(fields["errorLine"]["value"]), 1,
                                        f"{name}: error line")
                self.assert_contiguous_from_zero(node_fields)
                self.assert_one_root_per_function(source, node_fields)

    def test_valid_shapes_complete(self):
        for name, source in VALID_SHAPES.items():
            with self.subTest(shape=name):
                _, fields, node_fields = self.parse(source)
                self.assertEqual(fields["status"]["value"], "complete",
                                 f"{name}: status")
                self.assertEqual(fields["errorCode"]["value"], "", f"{name}: code")
                self.assert_contiguous_from_zero(node_fields)
                self.assert_one_root_per_function(source, node_fields)

    def test_failure_after_valid_function_keeps_both_roots(self):
        """The 98b4147 crash: a good function followed by a broken one."""
        source = ("fn ok() -> Int { return 7 }\n"
                  "fn broken() -> Int { return 1 + }\n")
        _, fields, node_fields = self.parse(source)
        self.assertEqual(fields["status"]["value"], "invalid")
        names = [node["text"]["value"] for node in node_fields
                 if node["kind"]["value"] == "function"]
        self.assertEqual(sorted(names), ["broken", "ok"],
                         f"missing function root(s); got {names}")


if __name__ == "__main__":
    unittest.main()
