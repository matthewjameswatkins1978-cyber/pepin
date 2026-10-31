"""Living Prompt (step 1) checks: evaluation, persistent definitions,
source export and compiler inspection via the existing seed CLI."""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
LAB = ROOT / "pep_lab.py"


def lab(*args):
    return subprocess.run(
        [sys.executable, str(LAB), *map(str, args)],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )


class PepLabTests(unittest.TestCase):
    def test_eval_runs_existing_demo(self):
        proc = lab("eval", "examples/lab_demo.pep")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # lab_demo main returns 42; `run` exits 0 on success.
        self.assertEqual(proc.returncode, 0)

    def test_compiler_inspection_reports_valid(self):
        proc = lab("check", "examples/lab_demo.pep")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload.get("status"), "valid")
        self.assertEqual(payload.get("diagnostics"), [])

    def test_describe_reports_language_identity(self):
        proc = lab("describe")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload.get("language"), "Pep")
        self.assertEqual(payload.get("schemaVersion"), 2)

    def test_define_show_export_eval_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = pathlib.Path(tmp) / "lab"
            snippet = "fn triple(n: Int) -> Int { return n + n + n }\n"
            defined = lab("define", "--store", str(store), "--source", snippet)
            self.assertEqual(defined.returncode, 0, defined.stderr)
            self.assertIn("triple", defined.stdout)

            shown = lab("show", "--store", str(store))
            self.assertEqual(shown.returncode, 0, shown.stderr)
            self.assertIn("triple", shown.stdout)

            out = pathlib.Path(tmp) / "exported.pep"
            exported = lab("export", "--store", str(store), "--output", str(out))
            self.assertEqual(exported.returncode, 0, exported.stderr)
            body = out.read_text(encoding="utf-8")
            self.assertIn("store_sha256:", body)
            self.assertIn("fn triple", body)

            prog = pathlib.Path(tmp) / "main.pep"
            prog.write_text("say(int_text(triple(14)))\n", encoding="utf-8")
            ran = lab("eval-store", "--store", str(store), "--file", str(prog))
            self.assertEqual(ran.returncode, 0, ran.stderr)
            self.assertIn("42", ran.stdout)

    def test_define_rejects_invalid_snippet(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = pathlib.Path(tmp) / "lab"
            bad = lab("define", "--store", str(store), "--source",
                      'fn broken(n: Int) -> Int { return "nope" }\n')
            self.assertNotEqual(bad.returncode, 0)
            shown = lab("show", "--store", str(store))
            self.assertEqual(shown.returncode, 0, shown.stderr)
            self.assertNotIn("broken", shown.stdout)


if __name__ == "__main__":
    unittest.main()
