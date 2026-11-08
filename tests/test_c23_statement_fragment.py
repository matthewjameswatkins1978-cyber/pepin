"""Carried-binding name resolution for statement fragments (A2-S2, field 2).

A1's A1-S2 dry-run found the second fragment wall: a fragment whose statements
reference a `var` declared in an EARLIER fragment refuses with

    Pep C23 name lowering requires a direct immutable local let or scalar parameter

because the emitter resolves names only from in-slice `let`/`var`/`parameter`
nodes. The fix is a checked-aware fallback: on that exact refusal, `pep_c23_expression_checked`
consults the whole-function `checked.bindings` (name -> syntaxId) and emits the
binding's stable `pep_local_<syntaxId>` symbol — the prologue fragment declares it once.

Contract pinned here: a slice that drops the binding's node but carries its
`bindings` fact emits `pep_local_<id>`; a slice that drops the fact refuses
fail-closed with "no carried binding fact".
"""

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target, typed  # noqa: E402

SOURCE = ("fn main() -> Int {\n"
          "  var r = 0\n"
          "  return r\n"
          "}\n").encode()


def _fields_map(value):
    return {item["name"]: item["value"] for item in value["fields"]}


@unittest.skipUnless((ROOT / "pep.ps1").is_file(), "pep.ps1 required")
class CarriedBindingNameResolutionTests(unittest.TestCase):
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
                                   "name": "xchunk-cb-sample", "bytes": []})
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

    def _prepare(self):
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                    "name": "cb-target", "bytes": list(SOURCE)})
        semantic = {"document": target["document"], "revision": target["revision"],
                    "entryFunctions": []}
        parsed = parse_target(self.session, SOURCE, target, self.tool_revision)
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
    def _drop_statement(parsed, checked, root_index, drop_child_index, carry_bindings):
        """Return parsed/checked with the named function's statement at drop_child_index
        removed, its `bindings` fact either carried whole-function (carry_bindings=True)
        or dropped (False)."""
        nodes = _fields_map(parsed)["nodes"]["value"]
        id_to_parent = {int(_fields_map(n)["id"]["value"]):
                        int(_fields_map(n)["parentId"]["value"]) for n in nodes}
        id_to_child = {int(_fields_map(n)["id"]["value"]):
                       int(_fields_map(n).get("childIndex", {}).get("value", -1)) for n in nodes}
        id_to_kind = {int(_fields_map(n)["id"]["value"]):
                      _fields_map(n).get("kind", {}).get("value", "") for n in nodes}
        roots = [int(_fields_map(n)["id"]["value"]) for n in nodes
                 if int(_fields_map(n)["parentId"]["value"]) == -1]
        root_id = roots[root_index]
        statement_kinds = ("let", "var", "for_in", "while", "if_statement",
                           "return", "expression_statement")

        def subtree_ids(seed):
            out = set(seed)
            for _ in range(32):
                grown = set(out)
                for nid, parent in id_to_parent.items():
                    if parent in out:
                        grown.add(nid)
                if grown == out:
                    break
                out = grown
            return out

        function_ids = subtree_ids({root_id})
        drop_roots = {nid for nid in id_to_child
                      if id_to_parent.get(nid, -1) == root_id
                      and id_to_kind.get(nid, "") in statement_kinds
                      and id_to_child[nid] == drop_child_index}
        drop_ids = subtree_ids(drop_roots)
        keep = function_ids - drop_ids

        chunk_nodes = [n for n in nodes if int(_fields_map(n)["id"]["value"]) in keep]

        chunk_checked = dict(checked)
        chunk_checked["fields"] = []
        for item in checked["fields"]:
            name, value = item["name"], item["value"]
            if name == "syntaxNodeCount":
                value = dict(value); value["value"] = str(len(chunk_nodes))
            elif name == "bindings":
                if not carry_bindings:
                    value = dict(value); value["value"] = []
            elif name in ("calls", "expressionTypes", "holes", "references", "diagnostics"):
                kept = [f for f in (value.get("value") or [])
                        if int(_fields_map(f).get("syntaxId", {}).get("value", -1)) in keep]
                value = dict(value); value["value"] = kept
            chunk_checked["fields"].append({"name": name, "value": value})

        chunk_parsed = dict(parsed)
        chunk_parsed["fields"] = [
            {"name": "nodes", "value": {"type": "List[FlatAstNode]", "value": chunk_nodes}}
            if item["name"] == "nodes" else item
            for item in parsed["fields"]
        ]
        return chunk_parsed, chunk_checked

    def test_carried_binding_resolves_name(self):
        parsed, checked, semantic = self._prepare()
        whole_status, _, _ = self._emit_unit(parsed, checked, semantic, 0)
        self.assertEqual(whole_status, "emitted")

        # The dropped var's carried binding id (r's syntaxId).
        binding_sid = None
        for f in checked["fields"]:
            if f["name"] == "bindings":
                for b in (f["value"].get("value") or []):
                    bm = _fields_map(b)
                    if bm.get("name", {}).get("value") == "r":
                        binding_sid = bm.get("syntaxId", {}).get("value")
        self.assertIsNotNone(binding_sid)

        chunk_parsed, chunk_checked = self._drop_statement(parsed, checked, 0, 0, carry_bindings=True)
        status, diagnostic, parts = self._emit_unit(chunk_parsed, chunk_checked, semantic, 0)
        self.assertEqual(status, "emitted", diagnostic)
        joined = "".join(parts)
        # The fragment references the carried binding's stable symbol but does NOT
        # re-declare it (the prologue fragment declares it once).
        self.assertIn("pep_local_" + binding_sid, joined)
        self.assertNotIn("pep_local_" + binding_sid + " =", joined)

    def test_missing_carried_binding_refuses(self):
        parsed, checked, semantic = self._prepare()
        chunk_parsed, chunk_checked = self._drop_statement(parsed, checked, 0, 0, carry_bindings=False)
        status, diagnostic, _ = self._emit_unit(chunk_parsed, chunk_checked, semantic, 0)
        self.assertEqual(status, "unsupported")
        self.assertEqual(diagnostic, "Pep C23 name lowering has no carried binding fact")


if __name__ == "__main__":
    unittest.main()
