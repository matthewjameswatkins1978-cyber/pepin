"""Per-construct cost table: how many nodes of each construct fit in one check budget?

The cost model is bounded but not decomposed. What is established:

  - not bytes (a sparse program reaches 1501 bytes where a dense one stops at 281)
  - not node count alone (the ceiling varies 40-56 nodes by shape)
  - not a linear combination of the two (that needs a negative coefficient)
  - construct-dependent, with node count mattering more than bytes

"Construct-dependent" is the useful part, but it is not actionable until the
constructs are ranked. This probe ranks them: for each construct it builds a program
of N repetitions and reports the largest N whose node count still checks.

That gives A1 a table to design against -- which constructs are expensive, and
therefore which are worth optimising or avoiding in a staged unit.

Run: python tests/probe_checker_construct_cost.py
"""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_build"))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target  # noqa: E402


def let_bindings(count):
    body = "".join(f"  let a{index} = {index}\n" for index in range(count))
    return f"fn f() -> Int {{\n{body}  return 0\n}}\nfn main() -> Int {{ return f() }}\n"


def if_statements(count):
    body = "".join(f"  if {index} <= {index} {{ }} else {{ }}\n" for index in range(count))
    return f"fn f() -> Int {{\n{body}  return 0\n}}\nfn main() -> Int {{ return f() }}\n"


def while_loops(count):
    body = "".join(f"  while 1 <= 0 {{ }}\n" for _ in range(count))
    return f"fn f() -> Int {{\n{body}  return 0\n}}\nfn main() -> Int {{ return f() }}\n"


def calls(count):
    body = "".join(f"  let r{index} = g({index})\n" for index in range(count))
    return ("fn g(n: Int) -> Int { return n }\n"
            f"fn f() -> Int {{\n{body}  return 0\n}}\n"
            "fn main() -> Int { return f() }\n")


def string_literals(count):
    body = "".join(f'  say("{"x" * 20}")\n' for _ in range(count))
    return f"fn f() -> Int {{\n{body}  return 0\n}}\nfn main() -> Int {{ return f() }}\n"


def record_literals(count):
    body = "".join(f"  let p{index} = Point {{ x: {index}, y: {index} }}\n"
                   for index in range(count))
    return ("type Point { x: Int, y: Int }\n"
            f"fn f() -> Int {{\n{body}  return 0\n}}\n"
            "fn main() -> Int { return f() }\n")


SHAPES = {
    "let": let_bindings,
    "if": if_statements,
    "while": while_loops,
    "call": calls,
    "string": string_literals,
    "record": record_literals,
}

COUNTS = [1, 2, 3, 4, 6, 8, 10, 12, 16, 20, 24, 32]


def measure(session, revision, source, label):
    """Return (node_count, outcome)."""
    payload = source.encode("utf-8")
    target = session.send({"schemaVersion": 3, "op": "open_bytes",
                           "name": label, "bytes": list(payload)})
    if target.get("outcome") != "ok":
        return None, "open:" + str((target.get("error") or {}).get("code"))
    semantic = {"document": target["document"], "revision": target["revision"],
                "entryFunctions": []}
    try:
        parsed = parse_target(session, payload, target, revision)
    except Exception as error:  # noqa: BLE001
        text = str(error)
        for code in ("PEP_RUNTIME_STEP_LIMIT", "PEP_TOOL_VALUE_LIMIT",
                     "PEP_SOURCE_BYTE_LIMIT"):
            if code in text:
                return None, "parse:" + code
        return None, "parse-failed"
    nodes = session.parser_measurements.get("parser_node_count")
    try:
        checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-checker",
                                "arguments": [parsed], "semanticTarget": semantic})
    except RuntimeError as error:
        return nodes, "transport:" + str(error)[:40]
    if checked.get("outcome") != "ok":
        return nodes, (checked.get("error") or {}).get("code")
    fields = {f["name"]: f["value"] for f in checked["result"]["fields"]}
    return nodes, fields["status"]["value"]


def main():
    session = Session()
    table = {}
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

        for shape, builder in SHAPES.items():
            largest_units = None
            largest_nodes = None
            for count in COUNTS:
                source = builder(count)
                nodes, outcome = measure(session, revision, source,
                                         f"cost-{shape}-{count}")
                if outcome == "valid":
                    largest_units = count
                    largest_nodes = nodes
                else:
                    break
            table[shape] = (largest_units, largest_nodes)
    finally:
        session.close()

    print(f"{'construct':10s} | {'max units':>9} | {'nodes at max':>12} | "
          f"nodes per unit")
    for shape, (units, nodes) in table.items():
        per_unit = (nodes / units) if (units and nodes) else None
        per_text = f"{per_unit:.1f}" if per_unit else "-"
        print(f"{shape:10s} | {str(units):>9} | {str(nodes):>12} | {per_text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
