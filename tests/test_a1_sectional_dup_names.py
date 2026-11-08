"""A1 R3 follow-up: duplicate top-level function names refused host-side.

The seed refuses whole-file duplicates (PEP_DUPLICATE_FUNCTION, pinned by
A4's a_dup fixture), but the sectional path checks each slice alone — so
the host must refuse the shadow before any dict keying by function name.
Pure-function tests over the helper; no session needed.
"""
import unittest

import pep_sectional


def _node(kind, parent, text):
    return {"fields": [
        {"name": "kind", "value": {"value": kind}},
        {"name": "parentId", "value": {"value": parent}},
        {"name": "text", "value": {"value": text}}]}


class DupNamesTest(unittest.TestCase):
    def test_unique_names_pass(self):
        nodes = [_node("function", "-1", "main"),
                 _node("function", "-1", "foo"),
                 _node("return", "3", "")]
        self.assertEqual(pep_sectional._duplicate_top_level_functions(nodes), [])

    def test_duplicate_main_found(self):
        nodes = [_node("function", "-1", "main"),
                 _node("function", "-1", "foo"),
                 _node("function", "-1", "main")]
        self.assertEqual(
            pep_sectional._duplicate_top_level_functions(nodes), ["main"])

    def test_nested_same_name_ignored(self):
        nodes = [_node("function", "-1", "main"),
                 _node("function", "9", "main")]
        self.assertEqual(pep_sectional._duplicate_top_level_functions(nodes), [])

    def test_check_program_dup_path_shape(self):
        # A3-082 note 1: the refusal dict carries sigs=[] (never None)
        # and the seed code, with no session use on this path.
        nodes = [_node("function", "-1", "main"),
                 _node("function", "-1", "main")]
        parsed = {"fields": [
            {"name": "nodes",
             "value": {"type": "List[FlatAstNode]", "value": nodes}}]}
        out = pep_sectional.check_program(None, None, parsed, None, None,
                                          None)
        self.assertEqual(out["failures"],
                         [("main", "duplicate-function",
                           ["PEP_DUPLICATE_FUNCTION"])])
        self.assertEqual(out["sigs"], [])

    def test_non_function_kinds_ignored(self):
        nodes = [_node("record", "-1", "P"),
                 _node("record", "-1", "P")]
        self.assertEqual(pep_sectional._duplicate_top_level_functions(nodes), [])


if __name__ == "__main__":
    unittest.main()
