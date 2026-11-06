"""How much does STAGING buy? The same question as the 144-byte ceiling, asked of the
three-invocation path instead of the single-budget one.

`tests/probe_frontend_budget_ceiling.py` measures the zero-argument `emit_c23()` entry:
parse + check + emit inside ONE 100k budget, which buys 144 bytes.

This probe measures the STAGED path the host actually uses -- `parse_target`, then the
`pep-c23-checker` tool, then the `pep-c23-emitter` tool, each in its own invocation
with its own budget -- and finds the ceiling for each phase separately.

That number is what a staged-checking design has to beat, so it is worth having
explicitly rather than inferring it from failures elsewhere.

Run: python tests/probe_staged_budget_ceiling.py
"""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_build"))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target  # noqa: E402

# A program of controllable size: N independent one-line functions plus main.
def program(function_count):
    body = "".join(f"fn pad{index}() -> Int {{ return {index} }}\n"
                   for index in range(function_count))
    return body + "fn main() -> Int { return pad0() }\n"


COUNTS = [1, 5, 10, 20, 40, 80]


def measure(session, revision, source, label):
    """Return (parse, check, emit) outcomes, each named, never raising."""
    payload = source.encode("utf-8")
    target = session.send({"schemaVersion": 3, "op": "open_bytes",
                           "name": label, "bytes": list(payload)})
    if target.get("outcome") != "ok":
        return "open:" + str((target.get("error") or {}).get("code")), None, None
    semantic = {"document": target["document"], "revision": target["revision"],
                "entryFunctions": []}
    try:
        parsed = parse_target(session, payload, target, revision)
        parse_result = "ok"
    except Exception as error:  # noqa: BLE001
        text = str(error)
        for code in ("PEP_RUNTIME_STEP_LIMIT", "PEP_TOOL_VALUE_LIMIT",
                     "PEP_SOURCE_BYTE_LIMIT"):
            if code in text:
                return code, None, None
        return "parse-failed", None, None

    try:
        checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-checker",
                                "arguments": [parsed], "semanticTarget": semantic})
    except RuntimeError as error:
        return parse_result, "transport:" + str(error)[:40], None
    if checked.get("outcome") != "ok":
        return parse_result, (checked.get("error") or {}).get("code"), None
    cfields = {f["name"]: f["value"] for f in checked["result"]["fields"]}
    if cfields["status"]["value"] != "valid":
        return parse_result, "invalid", None

    try:
        emitted = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-emitter",
                                "arguments": [parsed, checked["result"]],
                                "semanticTarget": semantic})
    except RuntimeError as error:
        return parse_result, "ok", "transport:" + str(error)[:40]
    if emitted.get("outcome") != "ok":
        return parse_result, "ok", (emitted.get("error") or {}).get("code")
    efields = {f["name"]: f["value"] for f in emitted["result"]["fields"]}
    return parse_result, "ok", efields["status"]["value"]


def main():
    session = Session()
    try:
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "pep-c23-emitter", "metadataOnly": True})
        require(opened, "outcome", "ok", "open compiler bundle")
        require(opened, "status", "valid", "check compiler bundle")
        document, revision = opened["document"], opened["revision"]
        sample = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": "validate", "bytes": []})
        require(sample, "outcome", "ok", "open validation source")

        spec = importlib.util.spec_from_file_location(
            "pic", ROOT / "tests" / "probe_integration_case.py")
        pic = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pic)
        pic.register(session, document, revision, sample["document"], sample["revision"])

        print(f"{'bytes':>7} | {'parse':<26} | {'check':<26} | emit")
        for count in COUNTS:
            source = program(count)
            parse_result, check_result, emit_result = measure(
                session, revision, source, f"staged-{count}")
            print(f"{len(source.encode('utf-8')):>7} | {parse_result:<26} | "
                  f"{str(check_result):<26} | {emit_result}")
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
