"""Checker step-budget boundaries on real lexer type closures (A1-1).

Uses the REAL C23 pipeline stages (pep_c23: host-driven staged parse,
then ONE analyze_parsed invocation under the unchanged 100k step
budget), so every boundary here is the exact production failure mode,
not a synthetic harness artifact.

Current pins (to be flipped to valid by the A1-2 repair):
- T5 (SourcePosition..LexProgress closure): PEP_RUNTIME_STEP_LIMIT
- R32 (32 trivial records): PEP_RUNTIME_STEP_LIMIT

Stable asserts regardless of repair: every fixture is OCaml-valid
(semantic acceptance, not a budget artifact) and T1-T4/R8/R16 check
valid today.

Do NOT raise any budget to make these pass; a passing boundary must
come from cheaper checking.
"""
import json
import pathlib
import subprocess
import unittest

from pep_c23 import Session, require, parse_target
import pep_c23
from tests.test_c23_list_record_fields import lexer_type_block

ROOT = pathlib.Path(__file__).resolve().parents[1]
NL = chr(10)


def cumulative_type_prefixes(block_text):
    blocks, current = [], []
    for line in block_text.split(NL):
        if (line.startswith("type ") or line.startswith("fn ")) and current:
            blocks.append(NL.join(current))
            current = [line]
        else:
            current.append(line)
    blocks.append(NL.join(current))
    type_blocks = [b for b in blocks if b.startswith("type ")]
    out, acc = {}, ""
    for i, b in enumerate(type_blocks):
        acc = (acc + NL + b).strip() + NL
        out[f"T{i + 1}"] = acc
    return out


def ocaml_check(source):
    with open(ROOT / "_build" / "budget_target.pep", "w",
              encoding="utf-8", newline="\n") as fh:
        fh.write(source)
    proc = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"), "check",
         str(ROOT / "_build" / "budget_target.pep"), "--json"],
        cwd=ROOT, text=True, capture_output=True, check=False)
    return json.loads(proc.stdout).get("status")


class CheckerBudgetBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = Session()
        bundle = NL.join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
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
        for tool, function, arguments, expected in [
                ("pep-c23-parser-start", "parser_start", [], start_cursor),
                ("pep-c23-parser-step", "parser_step", [finished_cursor],
                 pep_c23.parser_chunk_value(sample["document"], sample["revision"],
                                            finished_cursor)),
                ("pep-c23-checker", "analyze_parsed",
                 [pep_c23.parser_progress(sample["document"], sample["revision"])],
                 pep_c23.checker_report(sample["document"], sample["revision"]))]:
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_register",
                              "tool": tool, "document": tool_document,
                              "revision": cls.tool_revision, "function": function})
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_validate",
                              "tool": tool, "document": tool_document,
                              "revision": cls.tool_revision,
                              "testVectors": [{"arguments": arguments, "expect": expected,
                                                "semanticTarget": target_spec}]})
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_activate",
                              "tool": tool, "document": tool_document,
                              "revision": cls.tool_revision})
        prefixes = cumulative_type_prefixes(lexer_type_block())
        cls.fixtures = dict(prefixes)
        for n in (8, 16, 32, 48, 96):
            cls.fixtures[f"R{n}"] = (
                NL.join(f"type R{i} {{ f: Int }}" for i in range(n)) + NL)

    @classmethod
    def tearDownClass(cls):
        cls.session.process.stdin.close()
        cls.session.process.terminate()

    def invoke_checker(self, source):
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                    "name": "boundary-target",
                                    "bytes": list(source.encode("utf-8"))})
        self.assertEqual(target.get("outcome"), "ok", target)
        semantic_target = {"document": target["document"], "revision": target["revision"],
                           "entryFunctions": []}
        parsed = parse_target(self.session, source.encode("utf-8"), target, self.tool_revision)
        return self.session.send(
            {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
             "tool": "pep-c23-checker", "arguments": [parsed],
             "semanticTarget": semantic_target})

    def assert_ocaml_valid(self, source):
        self.assertEqual(ocaml_check(source), "valid",
                         "OCaml oracle must accept the fixture (else it is not a budget boundary)")

    def report_status(self, result):
        self.assertEqual(result.get("outcome"), "ok", result)
        fields = {item["name"]: item["value"] for item in result["result"]["fields"]}
        status = fields["status"]
        return status["value"] if isinstance(status, dict) else status

    def test_small_closures_check_valid(self):
        for label in ("T1", "T2", "T3", "T4", "R8", "R16"):
            with self.subTest(fixture=label):
                source = self.fixtures[label]
                self.assert_ocaml_valid(source)
                self.assertEqual(self.report_status(self.invoke_checker(source)), "valid")

    def test_lexprogress_closure_checks_valid(self):
        # A2's production failure (A2N-20261031-002), repaired by the
        # single-pass record-field resolution: the real LexToken/LexCursor/
        # LexProgress closure now checks valid under the unchanged 100k budget.
        source = self.fixtures["T5"]
        self.assert_ocaml_valid(source)
        result = self.invoke_checker(source)
        self.assertEqual(result.get("outcome"), "ok", result)
        self.assertEqual(self.report_status(result), "valid")

    def test_real_function_body_hits_step_budget(self):
        # Next frontier (A1-5): real function bodies with conditional logic
        # (stdlib collections shape) still exceed the unchanged budget.
        # Bisection: params/lets/plain-for pass; the if-expression with a
        # compound boolean condition is the cliff. Flip to valid when the
        # expression-inference path is staged or memoized.
        source = ("fn list_int_min_between(values: List[Int], lower: Int, upper: Int, fallback: Int) -> Int {\n"
                  "  var found = false\n"
                  "  var minimum = fallback\n"
                  "  for item in values {\n"
                  "    minimum = if lower <= item && item <= upper && (!found || item <= minimum) { item } else { minimum }\n"
                  "    found = found || (lower <= item && item <= upper)\n"
                  "  }\n"
                  "  return minimum\n"
                  "}\n"
                  "fn main() -> Int {\n"
                  "  return list_int_min_between([1, 2, 3], 1, 3, 9)\n"
                  "}\n")
        self.assert_ocaml_valid(source)
        result = self.invoke_checker(source)
        self.assertEqual(result.get("outcome"), "error", result)
        self.assertEqual(result.get("error", {}).get("code"), "PEP_RUNTIME_STEP_LIMIT")

    def test_real_make_token_checks_valid(self):
        # Structural win (d158044): the real 8-parameter make_token
        # constructor with 8-field record construction now checks valid
        # via resolved-record field consults (was PEP_RUNTIME_STEP_LIMIT).
        decl = ("type LexToken {\n  kind: Str, text: Str, integerValue: Int, stringParts: List[Str],\n"
                "  startByte: Int, endByte: Int, line: Int, column: Int\n}\n")
        params = ", ".join(["kind: Str", "text: Str", "integerValue: Int", "stringParts: List[Str]",
                              "startByte: Int", "endByte: Int", "line: Int", "column: Int"])
        args = ", ".join(["kind: kind", "text: text", "integerValue: integerValue",
                            "stringParts: stringParts", "startByte: startByte", "endByte: endByte",
                            "line: line", "column: column"])
        source = decl + f"fn make_token({params}) -> LexToken {{\n  return LexToken {{ {args} }}\n}}\n"
        self.assert_ocaml_valid(source)
        result = self.invoke_checker(source)
        self.assertEqual(result.get("outcome"), "ok", result)
        self.assertEqual(self.report_status(result), "valid")

    def test_sixteen_literal_args_check_valid(self):
        # Structural win (literal fast-path): 16-argument calls with
        # literal args now check valid under the unchanged budget
        # (was PEP_RUNTIME_STEP_LIMIT). Per-literal infer/shape scans
        # eliminated in the main expression path + arg checking.
        params = ", ".join(f"p{i}: Int" for i in range(16))
        args = ", ".join(str(i) for i in range(16))
        source = (f"fn f16({params}) -> Int {{\n  return 0\n}}\n"
                  f"fn main() -> Int {{\n  return f16({args})\n}}\n")
        self.assert_ocaml_valid(source)
        result = self.invoke_checker(source)
        self.assertEqual(result.get("outcome"), "ok", result)
        self.assertEqual(self.report_status(result), "valid")

    def test_thirty_two_records_check_valid(self):
        # Scale pin flipped by the global single-pass record resolution:
        # 32 trivial records now check valid under the unchanged budget.
        source = self.fixtures["R32"]
        self.assert_ocaml_valid(source)
        result = self.invoke_checker(source)
        self.assertEqual(result.get("outcome"), "ok", result)
        self.assertEqual(self.report_status(result), "valid")

    def test_make_token_constructor_hits_step_budget(self):
        # A2's key reproducer (native make_token): 8-param constructor with
        # List field + record construction. Declaration alone checks valid;
        # the full constructor exceeds the unchanged budget.
        # Flip to valid when per-construct check cost drops further.
        mk = ("type LexToken { kind: Str, text: Str, integerValue: Int, "
              "stringParts: List[Str], startByte: Int, endByte: Int, line: Int, column: Int }\n"
              "fn make_token(kind: Str, text: Str, integerValue: Int, stringParts: List[Str], startByte: Int, endByte: Int, line: Int, column: Int) -> LexToken {\n"
              "  return LexToken { kind: kind, text: text, integerValue: integerValue, stringParts: stringParts, startByte: startByte, endByte: endByte, line: line, column: column }\n"
              "}\n"
              "fn main() -> Int { let t = make_token(\"s\", \"hi\", 7, [\"ab\", \"cd\"], 3, 9, 1, 4) return length(t.stringParts) }\n")
        self.assert_ocaml_valid(mk)
        result = self.invoke_checker(mk)
        self.assertEqual(result.get("outcome"), "error", result)
        self.assertEqual(result.get("error", {}).get("code"), "PEP_RUNTIME_STEP_LIMIT")

    def test_large_scales_hit_step_budget(self):
        # Documented frontier: 48+ trivial records still exceed the
        # unchanged 100k budget. Flip each to a valid-assertion when the
        # next composition repair lands it.
        for label in ("R48", "R96"):
            with self.subTest(fixture=label):
                source = self.fixtures[label]
                self.assert_ocaml_valid(source)
                result = self.invoke_checker(source)
                self.assertEqual(result.get("outcome"), "error", result)
                self.assertEqual(result.get("error", {}).get("code"), "PEP_RUNTIME_STEP_LIMIT")

    def test_nominal_empty_list_with_annotation_checks_valid(self):
        # A2 divergence (bc324100): OCaml-valid mutable List[record]
        # binding was rejected with PEP_EMPTY_LIST_NEEDS_TYPE. The empty
        # list inherits a concrete list type from a list-shaped annotation,
        # including nominal element types. All three use shapes pass.
        decl = "type P { x: Int }\n"
        for label, body in (
            ("length", "  var points: List[P] = []\n  return length(points)\n"),
            ("reverse", "  var points: List[P] = []\n  return length(reverse(points))\n"),
            ("prepend", "  var points: List[P] = []\n  points = prepend(points, P { x: 1 })\n  return length(points)\n"),
        ):
            with self.subTest(use=label):
                source = decl + "fn main() -> Int {\n" + body + "}\n"
                self.assert_ocaml_valid(source)
                result = self.invoke_checker(source)
                self.assertEqual(result.get("outcome"), "ok", result)
                self.assertEqual(self.report_status(result), "valid")

    def test_nominal_empty_list_in_record_field_checks_valid(self):
        # A2 divergence (15734c8): OCaml-valid empty List[record] as a
        # record field value was rejected with PEP_EMPTY_LIST_NEEDS_TYPE.
        # Same family as mutable-List[record] bindings: the field inherits
        # a concrete list type from the resolved record declaration.
        decl = ("type Tokenish { kind: Str, parts: List[Str] }\n"
                "type Progressish { status: Str, tokens: List[Tokenish] }\n")
        body = ("fn made() -> Progressish {\n  return Progressish { status: \"ok\", tokens: [] }\n}\n"
                "fn main() -> Int {\n  let p = made()\n  return length(p.tokens) + 5\n}\n")
        source = decl + body
        self.assert_ocaml_valid(source)
        result = self.invoke_checker(source)
        self.assertEqual(result.get("outcome"), "ok", result)
        self.assertEqual(self.report_status(result), "valid")


class CheckerChunkedEquivalenceTests(unittest.TestCase):
    # Per-function chunking (analyze_chunk + external signatures): a program
    # that exceeds the whole-program budget must check valid via bounded
    # chunks, with a combined verdict matching whole-program semantics.
    @classmethod
    def setUpClass(cls):
        cls.session = Session()
        bundle = NL.join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
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
        empty_ext = {"type": "List[CheckedFunction]", "value": []}
        empty_sig = {"type": "List[ResolvedSignature]", "value": []}
        for tool, function, arguments, expected in [
                ("pep-c23-parser-start", "parser_start", [], start_cursor),
                ("pep-c23-parser-step", "parser_step", [finished_cursor],
                 pep_c23.parser_chunk_value(sample["document"], sample["revision"],
                                            finished_cursor)),
                ("pep-c23-checker", "analyze_parsed", [empty_pp], empty_rep),
                ("pep-c23-checker-chunk", "analyze_chunk", [empty_pp, empty_ext, empty_sig], empty_rep),
                ("pep-c23-checker-sigs", "chunk_signatures", [empty_pp], empty_sig)]:
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_register",
                              "tool": tool, "document": tool_document,
                              "revision": cls.tool_revision, "function": function})
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_validate",
                              "tool": tool, "document": tool_document,
                              "revision": cls.tool_revision,
                              "testVectors": [{"arguments": arguments, "expect": expected,
                                                "semanticTarget": target_spec}]})
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_activate",
                              "tool": tool, "document": tool_document,
                              "revision": cls.tool_revision})

    @classmethod
    def tearDownClass(cls):
        cls.session.process.stdin.close()
        cls.session.process.terminate()

    def check_chunked(self, source):
        from tests.chunk_helper import (fields_map, nval, checked_fn_value,
                                         resolved_sig_value, slice_subtree, remap_chunk,
                                         variant_to_union, fetch_all_sigs, decl_closure)
        src = source.encode("utf-8")
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                     "name": "chunk-target", "bytes": list(src)})
        self.assertEqual(target.get("outcome"), "ok", target)
        parsed = parse_target(self.session, src, target, self.tool_revision)
        nodes = fields_map(parsed)["nodes"]["value"]
        sem0 = {"document": target["document"], "revision": target["revision"],
                "entryFunctions": []}
        sigs = fetch_all_sigs(self.session, parsed, self.tool_revision, sem0)
        v2u = variant_to_union(nodes)
        decl_by_id = {str(nval(n, "id")): n for n in nodes
                       if nval(n, "kind") in ("record_declaration", "union_declaration")
                       and str(nval(n, "parentId")) == "-1"}
        decl_name_to_id = {nval(d, "text"): i for i, d in decl_by_id.items()}
        fn_nodes = [n for n in nodes if nval(n, "kind") == "function"
                    and str(nval(n, "parentId")) == "-1"]
        self.assertGreater(len(fn_nodes), 1, "chunk test needs multiple functions")
        from tests.chunk_helper import decl_closure
        statuses, diags = [], []
        for fn in fn_nodes:
            fname = nval(fn, "text")
            sub = slice_subtree(nodes, nval(fn, "id"))
            sigs_by_name = {s["name"]: s for s in sigs}
            for sn in decl_closure(nodes, sub, sigs_by_name, decl_name_to_id, v2u):
                sub.append(sn)
            chunk = remap_chunk(sub)
            self.assertLessEqual(len(chunk), 60, f"chunk for {fname} exceeds budget-sized bound")
            sliced = {"type": "ParserProgress", "fields": [
                {"name": k, "value": ({"type": "List[FlatAstNode]", "value": chunk}
                                     if k == "nodes" else fields_map(parsed)[k])}
                for k in [f["name"] for f in parsed["fields"]]]}
            ext = [s for s in sigs if s["name"] != fname]
            extv = {"type": "List[CheckedFunction]",
                    "value": [checked_fn_value(s) for s in ext]}
            exts = {"type": "List[ResolvedSignature]",
                    "value": [resolved_sig_value(s) for s in ext]}
            sem = {"document": target["document"], "revision": target["revision"],
                   "entryFunctions": []}
            r = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                                    "tool": "pep-c23-checker-chunk",
                                    "arguments": [sliced, extv, exts], "semanticTarget": sem})
            self.assertEqual(r.get("outcome"), "ok", r)
            statuses.append(fields_map(r["result"])["status"]["value"])
            for d in fields_map(r["result"]).get("diagnostics", {}).get("value", []):
                df = fields_map(d)
                diags.append((df.get("code", {}).get("value"),
                              df.get("startByte", {}).get("value"),
                              df.get("endByte", {}).get("value")))
        return statuses, sorted(set(diags))

    def test_chunked_recpad6_valid(self):
        # recpad-6 (66 nodes) exceeds the whole-program budget but must
        # check valid via per-function chunks (each <= 60 nodes).
        parts = []
        for i in range(6):
            parts.append(f"type P{i} {{ x: Int }}\nfn mk{i}(v: Int) -> P{i} {{\n"
                           f"  return P{i} {{ x: v }}\n}}\n")
        source = "".join(parts)
        src = source.encode("utf-8")
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                     "name": "whole-target", "bytes": list(src)})
        self.assertEqual(target.get("outcome"), "ok", target)
        parsed = parse_target(self.session, src, target, self.tool_revision)
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": []}
        wr = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                                "tool": "pep-c23-checker", "arguments": [parsed],
                                "semanticTarget": sem})
        self.assertEqual(wr.get("outcome"), "error", wr)
        self.assertEqual(wr.get("error", {}).get("code"), "PEP_RUNTIME_STEP_LIMIT")
        statuses, diags = self.check_chunked(source)
        self.assertTrue(all(s == "valid" for s in statuses), statuses)
        self.assertEqual(diags, [], diags)

    def test_chunked_cross_call_match_valid(self):
        # Cross-chunk calls resolve via external signatures: correct
        # argument types check valid.
        source = ("fn callee(x: Int) -> Int {\n  return x\n}\n"
                  "fn caller(y: Int) -> Int {\n  return callee(y)\n}\n")
        statuses, diags = self.check_chunked(source)
        self.assertTrue(all(s == "valid" for s in statuses), statuses)
        self.assertEqual(diags, [], diags)

    def test_chunked_cross_call_mismatch_invalid(self):
        # Cross-chunk calls are fully checked (not weakened): wrong
        # argument types draw PEP_TYPE_MISMATCH via external param sigs.
        source = ("fn callee(x: Int) -> Int {\n  return x\n}\n"
                  "fn caller(y: Str) -> Int {\n  return callee(y)\n}\n")
        statuses, diags = self.check_chunked(source)
        self.assertIn("invalid", statuses, statuses)
        codes = [c for c, _, _ in diags]
        self.assertIn("PEP_TYPE_MISMATCH", codes, codes)

    def test_compact_lexer_step_fits_transport(self):
        # Transport gate (A2 field audit): the compact projection drops
        # exactly stringParts/line/column, keeps the other 10 fields,
        # and the 1,503-node lexer_step fits the 1 MiB JSONL message.
        import json
        from tests.chunk_helper import (fields_map, nval, slice_subtree,
                                         remap_chunk, compact_node)
        from pathlib import Path
        lex = (Path(__file__).resolve().parent.parent
               / "examples" / "pep_lexer.pep").read_bytes()
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                     "name": "lex-transport", "bytes": list(lex)})
        self.assertEqual(target.get("outcome"), "ok", target)
        parsed = parse_target(self.session, lex, target, self.tool_revision)
        nodes = fields_map(parsed)["nodes"]["value"]
        step = [n for n in nodes if nval(n, "kind") == "function"
                and nval(n, "text") == "lexer_step"]
        self.assertEqual(len(step), 1, "lexer_step must exist")
        sub = slice_subtree(nodes, nval(step[0], "id"))
        chunk = remap_chunk(sub)
        compact = [compact_node(n) for n in chunk]
        kept = {"id", "parentId", "childIndex", "role", "kind", "text",
                "integerValue", "booleanValue", "startByte", "endByte"}
        for n in compact:
            self.assertEqual({f["name"] for f in n["fields"]}, kept, n)
        blob = json.dumps([{"fields": n["fields"]} for n in compact]).encode()
        self.assertLess(len(blob), 1048576, len(blob))


class StagedParserBudgetBoundariesTests(unittest.TestCase):
    """Parser-stage (A1-owned) per-token step-budget boundaries on this head.

    A2 reported a 640-character string literal as emitter-accepted but
    parser-rejected, measured on a different branch. Re-measured here on
    the integrated head: 640 and 1,024 characters parse complete, and the
    parser first stops between 1,024 and 1,280. The identifier path has a
    separate boundary (1,280 complete, 1,536 stops), so the binding
    constraint is cost per scanned literal byte inside one lexer_step
    invocation, not a general source-size limit.

    Flip a stopping assertion to complete when a cheaper literal scan
    lands. Never raise the 100,000-step budget to make these pass.
    """

    @classmethod
    def setUpClass(cls):
        cls.session = Session()
        bundle = NL.join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = cls.session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                                    "name": "pep-c23", "metadataOnly": True})
        require(opened, "outcome", "ok", "open compiler bundle")
        tool_document = opened["document"]
        cls.tool_revision = opened["revision"]
        sample = cls.session.send({"schemaVersion": 3, "op": "open_bytes",
                                    "name": "validate", "bytes": []})
        target_spec = {"document": sample["document"], "revision": sample["revision"],
                       "entryFunctions": []}
        start_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"])
        finished_cursor = pep_c23.parser_cursor_value(
            sample["document"], sample["revision"], done=True, lex_done=True, lex_stage="done")
        for tool, function, arguments, expected in [
                ("pep-c23-parser-start", "parser_start", [], start_cursor),
                ("pep-c23-parser-step", "parser_step", [finished_cursor],
                 pep_c23.parser_chunk_value(sample["document"], sample["revision"],
                                            finished_cursor))]:
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_register",
                              "tool": tool, "document": tool_document,
                              "revision": cls.tool_revision, "function": function})
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_validate",
                              "tool": tool, "document": tool_document,
                              "revision": cls.tool_revision,
                              "testVectors": [{"arguments": arguments, "expect": expected,
                                                "semanticTarget": target_spec}]})
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_activate",
                              "tool": tool, "document": tool_document,
                              "revision": cls.tool_revision})

    @classmethod
    def tearDownClass(cls):
        cls.session.process.stdin.close()
        cls.session.process.terminate()

    def parse_source(self, source):
        src = source.encode("utf-8")
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                     "name": "parser-budget", "bytes": list(src)})
        self.assertEqual(target.get("outcome"), "ok", target)
        return parse_target(self.session, src, target, self.tool_revision)

    def report_status(self, parsed):
        for field in parsed["fields"]:
            if field["name"] == "status":
                return field["value"]["value"]
        self.fail("ParserProgress has no status field")

    def literal_program(self, length):
        return ('fn main() -> Int {\n  let s = "' + ("a" * length)
                + '"\n  return 0\n}\n')

    def identifier_program(self, length):
        name = "x" * length
        return f"fn main() -> Int {{\n  let {name} = 7\n  return {name}\n}}\n"

    def test_long_string_literal_parses_up_to_1024_characters(self):
        # A2's 640-character reproducer does not reproduce on this head.
        for length in (640, 1024):
            with self.subTest(literalCharacters=length):
                source = self.literal_program(length)
                self.assertEqual(ocaml_check(source), "valid")
                self.assertEqual(self.report_status(self.parse_source(source)), "complete")

    def test_long_string_literal_stops_between_1024_and_1280_characters(self):
        # Documented parser-stage frontier: OCaml-valid source, budget-bound
        # inside one lexer_step scan. Flip when a cheaper literal scan lands.
        source = self.literal_program(1280)
        self.assertEqual(ocaml_check(source), "valid")
        with self.assertRaisesRegex(RuntimeError, "PEP_RUNTIME_STEP_LIMIT"):
            self.parse_source(source)

    def test_long_identifier_parses_at_1280_and_stops_at_1536(self):
        # A separate boundary shows the literal limit is per scanned byte,
        # not a general source-size ceiling.
        accepted = self.identifier_program(1280)
        self.assertEqual(ocaml_check(accepted), "valid")
        self.assertEqual(self.report_status(self.parse_source(accepted)), "complete")
        stopped = self.identifier_program(1536)
        self.assertEqual(ocaml_check(stopped), "valid")
        with self.assertRaisesRegex(RuntimeError, "PEP_RUNTIME_STEP_LIMIT"):
            self.parse_source(stopped)


if __name__ == "__main__":
    unittest.main()
