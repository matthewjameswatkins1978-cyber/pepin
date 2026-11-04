"""Where does the checker's step budget actually run out?

The budget error reports a line:column into the concatenated compiler bundle,
so the location identifies the checker function that was executing when the
budget expired. That is a measured hot spot rather than a guess, and this test
pins it: if per-node cost work succeeds, the site moves and this fails,
forcing a re-measure.
"""
import pathlib
import re
import unittest

import pep_c23
from pep_c23 import Session, require, parse_target
from tests.chunk_helper import fields_map, nval

ROOT = pathlib.Path(__file__).resolve().parents[1]
FN_RE = re.compile(r"^\s*fn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
LOCATION_RE = re.compile(r"at (\d+):(\d+)")

RECPAD6 = "".join(
    f"type P{i} {{ x: Int }}\nfn mk{i}(v: Int) -> P{i} {{\n"
    f"  return P{i} {{ x: v }}\n}}\n" for i in range(6))


def bundle_lines():
    return "\n".join(p.read_text(encoding="utf-8")
                     for p in pep_c23.SOURCES).split("\n")


def function_spans(lines):
    spans = []
    for start, text in enumerate(lines, start=1):
        match = FN_RE.match(text)
        if not match:
            continue
        depth, started = 0, False
        for scan in range(start - 1, len(lines)):
            depth += lines[scan].count("{") - lines[scan].count("}")
            if "{" in lines[scan]:
                started = True
            if started and depth <= 0:
                spans.append((match.group(1), start, scan + 1, scan + 1))
                break
    return spans


def enclosing(spans, line):
    hits = [span for span in spans if span[1] <= line <= span[2]]
    if not hits:
        return None
    return min(hits, key=lambda span: span[2] - span[1])


class CheckerCostProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = Session()
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = cls.session.send({"schemaVersion": 3, "op": "open",
                                   "source": bundle, "name": "pep-c23",
                                   "metadataOnly": True})
        require(opened, "outcome", "ok", "open compiler bundle")
        cls.revision = opened["revision"]
        document = opened["document"]
        sample = cls.session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": "validate", "bytes": []})
        target = {"document": sample["document"], "revision": sample["revision"],
                  "entryFunctions": []}
        finished = pep_c23.parser_cursor_value(sample["document"],
                                               sample["revision"], done=True,
                                               lex_done=True, lex_stage="done")
        for tool, function, arguments, expected in [
                ("pep-c23-parser-start", "parser_start", [],
                 pep_c23.parser_cursor_value(sample["document"], sample["revision"])),
                ("pep-c23-parser-step", "parser_step", [finished],
                 pep_c23.parser_chunk_value(sample["document"], sample["revision"],
                                            finished)),
                ("pep-c23-checker", "analyze_parsed",
                 [pep_c23.parser_progress(sample["document"], sample["revision"])],
                 pep_c23.checker_report(sample["document"], sample["revision"]))]:
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                              "op": "tool_register", "tool": tool,
                              "document": document, "revision": cls.revision,
                              "function": function})
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                              "op": "tool_validate", "tool": tool,
                              "document": document, "revision": cls.revision,
                              "testVectors": [{"arguments": arguments,
                                               "expect": expected,
                                               "semanticTarget": target}]})
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                              "op": "tool_activate", "tool": tool,
                              "document": document, "revision": cls.revision})
        cls.lines = bundle_lines()
        cls.spans = function_spans(cls.lines)

    @classmethod
    def tearDownClass(cls):
        cls.session.process.stdin.close()
        cls.session.process.terminate()

    def test_recpad6_budget_expires_in_record_declaration_lookup(self):
        # 66-node whole-program check: the budget expires inside the linear
        # node scan of record_declaration, not in a type-inference walk. That
        # makes repeated O(n) name lookups the per-node cost to attack.
        source = RECPAD6.encode("utf-8")
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                    "name": "recpad6", "bytes": list(source)})
        self.assertEqual(target.get("outcome"), "ok", target)
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": []}
        parsed = parse_target(self.session, source, target, self.revision)
        response = self.session.send(
            {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
             "tool": "pep-c23-checker", "arguments": [parsed],
             "semanticTarget": sem})
        self.assertEqual(response.get("outcome"), "error", response)
        error = response.get("error") or {}
        self.assertEqual(error.get("code"), "PEP_RUNTIME_STEP_LIMIT")
        match = LOCATION_RE.search(error.get("message", ""))
        self.assertIsNotNone(match, error.get("message"))
        line = int(match.group(1))
        where = enclosing(self.spans, line)
        self.assertIsNotNone(where, f"line {line} is outside every function")
        name, start, end, _ = where
        self.assertEqual(name, "record_declaration",
                         f"budget now expires in {name}() [{start}..{end}]: "
                         f"{self.lines[line - 1].strip()!r}")

    def test_flat_ast_ids_are_dense_and_ascending(self):
        # lookup_node() scans the whole list by id. Because ids are dense
        # 0..n-1 and the list is ascending, an indexed access would make the
        # 31 lookup_node call sites O(1) instead of O(n). Pep exposes no list
        # index, so this is only reachable through the host; the fact is
        # pinned here so the option stays visible and measurable.
        source = (ROOT / "examples" / "pep_lexer.pep").read_bytes()
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                     "name": "id-shape", "bytes": list(source)})
        self.assertEqual(target.get("outcome"), "ok", target)
        parsed = parse_target(self.session, source, target, self.revision)
        nodes = fields_map(parsed)["nodes"]["value"]
        ids = [int(nval(n, "id")) for n in nodes]
        self.assertEqual(ids, list(range(len(ids))))

    def test_no_single_scan_helper_dominates_the_budget(self):
        # Diagnostic ablation: record_declaration is where the unmodified
        # checker happens to expire first, not the dominant cost. Replacing
        # its body with a constant does not raise the ceiling - the failure
        # migrates to union_declaration at 66 nodes and then through
        # child_at, lookup_node, type_shape_at, collect_bindings,
        # collect_functions and count_children as the program grows.
        # So per-node cost is distributed across the whole scan family and a
        # real fix must index every node lookup, not hoist one function.
        checker = (ROOT / "tests" / "pep_checker_a13.pep").read_text(encoding="utf-8")
        original = checker[checker.index("fn record_declaration("):]
        original = original[:original.index("\n}\n") + 3]
        stub = ("fn record_declaration(nodes: List[FlatAstNode], name: Str) -> NodeLookup {\n"
                "  return NodeLookup { found: false, node: empty_node() }\n}\n")
        self.assertNotEqual(original, stub)
        parts = []
        for path in pep_c23.SOURCES:
            text = path.read_text(encoding="utf-8")
            if path.name == "pep_checker_a13.pep":
                text = checker.replace(original, stub, 1)
            parts.append(text)
        bundle = "\n".join(parts)
        lines = bundle.split("\n")
        spans = function_spans(lines)

        session = Session()
        try:
            opened = session.send({"schemaVersion": 3, "op": "open",
                                   "source": bundle, "name": "stub-bundle",
                                   "metadataOnly": True})
            require(opened, "outcome", "ok", "open stub bundle")
            revision, document = opened["revision"], opened["document"]
            sample = session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": "validate", "bytes": []})
            target = {"document": sample["document"],
                      "revision": sample["revision"], "entryFunctions": []}
            finished = pep_c23.parser_cursor_value(
                sample["document"], sample["revision"], done=True,
                lex_done=True, lex_stage="done")
            for tool, function, arguments, expected in [
                    ("pep-c23-parser-start", "parser_start", [],
                     pep_c23.parser_cursor_value(sample["document"],
                                                 sample["revision"])),
                    ("pep-c23-parser-step", "parser_step", [finished],
                     pep_c23.parser_chunk_value(sample["document"],
                                                sample["revision"], finished)),
                    ("pep-c23-checker", "analyze_parsed",
                     [pep_c23.parser_progress(sample["document"],
                                              sample["revision"])],
                     pep_c23.checker_report(sample["document"],
                                            sample["revision"]))]:
                for op, payload in [
                        ("tool_register", {"tool": tool, "function": function}),
                        ("tool_validate", {"tool": tool,
                                           "testVectors": [{
                                               "arguments": arguments,
                                               "expect": expected,
                                               "semanticTarget": target}]}),
                        ("tool_activate", {"tool": tool})]:
                    session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                  "op": op, "document": document,
                                  "revision": revision, **payload})

            def site_for(k):
                raw = "".join(
                    f"type P{i} {{ x: Int }}\nfn mk{i}(v: Int) -> P{i} {{\n"
                    f"  return P{i} {{ x: v }}\n}}\n"
                    for i in range(k)).encode("utf-8")
                opened_target = session.send(
                    {"schemaVersion": 3, "op": "open_bytes",
                     "name": f"stub{k}", "bytes": list(raw)})
                self.assertEqual(opened_target.get("outcome"), "ok",
                                 opened_target)
                sem = {"document": opened_target["document"],
                       "revision": opened_target["revision"],
                       "entryFunctions": []}
                parsed = parse_target(session, raw, opened_target, revision)
                response = session.send(
                    {"schemaVersion": 3, "toolProtocolVersion": 2,
                     "op": "tool_invoke", "tool": "pep-c23-checker",
                     "arguments": [parsed], "semanticTarget": sem})
                if response.get("outcome") == "ok":
                    return "valid"
                error = response.get("error") or {}
                match = LOCATION_RE.search(error.get("message", ""))
                if not match:
                    return error.get("code")
                where = enclosing(spans, int(match.group(1)))
                return where[0] if where else "(top level)"

            first = site_for(6)
            self.assertNotEqual(first, "record_declaration",
                                "stubbing record_declaration should move the "
                                "budget elsewhere")
            self.assertIn(first, {"union_declaration", "child_at",
                                  "lookup_node", "type_shape_at",
                                  "collect_bindings", "collect_functions",
                                  "count_children"}, first)
        finally:
            session.process.stdin.close()
            session.process.terminate()

    def test_scanning_lookup_helpers_are_the_documented_hot_set(self):
        # Census of helpers that rescan the whole node list on every call.
        # Each is O(n) per call and several are called from inside node
        # loops, so their call-site counts bound the per-node multiplier.
        scanning = {}
        for name, start, end, _ in self.spans:
            body = "\n".join(self.lines[start - 1:end])
            if "for node in nodes {" in body or "for row in nodes {" in body:
                scanning[name] = body
        for expected in ("record_declaration", "lookup_node", "child_at",
                         "is_constructor", "count_children", "type_shape_at",
                         "union_declaration", "variant_declaration"):
            self.assertIn(expected, scanning)
        call_sites = {}
        for name in scanning:
            count = 0
            for text in self.lines:
                if FN_RE.match(text):
                    continue
                if re.search(rf"\b{re.escape(name)}\s*\(", text):
                    count += 1
            call_sites[name] = count
        # Pinned: child_at and lookup_node dominate. A drop here means the
        # lookups were indexed and the census must be re-measured.
        self.assertEqual(call_sites["child_at"], 71)
        self.assertEqual(call_sites["lookup_node"], 31)


if __name__ == "__main__":
    unittest.main()
