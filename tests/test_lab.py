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

    def test_eval_invalid_program_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = pathlib.Path(tmp) / "bad.pep"
            bad.write_text('fn broken(n: Int) -> Int { return "nope" }\n', encoding="utf-8")
            proc = lab("eval", str(bad))
            self.assertNotEqual(proc.returncode, 0)

    def test_eval_store_reports_exact_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = pathlib.Path(tmp) / "lab"
            defined = lab("define", "--store", str(store), "--source",
                          "fn triple(n: Int) -> Int { return n + n + n }\n")
            self.assertEqual(defined.returncode, 0, defined.stderr)
            prog = pathlib.Path(tmp) / "main.pep"
            prog.write_text("say(int_text(triple(14)))\n", encoding="utf-8")
            ran = lab("eval-store", "--store", str(store), "--file", str(prog))
            self.assertEqual(ran.returncode, 0, ran.stderr)
            self.assertEqual(ran.stdout, "42\n")

    def test_define_accepts_incomplete_and_export_preserves_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = pathlib.Path(tmp) / "lab"
            snippet = "fn h(n: Int) -> Int { return ?calc }\n"
            defined = lab("define", "--store", str(store), "--source", snippet)
            self.assertEqual(defined.returncode, 0, defined.stderr)
            self.assertIn("incomplete", defined.stdout)
            stored = (store / "definitions.pep").read_bytes()
            self.assertEqual(stored, snippet.encode("utf-8"))
            out = pathlib.Path(tmp) / "exported.pep"
            exported = lab("export", "--store", str(store), "--output", str(out))
            self.assertEqual(exported.returncode, 0, exported.stderr)
            body = out.read_bytes()
            self.assertTrue(body.endswith(snippet.encode("utf-8")))
            payload = json.loads(exported.stdout)
            self.assertEqual(payload["definitions"], ["h"])

    def test_duplicate_define_rejected_and_store_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = pathlib.Path(tmp) / "lab"
            snippet = "fn dup(n: Int) -> Int { return n }\n"
            first = lab("define", "--store", str(store), "--source", snippet)
            self.assertEqual(first.returncode, 0, first.stderr)
            before = (store / "definitions.pep").read_bytes()
            second = lab("define", "--store", str(store), "--source", snippet)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("PEP_DUPLICATE_FUNCTION", second.stderr)
            after = (store / "definitions.pep").read_bytes()
            self.assertEqual(before, after)

    def test_unicode_and_missing_trailing_newline(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = pathlib.Path(tmp) / "lab"
            snippet = 'fn greet() -> Str { return "h\u00e9llo \u4e16\u754c" }'
            defined = lab("define", "--store", str(store), "--source", snippet)
            self.assertEqual(defined.returncode, 0, defined.stderr)
            stored = (store / "definitions.pep").read_text(encoding="utf-8")
            self.assertTrue(stored.endswith("\n"))
            self.assertIn("h\u00e9llo \u4e16\u754c", stored)
            prog = pathlib.Path(tmp) / "main.pep"
            prog.write_text("say(greet())\n", encoding="utf-8")
            ran = lab("eval-store", "--store", str(store), "--file", str(prog))
            self.assertEqual(ran.returncode, 0, ran.stderr)
            self.assertEqual(ran.stdout, "h\u00e9llo \u4e16\u754c\n")

    def test_missing_files_report_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = str(pathlib.Path(tmp) / "absent.pep")
            checked = lab("check", missing)
            self.assertNotEqual(checked.returncode, 0)
            evaluated = lab("eval", missing)
            self.assertNotEqual(evaluated.returncode, 0)
            exported = lab("export", "--store", str(pathlib.Path(tmp) / "nostore"),
                           "--output", str(pathlib.Path(tmp) / "o.pep"))
            self.assertNotEqual(exported.returncode, 0)
            self.assertIn("error", exported.stderr)

    def test_malformed_compiler_json_rejected(self):
        sys.path.insert(0, str(ROOT))
        try:
            import pep_lab
        finally:
            sys.path.remove(str(ROOT))
        garbage = subprocess.CompletedProcess(
            args=["pep"], returncode=0, stdout="not json at all", stderr="")
        original = pep_lab._run_pep
        pep_lab._run_pep = lambda *a, **k: garbage  # noqa: E731
        try:
            with self.assertRaises(RuntimeError):
                pep_lab.cmd_describe()
            with self.assertRaises(RuntimeError):
                pep_lab.cmd_check(pathlib.Path("whatever.pep"))
        finally:
            pep_lab._run_pep = original

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
