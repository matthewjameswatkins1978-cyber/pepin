"""Reproducible warm JSONL measurements for the Pep-written A11 lexer."""

import json
import pathlib
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.test_a11 import A11DifferentialTests  # noqa: E402


def cases():
    examples = ROOT / "examples"
    return [
        ("identifiers-16", b"name " * 16),
        ("identifiers-64", b"name " * 64),
        ("identifiers-256", b"name " * 256),
        ("identifiers-1024", b"name " * 1024),
        ("single-long-identifier", b"n" * 16384),
        ("long-comment", b"#" + b"comment-" * 2048 + b"\r\n"),
        ("punctuation-dense", b"+," * 2048),
        ("escape-dense-string", b'"' + b"\\n" * 512 + b'"'),
        ("long-unescaped-string", b'"' + b"x" * 16384 + b'"'),
        ("repo-a8-analyser", (examples / "unused_functions.pep").read_bytes()),
        ("repo-a11-lexer", (examples / "pep_lexer.pep").read_bytes()),
    ]


def main():
    A11DifferentialTests.setUpClass()
    worker = A11DifferentialTests("test_chunked_scan_is_revision_bound_and_has_forward_progress")
    try:
        worker.setUp()
        print(json.dumps({"environment": "Windows warm schema-v3 JSONL session", "sessionStartMs": worker.session_start_ms}))
        for name, raw in cases():
            rows = []
            for _ in range(3):
                result = worker.pep_lex(raw)
                if result["error"]:
                    raise RuntimeError(f"{name} failed: {result['error']}")
                rows.append(worker.last_lex_metrics)
            for key in ("openMs", "invokeMs", "validateMs", "scanMs", "responseBytes"):
                values = [row[key] for row in rows]
                summary = {"min": min(values), "median": statistics.median(values), "max": max(values)}
                rows[0][key] = summary
            rows[0]["case"] = name
            print(json.dumps(rows[0], ensure_ascii=False, separators=(",", ":")))
    finally:
        worker.tearDown()
        A11DifferentialTests.tearDownClass()


if __name__ == "__main__":
    main()
