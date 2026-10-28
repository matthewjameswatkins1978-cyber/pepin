import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
SOURCES = (
    ROOT / "examples" / "pep_lexer.pep",
    ROOT / "examples" / "pep_parser.pep",
    ROOT / "tests" / "pep_checker_a13.pep",
    ROOT / "tests" / "pep_c23_emitter.pep",
)


class Session:
    def __init__(self):
        self.process = subprocess.Popen(
            ["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"), "session", "--jsonl"],
            cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8", bufsize=1,
        )

    def send(self, request):
        self.process.stdin.write(json.dumps(request, ensure_ascii=False, separators=(",", ":")) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            detail = self.process.stderr.read()
            raise RuntimeError("Pep session ended without a response" + (": " + detail.strip() if detail else ""))
        try:
            return json.loads(line)
        except json.JSONDecodeError as error:
            raise RuntimeError("Pep session returned invalid JSON: " + line[:400]) from error

    def close(self):
        if self.process.poll() is None:
            self.process.stdin.close()
            self.process.wait(timeout=30)
        detail = self.process.stderr.read()
        self.process.stdout.close()
        self.process.stderr.close()
        if self.process.returncode:
            raise RuntimeError(f"Pep session exited {self.process.returncode}: {detail.strip()}")


def require(response, key, expected, label):
    actual = response.get(key)
    if actual != expected:
        raise RuntimeError(f"{label}: expected {key}={expected!r}, received {response!r}")


def typed_record(status, parts=(), diagnostic=""):
    return {
        "type": "PepC23Emission",
        "fields": [
            {"name": "status", "value": {"type": "Str", "value": status}},
            {"name": "sourceParts", "value": {"type": "List[Str]", "value": [
                {"type": "Str", "value": part} for part in parts
            ]}},
            {"name": "diagnostic", "value": {"type": "Str", "value": diagnostic}},
        ],
    }


def typed(type_name, value):
    return {"type": type_name, "value": str(value) if type_name == "Int" else value}


def typed_list(item_type, values=()):
    return {"type": f"List[{item_type}]", "value": list(values)}


def typed_record_value(type_name, fields):
    return {"type": type_name, "fields": [
        {"name": name, "value": value} for name, value in fields
    ]}


def parser_progress(document, revision):
    return typed_record_value("ParserProgress", [
        ("document", typed("Str", document)), ("revision", typed("Str", revision)),
        ("status", typed("Str", "complete")), ("nodes", typed_list("FlatAstNode")),
        ("done", typed("Bool", True)), ("errorCode", typed("Str", "")),
        ("message", typed("Str", "")), ("errorStart", typed("Int", 0)),
        ("errorEnd", typed("Int", 0)), ("errorLine", typed("Int", 0)),
        ("errorColumn", typed("Int", 0)),
    ])


def checker_report(document, revision):
    fields = [("document", typed("Str", document)), ("revision", typed("Str", revision)),
              ("status", typed("Str", "valid")), ("syntaxNodeCount", typed("Int", 0))]
    for name, item_type in (("functions", "CheckedFunction"), ("bindings", "BindingFact"),
                            ("references", "ResolvedName"), ("calls", "ResolvedCall"),
                            ("expressionTypes", "ExpressionTypeFact"), ("holes", "HoleFact"),
                            ("diagnostics", "CheckDiagnostic")):
        fields.append((name, typed_list(item_type)))
    return typed_record_value("CheckerReport", fields)


def emit(source_bytes):
    try:
        bundle = "\n".join(path.read_text(encoding="utf-8") for path in SOURCES)
    except OSError as error:
        raise RuntimeError(f"cannot read Pep C23 compiler source: {error}") from error
    session = Session()
    try:
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                              "name": "pep-c23-emitter", "metadataOnly": True})
        require(opened, "outcome", "ok", "open compiler bundle")
        require(opened, "status", "valid", "check compiler bundle")
        tool_document, tool_revision = opened["document"], opened["revision"]
        sample = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "stage-validation", "bytes": []})
        require(sample, "outcome", "ok", "open stage validation source")
        empty_parsed = parser_progress(sample["document"], sample["revision"])
        empty_checked = checker_report(sample["document"], sample["revision"])
        target_spec = {"document": sample["document"], "revision": sample["revision"], "entryFunctions": []}
        empty_expected = [
            ("pep-c23-parser", "parser_parse_program", [], empty_parsed),
            ("pep-c23-checker", "analyze_parsed", [empty_parsed], empty_checked),
        ]
        for tool, function, arguments, expected in empty_expected:
            registered = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_register", "tool": tool,
                                      "document": tool_document, "revision": tool_revision,
                                      "function": function})
            require(registered, "status", "Registered", f"register {tool}")
            validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_validate", "tool": tool,
                                      "document": tool_document, "revision": tool_revision,
                                      "testVectors": [{"arguments": arguments, "expect": expected,
                                          "semanticTarget": target_spec}]})
            require(validated, "status", "Validated", f"validate {tool}")
            active = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                   "op": "tool_activate", "tool": tool,
                                   "document": tool_document, "revision": tool_revision})
            require(active, "status", "Active", f"activate {tool}")
        registered = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                  "op": "tool_register", "tool": "pep-c23-emitter",
                                  "document": tool_document, "revision": tool_revision,
                                  "function": "emit_c23_checked"})
        require(registered, "status", "Registered", "register emitter")
        expected_emission = typed_record("unsupported", (),
                                         "Pep C23 emission requires a top-level function named main")
        validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                  "op": "tool_validate", "tool": "pep-c23-emitter",
                                  "document": tool_document, "revision": tool_revision,
                                  "testVectors": [{"arguments": [empty_parsed, empty_checked],
                                      "expect": expected_emission, "semanticTarget": target_spec}]})
        require(validated, "status", "Validated", "validate emitter")
        activated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                  "op": "tool_activate", "tool": "pep-c23-emitter",
                                  "document": tool_document, "revision": tool_revision})
        require(activated, "status", "Active", "activate emitter")

        target = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "native-target",
                               "bytes": list(source_bytes)})
        require(target, "outcome", "ok", "open source")
        semantic_target = {"document": target["document"], "revision": target["revision"], "entryFunctions": []}
        parsed = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                               "op": "tool_invoke", "tool": "pep-c23-parser", "arguments": [],
                               "semanticTarget": semantic_target})
        require(parsed, "outcome", "ok", "parse source")
        parsed_value = parsed["result"]
        checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-checker",
                                "arguments": [parsed_value], "semanticTarget": semantic_target})
        require(checked, "outcome", "ok", "check parsed source")
        emitted = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-emitter",
                                "arguments": [parsed_value, checked["result"]],
                                "semanticTarget": semantic_target})
        require(emitted, "outcome", "ok", "emit checked source")
        require(emitted, "revision", tool_revision, "verify emitter revision")
        fields = {item["name"]: item["value"] for item in emitted["result"]["fields"]}
        if fields["status"]["value"] != "emitted":
            raise ValueError(fields["diagnostic"]["value"] or "Pep C23 emitter rejected the program")
        return "".join(part["value"] for part in fields["sourceParts"]["value"])
    finally:
        session.close()


def compiler_path(requested):
    candidates = ([requested] if requested else ["clang", "clang.exe",
        str(pathlib.Path.home() / "scoop" / "apps" / "llvm" / "current" / "bin" / "clang.exe")])
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return pathlib.Path(resolved)
        path = pathlib.Path(candidate)
        if path.is_file():
            return path.resolve()
    wanted = requested or "Clang"
    raise RuntimeError(f"C23 compiler not found: {wanted}; install Clang or pass --compiler PATH")


def parser():
    result = argparse.ArgumentParser(prog="pep.ps1 build-c23/run-c23",
        description="Build or run the supported Pep subset through the Pep-written strict C23 emitter.")
    result.add_argument("command", choices=("build-c23", "run-c23"))
    result.add_argument("source", type=pathlib.Path)
    result.add_argument("-o", "--output", type=pathlib.Path,
                        help="native executable path (required for build-c23)")
    result.add_argument("--compiler", help="Clang executable path (defaults to Clang on PATH)")
    result.add_argument("--emit-c", type=pathlib.Path,
                        help="generated C23 source path (defaults beside the executable)")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    source_path = args.source.resolve()
    if not source_path.is_file():
        print(f"Pep source file not found: {source_path}", file=sys.stderr)
        return 2
    if args.command == "build-c23" and args.output is None:
        print("build-c23 requires -o/--output", file=sys.stderr)
        return 2
    try:
        source_bytes = source_path.read_bytes()
        source_identity = hashlib.sha256(source_bytes).hexdigest()[:12]
        default_name = f"{source_path.stem}-{source_identity}.exe"
        output = (args.output or (ROOT / "_build" / "native" / default_name)).resolve()
        c_path = (args.emit_c or output.with_suffix(".c")).resolve()
        if source_path == output or source_path == c_path or output == c_path:
            raise ValueError("Pep source, generated C, and executable paths must be distinct")
        compiler = compiler_path(args.compiler)
        source = emit(source_bytes)
        c_path.parent.mkdir(parents=True, exist_ok=True)
        output.parent.mkdir(parents=True, exist_ok=True)
        c_path.write_text(source, encoding="utf-8", newline="\n")
        built = subprocess.run([str(compiler), "-std=c23", "-Wall", "-Wextra", "-Wpedantic",
                                "-Werror", "-O2", str(c_path), "-o", str(output)],
                               text=True, capture_output=True, check=False)
        if built.stdout:
            print(built.stdout, end="")
        if built.stderr:
            print(built.stderr, end="", file=sys.stderr)
        if built.returncode:
            return built.returncode
        stream = sys.stderr if args.command == "run-c23" else sys.stdout
        print(f"C23: {c_path}", file=stream)
        print(f"Executable: {output}", file=stream)
        if args.command == "run-c23":
            ran = subprocess.run([str(output)], text=True, check=False)
            return ran.returncode
        return 0
    except ValueError as error:
        print(f"Pep C23 unsupported: {error}", file=sys.stderr)
        return 2
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Pep C23 error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
