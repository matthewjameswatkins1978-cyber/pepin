"""str_concat builtin: typing, arity, reservation and runtime concatenation.

Covers the minimal host builtin added for CD3 diagnostic-message parity
(chunked checker must compose seed-exact "Unknown type '<name>'" text;
Pep has no other Str composition). Interpreter-only: the C23 emitter
does not lower Str, mirroring the str_contains precedent.
"""
import json
import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BUILD = ROOT / "_build" / "str-concat-tests"
PEP = ROOT / "pep.ps1"


def invoke(*args):
    return subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(PEP), *map(str, args)],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )


def check_source(source):
    BUILD.mkdir(parents=True, exist_ok=True)
    path = BUILD / "case.pep"
    path.write_text(source, encoding="utf-8", newline="")
    result = invoke("check", path, "--json")
    return result, json.loads(result.stdout)


def run_source(source):
    BUILD.mkdir(parents=True, exist_ok=True)
    path = BUILD / "run.pep"
    path.write_text(source, encoding="utf-8", newline="")
    return invoke("run", path)


class StrConcatTests(unittest.TestCase):
    def test_concat_types_as_str_to_str(self):
        _, report = check_source(
            'fn shout(name: Str) -> Str { return str_concat(str_concat("hi ", name), "!") }\n'
            'fn main() -> Str { return shout("Bo") }\n')
        self.assertEqual(report.get("status"), "valid", report)
        self.assertEqual(report.get("diagnostics"), [], report)

    def test_concat_empty_and_multibyte(self):
        _, report = check_source(
            'fn main() -> Str { return str_concat(str_concat("", "caf\xc3\xa9"), "") }\n')
        self.assertEqual(report.get("status"), "valid", report)

    def test_concat_arity_is_two(self):
        for source in ('fn main() -> Str { return str_concat("a") }\n',
                       'fn main() -> Str { return str_concat("a", "b", "c") }\n'):
            _, report = check_source(source)
            self.assertEqual(report.get("status"), "invalid", report)
            codes = [item["code"] for item in report.get("diagnostics", [])]
            self.assertIn("PEP_ARGUMENT_COUNT", codes, report)

    def test_concat_argument_types_are_str(self):
        # Seed-checked programs report the expected-Str mismatch as
        # PEP_TYPE_MISMATCH; the Pep checker's chunked path reports the
        # same shape as PEP_ARGUMENT_TYPE via fixed_builtin_parameter_type.
        _, report = check_source(
            'fn main() -> Str { return str_concat(1, "b") }\n')
        self.assertEqual(report.get("status"), "invalid", report)
        codes = [item["code"] for item in report.get("diagnostics", [])]
        self.assertIn("PEP_TYPE_MISMATCH", codes, report)

    def test_concat_name_is_reserved(self):
        _, report = check_source(
            'fn str_concat(a: Str, b: Str) -> Str { return a }\n'
            'fn main() -> Str { return str_concat("a", "b") }\n')
        self.assertEqual(report.get("status"), "invalid", report)
        codes = [item["code"] for item in report.get("diagnostics", [])]
        self.assertIn("PEP_RESERVED_FUNCTION", codes, report)

    def test_concat_runs_with_exact_bytes(self):
        # run executes top-level statements (fn main is not auto-invoked).
        result = run_source(
            'say(str_concat("ab", "cd"))\n'
            'say(str_concat("", "caf\u00e9"))\n'
            'say(str_concat(str_concat("a", ""), ""))\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["abcd", "caf\u00e9", "a"])


if __name__ == "__main__":
    unittest.main()
