"""C23 lowering of functions and calls with more than three parameters.

Before this capability existed the emitter refused every call with four or more
arguments (``Pep C23 calls require a known target and at most three arguments``)
and every function with four or more parameters, so Lucy's real lexer
constructors (``make_token`` 8, ``make_progress`` 11, ``make_cursor`` 16) could
not be lowered at all even though their record types now emit.

These tests pin the general ordered lowering, the native Clang/GCC result against
Pep's own interpreter, and the fail-closed boundaries that must survive it.
"""

import pathlib
import subprocess
import tempfile
import unittest

from pep_c23 import emit

ROOT = pathlib.Path(__file__).resolve().parents[1]
PEP = ROOT / "pep.ps1"
CLANG = pathlib.Path(r"C:\Users\Matmus\scoop\apps\llvm\current\bin\clang.exe")
GCC = pathlib.Path(r"C:\Users\Matmus\scoop\apps\mingw\current\bin\gcc.exe")
NATIVE_AVAILABLE = CLANG.is_file() and GCC.is_file()


def scalar_program(arity):
    parameters = ", ".join(f"a{index}: Int" for index in range(arity))
    total = " + ".join(f"a{index}" for index in range(arity))
    arguments = ", ".join(str(index + 1) for index in range(arity))
    return (f"fn sum{arity}({parameters}) -> Int {{ return {total} }}\n"
            f"fn main() -> Int {{ return sum{arity}({arguments}) }}\n")


class PepC23ArityTests(unittest.TestCase):
    def invoke(self, *args):
        return subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(PEP), *map(str, args)],
            cwd=ROOT, text=True, capture_output=True, check=False)

    def run_native(self, source_text, expected):
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            directory = pathlib.Path(temp_dir)
            reference_source = directory / "reference.pep"
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            interpreted = self.invoke("run", reference_source)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, f"{expected}\n")

            generated = emit(source_text.encode("utf-8"))
            if not NATIVE_AVAILABLE:
                return generated

            c_path = directory / "generated.c"
            c_path.write_text(generated, encoding="utf-8", newline="\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name, source=source_text):
                    executable = directory / (compiler.stem + "-case.exe")
                    built = subprocess.run(
                        [str(compiler), "-std=c23", "-Wall", "-Wextra", "-Wpedantic",
                         "-Werror", "-O2", str(c_path), "-o", str(executable)],
                        cwd=ROOT, text=True, capture_output=True, check=False)
                    self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
                    ran = subprocess.run([str(executable)], cwd=ROOT, text=True,
                                         capture_output=True, check=False)
                    self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
                    self.assertEqual(ran.stdout, interpreted.stdout)
            return generated

    def assert_refused(self, source_text, pattern):
        with self.assertRaisesRegex(ValueError, pattern):
            emit(source_text.encode("utf-8"))

    # --- positive capability -------------------------------------------------

    def test_scalar_arity_ladder_runs_natively(self):
        for arity in range(3, 9):
            with self.subTest(arity=arity):
                self.run_native(scalar_program(arity), arity * (arity + 1) // 2)

    def test_every_parameter_binds_beyond_three(self):
        """The fourth and later parameters must resolve by name, not only the first three."""
        generated = self.run_native(
            "fn last_of_four(a: Int, b: Int, c: Int, d: Int) -> Int { return d }\n"
            "fn main() -> Int { return last_of_four(1, 2, 3, 42) }\n",
            42)
        self.assertEqual(generated.count("(void)pep_arg_"), 4)
        self.assertRegex(generated, r"int64_t pep_fn_\d+\(int64_t pep_arg_\d+, "
                                    r"int64_t pep_arg_\d+, int64_t pep_arg_\d+, int64_t pep_arg_\d+\);")
        self.assertIn("return pep_result", generated)

    def test_mixed_scalar_and_bool_parameters_run_natively(self):
        self.run_native(
            "fn flag(a: Int, b: Bool, c: Int, d: Bool, e: Int) -> Int {\n"
            "  return if b && d { a + c + e } else { 0 }\n"
            "}\n"
            "fn main() -> Int { return flag(1, true, 2, true, 4) }\n",
            7)

    def test_record_parameters_at_arity_four_run_natively(self):
        self.run_native(
            "type P { x: Int }\n"
            "fn spread(a: P, b: P, c: P, d: P) -> Int { return a.x + b.x + c.x + d.x }\n"
            "fn main() -> Int { return spread(P { x: 1 }, P { x: 2 }, P { x: 3 }, P { x: 4 }) }\n",
            10)

    def test_single_fallible_argument_is_allowed_at_arity_four(self):
        self.run_native(
            "fn add4(a: Int, b: Int, c: Int, d: Int) -> Int { return a + b + c + d }\n"
            "fn compute() -> Int { return 40 }\n"
            "fn main() -> Int { return add4(1, compute(), 0, 1) }\n",
            42)

    def test_one_and_two_parameter_calls_are_unchanged(self):
        self.run_native(
            "fn identity(value: Int) -> Int { return value }\n"
            "fn total(first: Int, second: Int) -> Int { return first + second }\n"
            "fn main() -> Int { return total(identity(20), 22) }\n",
            42)

    # --- fail-closed boundaries ---------------------------------------------

    def test_multiple_fallible_arguments_still_fail_closed(self):
        self.assert_refused(
            "fn add4(a: Int, b: Int, c: Int, d: Int) -> Int { return a + b + c + d }\n"
            "fn compute() -> Int { return 1 }\n"
            "fn main() -> Int { return add4(compute(), compute(), 0, 1) }\n",
            "rejects multiple fallible call arguments")

    def test_argument_count_mismatch_is_rejected_before_lowering(self):
        """Arity mismatches are a checker error, so the emitter never sees them."""
        self.assert_refused(
            "fn add4(a: Int, b: Int, c: Int, d: Int) -> Int { return a + b + c + d }\n"
            "fn main() -> Int { return add4(1, 2, 3) }\n",
            "requires a valid Pep checker report")

    def test_extra_argument_for_a_short_signature_is_rejected(self):
        self.assert_refused(
            "fn one(a: Int) -> Int { return a }\n"
            "fn main() -> Int { return one(1, 2, 3, 4) }\n",
            "requires a valid Pep checker report")

    def test_unsupported_result_type_fails_closed(self):
        self.assert_refused(
            "fn render(a: Int, b: Int, c: Int, d: Int) -> Str { return \"x\" }\n"
            "fn main() -> Int { return 0 }\n",
            "functions require supported parameters and scalar or record results")

    # --- boundary ------------------------------------------------------------

    def test_high_arity_is_bounded_by_the_checker_not_the_emitter(self):
        """Arities above the checker's reach must never fail for an arity reason.

        At this revision the Pep-written checker exhausts its fixed 100k-step
        per-invocation budget somewhere above eight parameters on this fixture,
        so the emitter is never reached for 9..16. Either outcome is acceptable
        here; refusing the program because of its arity is not.
        """
        for arity in range(9, 17):
            with self.subTest(arity=arity):
                source = scalar_program(arity)
                try:
                    emit(source.encode("utf-8"))
                except RuntimeError as error:
                    self.assertIn("PEP_RUNTIME_STEP_LIMIT", str(error))
                except ValueError as error:
                    self.fail(f"arity {arity} was refused by the emitter: {error}")


if __name__ == "__main__":
    unittest.main()
