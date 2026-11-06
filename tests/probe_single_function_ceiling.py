"""Can ONE real compiler function fit in the checker's budget?

The budget picture so far:

  single-budget emit_c23()   144 bytes
  staged full pipeline       335 bytes
  check alone                ~250 bytes for the shapes measured

That last number is the one that decides whether statement-level staged checking can
work at all. If the checker handles ~250 bytes, then a single function must be under
~250 bytes to be checkable -- and the real lexer functions are much larger than that.

CAVEAT, and it matters: an earlier version of this docstring called the check ceiling
"shape-independent (~400 steps/byte)". That was RETRACTED. probe_checker_node_ceiling.py
shows the cost is construct-dependent -- a sparse program (long string literals)
reaches 1501 bytes where a dense one (let bindings) stops at 281. So the 293-byte
figure below is the ceiling for THIS fixture (let statements), not a general byte
budget. Read it as "about 40 nodes of this shape".

That still decides the question this probe asks: the real lexer functions are far
larger than any measured ceiling, whatever unit you use.

This probe measures the ceiling for ONE function of increasing size, then compares it
against the actual sizes of the real lexer functions. The comparison is the point: it
says whether staging needs to go below the function level.

Run: python tests/probe_single_function_ceiling.py
"""
import importlib.util
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_build"))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target  # noqa: E402

LEXER = ROOT / "examples" / "pep_lexer.pep"


def one_function(statement_count):
    """A single function with N let statements, plus a trivial main."""
    body = "".join(f"  let a{index} = {index}\n" for index in range(statement_count))
    return (f"fn big(n: Int) -> Int {{\n{body}  return a0\n}}\n"
            "fn main() -> Int { return big(1) }\n")


COUNTS = [2, 4, 8, 12, 16, 24, 32]


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


def lexer_function_sizes():
    """Byte size of each real top-level lexer function, by brace depth."""
    lines = LEXER.read_text(encoding="utf-8").split("\n")
    sizes = []
    index = 0
    while index < len(lines):
        if not lines[index].startswith("fn "):
            index += 1
            continue
        start = index
        depth = 0
        opened = False
        while index < len(lines):
            depth += lines[index].count("{") - lines[index].count("}")
            if "{" in lines[index]:
                opened = True
            index += 1
            if opened and depth == 0:
                break
        block = "\n".join(lines[start:index])
        name = re.match(r"fn\s+(\w+)", lines[start]).group(1)
        sizes.append((name, len(block.encode("utf-8"))))
    return sizes


def main():
    session = Session()
    ceiling = None
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

        print("ONE function, increasing statement count:")
        for count in COUNTS:
            source = one_function(count)
            size = len(source.encode("utf-8"))
            outcome = check_only(session, revision, source, f"onefn-{count}")
            print(f"  {count:3d} statements / {size:4d} bytes -> {outcome}")
            if outcome == "valid":
                ceiling = size
            elif ceiling is not None:
                break
    finally:
        session.close()

    print(f"\nlargest single function the checker accepted: {ceiling} bytes")
    print("\nreal lexer function sizes (for comparison):")
    for name, size in sorted(lexer_function_sizes(), key=lambda item: -item[1]):
        verdict = "fits" if ceiling and size <= ceiling else "EXCEEDS"
        print(f"  {name:20s} {size:5d} bytes  {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
