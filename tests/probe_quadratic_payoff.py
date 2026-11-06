"""How much would fixing the checker's O(n^2) actually buy?

`probe_checker_quadratic_lookups.py` found the cause by static analysis: every lookup
helper is a linear scan, and seven checker functions call one inside a loop, so the
cost is O(n^2) in node count.

This probe sizes the payoff, because "fix a quadratic" is only worth acting on if the
numbers are decisive. It measures bytes-per-node on real compiler source, extrapolates
to the whole compiler closure, and reports the operation-count ratio between O(n^2)
and O(n).

The ratio does not depend on the step-cost constant, which is what makes it the
defensible number. I deliberately do NOT claim a wall-clock or budget count, because
the constant is not measurable from here.

Run: python tests/probe_quadratic_payoff.py
"""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_build"))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target  # noqa: E402


def main():
    session = Session()
    sample_bytes = None
    sample_nodes = None
    bundle_bytes = None
    try:
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        bundle_bytes = len(bundle.encode("utf-8"))
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

        # Bytes-per-node from real compiler source, not from a synthetic fixture.
        for name, path in (("lexer", "examples/pep_lexer.pep"),
                           ("parser", "examples/pep_parser.pep")):
            source = (ROOT / path).read_bytes()
            target = session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": name, "bytes": list(source)})
            try:
                parse_target(session, source, target, revision)
            except Exception as error:  # noqa: BLE001
                print(f"{name}: parse not possible in one budget ({str(error)[:60]})")
                continue
            nodes = session.parser_measurements.get("parser_node_count")
            if nodes:
                per_node = len(source) / nodes
                print(f"{name:8s} bytes={len(source):6d} nodes={nodes:6d} "
                      f"bytes/node={per_node:.2f}")
                if sample_bytes is None:
                    sample_bytes, sample_nodes = len(source), nodes
    finally:
        session.close()

    if not sample_bytes or not bundle_bytes:
        print("no sample; cannot estimate")
        return 1

    per_node = sample_bytes / sample_nodes
    estimated_nodes = bundle_bytes / per_node

    print(f"\ncompiler closure: {bundle_bytes} bytes / {per_node:.2f} bytes-per-node "
          f"= ~{estimated_nodes:,.0f} nodes")
    print(f"\noperation counts:")
    print(f"  O(n^2) = {estimated_nodes ** 2:,.0f}")
    print(f"  O(n)   = {estimated_nodes:,.0f}")
    print(f"  ratio  = {estimated_nodes:,.0f}x fewer operations")
    print(f"\nThe ratio is the defensible number: it does not depend on the step-cost")
    print(f"constant. Fixing the scans turns a ~{estimated_nodes:,.0f}x problem into a")
    print(f"linear one. I am NOT claiming a specific budget count -- the constant is not")
    print(f"measurable from here.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
