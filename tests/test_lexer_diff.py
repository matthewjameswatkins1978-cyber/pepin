"""Three-way differential for the Pep-written lexer (PEP-A2-SUSTAINED-013 slice 4).

Legs compared on identical payloads:

1. `stdlib/scan.pep` `lex_source` -- this branch's source-backed driver.
2. `examples/pep_lexer.pep` -- the existing canonical lexer, driven through its cooperative
   `lexer_start` / `lexer_step` continuation and concatenated token chunks.
3. The OCaml seed (`pep.exe check --json`) -- production authority for accept/reject and exact
   diagnostic code / span / line / column on INVALID programs, and status valid|incomplete on
   valid ones (incomplete only where the program contains deliberate holes).

Token equality is field-for-field on the canonical LexToken shape: kind, text, integerValue,
stringParts, startByte, endByte, line, column -- including ordered NUL fragments inside strings.
"""

import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, typed, typed_record_value  # noqa: E402

SCAN = ROOT / "stdlib" / "scan.pep"
CANONICAL = ROOT / "examples" / "pep_lexer.pep"
SEED_EXE = ROOT / "_build" / "ocaml" / "pep.exe"
SEED_PROBE = ROOT / "_build" / "diff_seed_probe.pep"

MY_PROBE = """
fn lex_probe() -> LexResult {
  return lex_source(source_bytes())
}
"""

# Drives the canonical cooperative lexer to completion, concatenating each step's token chunk in
# order (chunks are already forward-order; make_progress returns reverse(tokens) of the step).
CANONICAL_PROBE = """
type CanonResult {
  status: Str,
  errorCode: Str,
  errorStart: Int,
  errorEnd: Int,
  errorLine: Int,
  errorColumn: Int,
  tokens: List[LexToken]
}

fn canonical_probe() -> CanonResult {
  var cursor = lexer_start()
  var tokens: List[LexToken] = []
  var errorCode = ""
  var errorStart = -1
  var errorEnd = -1
  var errorLine = -1
  var errorColumn = -1
  var status = "ok"
  var done = false
  while !done {
    let progress = lexer_step(cursor)
    cursor = progress.cursor
    for token in progress.tokens {
      tokens = append(tokens, token)
    }
    if progress.errorCode != "" {
      errorCode = progress.errorCode
      errorStart = progress.errorStart
      errorEnd = progress.errorEnd
      errorLine = progress.errorLine
      errorColumn = progress.errorColumn
      status = "error"
    } else {}
    done = progress.done
  }
  return CanonResult { status: status, errorCode: errorCode, errorStart: errorStart,
    errorEnd: errorEnd, errorLine: errorLine, errorColumn: errorColumn, tokens: tokens }
}
"""

EOF_TOKEN = typed_record_value("LexToken", [
    ("kind", typed("Str", "eof")),
    ("text", typed("Str", "")),
    ("integerValue", typed("Int", "0")),
    ("stringParts", {"type": "List[Str]", "value": []}),
    ("startByte", typed("Int", "0")),
    ("endByte", typed("Int", "0")),
    ("line", typed("Int", "1")),
    ("column", typed("Int", "1")),
])

MY_EXPECT = typed_record_value("LexResult", [
    ("status", typed("Str", "ok")),
    ("errorCode", typed("Str", "")),
    ("sourceBytes", typed("Int", "0")),
    ("errorStart", typed("Int", "-1")),
    ("errorEnd", typed("Int", "-1")),
    ("errorLine", typed("Int", "-1")),
    ("errorColumn", typed("Int", "-1")),
    ("tokens", {"type": "List[LexToken]", "value": [EOF_TOKEN]}),
])

CANON_EXPECT = typed_record_value("CanonResult", [
    ("status", typed("Str", "ok")),
    ("errorCode", typed("Str", "")),
    ("errorStart", typed("Int", "-1")),
    ("errorEnd", typed("Int", "-1")),
    ("errorLine", typed("Int", "-1")),
    ("errorColumn", typed("Int", "-1")),
    ("tokens", {"type": "List[LexToken]", "value": [EOF_TOKEN]}),
])

VALID_CORPUS = [
    "",
    "let a = 1;",
    "fn f(x: Int) -> Int {\n  return x + 2; // tail comment\n}\n",
    'let s = "a\\n\\t\\\\\\""; let t = "x\\0y";',
    "let h: Int = ?; let k = ?named; let u = _;",
    "let b = (1 <= 2) && (3 != 4) || !(5 == 6);",
    'let a = "é中"; # é comment\nlet b = 6 / 2;',
    "let a = 1;\r\nlet b = 2;\r\n",
    "let b = 2",
    "let x = -1 + 2 * 3 / 4;",
    "let y = [1, 2, 3];\n\n# done",
]

INVALID_CORPUS = [
    b"@",
    b'"abc',
    b'"a\nb"',
    b'"bad\\q"',
    b"99999999999999999999",
    "let a = 1 < 2;".encode("utf-8"),
    "let a = 1 > 2;".encode("utf-8"),
    b"let a = [1, 2, \x80];",
    b"let a = 1; @ trailing",
    b'let s = "partial"; "unterminated',
]


def seed_check(payload):
    """Run the OCaml seed on the exact bytes; return verdict plus first diagnostic span."""
    if not SEED_EXE.exists():
        subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                        "-File", str(ROOT / "pep.ps1"), "describe"],
                       capture_output=True, check=True, timeout=300)
    SEED_PROBE.write_bytes(payload)
    proc = subprocess.run([str(SEED_EXE), "check", str(SEED_PROBE), "--json"],
                          capture_output=True, text=True, timeout=120)
    document = json.loads(proc.stdout.strip().splitlines()[-1])
    verdict = {"status": document.get("status"), "code": None, "start": None, "end": None,
               "line": None, "column": None}
    diagnostics = document.get("diagnostics") or []
    if diagnostics:
        first = diagnostics[0]
        verdict["code"] = first["code"]
        verdict["start"] = first["span"]["start"]["offset"]
        verdict["end"] = first["span"]["endOffset"]
        verdict["line"] = first["span"]["start"]["line"]
        verdict["column"] = first["span"]["start"]["column"]
    return verdict


class LexerDifferentialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mine = Session()
        opened = cls.mine.send({"schemaVersion": 3, "op": "open",
                                "source": SCAN.read_text(encoding="utf-8") + MY_PROBE,
                                "name": "pep-lex-diff", "metadataOnly": True})
        require(opened, "outcome", "ok", "open scan module")
        require(opened, "status", "valid", "check scan module")
        cls.mine_document = opened["document"]
        cls.mine_revision = opened["revision"]

        cls.canon = Session()
        opened = cls.canon.send({"schemaVersion": 3, "op": "open",
                                 "source": CANONICAL.read_text(encoding="utf-8") + CANONICAL_PROBE,
                                 "name": "pep-canon-diff", "metadataOnly": True})
        require(opened, "outcome", "ok", "open canonical lexer")
        require(opened, "status", "valid", "check canonical lexer")
        cls.canon_document = opened["document"]
        cls.canon_revision = opened["revision"]

        # Each session validates against ITS OWN sample document: identity is per-session.
        sample = cls.mine.send({"schemaVersion": 3, "op": "open_bytes",
                                "name": "validate", "bytes": []})
        cls.mine_target = {"document": sample["document"], "revision": sample["revision"],
                           "entryFunctions": []}
        sample = cls.canon.send({"schemaVersion": 3, "op": "open_bytes",
                                 "name": "validate", "bytes": []})
        cls.canon_target = {"document": sample["document"], "revision": sample["revision"],
                            "entryFunctions": []}
        cls._register(cls.mine, "pep-lex-diff-tool", "lex_probe",
                      cls.mine_document, cls.mine_revision, MY_EXPECT, cls.mine_target)
        cls._register(cls.canon, "pep-canon-diff-tool", "canonical_probe",
                      cls.canon_document, cls.canon_revision, CANON_EXPECT, cls.canon_target)

    @classmethod
    def _register(cls, session, tool, function, document, revision, expect, target_spec):
        registered = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                   "op": "tool_register", "tool": tool, "document": document,
                                   "revision": revision, "function": function})
        require(registered, "status", "Registered", f"register {tool}")
        validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                  "op": "tool_validate", "tool": tool, "document": document,
                                  "revision": revision,
                                  "testVectors": [{"arguments": [], "expect": expect,
                                                   "semanticTarget": target_spec}]})
        require(validated, "status", "Validated", f"validate {tool}")
        activated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                  "op": "tool_activate", "tool": tool, "document": document,
                                  "revision": revision})
        require(activated, "status", "Active", f"activate {tool}")

    @classmethod
    def tearDownClass(cls):
        cls.mine.close()
        cls.canon.close()

    def _invoke_tokens(self, session, tool, document, revision, payload):
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        target = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": f"payload-{len(payload)}", "bytes": list(payload)})
        require(target, "outcome", "ok", "open payload")
        response = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                 "op": "tool_invoke", "tool": tool,
                                 "arguments": [],
                                 "semanticTarget": {"document": target["document"],
                                                    "revision": target["revision"],
                                                    "entryFunctions": []}})
        require(response, "outcome", "ok", f"invoke {tool}")
        fields = {item["name"]: item["value"] for item in response["result"]["fields"]}
        tokens = []
        for item in fields["tokens"]["value"]:
            entry = {field["name"]: field["value"] for field in item["fields"]}
            tokens.append((entry["kind"]["value"], entry["text"]["value"],
                           int(entry["integerValue"]["value"]),
                           tuple(part["value"] for part in entry["stringParts"]["value"]),
                           int(entry["startByte"]["value"]), int(entry["endByte"]["value"]),
                           int(entry["line"]["value"]), int(entry["column"]["value"])))
        return {
            "status": fields["status"]["value"],
            "errorCode": fields["errorCode"]["value"],
            "errorStart": int(fields["errorStart"]["value"]),
            "errorEnd": int(fields["errorEnd"]["value"]),
            "errorLine": int(fields["errorLine"]["value"]),
            "errorColumn": int(fields["errorColumn"]["value"]),
            "tokens": tokens,
        }

    def _mine(self, payload):
        return self._invoke_tokens(self.mine, "pep-lex-diff-tool",
                                   self.mine_document, self.mine_revision, payload)

    def _canon(self, payload):
        return self._invoke_tokens(self.canon, "pep-canon-diff-tool",
                                   self.canon_document, self.canon_revision, payload)

    def test_valid_corpus_is_token_identical_to_the_canonical_lexer(self):
        for payload in VALID_CORPUS:
            with self.subTest(payload=payload):
                mine, canon = self._mine(payload), self._canon(payload)
                self.assertEqual(mine["tokens"], canon["tokens"])
                self.assertEqual((mine["status"], mine["errorCode"]),
                                 (canon["status"], canon["errorCode"]))
                self.assertEqual((mine["errorStart"], mine["errorEnd"],
                                  mine["errorLine"], mine["errorColumn"]),
                                 (canon["errorStart"], canon["errorEnd"],
                                  canon["errorLine"], canon["errorColumn"]))

    def test_valid_corpus_is_accepted_by_the_ocaml_seed(self):
        for payload in VALID_CORPUS:
            with self.subTest(payload=payload):
                verdict = seed_check(payload.encode("utf-8"))
                self.assertIn(verdict["status"], ("valid", "incomplete"),
                              f"seed rejected a corpus program: {verdict}")

    def test_invalid_corpus_error_parity_three_ways(self):
        for payload in INVALID_CORPUS:
            with self.subTest(payload=payload):
                mine, canon = self._mine(payload), self._canon(payload)
                verdict = seed_check(payload)
                self.assertEqual(mine["tokens"], canon["tokens"],
                                 "partial token streams must agree too")
                self.assertEqual(mine["errorCode"], canon["errorCode"])
                self.assertEqual(verdict["code"], mine["errorCode"],
                                 f"seed says {verdict}, driver says {mine}")
                self.assertEqual(verdict["start"], mine["errorStart"])
                self.assertEqual(verdict["line"], mine["errorLine"])
                self.assertEqual(verdict["column"], mine["errorColumn"])
                self.assertEqual(verdict["end"], mine["errorEnd"],
                                 "errorEnd must match the seed's span end")

    def test_invalid_corpus_canonical_positions_track_the_seed(self):
        """The reference lexer is held to the same seed spans; a divergence here is a finding
        about the canonical lexer or the wrapper, not something to paper over."""
        for payload in INVALID_CORPUS:
            with self.subTest(payload=payload):
                canon = self._canon(payload)
                verdict = seed_check(payload)
                self.assertEqual(verdict["code"], canon["errorCode"])
                self.assertEqual((verdict["start"], verdict["line"], verdict["column"]),
                                 (canon["errorStart"], canon["errorLine"], canon["errorColumn"]))


if __name__ == "__main__":
    unittest.main()