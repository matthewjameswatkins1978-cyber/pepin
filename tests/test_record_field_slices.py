import unittest
import pep_record_slices


class RecordFieldSliceContractTests(unittest.TestCase):
    def test_a4_mc_seam_slices_satisfy_the_contract(self):
        result = pep_record_slices.validate_field_slices([
            "tests/fixtures/mc_seam_slice_0_7.json",
            "tests/fixtures/mc_seam_slice_8_15.json",
        ])
        self.assertTrue(result["valid"])
        self.assertEqual(result["recordType"], "LexCursor")
        self.assertEqual(result["fieldCount"], 16)
        self.assertEqual(result["slices"][0].startswith("mc_seam_slice_0_7"), True)

    def test_overlap_is_refused(self):
        s = pep_record_slices.validate_field_slices
        import json, pathlib, tempfile
        a = json.loads(pathlib.Path("tests/fixtures/mc_seam_slice_0_7.json").read_text())
        # overlapping fieldIds must fail tiling
        bad = dict(a)
        bad["fieldIds"] = [0, 1, 2, 3, 4, 5, 6, 8]
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as fh:
            json.dump(bad, fh)
            bad_path = fh.name
        with self.assertRaises(AssertionError):
            s([bad_path, "tests/fixtures/mc_seam_slice_8_15.json"])


if __name__ == "__main__":
    unittest.main()
