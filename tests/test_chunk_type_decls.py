"""Checker-certified external type declaration facts (slice 4a).

`chunk_type_declarations` (new tool `pep-c23-checker-typedecls`) derives
one ResolvedTypeDecl per non-duplicate, non-primitive record declaration
from the same resolve_all_records the whole-program checker uses, so a
body-only chunk can later consume certified facts instead of carrying
declaration subtrees. A duplicated name resolves to its first declaration
(the declaration chunk that carries the subtrees remains the authoritative
reporter of PEP_DUPLICATE_TYPE); primitive-shadowing declarations are
excluded (fail-closed).
"""
import copy
import pathlib
import unittest

import pep_c23
import pep_chunk_contract as contract
from pep_c23 import Session, parse_target, require
from tests.chunk_helper import fields_map, nval

ROOT = pathlib.Path(__file__).resolve().parents[1]


def type_decl_value(decl):
    fields = fields_map(decl)
    return {
        "typeName": fields["typeName"]["value"],
        "typeKind": fields["typeKind"]["value"],
        "document": fields["document"]["value"],
        "revision": fields["revision"]["value"],
        "declSpan": (int(fields["declStartByte"]["value"]),
                     int(fields["declEndByte"]["value"])),
        "fields": [(fields_map(f)["fieldName"]["value"],
                     fields_map(f)["fieldTypeName"]["value"],
                     {k: v["value"] for k, v in
                      fields_map(fields_map(f)["fieldShape"]).items()},
                     fields_map(f)["fieldCode"]["value"])
                    for f in fields["fields"]["value"]],
    }


class ChunkTypeDeclarationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = Session()
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
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
            sample["document"], sample["revision"],
            done=True, lex_done=True, lex_stage="done")
        empty_pp = pep_c23.parser_progress(sample["document"], sample["revision"])
        empty_types = {"type": "List[ResolvedTypeDecl]", "value": []}
        for tool, function, arguments, expected in [
                ("pep-c23-parser-start", "parser_start", [], start_cursor),
                ("pep-c23-parser-step", "parser_step", [finished_cursor],
                 pep_c23.parser_chunk_value(sample["document"], sample["revision"],
                                            finished_cursor)),
                ("pep-c23-checker-typedecls", "chunk_type_declarations",
                 [empty_pp], empty_types)]:
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                              "op": "tool_register", "tool": tool,
                              "document": tool_document,
                              "revision": cls.tool_revision, "function": function})
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                              "op": "tool_validate", "tool": tool,
                              "document": tool_document,
                              "revision": cls.tool_revision,
                              "testVectors": [{"arguments": arguments, "expect": expected,
                                                "semanticTarget": target_spec}]})
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                              "op": "tool_activate", "tool": tool,
                              "document": tool_document,
                              "revision": cls.tool_revision})

    @classmethod
    def tearDownClass(cls):
        cls.session.process.stdin.close()
        cls.session.process.terminate()

    def fetch_types(self, source_bytes, name):
        from tests.chunk_helper import remap_chunk
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                     "name": name, "bytes": list(source_bytes)})
        self.assertEqual(target.get("outcome"), "ok", target)
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": []}
        parsed = parse_target(self.session, source_bytes, target, self.tool_revision)
        nodes = fields_map(parsed)["nodes"]["value"]
        index = contract.DocumentIndex.from_parsed(parsed)
        by_id = {str(nval(node, "id")): node for node in nodes}
        decl_roots = [int(nval(node, "id")) for node in nodes
                      if str(nval(node, "parentId")) == "-1"
                      and nval(node, "kind") in ("record_declaration", "union_declaration")]
        chunks = [sorted(index.subtree(root)) for root in decl_roots] or [None]
        decls = []
        for chunk_ids in chunks:
            if chunk_ids is None:
                sliced_nodes = nodes
            else:
                sub = [copy.deepcopy(by_id[str(node_id)]) for node_id in chunk_ids]
                sliced_nodes = remap_chunk(sub)
            sliced = {"type": "ParserProgress", "fields": [
                {"name": key, "value": ({"type": "List[FlatAstNode]",
                                             "value": sliced_nodes}
                                            if key == "nodes" else fields_map(parsed)[key])}
                for key in [field["name"] for field in parsed["fields"]]]}
            response = self.session.send(
                {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                 "tool": "pep-c23-checker-typedecls", "arguments": [sliced],
                 "semanticTarget": sem})
            self.assertEqual(response.get("outcome"), "ok", response)
            decls.extend(type_decl_value(d) for d in response["result"]["value"])
        return target, decls

    def test_real_lexer_yields_five_record_decls(self):
        source_bytes = (ROOT / "examples" / "pep_lexer.pep").read_bytes()
        target, decls = self.fetch_types(source_bytes, "lexer-typedecls")
        by_name = {d["typeName"]: d for d in decls}
        self.assertEqual(sorted(by_name),
                         ["LexCursor", "LexProgress", "LexToken",
                          "SourcePosition", "Utf8Check"])
        for decl in decls:
            self.assertEqual(decl["typeKind"], "record", decl)
            self.assertEqual(decl["document"], target["document"])
            self.assertEqual(decl["revision"], target["revision"])
        token_fields = [f[0] for f in by_name["LexToken"]["fields"]]
        self.assertEqual(token_fields,
                         ["kind", "text", "integerValue", "stringParts",
                          "startByte", "endByte", "line", "column"])
        self.assertEqual(len(by_name["LexCursor"]["fields"]), 16)
        shapes = {f[0]: f[2] for f in by_name["LexToken"]["fields"]}
        self.assertEqual(shapes["text"]["name"], "Str")
        self.assertEqual(shapes["text"]["kind"], "builtin")
        progress_shapes = {f[0]: f[2] for f in by_name["LexProgress"]["fields"]}
        self.assertEqual(progress_shapes["tokens"]["name"], "LexToken")
        self.assertEqual(progress_shapes["tokens"]["kind"], "nominal")
        self.assertEqual(int(progress_shapes["tokens"]["listDepth"]), 1)
        cursor_shapes = {f[0]: f[2] for f in by_name["LexCursor"]["fields"]}
        self.assertEqual(cursor_shapes["mode"]["name"], "Str")

    def test_duplicate_name_keeps_first_declaration(self):
        # Producer dedupes within one input (first-in-source-order wins,
        # matching whole-path record_declaration resolution). Per-declaration
        # chunks each see a single consistent declaration, so each yields
        # its own fact; consumers take the first match in chunk order.
        source = (b"type Box { f: Int }\ntype Box { g: Int }\n"
                  b"fn main() -> Int { return 0 }\n")
        _, decls = self.fetch_types(source, "dup-typedecls")
        self.assertEqual([d["typeName"] for d in decls], ["Box", "Box"])
        self.assertEqual(decls[0]["fields"][0][0], "f")
        self.assertEqual(decls[1]["fields"][0][0], "g")

    def test_duplicate_name_dedupes_within_one_input(self):
        # Same input containing both copies yields one fact (first wins).
        from tests.chunk_helper import fields_map
        source = (b"type Box { f: Int }\ntype Box { g: Int }\n"
                    b"fn main() -> Int { return 0 }\n")
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                     "name": "dup-whole", "bytes": list(source)})
        self.assertEqual(target.get("outcome"), "ok", target)
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": []}
        parsed = parse_target(self.session, source, target, self.tool_revision)
        response = self.session.send(
            {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
             "tool": "pep-c23-checker-typedecls", "arguments": [parsed],
             "semanticTarget": sem})
        self.assertEqual(response.get("outcome"), "ok", response)
        names = [fields_map(d)["typeName"]["value"]
                 for d in response["result"]["value"]]
        self.assertEqual(names, ["Box"])

    def test_unknown_field_type_keeps_empty_shape(self):
        source = (b"type Box { f: Nope }\nfn main() -> Int { return 0 }\n")
        _, decls = self.fetch_types(source, "unknown-typedecls")
        self.assertEqual(len(decls), 1)
        self.assertEqual(decls[0]["typeName"], "Box")
        self.assertEqual(decls[0]["fields"][0][0], "f")
        self.assertEqual(decls[0]["fields"][0][1], "Nope")
        self.assertEqual(decls[0]["fields"][0][2]["kind"], "nominal")
        self.assertEqual(decls[0]["fields"][0][2]["name"], "Nope")
        self.assertEqual(decls[0]["fields"][0][3], "PEP_UNKNOWN_TYPE")


if __name__ == "__main__":
    unittest.main()
