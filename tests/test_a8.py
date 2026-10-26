import hashlib
import json
import pathlib
import re
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PEP = ROOT / "pep.ps1"
ANALYZER = ROOT / "examples" / "unused_functions.pep"
EXPLANATION = "No root-reachable call path reaches this function."
REPLACED_EXPLANATION = "No declared root path reaches this function."
ROOT_POLICY = "top_level_calls_plus_host_entry_functions"


def revision(source):
    return "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest()


def scalar(kind, value):
    return {"type": kind, "value": value}


def typed_list(kind, values):
    return {"type": kind, "value": values}


def record(type_name, **fields):
    return {"type": type_name, "fields": [{"name": name, "value": value} for name, value in fields.items()]}


def tool_request(operation, **fields):
    return {"schemaVersion": 3, "toolProtocolVersion": 2, "op": operation, **fields}


def semantic_target(document, source, entries=()):
    return {"document": document, "revision": revision(source), "entryFunctions": list(entries)}


def invoke_session(requests):
    payload = "\n".join(json.dumps(item, ensure_ascii=False) for item in requests) + "\n"
    result = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(PEP), "session", "--jsonl"],
        cwd=ROOT, text=True, input=payload, capture_output=True, check=False,
    )
    return result


def function_names(source):
    return re.findall(r"^fn\s+([A-Za-z_][A-Za-z0-9_]*)", source, re.MULTILINE)


def function_span_bytes(source, name):
    start = source.index("fn " + name)
    opening = source.index("{", start)
    depth = 0
    end = None
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                end = index + 1
                break
    if end is None:
        raise AssertionError(f"function {name} has no closing body")
    return len(source[:start].encode("utf-8")), len(source[:end].encode("utf-8"))


def expected_report(document, source, finding_names, *, explanation=EXPLANATION, status="valid", authoritative=True):
    names = function_names(source)
    findings = []
    for name in finding_names:
        symbol_id = names.index(name)
        start, end = function_span_bytes(source, name)
        findings.append(record(
            "Finding",
            kind=scalar("Str", "unreachable_function"),
            symbolId=scalar("Int", str(symbol_id)),
            functionName=scalar("Str", name),
            startByte=scalar("Int", str(start)),
            endByte=scalar("Int", str(end)),
            explanation=scalar("Str", explanation),
        ))
    return record(
        "AnalysisReport",
        targetDocument=scalar("Str", document),
        targetRevision=scalar("Str", revision(source)),
        protocol=scalar("Int", "2"),
        rootPolicy=scalar("Str", ROOT_POLICY),
        targetStatus=scalar("Str", status),
        authoritative=scalar("Bool", authoritative),
        findings=typed_list("List[Finding]", findings),
    )


class PepA8Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analyzer_source = ANALYZER.read_text(encoding="utf-8")

    def test_pep_analyzer_runs_real_fixture_matrix_and_hot_replaces(self):
        fixtures = [
            ("all_reachable", "fn entry() -> Int { return helper() }\nfn helper() -> Int { return 1 }\n", ["entry"], []),
            ("single_orphan", "fn entry() -> Int { return helper() }\nfn helper() -> Int { return 1 }\nfn orphan() -> Int { return 2 }\n", ["entry"], ["orphan"]),
            ("disconnected_chain", "fn entry() -> Int { return 1 }\nfn orphan_a() -> Int { return orphan_b() }\nfn orphan_b() -> Int { return 2 }\n", ["entry"], ["orphan_a", "orphan_b"]),
            ("mutual_cycle", "fn entry() -> Int { return 1 }\nfn orphan_a() -> Int { return orphan_b() }\nfn orphan_b() -> Int { return orphan_a() }\n", ["entry"], ["orphan_a", "orphan_b"]),
            ("reachable_self_recursion", "fn entry() -> Int { return cycle() }\nfn cycle() -> Int { return cycle() }\n", ["entry"], []),
            ("unrooted_self_recursion", "fn cycle() -> Int { return cycle() }\nfn isolated() -> Int { return 3 }\n", [], ["cycle", "isolated"]),
            ("top_level_root", "fn main() -> Int { return helper() }\nfn helper() -> Int { return 7 }\nmain()\n", [], []),
            ("explicit_entry_root", "fn entry() -> Int { return helper() }\nfn helper() -> Int { return 7 }\n", ["entry"], []),
            ("no_root_policy", "fn alpha() -> Int { return 1 }\nfn beta() -> Int { return alpha() }\n", [], ["alpha", "beta"]),
            ("constructor_is_not_call_edge", "type Maybe = Missing(Int) | Present(Int)\nfn entry() -> Maybe { return Present(4) }\nfn orphan() -> Int { return 9 }\nentry()\n", [], ["orphan"]),
            ("text_is_not_a_call_edge", 'fn entry() -> Int { let note = "orphan()"; return helper() }\nfn helper() -> Int { return 1 }\nfn orphan() -> Int { return 2 }\nentry()\n', [], ["orphan"]),
        ]
        prefix = 'let label = "λ🙂"\r\n'
        crlf_source = prefix + "fn entry() -> Int { return 1 }\r\nfn orphan() -> Int { return 2 }\r\n"
        fixtures.append(("utf8_crlf", crlf_source, ["entry"], ["orphan"]))

        requests = [{"schemaVersion": 3, "op": "open", "source": self.analyzer_source}]
        docs = {}
        for name, source, entries, findings in fixtures:
            requests.append({"schemaVersion": 3, "op": "open", "name": name, "source": source})
            docs[name] = (f"doc-{len(docs) + 2}", source, entries, findings)

        tool_revision = revision(self.analyzer_source)
        requests.append(tool_request("tool_register", tool="unused_functions", document="doc-1",
                                     revision=tool_revision, function="analyze"))
        vectors = [
            {"arguments": [], "expect": expected_report(document, source, findings),
             "semanticTarget": semantic_target(document, source, entries)}
            for document, source, entries, findings in docs.values()
        ]
        requests.append(tool_request("tool_validate", tool="unused_functions", document="doc-1",
                                     revision=tool_revision, testVectors=vectors))
        requests.append(tool_request("tool_activate", tool="unused_functions", document="doc-1", revision=tool_revision))
        requests.append(tool_request("tool_list"))
        single_doc, single_source, single_entries, single_findings = docs["single_orphan"]
        invoke_single = len(requests)
        requests.append(tool_request("tool_invoke", tool="unused_functions", arguments=[],
                                     semanticTarget=semantic_target(single_doc, single_source, single_entries)))

        changed_source = single_source.replace(
            "fn entry() -> Int { return helper() }",
            "fn entry() -> Int { return helper() + orphan() }",
        )
        changed_revision = revision(changed_source)
        edit_index = len(requests)
        requests.append({"schemaVersion": 3, "op": "apply_edit", "document": single_doc,
                         "expected_revision": revision(single_source), "start_byte": 0,
                         "end_byte": len(single_source.encode("utf-8")), "replacement": changed_source})
        invoke_old = len(requests)
        requests.append(tool_request("tool_invoke", tool="unused_functions", arguments=[],
                                     semanticTarget=semantic_target(single_doc, single_source, single_entries)))
        invoke_new = len(requests)
        requests.append(tool_request("tool_invoke", tool="unused_functions", arguments=[],
                                     semanticTarget=semantic_target(single_doc, changed_source, single_entries)))

        source_v2 = self.analyzer_source.replace(EXPLANATION, REPLACED_EXPLANATION)
        tool_revision_v2 = revision(source_v2)
        requests.append({"schemaVersion": 3, "op": "apply_edit", "document": "doc-1",
                         "expected_revision": tool_revision, "start_byte": 0,
                         "end_byte": len(self.analyzer_source.encode("utf-8")), "replacement": source_v2})
        requests.append(tool_request("tool_register", tool="unused_functions", document="doc-1",
                                     revision=tool_revision_v2, function="analyze"))
        chain_doc, chain_source, chain_entries, chain_findings = docs["disconnected_chain"]
        validate_v2 = len(requests)
        requests.append(tool_request("tool_validate", tool="unused_functions", document="doc-1",
                                     revision=tool_revision_v2,
                                     testVectors=[{"arguments": [],
                                                   "expect": expected_report(chain_doc, chain_source, chain_findings,
                                                                             explanation=REPLACED_EXPLANATION),
                                                   "semanticTarget": semantic_target(chain_doc, chain_source, chain_entries)}]))
        requests.append(tool_request("tool_activate", tool="unused_functions", document="doc-1", revision=tool_revision_v2))
        list_v2 = len(requests)
        requests.append(tool_request("tool_list"))
        invoke_v2 = len(requests)
        requests.append(tool_request("tool_invoke", tool="unused_functions", arguments=[],
                                     semanticTarget=semantic_target(chain_doc, chain_source, chain_entries)))

        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(responses), len(requests))
        self.assertEqual(responses[1]["document"], "doc-2")
        self.assertEqual(responses[len(fixtures)]["document"], "doc-13")
        register_index = 1 + len(fixtures)
        validate_index = register_index + 1
        activate_index = validate_index + 1
        list_index = activate_index + 1
        self.assertEqual(responses[register_index]["status"], "Registered")
        self.assertEqual(responses[validate_index]["status"], "Validated", responses[validate_index])
        self.assertEqual(responses[activate_index]["status"], "Active")
        self.assertEqual(responses[list_index]["tools"][0]["toolProtocolVersion"], 2)
        self.assertEqual(responses[invoke_single]["result"], expected_report(single_doc, single_source, single_findings))
        self.assertEqual(responses[invoke_single]["revision"], tool_revision)
        self.assertEqual(responses[edit_index]["revision"], changed_revision)
        self.assertEqual(responses[invoke_old]["result"], expected_report(single_doc, single_source, single_findings))
        self.assertEqual(responses[invoke_new]["result"], expected_report(single_doc, changed_source, []))
        self.assertEqual(responses[invoke_old]["revision"], tool_revision)
        self.assertEqual(responses[invoke_new]["revision"], tool_revision)
        self.assertEqual(responses[validate_v2]["status"], "Validated", responses[validate_v2])
        listed_tools = responses[list_v2]["tools"]
        self.assertEqual({entry["status"] for entry in listed_tools}, {"Superseded", "Active"})
        self.assertEqual(next(entry["revision"] for entry in listed_tools if entry["status"] == "Active"), tool_revision_v2)
        self.assertEqual(responses[invoke_v2]["revision"], tool_revision_v2)
        self.assertEqual(responses[invoke_v2]["result"], expected_report(chain_doc, chain_source, chain_findings,
                                                                          explanation=REPLACED_EXPLANATION))

    def test_invalid_incomplete_and_unauthorised_targets_are_not_authoritative(self):
        invalid_source = "fn broken( -> Int {}\n"
        incomplete_source = "fn partial() -> Int { return ?todo }\n"
        valid_source = "fn entry() -> Int { return 1 }\n"
        tool_revision = revision(self.analyzer_source)
        valid_revision = revision(valid_source)
        expected_valid = expected_report("doc-4", valid_source, [])
        requests = [
            {"schemaVersion": 3, "op": "open", "source": self.analyzer_source},
            {"schemaVersion": 3, "op": "open", "source": invalid_source},
            {"schemaVersion": 3, "op": "open", "source": incomplete_source},
            {"schemaVersion": 3, "op": "open", "source": valid_source},
            tool_request("tool_register", tool="analyzer", document="doc-1", revision=tool_revision, function="analyze"),
            tool_request("tool_validate", tool="analyzer", document="doc-1", revision=tool_revision,
                         testVectors=[{"arguments": [], "expect": expected_valid,
                                       "semanticTarget": semantic_target("doc-4", valid_source, ["entry"])}]),
            tool_request("tool_activate", tool="analyzer", document="doc-1", revision=tool_revision),
            tool_request("tool_invoke", tool="analyzer", arguments=[],
                         semanticTarget=semantic_target("doc-2", invalid_source)),
            tool_request("tool_invoke", tool="analyzer", arguments=[],
                         semanticTarget=semantic_target("doc-3", incomplete_source)),
            tool_request("tool_invoke", tool="analyzer", arguments=[],
                         semanticTarget=semantic_target("doc-4", valid_source, ["unknown"])),
            tool_request("tool_invoke", tool="analyzer", arguments=[],
                         semanticTarget=semantic_target("doc-4", valid_source, ["entry", "entry"])),
            tool_request("tool_invoke", tool="analyzer", arguments=[],
                         semanticTarget=semantic_target("doc-404", valid_source)),
        ]
        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(responses[5]["status"], "Validated", responses[5])
        self.assertEqual(responses[7]["result"], expected_report("doc-2", invalid_source, [], status="invalid", authoritative=False))
        self.assertEqual(responses[8]["result"], expected_report("doc-3", incomplete_source, [], status="incomplete", authoritative=False))
        self.assertEqual(responses[9]["error"]["code"], "PEP_SEMANTIC_ROOT_NOT_FOUND")
        self.assertEqual(responses[10]["error"]["code"], "PEP_SEMANTIC_ROOT_DUPLICATE")
        self.assertEqual(responses[11]["error"]["code"], "PEP_DOCUMENT_NOT_FOUND")

    def test_rejected_replacements_and_say_paths_leave_active_analyzer_unchanged(self):
        tool_revision = revision(self.analyzer_source)
        target_source = (
            "fn entry() -> Int { return helper() }\n"
            "fn helper() -> Int { return 1 }\n"
            "fn orphan() -> Int { return 2 }\n"
        )
        target_revision = revision(target_source)
        target = semantic_target("doc-2", target_source, ["entry"])
        expected = expected_report("doc-2", target_source, ["orphan"])
        requests = [
            {"schemaVersion": 3, "op": "open", "source": self.analyzer_source},
            {"schemaVersion": 3, "op": "open", "source": target_source},
            tool_request("tool_register", tool="analyzer", document="doc-1", revision=tool_revision, function="analyze"),
            tool_request("tool_validate", tool="analyzer", document="doc-1", revision=tool_revision,
                         testVectors=[{"arguments": [], "expect": expected, "semanticTarget": target}]),
            tool_request("tool_activate", tool="analyzer", document="doc-1", revision=tool_revision),
        ]
        candidates = [
            ("direct_say", self.analyzer_source.replace(
                "    let program = semantic_snapshot()",
                '    say("blocked")\n    let program = semantic_snapshot()',
            ), [], "reaches say"),
            ("transitive_say", self.analyzer_source.replace(
                "fn analyze() -> AnalysisReport {",
                'fn helper() -> Unit { say("blocked") }\n\nfn analyze() -> AnalysisReport {',
            ).replace(
                "    let program = semantic_snapshot()",
                "    helper()\n    let program = semantic_snapshot()",
            ), [], "reaches say"),
            ("incomplete", self.analyzer_source + "\nfn unfinished() -> Int { return ?todo }\n", [], "Incomplete source"),
            ("failed_vector", self.analyzer_source.replace(EXPLANATION, "Changed output must fail the frozen vector."),
             [{"arguments": [], "expect": expected, "semanticTarget": target}], "PEP_TOOL_TEST_FAILED"),
            ("incompatible", self.analyzer_source.replace(
                "fn analyze() -> AnalysisReport {", "fn analyze(mode: Int) -> AnalysisReport {"), [],
             "Replacement signature is incompatible"),
            ("invalid", "fn broken( -> Int {}\n", [], "Source is invalid"),
        ]
        current_source = self.analyzer_source
        current_revision = tool_revision
        validation_indices = []
        active_invoke_indices = []
        for _, replacement, vectors, _ in candidates:
            next_revision = revision(replacement)
            requests.append({"schemaVersion": 3, "op": "apply_edit", "document": "doc-1",
                             "expected_revision": current_revision, "start_byte": 0,
                             "end_byte": len(current_source.encode("utf-8")), "replacement": replacement})
            requests.append(tool_request("tool_register", tool="analyzer", document="doc-1",
                                         revision=next_revision, function="analyze"))
            validation_indices.append(len(requests))
            requests.append(tool_request("tool_validate", tool="analyzer", document="doc-1",
                                         revision=next_revision, testVectors=vectors))
            active_invoke_indices.append(len(requests))
            requests.append(tool_request("tool_invoke", tool="analyzer", arguments=[], semanticTarget=target))
            current_source, current_revision = replacement, next_revision

        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        for index, (_, _, _, error_fragment) in zip(validation_indices, candidates):
            self.assertEqual(responses[index]["status"], "Rejected", responses[index])
            self.assertIn(error_fragment, responses[index]["error"])
        for index in active_invoke_indices:
            self.assertEqual(responses[index]["revision"], tool_revision)
            self.assertEqual(responses[index]["result"], expected)

    def test_large_findings_hit_interpreter_budget_with_a_structured_error(self):
        target_source = "".join(
            f"fn orphan_{index}() -> Int {{ return {index} }}\n" for index in range(550)
        )
        tool_revision = revision(self.analyzer_source)
        small_source = "fn entry() -> Int { return 1 }\n"
        small_revision = revision(small_source)
        small_expected = expected_report("doc-2", small_source, [])
        requests = [
            {"schemaVersion": 3, "op": "open", "source": self.analyzer_source},
            {"schemaVersion": 3, "op": "open", "source": small_source},
            {"schemaVersion": 3, "op": "open", "source": target_source},
            tool_request("tool_register", tool="analyzer", document="doc-1", revision=tool_revision, function="analyze"),
            tool_request("tool_validate", tool="analyzer", document="doc-1", revision=tool_revision,
                         testVectors=[{"arguments": [], "expect": small_expected,
                                       "semanticTarget": semantic_target("doc-2", small_source, ["entry"])}]),
            tool_request("tool_activate", tool="analyzer", document="doc-1", revision=tool_revision),
            tool_request("tool_invoke", tool="analyzer", arguments=[],
                         semanticTarget=semantic_target("doc-3", target_source)),
        ]
        self.assertEqual(small_revision, revision(small_source))
        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(responses[4]["status"], "Validated", responses[4])
        self.assertIn(responses[6]["error"]["code"], {
            "PEP_RUNTIME_STEP_LIMIT", "PEP_TOOL_VALUE_LIMIT", "PEP_SEMANTIC_BUDGET",
        }, responses[6])

    def test_cli_reports_the_pep_source_as_valid_and_runtime_requires_host_context(self):
        checked = subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(PEP), "check", str(ANALYZER), "--json"],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        self.assertEqual(json.loads(checked.stdout)["status"], "valid")
        with pathlib.Path(ROOT / "_build" / "a8-direct-run.pep").open("w", encoding="utf-8", newline="") as stream:
            stream.write(self.analyzer_source + "\nanalyze()\n")
        run = subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(PEP), "run", str(ROOT / "_build" / "a8-direct-run.pep")],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(run.returncode, 1)
        self.assertIn("PEP_RUNTIME_SEMANTIC_CONTEXT", run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()