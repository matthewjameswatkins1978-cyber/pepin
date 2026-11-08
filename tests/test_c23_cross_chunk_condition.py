"""Cross-chunk calls in expression positions (conditions and var initialisers) — A2-S1.

A1's scope check (issue #16) established that `checked.calls`/`checked.functions`
already carry the callee signature in every per-slice report, so the emitter must
resolve a callee living in another checked chunk *inside* a binary condition or a
var initialiser — not only at direct-return/let-initialiser positions. The plain
`pep_c23_expression` path refuses such a call with:

    Pep C23 calls require a known target

and `pep_c23_expression_checked` must now re-lower the enclosing binary/unary
expression operand-by-operand (source-order and error-order preserved), routing
each call through `pep_c23_cross_chunk_call`.

Contract pinned here: a slice that drops the callee's `functions` fact refuses
fail-closed; a slice that carries it emits byte-identically to the whole file.
"""

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target, typed  # noqa: E402

CONDITION_SOURCE = ("fn helper() -> Int { return 1 }\n"
                    "fn main() -> Int {\n"
                    "  var r = 0\n"
                    "  if helper() == 1 { r = 1 } else { r = 2 }\n"
                    "  return r\n"
                    "}\n").encode()

VAR_INIT_SOURCE = ("fn helper() -> Int { return 1 }\n"
                   "fn main() -> Int {\n"
                   "  var flag = helper()\n"
                   "  var r = 0\n"
                   "  if flag == 1 { r = 1 } else { r = 2 }\n"
                   "  return r\n"
                   "}\n").encode()

TRANSITIVE_SOURCE = ("fn helper2() -> Int { return 7 }\n"
                     "fn helper() -> Int { return helper2() }\n"
                     "fn main() -> Int {\n"
                     "  var r = 0\n"
                     "  if helper() == 7 { r = 1 } else { r = 2 }\n"
                     "  return r\n"
                     "}\n").encode()


def _fields_map(value):
    return {item["name"]: item["value"] for item in value["fields"]}


@unittest.skipUnless((ROOT / "pep.ps1").is_file(), "pep.ps1 required")
class CrossChunkExpressionPositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = Session()
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = cls.session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                                   "name": "pep-c23-emitter", "metadataOnly": True})
        require(opened, "outcome", "ok", "open bundle")
        cls.tool_document = opened["document"]
        cls.tool_revision = opened["revision"]
        sample = cls.session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": "xchunk-cond-sample", "bytes": []})
        sd, sr = sample["document"], sample["revision"]
        cls.target_spec = {"document": sd, "revision": sr, "entryFunctions": []}
        empty_parsed = pep_c23.parser_progress(sd, sr)
        empty_checked = pep_c23.checker_report(sd, sr)
        refused = pep_c23.typed_record("unsupported", (),
                                       "Pep C23 emission requires a top-level function named main")
        c0 = pep_c23.parser_cursor_value(sd, sr)
        c1 = pep_c23.parser_cursor_value(sd, sr, done=True, lex_done=True, lex_stage="done")
        for tool, fn, args, exp in [
            ("pep-c23-parser-start", "parser_start", [], c0),
            ("pep-c23-parser-step", "parser_step", [c1], pep_c23.parser_chunk_value(sd, sr, c1)),
            ("pep-c23-checker", "analyze_parsed", [empty_parsed], empty_checked),
            ("pep-c23-unit", "emit_c23_function_unit",
             [empty_parsed, empty_checked, typed("Int", 0)], refused),
        ]:
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                              "op": "tool_register", "tool": tool,
                              "document": cls.tool_document, "revision": cls.tool_revision,
                              "function": fn})
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                              "op": "tool_validate", "tool": tool,
                              "document": cls.tool_document, "revision": cls.tool_revision,
                              "testVectors": [{"arguments": args, "expect": exp,
                                               "semanticTarget": cls.target_spec}]})
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                              "op": "tool_activate", "tool": tool,
                              "document": cls.tool_document, "revision": cls.tool_revision})

    @classmethod
    def tearDownClass(cls):
        cls.session.close()

    def _prepare(self, source):
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                    "name": "xchunk-cond-target", "bytes": list(source)})
        semantic = {"document": target["document"], "revision": target["revision"],
                    "entryFunctions": []}
        parsed = parse_target(self.session, source, target, self.tool_revision)
        checked = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                     "op": "tool_invoke", "tool": "pep-c23-checker",
                                     "arguments": [parsed], "semanticTarget": semantic})
        require(checked, "outcome", "ok", "check target")
        return parsed, checked["result"], semantic

    def _emit_unit(self, parsed, checked, semantic, index):
        r = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                               "op": "tool_invoke", "tool": "pep-c23-unit",
                               "arguments": [parsed, checked, typed("Int", index)],
                               "semanticTarget": semantic})
        require(r, "outcome", "ok", "emit unit")
        f = _fields_map(r["result"])
        return f["status"]["value"], f["diagnostic"]["value"], \
            [p["value"] for p in f["sourceParts"]["value"]]

    @staticmethod
    def _slice_to_root(parsed, checked, root_index, carry_functions):
        nodes = _fields_map(parsed)["nodes"]["value"]
        ids = [int(_fields_map(n)["id"]["value"]) for n in nodes]
        id_to_parent = {int(_fields_map(n)["id"]["value"]):
                        int(_fields_map(n)["parentId"]["value"]) for n in nodes}
        roots = [i for i in ids if id_to_parent[i] == -1]
        root_id = roots[root_index]

        def in_subtree(i):
            seen = set()
            cur = i
            while cur != -1 and cur not in seen:
                if cur == root_id:
                    return True
                seen.add(cur)
                cur = id_to_parent.get(cur, -1)
            return False

        chunk_ids = [i for i in ids if in_subtree(i)]
        chunk_nodes = [n for n in nodes if int(_fields_map(n)["id"]["value"]) in chunk_ids]

        chunk_checked = dict(checked)
        chunk_checked["fields"] = []
        for item in checked["fields"]:
            name, value = item["name"], item["value"]
            if name == "syntaxNodeCount":
                value = dict(value); value["value"] = str(len(chunk_nodes))
            elif name == "functions":
                if not carry_functions:
                    kept = [f for f in (value.get("value") or [])
                            if int(_fields_map(f).get("syntaxId", {}).get("value", -1)) in chunk_ids]
                    value = dict(value); value["value"] = kept
            elif name in ("bindings", "references", "calls", "expressionTypes",
                          "holes", "diagnostics"):
                kept = [f for f in (value.get("value") or [])
                        if int(_fields_map(f).get("syntaxId", {}).get("value", -1)) in chunk_ids]
                value = dict(value); value["value"] = kept
            chunk_checked["fields"].append({"name": name, "value": value})

        chunk_parsed = dict(parsed)
        chunk_parsed["fields"] = [
            {"name": "nodes", "value": {"type": "List[FlatAstNode]", "value": chunk_nodes}}
            if item["name"] == "nodes" else item
            for item in parsed["fields"]
        ]
        return chunk_parsed, chunk_checked

    def _assert_condition_position(self, source):
        parsed, checked, semantic = self._prepare(source)
        whole_status, whole_diag, whole_parts = self._emit_unit(parsed, checked, semantic, 1)
        self.assertEqual(whole_status, "emitted", whole_diag)

        # WITHOUT the callee's functions fact -> fail-closed.
        chunk_parsed, chunk_checked = self._slice_to_root(parsed, checked, 1, carry_functions=False)
        status, diagnostic, _ = self._emit_unit(chunk_parsed, chunk_checked, semantic, 0)
        self.assertEqual(status, "unsupported")
        self.assertEqual(diagnostic,
                         "Pep C23 cross-chunk call target is missing from the checked functions")

        # WITH the callee's functions fact -> byte-identical to whole-file.
        chunk_parsed, chunk_checked = self._slice_to_root(parsed, checked, 1, carry_functions=True)
        status, diagnostic, parts = self._emit_unit(chunk_parsed, chunk_checked, semantic, 0)
        self.assertEqual(status, "emitted", diagnostic)
        self.assertEqual(parts, whole_parts)

    def test_cross_chunk_call_in_condition(self):
        self._assert_condition_position(CONDITION_SOURCE)

    def test_cross_chunk_call_in_var_initialiser(self):
        self._assert_condition_position(VAR_INIT_SOURCE)

    def test_transitive_chain(self):
        # main -> helper -> helper2: emitting main's slice needs helper's fact (and only
        # helper's, transitively carried by the host closure filter); helper's own body
        # calls helper2 in a separate slice, resolved identically when helper is emitted.
        parsed, checked, semantic = self._prepare(TRANSITIVE_SOURCE)
        whole_status, whole_diag, whole_parts = self._emit_unit(parsed, checked, semantic, 2)
        self.assertEqual(whole_status, "emitted", whole_diag)
        chunk_parsed, chunk_checked = self._slice_to_root(parsed, checked, 2, carry_functions=True)
        status, diagnostic, parts = self._emit_unit(chunk_parsed, chunk_checked, semantic, 0)
        self.assertEqual(status, "emitted", diagnostic)
        self.assertEqual(parts, whole_parts)

    def test_no_resolved_call_fact_refuses(self):
        # A report whose `calls` fact is missing for the condition call refuses fail-closed
        # at the earlier, more specific gate (no resolved call fact) rather than guessing.
        parsed, checked, semantic = self._prepare(CONDITION_SOURCE)
        chunk_parsed, chunk_checked = self._slice_to_root(parsed, checked, 1, carry_functions=True)
        # Drop the `calls` fact entirely to force the no-fact path.
        chunk_checked["fields"] = [
            {"name": name, "value": ({"type": "List[ResolvedCall]", "value": []}
                                      if name == "calls" else value)}
            for name, value in ((f["name"], f["value"]) for f in chunk_checked["fields"])
        ]
        status, diagnostic, _ = self._emit_unit(chunk_parsed, chunk_checked, semantic, 0)
        self.assertEqual(status, "unsupported")
        self.assertEqual(diagnostic, "Pep C23 cross-chunk call has no resolved call fact")


if __name__ == "__main__":
    unittest.main()
