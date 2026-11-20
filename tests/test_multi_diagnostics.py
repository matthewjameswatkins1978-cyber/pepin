"""Unit tests for multi-error diagnostic accumulation in Pepin.
Verifies that independent type and declaration errors are collected in a single pass.
"""

import json
import subprocess
import unittest
from pathlib import Path


class TestMultiDiagnostics(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).parent.parent
        self.build_dir = self.root / "_build"
        self.build_dir.mkdir(exist_ok=True)

    def run_pep(self, *args):
        cmd = ["pwsh", "-NoProfile", "-File", str(self.root / "pep.ps1")] + list(args)
        return subprocess.run(
            cmd,
            cwd=str(self.root),
            capture_output=True,
            text=True,
        )

    def test_multi_function_errors_collected_in_one_pass(self):
        source = (
            "fn f1() -> Int {\n"
            "    return \"string\"\n"
            "}\n"
            "fn f2() -> Bool {\n"
            "    return 42\n"
            "}\n"
            "fn f3() -> Int {\n"
            "    return true\n"
            "}\n"
        )
        test_file = self.build_dir / "test_multi_fn.pep"
        test_file.write_text(source, encoding="utf-8")

        proc = self.run_pep("check", str(test_file), "--json")
        self.assertEqual(proc.returncode, 1)
        data = json.loads(proc.stdout)
        self.assertEqual(data["status"], "invalid")
        diags = data["diagnostics"]
        self.assertEqual(len(diags), 3)

        self.assertEqual(diags[0]["code"], "PEP_TYPE_MISMATCH")
        self.assertEqual(diags[0]["expectedType"], "Int")
        self.assertEqual(diags[0]["span"]["start"]["line"], 2)

        self.assertEqual(diags[1]["code"], "PEP_TYPE_MISMATCH")
        self.assertEqual(diags[1]["expectedType"], "Bool")
        self.assertEqual(diags[1]["span"]["start"]["line"], 5)

        self.assertEqual(diags[2]["code"], "PEP_TYPE_MISMATCH")
        self.assertEqual(diags[2]["expectedType"], "Int")
        self.assertEqual(diags[2]["span"]["start"]["line"], 8)

    def test_multi_statement_errors_within_same_function(self):
        source = (
            "fn bad_block() -> Int {\n"
            "    let a: Int = \"wrong\";\n"
            "    let b: Bool = 123;\n"
            "    return false;\n"
            "}\n"
        )
        test_file = self.build_dir / "test_multi_stmt.pep"
        test_file.write_text(source, encoding="utf-8")

        proc = self.run_pep("check", str(test_file), "--json")
        self.assertEqual(proc.returncode, 1)
        data = json.loads(proc.stdout)
        self.assertEqual(data["status"], "invalid")
        diags = data["diagnostics"]
        self.assertEqual(len(diags), 3)

        self.assertEqual(diags[0]["span"]["start"]["line"], 2)
        self.assertEqual(diags[1]["span"]["start"]["line"], 3)
        self.assertEqual(diags[2]["span"]["start"]["line"], 4)

    def test_multi_unknown_types_reported_together(self):
        source = (
            "fn bad_types(a: NonExistentOne, b: NonExistentTwo) -> NonExistentThree {\n"
            "    return 1\n"
            "}\n"
        )
        test_file = self.build_dir / "test_unknown_types.pep"
        test_file.write_text(source, encoding="utf-8")

        proc = self.run_pep("check", str(test_file), "--json")
        self.assertEqual(proc.returncode, 1)
        data = json.loads(proc.stdout)
        diags = data["diagnostics"]
        unknown_types = [d for d in diags if d["code"] == "PEP_UNKNOWN_TYPE"]
        self.assertGreaterEqual(len(unknown_types), 3)

    def test_human_readable_multi_error_output(self):
        source = (
            "fn err1() -> Int { return \"bad\" }\n"
            "fn err2() -> Bool { return 0 }\n"
        )
        test_file = self.build_dir / "test_human_diags.pep"
        test_file.write_text(source, encoding="utf-8")

        proc = self.run_pep("check", str(test_file))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("PEP_TYPE_MISMATCH", proc.stderr)
        # Should have at least two diagnostic lines printed to stderr
        lines = [line for line in proc.stderr.strip().splitlines() if "PEP_TYPE_MISMATCH" in line]
        self.assertEqual(len(lines), 2)


if __name__ == "__main__":
    unittest.main()
