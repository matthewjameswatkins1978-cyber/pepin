"""stdlib/c_init.pep: scanned integers rendered as C initializer text, then compiled and run.

This is the stdlib lane's first native evidence. The Pep code produces the declaration from a
SourceBytes document; the harness supplies a driver, compiles the pair under strict Clang and GCC, and
executes it. The expected value is computed by Pep's own `scan_int_sum` on the same document, so the
comparison is Pep-scanning versus native execution of Pep-generated C, not versus a hand-written guess.

Interpreted coverage lives in tests.test_scan and tests.test_text_builder; this file is host-context
only because `source_bytes()` needs a v2 semantic target.
"""

import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, typed, typed_record_value  # noqa: E402

MODULES = ["stdlib/text_builder.pep", "stdlib/scan.pep", "stdlib/c_init.pep"]

PROBES = """
fn c_int_array_probe(name: Str, nameBytes: Int) -> CArrayInit {
  return c_int_array(name, nameBytes, source_bytes())
}

fn scan_sum_probe() -> ScanSum {
  return scan_int_sum(source_bytes())
}
"""


def array_record(status, diagnostic, count):
    return typed_record_value("CArrayInit", [
        ("status", typed("Str", status)),
        ("diagnostic", typed("Str", diagnostic)),
        ("count", typed("Int", str(count))),
        ("parts", {"type": "List[Str]", "value": []}),
    ])


DRIVER = """
#include <stdio.h>
int main(void) {
  int64_t total = 0;
  for (size_t index = 0; index < sizeof(pep_values) / sizeof(pep_values[0]); ++index) {
    total += pep_values[index];
  }
  printf("%lld\\n", (long long)total);
  return 0;
}
"""


class CInitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = Session()
        module = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in MODULES) + PROBES
        opened = cls.session.send({"schemaVersion": 3, "op": "open", "source": module,
                                   "name": "pep-c-init", "metadataOnly": True})
        require(opened, "outcome", "ok", "open c_init module")
        require(opened, "status", "valid", "check c_init module")
        cls.document = opened["document"]
        cls.revision = opened["revision"]
        cls.temp = tempfile.TemporaryDirectory(prefix="pep-c-init-")
        sample = cls.session.send({"schemaVersion": 3, "op": "open_bytes", "name": "validate", "bytes": []})
        require(sample, "outcome", "ok", "open validation source")
        cls.target_spec = {"document": sample["document"], "revision": sample["revision"],
                           "entryFunctions": []}
        cls._register("pep-c-array", "c_int_array_probe",
                      [typed("Str", "pep_values"), typed("Int", "11")],
                      array_record("unsupported",
                                   "Pep C array initializer needs at least one integer", 0))
        cls._register("pep-scan-sum", "scan_sum_probe", [],
                      typed_record_value("ScanSum", [
                          ("status", typed("Str", "ok")),
                          ("diagnostic", typed("Str", "")),
                          ("count", typed("Int", "0")),
                          ("total", typed("Int", "0")),
                      ]))

    @classmethod
    def _register(cls, tool, function, arguments, expect):
        registered = cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                       "op": "tool_register", "tool": tool,
                                       "document": cls.document, "revision": cls.revision,
                                       "function": function})
        require(registered, "status", "Registered", f"register {tool}")
        validated = cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_validate", "tool": tool,
                                      "document": cls.document, "revision": cls.revision,
                                      "testVectors": [{"arguments": arguments, "expect": expect,
                                                       "semanticTarget": cls.target_spec}]})
        require(validated, "status", "Validated", f"validate {tool}")
        activated = cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_activate", "tool": tool,
                                      "document": cls.document, "revision": cls.revision})
        require(activated, "status", "Active", f"activate {tool}")

    @classmethod
    def tearDownClass(cls):
        cls.session.close()
        cls.temp.cleanup()

    def _invoke(self, tool, payload, arguments):
        raw = payload.encode("utf-8")
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                    "name": f"payload-{len(raw)}", "bytes": list(raw)})
        require(target, "outcome", "ok", "open payload")
        response = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_invoke", "tool": tool,
                                      "arguments": arguments,
                                      "semanticTarget": {"document": target["document"],
                                                         "revision": target["revision"],
                                                         "entryFunctions": []}})
        require(response, "outcome", "ok", f"invoke {tool}")
        return {item["name"]: item["value"] for item in response["result"]["fields"]}

    def _declaration(self, payload):
        fields = self._invoke("pep-c-array", payload,
                              [typed("Str", "pep_values"), typed("Int", "11")])
        return fields["status"]["value"], int(fields["count"]["value"]), \
            [part["value"] for part in fields["parts"]["value"]]

    def _pep_sum(self, payload):
        fields = self._invoke("pep-scan-sum", payload, [])
        return fields["status"]["value"], int(fields["total"]["value"])

    def test_generated_initializer_compiles_and_runs_under_clang_and_gcc(self):
        payload = "19 23 7\n"
        status, count, parts = self._declaration(payload)
        self.assertEqual(status, "ok")
        self.assertEqual(count, 3)
        text = "".join(parts)
        self.assertEqual(text, "static const int64_t pep_values[] = { 19, 23, 7, };")

        pep_status, pep_total = self._pep_sum(payload)
        self.assertEqual(pep_status, "ok")
        self.assertEqual(pep_total, 49)

        compilers = [name for name in ("clang", "gcc") if shutil.which(name)]
        if not compilers:
            self.skipTest("no C23 compiler on PATH")
        source = pathlib.Path(self.temp.name) / "generated.c"
        source.write_text("#include <stdint.h>\n#include <stdio.h>\n" + text + "\n" + DRIVER,
                          encoding="utf-8", newline="\n")
        for name in compilers:
            with self.subTest(compiler=name):
                executable = pathlib.Path(self.temp.name) / f"generated-{name}.exe"
                built = subprocess.run([shutil.which(name), "-std=c23", "-Wall", "-Wextra",
                                        "-Wpedantic", "-Werror", "-O2", str(source),
                                        "-o", str(executable)],
                                       text=True, capture_output=True, check=False)
                self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
                ran = subprocess.run([str(executable)], text=True, capture_output=True, check=False)
                self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
                self.assertEqual(ran.stdout, f"{pep_total}\n",
                                 "native execution of Pep-generated C must match Pep's own scan")

    def test_empty_document_is_refused_not_emitted(self):
        status, count, parts = self._declaration("   \n")
        self.assertEqual(status, "unsupported")
        self.assertEqual(count, 0)
        self.assertEqual(parts, [])

    def test_non_digit_document_refuses_and_keeps_the_partial_count(self):
        status, count, parts = self._declaration("1 2 x")
        self.assertEqual(status, "unsupported")
        self.assertEqual(count, 2, "the count reports how far scanning got")
        self.assertEqual(parts, [], "a refused declaration emits no text at all")


if __name__ == "__main__":
    unittest.main()
