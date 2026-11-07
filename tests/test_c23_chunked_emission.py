"""Chunked-input invariant for the sectional emitter (A2, de-risks A1's emit side).

A1's sectional orchestration will call the emitter with per-slice
`ParserProgress` + per-slice `CheckerReport` pairs (a function subtree plus a
slice-local `syntaxNodeCount` and syntaxId-filtered facts), not the whole-file
pair the existing `test_c23_bounded_emission` suite exercises. This test pins
the emitter-side half of that contract: `emit_c23_function_unit` emits the
**same** definition for a consistent chunked pair as for the whole-file pair.

The chunk recipe demonstrated here (function subtree with original ids preserved,
`checked.syntaxNodeCount == len(chunk_nodes)`, facts filtered by `syntaxId`)
is the shape the per-slice reports must follow for the revision gate in
`emit_c23_checked_part` to pass. Cross-function *calls inside the chunk* are not
exercised (the helper returns a literal); callee-visibility ordering is covered
by `test_c23_bounded_emission`'s `PepC23BoundedUnit.prerequisiteKinds/Ids`.
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
class ChunkedEmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = Session()
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = cls.session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                                   "name": "pep-c23-emitter", "metadataOnly": True})
        require(opened, "outcome", "ok", "open bundle")
        require(opened, "status", "valid", "check bundle")
        cls.tool_document = opened["document"]
        cls.tool_revision = opened["revision"]
        sample = cls.session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": "chunk-sample", "bytes": []})
        require(sample, "outcome", "ok", "open sample")
        sd, sr = sample["document"], sample["revision"]
        cls.target_spec = {"document": sd, "revision": sr, "entryFunctions": []}
        empty_parsed = pep_c23.parser_progress(sd, sr)
        empty_checked = pep_c23.checker_report(sd, sr)
        refused = typed_record("unsupported", (),
                               "Pep C23 emission requires a top-level function named main")
        c0 = pep_c23.parser_cursor_value(sd, sr)
        c1 = pep_c23.parser_cursor_value(sd, sr, done=True, lex_done=True, lex_stage="done")
        tools = [
            ("pep-c23-parser-start", "parser_start", [], c0),
            ("pep-c23-parser-step", "parser_step", [c1],
             pep_c23.parser_chunk_value(sd, sr, c1)),
            ("pep-c23-checker", "analyze_parsed", [empty_parsed], empty_checked),
            ("pep-c23-unit", "emit_c23_function_unit",
             [empty_parsed, empty_checked, typed("Int", 0)], refused),
        ]
        for tool, function, args, expect in tools:
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                              "op": "tool_register", "tool": tool,
                              "document": cls.tool_document, "revision": cls.tool_revision,
                              "function": function})
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                              "op": "tool_validate", "tool": tool,
                              "document": cls.tool_document, "revision": cls.tool_revision,
                              "testVectors": [{"arguments": args, "expect": expect,
                                               "semanticTarget": cls.target_spec}]})
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                              "op": "tool_activate", "tool": tool,
                              "document": cls.tool_document, "revision": cls.tool_revision})

    @classmethod
    def tearDownClass(cls):
        cls.session.close()

    def _prepare(self):
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                    "name": "chunk-target", "bytes": list(SOURCE)})
        require(target, "outcome", "ok", "open target")
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
        return f["status"]["value"], [p["value"] for p in f["sourceParts"]["value"]]

    @staticmethod
    def _slice_to_first_function(parsed, checked):
        """Return (chunk_parsed, chunk_checked) for the first top-level function."""
        nodes = _fields_map(parsed)["nodes"]["value"]
        ids = [int(_fields_map(n)["id"]["value"]) for n in nodes]
        id_to_parent = {int(_fields_map(n)["id"]["value"]):
                        int(_fields_map(n)["parentId"]["value"]) for n in nodes}
        root_id = next(i for i in ids if id_to_parent[i] == -1)

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
                value = dict(value)
                value["value"] = str(len(chunk_nodes))
            elif name in ("functions", "bindings", "references", "calls",
                          "expressionTypes", "holes", "diagnostics"):
                kept = []
                for fact in value.get("value", []) if value.get("value") is not None else []:
                    sid = _fields_map(fact).get("syntaxId", {}).get("value")
                    if sid is not None and int(sid) in chunk_ids:
                        kept.append(fact)
                value = dict(value)
                value["value"] = kept
            chunk_checked["fields"].append({"name": name, "value": value})

        chunk_parsed = dict(parsed)
        chunk_parsed["fields"] = [
            {"name": "nodes",
             "value": {"type": "List[FlatAstNode]", "value": chunk_nodes}}
            if item["name"] == "nodes" else item
            for item in parsed["fields"]
        ]
        return chunk_parsed, chunk_checked

    def test_chunked_function_unit_matches_whole_file(self):
        parsed, checked, semantic = self._prepare()
        whole_status, whole_parts = self._emit_unit(parsed, checked, semantic, 0)
        self.assertEqual(whole_status, "emitted")

        chunk_parsed, chunk_checked = self._slice_to_first_function(parsed, checked)
        chunk_status, chunk_parts = self._emit_unit(chunk_parsed, chunk_checked, semantic, 0)

        self.assertEqual(chunk_status, "emitted")
        self.assertEqual(chunk_parts, whole_parts)


if __name__ == "__main__":
    unittest.main()
