"""Can the O(n^2) lookups actually be fixed in Pep? What the language allows.

`probe_checker_quadratic_lookups.py` found the cause: every lookup is a linear scan.
The obvious fix is "index once, look up in O(1)". This probe asks whether Pep can
express that, because if it cannot, the fix is a different and larger piece of work
and A1 should know that before starting.

Three things are tested:

  1. list indexing -- `xs[0]` -- which would make lookup_node O(1) directly
  2. a map/dictionary type, which would make every lookup O(1)
  3. what the language DOES offer for element access

The answer decides the shape of the fix, so it is worth measuring rather than
assuming.

Run: python tests/probe_lookup_fix_feasibility.py
"""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_build"))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target  # noqa: E402

CASES = [
    ("list-index-int", 'fn f(xs: List[Int]) -> Int {\n  return xs[0]\n}\n'
                       'fn main() -> Int { return 0 }\n'),
    ("list-index-str", 'fn f(xs: List[Str]) -> Str {\n  return xs[1]\n}\n'
                       'fn main() -> Int { return 0 }\n'),
    ("list-index-record", 'type P { x: Int }\nfn f(xs: List[P]) -> Int {\n'
                          '  return xs[0].x\n}\nfn main() -> Int { return 0 }\n'),
    ("map-type", 'fn f(m: Map[Str, Int]) -> Int {\n  return 0\n}\n'
                 'fn main() -> Int { return 0 }\n'),
    ("dict-type", 'fn f(m: Dict[Str, Int]) -> Int {\n  return 0\n}\n'
                  'fn main() -> Int { return 0 }\n'),
]


def fields_map(record):
    return {f["name"]: f["value"] for f in record.get("fields", [])}


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

        for label, source in CASES:
            payload = source.encode("utf-8")
            target = session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": label, "bytes": list(payload)})
            semantic = {"document": target["document"],
                        "revision": target["revision"], "entryFunctions": []}
            try:
                parsed = parse_target(session, payload, target, revision)
            except Exception as error:  # noqa: BLE001
                print(f"{label:20s} PARSE-FAILED {str(error)[:90]}")
                continue
            checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                    "op": "tool_invoke", "tool": "pep-c23-checker",
                                    "arguments": [parsed], "semanticTarget": semantic})
            if checked.get("outcome") != "ok":
                error = checked.get("error") or {}
                print(f"{label:20s} CHECK-ERROR {error.get('code')}")
                continue
            fields = fields_map(checked["result"])
            codes = [fields_map(d).get("code", {}).get("value")
                     for d in (fields.get("diagnostics", {}).get("value") or [])]
            print(f"{label:20s} status={fields['status']['value']:8s} {codes[:2]}")
    finally:
        session.close()

    print("\nCONCLUSION: if list indexing and map types are both rejected, Pep cannot")
    print("express an O(1) lookup, so the fix is NOT 'add an index'. It has to remove")
    print("the need for the lookup -- thread the node through instead of its id.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
