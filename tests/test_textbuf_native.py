"""Agent-4 slice 1: native text/byte-builder foundation checks.

Builds the standalone demo with Clang (primary) and GCC (cross-check),
runs both, and verifies identical generated text. Also verifies the Pep
capacity model through the interpreter and the Pep-written C23 emitter.
"""
import pathlib
import shutil
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEXT = ROOT / "runtime" / "pep_text"
BUILD = ROOT / "_build" / "textbuf"

CLANG_FLAGS = ["-std=c23", "-Wall", "-Wextra", "-Wpedantic", "-Werror"]
MODEL_EXPECTED_OUTPUT = (
    "128\n64\n8\n9223372036854775807\n"
    "8\n100\n128\n2048\n"
    "1\n1\n2\n3\n19\n20\n"
)
UTF8_MODEL_EXPECTED_OUTPUT = (
    "1\n1\n-1\n-1\n2\n2\n3\n3\n4\n4\n-1\n-1\n"
    "160\n144\n128\n128\n159\n143\n191\n191\n"
)
PROBE_EXPECTED_OUTPUT = (
    "v ok\nv ok\nv ok\nv ok\nv ok\n"
    "v err 0\nv err 0\nv err 0\nv err 1\nv err 1\nv err 1\nv err 0\nv err 0\n"
    "v err 1\nv err 1\nv err 0\n"
    "d 41 1\nd E9 2\nd 20AC 3\nd 1F600 4\n"
    "d invalid\nd invalid\nd invalid\n"
    "e 1 41\ne 2 C3A9\ne 3 E282AC\ne 4 F09F9880\n"
    "e invalid\ne invalid\ne invalid\ne 4 F48FBFBF\n"
)
DEMO_MARKERS = (
    "/* fragments: one, two */",
    "static int64_t demo_add(int64_t a, int64_t b)",
    "int main(void)",
    "(void)printf(\"%lld\\n\", (long long)answer);",
    "/* i64min=-9223372036854775808 i64max=9223372036854775807 */",
)


def run_program(command, **kwargs):
    return subprocess.run(command, text=True, capture_output=True, check=False, **kwargs)


class TextbufNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        BUILD.mkdir(parents=True, exist_ok=True)

    def pep(self, *args):
        return run_program(["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"), *args], cwd=ROOT)

    def test_pep_core_checks(self):
        checked = self.pep("check", str(TEXT / "pep_textbuf_core.pep"), "--json")
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertIn('"status":"valid"', checked.stdout)

    def test_pep_model_runs_in_interpreter(self):
        checked = self.pep("check", str(TEXT / "pep_textbuf_model.pep"), "--json")
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertIn('"status":"valid"', checked.stdout)
        ran = self.pep("run", str(TEXT / "pep_textbuf_model.pep"))
        self.assertEqual(ran.returncode, 0, ran.stderr)
        self.assertEqual(ran.stdout, MODEL_EXPECTED_OUTPUT)

    def compile_demo(self, compiler, exe_name):
        exe = BUILD / exe_name
        compiled = run_program(
            [compiler, *CLANG_FLAGS, str(TEXT / "demo_textbuf.c"),
             str(TEXT / "pep_textbuf.c"), "-o", str(exe)],
            cwd=ROOT,
        )
        self.assertEqual(compiled.returncode, 0, compiled.stderr)
        return exe

    def test_demo_clang_gcc_agree(self):
        clang = shutil.which("clang")
        gcc = shutil.which("gcc")
        self.assertIsNotNone(clang, "Clang not found")
        self.assertIsNotNone(gcc, "GCC not found")
        clang_run = run_program([str(self.compile_demo(clang, "demo_clang.exe"))])
        gcc_run = run_program([str(self.compile_demo(gcc, "demo_gcc.exe"))])
        self.assertEqual(clang_run.returncode, 0, clang_run.stderr)
        self.assertEqual(gcc_run.returncode, 0, gcc_run.stderr)
        self.assertEqual(clang_run.stdout, gcc_run.stdout)
        for marker in DEMO_MARKERS:
            self.assertIn(marker, clang_run.stdout)

    def test_core_model_builds_through_emitter(self):
        exe = BUILD / "core_selftest.exe"
        built = run_program(
            ["python", str(ROOT / "pep_c23.py"), "build-c23",
             str(TEXT / "pep_textbuf_core.pep"), "-o", str(exe)],
            cwd=ROOT,
        )
        self.assertEqual(built.returncode, 0, built.stderr)
        ran = run_program([str(exe)])
        # The generated main prints main()'s return: the failure count.
        self.assertEqual(ran.stdout.strip(), "0")


    def test_pep_utf8_model_runs_in_interpreter(self):
        checked = self.pep("check", str(TEXT / "pep_utf8_model.pep"), "--json")
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertIn('"status":"valid"', checked.stdout)
        ran = self.pep("run", str(TEXT / "pep_utf8_model.pep"))
        self.assertEqual(ran.returncode, 0, ran.stderr)
        self.assertEqual(ran.stdout, UTF8_MODEL_EXPECTED_OUTPUT)

    def test_pep_utf8_core_checks(self):
        checked = self.pep("check", str(TEXT / "pep_utf8_core.pep"), "--json")
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertIn('"status":"valid"', checked.stdout)

    def test_utf8_core_builds_through_emitter(self):
        exe = BUILD / "utf8core_selftest.exe"
        built = run_program(
            ["python", str(ROOT / "pep_c23.py"), "build-c23",
             str(TEXT / "pep_utf8_core.pep"), "-o", str(exe)],
            cwd=ROOT,
        )
        self.assertEqual(built.returncode, 0, built.stderr)
        ran = run_program([str(exe)])
        self.assertEqual(ran.stdout.strip(), "0")

    def test_utf8_probe_clang_gcc_agree(self):
        clang = shutil.which("clang")
        gcc = shutil.which("gcc")
        self.assertIsNotNone(clang, "Clang not found")
        self.assertIsNotNone(gcc, "GCC not found")
        outputs = []
        for compiler, name in ((clang, "probe_clang.exe"), (gcc, "probe_gcc.exe")):
            exe = BUILD / name
            compiled = run_program(
                [compiler, *CLANG_FLAGS, str(TEXT / "utf8_probe.c"),
                 str(TEXT / "pep_utf8.c"), "-o", str(exe)],
                cwd=ROOT,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            ran = run_program([str(exe)])
            self.assertEqual(ran.returncode, 0, ran.stderr)
            outputs.append(ran.stdout)
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[0], PROBE_EXPECTED_OUTPUT)

    def test_demo_output_compiles_and_runs(self):
        clang = shutil.which("clang")
        gcc = shutil.which("gcc")
        self.assertIsNotNone(clang, "Clang not found")
        self.assertIsNotNone(gcc, "GCC not found")
        demo = self.compile_demo(clang, "demo_clang.exe")
        generated = run_program([str(demo)])
        self.assertEqual(generated.returncode, 0, generated.stderr)
        gen_path = BUILD / "demo_gen.c"
        gen_path.write_text(generated.stdout, encoding="utf-8", newline="\n")
        for compiler, name in ((clang, "gen_clang.exe"), (gcc, "gen_gcc.exe")):
            exe = BUILD / name
            compiled = run_program(
                [compiler, *CLANG_FLAGS, str(gen_path), "-o", str(exe)],
                cwd=ROOT,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            ran = run_program([str(exe)])
            self.assertEqual(ran.returncode, 0, ran.stderr)
            self.assertEqual(ran.stdout, "13\n")


if __name__ == "__main__":
    unittest.main()
