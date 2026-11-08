"""A1 R3: sectional merge refuses corrupted identity (no session needed).

merge_reports is a pure host function. These negatives pin its fail-closed
channel: stale revisions, foreign documents, empty group lists, holes, and
out-of-span facts all raise ValueError — never silent adoption, never a
bare KeyError. Valid merges still pass through unchanged.
"""
import unittest

import pep_sectional


def _field(ftype, value):
    return {"type": ftype, "value": value}


def _report(doc="doc1", rev="7", holes=None, calls=None, etypes=None):
    return {
        "document": _field("Str", doc),
        "revision": _field("Int", rev),
        "holes": _field("List[HoleFact]", holes or []),
        "functions": _field("List[CheckedFunction]", []),
        "calls": _field("List[ResolvedCall]", calls or []),
        "expressionTypes": _field("List[ExpressionTypeFact]", etypes or []),
    }


def _call(syntax_id):
    return {"fields": [
        {"name": "syntaxId",
         "value": {"type": "Int", "value": str(syntax_id)}}]}


def _call2(caller_id, callee_id, syntax_id):
    return {"fields": [
        {"name": "callerId",
         "value": {"type": "Int", "value": str(caller_id)}},
        {"name": "calleeId",
         "value": {"type": "Int", "value": str(callee_id)}},
        {"name": "syntaxId",
         "value": {"type": "Int", "value": str(syntax_id)}}]}


def _bind(syntax_id, name="x"):
    return {"fields": [
        {"name": "name", "value": {"type": "Str", "value": name}},
        {"name": "syntaxId",
         "value": {"type": "Int", "value": str(syntax_id)}}]}


def _fn(name, semantic_id):
    return {"fields": [
        {"name": "name", "value": {"type": "Str", "value": name}},
        {"name": "semanticId",
         "value": {"type": "Int", "value": str(semantic_id)}}]}


def _sliced():
    return {"type": "ParserProgress", "fields": [
        {"name": "nodes",
         "value": {"type": "List[FlatAstNode]", "value": []}}]}


class MergeNegativesTest(unittest.TestCase):
    def test_stale_revision_refused(self):
        groups = [([1, 2], _report(rev="7")), ([3, 4], _report(rev="8"))]
        with self.assertRaisesRegex(ValueError, "stale revision"):
            pep_sectional.merge_reports(_sliced(), groups, [1, 2, 3, 4],
                                        "main", [])

    def test_foreign_document_refused(self):
        groups = [([1, 2], _report(doc="doc1")), ([3, 4], _report(doc="docX"))]
        with self.assertRaisesRegex(ValueError, "foreign document"):
            pep_sectional.merge_reports(_sliced(), groups, [1, 2, 3, 4],
                                        "main", [])

    def test_empty_groups_refused(self):
        with self.assertRaisesRegex(ValueError, "empty group list"):
            pep_sectional.merge_reports(_sliced(), [], [], "main", [])

    def test_hole_still_refused(self):
        groups = [([1], _report(holes=[{"hole": True}]))]
        with self.assertRaisesRegex(ValueError, "hole"):
            pep_sectional.merge_reports(_sliced(), groups, [1], "main", [])

    def test_out_of_span_fact_refused_as_value_error(self):
        groups = [([5], _report(calls=[_call(99)]))]
        with self.assertRaisesRegex(ValueError, "outside slice span"):
            pep_sectional.merge_reports(_sliced(), groups, [5], "main", [])

    def test_valid_merge_passes_through(self):
        rep1 = _report(calls=[_call2(100000, 100000, 0)])
        rep1["functions"]["value"].append(_fn("main", 100000))
        rep2 = _report(calls=[_call2(100000, 100000, 0)])
        rep2["functions"]["value"].append(_fn("main", 100000))
        groups = [([1, 2], rep1), ([3], rep2)]
        merged = pep_sectional.merge_reports(_sliced(), groups, [1, 2, 3],
                                             "main", [])
        fields = {f["name"]: f["value"] for f in merged["fields"]}
        self.assertEqual(fields["status"]["value"], "valid")
        def _syn(e):
            for f in e["fields"]:
                if f["name"] == "syntaxId":
                    return int(f["value"]["value"])
            raise AssertionError("call without syntaxId")
        got = sorted(_syn(e) for e in fields["calls"]["value"])
        self.assertEqual(got, [0, 2])

    # A3-080 identity channels (all latent-not-live through the driver;
    # each must refuse rather than adopt or mis-attribute).
    def test_entry_disagreement_refused(self):
        groups = [([1], _report()), ([2], _report())]
        groups[0][1]["functions"]["value"].append(_fn("main", 100000))
        groups[1][1]["functions"]["value"].append(_fn("main", 100001))
        with self.assertRaisesRegex(ValueError, "entry fact disagreement"):
            pep_sectional.merge_reports(_sliced(), groups, [1, 2],
                                        "main", [])

    def test_duplicate_group_ids_refused(self):
        groups = [([3, 3], _report())]
        with self.assertRaisesRegex(ValueError, "ascending-unique"):
            pep_sectional.merge_reports(_sliced(), groups, [3],
                                        "main", [])

    def test_unsorted_group_ids_refused(self):
        groups = [([4, 2], _report())]
        with self.assertRaisesRegex(ValueError, "ascending-unique"):
            pep_sectional.merge_reports(_sliced(), groups, [2, 4],
                                        "main", [])

    def test_dangling_callee_refused(self):
        rep = _report(calls=[_call2(100000, 424242, 0)])
        rep["functions"]["value"].append(_fn("main", 100000))
        groups = [([5], rep)]
        with self.assertRaisesRegex(ValueError, "unknown function fact"):
            pep_sectional.merge_reports(_sliced(), groups, [5],
                                        "main", [])

    def test_anchored_call_passes(self):
        rep = _report(calls=[_call2(100000, 100000, 0)])
        rep["functions"]["value"].append(_fn("main", 100000))
        groups = [([5], rep)]
        merged = pep_sectional.merge_reports(_sliced(), groups, [5],
                                             "main", [])
        fields = {f["name"]: f["value"] for f in merged["fields"]}
        self.assertEqual(fields["status"]["value"], "valid")

    def test_carried_bindings_pass_through(self):
        rep = _report()
        rep["functions"]["value"].append(_fn("main", 100000))
        groups = [([5], rep)]
        merged = pep_sectional.merge_reports(
            _sliced(), groups, [5], "main", [],
            bindings=[_bind(0)])
        fields = {f["name"]: f["value"] for f in merged["fields"]}
        got = [(e["fields"][0]["value"]["value"],
                e["fields"][1]["value"]["value"])
               for e in fields["bindings"]["value"]]
        self.assertEqual(got, [("x", "0")])
        self.assertEqual(fields["status"]["value"], "valid")

    def test_out_of_span_binding_refused(self):
        rep = _report()
        rep["functions"]["value"].append(_fn("main", 100000))
        groups = [([5], rep)]
        with self.assertRaisesRegex(ValueError, "outside slice span"):
            pep_sectional.merge_reports(
                _sliced(), groups, [5], "main", [],
                bindings=[_bind(99)])


def _pbind(name, syntax_id, doc="doc-1", rev="7"):
    return {"fields": [
        {"name": "name", "value": {"type": "Str", "value": name}},
        {"name": "syntaxId",
         "value": {"type": "Int", "value": str(syntax_id)}},
        {"name": "semanticId", "value": {"type": "Int", "value": "2000000"}},
        {"name": "ownerFunctionId", "value": {"type": "Str", "value": "main"}},
        {"name": "scopeId", "value": {"type": "Str", "value": "100000"}},
        {"name": "visibleFrom", "value": {"type": "Int", "value": "0"}},
        {"name": "mutable", "value": {"type": "Bool", "value": True}},
        {"name": "typeName", "value": {"type": "Str", "value": "Int"}},
        {"name": "typeShape",
         "value": {"type": "PepTypeShape", "value": {"kind": "", "name": "", "listDepth": 0}}},
        {"name": "document", "value": {"type": "Str", "value": doc}},
        {"name": "revision", "value": {"type": "Str", "value": rev}}]}


class CarryBindingTest(unittest.TestCase):
    def _pool(self):
        import pep_chunk_contract as contract
        return contract.BindingPool("doc-1", "7")

    def test_new_binding_translated_and_pooled(self):
        pool = self._pool()
        pep_sectional._carry_binding(pool, _pbind("x", 2), {"2": "9"})
        self.assertEqual(len(pool.facts()), 1)
        got = {f["name"]: f["value"] for f in pool.facts()[0]["fields"]}
        self.assertEqual(got["syntaxId"]["value"], "9")

    def test_echo_accepted_without_retranslation(self):
        pool = self._pool()
        pep_sectional._carry_binding(pool, _pbind("x", 2), {"2": "9"})
        echo = _pbind("x", 9)
        pep_sectional._carry_binding(pool, echo, {"0": "0", "1": "1"})
        self.assertEqual(len(pool.facts()), 1)

    def test_conflicting_echo_refused(self):
        pool = self._pool()
        pep_sectional._carry_binding(pool, _pbind("x", 2), {"2": "9"})
        bad = _pbind("x", 9)
        for f in bad["fields"]:
            if f["name"] == "typeName":
                f["value"] = {"type": "Str", "value": "Bool"}
        with self.assertRaisesRegex(ValueError, "conflicting carried"):
            pep_sectional._carry_binding(pool, bad, {})

    def test_out_of_span_new_binding_refused(self):
        pool = self._pool()
        with self.assertRaisesRegex(ValueError, "outside slice span"):
            pep_sectional._carry_binding(pool, _pbind("x", 5), {"2": "9"})


if __name__ == "__main__":
    unittest.main()
