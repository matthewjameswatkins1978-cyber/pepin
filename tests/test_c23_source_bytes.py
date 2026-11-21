"""Compare a real Pep lexer helper on host-borrowed bytes and the OCaml seed."""

import hashlib
import json
import pathlib
import shutil
import tempfile
import unittest

from pep_c23_direct import C23Emitter, build_c23, run_pep_cmd
from tests.test_a10 import invoke_session, request, result_field, revision, scalar, typed_record
from tests.test_textbuf_native import CLANG_FLAGS, run_guarded


ROOT = pathlib.Path(__file__).resolve().parents[1]
LEXER = ROOT / "examples" / "pep_lexer.pep"
VECTORS = (
    (b"A", 0, False),
    (b"\x00\r\n", 0, False),
    (b"#\xc3\xa9", 1, False),
    (b"#\xe2\x82", 1, False),
    (b"#\xe2A\xa1", 1, False),
    (b"#\xed\xa0\x80", 1, False),
    (b"#\xf4\x90\x80\x80", 1, False),
    (b"#\xf4\x8f\xbf\xbf", 1, False),
    (b"\xc0\x80", 0, False),
    (b"\xff", 0, False),
    (b"", 0, False),
    (b"A", -1, False),
    (b"A", 1, False),
    (b"\xc3\xa9", 1, True),
    (b"A", 1, True),
)


def lexer_helper():
    text = LEXER.read_text(encoding="utf-8")
    record = next(line for line in text.splitlines() if line.startswith("type Utf8Check "))
    function = text[text.index("fn utf8_check("):text.index("fn advance_position(")]
    return record + "\n" + function + """
fn probe(source: SourceBytes, offset: Int, slice: Bool) -> Utf8Check {
    if slice {
        let window = byte_slice(source, offset, offset + 1)
        return Utf8Check { width: byte_at(window, 0), invalidOffset: byte_length(window) }
    }
    return utf8_check(source, offset, byte_length(source))
}
"""


def target(document, raw):
    return {"document": document, "revision": "sha256:" + hashlib.sha256(raw).hexdigest(),
            "entryFunctions": []}


def harness(vectors):
    lines = [
        "int main(int argc, char **argv) {",
        "  if (argc != 2) return 2;",
        "  pep_rec_Utf8Check result;",
        "  switch (strtol(argv[1], nullptr, 10)) {",
    ]
    for i, (raw, offset, slice_bytes) in enumerate(vectors):
        lines.append(f"    case {i}: {{")
        data = "nullptr"
        if raw:
            data = "raw"
            lines.append(f"      const unsigned char raw[] = {{ {', '.join(map(str, raw))} }};")
        view = f"(pep_source_bytes){{ {data}, {len(raw)} }}"
        lines.append(f"      result = pep_fn_probe({view}, {offset}, {'true' if slice_bytes else 'false'});")
        lines.extend(["      break;", "    }"])
    lines.extend([
        f"    case {len(vectors)}: {{",
        "      static const unsigned char too_large[65537] = {0};",
        "      result = pep_fn_probe((pep_source_bytes){ too_large, sizeof too_large }, 0, false);",
        "      break;",
        "    }",
        "    default: return 2;",
        "  }",
        '  printf("%lld %lld\\n", (long long)result.width, (long long)result.invalidOffset);',
        "  return 0;",
        "}",
    ])
    return "\n".join(lines)


class C23BorrowedSourceTests(unittest.TestCase):
    def setUp(self):
        build = ROOT / "_build"
        build.mkdir(exist_ok=True)
        directory = tempfile.TemporaryDirectory(dir=build)
        self.addCleanup(directory.cleanup)
        self.work = pathlib.Path(directory.name)

    def seed_oracle(self, source):
        tool = source + """
fn probe_tool(offset: Int, slice: Bool) -> Utf8Check {
    return probe(source_bytes(), offset, slice)
}
"""
        tool_ref = {"tool": "probe", "document": "doc-1", "revision": revision(tool)}
        args = [scalar("Int", "0"), scalar("Bool", False)]
        requests = [
            request("open", source=tool),
            request("open_bytes", bytes=[65]),
            request("tool_register", function="probe_tool", **tool_ref),
            request("tool_validate", **tool_ref, testVectors=[{
                "arguments": args,
                "expect": typed_record("Utf8Check", width=scalar("Int", "1"),
                                       invalidOffset=scalar("Int", "-1")),
                "semanticTarget": target("doc-2", b"A"),
            }]),
            request("tool_activate", **tool_ref),
        ]
        for i, (raw, offset, slice_bytes) in enumerate(VECTORS, start=3):
            requests.extend([
                request("open_bytes", bytes=list(raw)),
                request("tool_invoke", tool="probe",
                        arguments=[scalar("Int", str(offset)), scalar("Bool", slice_bytes)],
                        semanticTarget=target(f"doc-{i}", raw)),
            ])
        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(rows[3].get("status"), "Validated", rows[3])
        self.assertEqual(rows[4].get("status"), "Active", rows[4])
        return rows[6::2]

    def test_real_lexer_helper_matches_seed_on_checked_byte_views(self):
        compilers = [exe for name in ("clang", "gcc") if (exe := shutil.which(name))]
        if not compilers:
            self.skipTest("Clang and GCC are unavailable")
        source = lexer_helper()
        oracle = self.seed_oracle(source)
        self.assertEqual(len(oracle), len(VECTORS))
        pep_file = self.work / "helper.pep"
        pep_file.write_text(source, encoding="utf-8")
        status, stdout, stderr = run_pep_cmd("check", str(pep_file), "--json")
        self.assertEqual(status, 0, stderr or stdout)
        c_source = C23Emitter(json.loads(stdout)).generate_c23()
        c_file = pep_file.with_suffix(".c")
        c_file.write_text("#define main pep_generated_main\n" + c_source
                          + "\n#undef main\n" + harness(VECTORS), encoding="utf-8")
        executable = pep_file.with_suffix(".exe")
        for compiler in compilers:
            build = run_guarded([compiler, *CLANG_FLAGS, "-O2", str(c_file), "-o", str(executable)],
                                text=True, timeout=60)
            self.assertEqual(build.returncode, 0, build.stderr)
            for i, seed in enumerate(oracle):
                with self.subTest(compiler=compiler, vector=i):
                    run = run_guarded([str(executable), str(i)], text=True, timeout=30)
                    if "result" in seed:
                        width = result_field(seed["result"], "width")
                        invalid = result_field(seed["result"], "invalidOffset")
                        self.assertEqual((run.returncode, run.stdout, run.stderr),
                                         (0, f"{width} {invalid}\n", ""))
                    else:
                        self.assertEqual((run.returncode, run.stdout), (1, ""))
                        self.assertTrue(run.stderr.startswith(seed["error"]["code"] + ":"), run.stderr)
            oversized = run_guarded([str(executable), str(len(VECTORS))], text=True, timeout=30)
            self.assertEqual((oversized.returncode, oversized.stdout), (1, ""))
            self.assertIn("PEP_SOURCE_BYTE_LIMIT", oversized.stderr)

    def test_standalone_build_has_no_source_grant(self):
        pep_file = self.work / "ungranted.pep"
        executable = pep_file.with_suffix(".exe")
        for source, reason in (
            ("fn main() -> Int { return byte_length(source_bytes()) }", "source_bytes"),
            ("fn main(s: SourceBytes) -> Int { return byte_length(s) }", "without parameters"),
        ):
            with self.subTest(reason=reason):
                pep_file.write_text(source, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, reason):
                    build_c23(pep_file, executable)
                self.assertFalse(executable.exists())
                self.assertFalse(pep_file.with_suffix(".c").exists())
