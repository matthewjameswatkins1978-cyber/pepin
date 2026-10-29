import unittest

from pep_c23 import (validate_parser_final_outcome, validate_parser_node_sequence,
                      validate_parser_parent_links)


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


if __name__ == "__main__":
    unittest.main()
