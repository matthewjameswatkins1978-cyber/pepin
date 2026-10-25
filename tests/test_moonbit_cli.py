import pathlib
import json
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PEP = ROOT / "pep-moonbit.ps1"


def invoke(*args):
    return subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(PEP), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class PepCliTests(unittest.TestCase):
    def source(self, content):
        temp = tempfile.NamedTemporaryFile("wb", suffix=".pep", delete=False)
        temp.write(content)
        temp.close()
        self.addCleanup(pathlib.Path(temp.name).unlink, missing_ok=True)
        return pathlib.Path(temp.name)

    def test_hello_compiles_and_runs_exact_output(self):
        result = invoke("run", "examples/hello.pep")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "Hello, Pep!\n")

    def test_lf_and_crlf_are_equivalent(self):
        outputs = []
        for line_ending in (b"\n", b"\r\n"):
            path = self.source(b'say("line one")' + line_ending + b'say("line two")')
            result = invoke("run", path)
            self.assertEqual(result.returncode, 0, result.stderr)
            outputs.append(result.stdout)
        self.assertEqual(outputs, ["line one\nline two\n"] * 2)

    def test_escaped_string(self):
        path = self.source(b'say("quote: \\" slash: \\\\ tab: \\t")')
        result = invoke("run", path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'quote: " slash: \\ tab: \t\n')

    def test_unicode_is_preserved_as_utf8(self):
        path = self.source('say("café 🍣")'.encode("utf-8"))
        result = invoke("run", path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "café 🍣\n")

    def test_syntax_error_has_structured_diagnostic_and_nonzero_status(self):
        result = invoke("check", "--json", self.source(b'say("unfinished"'))
        self.assertEqual(result.returncode, 1)
        diagnostic = json.loads(result.stdout)["diagnostics"][0]
        self.assertEqual(diagnostic["code"], "PARSE001")
        self.assertEqual(diagnostic["severity"], "error")
        self.assertEqual(diagnostic["line"], 1)
        self.assertGreater(diagnostic["column"], 0)

    def test_invalid_escape_is_rejected(self):
        result = invoke("check", "--json", self.source(b'say("bad\\q")'))
        self.assertEqual(result.returncode, 1)
        diagnostic = json.loads(result.stdout)["diagnostics"][0]
        self.assertEqual(diagnostic["code"], "LEX003")
        self.assertEqual(diagnostic["message"], "Unsupported string escape")

    def test_unterminated_string_is_reported(self):
        result = invoke("check", "--json", self.source(b'say("unfinished)'))
        self.assertEqual(result.returncode, 1)
        self.assertIn('"code":"LEX002"', result.stdout)

    def test_unsupported_construct_is_reported(self):
        result = invoke("check", "--json", self.source(b'print("no")'))
        self.assertEqual(result.returncode, 1)
        self.assertIn('"code":"SEM001"', result.stdout)

    def test_generated_c_is_deterministic(self):
        path = self.source(b'say("same")')
        first = invoke("build", path)
        self.assertEqual(first.returncode, 0, first.stderr)
        c_path = ROOT / "_build" / "pep" / (path.stem + ".c")
        first_c = c_path.read_bytes()
        second = invoke("build", path)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(c_path.read_bytes(), first_c)

    def test_command_exit_codes(self):
        self.assertNotEqual(invoke("nonsense").returncode, 0)
        self.assertEqual(invoke("check", "examples/hello.pep").returncode, 0)
        self.assertNotEqual(invoke("check", "--json", self.source(b'@')).returncode, 0)

    def test_describe_reports_only_implemented_features(self):
        result = invoke("describe", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"languageVersion":"0.2"', result.stdout)
        self.assertIn('"say_builtin"', result.stdout)
        self.assertNotIn('"functions"', result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
