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


def tool_request(op, **fields):
    return {"schemaVersion": 3, "toolProtocolVersion": 2, "op": op, **fields}


def revision(source):
    return "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest()


def scalar(type_name, value):
    return {"type": type_name, "value": value}


def list_value(type_name, items):
    return {"type": type_name, "value": items}


def record(type_name, **fields):
    return {
        "type": type_name,
        "fields": [{"name": name, "value": value} for name, value in fields.items()],
    }


def declaration_span(source, function_name):
    start = source.index("fn " + function_name)
    opening = source.index("{", start)
    depth = 0
    for offset in range(opening, len(source)):
        if source[offset] == "{":
            depth += 1
        elif source[offset] == "}":
            depth -= 1
            if depth == 0:
                return start, offset + 1
    raise AssertionError("function body was not closed")


def semantic_target(document, source_revision, entries=()):
    return {
        "document": document,
        "revision": source_revision,
        "entryFunctions": list(entries),
    }


class PepA7Tests(unittest.TestCase):
    def test_checker_resolved_snapshot_typed_consumer_and_retained_revisions(self):
        tool_source = (
            "fn snapshot() -> ProgramInfo { return semantic_snapshot() }\n"
            "fn summarize() -> Int {\n"
            "  let program = semantic_snapshot()\n"
            "  var count = 0\n"
            "  for function in program.functions { count = count + 1 }\n"
            "  for edge in program.calls { count = count + 1 }\n"
            "  for root in program.roots { count = count + 1 }\n"
            "  return count\n"
            "}\n"
        )
        target_source = (
            "type Choice = Some(Int)\n"
            "fn entry(flag: Bool) -> Int { return if flag { helper(1) } else { helper(2) } }\n"
            "fn helper(value: Int) -> Int {\n"
            "  let local = value\n"
            "  { let local = local + 1; return leaf(local) }\n"
            "}\n"
            "fn leaf(value: Int) -> Int { return value }\n"
            "fn cycle_a() -> Int { return cycle_b() }\n"
            "fn cycle_b() -> Int { return cycle_a() }\n"
            "fn make(value: Int) -> Choice { return Some(helper(value)) }\n"
            "fn inspect(choice: Choice) -> Int { return match choice { Some(inner) => helper(inner) } }\n"
            "entry(true)\n"
        )
        tool_revision = revision(tool_source)
        target_revision = revision(target_source)
        function_names = ["entry", "helper", "leaf", "cycle_a", "cycle_b", "make", "inspect"]

        def expected_snapshot(source_revision, source):
            functions = []
            for function_id, name in enumerate(function_names):
                start, end = declaration_span(source, name)
                functions.append(record(
                    "FunctionInfo",
                    id=scalar("Int", str(function_id)),
                    name=scalar("Str", name),
                    startByte=scalar("Int", str(start)),
                    endByte=scalar("Int", str(end)),
                ))
            calls = [
                (0, 1), (1, 2), (3, 4), (4, 3), (5, 1), (6, 1),
            ]
            edges = [
                record("CallEdge", caller=scalar("Int", str(caller)), callee=scalar("Int", str(callee)))
                for caller, callee in calls
            ]
            roots = [0, 3]
            return record(
                "ProgramInfo",
                document=scalar("Str", "doc-2"),
                revision=scalar("Str", source_revision),
                status=scalar("Str", "valid"),
                functions=list_value("List[FunctionInfo]", functions),
                calls=list_value("List[CallEdge]", edges),
                roots=list_value("List[Int]", [scalar("Int", str(root)) for root in roots]),
                diagnostics=list_value("List[SemanticDiagnostic]", []),
            )

        target = semantic_target("doc-2", target_revision, ["cycle_a"])
        requests = [
            {"schemaVersion": 3, "op": "open", "source": tool_source},
            {"schemaVersion": 3, "op": "open", "source": target_source},
            tool_request("tool_register", tool="snapshot", document="doc-1", revision=tool_revision, function="snapshot"),
            tool_request("tool_validate", tool="snapshot", document="doc-1", revision=tool_revision,
                         testVectors=[{"arguments": [], "expect": expected_snapshot(target_revision, target_source),
                                       "semanticTarget": target}]),
            tool_request("tool_activate", tool="snapshot", document="doc-1", revision=tool_revision),
            tool_request("tool_invoke", tool="snapshot", arguments=[], semanticTarget=target),
            tool_request("tool_register", tool="summary", document="doc-1", revision=tool_revision, function="summarize"),
            tool_request("tool_validate", tool="summary", document="doc-1", revision=tool_revision,
                         testVectors=[{"arguments": [], "expect": scalar("Int", "15"), "semanticTarget": target}]),
            tool_request("tool_activate", tool="summary", document="doc-1", revision=tool_revision),
            tool_request("tool_invoke", tool="summary", arguments=[], semanticTarget=target),
        ]
        changed_source = target_source.replace(
            "fn leaf(value: Int) -> Int { return value }",
            "fn leaf(value: Int) -> Int { return value + 1 }",
        )
        changed_revision = revision(changed_source)
        start = target_source.index("fn leaf(value: Int)")
        end = start + len("fn leaf(value: Int) -> Int { return value }")
        requests.extend([
            {"schemaVersion": 3, "op": "apply_edit", "document": "doc-2",
             "expected_revision": target_revision, "start_byte": start, "end_byte": end,
             "replacement": "fn leaf(value: Int) -> Int { return value + 1 }"},
            tool_request("tool_invoke", tool="snapshot", arguments=[],
                         semanticTarget=semantic_target("doc-2", target_revision, ["cycle_a"])),
            tool_request("tool_invoke", tool="snapshot", arguments=[],
                         semanticTarget=semantic_target("doc-2", changed_revision, ["cycle_a"])),
        ])
        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(responses), len(requests))
        self.assertEqual(responses[3]["status"], "Validated", responses[3])
        self.assertEqual(responses[5]["toolProtocolVersion"], 2)
        self.assertEqual(responses[5]["revision"], tool_revision)
        self.assertEqual(responses[5]["result"], expected_snapshot(target_revision, target_source))
        self.assertEqual(responses[7]["status"], "Validated", responses[7])
        self.assertEqual(responses[9]["result"], scalar("Int", "15"))
        self.assertEqual(responses[10]["revision"], changed_revision)
        self.assertEqual(responses[11]["result"], expected_snapshot(target_revision, target_source))
        self.assertEqual(responses[12]["result"], expected_snapshot(changed_revision, changed_source))
        self.assertEqual(responses[11]["revision"], tool_revision)
        self.assertEqual(responses[12]["revision"], tool_revision)

    def test_host_target_grants_are_required_and_invalid_source_has_typed_diagnostics(self):
        tool_source = (
            "fn snapshot() -> ProgramInfo { return semantic_snapshot() }\n"
            "fn state() -> Str { return semantic_snapshot().status }\n"
        )
        invalid_source = "fn broken( -> Int {}\n"
        invalid_revision = revision(invalid_source)
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "invalid.pep"
            path.write_text(invalid_source, encoding="utf-8")
            checked = invoke("check", path, "--json")
        diagnostic = json.loads(checked.stdout)["diagnostics"][0]
        span = diagnostic["span"]
        expected = record(
            "ProgramInfo",
            document=scalar("Str", "doc-2"),
            revision=scalar("Str", invalid_revision),
            status=scalar("Str", "invalid"),
            functions=list_value("List[FunctionInfo]", []),
            calls=list_value("List[CallEdge]", []),
            roots=list_value("List[Int]", []),
            diagnostics=list_value("List[SemanticDiagnostic]", [
                record(
                    "SemanticDiagnostic",
                    code=scalar("Str", diagnostic["code"]),
                    message=scalar("Str", diagnostic["message"]),
                    startByte=scalar("Int", str(span["start"]["offset"])),
                    endByte=scalar("Int", str(span["endOffset"])),
                )
            ]),
        )
        good_source = "fn entry() -> Unit {}\n"
        good_revision = revision(good_source)
        incomplete_source = "fn partial() -> Int { return ?todo }\n"
        incomplete_revision = revision(incomplete_source)
        requests = [
            {"schemaVersion": 3, "op": "open", "source": tool_source},
            {"schemaVersion": 3, "op": "open", "source": invalid_source},
            {"schemaVersion": 3, "op": "open", "source": good_source},
            tool_request("tool_register", tool="snapshot", document="doc-1",
                         revision=revision(tool_source), function="snapshot"),
            tool_request("tool_validate", tool="snapshot", document="doc-1",
                         revision=revision(tool_source),
                         testVectors=[{"arguments": [], "expect": expected}]),
            tool_request("tool_validate", tool="snapshot", document="doc-1",
                         revision=revision(tool_source),
                         testVectors=[{"arguments": [], "expect": expected,
                                       "semanticTarget": semantic_target("doc-404", invalid_revision)}]),
            tool_request("tool_validate", tool="snapshot", document="doc-1",
                         revision=revision(tool_source),
                         testVectors=[{"arguments": [], "expect": expected,
                                       "semanticTarget": semantic_target("doc-2", invalid_revision)}]),
            tool_request("tool_activate", tool="snapshot", document="doc-1", revision=revision(tool_source)),
            tool_request("tool_invoke", tool="snapshot", arguments=[],
                         semanticTarget=semantic_target("doc-2", invalid_revision)),
            tool_request("tool_register", tool="bad-root", document="doc-1",
                         revision=revision(tool_source), function="snapshot"),
            tool_request("tool_validate", tool="bad-root", document="doc-1",
                         revision=revision(tool_source),
                         testVectors=[{"arguments": [], "expect": expected,
                                       "semanticTarget": semantic_target("doc-3", good_revision, ["missing"])}]),
            {"schemaVersion": 3, "op": "open", "source": incomplete_source},
            tool_request("tool_register", tool="state", document="doc-1", revision=revision(tool_source), function="state"),
            tool_request("tool_validate", tool="state", document="doc-1", revision=revision(tool_source),
                         testVectors=[{"arguments": [], "expect": scalar("Str", "incomplete"),
                                       "semanticTarget": semantic_target("doc-4", incomplete_revision)}]),
        ]
        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(responses[4]["status"], "Rejected")
        self.assertIn("PEP_RUNTIME_SEMANTIC_CONTEXT", responses[4]["error"])
        self.assertEqual(responses[5]["status"], "Rejected")
        self.assertIn("PEP_DOCUMENT_NOT_FOUND", responses[5]["error"])
        self.assertEqual(responses[6]["status"], "Validated", responses[6])
        self.assertEqual(responses[7]["status"], "Active")
        self.assertEqual(responses[8]["result"], expected)
        self.assertEqual(responses[10]["status"], "Rejected")
        self.assertIn("PEP_SEMANTIC_ROOT_NOT_FOUND", responses[10]["error"])
        self.assertEqual(responses[13]["status"], "Validated", responses[13])

    def test_v2_records_lists_precision_limits_and_v1_compatibility(self):
        source = (
            "type Point { x: Int; label: Str }\n"
            "type Chain { next: List[Chain] }\n"
            "fn echo_points(points: List[Point]) -> List[Point] { return points }\n"
            "fn echo_chain(value: Chain) -> Chain { return value }\n"
        )
        source_revision = revision(source)
        point = record("Point", x=scalar("Int", "9223372036854775807"), label=scalar("Str", "precise"))
        point_list = list_value("List[Point]", [point])
        chain = record("Chain", next=list_value("List[Chain]", []))
        requests = [
            {"schemaVersion": 3, "op": "open", "source": source},
            tool_request("tool_register", tool="points", document="doc-1", revision=source_revision, function="echo_points"),
            tool_request("tool_validate", tool="points", document="doc-1", revision=source_revision,
                         testVectors=[{"arguments": [point_list], "expect": point_list}]),
            tool_request("tool_activate", tool="points", document="doc-1", revision=source_revision),
            tool_request("tool_invoke", tool="points", arguments=[point_list]),
            tool_request("tool_invoke", tool="points", arguments=[
                list_value("List[Point]", [record("Point", label=scalar("Str", "wrong order"),
                                                    x=scalar("Int", "1"))])
            ]),
            tool_request("tool_register", tool="chain", document="doc-1", revision=source_revision, function="echo_chain"),
            tool_request("tool_validate", tool="chain", document="doc-1", revision=source_revision,
                         testVectors=[{"arguments": [chain], "expect": chain}]),
            tool_request("tool_activate", tool="chain", document="doc-1", revision=source_revision),
        ]
        deep = chain
        for _ in range(9):
            deep = record("Chain", next=list_value("List[Chain]", [deep]))
        requests.append(tool_request("tool_invoke", tool="chain", arguments=[deep]))
        requests.append(tool_request("tool_invoke", tool="points", arguments=[
            list_value("List[Point]", [point] * 4_000)
        ]))
        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(responses[2]["status"], "Validated", responses[2])
        self.assertEqual(responses[4]["result"], point_list)
        self.assertEqual(responses[5]["error"]["code"], "PEP_TOOL_ARGUMENT_FIELDS")
        self.assertEqual(responses[7]["status"], "Validated", responses[7])
        self.assertEqual(responses[9]["error"]["code"], "PEP_TOOL_VALUE_DEPTH")
        self.assertEqual(responses[10]["error"]["code"], "PEP_TOOL_VALUE_LIMIT")

        too_large = invoke_session([{"schemaVersion": 3, "op": "open", "source": "x" * 1_048_600}])
        self.assertEqual(too_large.returncode, 0, too_large.stderr)
        self.assertEqual(json.loads(too_large.stdout)["error"]["code"], "PEP_TOOL_MESSAGE_TOO_LARGE")


    def test_semantic_snapshot_spans_use_original_utf8_bytes_for_lf_and_crlf(self):
        tool_source = (
            "fn start() -> Int {\n"
            "  let program = semantic_snapshot()\n"
            "  var offset = 0\n"
            "  for function in program.functions {\n"
            "    if function.name == \"main\" { offset = function.startByte } else {}\n"
            "  }\n"
            "  return offset\n"
            "}\n"
        )
        prefix_lf = 'say("λ🙂")\n'
        prefix_crlf = 'say("λ🙂")\r\n'
        target_lf = prefix_lf + "fn main() -> Int { return 7 }\n"
        target_crlf = prefix_crlf + "fn main() -> Int { return 7 }\r\n"
        tool_revision = revision(tool_source)
        target_lf_revision = revision(target_lf)
        target_crlf_revision = revision(target_crlf)
        expected_lf = len(prefix_lf.encode("utf-8"))
        expected_crlf = len(prefix_crlf.encode("utf-8"))
        requests = [
            {"schemaVersion": 3, "op": "open", "source": tool_source},
            {"schemaVersion": 3, "op": "open", "source": target_lf},
            {"schemaVersion": 3, "op": "open", "source": target_crlf},
            tool_request("tool_register", tool="start", document="doc-1", revision=tool_revision, function="start"),
            tool_request("tool_validate", tool="start", document="doc-1", revision=tool_revision,
                         testVectors=[{"arguments": [], "expect": scalar("Int", str(expected_lf)),
                                       "semanticTarget": semantic_target("doc-2", target_lf_revision, ["main"])}]),
            tool_request("tool_activate", tool="start", document="doc-1", revision=tool_revision),
            tool_request("tool_invoke", tool="start", arguments=[],
                         semanticTarget=semantic_target("doc-2", target_lf_revision, ["main"])),
            tool_request("tool_invoke", tool="start", arguments=[],
                         semanticTarget=semantic_target("doc-3", target_crlf_revision, ["main"])),
        ]
        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(responses[4]["status"], "Validated", responses[4])
        self.assertEqual(responses[6]["result"], scalar("Int", str(expected_lf)))
        self.assertEqual(responses[7]["result"], scalar("Int", str(expected_crlf)))
        self.assertEqual(expected_lf, len('say("λ🙂")\n'.encode("utf-8")))
        self.assertEqual(expected_crlf, len('say("λ🙂")\r\n'.encode("utf-8")))

    def test_v2_rejects_records_with_nontransportable_nested_union_fields(self):
        source = (
            "type Maybe = Missing(Int) | Present(Int)\n"
            "type Box { item: Maybe }\n"
            "fn echo(value: Box) -> Box { return value }\n"
        )
        source_revision = revision(source)
        requests = [
            {"schemaVersion": 3, "op": "open", "source": source},
            tool_request("tool_register", tool="box", document="doc-1", revision=source_revision, function="echo"),
            tool_request("tool_validate", tool="box", document="doc-1", revision=source_revision, testVectors=[]),
        ]
        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(responses[2]["status"], "Rejected")
        self.assertIn("Version 2 supports only scalar, List, and monomorphic record values", responses[2]["error"])

if __name__ == "__main__":
    unittest.main()
