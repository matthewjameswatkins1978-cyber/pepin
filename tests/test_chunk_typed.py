"""Body-only chunks with checker-certified external type facts (slice 4b).

Uses the new `pep-c23-checker-chunk-typed` tool (`analyze_chunk_typed`):
the chunk carries only the function subtree while record shapes arrive as
`ResolvedTypeDecl` facts derived by `chunk_type_declarations` from the
declaration chunks. No plan/contract change: the frozen `analyze_chunk`
3-arg tool is untouched; stale facts are refused with PEP_STALE_REVISION.

Expected flips (measured): lexer_start body-only 25 nodes + LexCursor
fact becomes valid (was PEP_UNKNOWN_TYPE without facts); make_token
37 nodes stays valid without carrying 18 declaration nodes.
make_progress/make_cursor bodies alone still exceed the step budget -
statement-group continuation remains queued (slice 4c/5).
"""
import copy
import pathlib
import unittest

import pep_c23
import pep_chunk_contract as contract
from pep_c23 import Session, parse_target, require
from tests.chunk_helper import (checked_fn_value, fetch_all_sigs, fields_map,
                                nval, remap_chunk, resolved_sig_value)

ROOT = pathlib.Path(__file__).resolve().parents[1]


def diag_tuples(report):
    out = []
    for item in report.get("diagnostics", {}).get("value", []):
        fields = fields_map(item)
        out.append((fields["code"]["value"], int(fields["startByte"]["value"]),
                    int(fields["endByte"]["value"])))
    return sorted(out)


def host_builtins(document, revision):
    """Host-authorised contract for chunked checking of host builtins.

    `semantic_snapshot` has no Pep-written definition; the host is its
    authority (v2 semanticTarget grant), so the harness supplies its
    CheckedFunction + ResolvedSignature exactly as fetch_all_sigs does
    for user functions (synthetic ids in dedicated ranges, never real
    node ids). `ProgramInfo` facts carry the fields lexer_start needs
    (document/revision/status: Str); the full host record also has
    functions/calls/roots/diagnostics (see pep_ocaml.ml
    semantic_record_info) - unlisted fields stay fail-closed unknown,
    which is sound for bodies that do not touch them. Facts are stamped
    with the target document/revision at provision time, so the typed
    chunk's provenance check treats them as current for this target.
    """
    typed = lambda t, v: {"type": t, "value": str(v) if t == "Int" else v}
    shape = lambda kind, name, depth: {"type": "PepTypeShape", "fields": [
        {"name": "kind", "value": typed("Str", kind)},
        {"name": "name", "value": typed("Str", name)},
        {"name": "listDepth", "value": typed("Int", depth)}]}
    field = lambda name, tname, kind, sname, depth, code, sb, eb, ln, co: {
        "type": "ResolvedTypeField", "fields": [
            {"name": "fieldName", "value": typed("Str", name)},
            {"name": "fieldTypeName", "value": typed("Str", tname)},
            {"name": "fieldShape", "value": shape(kind, sname, depth)},
            {"name": "fieldCode", "value": typed("Str", code)},
            {"name": "startByte", "value": typed("Int", sb)},
            {"name": "endByte", "value": typed("Int", eb)},
            {"name": "line", "value": typed("Int", ln)},
            {"name": "column", "value": typed("Int", co)}]}
    checked_fn = {"type": "CheckedFunction", "fields": [
        {"name": "semanticId", "value": typed("Int", 9500)},
        {"name": "syntaxId", "value": typed("Int", 2000000000)},
        {"name": "name", "value": typed("Str", "semantic_snapshot")},
        {"name": "arity", "value": typed("Int", 0)},
        {"name": "returnType", "value": typed("Str", "ProgramInfo")},
        {"name": "returnShape", "value": shape("nominal", "ProgramInfo", 0)},
        {"name": "startByte", "value": typed("Int", 0)},
        {"name": "endByte", "value": typed("Int", 0)}]}
    sig = {"type": "ResolvedSignature", "fields": [
        {"name": "functionId", "value": typed("Int", 2000000000)},
        {"name": "functionName", "value": typed("Str", "semantic_snapshot")},
        {"name": "params", "value": {"type": "List[ParamTypeFact]", "value": []}},
        {"name": "returnType", "value": typed("Str", "ProgramInfo")},
        {"name": "returnShape", "value": shape("nominal", "ProgramInfo", 0)}]}
    prog_info = {"type": "ResolvedTypeDecl", "fields": [
        {"name": "typeName", "value": typed("Str", "ProgramInfo")},
        {"name": "typeKind", "value": typed("Str", "record")},
        {"name": "declStartByte", "value": typed("Int", 0)},
        {"name": "declEndByte", "value": typed("Int", 0)},
        {"name": "declLine", "value": typed("Int", 1)},
        {"name": "declColumn", "value": typed("Int", 1)},
        {"name": "duplicateType", "value": {"type": "Bool", "value": False}},
        {"name": "document", "value": typed("Str", document)},
        {"name": "revision", "value": typed("Str", revision)},
        {"name": "fields", "value": {"type": "List[ResolvedTypeField]", "value": [
            field("document", "Str", "builtin", "Str", 0, "", 0, 0, 1, 1),
            field("revision", "Str", "builtin", "Str", 0, "", 0, 0, 1, 1),
            field("status", "Str", "builtin", "Str", 0, "", 0, 0, 1, 1)]}}]}
    return [checked_fn], [sig], [prog_info]


class TypedChunkTests(unittest.TestCase):
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
        empty_rep = pep_c23.checker_report(sample["document"], sample["revision"])
        empty_ext = {"type": "List[CheckedFunction]", "value": []}
        empty_sig = {"type": "List[ResolvedSignature]", "value": []}
        empty_types = {"type": "List[ResolvedTypeDecl]", "value": []}
        expect_true = {"type": "Bool", "value": True}
        for tool, function, arguments, expected in [
                ("pep-c23-parser-start", "parser_start", [], start_cursor),
                ("pep-c23-parser-step", "parser_step", [finished_cursor],
                 pep_c23.parser_chunk_value(sample["document"], sample["revision"],
                                            finished_cursor)),
                ("pep-c23-checker", "analyze_parsed",
                 [empty_pp], empty_rep),
                ("pep-c23-checker-chunk", "analyze_chunk",
                 [empty_pp, empty_ext, empty_sig], empty_rep),
                ("pep-c23-checker-typedecls", "chunk_type_declarations",
                 [empty_pp], empty_types),
                ("pep-c23-checker-sigs", "chunk_signatures",
                 [empty_pp], empty_sig),
                ("pep-c23-checker-chunk-typed", "analyze_chunk_typed",
                 [empty_pp, empty_ext, empty_sig, empty_types, expect_true], empty_rep)]:
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

    def sliced(self, parsed, node_ids):
        nodes = fields_map(parsed)["nodes"]["value"]
        by_id = {str(nval(node, "id")): node for node in nodes}
        sub = [copy.deepcopy(by_id[str(node_id)]) for node_id in node_ids]
        chunk = remap_chunk(sub)
        return {"type": "ParserProgress", "fields": [
            {"name": key, "value": ({"type": "List[FlatAstNode]", "value": chunk}
                                    if key == "nodes" else fields_map(parsed)[key])}
            for key in [field["name"] for field in parsed["fields"]]]}

    def type_facts(self, parsed, sem, node_ids):
        response = self.session.send(
            {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
             "tool": "pep-c23-checker-typedecls",
             "arguments": [self.sliced(parsed, node_ids)], "semanticTarget": sem})
        self.assertEqual(response.get("outcome"), "ok", response)
        return response["result"]["value"]

    def invoke_typed(self, sliced, extfns, extsigs, exttypes, sem, expect_returns=True):
        args = [sliced, extfns, extsigs, exttypes,
                {"type": "Bool", "value": expect_returns}]
        response = self.session.send(
            {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
             "tool": "pep-c23-checker-chunk-typed",
             "arguments": args, "semanticTarget": sem})
        self.assertEqual(response.get("outcome"), "ok", response)
        return response["result"]

    def check_whole(self, source_bytes, name):
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                     "name": name, "bytes": list(source_bytes)})
        self.assertEqual(target.get("outcome"), "ok", target)
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": []}
        parsed = parse_target(self.session, source_bytes, target, self.tool_revision)
        response = self.session.send(
            {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
             "tool": "pep-c23-checker",
             "arguments": [parsed], "semanticTarget": sem})
        self.assertEqual(response.get("outcome"), "ok", response)
        report = fields_map(response["result"])
        return target, sem, parsed, report["status"]["value"], diag_tuples(report)

    def check_body_with_facts(self, source_bytes, name, entry, host_builtin_names=(),
                              scope_facts=False, allow_error=False,
                              loop_body_range=None, reverse_facts=False,
                              expect_returns=True):
        # allow_error=True returns the tool error code as the status instead
        # of failing the assertion, so a test can pin a budget refusal.
        # scope_facts=True supplies only the external declarations the chunk
        # can name (index.fact_closure) instead of every declaration in the
        # document. Omitting a declaration the chunk never mentions cannot
        # change its meaning, but it does stop the chunk paying to re-derive
        # facts about the rest of the program.
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                     "name": name, "bytes": list(source_bytes)})
        self.assertEqual(target.get("outcome"), "ok", target)
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": []}
        parsed = parse_target(self.session, source_bytes, target, self.tool_revision)
        nodes = fields_map(parsed)["nodes"]["value"]
        index = contract.DocumentIndex.from_parsed(parsed)
        sigs = fetch_all_sigs(self.session, parsed, self.tool_revision, sem)
        decl_roots = [int(nval(node, "id")) for node in nodes
                      if str(nval(node, "parentId")) == "-1"
                      and nval(node, "kind") in ("record_declaration", "union_declaration")]
        facts = []
        for root in decl_roots:
            facts.extend(self.type_facts(parsed, sem, index.subtree(root)))
        if reverse_facts:
            # Order-dependence probe: the staged verdict must not depend on
            # fact order, and a duplicated source must be refused either way.
            facts = facts[::-1]
        functions = [node for node in nodes if nval(node, "kind") == "function"
                     and str(nval(node, "parentId")) == "-1"]
        bodies = {str(nval(fn, "text")): index.subtree(int(nval(fn, "id")))
                  for fn in functions}
        self.assertIn(entry, bodies)
        if loop_body_range is not None:
            bodies[entry] = self.trim_loop_body(
                index, nodes, entry, loop_body_range)
        ext = [s for s in sigs if s["name"] != entry]
        if scope_facts:
            allowed = index.fact_closure(
                bodies[entry], {s["name"] for s in ext})
            ext = [s for s in ext if s["name"] in allowed]
        host_fns, host_sigs, host_types = [], [], []
        if host_builtin_names:
            assert set(host_builtin_names) <= {"semantic_snapshot"}
            host_fns, host_sigs, host_types = host_builtins(
                target["document"], target["revision"])
        args = [self.sliced(parsed, bodies[entry]),
                {"type": "List[CheckedFunction]",
                 "value": [checked_fn_value(s) for s in ext] + host_fns},
                {"type": "List[ResolvedSignature]",
                 "value": [resolved_sig_value(s) for s in ext] + host_sigs},
                {"type": "List[ResolvedTypeDecl]", "value": facts + host_types}]
        if allow_error:
            response = self.session.send(
                {"schemaVersion": 3, "toolProtocolVersion": 2,
                 "op": "tool_invoke", "tool": "pep-c23-checker-chunk-typed",
                 "arguments": args + [{"type": "Bool", "value": expect_returns}],
                 "semanticTarget": sem})
            if response.get("outcome") != "ok":
                return (response.get("error") or {}).get("code"), []
            return fields_map(response["result"])["status"]["value"], []
        report = fields_map(self.invoke_typed(
            args[0], args[1], args[2], args[3], sem,
            expect_returns=expect_returns))
        return report["status"]["value"], diag_tuples(report)

    def trim_loop_body(self, index, nodes, entry, rng):
        # Bounded unit below statement granularity: keep the function, keep a
        # single range of the for-loop's body statements, and drop the rest.
        # Byte spans are untouched, so the unit still reports diagnostics at
        # original source offsets.
        fn = [n for n in nodes if nval(n, "kind") == "function"
              and str(nval(n, "parentId")) == "-1"
              and str(nval(n, "text")) == entry]
        self.assertEqual(len(fn), 1, entry)
        fn_id = str(nval(fn[0], "id"))
        for_node = [n for n in nodes if str(nval(n, "parentId")) == fn_id
                    and nval(n, "kind") == "for_in"]
        self.assertEqual(len(for_node), 1, f"{entry} needs exactly one for-in")
        for_id = str(nval(for_node[0], "id"))
        inner = sorted([n for n in nodes
                        if str(nval(n, "parentId")) == for_id
                        and nval(n, "role") == "body"],
                       key=lambda n: int(nval(n, "childIndex")))
        lo, hi = rng
        self.assertLessEqual(hi, len(inner))
        drop = set()
        for position, statement in enumerate(inner):
            if not lo <= position < hi:
                drop.update(index.subtree(int(nval(statement, "id"))))
        return tuple(i for i in index.subtree(int(fn_id)) if i not in drop)

    def check_statement_group(self, source_bytes, name, entry, stmt_range,
                              host_builtin_names=(), expect_returns=False,
                              carry_stmt_indexes=(), scope_facts=False):
        """Check a header + statement-subset chunk (non-terminal by default).

        Carried bindings are re-included as source subtrees (deterministic
        re-check, same diagnostics); only the terminal group needs
        expect_returns=True. stmt_range is a (lo, hi) slice over the
        function body's top-level statements in order; carry_stmt_indexes
        names additional earlier statements (e.g. lets/vars the group reads)
        to re-include for binding context.
        """
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                     "name": name, "bytes": list(source_bytes)})
        self.assertEqual(target.get("outcome"), "ok", target)
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": []}
        parsed = parse_target(self.session, source_bytes, target, self.tool_revision)
        nodes = fields_map(parsed)["nodes"]["value"]
        index = contract.DocumentIndex.from_parsed(parsed)
        sigs = fetch_all_sigs(self.session, parsed, self.tool_revision, sem)
        decl_roots = [int(nval(node, "id")) for node in nodes
                      if str(nval(node, "parentId")) == "-1"
                      and nval(node, "kind") in ("record_declaration", "union_declaration")]
        facts = []
        for root in decl_roots:
            facts.extend(self.type_facts(parsed, sem, index.subtree(root)))
        by_id = {str(nval(node, "id")): node for node in nodes}
        table = {str(nval(fn, "text")): int(nval(fn, "id"))
                 for fn in nodes
                 if nval(fn, "kind") == "function"
                 and str(nval(fn, "parentId")) == "-1"}
        self.assertIn(entry, table)
        root_id = str(table[entry])
        keep = {root_id}
        for node in nodes:
            if str(nval(node, "parentId")) == root_id and \
                    nval(node, "role") in ("parameter", "return_type"):
                keep.update(index.subtree(int(nval(node, "id"))))
        statements = [node for node in nodes
                      if str(nval(node, "parentId")) == root_id
                      and nval(node, "role") == "statement"]
        lo, hi = stmt_range
        for st in statements[lo:hi]:
            keep.update(index.subtree(int(nval(st, "id"))))
        for ci in carry_stmt_indexes:
            keep.update(index.subtree(int(nval(statements[ci], "id"))))
        ext = [s for s in sigs if s["name"] != entry]
        if scope_facts:
            allowed = index.fact_closure(keep, {s["name"] for s in ext})
            ext = [s for s in ext if s["name"] in allowed]
        host_fns, host_sigs, host_types = [], [], []
        if host_builtin_names:
            assert set(host_builtin_names) <= {"semantic_snapshot"}
            host_fns, host_sigs, host_types = host_builtins(
                target["document"], target["revision"])
        report = fields_map(self.invoke_typed(
            self.sliced(parsed, keep),
            {"type": "List[CheckedFunction]",
             "value": [checked_fn_value(s) for s in ext] + host_fns},
            {"type": "List[ResolvedSignature]",
             "value": [resolved_sig_value(s) for s in ext] + host_sigs},
            {"type": "List[ResolvedTypeDecl]", "value": facts + host_types},
            sem, expect_returns=expect_returns))
        return report["status"]["value"], diag_tuples(report)

    def test_staged_lexer_landscape_matches_pins(self):
        # Full per-function staged ledger: body-only chunk + external type
        # facts (+ host builtins where the body needs semantic_snapshot).
        # Pins are deliberate: a flip in either direction forces re-measure.
        # make_progress (49n) was valid unscoped until the duplicate-type
        # closure gate spent its last headroom (re-measured: the same
        # function stays valid via scope_facts, the production pattern, so
        # no capability is lost — unscoped recovery is scaling work);
        # make_cursor (69n) remains a single-return body over
        # budget; utf8_check (268n) needs statement groups (see
        # the G1/G2 tests); lexer_step body alone exceeds the 1 MiB message.
        source = (ROOT / "examples" / "pep_lexer.pep").read_bytes()
        pinned = {
            "ascii_letter": "valid",
            "ascii_digit": "valid",
            "ascii_continue": "valid",
            "advance_position": "valid",
            "make_token": "valid",
            "lexer_start": "valid",
            "make_progress": "STEP_LIMIT",
            "make_cursor": "STEP_LIMIT",
            "utf8_check": "STEP_LIMIT",
        }
        host_needed = {"lexer_start"}
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                     "name": "ledger-landscape",
                                     "bytes": list(source)})
        self.assertEqual(target.get("outcome"), "ok", target)
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": []}
        parsed = parse_target(self.session, source, target, self.tool_revision)
        nodes = fields_map(parsed)["nodes"]["value"]
        index = contract.DocumentIndex.from_parsed(parsed)
        by_id = {str(nval(node, "id")): node for node in nodes}
        sigs = fetch_all_sigs(self.session, parsed, self.tool_revision, sem)
        decl_roots = [int(nval(node, "id")) for node in nodes
                      if str(nval(node, "parentId")) == "-1"
                      and nval(node, "kind") in ("record_declaration", "union_declaration")]
        facts = []
        for root in decl_roots:
            facts.extend(self.type_facts(parsed, sem, index.subtree(root)))
        functions = {str(nval(node, "text")): int(nval(node, "id"))
                     for node in nodes
                     if nval(node, "kind") == "function"
                     and str(nval(node, "parentId")) == "-1"}
        for name, want in pinned.items():
            with self.subTest(function=name):
                self.assertIn(name, functions)
                sub = [copy.deepcopy(by_id[str(i)])
                       for i in index.subtree(functions[name])]
                chunk = remap_chunk(sub)
                sliced = {"type": "ParserProgress", "fields": [
                    {"name": key,
                     "value": ({"type": "List[FlatAstNode]", "value": chunk}
                               if key == "nodes" else fields_map(parsed)[key])}
                    for key in [field["name"] for field in parsed["fields"]]]}
                ext = [s for s in sigs if s["name"] != name]
                host_fns, host_sigs, host_types = [], [], []
                if name in host_needed:
                    host_fns, host_sigs, host_types = host_builtins(
                        target["document"], target["revision"])
                args = [sliced,
                        {"type": "List[CheckedFunction]",
                         "value": [checked_fn_value(s) for s in ext] + host_fns},
                        {"type": "List[ResolvedSignature]",
                         "value": [resolved_sig_value(s) for s in ext] + host_sigs},
                        {"type": "List[ResolvedTypeDecl]",
                         "value": facts + host_types},
                        {"type": "Bool", "value": True}]
                try:
                    response = self.session.send(
                        {"schemaVersion": 3, "toolProtocolVersion": 2,
                         "op": "tool_invoke", "tool": "pep-c23-checker-chunk-typed",
                         "arguments": args, "semanticTarget": sem})
                except RuntimeError as error:
                    self.assertEqual(want, "TRANSPORT", name)
                    self.assertIn("1 MiB", str(error), name)
                    continue
                if response.get("outcome") != "ok":
                    code = (response.get("error") or {}).get("code")
                    self.assertEqual(code, "PEP_RUNTIME_STEP_LIMIT", response)
                    self.assertEqual(want, "STEP_LIMIT", name)
                    continue
                report = fields_map(response["result"])
                self.assertEqual(report["status"]["value"], want, report)
                self.assertEqual(diag_tuples(report), [])

    def test_lexer_start_body_only_flips_with_facts(self):
        source = (ROOT / "examples" / "pep_lexer.pep").read_bytes()
        status, diags = self.check_body_with_facts(
            source, "lexer-facts", "lexer_start",
            host_builtin_names=("semantic_snapshot",))
        self.assertEqual(status, "valid", diags)
        self.assertEqual(diags, [])

    def test_make_token_body_only_stays_valid_with_facts(self):
        source = (ROOT / "examples" / "pep_lexer.pep").read_bytes()
        status, diags = self.check_body_with_facts(source, "lexer-facts", "make_token")
        self.assertEqual(status, "valid", diags)
        self.assertEqual(diags, [])

    def test_stdlib_collection_loop_checks_staged(self):
        # A real stdlib helper with a for-in loop and conditional updates.
        # Whole-program checking (55 nodes) exceeds the step budget, but the
        # function body checks valid on its own once the other declarations
        # are supplied as certified external facts. This is the concrete
        # route through real Pep modules: the cost lives in re-deriving
        # program-wide facts, not in the loop body itself.
        source = self.collection_probe_source()
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                     "name": "coll-whole", "bytes": list(source)})
        self.assertEqual(target.get("outcome"), "ok", target)
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": []}
        parsed = parse_target(self.session, source, target, self.tool_revision)
        whole = self.session.send(
            {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
             "tool": "pep-c23-checker", "arguments": [parsed],
             "semanticTarget": sem})
        self.assertEqual(whole.get("outcome"), "error", whole)
        self.assertEqual((whole.get("error") or {}).get("code"),
                         "PEP_RUNTIME_STEP_LIMIT", whole)
        staged, diags = self.check_body_with_facts(
            source, "coll-staged", "list_int_min_between")
        self.assertEqual(staged, "valid", diags)
        self.assertEqual(diags, [])
        # The whole program is then covered by independently bounded units:
        # every top-level function checks valid as its own chunk, so the
        # staged path accepts a real program the whole-program checker
        # rejects. Coverage is asserted, not assumed.
        functions = [str(nval(node, "text")) for node in fields_map(parsed)["nodes"]["value"]
                     if nval(node, "kind") == "function"
                     and str(nval(node, "parentId")) == "-1"]
        self.assertEqual(sorted(functions), ["list_int_min_between", "main"])
        for entry in functions:
            with self.subTest(entry=entry):
                status, diags = self.check_body_with_facts(
                    source, f"coll-unit-{entry}", entry)
                self.assertEqual(status, "valid", diags)
                self.assertEqual(diags, [])

    def test_stdlib_collection_loop_staged_is_genuinely_checked(self):
        # The staged flip above must not be a weakened check: three separate
        # type errors inside the loop body are still reported with spans.
        text = self.collection_probe_source().decode("utf-8")
        for old, new, offset in [
                ("var minimum = fallback", "var minimum = found", 226),
                ("found = found || (lower <= item && item <= upper)",
                 "found = minimum", 276),
                ("minimum = if lower <= item", "minimum = if lower", 176)]:
            with self.subTest(mutation=new):
                self.assertEqual(text.count(old), 1, old)
                mutated = text.replace(old, new, 1).encode("utf-8")
                status, diags = self.check_body_with_facts(
                    mutated, "coll-neg", "list_int_min_between")
                self.assertEqual(status, "invalid", diags)
                self.assertEqual([(code, start) for code, start, _ in diags],
                                 [("PEP_TYPE_MISMATCH", offset)], diags)

    def collection_probe_source(self):
        # Exact fixture used by tests/test_c23_collections.py for
        # list_int_min_between, so the staged path is measured on the same
        # real program the whole-program checker currently rejects.
        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        start = library.index("fn list_int_min_between(")
        end = library.index("\n}\n", start) + 3
        return (library[start:end]
                + "\nfn main() -> Int {\n"
                + "  return list_int_min_between([], 0, 3, 9)\n}\n").encode("utf-8")

    def test_module_functions_need_dependency_scoped_facts(self):
        # stdlib/collections.pep: 2901 nodes, 107 top-level functions. Giving
        # one chunk every external signature in the module exceeds the step
        # budget; scoping the facts to the chunk's own name closure (often
        # empty) makes the same bodies check valid. The choice is sound
        # because a declaration the chunk never names cannot affect it.
        source = (ROOT / "stdlib" / "collections.pep").read_bytes()
        entries = ["list_int_min_between", "list_int_count_between_runs",
                   "list_int_count_runs", "list_bool_has_true_majority"]
        for entry in entries:
            with self.subTest(entry=entry, facts="all"):
                status, _ = self.check_body_with_facts(
                    source, f"mod-{entry}-all", entry, allow_error=True)
                self.assertEqual(status, "PEP_RUNTIME_STEP_LIMIT")
            with self.subTest(entry=entry, facts="closure"):
                status, diags = self.check_body_with_facts(
                    source, f"mod-{entry}-closure", entry, scope_facts=True)
                self.assertEqual(status, "valid", diags)
                self.assertEqual(diags, [])

    def test_fact_closure_keeps_named_declarations_and_drops_the_rest(self):
        # Sound selection: a candidate survives only if the chunk can name it.
        source = (ROOT / "stdlib" / "collections.pep").read_bytes()
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                     "name": "closure-index", "bytes": list(source)})
        self.assertEqual(target.get("outcome"), "ok", target)
        parsed = parse_target(self.session, source, target, self.tool_revision)
        nodes = fields_map(parsed)["nodes"]["value"]
        index = contract.DocumentIndex.from_parsed(parsed)
        table = {str(nval(fn, "text")): int(nval(fn, "id"))
                 for fn in nodes
                 if nval(fn, "kind") == "function"
                 and str(nval(fn, "parentId")) == "-1"}
        body = index.subtree(table["list_int_min_between"])
        candidates = {"list_int_min_between", "list_int_sum_between",
                      "list_bool_longest_run", "no_such_declaration"}
        kept = index.fact_closure(body, candidates)
        self.assertEqual(sorted(kept), ["list_int_min_between"])

    def test_residual_module_functions_split_inside_the_loop(self):
        # The last 2 of 107 collection functions have 75-node bodies whose
        # single for statement is over budget on its own, so neither whole
        # body nor statement groups suffice. Splitting inside the loop body
        # brings each unit to ~42 nodes and all of them check valid.
        source = (ROOT / "stdlib" / "collections.pep").read_bytes()
        for entry in ["list_int_min_index_between",
                      "list_int_max_index_between"]:
            with self.subTest(entry=entry, unit="whole-body"):
                status, _ = self.check_body_with_facts(
                    source, f"res-{entry}", entry,
                    scope_facts=True, allow_error=True)
                self.assertEqual(status, "PEP_RUNTIME_STEP_LIMIT")
            for lo, hi in [(0, 1), (1, 2), (2, 4)]:
                with self.subTest(entry=entry, unit=f"loop-body[{lo}:{hi}]"):
                    status, diags = self.check_body_with_facts(
                        source, f"res-{entry}-{lo}-{hi}", entry,
                        scope_facts=True, loop_body_range=(lo, hi))
                    self.assertEqual(status, "valid", diags)
                    self.assertEqual(diags, [])

    def test_loop_body_unit_keeps_source_offsets(self):
        # A trimmed unit must still report an error at the original byte
        # offset, so staged units are not detached from source identity.
        source = (ROOT / "stdlib" / "collections.pep").read_bytes()
        text = source.decode("utf-8")
        old = "found = found || (lower <= item && item <= upper)"
        start = text.index("fn list_int_min_index_between(")
        tail = "\n}\n" if "\n}\n" in text[start:] else "\r\n}\r\n"
        end = text.index(tail, start) + len(tail)
        self.assertIn(old, text[start:end])
        mutated = (text[:start]
                   + text[start:end].replace(old, "found = index", 1)
                   + text[end:]).encode("utf-8")
        status, diags = self.check_body_with_facts(
            mutated, "loop-offsets", "list_int_min_index_between",
            scope_facts=True, loop_body_range=(2, 4))
        self.assertEqual(status, "invalid", diags)
        self.assertEqual([code for code, _, _ in diags], ["PEP_TYPE_MISMATCH"])
        start = diags[0][1]
        self.assertEqual(mutated[start:start + 5], b"index")

    def test_residual_functions_have_a_complete_valid_partition(self):
        # Both residual functions partition into gapless bounded units that
        # each check valid: statements 0-3 (declarations), the three loop-body
        # units, and the terminal return with its binding carried. Together
        # this covers every statement, so the 107th of 107 real module
        # functions is verifiable under the unchanged budget.
        source = (ROOT / "stdlib" / "collections.pep").read_bytes()
        for entry in ["list_int_min_index_between",
                      "list_int_max_index_between"]:
            with self.subTest(entry=entry, unit="statements[0:4]"):
                status, diags = self.check_statement_group(
                    source, f"part-{entry}-vars", entry, (0, 4),
                    scope_facts=True)
                self.assertEqual(status, "valid", diags)
            for lo, hi in [(0, 1), (1, 2), (2, 4)]:
                with self.subTest(entry=entry, unit=f"loop[{lo}:{hi}]"):
                    status, diags = self.check_body_with_facts(
                        source, f"part-{entry}-{lo}", entry,
                        scope_facts=True, loop_body_range=(lo, hi))
                    self.assertEqual(status, "valid", diags)
                    self.assertEqual(diags, [])
            with self.subTest(entry=entry, unit="return[5:6]"):
                status, diags = self.check_statement_group(
                    source, f"part-{entry}-ret", entry, (5, 6),
                    expect_returns=True, scope_facts=True,
                    carry_stmt_indexes=(1,))
                self.assertEqual(status, "valid", diags)

    def test_lexer_step_split_floor_is_the_step_budget(self):
        # lexer_step (1427 nodes) cannot be covered by splitting. Its while
        # body holds one if_statement (1021 nodes) whose else spine nests to
        # a single 12-node branch. The smallest structurally valid unit is the
        # function with the outermost else pruned: 518 nodes, which still
        # exceeds the step budget. Deeper units grow, not shrink, so no split
        # reaches a passing unit - the residual is per-node checker cost.
        source = (ROOT / "examples" / "pep_lexer.pep").read_bytes()
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                     "name": "lexer-step-floor",
                                     "bytes": list(source)})
        self.assertEqual(target.get("outcome"), "ok", target)
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": []}
        parsed = parse_target(self.session, source, target, self.tool_revision)
        nodes = fields_map(parsed)["nodes"]["value"]
        index = contract.DocumentIndex.from_parsed(parsed)
        sigs = fetch_all_sigs(self.session, parsed, self.tool_revision, sem)
        decl_roots = [int(nval(n, "id")) for n in nodes
                      if str(nval(n, "parentId")) == "-1"
                      and nval(n, "kind") in ("record_declaration",
                                              "union_declaration")]
        facts = []
        for root in decl_roots:
            facts.extend(self.type_facts(parsed, sem, index.subtree(root)))
        table = {str(nval(fn, "text")): int(nval(fn, "id")) for fn in nodes
                 if nval(fn, "kind") == "function"
                 and str(nval(fn, "parentId")) == "-1"}
        full = index.subtree(table["lexer_step"])
        self.assertEqual(len(full), 1427)

        def invoke(keep):
            ext = [s for s in sigs if s["name"] != "lexer_step"]
            allowed = index.fact_closure(keep, {s["name"] for s in ext})
            ext = [s for s in ext if s["name"] in allowed]
            try:
                response = self.session.send(
                    {"schemaVersion": 3, "toolProtocolVersion": 2,
                     "op": "tool_invoke",
                     "tool": "pep-c23-checker-chunk-typed",
                     "arguments": [
                         self.sliced(parsed, keep),
                         {"type": "List[CheckedFunction]",
                          "value": [checked_fn_value(s) for s in ext]},
                         {"type": "List[ResolvedSignature]",
                          "value": [resolved_sig_value(s) for s in ext]},
                         {"type": "List[ResolvedTypeDecl]", "value": facts},
                         {"type": "Bool", "value": True}],
                     "semanticTarget": sem})
            except RuntimeError as error:
                self.assertIn("1 MiB", str(error))
                return "TRANSPORT"
            if response.get("outcome") != "ok":
                return (response.get("error") or {}).get("code")
            return fields_map(response["result"])["status"]["value"]

        self.assertEqual(invoke(full), "TRANSPORT")
        # Prune the outermost if's else: the smallest valid unit.
        while_body = [n for n in nodes
                      if str(nval(n, "parentId")) == str(table["lexer_step"])
                      and nval(n, "role") == "statement"
                      and nval(n, "kind") == "while"][0]
        inner_if = [n for n in nodes
                    if str(nval(n, "parentId")) == str(nval(while_body, "id"))
                    and nval(n, "role") == "body"][0]
        outer_else = [n for n in nodes
                      if str(nval(n, "parentId")) == str(nval(inner_if, "id"))
                      and nval(n, "role") == "else"][0]
        drop = set(index.subtree(int(nval(outer_else, "id"))))
        keep = tuple(i for i in full if i not in drop)
        self.assertEqual(len(keep), 518)
        self.assertEqual(invoke(keep), "PEP_RUNTIME_STEP_LIMIT")

    def test_utf8_check_prefix_group_checks_valid(self):
        # First statement group of utf8_check (params + first 4 statements,
        # 28 header/body nodes + external type facts): no missing-return
        # diagnostic because the group is explicitly non-terminal.
        source = (ROOT / "examples" / "pep_lexer.pep").read_bytes()
        status, diags = self.check_statement_group(
            source, "lexer-g1", "utf8_check", (0, 4))
        self.assertEqual(status, "valid", diags)
        self.assertEqual(diags, [])

    def test_utf8_check_second_group_with_carried_bindings(self):
        # Statements 4-5 (two range checks, ~24 nodes) plus re-included
        # binding statements (let first, var width, var minimum): the group
        # checks valid without re-verifying the whole prefix and without a
        # missing-return diagnostic (non-terminal).
        source = (ROOT / "examples" / "pep_lexer.pep").read_bytes()
        status, diags = self.check_statement_group(
            source, "lexer-g2", "utf8_check", (4, 6),
            carry_stmt_indexes=(0, 2, 3))
        self.assertEqual(status, "valid", diags)
        self.assertEqual(diags, [])

    def test_stale_facts_are_refused(self):
        source = (b"type Box { f: Int }\n"
                  b"fn main() -> Int { return 0 }\n")
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                     "name": "stale-rev1", "bytes": list(source)})
        self.assertEqual(target.get("outcome"), "ok", target)
        sem1 = {"document": target["document"], "revision": target["revision"],
                "entryFunctions": []}
        parsed1 = parse_target(self.session, source, target, self.tool_revision)
        nodes = fields_map(parsed1)["nodes"]["value"]
        index = contract.DocumentIndex.from_parsed(parsed1)
        decl_roots = [int(nval(node, "id")) for node in nodes
                      if str(nval(node, "parentId")) == "-1"
                      and nval(node, "kind") in ("record_declaration", "union_declaration")]
        facts = []
        for root in decl_roots:
            facts.extend(self.type_facts(parsed1, sem1, index.subtree(root)))
        advance = self.session.send({"schemaVersion": 3, "op": "apply_edit",
                                      "document": target["document"],
                                      "expected_revision": target["revision"],
                                      "start_byte": 0, "end_byte": 0,
                                      "replacement": "//x\n"})
        self.assertEqual(advance.get("outcome"), "ok", advance)
        fresh = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                    "name": "stale-rev2",
                                    "bytes": list(b"//x\n" + source)})
        self.assertEqual(fresh.get("outcome"), "ok", fresh)
        sem2 = {"document": fresh["document"], "revision": fresh["revision"],
                "entryFunctions": []}
        parsed2 = parse_target(self.session, b"//x\n" + source, fresh,
                               self.tool_revision)
        nodes2 = fields_map(parsed2)["nodes"]["value"]
        mains = [int(nval(node, "id")) for node in nodes2
                 if nval(node, "kind") == "function"
                 and str(nval(node, "parentId")) == "-1"]
        empty = lambda t: {"type": t, "value": []}
        response = self.session.send(
            {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
             "tool": "pep-c23-checker-chunk-typed",
             "arguments": [self.sliced(parsed2, index.subtree(mains[0])),
                           empty("List[CheckedFunction]"),
                           empty("List[ResolvedSignature]"),
                           {"type": "List[ResolvedTypeDecl]", "value": facts},
                           {"type": "Bool", "value": True}],
             "semanticTarget": sem2})
        self.assertEqual(response.get("outcome"), "ok", response)
        report = fields_map(response["result"])
        self.assertEqual(report["status"]["value"], "invalid", report)
        diags = report.get("diagnostics", {}).get("value", [])
        codes = [fields_map(item)["code"]["value"] for item in diags]
        self.assertIn("PEP_STALE_REVISION", codes)
        messages = [fields_map(item)["message"]["value"] for item in diags]
        self.assertTrue(
            any("External type facts" in message for message in messages),
            messages)

    def test_missing_field_matches_whole_path(self):
        source = (b"type Box { f: Int, g: Int }\n"
                  b"fn build() -> Box { return Box { f: 1 } }\n"
                  b"fn main() -> Int { return 0 }\n")
        _, _, _, whole_status, whole_diags = self.check_whole(source, "miss-whole")
        self.assertEqual(whole_status, "invalid")
        status, diags = self.check_body_with_facts(source, "miss-chunk", "build")
        self.assertEqual(status, "invalid")
        self.assertEqual(diags, whole_diags)

    def test_wrong_field_type_matches_whole_path(self):
        source = (b'type Box { f: Int, g: Str }\n'
                  b'fn build() -> Box { return Box { f: 1, g: 2 } }\n'
                  b'fn main() -> Int { return 0 }\n')
        _, _, _, whole_status, whole_diags = self.check_whole(source, "mistype-whole")
        self.assertEqual(whole_status, "invalid")
        status, diags = self.check_body_with_facts(source, "mistype-chunk", "build")
        self.assertEqual(status, "invalid")
        self.assertEqual(diags, whole_diags)

    # --- Staged declaration-closure contract (duplicate-type fail-open fix).
    #
    # Agent 3's minimised 81-byte counterexample: two `type D` declarations.
    # The seed rejects it with PEP_DUPLICATE_TYPE; the staged chunk used to
    # accept it when the per-declaration facts arrived in gathered order.

    DUP_SOURCE = (b"type D {\n"
                  b"    a: Int\n"
                  b"}\n"
                  b"type D {\n"
                  b"    b: Int\n"
                  b"}\n"
                  b"fn f(d: D) -> Int {\n"
                  b"    return d.a\n"
                  b"}\n")

    def test_duplicate_type_source_matches_whole_path(self):
        self.assertEqual(len(self.DUP_SOURCE), 81, len(self.DUP_SOURCE))
        _, _, _, whole_status, whole_diags = self.check_whole(
            self.DUP_SOURCE, "dup-whole")
        self.assertEqual(whole_status, "invalid")
        self.assertTrue(any(code == "PEP_DUPLICATE_TYPE"
                            for code, _, _ in whole_diags), whole_diags)
        for reverse in (False, True):
            status, diags = self.check_body_with_facts(
                self.DUP_SOURCE, f"dup-chunk-{reverse}", "f",
                reverse_facts=reverse)
            self.assertEqual(status, "invalid", (reverse, diags))
            self.assertTrue(any(code == "PEP_DUPLICATE_TYPE"
                                for code, _, _ in diags), (reverse, diags))

    def test_duplicate_type_refused_without_expect_returns(self):
        # A3's R4 cell: with expectReturns=false the pre-fix chunk accepted
        # the duplicated source in BOTH fact orders. Both must refuse now.
        for reverse in (False, True):
            status, diags = self.check_body_with_facts(
                self.DUP_SOURCE, f"dup-noret-{reverse}", "f",
                reverse_facts=reverse, expect_returns=False)
            self.assertEqual(status, "invalid", (reverse, diags))
            self.assertTrue(any(code == "PEP_DUPLICATE_TYPE"
                                for code, _, _ in diags), (reverse, diags))

    def test_carried_duplicate_flag_is_refused(self):
        # Whole-document producer output marks the repeated name, so a body
        # chunk built from those facts alone must refuse (producer leg).
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                     "name": "dup-prod",
                                     "bytes": list(self.DUP_SOURCE)})
        self.assertEqual(target.get("outcome"), "ok", target)
        sem = {"document": target["document"],
               "revision": target["revision"], "entryFunctions": []}
        parsed = parse_target(self.session, self.DUP_SOURCE, target,
                              self.tool_revision)
        nodes = fields_map(parsed)["nodes"]["value"]
        index = contract.DocumentIndex.from_parsed(parsed)
        all_ids = [int(nval(node, "id")) for node in nodes]
        facts = self.type_facts(parsed, sem, all_ids)
        dup_flags = [fields_map(fact)["duplicateType"]["value"]
                     for fact in facts]
        self.assertIn(True, dup_flags, dup_flags)
        sigs = fetch_all_sigs(self.session, parsed, self.tool_revision, sem)
        ext = [s for s in sigs if s["name"] != "f"]
        bodies = {str(nval(node, "text")): index.subtree(int(nval(node, "id")))
                  for node in nodes
                  if nval(node, "kind") == "function"
                  and str(nval(node, "parentId")) == "-1"}
        report = fields_map(self.invoke_typed(
            self.sliced(parsed, bodies["f"]),
            {"type": "List[CheckedFunction]",
             "value": [checked_fn_value(s) for s in ext]},
            {"type": "List[ResolvedSignature]",
             "value": [resolved_sig_value(s) for s in ext]},
            {"type": "List[ResolvedTypeDecl]", "value": facts}, sem))
        self.assertEqual(report["status"]["value"], "invalid", report)
        codes = [fields_map(item)["code"]["value"]
                 for item in report.get("diagnostics", {}).get("value", [])]
        self.assertIn("PEP_DUPLICATE_TYPE", codes, codes)

    # --- Cross-kind (record/union) duplicate closure (A3 X3/X6/X7).
    #
    # The seed keeps one source-wide type namespace across record and
    # union declarations. The staged producer now emits union facts, so
    # per-root gathered facts refuse by repeated name and whole-input
    # facts refuse by carried flag, both with PEP_DUPLICATE_TYPE.

    CROSS_KIND_DUP = (b"type D {\n"
                      b"    a: Int\n"
                      b"}\n"
                      b"type D = Left() | Right()\n"
                      b"fn f(d: D) -> Int {\n"
                      b"    return d.a\n"
                      b"}\n")
    CROSS_KIND_DUP_REV = (b"type D = Left() | Right()\n"
                          b"type D {\n"
                          b"    a: Int\n"
                          b"}\n"
                          b"fn f(d: D) -> Int {\n"
                          b"    return d.a\n"
                          b"}\n")
    CROSS_KIND_OK = (b"type E {\n"
                     b"    a: Int\n"
                     b"}\n"
                     b"type F = Left() | Right()\n"
                     b"fn f(e: E) -> Int {\n"
                     b"    return e.a\n"
                     b"}\n")
    UNION_PARAM = (b"type F = Left() | Right()\n"
                   b"fn f(x: F) -> Int {\n"
                   b"    return 0\n"
                   b"}\n")

    def test_cross_kind_duplicate_matches_whole_path(self):
        for source, tag in ((self.CROSS_KIND_DUP, "kk"),
                            (self.CROSS_KIND_DUP_REV, "kkrev")):
            _, _, _, whole_status, whole_diags = self.check_whole(
                source, f"kk-whole-{tag}")
            self.assertEqual(whole_status, "invalid")
            self.assertTrue(any(code == "PEP_DUPLICATE_TYPE"
                                for code, _, _ in whole_diags), whole_diags)
            for reverse in (False, True):
                status, diags = self.check_body_with_facts(
                    source, f"kk-chunk-{tag}-{reverse}", "f",
                    reverse_facts=reverse)
                self.assertEqual(status, "invalid", (tag, reverse, diags))
                self.assertTrue(any(code == "PEP_DUPLICATE_TYPE"
                                    for code, _, _ in diags),
                                (tag, reverse, diags))

    def test_cross_kind_distinct_names_stay_valid(self):
        _, _, _, whole_status, _ = self.check_whole(
            self.CROSS_KIND_OK, "kk-ok-whole")
        self.assertEqual(whole_status, "valid")
        for reverse in (False, True):
            status, diags = self.check_body_with_facts(
                self.CROSS_KIND_OK, f"kk-ok-{reverse}", "f",
                reverse_facts=reverse)
            self.assertEqual(status, "valid", (reverse, diags))
            self.assertEqual(diags, [])

    def test_union_typed_parameter_stays_valid_staged(self):
        _, _, _, whole_status, _ = self.check_whole(
            self.UNION_PARAM, "union-param-whole")
        self.assertEqual(whole_status, "valid")
        status, diags = self.check_body_with_facts(
            self.UNION_PARAM, "union-param-chunk", "f")
        self.assertEqual(status, "valid", diags)
        self.assertEqual(diags, [])

    # Caller-precondition note (not a runtime test): the closure gate covers
    # carried flags and repeated external names, but not a chunk that itself
    # declares a type also supplied externally (split-root shape). No harness
    # chunk shape produces that input — chunks are function or statement
    # subtrees, which cannot declare types — so it is a documented caller
    # obligation, enforced by construction of the gathering helpers above.

    def test_unique_type_facts_stay_valid_both_orders(self):
        # Guard against over-refusal: two distinct types must check valid in
        # either fact order, matching the whole path.
        source = (b"type Box { f: Int }\n"
                  b"type Bag { g: Str }\n"
                  b"fn f(bx: Box, bg: Bag) -> Int { return bx.f }\n")
        _, _, _, whole_status, _ = self.check_whole(source, "uniq-whole")
        self.assertEqual(whole_status, "valid")
        for reverse in (False, True):
            status, diags = self.check_body_with_facts(
                source, f"uniq-chunk-{reverse}", "f",
                reverse_facts=reverse)
            self.assertEqual(status, "valid", (reverse, diags))
            self.assertEqual(diags, [])

    def test_make_progress_scoped_stays_valid_under_closure_gate(self):
        # Production-pattern guard: the function the unscoped landscape pin
        # now records as STEP_LIMIT stays valid with dependency-scoped
        # facts, proving the closure gate fits the production path and no
        # capability is lost — unscoped recovery is scaling work.
        source = (ROOT / "examples" / "pep_lexer.pep").read_bytes()
        status, diags = self.check_body_with_facts(
            source, "mp-scoped-gate", "make_progress", scope_facts=True)
        self.assertEqual(status, "valid", diags)
        self.assertEqual(diags, [])

    def test_forged_primitive_fact_stays_inert(self):
        # S10 regression pin: a bogus record fact named `Int` must not
        # disturb Int arithmetic, and the closure gate must exempt it.
        source = b"fn f(x: Int) -> Int { return x + 1 }\n"
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                     "name": "prim-forge",
                                     "bytes": list(source)})
        self.assertEqual(target.get("outcome"), "ok", target)
        sem = {"document": target["document"],
               "revision": target["revision"], "entryFunctions": []}
        parsed = parse_target(self.session, source, target,
                              self.tool_revision)
        nodes = fields_map(parsed)["nodes"]["value"]
        index = contract.DocumentIndex.from_parsed(parsed)
        typed = lambda t, v: {"type": t,
                              "value": str(v) if t == "Int" else v}
        int_fact = {"type": "ResolvedTypeDecl", "fields": [
            {"name": "typeName", "value": typed("Str", "Int")},
            {"name": "typeKind", "value": typed("Str", "record")},
            {"name": "declStartByte", "value": typed("Int", 0)},
            {"name": "declEndByte", "value": typed("Int", 0)},
            {"name": "declLine", "value": typed("Int", 1)},
            {"name": "declColumn", "value": typed("Int", 1)},
            {"name": "duplicateType", "value": typed("Bool", False)},
            {"name": "document",
             "value": typed("Str", target["document"])},
            {"name": "revision",
             "value": typed("Str", target["revision"])},
            {"name": "fields",
             "value": {"type": "List[ResolvedTypeField]", "value": []}}]}
        bodies = {str(nval(node, "text")): index.subtree(int(nval(node, "id")))
                  for node in nodes
                  if nval(node, "kind") == "function"
                  and str(nval(node, "parentId")) == "-1"}
        sigs = fetch_all_sigs(self.session, parsed, self.tool_revision, sem)
        ext = [s for s in sigs if s["name"] != "f"]
        report = fields_map(self.invoke_typed(
            self.sliced(parsed, bodies["f"]),
            {"type": "List[CheckedFunction]",
             "value": [checked_fn_value(s) for s in ext]},
            {"type": "List[ResolvedSignature]",
             "value": [resolved_sig_value(s) for s in ext]},
            {"type": "List[ResolvedTypeDecl]", "value": [int_fact]}, sem))
        self.assertEqual(report["status"]["value"], "valid", report)


if __name__ == "__main__":
    unittest.main()
