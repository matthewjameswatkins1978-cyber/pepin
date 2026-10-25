import hashlib
import json
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PEP = ROOT / "pep.ps1"


def invoke(*args):
    return subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(PEP), *map(str, args)],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )


def invoke_session(requests):
    payload = "\n".join(json.dumps(item, ensure_ascii=False) for item in requests) + "\n"
    return subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(PEP), "session", "--jsonl"],
        cwd=ROOT, text=True, input=payload, capture_output=True, check=False,
    )


class PepCliTests(unittest.TestCase):
    def test_session_revision_hash_matches_sha256_for_multiblock_source(self):
        source = 'say("x")\n' * 12
        result = invoke_session([{"schemaVersion": 3, "op": "open", "source": source}])
        self.assertEqual(result.returncode, 0, result.stderr)
        opened = json.loads(result.stdout)
        self.assertEqual(opened["revision"], "sha256:" + hashlib.sha256(source.encode()).hexdigest())

    def test_session_revisions_queries_and_analysis_cache(self):
        source = 'fn double(n: Int) -> Int { return ?calculation }\n'
        opened, query_a, query_b, metrics = [
            {"schemaVersion": 3, "op": "open", "name": "example", "source": source},
            {"schemaVersion": 3, "op": "query", "document": "doc-1", "revision": "REVISION"},
            {"schemaVersion": 3, "op": "query", "document": "doc-1", "revision": "REVISION"},
            {"schemaVersion": 3, "op": "metrics"},
        ]
        revision = "sha256:" + hashlib.sha256(source.encode()).hexdigest()
        query_a["revision"] = revision
        query_b["revision"] = revision
        result = invoke_session([opened, query_a, query_b, metrics])
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(responses[0]["revision"], revision)
        self.assertEqual(responses[1], responses[2])
        for key in ("status", "ast", "typedTree", "holes", "diagnostics"):
            self.assertEqual(responses[0][key], responses[1][key])
        self.assertEqual(responses[1]["status"], "incomplete")
        hole = responses[1]["holes"][0]
        self.assertEqual(hole["expectedType"], "Int")
        self.assertEqual(hole["identity"]["revision"], revision)
        self.assertGreaterEqual(responses[3]["metrics"]["cache_hits"], 2)
        self.assertEqual(responses[3]["metrics"]["parse_count"], 1)
        self.assertEqual(responses[3]["metrics"]["typecheck_count"], 1)

    def test_session_edit_preserves_old_revision_and_rejects_stale_edit(self):
        source = "let value: Int = ?todo\n"
        original_file = self.source(source)
        original_bytes = original_file.read_bytes()
        revision = "sha256:" + hashlib.sha256(source.encode()).hexdigest()
        requests = [
            {"schemaVersion": 3, "op": "open", "source": source},
            {"schemaVersion": 3, "op": "apply_edit", "document": "doc-1", "expected_revision": revision,
             "start_byte": source.index("?todo"), "end_byte": source.index("?todo") + 5, "replacement": "1"},
            {"schemaVersion": 3, "op": "query", "document": "doc-1", "revision": revision},
            {"schemaVersion": 3, "op": "apply_edit", "document": "doc-1", "expected_revision": revision,
             "start_byte": 0, "end_byte": 0, "replacement": " "},
            {"schemaVersion": 3, "op": "query", "document": "doc-1", "revision": "sha256:" + hashlib.sha256(b"let value: Int = 1\n").hexdigest()},
        ]
        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        opened, edited, old, stale, current = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(opened["revision"], revision)
        self.assertNotEqual(edited["revision"], revision)
        self.assertEqual(old["status"], "incomplete")
        self.assertEqual(len(old["holes"]), 1)
        self.assertEqual(stale["error"]["code"], "PEP_STALE_REVISION")
        self.assertEqual(stale["currentRevision"], edited["revision"])
        self.assertEqual(current["status"], "valid")
        fresh = json.loads(invoke("check", self.source("let value: Int = 1\n"), "--json").stdout)
        self.assertEqual(current["typedTree"], fresh["typedTree"])
        self.assertEqual(original_file.read_bytes(), original_bytes)

    def test_session_edit_validates_byte_ranges_and_utf8_boundaries(self):
        source = 'say("é")\n'
        revision = "sha256:" + hashlib.sha256(source.encode()).hexdigest()
        start = source.encode().index("é".encode())
        requests = [
            {"schemaVersion": 3, "op": "open", "source": source},
            {"schemaVersion": 3, "op": "apply_edit", "document": "doc-1", "expected_revision": revision,
             "start_byte": start + 1, "end_byte": start + 2, "replacement": "x"},
            {"schemaVersion": 3, "op": "apply_edit", "document": "doc-1", "expected_revision": revision,
             "start_byte": -1, "end_byte": 0, "replacement": ""},
            {"schemaVersion": 3, "op": "metrics"},
        ]
        responses = [json.loads(line) for line in invoke_session(requests).stdout.splitlines()]
        self.assertEqual(responses[1]["error"]["code"], "PEP_UTF8_BOUNDARY")
        self.assertEqual(responses[2]["error"]["code"], "PEP_INVALID_EDIT_RANGE")
        self.assertEqual(responses[3]["metrics"]["parse_count"], 1)

    def test_session_malformed_json_does_not_end_process(self):
        payload = "{not json}\n" + json.dumps({"schemaVersion": 3, "op": "open", "source": 'say("ok")\n'}) + "\n"
        result = subprocess.run(["pwsh", "-NoProfile", "-File", str(PEP), "session", "--jsonl"],
                                cwd=ROOT, text=True, input=payload, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(responses), 2)
        self.assertEqual(responses[0]["error"]["code"], "PEP_SESSION_MALFORMED_JSON")
        self.assertEqual(responses[1]["status"], "valid")

    def test_session_keeps_lf_and_crlf_offsets_in_original_bytes(self):
        sources = ['let greeting: Str = "café"\n?x\n', 'let greeting: Str = "café"\r\n?x\r\n']
        requests = [{"schemaVersion": 3, "op": "open", "source": source} for source in sources]
        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        holes = [response["holes"][0] for response in responses]
        self.assertEqual([hole["span"]["start"]["line"] for hole in holes], [2, 2])
        self.assertEqual(holes[1]["span"]["start"]["offset"] - holes[0]["span"]["start"]["offset"], 1)

    def test_session_new_revision_reports_type_errors_then_validity(self):
        source = 'fn amount(seed: Int) -> Int { return ?answer }\n'
        revision = "sha256:" + hashlib.sha256(source.encode()).hexdigest()
        hole = source.index("?answer")
        requests = [
            {"schemaVersion": 3, "op": "open", "source": source},
            {"schemaVersion": 3, "op": "apply_edit", "document": "doc-1", "expected_revision": revision,
             "start_byte": hole, "end_byte": hole + len("?answer"), "replacement": '"bad"'},
        ]
        invalid_source = source.replace("?answer", '"bad"')
        invalid_revision = "sha256:" + hashlib.sha256(invalid_source.encode()).hexdigest()
        requests.extend([
            {"schemaVersion": 3, "op": "query", "document": "doc-1", "revision": invalid_revision},
            {"schemaVersion": 3, "op": "apply_edit", "document": "doc-1", "expected_revision": invalid_revision,
             "start_byte": hole, "end_byte": hole + len('"bad"'), "replacement": "seed"},
        ])
        valid_source = source.replace("?answer", "seed")
        valid_revision = "sha256:" + hashlib.sha256(valid_source.encode()).hexdigest()
        requests.append({"schemaVersion": 3, "op": "query", "document": "doc-1", "revision": valid_revision})
        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        opened, invalid_edit, invalid, valid_edit, valid = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(opened["status"], "incomplete")
        self.assertNotEqual(invalid_edit["revision"], revision)
        self.assertEqual(invalid["status"], "invalid")
        self.assertEqual(invalid["diagnostics"][0]["code"], "PEP_TYPE_MISMATCH")
        self.assertEqual(valid_edit["status"], "valid")
        self.assertEqual(valid["status"], "valid")

    def test_session_edit_before_function_recalculates_spans(self):
        source = 'fn f(n: Int) -> Int { return ?x }\n'
        revision = "sha256:" + hashlib.sha256(source.encode()).hexdigest()
        requests = [
            {"schemaVersion": 3, "op": "open", "source": source},
            {"schemaVersion": 3, "op": "apply_edit", "document": "doc-1", "expected_revision": revision,
             "start_byte": 0, "end_byte": 0, "replacement": "\n"},
        ]
        edited = source[:0] + "\n" + source
        new_revision = "sha256:" + hashlib.sha256(edited.encode()).hexdigest()
        requests.append({"schemaVersion": 3, "op": "query", "document": "doc-1", "revision": new_revision})
        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        opened, updated, queried = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(opened["holes"][0]["span"]["start"]["line"], 1)
        self.assertEqual(updated["holes"][0]["span"]["start"]["line"], 2)
        self.assertEqual(queried["holes"], updated["holes"])
        self.assertEqual(queried["revision"], updated["revision"])

    def test_help_lists_supported_commands(self):
        result = invoke("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("query FILE --holes --json", result.stdout)
        self.assertIn("run FILE", result.stdout)
        self.assertIn("session --jsonl", result.stdout)

    def source(self, text):
        temp = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".pep", delete=False, newline="")
        temp.write(text)
        temp.close()
        path = pathlib.Path(temp.name)
        self.addCleanup(path.unlink, missing_ok=True)
        return path

    def test_complete_typed_program_runs(self):
        path = self.source(
            'fn greet(name: Str) -> Str { return name }\n'
            'say(greet("Pep"))\n'
        )
        result = invoke("run", path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "Pep\n")

    def test_inspect_returns_source_spanned_ast(self):
        result = invoke("inspect", "examples/hello.pep", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        ast = json.loads(result.stdout)["ast"]
        self.assertEqual(ast[0]["kind"], "expression")
        self.assertEqual(ast[0]["value"]["kind"], "call")
        self.assertEqual(ast[0]["span"]["start"]["line"], 1)
        self.assertGreater(ast[0]["span"]["endOffset"], 0)

    def test_hole_reports_expected_type_bindings_and_action(self):
        path = self.source(
            'let label: Str = "ready"\n'
            'let seed: Int = 1\n'
            'let count: Int = ?\n'
        )
        result = invoke("check", path, "--json")
        self.assertEqual(result.returncode, 1)
        response = json.loads(result.stdout)
        self.assertEqual(response["status"], "incomplete")
        hole = response["holes"][0]
        self.assertEqual(hole["expectedType"], "Int")
        self.assertEqual(
            [(binding["name"], binding["type"]) for binding in hole["bindings"]],
            [("seed", "Int"), ("label", "Str")],
        )
        action = hole["actions"][0]
        self.assertEqual(action["kind"], "fill_hole")
        self.assertEqual([candidate["name"] for candidate in action["candidates"]], ["seed"])
        self.assertEqual(hole["span"]["start"]["line"], 3)

    def test_unconstrained_hole_does_not_claim_an_expected_type(self):
        path = self.source('let label: Str = "ready"\n?\n')
        result = invoke("check", path, "--json")
        self.assertEqual(result.returncode, 1)
        response = json.loads(result.stdout)
        self.assertEqual(response["status"], "incomplete")
        hole = response["holes"][0]
        self.assertIsNone(hole["expectedType"])
        self.assertEqual(hole["bindings"][0]["name"], "label")
        self.assertEqual(hole["actions"], [])

    def test_function_hole_query_reports_return_type_and_parameter_scope(self):
        source = 'fn greet(name: Str) -> Str { return ? }\n'
        path = self.source(source)
        result = invoke("query", path, "--holes", "--json", "--offset", source.index("?"))
        self.assertEqual(result.returncode, 0, result.stderr)
        response = json.loads(result.stdout)
        self.assertEqual(response["status"], "incomplete")
        self.assertEqual(len(response["holes"]), 1)
        hole = response["holes"][0]
        self.assertEqual(hole["scope"], "greet")
        self.assertEqual(hole["expectedType"], "Str")
        self.assertEqual([binding["name"] for binding in hole["bindings"]], ["name"])

    def test_type_mismatch_is_structured(self):
        path = self.source('let count: Int = "wrong"\n')
        result = invoke("check", path, "--json")
        self.assertEqual(result.returncode, 1)
        diagnostic = json.loads(result.stdout)["diagnostics"][0]
        self.assertEqual(diagnostic["code"], "PEP_TYPE_MISMATCH")
        self.assertIn("Expected Int", diagnostic["message"])

    def test_describe_reports_seed_and_supported_types(self):
        result = invoke("describe", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        description = json.loads(result.stdout)
        self.assertEqual(description["language"], "Pep")
        self.assertEqual(description["schemaVersion"], 2)
        self.assertEqual(description["types"], ["Int", "Bool", "Str", "Unit"])
        self.assertIn("query_holes", description["features"])
        self.assertIn("jsonl_session", description["features"])
        self.assertEqual(description["session"]["schemaVersion"], 3)
        self.assertFalse(description["session"]["crossRevisionReuse"])


    def test_recursive_factorial_runs(self):
        source = 'fn factorial(n: Int) -> Int {\n return if n <= 1 { 1 } else { n * factorial(n - 1) }\n}\nsay(int_text(factorial(6)))\n'
        result = invoke("run", self.source(source))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "720\n")

    def test_multiple_parameters_locals_and_lexical_shadowing(self):
        source = 'fn total(a: Int, b: Int, scale: Int) -> Int {\n let sum: Int = a + b\n { let sum: Int = 99 }\n return sum * scale\n}\nsay(int_text(total(2, 3, 4)))\n'
        result = invoke("run", self.source(source))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "20\n")

    def test_call_argument_hole_infers_parameter_type(self):
        source = 'fn square(n: Int) -> Int { return n * n }\nlet result: Int = square(?input)\n'
        result = invoke("query", self.source(source), "--holes", "--json")
        self.assertEqual(result.returncode, 0)
        hole = json.loads(result.stdout)["holes"][0]
        self.assertEqual(hole["identity"], "input")
        self.assertEqual(hole["expectedType"], "Int")

    def test_unannotated_binding_hole_is_explicitly_unconstrained(self):
        result = invoke("check", self.source("let value = ?unknown\n"), "--json")
        body = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(body["status"], "incomplete")
        self.assertIsNone(body["holes"][0]["expectedType"])

    def test_function_hole_candidates_use_visible_binding_types(self):
        source = 'fn f(label: Str, seed: Int) -> Int {\n let count: Int = ?\n return count\n}\n'
        result = invoke("query", self.source(source), "--holes", "--json")
        hole = json.loads(result.stdout)["holes"][0]
        self.assertEqual([x["name"] for x in hole["actions"][0]["candidates"]], ["seed"])
        self.assertEqual([x["name"] for x in hole["bindings"]], ["label", "seed"])

    def test_function_and_scope_failures_are_structured(self):
        cases = [
            ('say(int_text(missing(1)))\n', "PEP_UNKNOWN_FUNCTION"),
            ('fn f(n: Int) -> Int { return n } let x: Int = f("bad")\n', "PEP_TYPE_MISMATCH"),
            ('let old_name: String = "legacy"\n', "PEP_PARSE_TYPE"),
            ('fn f() -> Int { return "bad" }\n', "PEP_TYPE_MISMATCH"),
            ('fn f() -> Int { let x: Int = 1 }\n', "PEP_MISSING_RETURN"),
            ('fn f() -> Int { return absent }\n', "PEP_UNKNOWN_VARIABLE"),
            ('fn f() -> Int { let x: Int = 1 let x: Int = 2 return x }\n', "PEP_DUPLICATE_BINDING"),
            ('fn f() -> Int { { let inner: Int = 2 } return inner }\n', "PEP_UNKNOWN_VARIABLE"),
            ('fn f(x: Int, x: Int) -> Int { return x }\n', "PEP_DUPLICATE_PARAMETER"),
        ]
        for source, code in cases:
            with self.subTest(code=code):
                result = invoke("check", self.source(source), "--json")
                self.assertEqual(result.returncode, 1)
                self.assertEqual(json.loads(result.stdout)["diagnostics"][0]["code"], code)

    def test_hole_in_unreferenced_function_prevents_any_execution(self):
        source = 'fn unused() -> Int { return ?todo }\nsay("must not run")\n'
        result = invoke("run", self.source(source))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")

    def test_lf_and_crlf_preserve_semantics_and_original_offsets(self):
        source = "fn f(n: Int) -> Int {\n return ?x\n}\n"
        paths = [self.source(source), self.source(source.replace("\n", "\r\n"))]
        results = [invoke("query", path, "--holes", "--json") for path in paths]
        self.assertEqual([x.returncode for x in results], [0, 0])
        holes = [json.loads(x.stdout)["holes"][0] for x in results]
        self.assertEqual(holes[0]["expectedType"], holes[1]["expectedType"])
        self.assertEqual(holes[0]["span"]["start"]["line"], holes[1]["span"]["start"]["line"])
        self.assertEqual(holes[0]["span"]["start"]["column"], holes[1]["span"]["start"]["column"])
        self.assertNotEqual(holes[0]["span"]["start"]["offset"], holes[1]["span"]["start"]["offset"])

    def test_integer_overflow_and_division_by_zero_are_controlled(self):
        cases = [
            ("say(int_text(9223372036854775807 + 1))\n", "PEP_RUNTIME_OVERFLOW"),
            ("say(int_text(8 / 0))\n", "PEP_RUNTIME_DIVISION_BY_ZERO"),
        ]
        for source, code in cases:
            with self.subTest(code=code):
                result = invoke("run", self.source(source), "--json")
                self.assertEqual(result.returncode, 1)
                self.assertEqual(json.loads(result.stdout)["diagnostics"][0]["code"], code)

    def test_query_is_deterministic_and_accepts_source_offset(self):
        path = self.source("fn f(n: Int) -> Int { return ?x }\n")
        first = invoke("query", path, "--holes", "--json")
        second = invoke("query", path, "--holes", "--json")
        self.assertEqual(first.stdout, second.stdout)
        hole = json.loads(first.stdout)["holes"][0]
        selected = invoke("query", path, "--holes", "--json", "--offset", str(hole["span"]["start"]["offset"]))
        self.assertEqual(json.loads(selected.stdout)["holes"], [hole])

    def test_invalid_syntax_and_reserved_builtin_names_do_not_crash(self):
        malformed = invoke("check", self.source("fn broken(n: Int -> Int { return n }\n"), "--json")
        reserved = invoke("check", self.source("fn say(x: Int) -> Int { return x }\n"), "--json")
        self.assertEqual(json.loads(malformed.stdout)["status"], "invalid")
        self.assertEqual(json.loads(reserved.stdout)["diagnostics"][0]["code"], "PEP_RESERVED_FUNCTION")

if __name__ == "__main__":
    unittest.main(verbosity=2)
