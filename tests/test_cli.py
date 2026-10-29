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
    @staticmethod
    def tool_request(op, **fields):
        return {"schemaVersion": 3, "toolProtocolVersion": 1, "op": op, **fields}

    def test_tool_registry_validates_activates_invokes_and_hot_replaces(self):
        source = "fn calculate_fee(amount: Int) -> Int { return amount + 2 }\n"
        revision1 = "sha256:" + hashlib.sha256(source.encode()).hexdigest()
        source2 = source.replace("+ 2", "+ 3")
        revision2 = "sha256:" + hashlib.sha256(source2.encode()).hexdigest()
        source3 = source2.replace("amount + 3", '"bad"')
        revision3 = "sha256:" + hashlib.sha256(source3.encode()).hexdigest()
        source4 = 'fn calculate_fee(amount: Str) -> Int { return 23 }\n'
        revision4 = "sha256:" + hashlib.sha256(source4.encode()).hexdigest()
        requests = [
            {"schemaVersion": 3, "op": "open", "source": source},
            self.tool_request("tool_register", tool="fee", document="doc-1", revision=revision1,
                              function="calculate_fee", description="Calculate the fee"),
            self.tool_request("tool_validate", tool="fee", document="doc-1", revision=revision1,
                              testVectors=[{"arguments":[{"type":"Int","value":"20"}],
                                            "expect":{"type":"Int","value":"22"}}]),
            self.tool_request("tool_activate", tool="fee", document="doc-1", revision=revision1),
            self.tool_request("tool_list"),
            self.tool_request("tool_invoke", tool="fee", arguments=[{"type":"Int","value":"20"}]),
            {"schemaVersion":3,"op":"apply_edit","document":"doc-1","expected_revision":revision1,
             "start_byte":source.index("+ 2"),"end_byte":source.index("+ 2")+3,"replacement":"+ 3"},
            self.tool_request("tool_register", tool="fee", document="doc-1", revision=revision2,
                              function="calculate_fee", description="Calculate the fee"),
            self.tool_request("tool_validate", tool="fee", document="doc-1", revision=revision2,
                              testVectors=[{"arguments":[{"type":"Int","value":"20"}],
                                            "expect":{"type":"Int","value":"23"}}]),
            self.tool_request("tool_activate", tool="fee", document="doc-1", revision=revision2),
            self.tool_request("tool_list"),
            self.tool_request("tool_invoke", tool="fee", arguments=[{"type":"Int","value":"20"}]),
            {"schemaVersion":3,"op":"open","source":source3},
            self.tool_request("tool_register", tool="fee", document="doc-2", revision=revision3,
                              function="calculate_fee", description="Invalid replacement"),
            self.tool_request("tool_validate", tool="fee", document="doc-2", revision=revision3,
                              testVectors=[{"arguments":[{"type":"Int","value":"20"}],
                                            "expect":{"type":"Int","value":"23"}}]),
            self.tool_request("tool_list"),
            self.tool_request("tool_invoke", tool="fee", arguments=[{"type":"Int","value":"20"}]),
            self.tool_request("tool_invoke", tool="fee", arguments=[{"type":"Str","value":"20"}]),
            self.tool_request("tool_invoke", tool="fee", arguments=[]),
            self.tool_request("tool_invoke", tool="fee", arguments=[{"type":"Int","value":"0x14"}]),
            {"schemaVersion":3,"op":"open","source":source4},
            self.tool_request("tool_register",tool="fee",document="doc-3",revision=revision4,function="calculate_fee"),
            self.tool_request("tool_validate",tool="fee",document="doc-3",revision=revision4,
                              testVectors=[{"arguments":[{"type":"Str","value":"20"}],"expect":{"type":"Int","value":"23"}}]),
            self.tool_request("tool_list"),
            self.tool_request("tool_invoke",tool="fee",arguments=[{"type":"Int","value":"20"}]),
        ]
        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(responses), len(requests))
        self.assertEqual(responses[1]["status"], "Registered")
        self.assertEqual(responses[1]["signature"], {"parameters":["Int"],"returns":"Int"})
        self.assertEqual(responses[2]["status"], "Validated")
        self.assertEqual(responses[3]["status"], "Active")
        self.assertTrue(responses[4]["tools"][0]["callable"])
        self.assertEqual(responses[5]["result"], {"type":"Int","value":"22"})
        self.assertEqual(responses[8]["status"], "Validated")
        self.assertEqual(responses[9]["status"], "Active")
        listed_statuses = {tool["status"] for tool in responses[10]["tools"]}
        self.assertEqual(listed_statuses, {"Superseded", "Active"})
        self.assertEqual(responses[11]["result"], {"type":"Int","value":"23"})
        self.assertEqual(responses[12]["revision"], revision3)
        self.assertEqual(responses[13]["status"], "Rejected")
        self.assertEqual(responses[14]["status"], "Rejected")
        self.assertEqual([tool["status"] for tool in responses[15]["tools"]].count("Active"), 1)
        self.assertTrue(all(not tool["callable"] for tool in responses[15]["tools"] if tool["status"] == "Rejected"))
        self.assertEqual(responses[16]["result"], {"type":"Int","value":"23"})
        self.assertEqual(responses[17]["error"]["code"], "PEP_TOOL_ARGUMENT_TYPE")
        self.assertEqual(responses[18]["error"]["code"], "PEP_TOOL_ARGUMENT_COUNT")
        self.assertEqual(responses[19]["error"]["code"], "PEP_TOOL_INTEGER_FORMAT")
        self.assertEqual(responses[22]["status"], "Rejected")
        self.assertIn("incompatible", responses[22]["error"])
        self.assertEqual([tool["status"] for tool in responses[23]["tools"]].count("Active"), 1)
        self.assertTrue(all(tool["activeRevision"] == revision2 for tool in responses[23]["tools"]))
        self.assertEqual(responses[24]["result"], {"type":"Int","value":"23"})

    def test_tool_validation_rejects_incomplete_unsupported_effectful_and_over_budget_functions(self):
        source = (
            'fn direct() -> Int { say("blocked"); return 1 }\n'
            'fn helper() -> Int { say("blocked"); return 1 }\n'
            'fn transitive() -> Int { return helper() }\n'
            'type Box { value: Int }\n'
            'fn unsupported(box: Box) -> Int { return box.value }\n'
            'fn fib(n: Int) -> Int { return if n <= 1 { n } else { fib(n - 1) + fib(n - 2) } }\n'
            'fn deep(n: Int) -> Int { return deep(n + 1) }\n'
        )
        revision = "sha256:" + hashlib.sha256(source.encode()).hexdigest()
        requests = [{"schemaVersion":3,"op":"open","source":source}]
        cases = [
            ("direct", [{"arguments":[],"expect":{"type":"Int","value":"1"}}]),
            ("transitive", [{"arguments":[],"expect":{"type":"Int","value":"1"}}]),
            ("unsupported", [{"arguments":[{"type":"Box","value":{}}],"expect":{"type":"Int","value":"1"}}]),
            ("fib", [{"arguments":[{"type":"Int","value":"30"}],"expect":{"type":"Int","value":"832040"}}]),
            ("deep", [{"arguments":[{"type":"Int","value":"1"}],"expect":{"type":"Int","value":"1"}}]),
        ]
        for name, vectors in cases:
            requests.append(self.tool_request("tool_register",tool=name,document="doc-1",revision=revision,function=name))
            requests.append(self.tool_request("tool_validate",tool=name,document="doc-1",revision=revision,testVectors=vectors))
        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        validations = responses[2::2]
        self.assertEqual([item["status"] for item in validations], ["Rejected"] * len(cases))
        self.assertNotIn("blocked", result.stdout.splitlines())
        self.assertIn("say", validations[0]["error"])
        self.assertIn("say", validations[1]["error"])
        self.assertIn("Only Int", validations[2]["error"])
        self.assertIn("budget", validations[3]["error"])
        self.assertIn("depth", validations[4]["error"])

        incomplete = 'fn unfinished(value: Int) -> Int { return ?hole }\n'
        incomplete_revision = "sha256:" + hashlib.sha256(incomplete.encode()).hexdigest()
        incomplete_result = invoke_session([
            {"schemaVersion":3,"op":"open","source":incomplete},
            self.tool_request("tool_register",tool="unfinished",document="doc-1",revision=incomplete_revision,function="unfinished"),
            self.tool_request("tool_validate",tool="unfinished",document="doc-1",revision=incomplete_revision,
                              testVectors=[{"arguments":[{"type":"Int","value":"1"}],"expect":{"type":"Int","value":"1"}}]),
        ])
        incomplete_responses = [json.loads(line) for line in incomplete_result.stdout.splitlines()]
        self.assertEqual(incomplete_responses[1]["status"], "Registered")
        self.assertEqual(incomplete_responses[2]["status"], "Rejected")
        self.assertIn("Incomplete", incomplete_responses[2]["error"])

    def test_tool_scalar_message_types_round_trip(self):
        source = (
            'fn echo_bool(value: Bool) -> Bool { return value }\n'
            'fn echo_text(value: Str) -> Str { return value }\n'
            'fn no_result() -> Unit { }\n'
        )
        revision = "sha256:" + hashlib.sha256(source.encode()).hexdigest()
        requests = [{"schemaVersion":3,"op":"open","source":source}]
        definitions = [
            ("bool", "echo_bool", ["Bool"], "Bool", [{"arguments":[{"type":"Bool","value":True}],"expect":{"type":"Bool","value":True}}], [{"type":"Bool","value":False}]),
            ("text", "echo_text", ["Str"], "Str", [{"arguments":[{"type":"Str","value":"hello"}],"expect":{"type":"Str","value":"hello"}}], [{"type":"Str","value":"Pep"}]),
            ("unit", "no_result", [], "Unit", [{"arguments":[],"expect":{"type":"Unit","value":None}}], []),
        ]
        for name, function, _, _, vectors, args in definitions:
            requests.extend([
                self.tool_request("tool_register",tool=name,document="doc-1",revision=revision,function=function),
                self.tool_request("tool_validate",tool=name,document="doc-1",revision=revision,testVectors=vectors),
                self.tool_request("tool_activate",tool=name,document="doc-1",revision=revision),
                self.tool_request("tool_invoke",tool=name,arguments=args),
            ])
        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual([responses[index]["status"] for index in (2,6,10)], ["Validated"] * 3)
        self.assertEqual(responses[4]["result"], {"type":"Bool","value":False})
        self.assertEqual(responses[8]["result"], {"type":"Str","value":"Pep"})
        self.assertEqual(responses[12]["result"], {"type":"Unit","value":None})

    def test_tool_protocol_rejects_unknown_versions(self):
        missing_version = {"schemaVersion":3,"op":"tool_list"}
        unsupported_version = self.tool_request("tool_list")
        unsupported_version["toolProtocolVersion"] = 99
        responses = [json.loads(line) for line in invoke_session([missing_version,unsupported_version]).stdout.splitlines()]
        self.assertEqual(responses[0]["error"]["code"], "PEP_SESSION_FIELD_REQUIRED")
        self.assertEqual(responses[1]["error"]["code"], "PEP_TOOL_PROTOCOL_VERSION")
        self.assertEqual(responses[1]["toolProtocolVersion"], 1)

    def test_registered_tools_are_listed_but_not_callable_before_activation(self):
        source = 'fn plus_one(value: Int) -> Int { return value + 1 }\n'
        revision = "sha256:" + hashlib.sha256(source.encode()).hexdigest()
        responses = [json.loads(line) for line in invoke_session([
            {"schemaVersion":3,"op":"open","source":source},
            self.tool_request("tool_register",tool="plus",document="doc-1",revision=revision,function="plus_one"),
            self.tool_request("tool_list"),
        ]).stdout.splitlines()]
        self.assertEqual(responses[1]["status"], "Registered")
        self.assertFalse(responses[1]["callable"])
        self.assertEqual(responses[2]["tools"][0]["status"], "Registered")
        self.assertFalse(responses[2]["tools"][0]["callable"])

    def test_session_fill_hole_previews_applies_and_preserves_history(self):
        source = (
            "# retain this header\n"
            "fn double(n: Int) -> Int {\n"
            "    // keep before the target\n"
            "    return ?calculation // keep after the target\n"
            "}\n"
            "# retain this footer\n"
            "say(int_text(double(21)))\n"
        )
        old_revision = "sha256:" + hashlib.sha256(source.encode()).hexdigest()
        new_source = source.replace("?calculation", "n * 2")
        new_revision = "sha256:" + hashlib.sha256(new_source.encode()).hexdigest()
        fill = {
            "schemaVersion": 3, "op": "fill_hole", "document": "doc-1",
            "expected_revision": old_revision, "scope": "double", "name": "calculation",
            "replacement": "n * 2", "mode": "preview",
        }
        requests = [
            {"schemaVersion": 3, "op": "open", "name": "demo", "source": source},
            {"schemaVersion": 3, "op": "query", "document": "doc-1", "revision": old_revision},
            fill,
            {**fill},
            {"schemaVersion": 3, "op": "query", "document": "doc-1", "revision": old_revision},
            {**fill, "mode": "apply"},
            {"schemaVersion": 3, "op": "query", "document": "doc-1", "revision": old_revision},
            {"schemaVersion": 3, "op": "query", "document": "doc-1", "revision": new_revision},
            {"schemaVersion": 3, "op": "metrics"},
        ]
        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        opened, initial, preview, repeated, before_apply, applied, old, new, metrics = [
            json.loads(line) for line in result.stdout.splitlines()
        ]
        self.assertEqual(opened["revision"], old_revision)
        self.assertEqual(initial["holes"][0]["expectedType"], "Int")
        self.assertEqual(initial["holes"][0]["bindings"][0]["name"], "n")
        self.assertEqual(preview, repeated)
        self.assertEqual(preview["mode"], "preview")
        self.assertEqual(preview["status"], "valid")
        self.assertEqual(preview["revision"], new_revision)
        self.assertEqual(preview["currentRevision"], old_revision)
        self.assertEqual(preview["sourceDiff"]["removed"], "?calculation")
        self.assertEqual(preview["sourceDiff"]["inserted"], "n * 2")
        self.assertEqual(before_apply["revision"], old_revision)
        self.assertEqual(applied["currentRevision"], new_revision)
        self.assertEqual(old["status"], "incomplete")
        self.assertEqual(old["holes"][0]["name"], "calculation")
        self.assertEqual(new["status"], "valid")
        self.assertEqual(new["holes"], [])
        fresh = json.loads(invoke("check", self.source(new_source), "--json").stdout)
        self.assertEqual(new["typedTree"], fresh["typedTree"])
        start = len(source[:source.index("?calculation")].encode())
        raw_result = invoke_session([
            {"schemaVersion": 3, "op": "open", "source": source},
            {"schemaVersion": 3, "op": "apply_edit", "document": "doc-1", "expected_revision": old_revision,
             "start_byte": start, "end_byte": start + len("?calculation"), "replacement": "n * 2"},
        ])
        raw_open, raw_edit = [json.loads(line) for line in raw_result.stdout.splitlines()]
        self.assertEqual(raw_open["revision"], old_revision)
        self.assertEqual(raw_edit["revision"], new_revision)
        self.assertEqual(raw_edit["typedTree"], new["typedTree"])
        self.assertEqual(invoke("run", self.source(new_source)).stdout, "42\n")
        self.assertEqual(metrics["metrics"]["parse_count"], 4)

    def test_session_fill_hole_checks_replacement_and_rejects_injection(self):
        source = "fn f(n: Int) -> Int { return ?target }\n"
        revision = "sha256:" + hashlib.sha256(source.encode()).hexdigest()
        replacements = [
            ("true", "PEP_TYPE_MISMATCH"),
            ('f("wrong")', "PEP_TYPE_MISMATCH"),
            ("missing", "PEP_UNKNOWN_VARIABLE"),
            ("n *", "PEP_PARSE_EXPRESSION"),
            ("n\nlet injected = 1", "PEP_REPLACEMENT_TRAILING_INPUT"),
        ]
        requests = [{"schemaVersion": 3, "op": "open", "source": source}]
        for replacement, _ in replacements:
            requests.append({
                "schemaVersion": 3, "op": "fill_hole", "document": "doc-1",
                "expected_revision": revision, "scope": "f", "name": "target",
                "replacement": replacement, "mode": "preview",
            })
        requests.append({"schemaVersion": 3, "op": "query", "document": "doc-1", "revision": revision})
        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        for response, (_, code) in zip(responses[1:-1], replacements):
            self.assertEqual(response["outcome"], "rejected")
            self.assertEqual(response["candidateStatus"], "invalid")
            self.assertEqual(response["diagnostics"][0]["code"], code)
            self.assertEqual(response["currentRevision"], revision)
        self.assertEqual(responses[-1]["holes"][0]["name"], "target")

    def test_session_fill_hole_resolves_scope_and_rejects_duplicates(self):
        source = (
            "fn first(n: Int) -> Int { return ?answer }\n"
            "fn second(n: Int) -> Int { return ?answer }\n"
        )
        revision = "sha256:" + hashlib.sha256(source.encode()).hexdigest()
        requests = [
            {"schemaVersion": 3, "op": "open", "source": source},
            {"schemaVersion": 3, "op": "fill_hole", "document": "doc-1", "expected_revision": revision,
             "scope": "second", "name": "answer", "replacement": "n + 1", "mode": "apply"},
        ]
        second_source = source.replace(
            "fn second(n: Int) -> Int { return ?answer }",
            "fn second(n: Int) -> Int { return n + 1 }",
        )
        second_revision = "sha256:" + hashlib.sha256(second_source.encode()).hexdigest()
        requests.append({"schemaVersion": 3, "op": "query", "document": "doc-1", "revision": second_revision})
        duplicate_source = "fn dup(n: Int) -> Int { let a: Int = ?same return ?same }\n"
        duplicate_revision = "sha256:" + hashlib.sha256(duplicate_source.encode()).hexdigest()
        requests.extend([
            {"schemaVersion": 3, "op": "open", "source": duplicate_source},
            {"schemaVersion": 3, "op": "fill_hole", "document": "doc-2", "expected_revision": duplicate_revision,
             "scope": "dup", "name": "same", "replacement": "n", "mode": "preview"},
            {"schemaVersion": 3, "op": "fill_hole", "document": "doc-2", "expected_revision": duplicate_revision,
             "scope": "absent", "name": "same", "replacement": "n", "mode": "preview"},
        ])
        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        opened, applied, queried, duplicate_open, duplicate, missing = [
            json.loads(line) for line in result.stdout.splitlines()
        ]
        self.assertEqual(opened["status"], "incomplete")
        self.assertEqual(applied["status"], "incomplete")
        self.assertEqual([hole["scope"] for hole in queried["holes"]], ["first"])
        self.assertEqual(duplicate["error"]["code"], "PEP_HOLE_AMBIGUOUS")
        self.assertEqual(missing["error"]["code"], "PEP_HOLE_NOT_FOUND")
        self.assertEqual(missing["currentRevision"], duplicate_open["revision"])

    def test_session_fill_hole_stale_apply_and_failed_apply_preserve_current_revision(self):
        source = "fn f(n: Int) -> Int { return ?target }\n"
        revision = "sha256:" + hashlib.sha256(source.encode()).hexdigest()
        changed = "\n" + source
        changed_revision = "sha256:" + hashlib.sha256(changed.encode()).hexdigest()
        requests = [
            {"schemaVersion": 3, "op": "open", "source": source},
            {"schemaVersion": 3, "op": "fill_hole", "document": "doc-1", "expected_revision": revision,
             "scope": "f", "name": "target", "replacement": "n", "mode": "preview"},
            {"schemaVersion": 3, "op": "apply_edit", "document": "doc-1", "expected_revision": revision,
             "start_byte": 0, "end_byte": 0, "replacement": "\n"},
            {"schemaVersion": 3, "op": "fill_hole", "document": "doc-1", "expected_revision": revision,
             "scope": "f", "name": "target", "replacement": "n", "mode": "apply"},
            {"schemaVersion": 3, "op": "query", "document": "doc-1", "revision": changed_revision},
            {"schemaVersion": 3, "op": "fill_hole", "document": "doc-1", "expected_revision": changed_revision,
             "scope": "f", "name": "target", "replacement": "true", "mode": "apply"},
            {"schemaVersion": 3, "op": "query", "document": "doc-1", "revision": changed_revision},
        ]
        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        opened, preview, edit, stale, current, rejected, still_current = [
            json.loads(line) for line in result.stdout.splitlines()
        ]
        self.assertEqual(preview["outcome"], "ok")
        self.assertEqual(edit["revision"], changed_revision)
        self.assertEqual(stale["error"]["code"], "PEP_STALE_REVISION")
        self.assertEqual(stale["currentRevision"], changed_revision)
        self.assertEqual(current["holes"][0]["name"], "target")
        self.assertEqual(rejected["outcome"], "rejected")
        self.assertEqual(rejected["candidateStatus"], "invalid")
        self.assertEqual(still_current["revision"], changed_revision)
        self.assertEqual(still_current["holes"], current["holes"])

    def test_session_fill_hole_uses_original_utf8_lf_and_crlf_spans(self):
        for newline in ("\n", "\r\n"):
            source = f'say("café") // keep unicode comment{newline}fn f(n: Int) -> Int {{{newline} return ?target // preserve this{newline}}}{newline}'
            revision = "sha256:" + hashlib.sha256(source.encode()).hexdigest()
            expected_start = len(source[:source.index("?target")].encode())
            result = invoke_session([
                {"schemaVersion": 3, "op": "open", "source": source},
                {"schemaVersion": 3, "op": "fill_hole", "document": "doc-1", "expected_revision": revision,
                 "scope": "f", "name": "target", "replacement": "n", "mode": "preview"},
            ])
            self.assertEqual(result.returncode, 0, result.stderr)
            opened, preview = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(opened["holes"][0]["span"]["start"]["offset"], expected_start)
            self.assertEqual(preview["sourceDiff"]["startByte"], expected_start)
            self.assertEqual(preview["sourceDiff"]["removed"], "?target")

    def test_session_fill_hole_leaves_unrelated_holes_incomplete(self):
        source = (
            "fn f(n: Int) -> Int { return ?target }\n"
            "fn g(n: Int) -> Int { return ?other }\n"
        )
        revision = "sha256:" + hashlib.sha256(source.encode()).hexdigest()
        new_source = source.replace("?target", "n * 2")
        new_revision = "sha256:" + hashlib.sha256(new_source.encode()).hexdigest()
        result = invoke_session([
            {"schemaVersion": 3, "op": "open", "source": source},
            {"schemaVersion": 3, "op": "fill_hole", "document": "doc-1", "expected_revision": revision,
             "scope": "f", "name": "target", "replacement": "n * 2", "mode": "apply"},
            {"schemaVersion": 3, "op": "query", "document": "doc-1", "revision": new_revision},
        ])
        self.assertEqual(result.returncode, 0, result.stderr)
        _, applied, queried = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(applied["status"], "incomplete")
        self.assertEqual([hole["name"] for hole in queried["holes"]], ["other"])

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
        self.assertEqual(description["types"], ["Int", "Bool", "Str", "SourceBytes", "Unit"])
        self.assertIn("query_holes", description["features"])
        self.assertIn("jsonl_session", description["features"])
        self.assertIn("tool_hot_replacement", description["features"])
        self.assertEqual(description["session"]["schemaVersion"], 3)
        self.assertFalse(description["session"]["crossRevisionReuse"])
        self.assertEqual(description["session"]["toolProtocolVersion"], 1)
        self.assertFalse(description["session"]["toolRuntime"]["sandboxed"])
        self.assertIn("semantic_hole_fill", description["features"])
        self.assertIn("records", description["features"])
        self.assertIn("tagged_unions", description["features"])
        self.assertIn("pattern_matching", description["features"])
        self.assertIn("fill_hole", description["session"]["operations"])


    def test_records_are_checked_resolved_and_interpreted(self):
        source = (
            "type Point {\n x: Int\n y: Int\n}\n"
            "fn sum(point: Point) -> Int { return point.x + point.y }\n"
            "let point = Point { x: 20, y: 22 }\n"
            "say(int_text(sum(point)))\n"
        )
        path = self.source(source)
        checked = invoke("check", path, "--json")
        self.assertEqual(checked.returncode, 0, checked.stderr)
        value = json.loads(checked.stdout)
        self.assertEqual(value["status"], "valid")
        self.assertEqual(value["typedTree"]["types"][0]["name"], "Point")
        self.assertEqual([field["name"] for field in value["typedTree"]["types"][0]["fields"]], ["x", "y"])
        binary = value["typedTree"]["functions"][0]["body"][0]["value"]["expression"]
        field_accesses = [node["expression"]["fieldId"] for node in (binary["left"], binary["right"])]
        self.assertEqual(field_accesses, [0, 1])
        self.assertEqual(invoke("run", path).stdout, "42\n")

    def test_record_declaration_and_construction_errors(self):
        cases = [
            ("type Point { x: Int x: Bool }\n", "PEP_DUPLICATE_FIELD"),
            ("type Point { x: Int }\nlet p = Point { x: 1, x: 2 }\n", "PEP_DUPLICATE_FIELD"),
            ("type Point { x: Int }\nlet p = Point { y: 1 }\n", "PEP_MISSING_FIELD"),
            ("type Point { x: Int }\nlet p = Point { x: 1, y: 2 }\n", "PEP_UNKNOWN_FIELD"),
            ("type Point { x: Int }\nlet p = Point { x: true }\n", "PEP_TYPE_MISMATCH"),
            ("type Point { x: Missing }\n", "PEP_UNKNOWN_TYPE"),
            ("type Say = say(Str)\n", "PEP_RESERVED_CONSTRUCTOR"),
            ("type Point { x: Int }\nlet p = Point { x: 1 }\nlet n: Int = p.y\n", "PEP_UNKNOWN_FIELD"),
        ]
        for source, code in cases:
            with self.subTest(code=code, source=source):
                result = invoke("check", self.source(source), "--json")
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertEqual(json.loads(result.stdout)["diagnostics"][0]["code"], code)

    def test_recursive_tagged_union_match_and_checked_evaluation(self):
        source = (
            "type Expr = Number(Int) | Add(Expr, Expr)\n"
            "fn evaluate(expr: Expr) -> Int {\n"
            " return match expr { Number(n) => n Add(a, b) => evaluate(a) + evaluate(b) }\n"
            "}\n"
            "say(int_text(evaluate(Add(Number(20), Number(22)))))\n"
        )
        path = self.source(source)
        first = invoke("check", path, "--json")
        self.assertEqual(first.returncode, 0, first.stderr)
        value = json.loads(first.stdout)
        self.assertEqual(value["status"], "valid")
        union = value["typedTree"]["types"][0]
        self.assertEqual(union["kind"], "union")
        self.assertEqual([variant["name"] for variant in union["variants"]], ["Number", "Add"])
        self.assertEqual(value["typedTree"]["functions"][0]["body"][0]["value"]["expression"]["kind"], "match")
        pattern = value["typedTree"]["functions"][0]["body"][0]["value"]["expression"]["arms"][0]["pattern"]
        self.assertEqual(pattern["kind"], "constructor")
        self.assertEqual(pattern["span"]["start"]["offset"], source.index("Number(n)"))
        second = invoke("check", path, "--json")
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(invoke("run", path).stdout, "42\n")

    def test_nested_patterns_and_constructor_runtime(self):
        source = (
            "type Expr = Number(Int) | Add(Expr, Expr)\n"
            "fn leftmost(expr: Expr) -> Int {\n"
            " return match expr { Number(n) => n Add(Number(n), _) => n Add(_, _) => 0 }\n"
            "}\n"
            "say(int_text(leftmost(Add(Number(7), Number(9)))))\n"
        )
        result = invoke("run", self.source(source))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "7\n")

    def test_match_holes_have_expected_types_and_arm_local_bindings(self):
        source = (
            "type Expr = Number(Int) | Add(Expr, Expr)\n"
            "fn evaluate(expr: Expr) -> Int {\n"
            " return match expr { Number(n) => ?number_case Add(a, b) => ?addition_case }\n"
            "}\n"
        )
        result = invoke("query", self.source(source), "--holes", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        holes = json.loads(result.stdout)["holes"]
        self.assertEqual([hole["expectedType"] for hole in holes], ["Int", "Int"])
        self.assertEqual(holes[0]["identity"], "number_case")
        self.assertIn(("n", "Int"), [(b["name"], b["type"]) for b in holes[0]["bindings"]])
        self.assertEqual(holes[1]["identity"], "addition_case")
        self.assertIn(("a", "Expr"), [(b["name"], b["type"]) for b in holes[1]["bindings"]])
        self.assertIn(("b", "Expr"), [(b["name"], b["type"]) for b in holes[1]["bindings"]])
        self.assertEqual(invoke("run", self.source(source)).returncode, 1)

    def test_match_infers_result_type_for_earlier_holes(self):
        source = (
            "type Maybe = Some(Int) | None()\n"
            "let maybe: Maybe = Some(5)\n"
            "let selected = match maybe { Some(n) => ?selected_value None() => 1 }\n"
        )
        result = invoke("query", self.source(source), "--holes", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        hole = json.loads(result.stdout)["holes"][0]
        self.assertEqual(hole["expectedType"], "Int")
        self.assertIn(("n", "Int"), [(b["name"], b["type"]) for b in hole["bindings"]])

    def test_union_constructor_and_match_errors(self):
        prefix = "type Expr = Number(Int) | Add(Expr, Expr)\n"
        cases = [
            (prefix + "let x = Missing(1)\n", "PEP_UNKNOWN_CONSTRUCTOR"),
            (prefix + "let x = Number()\n", "PEP_ARGUMENT_COUNT"),
            (prefix + "let x = Number(true)\n", "PEP_TYPE_MISMATCH"),
            (prefix + "fn f(x: Expr) -> Int { return match x { Number(n) => n } }\n", "PEP_NON_EXHAUSTIVE_MATCH"),
            (prefix + "fn f(x: Expr) -> Int { return match x { Number(n) => n Number(m) => m Add(a,b) => 0 } }\n", "PEP_DUPLICATE_MATCH_ARM"),
            (prefix + "fn f(x: Expr) -> Int { return match x { _ => 0 Number(n) => n } }\n", "PEP_UNREACHABLE_MATCH_ARM"),
            (prefix + "fn f(x: Expr) -> Int { return match x { Number(n) => n Add(a,b) => false } }\n", "PEP_MATCH_ARM_TYPE_MISMATCH"),
            (prefix + "fn f(x: Expr) -> Int { return match x { Number(n) => missing Add(a,b) => 0 } }\n", "PEP_UNKNOWN_VARIABLE"),
        ]
        for source, code in cases:
            with self.subTest(code=code):
                result = invoke("check", self.source(source), "--json")
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertEqual(json.loads(result.stdout)["diagnostics"][0]["code"], code)

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
            ('let old_name: String = "legacy"\n', "PEP_UNKNOWN_TYPE"),
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
        reserved_string_search = invoke("check", self.source("fn str_contains(x: Str, y: Str) -> Bool { return true }\n"), "--json")
        self.assertEqual(json.loads(reserved_string_search.stdout)["diagnostics"][0]["code"], "PEP_RESERVED_FUNCTION")

if __name__ == "__main__":
    unittest.main(verbosity=2)
