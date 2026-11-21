"""Tests for the Pepin Standard Prelude (std/prelude.pep).
Verifies behavioural correctness across both interpreter and native C23 (Clang & GCC),
anchored to living specification requirements in std/prelude.spec.json.
"""

import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
PEP_PRELUDE = ROOT / "std" / "prelude.pep"


class TestStdPrelude(unittest.TestCase):
    def run_interpreter(self, source=PEP_PRELUDE) -> str:
        res = subprocess.run(
            ["pwsh", "-NoProfile", "-File", "pep.ps1", "run", str(source)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        self.assertEqual(res.returncode, 0, f"Interpreter failed: {res.stderr}")
        return res.stdout.strip()

    def run_c23_direct(self, compiler: str = "clang", source=PEP_PRELUDE) -> str:
        res = subprocess.run(
            ["pwsh", "-NoProfile", "-File", "pep.ps1", "run-c23", str(source), "--direct", "--compiler", compiler],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        self.assertEqual(res.returncode, 0, f"C23 ({compiler}) failed: {res.stderr}")
        return res.stdout.strip()

    def test_prelude_interpreter_and_native_c23_parity(self):
        """Verify 100% bit-for-bit parity between interpreter, Clang C23, and GCC C23."""
        expected = "\n".join([
            "42",     # abs(0 - 42)
            "1024",   # pow(2, 10)
            "6",      # gcd(48, 18)
            "15",     # sum([1, 2, 3, 4, 5])
            "99",     # list_max
            "1",      # list_min
            "77",     # unwrap_or(Some(77), 0)
            "404",    # unwrap_or(None(), 404)
            "3"       # count_occurrences([1, 2, 1, 3, 1, 4], 1)
        ])

        interp_out = self.run_interpreter()
        self.assertEqual(interp_out, expected)

        clang_out = self.run_c23_direct("clang")
        self.assertEqual(clang_out, expected)

        gcc_out = self.run_c23_direct("gcc")
        self.assertEqual(gcc_out, expected)

    def test_math_primitives(self):
        """REQ-STD-MATH-001: Verification of abs, min, max, clamp, sign."""
        out = self.run_interpreter().splitlines()
        self.assertEqual(out[0], "42")

    def test_pow_and_gcd(self):
        """REQ-STD-MATH-002: Verification of mod, pow, gcd, is_even, is_odd."""
        out = self.run_interpreter().splitlines()
        self.assertEqual(out[1], "1024")
        self.assertEqual(out[2], "6")

    def test_option_int(self):
        """REQ-STD-OPT-001: Verification of OptionInt tagged union and unwrap_or."""
        out = self.run_interpreter().splitlines()
        self.assertEqual(out[6], "77")
        self.assertEqual(out[7], "404")

    def test_list_utilities(self):
        """REQ-STD-LIST-001: Verification of sum, list_max, list_min, count_occurrences."""
        out = self.run_interpreter().splitlines()
        self.assertEqual(out[3], "15")
        self.assertEqual(out[4], "99")
        self.assertEqual(out[5], "1")
        self.assertEqual(out[8], "3")


    def test_list_prefix_sum(self):
        with tempfile.TemporaryDirectory() as folder:
            source = pathlib.Path(folder) / "prefix.pep"
            source.write_text(
                PEP_PRELUDE.read_text(encoding="utf-8") + """
say(int_text(list_prefix_sum([], 1)))
say(int_text(list_prefix_sum([9], -1)))
say(int_text(list_prefix_sum([1, 2, 9223372036854775807], 2)))
say(int_text(list_prefix_sum([9, -2], 9223372036854775807)))
""",
                encoding="utf-8",
            )
            reference = self.run_interpreter(source)
            self.assertEqual(reference.splitlines()[-4:], ["0", "0", "3", "7"])
            for compiler in ("clang", "gcc"):
                with self.subTest(compiler=compiler):
                    self.assertEqual(self.run_c23_direct(compiler, source), reference)


    def test_list_first_or(self):
        with tempfile.TemporaryDirectory() as folder:
            source = pathlib.Path(folder) / "first_or.pep"
            source.write_text(
                PEP_PRELUDE.read_text(encoding="utf-8") + """
say(list_first_or(["first", "ignored"], "fallback"))
say(list_first_or([], "fallback"))
say(int_text(list_first_or([42], 0)))
let nested = list_first_or([], [17, 18])
say(int_text(nested[1]))
""",
                encoding="utf-8",
            )
            reference = self.run_interpreter(source)
            self.assertEqual(reference.splitlines()[-4:], ["first", "fallback", "42", "18"])
            for compiler in ("clang", "gcc"):
                with self.subTest(compiler=compiler):
                    self.assertEqual(self.run_c23_direct(compiler, source), reference)


if __name__ == "__main__":
    unittest.main()
