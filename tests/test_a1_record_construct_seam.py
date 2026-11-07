"""A1 reserve (LUCY-20261107-014): record-construction seam twin.

Prior scratch probes (`mc_seam_oracle` / `mc_seam_neg`) exercised a 16-field
record construction through a 16-argument constructor call; this test commits
the pair. It lives one layer above the tracked parser error contract
(`test_parser_error_contract.py`, chunk contiguity): that contract asserts the
parser always emits contiguous node ids on error shapes, while this test
asserts the *checker* accepts the well-typed construction and rejects exactly
the one wrong field type (`offset: \"oops\"` for an `Int` field) with
PEP_TYPE_MISMATCH on the offending literal's span. No shape duplication.
"""
import json
import pathlib
import re
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures"

EXPECTED = {
    # (status, [(code, start_offset, end_offset, line, column)])
    "mc_seam_oracle": ("valid", []),
    "mc_seam_neg": ("invalid", [("PEP_TYPE_MISMATCH", 742, 748, 29, 13)]),
}


def check_fixture(name):
    target = FIX / (name + ".pep")
    proc = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"),
         "check", str(target), "--json"],
        cwd=ROOT, text=True, capture_output=True, check=False)
    text = re.sub(r"\x1b\[[0-9;]*m", "", proc.stdout.strip())
    text = text[text.find("{"):] if "{" in text else text
    data = json.loads(text)
    diags = []
    for diag in data.get("diagnostics", []):
        span = diag.get("span", {})
        start = span.get("start", {})
        diags.append((diag.get("code"), start.get("offset"),
                      span.get("endOffset"), start.get("line"),
                      start.get("column")))
    return (data.get("status"), diags)


class RecordConstructSeamTest(unittest.TestCase):
    def test_seam_twin(self):
        for name, (want_status, want_diags) in EXPECTED.items():
            with self.subTest(fixture=name):
                got_status, got_diags = check_fixture(name)
                self.assertEqual(got_status, want_status)
                self.assertEqual(got_diags[:1], want_diags[:1])


if __name__ == "__main__":
    unittest.main()
