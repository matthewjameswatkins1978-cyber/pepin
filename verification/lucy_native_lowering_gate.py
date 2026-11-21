#!/usr/bin/env python3
"""Native C23 authority and lowering acceptance gate (explicitly run).

The checked-IR fixtures isolate the native emitter from the seed compiler;
the driver tests substitute only its check invocation, then build real C.
When pwsh is installed, the source cases additionally use real seed check
and run. No fixture is claimed to be captured compiler output.
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pep_c23_direct as native


def expr(ty, kind, **fields):
    return {"type": ty, "expression": {"kind": kind, **fields}}


def number(value):
    return expr("Int", "int", value=value)


def call(ty, name, *args, fid=None):
    return expr(ty, "call", name=name, functionId=fid, arguments=list(args))


def say(text):
    return call("Unit", "say", expr("Str", "string", value=text))


def print_int(value):
    return {"kind": "expression", "value": call("Unit", "say", call("Str", "int_text", value))}


def binding(ty, bid):
    return expr(ty, "binding", bindingId=bid)


def let(ty, bid, value):
    return {"kind": "let", "type": ty, "bindingId": bid, "name": f"v{bid}", "value": value}


def checked(statements, *, types=(), functions=()):
    return {"schemaVersion": 2, "status": "valid", "ast": [], "holes": [], "diagnostics": [],
            "typedTree": {"types": list(types), "functions": list(functions),
                          "statements": list(statements)}}


def record_case(field_name):
    decl = {"kind": "record", "typeId": 1, "name": "Box", "fields": [
        {"fieldId": 1, "name": field_name, "type": "Int"}]}
    value = expr("Box", "record", typeId=1, fields=[{"fieldId": 1, "value": number(42)}])
    field = expr("Int", "field_access", fieldId=1, value=binding("Box", 1))
    return checked([let("Box", 1, value), print_int(field)], types=[decl])


def union_case(ctor_name):
    decl = {"kind": "union", "typeId": 1, "name": "Choice", "variants": [
        {"constructorId": 1, "name": ctor_name, "arguments": ["Int"]}]}
    value = expr("Choice", "constructor", typeId=1, constructorId=1,
                 name=ctor_name, arguments=[number(42)])
    pat = {"kind": "constructor", "constructorId": 1, "arguments": [
        {"kind": "binding", "bindingId": 2, "name": "n", "type": "Int"}]}
    matched = expr("Int", "match", value=binding("Choice", 1), arms=[
        {"pattern": pat, "result": binding("Int", 2)}])
    return checked([let("Choice", 1, value), print_int(matched)], types=[decl])


def unit_binding_case():
    # Unit is a genuine checked scalar; its evaluation may have an effect.
    return checked([let("Unit", 1, say("first")), print_int(number(42))])


def unit_argument_case():
    fn = {"functionId": 1, "name": "accept", "returnType": "Int",
          "parameters": [{"name": "u", "bindingId": 1, "type": "Unit"}],
          "body": [{"kind": "return", "value": number(42)}]}
    return checked([print_int(call("Int", "accept", say("first"), fid=1))], functions=[fn])


class NativeLoweringGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compilers = [pathlib.Path(path) for name in ("gcc", "clang")
                         if (path := shutil.which(name))]
        if not cls.compilers:
            raise unittest.SkipTest("No GCC/Clang C23 compiler available")

    def assert_native_output(self, report, expected):
        source = native.C23Emitter(report).generate_c23()
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            c_file = root / "fixture.c"
            c_file.write_text(source, encoding="utf-8")
            for compiler in self.compilers:
                with self.subTest(compiler=compiler):
                    exe = root / "fixture.exe"
                    compiled = subprocess.run([str(compiler), "-std=c23", "-pedantic-errors",
                                               "-O2", str(c_file), "-o", str(exe)],
                                              capture_output=True, text=True, timeout=30)
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    ran = subprocess.run([str(exe)], capture_output=True, text=True, timeout=10)
                    self.assertEqual((ran.returncode, ran.stdout, ran.stderr), (0, expected, ""))

    def test_ordinary_record_and_union_controls(self):
        self.assert_native_output(record_case("value"), "42\n")
        self.assert_native_output(union_case("Some"), "42\n")

    def test_record_fields_do_not_inherit_c23_keywords(self):
        for field in ("switch", "bool", "nullptr"):
            with self.subTest(field=field):
                self.assert_native_output(record_case(field), "42\n")

    def test_union_payload_names_do_not_inherit_c23_keywords(self):
        for ctor in ("switch", "bool", "nullptr"):
            with self.subTest(constructor=ctor):
                self.assert_native_output(union_case(ctor), "42\n")

    def test_unit_statement_control(self):
        self.assert_native_output(checked([{"kind": "expression", "value": say("first")},
                                           print_int(number(42))]), "first\n42\n")

    def test_unit_binding_preserves_effects(self):
        self.assert_native_output(unit_binding_case(), "first\n42\n")

    def test_unit_argument_preserves_effects(self):
        self.assert_native_output(unit_argument_case(), "first\n42\n")

    def drive(self, code, report, *, accepted, expected="42\n"):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            pep, output = root / "fixture.pep", root / "fixture.exe"
            pep.write_text('say("42")\n' if expected else "", encoding="utf-8")
            # The process exit and report are controlled; the native compiler,
            # filesystem and generated executable remain real.
            with patch.object(native, "run_pep_cmd", return_value=(code, json.dumps(report), "")):
                try:
                    native.build_c23(pep, output, self.compilers[0])
                except (RuntimeError, ValueError) as exc:
                    if accepted:
                        self.fail(str(exc))
                else:
                    if not accepted:
                        self.fail(f"untrusted check result built {output.exists()=}, {output.with_suffix('.c').exists()=}")
            if accepted:
                ran = subprocess.run([str(output)], capture_output=True, text=True, timeout=10)
                self.assertEqual((ran.returncode, ran.stdout, ran.stderr), (0, expected, ""))
            else:
                self.assertFalse(output.exists())
                self.assertFalse(output.with_suffix(".c").exists())

    def test_valid_and_invalid_check_controls(self):
        self.drive(0, checked([print_int(number(42))]), accepted=True)
        self.drive(0, checked([]), accepted=True, expected="")
        self.drive(1, {"schemaVersion": 2, "status": "invalid", "diagnostics": []}, accepted=False)
        self.drive(0, checked([]) | {"status": "incomplete"}, accepted=False)

    def test_nonzero_check_cannot_build_even_with_valid_json(self):
        self.drive(17, checked([print_int(number(42))]), accepted=False)

    def test_missing_or_partial_typed_tree_cannot_build(self):
        report = checked([])
        no_tree = {key: value for key, value in report.items() if key != "typedTree"}
        for malformed in (no_tree, report | {"typedTree": {}},
                          report | {"typedTree": {"types": [], "functions": []}}):
            with self.subTest(report=malformed):
                self.drive(0, malformed, accepted=False)

    @unittest.skipUnless(shutil.which("pwsh"), "real seed CLI requires PowerShell")
    def test_real_seed_source_differential(self):
        examples = (
            ("type Box { switch: Int }\nlet x = Box { switch: 42 }\nsay(int_text(x.switch))\n", "42\n"),
            ("type Choice = switch(Int)\nlet x = switch(42)\nsay(int_text(match x { switch(n) => n }))\n", "42\n"),
            ('let u: Unit = say("first")\nsay(int_text(42))\n', "first\n42\n"),
            ('fn accept(u: Unit) -> Int { return 42 }\nsay(int_text(accept(say("first"))))\n', "first\n42\n"),
        )
        with tempfile.TemporaryDirectory() as directory:
            for i, (source, expected) in enumerate(examples):
                with self.subTest(source=source):
                    pep = pathlib.Path(directory) / f"case_{i}.pep"
                    pep.write_text(source, encoding="utf-8")
                    code, stdout, stderr = native.run_pep_cmd("check", str(pep), "--json")
                    self.assertEqual(code, 0, stderr)
                    report = json.loads(stdout)
                    self.assertEqual(report["status"], "valid", report)
                    self.assertEqual(native.run_pep_cmd("run", str(pep)), (0, expected, ""))
                    self.assert_native_output(report, expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
