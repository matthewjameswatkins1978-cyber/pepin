"""UTF-8 slice diagnostics and managed result ownership in generated C23."""

import json
import pathlib
import re
import shutil
import tempfile
import unittest

from pep_c23_direct import C23Emitter, run_pep_cmd
from tests.test_a10 import invoke_session, request, revision, scalar
from tests.test_c23_source_bytes import target
from tests.test_textbuf_native import CLANG_FLAGS, run_guarded


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = """\
fn native_slice(source: SourceBytes, start: Int, finish: Int) -> Str {
    let text = utf8_slice(source, start, finish)
    let later = int_text(314159)
    if later == "314159" { return text }
    return later
}
"""
VECTORS = (
    (b"#A\x00B", 1, 4),
    (b"#\xc3\xa9!", 1, 3),
    (b"#\xc3\xa9!", 2, 2),
    (b"#\xc3\xa9!", 1, 2),
    (b"#\xc3\xa9!", -1, 2),
    (b"#\xc3\xa9!", 3, 2),
    (b"#\xc3\xa9!", 2, 5),
    (b"#\xf4\x90\x80(", 1, 5),
    (b"#\xf4\x90\x80(", 1, 4),
    (b"#\xed\xa0\x80", 1, 4),
    (b"\xff", 1, 1),
    (b"", 0, 0),
)
TRAP_OFFSET = re.compile(r"encoding at byte (\d+)")


def harness():
    lines = [
        "int main(int argc, char **argv) {",
        "  if (argc != 2 || atexit(pep_destroy_native_heap) != 0) return 2;",
        "  pep_native_heap.stress = true;",
        "  pep_str_t selected;",
        "  switch (strtol(argv[1], nullptr, 10)) {",
    ]
    for i, (raw, start, finish) in enumerate(VECTORS):
        lines.append(f"    case {i}: {{")
        data = "nullptr"
        if raw:
            data = "raw"
            lines.append(f"      unsigned char raw[] = {{ {', '.join(map(str, raw))} }};")
        view = f"(pep_source_bytes){{ {data}, {len(raw)} }}"
        lines.append(f"      selected = pep_fn_native_slice({view}, {start}, {finish});")
        if raw:
            # The borrow has ended. A returned string must own its bytes.
            lines.append("      memset(raw, 0, sizeof raw);")
        lines.extend(["      break;", "    }"])
    lines.extend([
        "    default: return 2;",
        "  }",
        '  for (size_t i = 0; i < selected.len; ++i) printf("%02x", (unsigned int)(unsigned char)selected.data[i]);',
        "  putchar('\\n');",
        "  return 0;",
        "}",
    ])
    return "\n".join(lines)


class NativeUtf8SliceTests(unittest.TestCase):
    def seed_oracle(self):
        tool = SOURCE + """
fn probe(start: Int, finish: Int) -> Str {
    return native_slice(source_bytes(), start, finish)
}
"""
        tool_ref = {"tool": "slice", "document": "doc-1", "revision": revision(tool)}
        raw, start, finish = VECTORS[0]
        requests = [
            request("open", source=tool),
            request("open_bytes", bytes=list(raw)),
            request("tool_register", function="probe", **tool_ref),
            request("tool_validate", **tool_ref, testVectors=[{
                "arguments": [scalar("Int", str(start)), scalar("Int", str(finish))],
                "expect": scalar("Str", "A\0B"),
                "semanticTarget": target("doc-2", raw),
            }]),
            request("tool_activate", **tool_ref),
        ]
        for i, (raw, start, finish) in enumerate(VECTORS, start=3):
            requests.extend([
                request("open_bytes", bytes=list(raw)),
                request("tool_invoke", tool="slice",
                        arguments=[scalar("Int", str(start)), scalar("Int", str(finish))],
                        semanticTarget=target(f"doc-{i}", raw)),
            ])
        run = invoke_session(requests)
        self.assertEqual(run.returncode, 0, run.stderr)
        rows = [json.loads(row) for row in run.stdout.splitlines()]
        self.assertEqual(rows[3].get("status"), "Validated", rows[3])
        self.assertEqual(rows[4].get("status"), "Active", rows[4])
        return rows[6::2]

    def test_slice_matches_seed_and_owns_its_backing(self):
        compilers = [exe for name in ("clang", "gcc") if (exe := shutil.which(name))]
        if not compilers:
            self.skipTest("Clang and GCC are unavailable")
        oracle = self.seed_oracle()
        self.assertEqual(len(oracle), len(VECTORS))
        build = ROOT / "_build"
        build.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=build) as directory:
            pep_file = pathlib.Path(directory) / "slice.pep"
            pep_file.write_text(SOURCE, encoding="utf-8")
            status, output, error = run_pep_cmd("check", str(pep_file), "--json")
            self.assertEqual(status, 0, error or output)
            c_file = pep_file.with_suffix(".c")
            generated = C23Emitter(json.loads(output)).generate_c23()
            c_file.write_text("#define main pep_generated_main\n" + generated
                              + "\n#undef main\n" + harness(), encoding="utf-8")
            exe = pep_file.with_suffix(".exe")
            for compiler in compilers:
                compiled = run_guarded([compiler, *CLANG_FLAGS, "-O2", str(c_file), "-o", str(exe)],
                                       text=True, timeout=60)
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                for i, seed in enumerate(oracle):
                    with self.subTest(compiler=compiler, vector=i):
                        run = run_guarded([str(exe), str(i)], text=True, timeout=30)
                        if "result" in seed:
                            expected = seed["result"]["value"].encode("utf-8").hex()
                            self.assertEqual((run.returncode, run.stdout, run.stderr),
                                             (0, expected + "\n", ""))
                            continue
                        self.assertEqual((run.returncode, run.stdout), (1, ""))
                        trap = seed["error"]
                        self.assertTrue(run.stderr.startswith(trap["code"] + ":"), run.stderr)
                        if trap["code"] == "PEP_RUNTIME_INVALID_UTF8":
                            seed_offset = TRAP_OFFSET.search(trap["message"])
                            native_offset = TRAP_OFFSET.search(run.stderr)
                            self.assertIsNotNone(seed_offset, trap)
                            self.assertIsNotNone(native_offset, run.stderr)
                            self.assertEqual(native_offset.group(1), seed_offset.group(1))
