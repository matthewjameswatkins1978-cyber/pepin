"""Cross-chunk call resolution in the sectional emitter (A2, A1's "carried facts" seam).

`emit_c23_function_unit` on a function whose body calls a peer resolves the call
in two hops over the checked report: `checked.calls` (call-site syntaxId ->
calleeId) then `checked.functions` (semanticId -> name/arity/returnType). A
per-slice report that drops the callee's `functions` fact therefore refuses:

    Pep C23 cross-chunk call target is missing from the checked functions

This pins the contract A1's per-slice reports must follow: carry the callee's
`functions` fact (transitively), keep `calls`/`bindings`/`references`/
`expressionTypes` slice-local, and `syntaxNodeCount` = the slice's node count.
"""

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target, typed, typed_record  # noqa: E402

SOURCE = ("fn helper() -> Int { return 1 }\n"
          "fn main() -> Int { return helper() }\n").encode()


def _fields_map(value):
    return {item["name"]: item["value"] for item in value["fields"]}


@unittest.skipUnless((ROOT / "pep.ps1").is_file(), "pep.ps1 required")
class CrossChunkCallTests(unittest.TestCase):
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
                                   "name": "xchunk-sample", "bytes": []})
        sd, sr = sample["document"], sample["revision"]
        cls.target_spec = {"document": sd, "revision": sr, "entryFunctions": []}
        empty_parsed = pep_c23.parser_progress(sd, sr)
        empty_checked = pep_c23.checker_report(sd, sr)
        refused = typed_record("unsupported", (),
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
                                    "name": "xchunk-target", "bytes": list(SOURCE)})
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

    def test_calling_function_unit_requires_callee_functions_fact(self):
        parsed, checked, semantic = self._prepare()
        whole_status, _, whole_parts = self._emit_unit(parsed, checked, semantic, 1)
        self.assertEqual(whole_status, "emitted")

        # WITHOUT the callee's functions fact -> refuse with the exact diagnostic.
        chunk_parsed, chunk_checked = self._slice_to_root(parsed, checked, 1, carry_functions=False)
        status, diagnostic, _ = self._emit_unit(chunk_parsed, chunk_checked, semantic, 0)
        self.assertEqual(status, "unsupported")
        self.assertEqual(diagnostic, "Pep C23 cross-chunk call target is missing from the checked functions")

        # WITH the callee's functions fact carried -> emits identically to whole-file.
        chunk_parsed, chunk_checked = self._slice_to_root(parsed, checked, 1, carry_functions=True)
        status, diagnostic, parts = self._emit_unit(chunk_parsed, chunk_checked, semantic, 0)
        self.assertEqual(status, "emitted")
        self.assertEqual(parts, whole_parts)


if __name__ == "__main__":
    unittest.main()
