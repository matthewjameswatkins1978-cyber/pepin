import json
import os
import pathlib
import random
import copy
import subprocess
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PEP = ROOT / "pep.ps1"
LEXER = ROOT / "examples" / "pep_lexer.pep"
OCAML = ROOT / "pep_ocaml.ml"
BUILD = ROOT / "_build" / "a11"


def revision(raw):
    import hashlib
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def typed(kind, value):
    return {"type": kind, "value": value}


def typed_record(name, fields):
    return {"type": name, "fields": [{"name": key, "value": value} for key, value in fields]}


def typed_list(name, values):
    return {"type": f"List[{name}]", "value": values}


def record_fields(value):
    return {field["name"]: field["value"] for field in value["fields"]}


class JsonLineClient:
    def __init__(self, command, cwd, env=None):
        self.process = subprocess.Popen(
            command, cwd=cwd, env=env, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            encoding="utf-8", bufsize=1,
        )

    def send(self, request):
        request_line = json.dumps(request, ensure_ascii=False, separators=(",", ":")) + "\n"
        self.last_request_bytes = len(request_line.encode("utf-8"))
        self.process.stdin.write(request_line)
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            stderr = self.process.stderr.read()
            raise AssertionError(f"JSONL process ended without a response: {stderr}")
        self.last_response_bytes = len(line.encode("utf-8"))
        return json.loads(line)

    def close(self):
        if self.process.poll() is None:
            self.process.stdin.close()
            self.process.wait(timeout=30)
        stderr = self.process.stderr.read()
        self.process.stdout.close()
        self.process.stderr.close()
        if self.process.returncode != 0:
            raise AssertionError(f"JSONL process exited {self.process.returncode}: {stderr}")


ORACLE_SUFFIX = r'''
let oracle_token_json token =
  let kind, value = match token.kind with
    | Id name -> "identifier", json_string name
    | Number number -> "integer", json_string (Int64.to_string number)
    | Text text -> "string", json_string text
    | Hole None -> "hole", json_string ""
    | Hole (Some name) -> "hole", json_string name
    | Sym symbol -> "symbol", json_string symbol
    | Eof -> "eof", json_string ""
  in
  Printf.sprintf "{\"kind\":%s,\"value\":%s,\"startByte\":%d,\"endByte\":%d,\"line\":%d,\"column\":%d}"
    (json_string kind) value token.at.lo token.at.hi token.at.line token.at.column

let oracle_hex_decode input =
  if String.length input mod 2 <> 0 then failwith "odd hex input";
  String.init (String.length input / 2) (fun index ->
    Char.chr (int_of_string ("0x" ^ String.sub input (index * 2) 2)))

let oracle_one raw =
  try
    let tokens = lex raw |> Array.to_list |> List.map oracle_token_json |> String.concat "," in
    "{\"tokens\":[" ^ tokens ^ "],\"error\":null}"
  with Error diagnostic ->
    let span = diagnostic.at in
    Printf.sprintf
      "{\"tokens\":[],\"error\":{\"code\":%s,\"startByte\":%d,\"endByte\":%d,\"line\":%d,\"column\":%d}}"
      (json_string diagnostic.code) span.lo span.hi span.line span.column

let () =
  try while true do
    let line = input_line stdin in
    let raw = oracle_hex_decode line in
    print_endline (oracle_one raw);
    flush stdout
  done with End_of_file -> ()
'''


def normalized_lexer_result(tokens, error):
    if error:
        return {"tokens": [], "error": error}
    normalized = []
    for item in tokens:
        fields = record_fields(item)
        kind = fields["kind"]["value"]
        value = fields["text"]["value"]
        if kind == "integer":
            value = fields["integerValue"]["value"]
        elif kind == "string":
            value = "".join(part["value"] for part in fields["stringParts"]["value"])
        normalized.append({
            "kind": kind,
            "value": value,
            "startByte": int(fields["startByte"]["value"]),
            "endByte": int(fields["endByte"]["value"]),
            "line": int(fields["line"]["value"]),
            "column": int(fields["column"]["value"]),
        })
    return {"tokens": normalized, "error": None}


class A11DifferentialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        BUILD.mkdir(parents=True, exist_ok=True)
        source = OCAML.read_text(encoding="utf-8")
        main_marker = "\nlet () =\n"
        if source.count(main_marker) != 1:
            raise AssertionError("OCaml test oracle main marker is missing or ambiguous")
        helper_source = BUILD / "lexer_oracle.ml"
        helper_source.write_text(source.split(main_marker, 1)[0] + "\n" + ORACLE_SUFFIX, encoding="utf-8")
        cls.oracle_executable = BUILD / "lexer_oracle.exe"
        opam_root = os.environ.get("PEPIN_OPAM_ROOT", r"D:\opam-roots\pepin")
        build_env = os.environ.copy()
        build_env["PEPIN_OPAM_ROOT"] = opam_root
        compiled = subprocess.run(
            ["opam", "exec", "--root", opam_root, "--switch", "pepin-5.5.2", "--",
             "ocamlopt", "unix.cmxa", "-o", str(cls.oracle_executable), str(helper_source)],
            cwd=ROOT, env=build_env, text=True, capture_output=True, check=False,
        )
        if compiled.returncode != 0:
            raise AssertionError(f"Could not build test-only OCaml lexer oracle: {compiled.stderr}")
        cls.oracle_client = JsonLineClient([str(cls.oracle_executable)], ROOT, build_env)
        cls.lexer_source = LEXER.read_text(encoding="utf-8")
        cls.lexer_revision = revision(cls.lexer_source.encode("utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.oracle_client.close()

    def setUp(self):
        env = os.environ.copy()
        env["PEPIN_OPAM_ROOT"] = env.get("PEPIN_OPAM_ROOT", r"D:\opam-roots\pepin")
        session_started = time.perf_counter()
        self.session = JsonLineClient(
            ["pwsh", "-NoProfile", "-File", str(PEP), "session", "--jsonl"], ROOT, env,
        )
        self.session_start_ms = (time.perf_counter() - session_started) * 1000
        opened = self.session.send({"schemaVersion": 3, "op": "open", "name": "a11-lexer", "source": self.lexer_source})
        self.assertEqual(opened.get("outcome"), "ok", opened)
        self.lexer_document = opened["document"]
        self.lexer_revision = opened["revision"]
        empty = self.session.send({"schemaVersion": 3, "op": "open", "name": "empty", "source": ""})
        empty_revision = revision(b"")
        initial_cursor = self.cursor_value(empty["document"], empty_revision, "validate")
        registered = self.session.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_register",
            "tool": "lexer-start", "document": self.lexer_document, "revision": self.lexer_revision,
            "function": "lexer_start",
        })
        self.assertEqual(registered.get("outcome"), "ok", registered)
        validated = self.session.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_validate",
            "tool": "lexer-start", "document": self.lexer_document, "revision": self.lexer_revision,
            "testVectors": [{"arguments": [], "expect": initial_cursor,
                             "semanticTarget": {"document": empty["document"], "revision": empty_revision, "entryFunctions": []}}],
        })
        self.assertEqual(validated.get("status"), "Validated", validated)
        activated = self.session.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_activate",
            "tool": "lexer-start", "document": self.lexer_document, "revision": self.lexer_revision,
        })
        self.assertEqual(activated.get("status"), "Active", activated)

        registered = self.session.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_register",
            "tool": "lexer-step", "document": self.lexer_document, "revision": self.lexer_revision,
            "function": "lexer_step",
        })
        self.assertEqual(registered.get("outcome"), "ok", registered)
        scan_cursor = self.cursor_value(empty["document"], empty_revision, "scan")
        expected = self.progress_value(empty["document"], empty_revision, "valid", scan_cursor)
        validated = self.session.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_validate",
            "tool": "lexer-step", "document": self.lexer_document, "revision": self.lexer_revision,
            "testVectors": [{"arguments": [scan_cursor], "expect": expected,
                             "semanticTarget": {"document": empty["document"], "revision": empty_revision, "entryFunctions": []}}],
        })
        self.assertEqual(validated.get("status"), "Validated", validated)
        activated = self.session.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_activate",
            "tool": "lexer-step", "document": self.lexer_document, "revision": self.lexer_revision,
        })
        self.assertEqual(activated.get("status"), "Active", activated)

    @staticmethod
    def cursor_value(document, source_revision, stage, offset=0, line=1, column=1, mode=""):
        return typed_record("LexCursor", [
            ("document", typed("Str", document)), ("revision", typed("Str", source_revision)),
            ("status", typed("Str", "valid")), ("stage", typed("Str", stage)),
            ("offset", typed("Int", str(offset))), ("line", typed("Int", str(line))),
            ("column", typed("Int", str(column))), ("mode", typed("Str", mode)),
            ("tokenStart", typed("Int", "0")), ("tokenLine", typed("Int", "1")),
            ("tokenColumn", typed("Int", "1")), ("integerValue", typed("Int", "0")),
            ("integerOverflow", typed("Bool", False)), ("escapePending", typed("Bool", False)),
            ("stringPartStart", typed("Int", "0")), ("stringPartsReversed", typed_list("Str", [])),
        ])

    @classmethod
    def progress_value(cls, document, source_revision, status, cursor):
        eof = typed_record("LexToken", [
            ("kind", typed("Str", "eof")), ("text", typed("Str", "")),
            ("integerValue", typed("Int", "0")), ("stringParts", typed_list("Str", [])),
            ("startByte", typed("Int", "0")), ("endByte", typed("Int", "0")),
            ("line", typed("Int", "1")), ("column", typed("Int", "1")),
        ])
        done_cursor = cls.cursor_value(document, source_revision, "done")
        return typed_record("LexProgress", [
            ("document", typed("Str", document)), ("revision", typed("Str", source_revision)),
            ("status", typed("Str", status)), ("tokens", typed_list("LexToken", [eof])),
            ("cursor", done_cursor), ("done", typed("Bool", True)),
            ("errorCode", typed("Str", "")), ("errorStart", typed("Int", "0")),
            ("errorEnd", typed("Int", "0")), ("errorLine", typed("Int", "0")),
            ("errorColumn", typed("Int", "0")),
        ])

    def tearDown(self):
        self.session.close()

    def oracle(self, raw):
        return self.oracle_request(raw)

    @classmethod
    def oracle_request(cls, raw):
        cls.oracle_client.process.stdin.write(raw.hex() + "\n")
        cls.oracle_client.process.stdin.flush()
        line = cls.oracle_client.process.stdout.readline()
        if not line:
            raise AssertionError("OCaml lexer oracle ended without a response")
        return json.loads(line)

    def pep_lex(self, raw):
        open_started = time.perf_counter()
        opened = self.session.send({
            "schemaVersion": 3, "op": "open_bytes", "name": "lex-target", "bytes": list(raw),
        })
        open_ms = (time.perf_counter() - open_started) * 1000
        self.assertEqual(opened.get("outcome"), "ok", opened)
        target = {"document": opened["document"], "revision": opened["revision"], "entryFunctions": []}
        invoke_started = time.perf_counter()
        started = self.session.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
            "tool": "lexer-start", "arguments": [], "semanticTarget": target,
        })
        self.assertEqual(started.get("outcome"), "ok", started)
        self.assertEqual(started.get("revision"), self.lexer_revision)
        cursor = started["result"]
        tokens = []
        validation_ms = 0.0
        scan_ms = 0.0
        validation_calls = 0
        scan_calls = 0
        response_bytes = self.session.last_response_bytes
        for _ in range(3000):
            input_stage = record_fields(cursor)["stage"]["value"]
            call_started = time.perf_counter()
            response = self.session.send({
                "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                "tool": "lexer-step", "arguments": [cursor], "semanticTarget": target,
            })
            call_ms = (time.perf_counter() - call_started) * 1000
            self.assertEqual(response.get("outcome"), "ok", response)
            self.assertEqual(response.get("revision"), self.lexer_revision)
            response_bytes += self.session.last_response_bytes
            if input_stage == "validate":
                validation_ms += call_ms
                validation_calls += 1
            else:
                scan_ms += call_ms
                scan_calls += 1
            result = record_fields(response["result"])
            self.assertEqual(result["document"]["value"], target["document"])
            self.assertEqual(result["revision"]["value"], target["revision"])
            tokens.extend(result["tokens"]["value"])
            code = result["errorCode"]["value"]
            if not result["done"]["value"]:
                self.assertNotEqual(result["cursor"], cursor,
                                    f"lexer continuation made no progress on {raw.hex()}")
            if result["done"]["value"]:
                error = None
                if code:
                    error = {
                        "code": code,
                        "startByte": int(result["errorStart"]["value"]),
                        "endByte": int(result["errorEnd"]["value"]),
                        "line": int(result["errorLine"]["value"]),
                        "column": int(result["errorColumn"]["value"]),
                    }
                output = normalized_lexer_result(tokens, error)
                self.last_lex_metrics = {
                    "bytes": len(raw), "tokens": len(tokens),
                    "openMs": open_ms,
                    "invokeMs": (time.perf_counter() - invoke_started) * 1000,
                    "validateMs": validation_ms, "scanMs": scan_ms,
                    "validateCalls": validation_calls, "scanCalls": scan_calls,
                    "responseBytes": response_bytes,
                    "errorCode": error["code"] if error else "",
                }
                return output
            cursor = result["cursor"]
        self.fail("Pep lexer exceeded 3,000 resumptions without completion")

    def assert_differential(self, raw):
        self.assertEqual(self.pep_lex(raw), self.oracle(raw), raw.hex())

    def test_fixed_lexical_contract_corpus_matches_ocaml(self):
        fixed = [
            b"",
            b" \t\r\n# comment\r\n// another comment\n",
            b"fn type let var return if else while for in match true false Int Bool Str SourceBytes Unit List",
            b"_ _x ? ?name ?1 name2",
            b"(){}[],:;+-*/=.|&! <= == != && || -> =>",
            b"<",
            b"> >= %=",
            b"0 7 0010 9223372036854775807 -12",
            b"9223372036854775808",
            b"-9223372036854775808",
            b"\"\" \"plain Unicode \xf0\x9f\x98\x80\" \"a\\n\\r\\t\\0\\\\\\\"z\"",
            b"\"bad\\q\"",
            b"\"unterminated",
            b"\"trailing\\",
            b"\"line\nbreak\"",
            "# 😀\r\nlet x = 42 <= 43\n".encode("utf-8"),
            "é".encode("utf-8"),
            b"// comment with \xff\n",
            b"\xc0\x80",
            b"\xe2\x82",
            b"\xed\xa0\x80",
            b"\xf4\x90\x80\x80",
            b"A\xe2(\xa1",
            b"#\r\n?hole//tail\n",
            b"\"" + b"x" * 1024 + b"\"",
            b"\"" + b"\\n" * 256 + b"\"",
            b"word" * 1024,
            b"#" + b"comment-" * 512 + b"\r\n",
            b"+," * 512,
        ]
        for raw in fixed:
            with self.subTest(source=raw[:40]):
                self.assert_differential(raw)

    def test_deterministic_generated_and_truncated_inputs_match_ocaml(self):
        rng = random.Random(0xA11)
        fragments = [
            "alpha", "x9", "_", "?", "?slot", "7", "42", "<=", "==", "!=", "&&",
            "||", "->", "=>", "(", ")", "{", "}", "[", "]", ",", ":", ";", ".",
            "+", "-", "*", "/", "|", "&", "!", "#c\n", "//d\r\n", '"s\\n"', " ", "\r\n",
        ]
        generated = []
        for _ in range(60):
            generated.append("".join(rng.choice(fragments) for _ in range(rng.randint(1, 12))).encode("utf-8"))
        boundary_source = b"name123 ?slot <= 9223372036854775807 \"a\\n\" // tail\r\n"
        generated.extend(boundary_source[:end] for end in range(len(boundary_source) + 1))
        for raw in generated:
            with self.subTest(source=raw[:40]):
                self.assert_differential(raw)

    def test_repository_pep_examples_match_ocaml_reference(self):
        examples = [
            "point_sum.pep", "recursive_expr.pep", "a6_collections_control.pep",
            "unused_functions.pep", "lexer_fragment.pep", "pep_lexer.pep",
        ]
        for name in examples:
            raw = (ROOT / "examples" / name).read_bytes()
            with self.subTest(example=name, bytes=len(raw)):
                self.assert_differential(raw)

    def test_chunked_scan_is_revision_bound_and_has_forward_progress(self):
        raw = ("name " * 300 + '"' + "x" * 4096 + '"\r\n').encode("utf-8")
        opened = self.session.send({"schemaVersion": 3, "op": "open_bytes", "name": "large", "bytes": list(raw)})
        target = {"document": opened["document"], "revision": opened["revision"], "entryFunctions": []}
        started = self.session.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
            "tool": "lexer-start", "arguments": [], "semanticTarget": target,
        })
        cursor = started["result"]
        last_offset = -1
        count = 0
        started_at = time.perf_counter()
        for _ in range(3000):
            response = self.session.send({
                "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                "tool": "lexer-step", "arguments": [cursor], "semanticTarget": target,
            })
            self.assertEqual(response.get("outcome"), "ok", response)
            result = record_fields(response["result"])
            next_cursor = record_fields(result["cursor"])
            offset = int(next_cursor["offset"]["value"])
            stage = next_cursor["stage"]["value"]
            if not result["done"]["value"]:
                self.assertTrue(offset > last_offset or stage == "scan", (last_offset, offset, stage))
            last_offset = offset
            count += len(result["tokens"]["value"])
            if result["done"]["value"]:
                self.assertEqual(result["errorCode"]["value"], "")
                break
            cursor = result["cursor"]
        else:
            self.fail("chunked scanner did not finish")
        elapsed = time.perf_counter() - started_at
        self.assertEqual(count, 302)
        self.assertGreater(last_offset, 0)
        self.assertLess(elapsed, 60.0)

    def test_continuations_cannot_change_revision_or_escape_target_bounds(self):
        raw = b"name"
        opened = self.session.send({"schemaVersion": 3, "op": "open_bytes", "name": "cursor-target", "bytes": list(raw)})
        target = {"document": opened["document"], "revision": opened["revision"], "entryFunctions": []}
        started = self.session.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
            "tool": "lexer-start", "arguments": [], "semanticTarget": target,
        })
        original_cursor = started["result"]

        wrong_revision = copy.deepcopy(original_cursor)
        wrong_fields = {field["name"]: field for field in wrong_revision["fields"]}
        wrong_fields["revision"]["value"]["value"] = "sha256:" + "0" * 64
        rejected_cursor = self.session.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
            "tool": "lexer-step", "arguments": [wrong_revision], "semanticTarget": target,
        })
        self.assertEqual(record_fields(rejected_cursor["result"])["errorCode"]["value"], "PEP_LEXER_CURSOR_REVISION")

        out_of_range = copy.deepcopy(original_cursor)
        range_fields = {field["name"]: field for field in out_of_range["fields"]}
        range_fields["offset"]["value"]["value"] = str(len(raw) + 1)
        rejected_range = self.session.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
            "tool": "lexer-step", "arguments": [out_of_range], "semanticTarget": target,
        })
        self.assertEqual(record_fields(rejected_range["result"])["errorCode"]["value"], "PEP_LEXER_CURSOR_RANGE")

        unknown_revision = dict(target, revision="sha256:" + "0" * 64)
        unknown = self.session.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
            "tool": "lexer-start", "arguments": [], "semanticTarget": unknown_revision,
        })
        self.assertEqual(unknown["error"]["code"], "PEP_REVISION_NOT_FOUND")
        unauthorized = self.session.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
            "tool": "lexer-start", "arguments": [],
        })
        self.assertEqual(unauthorized["error"]["code"], "PEP_RUNTIME_SEMANTIC_CONTEXT")

        valid = self.session.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
            "tool": "lexer-step", "arguments": [original_cursor], "semanticTarget": target,
        })
        self.assertEqual(valid["outcome"], "ok", valid)
        next_cursor = record_fields(valid["result"])["cursor"]
        finished = self.session.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
            "tool": "lexer-step", "arguments": [next_cursor], "semanticTarget": target,
        })
        finished_fields = record_fields(finished["result"])
        self.assertTrue(finished_fields["done"]["value"])
        self.assertEqual([record_fields(item)["kind"]["value"] for item in finished_fields["tokens"]["value"]],
                         ["identifier", "eof"])

    def test_caller_made_cursors_are_not_validation_or_completion_proofs(self):
        invalid_raw = b"\xffname"
        opened = self.session.send({
            "schemaVersion": 3, "op": "open_bytes", "name": "forged-scan", "bytes": list(invalid_raw),
        })
        target = {"document": opened["document"], "revision": opened["revision"], "entryFunctions": []}
        forged_scan = self.cursor_value(
            target["document"], target["revision"], "scan", offset=1, line=1, column=2,
        )
        scanned = self.session.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
            "tool": "lexer-step", "arguments": [forged_scan], "semanticTarget": target,
        })
        scanned_fields = record_fields(scanned["result"])
        self.assertTrue(scanned_fields["done"]["value"])
        self.assertEqual(scanned_fields["errorCode"]["value"], "")
        self.assertEqual(
            [record_fields(item)["kind"]["value"] for item in scanned_fields["tokens"]["value"]],
            ["identifier", "eof"],
        )

        valid_raw = b"name"
        valid_opened = self.session.send({
            "schemaVersion": 3, "op": "open_bytes", "name": "forged-done", "bytes": list(valid_raw),
        })
        valid_target = {
            "document": valid_opened["document"],
            "revision": valid_opened["revision"],
            "entryFunctions": [],
        }
        forged_done = self.cursor_value(valid_target["document"], valid_target["revision"], "done")
        skipped = self.session.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
            "tool": "lexer-step", "arguments": [forged_done], "semanticTarget": valid_target,
        })
        skipped_fields = record_fields(skipped["result"])
        self.assertTrue(skipped_fields["done"]["value"])
        self.assertEqual(skipped_fields["errorCode"]["value"], "")
        self.assertEqual(skipped_fields["tokens"]["value"], [])

    def test_32_byte_boundary_fixtures_match_ocaml_and_progress(self):
        fixtures = [
            ("utf8 scalar crosses work edge", b" " * 30 + b'"\xf0\x9f\x98\x80"'),
            ("malformed continuation at edge", b" " * 30 + b"\xe2(\xa1"),
            ("truncated scalar at edge", b" " * 31 + b"\xe2\x82"),
            ("two-byte operator crosses edge", b" " * 31 + b"=="),
            ("named hole crosses edge", b" " * 30 + b"?slot name"),
            ("identifier begins at edge", b" " * 31 + b"alpha"),
            ("escape payload begins after edge", b" " * 27 + b'"abc\\n"'),
            ("closing quote after edge", b" " * 30 + b'"x"'),
            ("unterminated string crosses edge", b" " * 31 + b'"open' + b"x" * 40),
            ("maximum integer crosses edge", b" " * 29 + b"9223372036854775807 "),
            ("overflow integer crosses edge", b" " * 29 + b"9223372036854775808 "),
            ("comment LF after edge", b"#" + b"x" * 31 + b"\nname"),
            ("comment CRLF crosses edge", b"#" + b"x" * 30 + b"\r\nname"),
            ("EOF exactly at work edge", b" " * 31 + b"x"),
        ]
        for label, raw in fixtures:
            with self.subTest(boundary=label, length=len(raw)):
                self.assert_differential(raw)


if __name__ == "__main__":
    unittest.main()
