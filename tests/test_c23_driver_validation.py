import unittest

from pep_c23 import (checker_binding_context_nodes, checker_node_context_index, emit,
                      typed, typed_record_value, validate_parser_final_outcome,
                      validate_parser_node_sequence, validate_parser_parent_links)


class PepC23ParserValidationTests(unittest.TestCase):
    def test_node_ids_must_start_at_zero(self):
        with self.assertRaisesRegex(RuntimeError, "exactly 0..n-1"):
            validate_parser_node_sequence({1, 2})

    def test_node_ids_must_be_contiguous(self):
        with self.assertRaisesRegex(RuntimeError, "exactly 0..n-1"):
            validate_parser_node_sequence({0, 2})

    def test_empty_node_sequence_is_valid(self):
        validate_parser_node_sequence(set())

    def test_parent_links_ignore_chunk_arrival_order(self):
        # Child-first chunk arrival is okay once the full tree is reconstructed.
        validate_parser_parent_links({0, 1}, [(1, 0), (0, -1)])

    def test_parent_id_must_exist(self):
        with self.assertRaisesRegex(RuntimeError, "missing parent"):
            validate_parser_parent_links({0, 1}, [(0, -1), (1, 3)])

    def test_parent_id_must_follow_checker_preorder_contract(self):
        with self.assertRaisesRegex(RuntimeError, "preorder tree contract"):
            validate_parser_parent_links({0, 1}, [(0, 1), (1, -1)])

    def test_complete_status_requires_empty_error_code(self):
        validate_parser_final_outcome("complete", "")
        with self.assertRaisesRegex(RuntimeError, "errored result complete"):
            validate_parser_final_outcome("complete", "PEP_PARSE_EXPECTED")

    def test_failed_status_requires_error_code(self):
        validate_parser_final_outcome("incomplete", "PEP_PARSE_EXPECTED")
        validate_parser_final_outcome("invalid", "PEP_UNEXPECTED_CHARACTER")
        with self.assertRaisesRegex(RuntimeError, "without an error code"):
            validate_parser_final_outcome("invalid", "")

    def test_final_status_is_closed_to_unknown_values(self):
        with self.assertRaisesRegex(RuntimeError, "unknown final status"):
            validate_parser_final_outcome("continuing", "")



class PepC23CheckerDriverTests(unittest.TestCase):
    @staticmethod
    def _node(node_id, parent_id, child_index, role, kind, text="", start=0, end=0):
        return typed_record_value("CheckerNode", [
            ("id", typed("Int", node_id)),
            ("parentId", typed("Int", parent_id)),
            ("childIndex", typed("Int", child_index)),
            ("role", typed("Str", role)),
            ("kind", typed("Str", kind)),
            ("text", typed("Str", text)),
            ("startByte", typed("Int", start)),
            ("endByte", typed("Int", end)),
        ])

    def test_binding_range_carries_ancestors_and_complete_annotation_type(self):
        nodes = [
            self._node(0, -1, -1, "", "function"),
            self._node(1, 0, 0, "statement", "let"),
            self._node(2, 1, 0, "annotation", "type_list"),
            self._node(3, 2, 0, "element", "type_named", "Point"),
            self._node(4, 1, 0, "value", "integer", "1"),
        ]
        index = checker_node_context_index(nodes)

        actual = checker_binding_context_nodes(index, 1, 2)
        actual_ids = [int({field["name"]: field["value"] for field in node["fields"]}["id"]["value"])
                      for node in actual]

        self.assertEqual(actual_ids, [0, 1, 2, 3])
        self.assertNotIn(4, actual_ids)

    def test_binding_pattern_range_carries_arm_result_context(self):
        nodes = [
            self._node(0, -1, -1, "", "function"),
            self._node(1, 0, 0, "statement", "match_arm"),
            self._node(2, 1, 0, "pattern", "constructor_pattern"),
            self._node(3, 2, 0, "argument", "binding_pattern", "value"),
            self._node(4, 1, 1, "result", "integer", "1"),
        ]
        actual = checker_binding_context_nodes(checker_node_context_index(nodes), 3, 4)
        actual_ids = [int({field["name"]: field["value"] for field in node["fields"]}["id"]["value"])
                      for node in actual]

        self.assertEqual(actual_ids, [0, 1, 2, 3, 4])


    def test_staged_checker_emits_small_program_with_fixed_budgets(self):
        measurements = {}
        c_source = emit(b"fn main() -> Int { return 0 }\n", measurements)

        self.assertIn("int main", c_source)
        self.assertEqual(measurements["checker_status"], "valid")
        self.assertEqual(measurements["emitter_status"], "emitted")
        self.assertGreater(measurements["checker_step_count"], 1)
        self.assertLess(measurements["checker_step_count"], measurements["checker_host_step_limit"])


if __name__ == "__main__":
    unittest.main()
