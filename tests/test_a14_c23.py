import json
import os
import pathlib
import subprocess
import unittest

from tests.test_a11 import JsonLineClient, revision, typed, typed_list, typed_record

ROOT = pathlib.Path(__file__).resolve().parents[1]
BUILD = ROOT / "_build" / "a14"
LEXER = ROOT / "examples" / "pep_lexer.pep"
PARSER = ROOT / "examples" / "pep_parser.pep"
CHECKER = ROOT / "tests" / "pep_checker_a13.pep"
EMITTER = ROOT / "tests" / "pep_c23_emitter.pep"
CLANG = pathlib.Path(r"C:\Users\Matmus\scoop\apps\llvm\current\bin\clang.exe")
GCC = pathlib.Path(r"C:\Users\Matmus\scoop\apps\mingw\current\bin\gcc.exe")


def fields(value):
    return {item["name"]: item["value"] for item in value["fields"]}


def scalar(value):
    return int(value["value"]) if value["type"] == "Int" else value["value"]


def emission(status, parts=(), diagnostic=""):
    return typed_record("PepC23Emission", [
        ("status", typed("Str", status)),
        ("sourceParts", typed_list("Str", [typed("Str", part) for part in parts])),
        ("diagnostic", typed("Str", diagnostic)),
    ])


class A14C23EmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        BUILD.mkdir(parents=True, exist_ok=True)
        cls.bundle = "\n".join(path.read_text(encoding="utf-8") for path in
                                (LEXER, PARSER, CHECKER, EMITTER))
        (BUILD / "emitter_bundle.pep").write_text(cls.bundle, encoding="utf-8", newline="\n")
        for compiler in (CLANG, GCC):
            if not compiler.is_file():
                raise unittest.SkipTest(f"required C23 compiler unavailable: {compiler}")

    def setUp(self):
        self.client = JsonLineClient(
            ["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"), "session", "--jsonl"],
            ROOT, os.environ.copy(),
        )
        opened = self.client.send({"schemaVersion": 3, "op": "open", "source": self.bundle,
                                   "name": "a14-c23-emitter", "metadataOnly": True})
        self.assertEqual(opened.get("outcome"), "ok", opened)
        self.assertEqual(opened.get("status"), "valid", opened)
        self.tool_document = opened["document"]
        self.tool_revision = revision(self.bundle.encode("utf-8"))
        registered = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_register",
                                       "tool": "pep-c23-emitter", "document": self.tool_document,
                                       "revision": self.tool_revision, "function": "emit_c23"})
        self.assertEqual(registered.get("status"), "Registered", registered)
        sample = "fn main() -> Int { return 17 }"
        target = self._open(sample)
        parts = [
            "#include <stdio.h>\n", "int main(void) {\n",
            "  (void)printf(\"%lld\\n\", (long long)(", "17", "));\n",
            "  return 0;\n", "}\n",
        ]
        validated = self.client.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_validate",
            "tool": "pep-c23-emitter", "document": self.tool_document, "revision": self.tool_revision,
            "testVectors": [{
                "arguments": [], "expect": emission("emitted", parts),
                "semanticTarget": {"document": target["document"], "revision": target["revision"],
                                   "entryFunctions": []},
            }],
        })
        self.assertEqual(validated.get("status"), "Validated", validated)
        active = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_activate",
                                   "tool": "pep-c23-emitter", "document": self.tool_document,
                                   "revision": self.tool_revision})
        self.assertEqual(active.get("status"), "Active", active)

    def tearDown(self):
        self.client.close()

    def _open(self, source):
        return self.client.send({"schemaVersion": 3, "op": "open_bytes", "name": "a14-target",
                                 "bytes": list(source.encode("utf-8"))})

    def _emit(self, source):
        opened = self._open(source)
        self.assertEqual(opened.get("outcome"), "ok", opened)
        result = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                                   "tool": "pep-c23-emitter", "arguments": [],
                                   "semanticTarget": {"document": opened["document"],
                                                      "revision": opened["revision"],
                                                      "entryFunctions": []}})
        self.assertEqual(result.get("outcome"), "ok", result)
        self.assertEqual(result.get("revision"), self.tool_revision)
        return fields(result["result"])

    def _compile_and_run(self, source, expected):
        emitted = self._emit(source)
        self.assertEqual(scalar(emitted["status"]), "emitted", emitted)
        c_source = "".join(scalar(part) for part in emitted["sourceParts"]["value"])
        c_path = BUILD / "generated.c"
        c_path.write_text(c_source, encoding="utf-8", newline="\n")
        for compiler in (CLANG, GCC):
            with self.subTest(compiler=compiler.name, source=source):
                exe = BUILD / (compiler.stem + ".exe")
                built = subprocess.run(
                    [str(compiler), "-std=c23", "-Wall", "-Wextra", "-Wpedantic", "-Werror",
                     "-O2", str(c_path), "-o", str(exe)],
                    text=True, capture_output=True, check=False,
                )
                self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
                ran = subprocess.run([str(exe)], text=True, capture_output=True, check=False)
                self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
                self.assertEqual(ran.stdout, f"{expected}\n")

    def test_generated_c23_executes_source_backed_programs_under_clang_and_gcc(self):
        self.assertEqual(subprocess.run([str(CLANG), "--version"], text=True, capture_output=True).returncode, 0)
        self.assertEqual(subprocess.run([str(GCC), "--version"], text=True, capture_output=True).returncode, 0)
        for value in (0, 17, 2147483647):
            with self.subTest(value=value):
                self._compile_and_run(f"fn main() -> Int {{ return {value} }}", value)

    def test_unsupported_valid_program_is_reported_without_c_output(self):
        emitted = self._emit("fn main() -> Int { return 1 + 2 }")
        self.assertEqual(scalar(emitted["status"]), "unsupported")
        self.assertEqual(emitted["sourceParts"]["value"], [])
        self.assertNotEqual(scalar(emitted["diagnostic"]), "")

    def test_checker_invalid_program_is_not_emitted(self):
        emitted = self._emit("fn main() -> Int { return true }")
        self.assertEqual(scalar(emitted["status"]), "unsupported")
        self.assertEqual(emitted["sourceParts"]["value"], [])
        self.assertIn("valid Pep checker report", scalar(emitted["diagnostic"]))


if __name__ == "__main__":
    unittest.main()
