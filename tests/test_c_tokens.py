"""stdlib/c_tokens.pep: one pass, both scanners, counts rendered as C and executed natively.

The point of this slice is composition: the same document drives integer scanning and identifier
scanning, and the counts become a C table that strict Clang and GCC compile and run. The Pep-side
counts and the native output must agree, so a scanner that miscounts cannot pass by producing
plausible text.
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

MODULES = ["stdlib/scan.pep", "stdlib/c_tokens.pep"]

PROBES = """
fn c_token_counts_probe(name: Str, nameBytes: Int) -> CTokenCounts {
  return c_token_counts(name, nameBytes, source_bytes())
}
"""

DRIVER = """
int main(void) {
  printf("%lld\\n", (long long)pep_counts[0]);
  printf("%lld\\n", (long long)pep_counts[1]);
  return 0;
}
"""


def refusal_record():
    return typed_record_value("CTokenCounts", [
        ("status", typed("Str", "unsupported")),
        ("diagnostic", typed("Str", "Pep C token counts need at least one token")),
        ("identifiers", typed("Int", "0")),
        ("integers", typed("Int", "0")),
        ("parts", {"type": "List[Str]", "value": []}),
    ])


class CTokenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = Session()
        module = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in MODULES) + PROBES
        opened = cls.session.send({"schemaVersion": 3, "op": "open", "source": module,
                                   "name": "pep-c-tokens", "metadataOnly": True})
        require(opened, "outcome", "ok", "open c_tokens module")
        require(opened, "status", "valid", "check c_tokens module")
        cls.document = opened["document"]
        cls.revision = opened["revision"]
        cls.temp = tempfile.TemporaryDirectory(prefix="pep-c-tokens-")
        sample = cls.session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": "validate", "bytes": []})
        require(sample, "outcome", "ok", "open validation source")
        cls.target_spec = {"document": sample["document"], "revision": sample["revision"],
                           "entryFunctions": []}
        cls._register()

    @classmethod
    def _register(cls):
        registered = cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                       "op": "tool_register", "tool": "pep-c-token-counts",
                                       "document": cls.document, "revision": cls.revision,
                                       "function": "c_token_counts_probe"})
        require(registered, "status", "Registered", "register token counts")
        validated = cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_validate", "tool": "pep-c-token-counts",
                                      "document": cls.document, "revision": cls.revision,
                                      "testVectors": [{
                                          "arguments": [typed("Str", "pep_counts"), typed("Int", "10")],
                                          "expect": refusal_record(),
                                          "semanticTarget": cls.target_spec}]})
        require(validated, "status", "Validated", "validate token counts")
        activated = cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_activate", "tool": "pep-c-token-counts",
                                      "document": cls.document, "revision": cls.revision})
        require(activated, "status", "Active", "activate token counts")

    @classmethod
    def tearDownClass(cls):
        cls.session.close()
        cls.temp.cleanup()

    def _counts(self, payload):
        raw = payload.encode("utf-8")
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                    "name": f"payload-{len(raw)}", "bytes": list(raw)})
        require(target, "outcome", "ok", "open payload")
        response = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_invoke", "tool": "pep-c-token-counts",
                                      "arguments": [typed("Str", "pep_counts"), typed("Int", "10")],
                                      "semanticTarget": {"document": target["document"],
                                                         "revision": target["revision"],
                                                         "entryFunctions": []}})
        require(response, "outcome", "ok", "invoke token counts")
        fields = {item["name"]: item["value"] for item in response["result"]["fields"]}
        return {
            "status": fields["status"]["value"],
            "diagnostic": fields["diagnostic"]["value"],
            "identifiers": int(fields["identifiers"]["value"]),
            "integers": int(fields["integers"]["value"]),
            "parts": [part["value"] for part in fields["parts"]["value"]],
        }

    def test_one_pass_counts_both_kinds_and_the_table_executes(self):
        payload = "alpha beta_2 12 34 gamma\n"
        counts = self._counts(payload)
        self.assertEqual(counts["status"], "ok", counts["diagnostic"])
        self.assertEqual((counts["identifiers"], counts["integers"]), (3, 2))
        text = "".join(counts["parts"])
        self.assertEqual(text, "static const int64_t pep_counts[] = { 3, 2, };")

        compilers = [name for name in ("clang", "gcc") if shutil.which(name)]
        if not compilers:
            self.skipTest("no C23 compiler on PATH")
        source = pathlib.Path(self.temp.name) / "counts.c"
        source.write_text("#include <stdint.h>\n#include <stdio.h>\n" + text + "\n" + DRIVER,
                          encoding="utf-8", newline="\n")
        for name in compilers:
            with self.subTest(compiler=name):
                executable = pathlib.Path(self.temp.name) / f"counts-{name}.exe"
                built = subprocess.run([shutil.which(name), "-std=c23", "-Wall", "-Wextra",
                                        "-Wpedantic", "-Werror", "-O2", str(source),
                                        "-o", str(executable)],
                                       text=True, capture_output=True, check=False)
                self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
                ran = subprocess.run([str(executable)], text=True, capture_output=True, check=False)
                self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
                self.assertEqual(ran.stdout, f"{counts['identifiers']}\n{counts['integers']}\n",
                                 "native execution must reproduce the Pep-side counts")

    def test_punctuation_refuses_with_the_offset_and_no_table(self):
        counts = self._counts("alpha $beta")
        self.assertEqual(counts["status"], "unsupported")
        self.assertEqual((counts["identifiers"], counts["integers"]), (1, 0),
                         "counts report how far the scan got")
        self.assertEqual(counts["parts"], [], "a refused table emits no text at all")

    def test_whitespace_only_document_is_refused(self):
        counts = self._counts("  \n\t ")
        self.assertEqual(counts["status"], "unsupported")
        self.assertEqual(counts["parts"], [])


if __name__ == "__main__":
    unittest.main()
