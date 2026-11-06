"""Is the checker's cost driven by NODES or by BYTES?

Everything measured so far says the checker's ceiling is fixed in BYTES and
independent of construct (~250 bytes whether the program is trivial functions, let
bindings, call chains or if statements). That is consistent with one explanation:

  the checker makes ~60 FULL SCANS of the node list (34 functions contain
  `for x in nodes`, 60 scans in total; `type_analysis` alone has 18), so its cost is
  proportional to the NODE COUNT times a constant -- and node count is proportional
  to bytes for ordinary source.

That explanation makes a testable prediction: a program with the SAME byte size but
FEWER nodes should be checked noticeably more cheaply.

This probe builds exactly that pair and compares where each hits the ceiling.

  many-nodes: N short statements          -> ~N nodes
  few-nodes:  a few long string literals  -> ~N/8 nodes, same bytes

If few-nodes survives where many-nodes fails, the scans dominate and the lever is
indexing the node list instead of re-walking it ~60 times.

Run: python tests/probe_checker_cost_driver.py
"""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_build"))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target  # noqa: E402


def many_nodes(payload_bytes):
    """Many short statements: ~1 node per ~12 source bytes."""
    lines = []
    index = 0
    size = 0
    while size < payload_bytes:
        line = f"  let a{index} = {index}\n"
        lines.append(line)
        size += len(line)
        index += 1
    return "fn f() -> Int {\n" + "".join(lines) + "  return 0\n}\n" + \
        "fn main() -> Int { return f() }\n"


def few_nodes(payload_bytes):
    """Few long string literals: ~1 node per ~100 source bytes."""
    lines = []
    size = 0
    index = 0
    while size < payload_bytes:
        line = f'  say("{"x" * 80}")\n'
        lines.append(line)
        size += len(line)
        index += 1
    return "fn f() -> Int {\n" + "".join(lines) + "  return 0\n}\n" + \
        "fn main() -> Int { return f() }\n"


SIZES = [200, 300, 400, 600]


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

        for target_size in SIZES:
            for label, builder in (("many-nodes", many_nodes),
                                   ("few-nodes", few_nodes)):
                source = builder(target_size)
                outcome = check_only(session, revision, source,
                                     f"{label}-{target_size}")
                print(f"{label:11s} requested={target_size:4d} "
                      f"actual={len(source.encode('utf-8')):4d} bytes -> {outcome}")
            print()
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
