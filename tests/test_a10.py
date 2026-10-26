import hashlib
import json
import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PEP = ROOT / "pep.ps1"
LEXER = ROOT / "examples" / "lexer_fragment.pep"


def revision(source):
    return "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest()


def scalar(kind, value):
    return {"type": kind, "value": value}


def typed_record(name, **values):
    return {"type": name, "fields": [{"name": key, "value": value} for key, value in values.items()]}


def request(op, **fields):
    return {"schemaVersion": 3, "toolProtocolVersion": 2, "op": op, **fields}


def invoke_session(requests):
    payload = "\n".join(json.dumps(item, ensure_ascii=False) for item in requests) + "\n"
    return subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(PEP), "session", "--jsonl"],
        cwd=ROOT, text=True, input=payload, capture_output=True, check=False,
    )


def fields(value):
    return {item["name"]: item["value"] for item in value["fields"]}


def result_field(result, name):
    return fields(result)[name]["value"]


def lexer_requests(target_source):
    lexer_source = LEXER.read_text(encoding="utf-8")
    empty_target = ""
    expected = typed_record(
        "LexReport",
        document=scalar("Str", "doc-2"),
        revision=scalar("Str", revision(empty_target)),
        status=scalar("Str", "valid"),
        tokens={"type": "List[LexToken]", "value": [typed_record(
            "LexToken", kind=scalar("Str", "eof"), startByte=scalar("Int", "0"),
            endByte=scalar("Int", "0"), line=scalar("Int", "1"),
            column=scalar("Int", "1"), lexeme=scalar("Str", ""),
        )]},
        errorCode=scalar("Str", ""), errorStart=scalar("Int", "0"),
        errorEnd=scalar("Int", "0"), errorLine=scalar("Int", "0"),
        errorColumn=scalar("Int", "0"),
    )
    return lexer_source, [
        request("open", source=lexer_source, name="lexer"),
        request("open", source=empty_target, name="empty"),
        request("tool_register", tool="lexer", document="doc-1", revision=revision(lexer_source), function="lex_fragment"),
        request("tool_validate", tool="lexer", document="doc-1", revision=revision(lexer_source), testVectors=[{
            "arguments": [], "expect": expected,
            "semanticTarget": {"document": "doc-2", "revision": revision(empty_target), "entryFunctions": []},
        }]),
        request("tool_activate", tool="lexer", document="doc-1", revision=revision(lexer_source)),
        request("open", source=target_source, name="source"),
        request("tool_invoke", tool="lexer", arguments=[], semanticTarget={
            "document": "doc-3", "revision": revision(target_source), "entryFunctions": [],
        }),
    ]


class PepA10Tests(unittest.TestCase):
    def test_pep_lexer_preserves_original_utf8_and_crlf_byte_spans(self):
        source = "# 😀\r\nlet x = 42 <= 43\n"
        _, requests = lexer_requests(source)
        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(responses[3]["status"], "Validated", responses[3])
        self.assertEqual(responses[4]["status"], "Active", responses[4])
        report = fields(responses[6]["result"])
        self.assertEqual(report["document"]["value"], "doc-3")
        self.assertEqual(report["revision"]["value"], revision(source))
        tokens = report["tokens"]["value"]
        actual = [(fields(item)["kind"]["value"], fields(item)["startByte"]["value"],
                   fields(item)["endByte"]["value"], fields(item)["line"]["value"],
                   fields(item)["column"]["value"], fields(item)["lexeme"]["value"])
                  for item in tokens]
        self.assertEqual(actual, [
            ("name", "8", "11", "2", "1", "let"),
            ("name", "12", "13", "2", "5", "x"),
            ("symbol", "14", "15", "2", "7", "="),
            ("number", "16", "18", "2", "9", "42"),
            ("symbol", "19", "21", "2", "12", "<="),
            ("number", "22", "24", "2", "15", "43"),
            ("eof", "25", "25", "3", "1", ""),
        ])
        self.assertEqual(report["errorCode"]["value"], "")

    def test_pep_lexer_reports_invalid_utf8_and_escape_with_byte_spans(self):
        lexer_source = LEXER.read_text(encoding="utf-8")
        invalid = bytes([35, 32, 111, 107, 13, 10, 255])
        invalid_target = {"schemaVersion": 3, "op": "open_bytes", "name": "invalid", "bytes": list(invalid)}
        malformed = '"bad\\q"'
        _, requests = lexer_requests("")
        requests = requests[:5] + [invalid_target]
        requests.append(request("tool_invoke", tool="lexer", arguments=[], semanticTarget={
            "document": "doc-3", "revision": "sha256:" + hashlib.sha256(invalid).hexdigest(), "entryFunctions": [],
        }))
        requests.append({"schemaVersion": 3, "op": "open", "source": malformed, "name": "malformed"})
        requests.append(request("tool_invoke", tool="lexer", arguments=[], semanticTarget={
            "document": "doc-4", "revision": revision(malformed), "entryFunctions": [],
        }))
        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        invalid_report = fields(responses[6]["result"])
        self.assertEqual(invalid_report["errorCode"]["value"], "PEP_INVALID_UTF8")
        self.assertEqual((invalid_report["errorStart"]["value"], invalid_report["errorEnd"]["value"]), ("6", "7"))
        self.assertEqual((invalid_report["errorLine"]["value"], invalid_report["errorColumn"]["value"]), ("2", "1"))
        escape_report = fields(responses[8]["result"])
        self.assertEqual(escape_report["errorCode"]["value"], "PEP_INVALID_ESCAPE")
        self.assertEqual((escape_report["errorStart"]["value"], escape_report["errorEnd"]["value"]), ("4", "6"))

    def test_pep_utf8_validator_rejects_overlong_truncated_surrogate_and_bad_continuation(self):
        invalid_sources = [b"\xc0\x80", b"\xe2\x82", b"\xed\xa0\x80", b"\xf4\x90\x80\x80", b"A\xe2(\xa1"]
        _, requests = lexer_requests("")
        requests = requests[:5]
        for index, raw in enumerate(invalid_sources, start=3):
            requests.append({"schemaVersion": 3, "op": "open_bytes", "bytes": list(raw)})
            requests.append(request("tool_invoke", tool="lexer", arguments=[], semanticTarget={
                "document": f"doc-{index}", "revision": "sha256:" + hashlib.sha256(raw).hexdigest(), "entryFunctions": [],
            }))
        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        for response_index, expected_offset in zip(range(6, len(responses), 2), [0, 0, 0, 0, 2]):
            report = fields(responses[response_index]["result"])
            self.assertEqual(report["errorCode"]["value"], "PEP_INVALID_UTF8")
            self.assertEqual(report["errorStart"]["value"], str(expected_offset))

    def test_open_bytes_rejects_non_byte_values_and_oversized_input(self):
        result = invoke_session([
            {"schemaVersion": 3, "op": "open_bytes", "bytes": [256]},
            {"schemaVersion": 3, "op": "open_bytes", "bytes": [0] * 65537},
        ])
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(responses[0]["error"]["code"], "PEP_SOURCE_BYTE_VALUE")
        self.assertEqual(responses[1]["error"]["code"], "PEP_SOURCE_BYTE_LIMIT")

    def test_byte_bounds_and_utf8_slice_boundaries_are_explicit(self):
        source = (
            "fn probe() -> Int { return byte_at(source_bytes(), byte_length(source_bytes()) - 1) }\n"
            "fn slice_probe() -> Str { return utf8_slice(source_bytes(), 0, 1) }\n"
        )
        ordinary = "x"
        empty = ""
        accented = "é"
        requests = [
            request("open", source=source), request("open", source=ordinary),
            request("open", source=empty), request("open", source=accented),
            request("tool_register", tool="probe", document="doc-1", revision=revision(source), function="probe"),
            request("tool_validate", tool="probe", document="doc-1", revision=revision(source), testVectors=[{
                "arguments": [], "expect": scalar("Int", "120"),
                "semanticTarget": {"document": "doc-2", "revision": revision(ordinary), "entryFunctions": []},
            }]),
            request("tool_activate", tool="probe", document="doc-1", revision=revision(source)),
            request("tool_invoke", tool="probe", arguments=[]),
            request("tool_invoke", tool="probe", arguments=[], semanticTarget={
                "document": "doc-3", "revision": revision(empty), "entryFunctions": [],
            }),
            request("tool_register", tool="slice", document="doc-1", revision=revision(source), function="slice_probe"),
            request("tool_validate", tool="slice", document="doc-1", revision=revision(source), testVectors=[{
                "arguments": [], "expect": scalar("Str", "x"),
                "semanticTarget": {"document": "doc-2", "revision": revision(ordinary), "entryFunctions": []},
            }]),
            request("tool_activate", tool="slice", document="doc-1", revision=revision(source)),
            request("tool_invoke", tool="slice", arguments=[], semanticTarget={
                "document": "doc-4", "revision": revision(accented), "entryFunctions": [],
            }),
        ]
        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(responses[5]["status"], "Validated", responses[5])
        self.assertEqual(responses[7]["error"]["code"], "PEP_RUNTIME_SOURCE_CONTEXT")
        self.assertEqual(responses[8]["error"]["code"], "PEP_RUNTIME_BYTE_RANGE")
        self.assertEqual(responses[10]["status"], "Validated", responses[10])
        self.assertEqual(responses[12]["error"]["code"], "PEP_RUNTIME_BYTE_BOUNDARY")

    def test_raw_byte_slice_may_split_utf8_for_bytewise_scanning(self):
        source = "fn first() -> Int { return byte_at(byte_slice(source_bytes(), 0, 1), 0) }\n"
        target = "é"
        requests = [
            request("open", source=source), request("open", source=target),
            request("tool_register", tool="first", document="doc-1", revision=revision(source), function="first"),
            request("tool_validate", tool="first", document="doc-1", revision=revision(source), testVectors=[{
                "arguments": [], "expect": scalar("Int", "195"),
                "semanticTarget": {"document": "doc-2", "revision": revision(target), "entryFunctions": []},
            }]),
            request("tool_activate", tool="first", document="doc-1", revision=revision(source)),
            request("tool_invoke", tool="first", arguments=[], semanticTarget={
                "document": "doc-2", "revision": revision(target), "entryFunctions": [],
            }),
        ]
        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(responses[3]["status"], "Validated", responses[3])
        self.assertEqual(responses[5]["result"]["value"], "195")
        self.assertEqual(responses[5]["revision"], revision(source))

    def test_source_bytes_is_opaque_and_utf8_conversion_is_explicit(self):
        invalid_text = "fn bad_text() -> Str { return source_bytes() }\n"
        source = (
            "type RawBox { raw: SourceBytes }\n"
            "fn raw_result() -> SourceBytes { return source_bytes() }\n"
            "fn nested_result() -> List[RawBox] { return [RawBox { raw: source_bytes() }] }\n"
            "fn raw_length() -> Int { return byte_length(source_bytes()) }\n"
            "fn as_text() -> Str { return utf8_slice(source_bytes(), 0, byte_length(source_bytes())) }\n"
        )
        raw = bytes([255])
        ordinary = "x"
        requests = [
            request("open", source=invalid_text),
            request("open", source=source),
            {"schemaVersion": 3, "op": "open_bytes", "bytes": list(raw)},
            request("open", source=ordinary),
            request("tool_register", tool="length", document="doc-2", revision=revision(source), function="raw_length"),
            request("tool_validate", tool="length", document="doc-2", revision=revision(source), testVectors=[{
                "arguments": [], "expect": scalar("Int", "1"),
                "semanticTarget": {"document": "doc-3", "revision": "sha256:" + hashlib.sha256(raw).hexdigest(), "entryFunctions": []},
            }]),
            request("tool_activate", tool="length", document="doc-2", revision=revision(source)),
            request("tool_invoke", tool="length", arguments=[], semanticTarget={
                "document": "doc-3", "revision": "sha256:" + hashlib.sha256(raw).hexdigest(), "entryFunctions": [],
            }),
            request("tool_register", tool="raw", document="doc-2", revision=revision(source), function="raw_result"),
            request("tool_validate", tool="raw", document="doc-2", revision=revision(source), testVectors=[]),
            request("tool_register", tool="nested", document="doc-2", revision=revision(source), function="nested_result"),
            request("tool_validate", tool="nested", document="doc-2", revision=revision(source), testVectors=[]),
            request("tool_register", tool="text", document="doc-2", revision=revision(source), function="as_text"),
            request("tool_validate", tool="text", document="doc-2", revision=revision(source), testVectors=[{
                "arguments": [], "expect": scalar("Str", ordinary),
                "semanticTarget": {"document": "doc-4", "revision": revision(ordinary), "entryFunctions": []},
            }]),
            request("tool_activate", tool="text", document="doc-2", revision=revision(source)),
            request("tool_invoke", tool="text", arguments=[], semanticTarget={
                "document": "doc-3", "revision": "sha256:" + hashlib.sha256(raw).hexdigest(), "entryFunctions": [],
            }),
        ]
        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(responses[0]["status"], "invalid", responses[0])
        self.assertEqual(responses[5]["status"], "Validated", responses[5])
        self.assertEqual(responses[7]["result"]["value"], "1")
        self.assertEqual(responses[9]["status"], "Rejected", responses[9])
        self.assertIn("Version 2 supports only", responses[9]["error"])
        self.assertEqual(responses[11]["status"], "Rejected", responses[11])
        self.assertIn("Version 2 supports only", responses[11]["error"])
        self.assertEqual(responses[13]["status"], "Validated", responses[13])
        self.assertEqual(responses[15]["error"]["code"], "PEP_RUNTIME_INVALID_UTF8")

    def test_retained_source_bytes_are_revision_bound_and_errors_do_not_mutate(self):
        original = "# 😀\r\nlet x = 42 <= 43\n"
        edited = original.replace("42", "105")
        _, requests = lexer_requests(original)
        lexer_source = requests[0]["source"] + "\nfn source_echo() -> Str { return utf8_slice(source_bytes(), 0, byte_length(source_bytes())) }\n"
        requests[0]["source"] = lexer_source
        for index in (2, 3, 4):
            requests[index]["revision"] = revision(lexer_source)
        requests.extend([
            request("tool_register", tool="echo", document="doc-1", revision=revision(lexer_source), function="source_echo"),
            request("tool_validate", tool="echo", document="doc-1", revision=revision(lexer_source), testVectors=[{
                "arguments": [], "expect": scalar("Str", ""),
                "semanticTarget": {"document": "doc-2", "revision": revision(""), "entryFunctions": []},
            }]),
            request("tool_activate", tool="echo", document="doc-1", revision=revision(lexer_source)),
        ])
        start = original.encode("utf-8").index(b"42")
        requests.extend([
            {"schemaVersion": 3, "op": "apply_edit", "document": "doc-3",
             "expected_revision": revision(original), "start_byte": start, "end_byte": start + 2,
             "replacement": "105"},
            request("tool_invoke", tool="lexer", arguments=[], semanticTarget={
                "document": "doc-3", "revision": revision(original), "entryFunctions": [],
            }),
            request("tool_invoke", tool="lexer", arguments=[], semanticTarget={
                "document": "doc-3", "revision": revision(edited), "entryFunctions": [],
            }),
            request("tool_invoke", tool="echo", arguments=[], semanticTarget={
                "document": "doc-3", "revision": revision(original), "entryFunctions": [],
            }),
            request("tool_invoke", tool="echo", arguments=[], semanticTarget={
                "document": "doc-3", "revision": revision(edited), "entryFunctions": [],
            }),
            {"schemaVersion": 3, "op": "apply_edit", "document": "doc-3",
             "expected_revision": revision(original), "start_byte": start, "end_byte": start + 2,
             "replacement": "999"},
            request("tool_invoke", tool="lexer", arguments=[], semanticTarget={
                "document": "doc-404", "revision": revision(original), "entryFunctions": [],
            }),
            request("tool_invoke", tool="lexer", arguments=[], semanticTarget={
                "document": "doc-3", "revision": "sha256:" + "0" * 64, "entryFunctions": [],
            }),
            request("tool_invoke", tool="lexer", arguments=[]),
            request("tool_invoke", tool="lexer", arguments=[], semanticTarget={
                "document": "doc-3", "revision": revision(original), "entryFunctions": [],
            }),
        ])
        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(responses), len(requests))
        initial, edit_result, old_again, new_report = responses[6], responses[10], responses[11], responses[12]
        stale, unknown_document, unknown_revision, unauthorized, after_errors = responses[15:20]
        self.assertEqual(initial["revision"], revision(lexer_source))
        self.assertEqual(fields(initial["result"])["revision"]["value"], revision(original))
        self.assertEqual(fields(old_again["result"])["revision"]["value"], revision(original))
        old_tokens = fields(old_again["result"])["tokens"]["value"]
        old_numbers = [(fields(token)["startByte"]["value"], fields(token)["endByte"]["value"],
                        fields(token)["lexeme"]["value"]) for token in old_tokens if fields(token)["kind"]["value"] == "number"]
        self.assertEqual(old_numbers, [("16", "18", "42"), ("22", "24", "43")])
        self.assertEqual(new_report["revision"], revision(lexer_source))
        self.assertEqual(fields(new_report["result"])["revision"]["value"], revision(edited))
        new_tokens = fields(new_report["result"])["tokens"]["value"]
        new_numbers = [(fields(token)["startByte"]["value"], fields(token)["endByte"]["value"],
                        fields(token)["lexeme"]["value"]) for token in new_tokens if fields(token)["kind"]["value"] == "number"]
        self.assertEqual(new_numbers, [("16", "19", "105"), ("23", "25", "43")])
        self.assertEqual(stale["error"]["code"], "PEP_STALE_REVISION")
        self.assertEqual(unknown_document["error"]["code"], "PEP_DOCUMENT_NOT_FOUND")
        self.assertEqual(unknown_revision["error"]["code"], "PEP_REVISION_NOT_FOUND")
        self.assertEqual(unauthorized["error"]["code"], "PEP_RUNTIME_SEMANTIC_CONTEXT")
        self.assertEqual(fields(after_errors["result"])["revision"]["value"], revision(original))
        self.assertEqual(responses[13]["result"], scalar("Str", original))
        self.assertEqual(responses[14]["result"], scalar("Str", edited))
        self.assertEqual(responses[13]["revision"], revision(lexer_source))
        self.assertEqual(responses[14]["revision"], revision(lexer_source))
        self.assertEqual(edit_result["revision"], revision(edited))
        self.assertEqual(old_again["revision"], revision(lexer_source))
        self.assertEqual(new_report["revision"], revision(lexer_source))

    def test_step_limit_failure_leaves_the_session_usable(self):
        source = "# scan target\n"
        _, requests = lexer_requests(source)
        requests = requests[:5] + [request("open", source="name " * 256, name="large")]
        requests.append(request("tool_invoke", tool="lexer", arguments=[], semanticTarget={
            "document": "doc-3", "revision": revision("name " * 256), "entryFunctions": [],
        }))
        requests.append(request("open", source="let x = 1\n", name="small"))
        requests.append(request("tool_invoke", tool="lexer", arguments=[], semanticTarget={
            "document": "doc-4", "revision": revision("let x = 1\n"), "entryFunctions": [],
        }))
        result = invoke_session(requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(responses[6]["error"]["code"], "PEP_RUNTIME_STEP_LIMIT")
        self.assertEqual(responses[8]["outcome"], "ok", responses[8])
        self.assertEqual(result_field(responses[8]["result"], "revision"), revision("let x = 1\n"))


if __name__ == "__main__":
    unittest.main()