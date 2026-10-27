import json
import unittest

from tests import integration01_lab as lab


class Integration01LabTests(unittest.TestCase):
    def test_manifest_keeps_accepted_and_unaccepted_stages_distinct(self):
        manifest = lab.validate_manifest()
        self.assertEqual(manifest["limits"]["sourceBytes"], 65536)
        a12 = next(entry for entry in manifest["inputs"] if entry["name"] == "A12 parser")
        self.assertEqual(a12["sha"], "69a47fe77187666bdd045b8dc8a9f633a7dd49d7")
        a13 = next(entry for entry in manifest["inputs"] if entry["name"] == "A13 checker")
        self.assertIsNone(a13["sha"])

    def test_manifest_rejects_a13_promotion(self):
        manifest = lab.load_manifest()
        mutated = json.loads(json.dumps(manifest))
        a13 = next(entry for entry in mutated["inputs"] if entry["name"] == "A13 checker")
        a13["status"] = "accepted"
        with self.assertRaises(lab.IntegrationError):
            lab.validate_manifest(mutated)

    def test_matrix_has_independent_expected_outcomes(self):
        matrix = lab.validate_matrix()
        self.assertGreaterEqual(len(matrix["cases"]), 14)
        self.assertIn("subprocess exit alone is never success", matrix["oracleRule"])

    def test_matrix_rejects_duplicate_case_ids(self):
        matrix = lab.load_matrix()
        mutated = json.loads(json.dumps(matrix))
        mutated["cases"].append(mutated["cases"][0])
        with self.assertRaises(lab.IntegrationError):
            lab.validate_matrix(mutated)

    def test_span_check_rejects_out_of_source_bounds(self):
        with self.assertRaises(lab.IntegrationError):
            lab._span_check([{"span": {"start": 0, "end": 9}}], 8)

    def test_first_native_slice_remains_planned_only(self):
        manifest = lab.load_manifest()
        self.assertEqual(manifest["firstVerticalSlice"]["status"], "planned-not-implemented")
        self.assertIn("stable semantic IDs", manifest["firstVerticalSlice"]["requiredA13Facts"])


if __name__ == "__main__":
    unittest.main()
