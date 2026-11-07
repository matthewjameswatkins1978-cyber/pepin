"""Native `say(...)` lowering: positives under Clang and GCC, backend refusals, and an honest
seed comparison.

Three facts pin the contract:

* `say` at direct function-body level lowers to an inlined byte-exact print helper -- no C string
  is assumed, so embedded NULs print (the runtime is length-driven, like the seed's say).
* Backend-specific refusals are ValueError diagnostics from the emitter itself, on programs the
  CHECKER accepted (say with a non-Str value position, a non-say expression statement, say inside
  a loop body -- those bodies keep their own statement whitelists).
* ENTRY-POINT MISMATCH, stated not hidden: the seed executes top-level statements and ignores
  `fn main`, while the emitter requires `fn main() -> Int` and echoes its return value as a final
  line. Parity is therefore asserted between native output and the seed running the SAME say
  calls at top level, with the return echo accounted for explicitly -- never same-file.
"""

import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pep_c23  # noqa: E402

SEED_EXE = ROOT / "_build" / "ocaml" / "pep.exe"


def emit_c(source):
    """Full pipeline (parse -> check -> emit). Raises ValueError with the emitter diagnostic."""
    return pep_c23.emit(source.encode("utf-8"))


def normalize(raw):
    """Both the seed (OCaml CRT) and the native CRT translate LF to CRLF on this host; compare
    semantic bytes after folding that translation on both sides."""
    return raw.replace(b"\r\n", b"\n")


def build_and_run(compiler_name, c_source, stem):
    """Compile with the CLI's exact strict flags and run the executable."""
    compiler = pep_c23.compiler_path(compiler_name)
    c_path = ROOT / "_build" / f"{stem}.c"
    exe_path = ROOT / "_build" / f"{stem}.exe"
    c_path.write_text(c_source, encoding="utf-8", newline="\n")
    built = subprocess.run([str(compiler), "-std=c23", "-Wall", "-Wextra", "-Wpedantic",
                            "-Werror", "-O2", str(c_path), "-o", str(exe_path)],
                           capture_output=True, text=True, check=False)
    if built.returncode:
        raise AssertionError(f"{compiler_name} strict build failed: {built.stderr[:800]}")
    ran = subprocess.run([str(exe_path)], capture_output=True, check=False)
    return ran.stdout, ran.returncode


def seed_run(source, stem):
    """Run the OCaml seed on an equivalent top-level file; return raw stdout bytes."""
    if not SEED_EXE.exists():
        subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                        "-File", str(ROOT / "pep.ps1"), "describe"],
                       capture_output=True, check=True, timeout=300)
    path = ROOT / "_build" / f"{stem}.pep"
    path.write_text(source, encoding="utf-8", newline="\n")
    ran = subprocess.run([str(SEED_EXE), "run", str(path)], capture_output=True, check=False)
    if ran.returncode:
        raise AssertionError(f"seed run failed: {ran.stderr.decode('utf-8', 'replace')[:400]}")
    return ran.stdout


class SayNativeTests(unittest.TestCase):
    def test_say_literal_matches_the_seed_surface_on_both_compilers(self):
        native_source = 'fn main() -> Int {\n  say("hi")\n  return 0\n}\n'
        seed_source = 'say("hi");'
        c_source = emit_c(native_source)
        self.assertIn("pep_say", c_source)
        seed_bytes = normalize(seed_run(seed_source, "say_seed_literal"))
        for compiler in ("clang", "gcc"):
            with self.subTest(compiler=compiler):
                stdout, exit_code = build_and_run(compiler, c_source, f"say_literal_{compiler}")
                self.assertEqual(exit_code, 0)
                self.assertEqual(normalize(stdout), seed_bytes + b"0\n",
                                 "seed say surface, then the emitter's return-value echo line")

    def test_say_escapes_and_embedded_nul_match_the_seed(self):
        """`fputc` per byte, not a C string: the NUL escape must survive to stdout."""
        body = 'say("a\\n\\t\\\\\\"\\0b")\n  return 7'
        native_source = "fn main() -> Int {\n  " + body + "\n}\n"
        seed_source = 'say("a\\n\\t\\\\\\"\\0b");'
        c_source = emit_c(native_source)
        seed_bytes = normalize(seed_run(seed_source, "say_seed_escapes"))
        self.assertIn(b"\x00", seed_bytes, "seed really printed a NUL byte")
        for compiler in ("clang", "gcc"):
            with self.subTest(compiler=compiler):
                stdout, exit_code = build_and_run(compiler, c_source, f"say_esc_{compiler}")
                self.assertEqual(exit_code, 0)
                self.assertEqual(normalize(stdout), seed_bytes + b"7\n")

    def test_say_of_str_parameter_and_immutable_local(self):
        native_source = ('fn shout(text: Str) -> Int {\n  say(text)\n  return 0\n}\n'
                         'fn main() -> Int {\n  let local = "loc"\n  say(local)\n'
                         '  return shout("par")\n}\n')
        seed_source = ('fn shout(text: Str) -> Int {\n  say(text)\n  return 0\n}\n'
                       'let local = "loc"\n'
                       'say(local);\n'
                       'shout("par");\n')
        c_source = emit_c(native_source)
        seed_bytes = normalize(seed_run(seed_source, "say_seed_param"))
        for compiler in ("clang", "gcc"):
            with self.subTest(compiler=compiler):
                stdout, exit_code = build_and_run(compiler, c_source, f"say_param_{compiler}")
                self.assertEqual(exit_code, 0)
                self.assertEqual(normalize(stdout), seed_bytes + b"0\n")

    def test_helper_is_unconditionally_placed_but_uploads_nothing_without_say(self):
        """Placement decision, measured: ANY conditional detection (node scan, even text-first)
        costs more than the one-shot emit_c23 budget leaves on the depth-510 recursion fixture,
        which regressed by hundreds of ticks; an unconditional [[maybe_unused]] helper costs
        ~constant. Programs without say keep byte-identical RUNTIME output -- only the fixed,
        unused helper block is added to their generated C."""
        c_source = emit_c("fn main() -> Int {\n  return 42\n}\n")
        self.assertIn("[[maybe_unused]] static void pep_say", c_source)
        self.assertIn("pep_str_equal", c_source, "ordinary preamble still present")
        stdout, exit_code = build_and_run("clang", c_source, "say_absent_unused")
        self.assertEqual(exit_code, 0)
        self.assertEqual(normalize(stdout), b"42\n", "runtime output unchanged without say")


class SayBackendRefusalTests(unittest.TestCase):
    def test_say_int_text_builtin_emits_in_value_position(self):
        """SUPERSEDED refusal pin (A2 int channel @7335114): say(int_text(42)) used to be a
        pinned emitter bound; it now lowers natively like str_concat. Pins the emission."""
        c_source = emit_c('fn main() -> Int {\n say(int_text(42))\n return 0\n}\n')
        self.assertIn("pep_int_text(", c_source)
        self.assertIn("pep_say(", c_source)
    def test_non_say_expression_statement_refuses(self):
        with self.assertRaises(ValueError) as caught:
            emit_c("fn main() -> Int {\n  42 + 1\n  return 0\n}\n")
        self.assertIn("Pep C23 expression statements currently support only say(...)",
                      str(caught.exception))

    def test_say_inside_a_while_body_emits_per_iteration(self):
        """SUPERSEDED v1 boundary (A2 emit-loop idiom @445a152): say inside a while body now
        lowers per iteration; pins the emission instead of the old whitelist refusal."""
        c_source = emit_c('fn main() -> Int {\n var i = 0\n while i <= 1 {\n say("x")\n i = i + 1\n }\n return i\n}\n')
        self.assertIn("pep_say(", c_source)


if __name__ == "__main__":
    unittest.main()