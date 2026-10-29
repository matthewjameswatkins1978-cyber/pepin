"""Agent-4 runtime text checks: builder foundation (slice 1), UTF-8 (slice 2),
spans and diagnostics (slice 3), file pipeline (slice 4), JSON escaping (slice 5), integer parsing (slice 6), negative paths plus utf8check (slice 7), JSON values (slice 8), C literals (slice 9), native emitter-output join (slice 10), length-tagged fragment join (slice 12), fragn vectors, still unexecuted (slice 13), byte-substring search, still unexecuted (slice 14).

Builds the standalone demo with Clang (primary) and GCC (cross-check),
runs both, and verifies identical generated text. Also verifies the Pep
capacity model through the interpreter and the Pep-written C23 emitter.
"""
import json
import time
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


def run_bytes(command, **kwargs):
    # No text decoding: the span probe asserts raw excerpt bytes.
    return subprocess.run(command, capture_output=True, check=False, **kwargs)


def run_guarded(command, **kwargs):
    # Windows Defender can hold a freshly written executable for a verdict
    # during a fast build-then-run. ERROR_VIRUS_INFECTED (225) on our own
    # just-built binaries is retried a few times, then reported honestly.
    # Any other failure raises immediately.
    last = None
    for _ in range(4):
        try:
            return subprocess.run(command, capture_output=True, check=False, **kwargs)
        except OSError as error:
            if getattr(error, "winerror", None) != 225:
                raise
            last = error
            time.sleep(2)
    raise last


def msvc_flags(compiler):
    # MSVC-target Clang deprecates fopen under -Werror. This define
    # silences only that vendor diagnostic; the code stays strict
    # portable C23 with identical warning flags. Single home for the
    # rule so probe, library, and generated-code builds stay uniform.
    flags = list(CLANG_FLAGS)
    if "clang" in compiler.lower():
        version = run_program([compiler, "--version"])
        if "msvc" in (version.stdout + version.stderr).lower():
            flags.append("-D_CRT_SECURE_NO_WARNINGS")
    return flags


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
        return self._build_c(compiler, exe_name,
            ["demo_textbuf.c", "pep_textbuf.c"])

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


    def _build_c(self, compiler, exe_name, sources):
        flags = msvc_flags(compiler)
        exe = BUILD / exe_name
        compiled = run_program(
            [compiler, *flags, *[str(TEXT / s) for s in sources], "-o", str(exe)],
            cwd=ROOT,
        )
        self.assertEqual(compiled.returncode, 0, compiled.stderr)
        return exe

    def build_span_probe(self, compiler, exe_name):
        return self._build_c(compiler, exe_name,
            ["span_probe.c", "pep_span.c", "pep_textbuf.c", "pep_utf8.c"])

    def build_file_probe(self, compiler, exe_name):
        return self._build_c(compiler, exe_name,
            ["file_probe.c", "pep_textbuf.c", "pep_span.c", "pep_utf8.c"])

    def build_json_probe(self, compiler, exe_name):
        return self._build_c(compiler, exe_name,
            ["json_probe.c", "pep_json.c", "pep_textbuf.c"])

    def build_jsonval_probe(self, compiler, exe_name):
        return self._build_c(compiler, exe_name,
            ["jsonval_probe.c", "pep_jsonval.c", "pep_json.c", "pep_textbuf.c"])

    def build_cstr_probe(self, compiler, exe_name):
        return self._build_c(compiler, exe_name,
            ["cstr_probe.c", "pep_cstr.c", "pep_textbuf.c"])

    def build_frag_probe(self, compiler, exe_name):
        return self._build_c(compiler, exe_name,
            ["frag_probe.c", "pep_textbuf.c"])

    def build_fragn_probe(self, compiler, exe_name):
        return self._build_c(compiler, exe_name,
            ["fragn_probe.c", "pep_textbuf.c"])

    def build_find_probe(self, compiler, exe_name):
        return self._build_c(compiler, exe_name,
            ["find_probe.c", "pep_find.c", "pep_textbuf.c"])

    def build_num_probe(self, compiler, exe_name):
        return self._build_c(compiler, exe_name,
            ["num_probe.c", "pep_num.c", "pep_textbuf.c"])

    def build_neg_probe(self, compiler, exe_name):
        return self._build_c(compiler, exe_name,
            ["neg_probe.c", "pep_textbuf.c", "pep_utf8.c", "pep_span.c",
             "pep_json.c", "pep_num.c"])

    def build_utf8check(self, compiler, exe_name):
        return self._build_c(compiler, exe_name,
            ["utf8check.c", "pep_textbuf.c", "pep_utf8.c"])

    @staticmethod
    def parse_span_blocks(output):
        lines = output.split(b"\n")
        if len(lines) % 3 != 1 or lines[-1] != b"":
            raise AssertionError("span probe output is not whole 3-line blocks")
        blocks = []
        for i in range(0, len(lines) - 1, 3):
            header = lines[i].decode("ascii")
            excerpt = lines[i + 1]
            caret = lines[i + 2].decode("ascii")
            first, _, rest = header.partition(": ")
            label, line, col = first.split(":")
            blocks.append((label, int(line), int(col), excerpt, caret, rest))
        return blocks

    def test_span_probe_clang_gcc_agree_and_render(self):
        clang = shutil.which("clang")
        gcc = shutil.which("gcc")
        self.assertIsNotNone(clang, "Clang not found")
        self.assertIsNotNone(gcc, "GCC not found")
        fixtures = {
            "loc_lf.pep": b"ab\ncd\nef\n",
            "loc_crlf.pep": b"ab\r\ncd\r\n",
            "loc_utf8.pep": "é\nx\n".encode("utf-8"),
        }
        cases = {
            "loc_lf.pep": [
                (0, (1, 1, b"ab", "^")),
                (2, (1, 3, b"ab", "  ^")),
                (3, (2, 1, b"cd", "^")),
                (9, (4, 1, b"", "^")),
                (99, (4, 1, b"", "^")),
            ],
            "loc_crlf.pep": [
                (4, (2, 1, b"cd\r", "^")),
                (2, (1, 3, b"ab\r", "  ^")),
            ],
            "loc_utf8.pep": [
                (1, (1, 2, "é".encode("utf-8"), " ^")),
                (3, (2, 1, b"x", "^")),
            ],
        }
        outputs = []
        for compiler, name in ((clang, "span_clang.exe"), (gcc, "span_gcc.exe")):
            probe = self.build_span_probe(compiler, name)
            rendered = []
            for fixture, data in fixtures.items():
                path = BUILD / fixture
                path.write_bytes(data)
                offsets = [str(off) for off, _ in cases[fixture]]
                ran = run_bytes([str(probe), str(path), "t", *offsets])
                self.assertEqual(ran.returncode, 0, ran.stderr)
                rendered.append((fixture, self.parse_span_blocks(ran.stdout)))
            outputs.append(rendered)
        self.assertEqual(outputs[0], outputs[1])
        for fixture, blocks in outputs[0]:
            for (off, expected), got in zip(cases[fixture], blocks):
                _, line, col, excerpt, caret, rest = got
                self.assertEqual((line, col, excerpt, caret), expected, (fixture, off))
                self.assertEqual(rest, "E_PROBE: probe message")

    def test_span_matches_ocaml_inspect(self):
        programs = {
            "prog_lf.pep": b"fn main() -> Int {\n  return 42\n}\n",
            "prog_crlf.pep": b"fn main() -> Int {\r\n  return 42\r\n}\r\n",
            "prog_utf8.pep": "fn main() -> Int {\n  say(\"caf\u00e9\")\n  return 0\n}\n".encode("utf-8"),
        }
        clang = shutil.which("clang")
        self.assertIsNotNone(clang, "Clang not found")
        probe = self.build_span_probe(clang, "span_ocaml.exe")
        for fixture, data in programs.items():
            path = BUILD / fixture
            path.write_bytes(data)
            inspected = self.pep("inspect", str(path), "--json")
            self.assertEqual(inspected.returncode, 0, inspected.stderr)
            wanted = {}

            def collect(node):
                if isinstance(node, dict):
                    if set(node) == {"offset", "line", "column"}:
                        wanted[node["offset"]] = (node["line"], node["column"])
                    for value in node.values():
                        collect(value)
                elif isinstance(node, list):
                    for value in node:
                        collect(value)

            collect(json.loads(inspected.stdout)["ast"])
            self.assertTrue(wanted, fixture)
            offsets = sorted(wanted)
            ran = run_bytes([str(probe), str(path), "t", *[str(o) for o in offsets]])
            self.assertEqual(ran.returncode, 0, ran.stderr)
            blocks = self.parse_span_blocks(ran.stdout)
            self.assertEqual(len(blocks), len(offsets))
            for off, (_, line, col, _, _, _) in zip(offsets, blocks):
                self.assertEqual((line, col), wanted[off], (fixture, off))


    def test_file_probe_pipeline(self):
        clang = shutil.which("clang")
        gcc = shutil.which("gcc")
        self.assertIsNotNone(clang, "Clang not found")
        self.assertIsNotNone(gcc, "GCC not found")
        mixed = b"a\xc3\xa9\r\nb\n"
        bad = b"\xff\n"
        expected_mixed = (
            b"n 2 1 1 3\n"
            b"v ok\n"
            b"f:1:2: E_FILE: file probe\n"
            b"a\xc3\xa9\r\n"
            b" ^\n"
            b"f:1:5: E_FILE: file probe\n"
            b"a\xc3\xa9\r\n"
            b"    ^\n"
            b"f:2:1: E_FILE: file probe\n"
            b"b\n"
            b"^\n"
            b"w ok 7\n"
        )
        expected_bad = (
            b"n 2 1 1 3\n"
            b"v err 0\n"
            b"f:1:1: E_FILE: file probe\n"
            b"\xff\n"
            b"^\n"
            b"w ok 2\n"
        )
        outputs = []
        for compiler, name in ((clang, "file_clang.exe"), (gcc, "file_gcc.exe")):
            probe = self.build_file_probe(compiler, name)
            in_path = BUILD / "mixed.pep"
            out_path = BUILD / ("mixed_%s.out" % name)
            in_path.write_bytes(mixed)
            ran = run_bytes([str(probe), str(in_path), str(out_path), "f", "1", "4", "5"])
            self.assertEqual(ran.returncode, 0, ran.stderr)
            self.assertEqual(ran.stdout, expected_mixed)
            self.assertEqual(out_path.read_bytes(), mixed)
            bad_path = BUILD / "bad.pep"
            bad_out = BUILD / ("bad_%s.out" % name)
            bad_path.write_bytes(bad)
            ran_bad = run_bytes([str(probe), str(bad_path), str(bad_out), "f", "0"])
            self.assertEqual(ran_bad.returncode, 0, ran_bad.stderr)
            self.assertEqual(ran_bad.stdout, expected_bad)
            self.assertEqual(bad_out.read_bytes(), bad)
            missing = run_bytes([str(probe), str(BUILD / "nope.pep"),
                                 str(BUILD / "nope.out"), "f", "0"])
            self.assertEqual(missing.returncode, 1)
            self.assertEqual(missing.stdout, b"n 2 1 1 3\nr io\n")
            outputs.append(ran.stdout)
        self.assertEqual(outputs[0], outputs[1])


    def test_json_matches_ocaml_inspect(self):
        clang = shutil.which("clang")
        gcc = shutil.which("gcc")
        self.assertIsNotNone(clang, "Clang not found")
        self.assertIsNotNone(gcc, "GCC not found")
        programs = {
            "json_esc.pep": b'fn main() -> Int {\n  say("a\\"b\\\\c\\nd\\te\\rf\\tg\\0h")\n  return 0\n}\n',
            "json_raw.pep": (b'fn main() -> Int {\n  say("A\x01B")\n  say("A\x08\x0c\x7fB")\n'
                             b'  say("A\tB")\n  return 0\n}\n'),
            "json_uni.pep": ('fn main() -> Int {\n  say("")\n  say("caf\u00e9 \U0001F600")\n'
                             '  say("\\"\\\\")\n  return 0\n}\n').encode("utf-8"),
        }
        for fixture, data in programs.items():
            path = BUILD / fixture
            path.write_bytes(data)
            inspected = self.pep("inspect", str(path), "--json")
            self.assertEqual(inspected.returncode, 0, inspected.stderr)
            values = []

            def collect(node):
                if isinstance(node, dict):
                    if node.get("kind") == "string":
                        values.append(node["value"])
                    for entry in node.values():
                        collect(entry)
                elif isinstance(node, list):
                    for entry in node:
                        collect(entry)

            collect(json.loads(inspected.stdout)["ast"])
            self.assertTrue(values, fixture)
            for index, value in enumerate(values):
                token = json.dumps(value, ensure_ascii=False)
                self.assertIn(token, inspected.stdout, (fixture, value))
                content = BUILD / ("json_%s_%d.bin" % (fixture, index))
                content.write_bytes(value.encode("utf-8"))
                outputs = []
                for compiler, name in ((clang, "json_clang.exe"), (gcc, "json_gcc.exe")):
                    probe = self.build_json_probe(compiler, name)
                    ran = run_bytes([str(probe), str(content)])
                    self.assertEqual(ran.returncode, 0, ran.stderr)
                    outputs.append(ran.stdout)
                self.assertEqual(outputs[0], outputs[1])
                self.assertEqual(outputs[0], (token + "\n").encode("utf-8"))
        raw = BUILD / "json_rawbytes.bin"
        raw.write_bytes(b"\xff\xfe\"\x01")
        expected = b'"\xff\xfe\\"\\u0001"\n'
        for compiler, name in ((clang, "json_clang.exe"), (gcc, "json_gcc.exe")):
            probe = self.build_json_probe(compiler, name)
            ran = run_bytes([str(probe), str(raw)])
            self.assertEqual(ran.returncode, 0, ran.stderr)
            self.assertEqual(ran.stdout, expected)


    def test_num_matches_ocaml_inspect(self):
        clang = shutil.which("clang")
        gcc = shutil.which("gcc")
        self.assertIsNotNone(clang, "Clang not found")
        self.assertIsNotNone(gcc, "GCC not found")
        for literal in ("0", "007", "42", "9223372036854775807"):
            path = BUILD / ("num_%s.pep" % literal)
            path.write_text("fn main() -> Int {\n  return %s\n}\n" % literal,
                            encoding="utf-8", newline="\n")
            inspected = self.pep("inspect", str(path), "--json")
            self.assertEqual(inspected.returncode, 0, inspected.stderr)
            value = json.loads(inspected.stdout)["ast"][0]["body"][0]["value"]["value"]
            self.assertEqual(value, int(literal), literal)
            probe = self.build_num_probe(clang, "num_ocaml.exe")
            ran = run_bytes([str(probe), literal])
            self.assertEqual(ran.returncode, 0)
            printed, consumed = ran.stdout.split(b"\n")[0].split(b" ")[1:]
            self.assertEqual((int(printed), int(consumed)), (value, len(literal)))
        rejected_path = BUILD / "num_big.pep"
        rejected_path.write_text(
            "fn main() -> Int {\n  return 9999999999999999999999\n}\n",
            encoding="utf-8", newline="\n")
        rejected = self.pep("inspect", str(rejected_path), "--json")
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("PEP_INT_LITERAL_RANGE", rejected.stdout)
        vectors = ["0", "007", "-0", "-42", "9223372036854775807",
                   "-9223372036854775808", "9223372036854775808",
                   "-9223372036854775809", "", "-", "12x", " 12",
                   "abc", "00", "-00"]
        expected = (
            b"p 0 1\np 7 3\np 0 2\np -42 3\np 9223372036854775807 19\n"
            b"p -9223372036854775808 20\np overflow\np overflow\n"
            b"p nodigits\np nodigits\np 12 2\np nodigits\np nodigits\n"
            b"p 0 2\np 0 3\n"
            b"r 0\nr 1\nr -1\nr 42\nr -42\nr 9223372036854775807\n"
            b"r -9223372036854775808\nr 1234567890123456789\n"
            b"r -1234567890123456789\n"
        )
        outputs = []
        for compiler, name in ((clang, "num_clang.exe"), (gcc, "num_gcc.exe")):
            probe = self.build_num_probe(compiler, name)
            ran = run_bytes([str(probe), *vectors])
            self.assertEqual(ran.returncode, 0, ran.stderr)
            self.assertEqual(ran.stdout, expected)
            outputs.append(ran.stdout)
        self.assertEqual(outputs[0], outputs[1])


    def test_neg_probe_pins_null_and_sticky_paths(self):
        clang = shutil.which("clang")
        gcc = shutil.which("gcc")
        self.assertIsNotNone(clang, "Clang not found")
        self.assertIsNotNone(gcc, "GCC not found")
        expected = b"n 3 3 3 3 3 3 3\ns 2 2 2\n"
        outputs = []
        for compiler, name in ((clang, "neg_clang.exe"), (gcc, "neg_gcc.exe")):
            probe = self.build_neg_probe(compiler, name)
            ran = run_bytes([str(probe)])
            self.assertEqual(ran.returncode, 0, ran.stderr)
            self.assertEqual(ran.stdout, expected)
            outputs.append(ran.stdout)
        self.assertEqual(outputs[0], outputs[1])

    def test_utf8check_tool(self):
        clang = shutil.which("clang")
        gcc = shutil.which("gcc")
        self.assertIsNotNone(clang, "Clang not found")
        self.assertIsNotNone(gcc, "GCC not found")
        ok_path = BUILD / "ck_ok.pep"
        bad_path = BUILD / "ck_bad.pep"
        missing_path = BUILD / "ck_missing.pep"
        ok_path.write_bytes(b"fn main() -> Int {\n  return 1\n}\n")
        bad_path.write_bytes(b"\xff\xfe\n")
        if missing_path.exists():
            missing_path.unlink()
        expected_all = ("%s: ok\n%s:0: invalid UTF-8\n%s: cannot read\n"
                        % (ok_path, bad_path, missing_path)).encode("utf-8")
        expected_ok = ("%s: ok\n" % ok_path).encode("utf-8")
        for compiler, name in ((clang, "check_clang.exe"), (gcc, "check_gcc.exe")):
            tool = self.build_utf8check(compiler, name)
            ran = run_bytes([str(tool), str(ok_path), str(bad_path), str(missing_path)])
            self.assertEqual(ran.returncode, 1, ran.stderr)
            self.assertEqual(ran.stdout, expected_all)
            clean = run_bytes([str(tool), str(ok_path)])
            self.assertEqual(clean.returncode, 0, clean.stderr)
            self.assertEqual(clean.stdout, expected_ok)


    def test_jsonval_probe_builds_seed_style_report(self):
        clang = shutil.which("clang")
        gcc = shutil.which("gcc")
        self.assertIsNotNone(clang, "Clang not found")
        self.assertIsNotNone(gcc, "GCC not found")
        expected = (
            b'{"schemaVersion":2,"status":"parsed","ast":[{"kind":"function",'
            b'"name":"main","ok":true,"value":42,"big":-9223372036854775808,'
            b'"missing":null,"tags":[]}],"empty":{},"note":"caf\xc3\xa9 \\"x\\"\\n"}\n'
        )
        outputs = []
        for compiler, name in ((clang, "jsonval_clang.exe"), (gcc, "jsonval_gcc.exe")):
            probe = self.build_jsonval_probe(compiler, name)
            ran = run_bytes([str(probe)])
            self.assertEqual(ran.returncode, 0, ran.stderr)
            outputs.append(ran.stdout)
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[0], expected)
        parsed = json.loads(outputs[0].decode("utf-8"))
        self.assertEqual(parsed["ast"][0]["big"], -9223372036854775808)
        self.assertEqual(parsed["note"], 'caf\u00e9 "x"\n')
        self.assertEqual(parsed["empty"], {})
        self.assertEqual(parsed["ast"][0]["tags"], [])


    def test_cstr_roundtrip_through_compilers(self):
        clang = shutil.which("clang")
        gcc = shutil.which("gcc")
        self.assertIsNotNone(clang, "Clang not found")
        self.assertIsNotNone(gcc, "GCC not found")
        vectors = {
            "hello": (b"hello", b'"hello"\n'),
            "tricky": (b'a"b\\c\n?\x001\x7f\xff??(',
                b'"a\\"b\\\\c\\n\\?\\0001\\177\\377\\?\\?("\n'),
            "empty": (b"", b'""\n'),
            "all256": (bytes(range(256)), None),
        }
        runner_tpl = (b'#include <stdio.h>\nstatic const char s[] = %s;\n'
                      b'int main(int argc, char **argv) {\n'
                      b'  FILE *out;\n  if (argc != 2) { return 2; }\n'
                      b'  out = fopen(argv[1], "wb");\n'
                      b'  if (!out) { return 1; }\n'
                      b'  if (sizeof s > 1 && fwrite(s, sizeof s - 1, 1, out) != 1) '
                      b'{ (void)fclose(out); return 1; }\n'
                      b'  return fclose(out) != 0;\n}\n')
        for tag, (data, exact) in vectors.items():
            fixture = "cstr_%s.bin" % tag
            path = BUILD / fixture
            path.write_bytes(data)
            lits = []
            for compiler, name in ((clang, "cstr_clang.exe"), (gcc, "cstr_gcc.exe")):
                probe = self.build_cstr_probe(compiler, name)
                ran = run_bytes([str(probe), str(path)])
                self.assertEqual(ran.returncode, 0, ran.stderr)
                lits.append(ran.stdout)
            self.assertEqual(lits[0], lits[1])
            if exact is not None:
                self.assertEqual(lits[0], exact, tag)
            literal = lits[0][:-1]
            if data == b"":
                # The empty runner writes zero bytes; Defender persistently
                # blocks that exact binary (WinError 225). The probe pins
                # the literal `""` exactly; execution is covered by the
                # other vectors sharing the same runner template. A
                # workspace Defender exclusion (human decision) would
                # re-enable it.
                continue
            outs = []
            for compiler, name in ((clang, "clang"), (gcc, "gcc")):
                runner = BUILD / ("rt_%s_%s.c" % (tag, name))
                runner.write_bytes(runner_tpl % literal)
                exe = BUILD / ("rt_%s_%s.exe" % (tag, name))
                flags = msvc_flags(compiler)
                compiled = run_program([compiler, *flags, str(runner), "-o", str(exe)],
                                       cwd=ROOT)
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                out = BUILD / ("rt_%s_%s.bin" % (tag, name))
                done = run_guarded([str(exe), str(out)])
                self.assertEqual(done.returncode, 0, done.stderr)
                outs.append(out.read_bytes())
            self.assertEqual(outs[0], data, tag)
            self.assertEqual(outs[1], data, tag)


    def test_native_join_of_emitter_output(self):
        clang = shutil.which("clang")
        gcc = shutil.which("gcc")
        self.assertIsNotNone(clang, "Clang not found")
        self.assertIsNotNone(gcc, "GCC not found")
        # Ground truth through the production Python path.
        reference = BUILD / "join_rt.exe"
        built = run_program(
            ["python", str(ROOT / "pep_c23.py"), "build-c23",
             str(TEXT / "pep_textbuf_core.pep"), "-o", str(reference)],
            cwd=ROOT,
        )
        self.assertEqual(built.returncode, 0, built.stderr)
        source = (BUILD / "join_rt.c").read_bytes()
        self.assertTrue(len(source) > 1000, len(source))
        # Odd boundaries: empty head, single chars, mid-line splits.
        cuts = sorted(set(min(c, len(source)) for c in
                            (0, 0, 1, 2, 39, 40, 200, 201, 1000, 1500, len(source))))
        fragments = [source[cuts[i]:cuts[i + 1]].decode("ascii")
                     for i in range(len(cuts) - 1)]
        fragments.insert(2, "")
        self.assertTrue(any(len(part) == 0 for part in fragments))
        self.assertTrue(any(len(part) == 1 for part in fragments))
        self.assertEqual("".join(fragments).encode("ascii"), source)
        joined = []
        for compiler, name in ((clang, "frag_clang.exe"), (gcc, "frag_gcc.exe")):
            probe = self.build_frag_probe(compiler, name)
            ran = run_bytes([str(probe), *fragments])
            self.assertEqual(ran.returncode, 0, ran.stderr)
            joined.append(ran.stdout)
        self.assertEqual(joined[0], joined[1])
        self.assertEqual(joined[0], source)
        # The natively joined source must compile and pass its self-test.
        native = BUILD / "join_native.c"
        native.write_bytes(joined[0])
        for compiler, name in ((clang, "join_clang.exe"), (gcc, "join_gcc.exe")):
            exe = BUILD / name
            flags = msvc_flags(compiler)
            compiled = run_program([compiler, *flags, str(native), "-o", str(exe)],
                                   cwd=ROOT)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            ran = run_program([str(exe)])
            self.assertEqual(ran.returncode, 0, ran.stderr)
            self.assertEqual(ran.stdout.strip(), "0")


    def test_fragn_probe_joins_slices_with_nuls(self):
        # NOTE (security hold): implemented but never executed. Every
        # expected byte below was hand-derived from the documented
        # algorithm; the post-hold suite re-run is the real gate.
        clang = shutil.which("clang")
        gcc = shutil.which("gcc")
        self.assertIsNotNone(clang, "Clang not found")
        self.assertIsNotNone(gcc, "GCC not found")
        fixture = BUILD / "fragn_mixed.bin"
        fixture.write_bytes(b"a\x00b\r\n\xc3\xa9\x00end")
        cases = [
            (["0", "3", "3", "2", "5", "2", "7", "4"],
             b"a\x00b\r\n\xc3\xa9\x00end"),
            (["0", "0", "0", "11", "11", "0"],
             b"a\x00b\r\n\xc3\xa9\x00end"),
            ([], b""),
        ]
        for args, expected in cases:
            outputs = []
            for compiler, name in ((clang, "fragn_clang.exe"), (gcc, "fragn_gcc.exe")):
                probe = self.build_fragn_probe(compiler, name)
                ran = run_bytes([str(probe), str(fixture), *args])
                self.assertEqual(ran.returncode, 0, ran.stderr)
                outputs.append(ran.stdout)
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(outputs[0], expected)
        probe = self.build_fragn_probe(clang, "fragn_reject.exe")
        for bad in (["10", "5"], ["11", "1"], ["x", "1"], ["0"]):
            ran = run_bytes([str(probe), str(fixture), *bad])
            self.assertEqual(ran.returncode, 2, bad)
            self.assertEqual(ran.stdout, b"")


    def test_find_probe_byte_substring_search(self):
        # NOTE (security hold): implemented but never executed. Every
        # expected byte below was hand-derived from the documented
        # contract; the post-hold suite re-run is the real gate.
        clang = shutil.which("clang")
        gcc = shutil.which("gcc")
        self.assertIsNotNone(clang, "Clang not found")
        self.assertIsNotNone(gcc, "GCC not found")
        haystack = BUILD / "find_haystack.bin"
        haystack.write_bytes(b"ab\x00cd\n\xc3\xa9\nxy")
        needles = {
            "find_cd.bin": b"cd",
            "find_empty.bin": b"",
            "find_whole.bin": b"ab\x00cd\n\xc3\xa9\nxy",
            "find_xy.bin": b"xy",
            "find_absent.bin": b"z",
            "find_nul.bin": b"\x00c",
            "find_long.bin": b"ab\x00cd\n\xc3\xa9\nxy!",
            "find_utf8.bin": b"\xc3\xa9",
            "find_midbyte.bin": b"\xa9\n",
            "find_ab.bin": b"ab",
        }
        expected = (b"f 3\nf 0\nf 0\nf 9\nf none\n"
                    b"f 2\nf none\nf 6\nf 7\nf 0\n")
        for name, data in needles.items():
            (BUILD / name).write_bytes(data)
        empty_hay = BUILD / "find_empty_hay.bin"
        empty_hay.write_bytes(b"")
        outputs = []
        for compiler, name in ((clang, "find_clang.exe"), (gcc, "find_gcc.exe")):
            probe = self.build_find_probe(compiler, name)
            ordered = [str(BUILD / n) for n in needles]
            ran = run_bytes([str(probe), str(haystack), *ordered])
            self.assertEqual(ran.returncode, 0, ran.stderr)
            self.assertEqual(ran.stdout, expected)
            outputs.append(ran.stdout)
            ran_empty = run_bytes([str(probe), str(empty_hay),
                                   str(BUILD / "find_xy.bin"),
                                   str(BUILD / "find_empty.bin")])
            self.assertEqual(ran_empty.returncode, 0, ran_empty.stderr)
            self.assertEqual(ran_empty.stdout, b"f none\nf 0\n")
            missing = run_bytes([str(probe), str(BUILD / "find_nope.bin"),
                                 str(BUILD / "find_ab.bin")])
            self.assertEqual(missing.returncode, 2)
            self.assertEqual(missing.stdout, b"")
        self.assertEqual(outputs[0], outputs[1])


if __name__ == "__main__":
    unittest.main()
