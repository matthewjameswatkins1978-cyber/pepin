"""Timing the checker: the cost is mildly superlinear, NOT quadratic.

This probe exists to test the O(n^2) claim, and it does not support it. Recording that
plainly, because the claim was published and needs correcting.

Method: time the checker as the node count grows, subtract the fixed floor (a minimal
program's check time, which covers the host and JSONL round trip), and look at
work-per-node. If the cost is O(n^2), work/node rises linearly with n. If O(n), it is
flat.

Sparse construct (say + long string literals), all checks valid:

  nodes | work/node
     14 |    0.0594
     20 |    0.0732
     26 |    0.1065
     32 |    0.0741
     38 |    0.0851
     44 |    0.0772
     56 |    0.0972

work/node rises 1.64x over 4x nodes. Quadratic would be 4x. Linear would be 1x. So
the cost is MILDLY SUPERLINEAR -- somewhere between linear and quadratic, not
quadratic.

WHAT THIS MEANS FOR THE EARLIER CLAIMS:

  - "the checker is O(n^2)" -- NOT SUPPORTED by runtime timing. The static analysis
    showed a quadratic is POSSIBLE (linear scans called from 25 sites, 7 functions
    calling one inside a loop); it is not what the runtime shows at reachable sizes.
  - "the fix is worth 55,930x fewer operations" -- WRONG, because it assumed the
    quadratic. That number should not be used.
  - "the cost is global in total nodes" -- still supported: splitting the same nodes
    across two functions bought ~10%, not 2x (probe_quadratic_empirical.py).

WHAT SURVIVES: the cost is global in total node count, construct-dependent, and mildly
superlinear. The lever is reducing per-node work or staging -- not "removing a
quadratic", because there is no demonstrated quadratic to remove.

Timing is noisy: the host, the JSONL round trip and Python all contribute, and the
fixed floor is subtracted but imperfectly. Read the trend, not an exponent.

Run: python tests/probe_checker_scaling_timing.py
"""
import importlib.util
import pathlib
import statistics
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_build"))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target  # noqa: E402

COUNTS = [2, 4, 6, 8, 10, 12, 16]
REPEATS = 7


def fields_map(record):
    return {f["name"]: f["value"] for f in record.get("fields", [])}


def sparse(count):
    body = "".join('  say("' + "x" * 80 + '")\n' for _ in range(count))
    return f"fn f() -> Int {{\n{body}  return 0\n}}\nfn main() -> Int {{ return f() }}\n"


def bench(session, revision, source, label):
    payload = source.encode("utf-8")
    target = session.send({"schemaVersion": 3, "op": "open_bytes",
                           "name": label, "bytes": list(payload)})
    if target.get("outcome") != "ok":
        return None, None, False
    semantic = {"document": target["document"], "revision": target["revision"],
                "entryFunctions": []}
    try:
        parsed = parse_target(session, payload, target, revision)
    except Exception:  # noqa: BLE001
        return None, None, False
    nodes = session.parser_measurements.get("parser_node_count")
    samples = []
    ok = False
    for _ in range(REPEATS):
        started = time.perf_counter()
        checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-checker",
                                "arguments": [parsed], "semanticTarget": semantic})
        samples.append(time.perf_counter() - started)
        ok = (checked.get("outcome") == "ok"
              and fields_map(checked["result"])["status"]["value"] == "valid")
    return nodes, statistics.median(samples) * 1000.0, ok


def main():
    session = Session()
    rows = []
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

        floor_nodes, floor_ms, _ = bench(session, revision,
                                         "fn main() -> Int { return 0 }\n", "floor")
        print(f"fixed floor: nodes={floor_nodes} ms={floor_ms:.3f}")
        print(f"{'units':>5} | {'nodes':>5} | {'ms':>7} | {'work/node':>9} | ok")
        for count in COUNTS:
            nodes, ms, ok = bench(session, revision, sparse(count), f"sparse-{count}")
            if ms is None:
                print(f"{count:>5} | {'-':>5} | {'-':>7} | {'-':>9} | parse-fail")
                continue
            work = ms - floor_ms
            per_node = work / nodes if nodes else 0.0
            print(f"{count:>5} | {nodes:>5} | {ms:>7.3f} | {per_node:>9.4f} | {ok}")
            if ok and nodes:
                rows.append((nodes, per_node))
    finally:
        session.close()

    if len(rows) >= 3:
        first_nodes, first_per = rows[0]
        last_nodes, last_per = rows[-1]
        node_ratio = last_nodes / first_nodes
        per_ratio = last_per / first_per
        print(f"\nwork/node: {first_per:.4f} at {first_nodes} nodes -> "
              f"{last_per:.4f} at {last_nodes} nodes")
        print(f"  node ratio {node_ratio:.2f}x, work/node ratio {per_ratio:.2f}x")
        print(f"  linear would be 1.00x, quadratic would be {node_ratio:.2f}x")
        if per_ratio < node_ratio * 0.5:
            print("\nVERDICT: NOT quadratic. The cost is mildly superlinear at most.")
        else:
            print("\nVERDICT: consistent with quadratic.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
