import unittest

from tests import performance03_lab as lab


class Performance03LabTests(unittest.TestCase):
    def test_workload_metadata_is_revision_and_byte_based(self):
        row = lab.workload_metadata("unicode", b"caf\xc3\xa9\r\n")
        self.assertEqual(row["sourceBytes"], 7)
        self.assertEqual(row["crlfBytes"], 1)
        self.assertEqual(row["sourceRevision"], lab.revision(b"caf\xc3\xa9\r\n"))
        self.assertNotEqual(row["sourceSha256"], lab.revision(b"caf\xc3\xa9\r\n"))

    def test_topology_oracle_rejects_parent_role_and_duplicate_edges(self):
        valid = [
            {"id": 0, "parentId": -1, "childIndex": 0, "role": "top_level", "kind": "function", "value": "f", "span": None},
            {"id": 1, "parentId": 0, "childIndex": 0, "role": "statement", "kind": "return", "value": "", "span": None},
        ]
        lab.topology_check(valid)
        for mutation in (
            lambda rows: rows[1].update(parentId=99),
            lambda rows: rows[1].update(role="wrong_role"),
            lambda rows: rows.append(dict(rows[1], id=2)),
        ):
            candidate = [dict(row) for row in valid]
            mutation(candidate)
            with self.assertRaises(lab.PipelineError):
                lab.topology_check(candidate)

    def test_independent_ast_count_and_kind_walk(self):
        ast = [{"kind": "function", "span": {}, "parameters": [], "returnType": "Int",
                "body": [{"kind": "return", "span": {}, "value": {"kind": "int", "span": {}}}]}]
        self.assertEqual(lab.ast_count(ast), 4)
        self.assertEqual(lab.ast_kinds(ast), ["function", "return", "int"])

    def test_continuation_oracle_rejects_repeated_cursor_and_early_terminal(self):
        valid = [
            {"stage": "parser_start", "sourceOffset": 0},
            {"stage": "parser_step", "sourceOffset": 0, "inputCursorSha256": "a", "done": False},
            {"stage": "parser_step", "sourceOffset": 2, "inputCursorSha256": "b", "done": True},
        ]
        lab.validate_continuation_rows(valid)
        repeated = [dict(row) for row in valid]
        repeated[2]["inputCursorSha256"] = "a"
        with self.assertRaises(lab.PipelineError):
            lab.validate_continuation_rows(repeated)
        early = [dict(row) for row in valid]
        early[1]["done"] = True
        with self.assertRaises(lab.PipelineError):
            lab.validate_continuation_rows(early)

    def test_source_cap_is_preserved(self):
        with self.assertRaises(ValueError):
            lab.parse_source(b"x" * (lab.MAX_SOURCE_BYTES + 1))


if __name__ == "__main__":
    unittest.main()
