"""Can ONE statement be checked? The question that decides whether statement-level
staged checking can work.

A1's receipt 017 reports that `lexer_step` contains a 1033-node statement and that
staged-descent sizing is "context-driven cost, not node count". My own measurements
agree from the other side: the checker's ceiling is ~293 bytes per function and is
shape-independent (~400 steps/byte).

Those two findings together raise a question neither answers alone: if a SINGLE
statement is larger than the whole budget, then no amount of statement-level carving
helps -- the carver has to go below the statement.

This probe measures the ceiling for one statement with an expression of increasing
size, and reports the largest expression the checker accepts.

Run: python tests/probe_single_statement_ceiling.py
"""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_build"))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target  # noqa: E402


def one_statement(term_count):
    """A single let whose expression is a chain of `+ 1` terms."""
    expression = " + ".join(["1"] * term_count)
    return f"fn main() -> Int {{\n  let x = {expression}\n  return x\n}}\n"


TERMS = [2, 4, 8, 16, 32, 64, 128]


def check_only(session, revision, source, label):
    payload = source.encode("utf-8")
    target = session.send({"schemaVersion": 3, "op": "open_bytes",
                           "name": label, "bytes": list(payload)})
    if target.get("outcome") != "ok":
        return "open:" + str((target.get("error") or {}).get("code"))
    semantic = {"document": target["document"], "revision": target["revision"],
                "entryFunctions": []}
    try:
        parsed = parse_target(session, payload, target, revision)
    except Exception as error:  # noqa: BLE001
        text = str(error)
        for code in ("PEP_RUNTIME_STEP_LIMIT", "PEP_TOOL_VALUE_LIMIT",
                     "PEP_SOURCE_BYTE_LIMIT"):
            if code in text:
                return "parse:" + code
        return "parse-failed"
    try:
        checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-checker",
                                "arguments": [parsed], "semanticTarget": semantic})
    except RuntimeError as error:
        return "transport:" + str(error)[:40]
    if checked.get("outcome") != "ok":
        return (checked.get("error") or {}).get("code")
    fields = {f["name"]: f["value"] for f in checked["result"]["fields"]}
    return fields["status"]["value"]


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

        print("ONE statement, expression of increasing size:")
        largest = None
        for terms in TERMS:
            source = one_statement(terms)
            size = len(source.encode("utf-8"))
            outcome = check_only(session, revision, source, f"onestmt-{terms}")
            print(f"  {terms:4d} terms / {size:5d} bytes -> {outcome}")
            if outcome == "valid":
                largest = (terms, size)
            else:
                break
        if largest:
            print(f"\nlargest single statement accepted: {largest[0]} terms / "
                  f"{largest[1]} bytes")
        else:
            print("\nno size accepted")
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
