"""Tracked repro of the two checker/host budget walls (A2 Slice 2 handoff).

A4's first real compiler-A source (`examples/dogfood/pep0/compiler_a.pep`,
19 functions, 1100 FlatAstNode records) is seed-check VALID but `build-c23`
fails *before the emitter is ever invoked*: the `pep-c23-checker` tool
invocation (`pep_c23.py` line 471, `require(checked, "outcome", "ok", ...)`)
is refused by one of two host budget walls in `pep_ocaml.ml`:

  1. **v2 tool-value element budget** (`tool_v2_max_nodes = 10_000`,
     pep_ocaml.ml:1372). A parsed AST crossing the v2 boundary charges ~14
     elements per FlatAstNode (13 fields + the record), so ~714+ nodes exceed
     the budget -> `PEP_TOOL_VALUE_LIMIT`. compiler_a.pep (1100 nodes) hits
     this: measured `parser_node_count = 1100`.

  2. **Checker step budget** (`tool_step_budget = 100_000`, pep_ocaml.ml:1308).
     Even when the argument fits, `pep_checker_a13.pep`'s execution on the
     target exceeds 100k steps at ~19 trivial functions (~80 nodes) ->
     `PEP_RUNTIME_STEP_LIMIT`.

Measured switch (2026-11-07, generated `fn f_i() -> Int { return 42 }` x N):
  19 funcs / 80 nodes -> PEP_RUNTIME_STEP_LIMIT; 180 funcs / 724 nodes ->
  PEP_TOOL_VALUE_LIMIT; 340 funcs / 1364 nodes -> the 1 MiB JSONL message limit
  (pep_c23.py MAX_SESSION_MESSAGE_BYTES, hit client-side before the host). All three
  are checker/host transport limits (A1 lane / host budget decision), NOT emitter
  budget decision), NOT emitter refusals -- the emitter never runs.
"""

import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PEP = ROOT / "pep.ps1"
CLANG = pathlib.Path(r"C:\Users\Matmus\scoop\apps\llvm\current\bin\clang.exe")


def _tiny_program(n):
    lines = [f"fn f{i}() -> Int {{ return 42 }}" for i in range(n)]
    lines.append("fn main() -> Int { return 0 }")
    return "\n".join(lines) + "\n"


@unittest.skipUnless(CLANG.is_file(), f"Clang not installed at {CLANG}")
class CheckerBudgetWalls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / "_build").mkdir(exist_ok=True)

    def invoke(self, *args):
        return subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(PEP), *map(str, args)],
            cwd=ROOT, text=True, capture_output=True, check=False)

    def _build(self, folder, name, source_text):
        source = folder / f"{name}.pep"
        source.write_text(source_text, encoding="utf-8", newline="\n")
        built = folder / f"{name}.exe"
        result = self.invoke("build-c23", source, "--compiler", CLANG,
                             "--output", built)
        return result

    def test_small_program_still_builds(self):
        # Sanity: a well-under-budget program (5 functions, ~24 nodes) still
        # builds -- the walls are size-dependent, not a total checker outage.
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            result = self._build(pathlib.Path(temp), "small", _tiny_program(5))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_checker_step_budget_wall(self):
        # ~19 trivial functions (~80 nodes) fit the v2 element budget but trip the
        # checker's 100k execution step budget -> PEP_RUNTIME_STEP_LIMIT, before
        # any emitter output.
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            result = self._build(pathlib.Path(temp), "steplimit", _tiny_program(19))
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("check parsed source", result.stderr)
            self.assertIn("PEP_RUNTIME_STEP_LIMIT", result.stderr)

    def test_checker_v2_element_budget_wall(self):
        # ~180 trivial functions (~724 nodes) exceed the 10_000-element v2 tool
        # value budget -> PEP_TOOL_VALUE_LIMIT. This is the exact wall
        # compiler_a.pep (1100 nodes) hits.
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            result = self._build(pathlib.Path(temp), "elementlimit", _tiny_program(180))
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("check parsed source", result.stderr)
            self.assertIn("PEP_TOOL_VALUE_LIMIT", result.stderr)

    def test_checker_jsonl_message_wall(self):
        # ~340 trivial functions (~1364 nodes) serialise past the 1 MiB JSONL
        # message limit client-side (pep_c23.py MAX_SESSION_MESSAGE_BYTES) before
        # the host even decodes the request. This is the exact wall A4's latest
        # compiler_a.pep @ 214887a (1448 nodes) hits.
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            result = self._build(pathlib.Path(temp), "messagelimit", _tiny_program(340))
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("1 MiB", result.stderr)


if __name__ == "__main__":
    unittest.main()
