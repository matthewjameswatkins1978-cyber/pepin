"""Runtime and transport measurements for PEP-PERFORMANCE-01.

This is an external, test-only harness. It does not change the JSONL protocol,
execution budgets, or production source inputs. Results are JSON Lines so a
later run can be compared without scraping human output.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import pathlib
import statistics
import subprocess
import threading
import sys
import time
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
PEP_SCRIPT = ROOT / "pep.ps1"
PEP_EXE = ROOT / "_build" / "ocaml" / "pep.exe"
PROFILE_EXE = ROOT / "_build" / "perf" / "pep-profile.exe"
LEXER = ROOT / "examples" / "pep_lexer.pep"
A8_ANALYSER = ROOT / "examples" / "unused_functions.pep"


def revision(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def typed(kind: str, value: Any) -> dict[str, Any]:
    return {"type": kind, "value": value}


def typed_record(name: str, fields: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    return {"type": name, "fields": [{"name": key, "value": value} for key, value in fields]}


def typed_list(name: str, values: list[dict[str, Any]]) -> dict[str, Any]:
    return typed(f"List[{name}]", values)


def record_fields(value: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {field["name"]: field["value"] for field in value["fields"]}


def scalar_int(value: int) -> dict[str, Any]:
    return typed("Int", str(value))


def cursor_value(document: str, source_revision: str, stage: str) -> dict[str, Any]:
    return typed_record("LexCursor", [
        ("document", typed("Str", document)), ("revision", typed("Str", source_revision)),
        ("status", typed("Str", "valid")), ("stage", typed("Str", stage)),
        ("offset", scalar_int(0)), ("line", scalar_int(1)), ("column", scalar_int(1)),
        ("mode", typed("Str", "")), ("tokenStart", scalar_int(0)),
        ("tokenLine", scalar_int(1)), ("tokenColumn", scalar_int(1)),
        ("integerValue", scalar_int(0)), ("integerOverflow", typed("Bool", False)),
        ("escapePending", typed("Bool", False)), ("stringPartStart", scalar_int(0)),
        ("stringPartsReversed", typed_list("Str", [])),
    ])


def empty_progress(document: str, source_revision: str) -> dict[str, Any]:
    eof = typed_record("LexToken", [
        ("kind", typed("Str", "eof")), ("text", typed("Str", "")),
        ("integerValue", scalar_int(0)), ("stringParts", typed_list("Str", [])),
        ("startByte", scalar_int(0)), ("endByte", scalar_int(0)),
        ("line", scalar_int(1)), ("column", scalar_int(1)),
    ])
    return typed_record("LexProgress", [
        ("document", typed("Str", document)), ("revision", typed("Str", source_revision)),
        ("status", typed("Str", "valid")), ("tokens", typed_list("LexToken", [eof])),
        ("cursor", cursor_value(document, source_revision, "done")),
        ("done", typed("Bool", True)), ("errorCode", typed("Str", "")),
        ("errorStart", scalar_int(0)), ("errorEnd", scalar_int(0)),
        ("errorLine", scalar_int(0)), ("errorColumn", scalar_int(0)),
    ])


class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_uint32), ("PageFaultCount", ctypes.c_uint32),
        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]


def process_memory(pid: int) -> dict[str, int] | None:
    if os.name != "nt":
        return None
    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not handle:
        return None
    try:
        counters = PROCESS_MEMORY_COUNTERS_EX()
        counters.cb = ctypes.sizeof(counters)
        if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            return None
        return {
            "workingSetBytes": int(counters.WorkingSetSize),
            "privateBytes": int(counters.PrivateUsage),
        }
    finally:
        kernel32.CloseHandle(handle)


class SessionClient:
    def __init__(self, mode: str, profile: bool = False, executable: pathlib.Path | None = None):
        env = os.environ.copy()
        if profile:
            env["PEP_PROFILE"] = "1"
        else:
            env.pop("PEP_PROFILE", None)
        if mode == "powershell":
            command = ["pwsh", "-NoProfile", "-File", str(PEP_SCRIPT), "session", "--jsonl"]
        elif mode == "direct":
            command = [str(executable or PEP_EXE), "session", "--jsonl"]
        else:
            raise ValueError(f"unsupported mode: {mode}")
        started = time.perf_counter()
        self.process = subprocess.Popen(
            command, cwd=ROOT, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, bufsize=0,
        )
        self.spawn_ms = (time.perf_counter() - started) * 1000
        self.mode = mode
        self.samples: list[dict[str, int]] = []
        self._stderr_chunks: list[bytes] = []
        self._stderr_thread = threading.Thread(target=self._drain_stderr, daemon=True)
        self._stderr_thread.start()

    def _drain_stderr(self) -> None:
        assert self.process.stderr is not None
        self._stderr_chunks.append(self.process.stderr.read())

    def send(self, request: dict[str, Any]) -> tuple[dict[str, Any], dict[str, float | int]]:
        encoded_started = time.perf_counter()
        line = json.dumps(request, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
        encoded_finished = time.perf_counter()
        write_started = time.perf_counter()
        assert self.process.stdin is not None
        self.process.stdin.write(line)
        self.process.stdin.flush()
        write_finished = time.perf_counter()
        read_started = time.perf_counter()
        assert self.process.stdout is not None
        response_line = self.process.stdout.readline()
        read_finished = time.perf_counter()
        if not response_line:
            stderr = self.process.stderr.read().decode("utf-8", errors="replace") if self.process.stderr else ""
            raise RuntimeError(f"session ended without a response: {stderr}")
        parse_started = time.perf_counter()
        response = json.loads(response_line)
        parse_finished = time.perf_counter()
        memory = process_memory(self.process.pid)
        if memory:
            self.samples.append(memory)
        timing: dict[str, float | int] = {
            "requestBytes": len(line), "responseBytes": len(response_line),
            "requestEncodeMs": (encoded_finished - encoded_started) * 1000,
            "writeMs": (write_finished - write_started) * 1000,
            "readMs": (read_finished - read_started) * 1000,
            "parseMs": (parse_finished - parse_started) * 1000,
            "totalMs": (parse_finished - encoded_started) * 1000,
        }
        return response, timing

    def close(self) -> str:
        assert self.process.stdin is not None
        self.process.stdin.close()
        self.process.wait(timeout=60)
        self._stderr_thread.join(timeout=5)
        stderr = b"".join(self._stderr_chunks).decode("utf-8", errors="replace")
        if self.process.returncode != 0:
            raise RuntimeError(f"session exited {self.process.returncode}: {stderr}")
        return stderr


def target(document: str, raw: bytes) -> dict[str, Any]:
    return {"document": document, "revision": revision(raw), "entryFunctions": []}


def tool_request(operation: str, **fields: Any) -> dict[str, Any]:
    return {"schemaVersion": 3, "toolProtocolVersion": 2, "op": operation, **fields}


def aggregate_timings(rows: list[dict[str, float | int]]) -> dict[str, float | int]:
    if not rows:
        return {"count": 0}
    result: dict[str, float | int] = {"count": len(rows)}
    for key in ("requestBytes", "responseBytes"):
        result[key] = sum(int(row[key]) for row in rows)
    for key in ("requestEncodeMs", "writeMs", "readMs", "parseMs", "totalMs"):
        result[key] = round(sum(float(row[key]) for row in rows), 4)
    return result


def normalize_lexer(tokens: list[dict[str, Any]], error: dict[str, Any] | None) -> dict[str, Any]:
    if error:
        return {"tokens": [], "error": error}
    normalized = []
    for token in tokens:
        fields = record_fields(token)
        kind = fields["kind"]["value"]
        value = fields["text"]["value"]
        if kind == "integer":
            value = fields["integerValue"]["value"]
        elif kind == "string":
            value = "".join(part["value"] for part in fields["stringParts"]["value"])
        normalized.append({
            "kind": kind, "value": value,
            "startByte": int(fields["startByte"]["value"]), "endByte": int(fields["endByte"]["value"]),
            "line": int(fields["line"]["value"]), "column": int(fields["column"]["value"]),
        })
    return {"tokens": normalized, "error": None}


class LexerSession:
    def __init__(self, mode: str, source: str, profile: bool = False, executable: pathlib.Path | None = None):
        self.client = SessionClient(mode, profile=profile, executable=executable)
        opened, _ = self.client.send({"schemaVersion": 3, "op": "open", "name": "lexer", "source": source})
        self.tool_document = opened["document"]
        self.tool_revision = opened["revision"]
        empty, _ = self.client.send({"schemaVersion": 3, "op": "open", "name": "empty", "source": ""})
        empty_revision = revision(b"")
        empty_target = target(empty["document"], b"")
        start_cursor = cursor_value(empty["document"], empty_revision, "validate")
        requests = [
            tool_request("tool_register", tool="lexer-start", document=self.tool_document,
                         revision=self.tool_revision, function="lexer_start"),
            tool_request("tool_validate", tool="lexer-start", document=self.tool_document,
                         revision=self.tool_revision, testVectors=[{"arguments": [], "expect": start_cursor,
                                                                    "semanticTarget": empty_target}]),
            tool_request("tool_activate", tool="lexer-start", document=self.tool_document,
                         revision=self.tool_revision),
            tool_request("tool_register", tool="lexer-step", document=self.tool_document,
                         revision=self.tool_revision, function="lexer_step"),
            tool_request("tool_validate", tool="lexer-step", document=self.tool_document,
                         revision=self.tool_revision, testVectors=[{"arguments": [cursor_value(empty["document"], empty_revision, "scan")],
                                                                    "expect": empty_progress(empty["document"], empty_revision),
                                                                    "semanticTarget": empty_target}]),
            tool_request("tool_activate", tool="lexer-step", document=self.tool_document,
                         revision=self.tool_revision),
        ]
        for request in requests:
            response, _ = self.client.send(request)
            if response.get("outcome") not in ("ok", None) or response.get("status") not in (None, "Validated", "Active", "Registered"):
                raise RuntimeError(f"lexer setup failed: {response}")

    def lex(self, raw: bytes) -> tuple[dict[str, Any], dict[str, Any]]:
        opened, open_timing = self.client.send({"schemaVersion": 3, "op": "open_bytes", "name": "target", "bytes": list(raw)})
        if opened.get("outcome") != "ok":
            raise RuntimeError(opened)
        semantic_target = target(opened["document"], raw)
        started, start_timing = self.client.send(tool_request("tool_invoke", tool="lexer-start", arguments=[], semanticTarget=semantic_target))
        cursor = started["result"]
        tokens: list[dict[str, Any]] = []
        validation_rows: list[dict[str, float | int]] = []
        scan_rows: list[dict[str, float | int]] = []
        for _ in range(10000):
            stage = record_fields(cursor)["stage"]["value"]
            response, timing = self.client.send(tool_request("tool_invoke", tool="lexer-step", arguments=[cursor], semanticTarget=semantic_target))
            if response.get("outcome") != "ok":
                raise RuntimeError(response)
            (validation_rows if stage == "validate" else scan_rows).append(timing)
            fields = record_fields(response["result"])
            tokens.extend(fields["tokens"]["value"])
            if fields["done"]["value"]:
                error = None
                if fields["errorCode"]["value"]:
                    error = {
                        "code": fields["errorCode"]["value"], "startByte": int(fields["errorStart"]["value"]),
                        "endByte": int(fields["errorEnd"]["value"]), "line": int(fields["errorLine"]["value"]),
                        "column": int(fields["errorColumn"]["value"]),
                    }
                metrics = {
                    "bytes": len(raw), "tokens": len(tokens), "open": open_timing,
                    "start": start_timing, "validate": aggregate_timings(validation_rows),
                    "scan": aggregate_timings(scan_rows),
                    "requests": aggregate_timings([start_timing] + validation_rows + scan_rows),
                }
                return normalize_lexer(tokens, error), metrics
            cursor = fields["cursor"]
        raise RuntimeError("lexer exceeded 10,000 resumptions")

    def close(self) -> str:
        return self.client.close()


def parse_profile(stderr: str) -> list[dict[str, Any]]:
    rows = []
    for line in stderr.splitlines():
        if line.startswith("PEP_PROFILE "):
            rows.append(json.loads(line[len("PEP_PROFILE "):]))
    return rows


def lexer_cases() -> list[tuple[str, bytes]]:
    return [
        ("identifiers-16", b"name " * 16),
        ("identifiers-64", b"name " * 64),
        ("identifiers-256", b"name " * 256),
        ("identifiers-1024", b"name " * 1024),
        ("punctuation-dense", b"+," * 2048),
        ("long-unescaped-string", b'"' + b"x" * 16384 + b'"'),
        ("repo-a8-analyser", A8_ANALYSER.read_bytes()),
        ("repo-a11-lexer", LEXER.read_bytes()),
    ]


def lexer_variant_source(width: int) -> str:
    source = LEXER.read_text(encoding="utf-8")
    first = "while !(32 <= processed)"
    second = "processed = 32"
    if source.count(first) != 1 or source.count(second) != 1:
        raise RuntimeError(f"unexpected lexer chunk markers for width {width}")
    return source.replace(first, f"while !({width} <= processed)", 1).replace(second, f"processed = {width}", 1)


def typed_result_source(count: int) -> tuple[str, dict[str, Any]]:
    items = []
    expected_items = []
    for index in range(count):
        leaves = ", ".join(
            f'Leaf {{ index: {index * 3 + offset}, text: "leaf-{index}-{offset}" }}'
            for offset in range(3)
        )
        items.append(f'Item {{ name: "item-{index}", leaves: [{leaves}] }}')
        expected_items.append(typed_record("Item", [
            ("name", typed("Str", f"item-{index}")),
            ("leaves", typed_list("Leaf", [
                typed_record("Leaf", [("index", scalar_int(index * 3 + offset)),
                                       ("text", typed("Str", f"leaf-{index}-{offset}"))])
                for offset in range(3)
            ])),
        ]))
    source = (
        "type Leaf { index: Int, text: Str }\n"
        "type Item { name: Str, leaves: List[Leaf] }\n"
        "fn build() -> List[Item] { return [" + ", ".join(items) + "] }\n"
    )
    return source, typed_list("Item", expected_items)


def run_typed_result(mode: str, count: int, profile: bool = False) -> dict[str, Any]:
    source, expected = typed_result_source(count)
    executable = build_profile_exe() if profile and mode == "direct" else None
    client = SessionClient(mode, profile=profile, executable=executable)
    setup_rows: list[dict[str, float | int]] = []
    try:
        opened, timing = client.send({"schemaVersion": 3, "op": "open", "name": "typed", "source": source})
        setup_rows.append(timing)
        document, source_revision = opened["document"], opened["revision"]
        for request in [
            tool_request("tool_register", tool="typed-result", document=document,
                         revision=source_revision, function="build"),
            tool_request("tool_validate", tool="typed-result", document=document,
                         revision=source_revision, testVectors=[{"arguments": [], "expect": expected}]),
            tool_request("tool_activate", tool="typed-result", document=document,
                         revision=source_revision),
        ]:
            response, row = client.send(request)
            setup_rows.append(row)
            if response.get("outcome") not in ("ok", None) and response.get("status") not in ("Validated", "Active", "Registered"):
                raise RuntimeError(response)
        invoked, invoke_timing = client.send(tool_request("tool_invoke", tool="typed-result", arguments=[]))
        if invoked.get("outcome") != "ok" or invoked.get("result") != expected:
            raise RuntimeError("typed result correctness check failed")
        stderr = client.close()
        return {
            "kind": "typed-result", "mode": mode, "count": count,
            "sourceBytes": len(source.encode("utf-8")), "response": invoke_timing,
            "setup": aggregate_timings(setup_rows), "memory": client.samples[-1] if client.samples else None,
            "peakMemory": {key: max((sample[key] for sample in client.samples), default=0)
                           for key in ("workingSetBytes", "privateBytes")},
            "profile": parse_profile(stderr),
        }
    except Exception:
        if client.process.poll() is None:
            client.process.kill()
        raise


def run_lexer(mode: str, source: str, raw: bytes, profile: bool = False) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    executable = build_profile_exe() if profile and mode == "direct" else None
    session = LexerSession(mode, source, profile=profile, executable=executable)
    try:
        result, metrics = session.lex(raw)
        stderr = session.close()
        process = {
            "spawnMs": round(session.client.spawn_ms, 4),
            "peakMemory": {key: max((sample[key] for sample in session.client.samples), default=0)
                           for key in ("workingSetBytes", "privateBytes")},
        }
        return result, metrics, parse_profile(stderr), process
    except Exception:
        if session.client.process.poll() is None:
            session.client.process.kill()
        raise


def build_profile_exe() -> pathlib.Path:
    global PROFILE_EXE
    if PROFILE_EXE.exists():
        return PROFILE_EXE
    profile_dir = PROFILE_EXE.parent
    profile_dir.mkdir(parents=True, exist_ok=True)
    profile_source = profile_dir / "pep_ocaml_profile.ml"
    source = (ROOT / "pep_ocaml.ml").read_text(encoding="utf-8")
    profile_source.write_text(source.replace("Sys.time()", "Unix.gettimeofday()"), encoding="utf-8")
    opam_root = os.environ.get("PEPIN_OPAM_ROOT", r"D:\opam-roots\pepin")
    result = subprocess.run(
        ["opam", "exec", "--root", opam_root, "--switch", "pepin-5.5.2", "--",
         "ocamlopt", "unix.cmxa", "-o", str(PROFILE_EXE), str(profile_source)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"profile build failed: {result.stderr}")
    return PROFILE_EXE


def ensure_build() -> None:
    result = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(PEP_SCRIPT), "describe", "--json"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    if result.returncode != 0 or not PEP_EXE.exists():
        raise RuntimeError(f"Pep build failed: {result.stderr}")


def emit(row: dict[str, Any]) -> None:
    print(json.dumps(row, ensure_ascii=False, separators=(",", ":")))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--modes", default="direct,powershell")
    parser.add_argument("--chunk-widths", default="16,32,64,128,256,512")
    args = parser.parse_args()
    ensure_build()
    modes = [item for item in args.modes.split(",") if item]
    cases = lexer_cases()
    base_source = LEXER.read_text(encoding="utf-8")

    for mode in modes:
        for name, raw in cases:
            rows = []
            correctness = None
            for _ in range(args.trials):
                result, metrics, _, process = run_lexer(mode, base_source, raw)
                if correctness is None:
                    correctness = result
                elif result != correctness:
                    raise RuntimeError(f"nondeterministic lexer result for {mode}/{name}")
                rows.append({"metrics": metrics, "process": process})
            median = statistics.median
            emit({
                "kind": "lexer", "mode": mode, "chunkWidth": 32, "case": name,
                "bytes": len(raw), "tokens": correctness and len(correctness["tokens"]),
                "trials": args.trials,
                "medianTotalMs": round(median([r["metrics"]["requests"]["totalMs"] for r in rows]), 4),
                "medianReadMs": round(median([r["metrics"]["requests"]["readMs"] for r in rows]), 4),
                "medianParseMs": round(median([r["metrics"]["requests"]["parseMs"] for r in rows]), 4),
                "medianResponseBytes": int(median([r["metrics"]["requests"]["responseBytes"] for r in rows])),
                "medianRequestBytes": int(median([r["metrics"]["requests"]["requestBytes"] for r in rows])),
                "medianValidateCalls": rows[0]["metrics"]["validate"]["count"],
                "medianScanCalls": rows[0]["metrics"]["scan"]["count"],
                "peakPrivateBytes": max(r["process"]["peakMemory"]["privateBytes"] for r in rows),
                "peakWorkingSetBytes": max(r["process"]["peakMemory"]["workingSetBytes"] for r in rows),
                "correct": True,
            })

    width_list = [int(item) for item in args.chunk_widths.split(",") if item]
    comparison_cases = [cases[-1], cases[-2], cases[4], cases[5]]
    baseline: dict[str, dict[str, Any]] = {}
    for name, raw in comparison_cases:
        baseline[name], _, _, _ = run_lexer("direct", base_source, raw)
    for width in width_list:
        source = lexer_variant_source(width)
        for name, raw in comparison_cases:
            timings = []
            variant_result = None
            for _ in range(args.trials):
                variant_result, metrics, _, process = run_lexer("direct", source, raw)
                timings.append((metrics, process))
            assert variant_result is not None
            emit({
                "kind": "chunk-variant", "mode": "direct", "chunkWidth": width,
                "case": name, "bytes": len(raw), "tokens": len(variant_result["tokens"]),
                "trials": args.trials,
                "medianTotalMs": round(statistics.median([item[0]["requests"]["totalMs"] for item in timings]), 4),
                "medianReadMs": round(statistics.median([item[0]["requests"]["readMs"] for item in timings]), 4),
                "medianResponseBytes": int(statistics.median([item[0]["requests"]["responseBytes"] for item in timings])),
                "stepCalls": timings[0][0]["requests"]["count"],
                "peakPrivateBytes": max(item[1]["peakMemory"]["privateBytes"] for item in timings),
                "peakWorkingSetBytes": max(item[1]["peakMemory"]["workingSetBytes"] for item in timings),
                "correctAgainstWidth32": variant_result == baseline[name],
            })

    for mode in ("direct",):
        result, metrics, profiles, process = run_lexer(mode, base_source, LEXER.read_bytes(), profile=True)
        emit({
            "kind": "profile", "mode": mode, "case": "repo-a11-lexer", "bytes": len(LEXER.read_bytes()),
            "resultTokens": len(result["tokens"]), "metrics": metrics["requests"], "profiles": profiles,
            "process": process,
        })

    for mode in modes:
        for count in (8, 32, 128, 256):
            emit(run_typed_result(mode, count, profile=False))
    emit(run_typed_result("direct", 256, profile=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())


