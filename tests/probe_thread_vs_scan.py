"""Can the structural fix be DEMONSTRATED at testable sizes? No -- and that matters.

The diagnosis: the checker is O(n^2) because it looks nodes up by id with a linear
scan, and Pep has no index or map to make that O(1). The proposed fix is structural --
walk the list once and thread the value through instead of looking it up by id.

This probe tries to prove that fix pays, in Pep, without touching the checker: write
both patterns over a List[Int] and measure how many elements each can process.

IT DOES NOT PROVE IT, and the reason is worth recording.

  scan    for each index i, scan the whole list to find element i   -> O(n^2)
  thread  walk the list once, carrying the index                    -> O(n)

Uncontrolled, the two versions differ in SIZE (the scan version needs a `find`
helper), so the comparison is confounded. Size-controlled, at ~400 bytes each:

  scan           392 bytes -> PEP_RUNTIME_STEP_LIMIT
  thread-padded  418 bytes -> PEP_RUNTIME_STEP_LIMIT

Both fail at the same size. So at the sizes the budget allows (n ~ 4-40), the
quadratic term is small relative to the per-node constant, and the algorithm
difference does not show.

WHAT THIS MEANS, honestly:

  - the O(n^2) diagnosis still stands on its own evidence: static analysis (linear
    scans called inside loops) and the empirical split test (splitting across
    functions buys ~10%, not 2x, so the quadratic is global)
  - but the fix's BENEFIT cannot be demonstrated inside the testable range, because
    the quadratic only dominates at n far beyond what one budget can check
  - so "the fix pays" is an inference from the complexity, not a measurement

That distinction matters: anyone asking "did you prove the fix works?" should get
"no, I proved the cost is quadratic; the payoff is inferred". Recording it here so
the claim is not overstated later.

Run: python tests/probe_thread_vs_scan.py
"""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_build"))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target  # noqa: E402

SCAN = """fn find(xs: List[Int], target: Int) -> Int {
  var index = 0
  for value in xs {
    if value == target { return index } else {}
    index = index + 1
  }
  return -1
}
fn work(xs: List[Int]) -> Int {
  var total = 0
  var index = 0
  while !(length(xs) <= index) {
    total = total + find(xs, index)
    index = index + 1
  }
  return total
}
fn main() -> Int { return work([{values}]) }
"""

THREAD = """fn work(xs: List[Int]) -> Int {
  var total = 0
  var index = 0
  for value in xs {
    total = total + index
    index = index + 1
  }
  return total
}
fn main() -> Int { return work([{values}]) }
"""

SIZES = [4, 8, 16, 24, 32, 48, 64]


def fields_map(record):
    return {f["name"]: f["value"] for f in record.get("fields", [])}


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
    fields = fields_map(checked["result"])
    return fields["status"]["value"]


def main():
    session = Session()
    ceilings = {}
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

        for label, template in (("scan", SCAN), ("thread", THREAD)):
            print(f"\n{label}:")
            largest = None
            for size in SIZES:
                values = ", ".join(str(index) for index in range(size))
                source = template.replace("{values}", values)
                outcome = check_only(session, revision, source, f"{label}-{size}")
                print(f"  n={size:4d} bytes={len(source.encode()):5d} -> {outcome}")
                if outcome == "valid":
                    largest = size
                else:
                    break
            ceilings[label] = largest
    finally:
        session.close()

    print(f"\nlargest n accepted: scan={ceilings.get('scan')} "
          f"thread={ceilings.get('thread')}")
    print("\nNOTE: the two versions differ in SIZE, so this comparison is confounded.")
    print("Size-controlled (see the docstring), both fail at ~400 bytes. The fix's")
    print("benefit is NOT demonstrated here; it is inferred from the complexity.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
