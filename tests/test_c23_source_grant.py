"""Native entry grants: deterministic host adapter, no ambient source access."""
import hashlib
import json
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from pep_c23_direct import C23Emitter, run_pep_cmd
from pep_c23_grant import NativeSourceGrant
from tests.test_a10 import invoke_session, request, revision, scalar


def target(raw, document="doc-2"):
    return {"document": document, "revision": "sha256:" + hashlib.sha256(raw).hexdigest(),
            "entryFunctions": [], "sourceGrant": {"mode": "entry-parameter"}}


def expr(ty, kind, **fields):
    return {"type": ty, "expression": {"kind": kind, **fields}}


def probe_report(operation="byte_at", *, ambient=False):
    source = (expr("SourceBytes", "call", name="source_bytes", arguments=[]) if ambient
              else expr("SourceBytes", "binding", bindingId=1))
    args = [source]
    if operation == "byte_at":
        args.append(expr("Int", "int", value=0))
    function = {"functionId": 1, "name": "main", "returnType": "Int",
                "parameters": [{"name": "source", "type": "SourceBytes", "bindingId": 1}],
                "body": [{"kind": "return", "value": expr("Int", "call", name=operation, arguments=args)}]}
    return {"schemaVersion": 2, "status": "valid", "holes": [], "diagnostics": [], "ast": [],
            "typedTree": {"types": [], "statements": [], "functions": [function]}}


class NativeSourceGrantTests(unittest.TestCase):
    def run_c(self, source):
        compilers = [p for name in ("gcc", "clang") if (p := shutil.which(name))]
        if not compilers:
            self.skipTest("No C23 compiler")
        with tempfile.TemporaryDirectory() as directory:
            c_file = pathlib.Path(directory) / "grant.c"
            c_file.write_text(source, encoding="utf-8")
            for compiler in compilers:
                exe = c_file.with_suffix(".exe")
                build = subprocess.run([compiler, "-std=c23", "-pedantic-errors", "-O2",
                                        str(c_file), "-o", str(exe)], capture_output=True, text=True, timeout=30)
                self.assertEqual(build.returncode, 0, build.stderr)
                result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=10)
                yield compiler, (result.returncode, result.stdout, result.stderr)

    def test_exact_bytes_and_deterministic_entry(self):
        for raw, expected in ((b"\x00\r\n", 0), (b"\xff", 255), (b"\xc3\xa9", 195)):
            with self.subTest(raw=raw):
                grant = NativeSourceGrant.bind(target(raw), "doc-2", raw)
                generated = C23Emitter(probe_report()).generate_c23(source_grant=grant)
                self.assertEqual(generated, C23Emitter(probe_report()).generate_c23(source_grant=grant))
                for compiler, result in self.run_c(generated):
                    with self.subTest(compiler=compiler):
                        self.assertEqual(result, (0, f"{expected}\n", ""))

    def test_empty_and_maximum_source_length(self):
        for raw in (b"", b"\x00" * 65536):
            with self.subTest(length=len(raw)):
                grant = NativeSourceGrant.bind(target(raw), "doc-2", raw)
                source = C23Emitter(probe_report("byte_length")).generate_c23(source_grant=grant)
                for compiler, result in self.run_c(source):
                    with self.subTest(compiler=compiler):
                        self.assertEqual(result, (0, f"{len(raw)}\n", ""))

    def test_refuses_missing_stale_foreign_or_oversize_grant(self):
        raw = b"A"
        for selected, doc, retained in (
            ({k: v for k, v in target(raw).items() if k != "sourceGrant"}, "doc-2", raw),
            (target(raw) | {"sourceGrant": {"mode": "ambient"}}, "doc-2", raw),
            (target(raw), "doc-3", raw),
            (target(raw), "doc-2", b"B"),
            (target(raw), "doc-2", bytearray(raw)),
            (target(b"X" * 65537), "doc-2", b"X" * 65537),
        ):
            with self.subTest(doc=doc, length=len(retained)):
                with self.assertRaises(ValueError):
                    NativeSourceGrant.bind(selected, doc, retained)

    def test_no_ambient_or_implicit_grant(self):
        grant = NativeSourceGrant.bind(target(b"A"), "doc-2", b"A")
        with self.assertRaisesRegex(ValueError, "without parameters"):
            C23Emitter(probe_report()).generate_c23()
        with self.assertRaisesRegex(ValueError, "source_bytes"):
            C23Emitter(probe_report(ambient=True)).generate_c23(source_grant=grant)
        wrong = probe_report()
        wrong["typedTree"]["functions"][0]["parameters"][0]["type"] = "Int"
        with self.assertRaisesRegex(ValueError, "main\\(source: SourceBytes\\)"):
            C23Emitter(wrong).generate_c23(source_grant=grant)

    @unittest.skipUnless(shutil.which("pwsh"), "real seed CLI requires PowerShell")
    def test_entry_bytes_match_host_authorised_seed(self):
        tool = "fn probe() -> Int { return byte_at(source_bytes(), 0) }\n"
        raw = b"\xff\x00"
        def semantic_target(data, doc):
            return {k: v for k, v in target(data, doc).items() if k != "sourceGrant"}
        tool_ref = {"tool": "probe", "document": "doc-1", "revision": revision(tool)}
        result = invoke_session([
            request("open", source=tool), request("open_bytes", bytes=[65]),
            request("tool_register", function="probe", **tool_ref),
            request("tool_validate", **tool_ref, testVectors=[{
                "arguments": [], "expect": scalar("Int", "65"),
                "semanticTarget": semantic_target(b"A", "doc-2")}]),
            request("tool_activate", **tool_ref), request("open_bytes", bytes=list(raw)),
            request("tool_invoke", tool="probe", arguments=[], semanticTarget=semantic_target(raw, "doc-3")),
        ])
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = json.loads(result.stdout.splitlines()[-1])["result"]["value"]
        with tempfile.TemporaryDirectory() as directory:
            source = pathlib.Path(directory) / "entry.pep"
            source.write_text("fn main(source: SourceBytes) -> Int { return byte_at(source, 0) }\n", encoding="utf-8")
            code, output, error = run_pep_cmd("check", str(source), "--json")
            self.assertEqual(code, 0, error or output)
            grant = NativeSourceGrant.bind(target(raw, "doc-3"), "doc-3", raw)
            generated = C23Emitter(json.loads(output)).generate_c23(source_grant=grant)
            for compiler, receipt in self.run_c(generated):
                with self.subTest(compiler=compiler):
                    self.assertEqual(receipt, (0, expected + "\n", ""))
