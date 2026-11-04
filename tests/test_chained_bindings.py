"""Chained binding facts: a later statement checks valid given earlier ones.

The chunk entry point ``analyze_chunk_typed_bound`` accepts externally
supplied BindingFacts. Scope keys are source-anchored, so a binding derived
while checking one unit matches the same source construct in another, and a
long function can be covered statement by statement without re-sending its
prefix as source.

Binding ids are NOT portable: every chunk numbers its bindings from 2000000,
so pooling raw facts aliases different bindings to one id and a lookup for
``width`` can resolve to ``first``. ``BindingPool`` renumbers on admission, and
that is the difference between 14/21 and 21/21 statements on ``utf8_check``.
"""
import unittest

import pep_c23
import pep_chunk_contract as contract
from pep_c23 import parse_target
from tests import test_chunk_typed as typed_probe
from tests.chunk_helper import (checked_fn_value, fetch_all_sigs, fields_map,
                                nval, resolved_sig_value)
from tests.test_chunk_typed import host_builtins


def stamped_binding(name, owner="100000", scope="100000", visible="1346",
                    mutable=True, type_name="Int", shape_kind="builtin",
                    shape_name="Int", shape_depth="0", document="doc",
                    revision="rev", semantic="2000003", syntax="7"):
    """A well-formed BindingFact value carrying source attestation."""
    shape = {"type": "PepTypeShape", "fields": [
        {"name": "kind", "value": {"type": "Str", "value": shape_kind}},
        {"name": "name", "value": {"type": "Str", "value": shape_name}},
        {"name": "listDepth", "value": {"type": "Int", "value": shape_depth}}]}
    typed = lambda t, v: {"type": t, "value": v}
    return {"type": "BindingFact", "fields": [
        {"name": "semanticId", "value": typed("Int", semantic)},
        {"name": "syntaxId", "value": typed("Int", syntax)},
        {"name": "name", "value": typed("Str", name)},
        {"name": "ownerFunctionId", "value": typed("Int", owner)},
        {"name": "scopeId", "value": typed("Int", scope)},
        {"name": "visibleFrom", "value": typed("Int", visible)},
        {"name": "mutable", "value": typed("Bool", mutable)},
        {"name": "typeName", "value": typed("Str", type_name)},
        {"name": "typeShape", "value": shape},
        {"name": "document", "value": typed("Str", document)},
        {"name": "revision", "value": typed("Str", revision)}]}


class ChainedBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.harness = typed_probe.TypedChunkTests(
            "test_make_token_body_only_stays_valid_with_facts")
        typed_probe.TypedChunkTests.setUpClass()
        cls.session = typed_probe.TypedChunkTests.session
        cls.revision = typed_probe.TypedChunkTests.tool_revision
        cls.raw = (typed_probe.ROOT / "examples" / "pep_lexer.pep").read_bytes()
        bundle_text = "\n".join(p.read_text(encoding="utf-8")
                                for p in pep_c23.SOURCES)
        bundle = cls.session.send({"schemaVersion": 3, "op": "open",
                                   "source": bundle_text, "name": "pep-c23",
                                   "metadataOnly": True})
        cls.tool_document = bundle["document"]
        target = cls.session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": "chain", "bytes": list(cls.raw)})
        assert target.get("outcome") == "ok", target
        cls.sem = {"document": target["document"],
                   "revision": target["revision"], "entryFunctions": []}
        cls.parsed = parse_target(cls.session, cls.raw, target, cls.revision)
        cls.nodes = fields_map(cls.parsed)["nodes"]["value"]
        cls.index = contract.DocumentIndex.from_parsed(cls.parsed)
        cls.sigs = fetch_all_sigs(cls.session, cls.parsed, cls.revision, cls.sem)
        decl_roots = [int(nval(n, "id")) for n in cls.nodes
                      if str(nval(n, "parentId")) == "-1"
                      and nval(n, "kind") in ("record_declaration",
                                              "union_declaration")]
        cls.facts = []
        for root in decl_roots:
            cls.facts.extend(cls.harness.type_facts(cls.parsed, cls.sem,
                                                    cls.index.subtree(root)))
        cls.host = host_builtins(target["document"], target["revision"])
        cls.table = {str(nval(n, "text")): int(nval(n, "id")) for n in cls.nodes
                     if nval(n, "kind") == "function"
                     and str(nval(n, "parentId")) == "-1"}
        sample = cls.session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": "validate", "bytes": []})
        vector = [pep_c23.parser_progress(sample["document"], sample["revision"]),
                  {"type": "List[CheckedFunction]", "value": []},
                  {"type": "List[ResolvedSignature]", "value": []},
                  {"type": "List[ResolvedTypeDecl]", "value": []},
                  {"type": "List[BindingFact]", "value": []},
                  {"type": "Bool", "value": True}]
        cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                          "op": "tool_register", "tool": "bound-chunk",
                          "document": cls.tool_document, "revision": cls.revision,
                          "function": "analyze_chunk_typed_bound"})
        registration = cls.session.send(
            {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_validate",
             "tool": "bound-chunk", "document": cls.tool_document,
             "revision": cls.revision,
             "testVectors": [{"arguments": vector,
                              "expect": pep_c23.checker_report(
                                  sample["document"], sample["revision"]),
                              "semanticTarget": {"document": sample["document"],
                                                 "revision": sample["revision"],
                                                 "entryFunctions": []}}]})
        assert registration.get("outcome") == "ok", registration.get("error")
        cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                          "op": "tool_activate", "tool": "bound-chunk",
                          "document": cls.tool_document,
                          "revision": cls.revision})

    @classmethod
    def tearDownClass(cls):
        typed_probe.TypedChunkTests.tearDownClass()

    def statement_chunk(self, entry, position):
        for label, ids, terminal in self.index.bounded_units(
                self.table[entry],
                groups=[("one", position, position + 1, (), False)]):
            if label == "one":
                return ids, terminal
        raise AssertionError(position)

    def invoke(self, entry, chunk_ids, expect_returns, bindings):
        host_fns, host_sigs, host_types = self.host
        ext = [s for s in self.sigs if s["name"] != entry]
        allowed = self.index.fact_closure(chunk_ids, {s["name"] for s in ext})
        ext = [s for s in ext if s["name"] in allowed]
        response = self.session.send(
            {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
             "tool": "bound-chunk",
             "arguments": [
                 self.harness.sliced(self.parsed, chunk_ids),
                 {"type": "List[CheckedFunction]",
                  "value": [checked_fn_value(s) for s in ext] + host_fns},
                 {"type": "List[ResolvedSignature]",
                  "value": [resolved_sig_value(s) for s in ext] + host_sigs},
                 {"type": "List[ResolvedTypeDecl]", "value": self.facts + host_types},
                 {"type": "List[BindingFact]", "value": bindings},
                 {"type": "Bool", "value": expect_returns}],
             "semanticTarget": self.sem})
        if response.get("outcome") != "ok":
            return None, [(response.get("error") or {}).get("code")]
        report = fields_map(response["result"])
        codes = [fields_map(d)["code"]["value"]
                 for d in report["diagnostics"]["value"]]
        return report, codes

    def chain(self, entry, pool=None):
        carried = pool if pool is not None else contract.BindingPool(
            self.sem["document"], self.sem["revision"])
        statements = self.index.statement_children(self.table[entry])
        accepted, rejected = 0, []
        for position in range(len(statements)):
            chunk, terminal = self.statement_chunk(entry, position)
            report, codes = self.invoke(entry, chunk, terminal, carried.facts())
            if report is not None and report["status"]["value"] == "valid" and not codes:
                accepted += 1
                carried.add(report["bindings"]["value"])
            else:
                status = report["status"]["value"] if report else codes
                rejected.append((position, status, sorted(set(codes))[:2]))
        return accepted, len(statements), rejected

    def test_utf8_check_is_fully_covered_by_chained_units(self):
        # 21 of 21 statements check valid, against 5 without binding facts.
        accepted, total, rejected = self.chain("utf8_check")
        self.assertEqual(total, 21)
        self.assertEqual(accepted, 21, rejected)

    def test_raw_pooling_aliases_bindings_and_loses_coverage(self):
        # Every chunk numbers bindings from 2000000, so concatenating raw
        # facts without renumbering collapses distinct bindings onto one id.
        class RawPool:
            def __init__(self):
                self.items = []

            def add(self, bindings):
                self.items.extend(bindings)

            def facts(self):
                return self.items

        accepted, _total, _rejected = self.chain("utf8_check", RawPool())
        self.assertLess(accepted, 21)
        self.assertEqual(accepted, 7)

    def test_pool_renumbers_and_dedupes(self):
        pool = contract.BindingPool("doc", "rev")
        self.assertEqual(pool.add([]), 0)
        fact = stamped_binding("width", document="doc", revision="rev")
        self.assertEqual(pool.add([fact]), 1)
        self.assertEqual(pool.add([fact]), 0)  # deduped by identity
        admitted = pool.facts()[0]
        semantic = [f for f in admitted["fields"] if f["name"] == "semanticId"][0]
        self.assertEqual(semantic["value"]["value"], str(contract.BindingPool.BASE))
        stamps = {f["name"]: f["value"] for f in admitted["fields"]
                  if f["name"] in ("document", "revision")}
        self.assertEqual(stamps["document"]["value"], "doc")
        self.assertEqual(stamps["revision"]["value"], "rev")

    def test_pool_rejects_stale_foreign_and_malformed(self):
        pool = contract.BindingPool("docA", "revA")
        self.assertEqual(pool.add([stamped_binding("x", document="docA",
                                                   revision="revA")]), 1)
        # Stale revision, foreign document: fail closed, never carried.
        for bad in (stamped_binding("y", document="docA", revision="revB"),
                    stamped_binding("z", document="docB", revision="revA")):
            with self.assertRaises(ValueError, msg=bad):
                pool.add([bad])
        self.assertEqual(len(pool), 1)
        # Malformed: missing attestation, missing shape, not a mapping.
        no_stamp = stamped_binding("w")
        no_stamp["fields"] = [f for f in no_stamp["fields"]
                              if f["name"] not in ("document", "revision")]
        no_shape = stamped_binding("v")
        no_shape["fields"] = [f for f in no_shape["fields"]
                              if f["name"] != "typeShape"]
        for bad in (no_stamp, no_shape, {"type": "BindingFact"}):
            with self.assertRaises(ValueError, msg=bad):
                pool.add([bad])
        self.assertEqual(len(pool), 1)

    def test_pool_conflict_is_explicit_not_silent(self):
        pool = contract.BindingPool("doc", "rev")
        self.assertEqual(pool.add([stamped_binding("x", type_name="Int")]), 1)
        # Identical re-admission dedupes silently.
        self.assertEqual(pool.add([stamped_binding("x", type_name="Int")]), 0)
        # Same identity, different semantics: conflict, fail closed.
        for clash in (stamped_binding("x", type_name="Str"),
                      stamped_binding("x", mutable=False),
                      stamped_binding("x", shape_name="Str")):
            with self.assertRaises(ValueError, msg=clash):
                pool.add([clash])
        # A different name is a different identity, admitted normally.
        self.assertEqual(pool.add([stamped_binding("y", type_name="Str")]), 1)

    def test_pool_facts_are_isolated_copies(self):
        pool = contract.BindingPool("doc", "rev")
        pool.add([stamped_binding("x")])
        first = pool.facts()
        first[0]["fields"] = [f for f in first[0]["fields"]
                              if f["name"] != "typeName"]
        shape = [f for f in pool.facts()[0]["fields"]
                 if f["name"] == "typeName"]
        self.assertEqual(len(shape), 1, shape)
        self.assertEqual(pool.add([stamped_binding("x")]), 0)

    OLD_SOURCE = (b"fn f() -> Int {\n"
                  b"    let x: Int = 1\n"
                  b"    return x + 1\n"
                  b"}\n")
    NEW_SOURCE = (b"fn f() -> Int {\n"
                  b'    let x: Str = "a"\n'
                  b"    return x + 1\n"
                  b"}\n")

    def open_parsed(self, source, name):
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                     "name": name, "bytes": list(source)})
        self.assertEqual(target.get("outcome"), "ok", target)
        sem = {"document": target["document"],
               "revision": target["revision"], "entryFunctions": []}
        return target, sem, parse_target(self.session, source, target,
                                         self.revision)

    def whole_body(self, parsed):
        nodes = fields_map(parsed)["nodes"]["value"]
        index = contract.DocumentIndex.from_parsed(parsed)
        table = {str(nval(n, "text")): int(nval(n, "id")) for n in nodes
                 if nval(n, "kind") == "function"
                 and str(nval(n, "parentId")) == "-1"}
        return index.subtree(table["f"])

    def return_group(self, parsed):
        nodes = fields_map(parsed)["nodes"]["value"]
        index = contract.DocumentIndex.from_parsed(parsed)
        table = {str(nval(n, "text")): int(nval(n, "id")) for n in nodes
                 if nval(n, "kind") == "function"
                 and str(nval(n, "parentId")) == "-1"}
        for label, ids, terminal in index.bounded_units(
                table["f"], groups=[("ret", 1, 2, (), True)]):
            if label == "ret":
                return ids, terminal
        raise AssertionError("no return group")

    def invoke_bound_on(self, parsed, sem, chunk_ids, bindings,
                        expect_returns=True):
        nodes = fields_map(parsed)["nodes"]["value"]
        index = contract.DocumentIndex.from_parsed(parsed)
        sigs = fetch_all_sigs(self.session, parsed, self.revision, sem)
        ext = [s for s in sigs if s["name"] != "f"]
        decl_roots = [int(nval(n, "id")) for n in nodes
                      if str(nval(n, "parentId")) == "-1"
                      and nval(n, "kind") in ("record_declaration",
                                              "union_declaration")]
        facts = []
        for root in decl_roots:
            facts.extend(self.harness.type_facts(parsed, sem,
                                                 index.subtree(root)))
        response = self.session.send(
            {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
             "tool": "bound-chunk",
             "arguments": [self.harness.sliced(parsed, chunk_ids),
                           {"type": "List[CheckedFunction]",
                            "value": [checked_fn_value(s) for s in ext]},
                           {"type": "List[ResolvedSignature]",
                            "value": [resolved_sig_value(s) for s in ext]},
                           {"type": "List[ResolvedTypeDecl]", "value": facts},
                           {"type": "List[BindingFact]", "value": bindings},
                           {"type": "Bool", "value": expect_returns}],
             "semanticTarget": sem})
        if response.get("outcome") != "ok":
            return None, [(response.get("error") or {}).get("code")]
        report = fields_map(response["result"])
        codes = [fields_map(d)["code"]["value"]
                 for d in report["diagnostics"]["value"]]
        return report, codes

    def test_foreign_binding_fact_is_refused(self):
        # A3 O1c shape across documents: bindings from `let x: Int` reused
        # where the source says `let x: Str`, on a use the seed rejects.
        _, old_sem, old_parsed = self.open_parsed(self.OLD_SOURCE, "bind-old")
        _, new_sem, new_parsed = self.open_parsed(self.NEW_SOURCE, "bind-new")
        old_report, old_codes = self.invoke_bound_on(
            old_parsed, old_sem, self.whole_body(old_parsed), [], True)
        self.assertIsNotNone(old_report, old_codes)
        self.assertEqual(old_report["status"]["value"], "valid", old_codes)
        old_bindings = old_report["bindings"]["value"]
        self.assertTrue(old_bindings, "no bindings to carry")
        ret_ids, _terminal = self.return_group(new_parsed)
        # Control: the return-only group without facts is invalid, matching
        # the whole path on the Str program.
        control, _ = self.invoke_bound_on(new_parsed, new_sem, ret_ids,
                                          [], True)
        self.assertIsNotNone(control)
        self.assertEqual(control["status"]["value"], "invalid")
        # With the foreign Int fact: fail closed with PEP_STALE_REVISION.
        report, codes = self.invoke_bound_on(
            new_parsed, new_sem, ret_ids, old_bindings, True)
        self.assertIsNotNone(report, codes)
        self.assertEqual(report["status"]["value"], "invalid", codes)
        self.assertIn("PEP_STALE_REVISION", codes, codes)

    def test_stale_revision_binding_fact_is_refused(self):
        # Same document, new revision: an Int-typed edit becomes Str, and the
        # pre-edit binding must not validate the post-edit use.
        target, _sem, parsed = self.open_parsed(self.OLD_SOURCE, "bind-stale")
        old_report, old_codes = self.invoke_bound_on(
            parsed,
            {"document": target["document"], "revision": target["revision"],
             "entryFunctions": []},
            self.whole_body(parsed), [], True)
        self.assertIsNotNone(old_report, old_codes)
        self.assertEqual(old_report["status"]["value"], "valid", old_codes)
        old_bindings = old_report["bindings"]["value"]
        start = self.OLD_SOURCE.index(b"Int = 1")
        advance = self.session.send(
            {"schemaVersion": 3, "op": "apply_edit",
             "document": target["document"],
             "expected_revision": target["revision"],
             "start_byte": start, "end_byte": start + len(b"Int = 1"),
             "replacement": 'Str = "a"'})
        self.assertEqual(advance.get("outcome"), "ok", advance)
        new_revision = advance.get("revision", target["revision"])
        self.assertNotEqual(new_revision, target["revision"])
        sem2 = {"document": target["document"], "revision": new_revision,
                "entryFunctions": []}
        target2 = {"document": target["document"], "revision": new_revision}
        parsed2 = parse_target(self.session, self.NEW_SOURCE, target2,
                               self.revision)
        ret_ids, _terminal = self.return_group(parsed2)
        report, codes = self.invoke_bound_on(
            parsed2, sem2, ret_ids, old_bindings, True)
        self.assertIsNotNone(report, codes)
        self.assertEqual(report["status"]["value"], "invalid", codes)
        self.assertIn("PEP_STALE_REVISION", codes, codes)

    def test_fresh_binding_fact_preserves_seed_parity(self):
        # Honest same-revision facts keep the invalid verdict the seed gives
        # the Str program: attestation must not launder a real mismatch.
        _, new_sem, new_parsed = self.open_parsed(self.NEW_SOURCE,
                                                   "bind-fresh")
        nodes = fields_map(new_parsed)["nodes"]["value"]
        index = contract.DocumentIndex.from_parsed(new_parsed)
        table = {str(nval(n, "text")): int(nval(n, "id")) for n in nodes
                 if nval(n, "kind") == "function"
                 and str(nval(n, "parentId")) == "-1"}
        groups = {}
        for label, ids, terminal in index.bounded_units(
                table["f"], groups=[("let", 0, 1, (), False),
                                    ("ret", 1, 2, (), True)]):
            groups[label] = (ids, terminal)
        let_report, let_codes = self.invoke_bound_on(
            new_parsed, new_sem, groups["let"][0], [], False)
        self.assertIsNotNone(let_report, let_codes)
        self.assertEqual(let_report["status"]["value"], "valid", let_codes)
        fresh = let_report["bindings"]["value"]
        report, codes = self.invoke_bound_on(
            new_parsed, new_sem, groups["ret"][0], fresh, True)
        self.assertIsNotNone(report, codes)
        self.assertEqual(report["status"]["value"], "invalid", codes)
        _, _, _, whole_status, whole_diags = self.harness.check_whole(
            self.NEW_SOURCE, "bind-fresh-whole")
        self.assertEqual(whole_status, "invalid")
        self.assertEqual(sorted(codes),
                         sorted(code for code, _, _ in whole_diags))

    def test_unattested_binding_fact_cannot_validate(self):
        # A fact with no source attestation must never check valid, however
        # it reaches the tool: fail closed at the boundary or in the checker.
        _, sem, parsed = self.open_parsed(self.NEW_SOURCE, "bind-malformed")
        ret_ids, _terminal = self.return_group(parsed)
        bad = stamped_binding("x", document="doc", revision="rev")
        bad["fields"] = [f for f in bad["fields"]
                         if f["name"] not in ("document", "revision")]
        report, codes = self.invoke_bound_on(parsed, sem, ret_ids, [bad],
                                             True)
        if report is not None:
            self.assertNotEqual(report["status"]["value"], "valid", codes)
if __name__ == "__main__":
    unittest.main()
