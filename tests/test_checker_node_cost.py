"""How much AST does one checker invocation actually afford?

Measured answer at `4ef8cbf`: the Pep-written A13 checker spends roughly
1,000 interpreter steps per AST node, so an invocation tops out near 100
nodes under the unchanged 100,000-step budget — regardless of which
construct the nodes belong to.

The three cases below bracket that with real lexer declarations:

- the five real lexer type declarations plus a trivial `main` (90 nodes)
  check valid;
- the same declarations plus a two-field `SourcePosition` literal and one
  field read (101 nodes) stop on the step budget;
- the same with a locally declared two-field record (102 nodes) stop too.

Two consequences this pins, both of which cost real money if forgotten:

1. `make_cursor` (103), `make_progress` (125), `utf8_check` (268) and
   `lexer_step` (1,513) do not fit because of *volume*, not because of an
   exotic construct. Micro-optimising one construct cannot buy 3x.
2. A chunk plan that carries the shared declaration closure into every body
   chunk spends most of its node budget on declarations. Clearing the hot
   functions needs checker-certified *external type declarations*, exactly
   as external function signatures already work, so a body chunk is just
   the body.

If a change moves any of these, the assertion fails on purpose: re-measure
and update the numbers rather than widening the limits.
"""
import pathlib
import unittest

import pep_c23
from pep_c23 import Session, parse_target, require

ROOT = pathlib.Path(__file__).resolve().parents[1]
NL = chr(10)

DECLARATIONS = """type SourcePosition { line: Int, column: Int }
type Utf8Check { width: Int, invalidOffset: Int }
type LexToken {
  kind: Str,
  text: Str,
  integerValue: Int,
  stringParts: List[Str],
  startByte: Int,
  endByte: Int,
  line: Int,
  column: Int
}
type LexCursor {
  document: Str,
  revision: Str,
  status: Str,
  stage: Str,
  offset: Int,
  line: Int,
  column: Int,
  mode: Str,
  tokenStart: Int,
  tokenLine: Int,
  tokenColumn: Int,
  integerValue: Int,
  integerOverflow: Bool,
  escapePending: Bool,
  stringPartStart: Int,
  stringPartsReversed: List[Str]
}
type LexProgress {
  document: Str,
  revision: Str,
  status: Str,
  tokens: List[LexToken],
  cursor: LexCursor,
  done: Bool,
  errorCode: Str,
  errorStart: Int,
  errorEnd: Int,
  errorLine: Int,
  errorColumn: Int
}
"""

CASES = {
    "declarations + trivial main": (
        "fn main() -> Int {" + NL + "  return 0" + NL + "}" + NL,
        "valid", 90),
    "declarations + two-field record literal and field read": (
        "fn pos() -> SourcePosition {" + NL
        + "  return SourcePosition { line: 1, column: 2 }" + NL + "}" + NL
        + "fn main() -> Int {" + NL + "  let p = pos()" + NL
        + "  return p.line" + NL + "}" + NL,
        "PEP_RUNTIME_STEP_LIMIT", 101),
    "declarations + local two-field record": (
        "type Small { a: Int, b: Int }" + NL
        + "fn main() -> Int {" + NL + "  let s = Small { a: 1, b: 2 }" + NL
        + "  return s.a" + NL + "}" + NL,
        "PEP_RUNTIME_STEP_LIMIT", 102),
}


class CheckerNodeCostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = Session()
        bundle = NL.join(path.read_text(encoding="utf-8") for path in pep_c23.SOURCES)
        opened = cls.session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                                    "name": "pep-c23", "metadataOnly": True})
        require(opened, "outcome", "ok", "open compiler bundle")
        cls.tool_revision = opened["revision"]
        tool_document = opened["document"]
        sample = cls.session.send({"schemaVersion": 3, "op": "open_bytes",
                                    "name": "validate", "bytes": []})
        target_spec = {"document": sample["document"], "revision": sample["revision"],
                       "entryFunctions": []}
        start_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"])
        finished_cursor = pep_c23.parser_cursor_value(
            sample["document"], sample["revision"], done=True, lex_done=True, lex_stage="done")
        empty_pp = pep_c23.parser_progress(sample["document"], sample["revision"])
        empty_rep = pep_c23.checker_report(sample["document"], sample["revision"])
        for tool, function, arguments, expected in [
                ("pep-c23-parser-start", "parser_start", [], start_cursor),
                ("pep-c23-parser-step", "parser_step", [finished_cursor],
                 pep_c23.parser_chunk_value(sample["document"], sample["revision"],
                                            finished_cursor)),
                ("pep-c23-checker", "analyze_parsed", [empty_pp], empty_rep)]:
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_register",
                              "tool": tool, "document": tool_document,
                              "revision": cls.tool_revision, "function": function})
            validated = cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                           "op": "tool_validate", "tool": tool,
                                           "document": tool_document,
                                           "revision": cls.tool_revision,
                                           "testVectors": [{"arguments": arguments,
                                                            "expect": expected,
                                                            "semanticTarget": target_spec}]})
            require(validated, "outcome", "ok", f"validate {tool}")
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                              "op": "tool_activate", "tool": tool,
                              "document": tool_document, "revision": cls.tool_revision})

    @classmethod
    def tearDownClass(cls):
        cls.session.process.stdin.close()
        cls.session.process.terminate()

    def measure(self, label):
        body, expected, expected_nodes = CASES[label]
        source = DECLARATIONS + body
        src = source.encode("utf-8")
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                     "name": "node-cost", "bytes": list(src)})
        self.assertEqual(target.get("outcome"), "ok", target)
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": []}
        parsed = parse_target(self.session, src, target, self.tool_revision)
        nodes = self.session.parser_measurements["parser_node_count"]
        checked = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_invoke", "tool": "pep-c23-checker",
                                      "arguments": [parsed], "semanticTarget": sem})
        if checked.get("outcome") != "ok":
            result = checked.get("error", {}).get("code")
        else:
            result = None
            for field in checked["result"]["fields"]:
                if field["name"] == "status":
                    result = field["value"]["value"]
        return result, nodes, expected, expected_nodes

    def test_each_case_matches_the_pinned_measurement(self):
        for label in CASES:
            with self.subTest(case=label):
                result, nodes, expected, expected_nodes = self.measure(label)
                self.assertEqual(nodes, expected_nodes,
                                 f"{label}: node count moved from {expected_nodes}")
                self.assertEqual(result, expected, f"{label}: checker result moved")

    def test_a_hundred_nodes_is_the_practical_ceiling(self):
        # 90 nodes pass, 101/102 stop: the affordance is volume, not construct.
        values = {label: self.measure(label)[1] for label in CASES}
        self.assertLess(values["declarations + trivial main"], 100)
        for label, count in values.items():
            if label != "declarations + trivial main":
                self.assertGreaterEqual(count, 100)
                self.assertLess(count, 110)


if __name__ == "__main__":
    unittest.main()
