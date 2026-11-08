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
        groups = [([1, 2], _report(calls=[_call(0)])),
                  ([3], _report(calls=[_call(0)]))]
        merged = pep_sectional.merge_reports(_sliced(), groups, [1, 2, 3],
                                             "main", [])
        fields = {f["name"]: f["value"] for f in merged["fields"]}
        self.assertEqual(fields["status"]["value"], "valid")
        got = sorted(int(e["fields"][0]["value"]["value"])
                     for e in fields["calls"]["value"])
        self.assertEqual(got, [0, 2])


if __name__ == "__main__":
    unittest.main()
