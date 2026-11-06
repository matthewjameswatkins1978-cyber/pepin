"""Determinism: the same source must produce byte-identical C, across sessions.

A1's native SourceBytes grant contract (@a802290) states as invariant 4:

  "Deterministic: same host grant + same target bytes => same C; the existing
   bundle determinism probes apply unchanged."

That invariant is load-bearing for the whole bootstrap: A->B->C compares emitted
output, and a cache keyed by source identity is only sound if emission is a pure
function of its inputs. It had no direct evidence in A2's lane, so this probe
supplies it.

Two independent sessions, same source, compare the emitted bytes exactly. Repeated
for three shapes: a scalar program, a record-returning program, and the
entry-parameter SourceBytes grant wrapper (the newest and least-exercised path).

Run: python tests/probe_emitter_determinism.py
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
    ("scalar",
     "fn add_one(v: Int) -> Int { return v + 1 }\n"
     "fn main() -> Int { return add_one(41) }\n"),
    # The if/else form, not the trailing-return form: the three-parameter call gate
    # requires a "call-free result", and the trailing-return body is refused there
    # (measured). This is the shape probe_k4_record_return.py already proves native.
    ("record-return",
     "type SourcePosition { line: Int, column: Int }\n"
     "fn advance_position(line: Int, column: Int, byte: Int) -> SourcePosition {\n"
     "  if byte == 10 { return SourcePosition { line: line + 1, column: 1 } } else {\n"
     "    return SourcePosition { line: line, column: column + 1 }\n"
     "  }\n"
     "}\n"
     "fn main() -> Int {\n"
     "  let p = advance_position(1, 1, 10)\n"
     "  return p.line * 10 + p.column\n"
     "}\n"),
    ("source-grant-entry",
     "fn main(source: SourceBytes) -> Int { return byte_at(source, 0) }\n"),
]


def fields_map(record):
    return {f["name"]: f["value"] for f in record.get("fields", [])}


def emit_once(source, label):
    """One full session: open bundle, check, emit. Returns the C text."""
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

        payload = source.encode("utf-8")
        target = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": label, "bytes": list(payload)})
        require(target, "outcome", "ok", f"open {label}")
        semantic = {"document": target["document"], "revision": target["revision"],
                    "entryFunctions": []}
        parsed = parse_target(session, payload, target, revision)
        checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-checker",
                                "arguments": [parsed], "semanticTarget": semantic})
        require(checked, "outcome", "ok", f"check {label}")
        cfields = fields_map(checked["result"])
        if cfields["status"]["value"] != "valid":
            return None, f"check status={cfields['status']['value']}"
        emitted = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-emitter",
                                "arguments": [parsed, checked["result"]],
                                "semanticTarget": semantic})
        require(emitted, "outcome", "ok", f"emit {label}")
        efields = fields_map(emitted["result"])
        if efields["status"]["value"] != "emitted":
            return None, f"emit status={efields['status']['value']} " \
                         f"{efields['diagnostic']['value'][:140]}"
        return "".join(p["value"] for p in efields["sourceParts"]["value"]), "emitted"
    finally:
        session.close()


def main():
    failures = 0
    for label, source in CASES:
        first, detail = emit_once(source, f"det-{label}-1")
        if first is None:
            print(f"{label:20s} EMIT-REFUSED {detail}")
            failures += 1
            continue
        second, detail = emit_once(source, f"det-{label}-2")
        if second is None:
            print(f"{label:20s} EMIT-REFUSED (2nd session) {detail}")
            failures += 1
            continue
        ok = first == second
        print(f"{label:20s} {'OK' if ok else 'FAIL'} "
              f"bytes={len(first)} identical={ok}")
        if not ok:
            # Report the first divergence rather than dumping both blobs.
            for index, (a, b) in enumerate(zip(first, second)):
                if a != b:
                    print(f"  first divergence at byte {index}: "
                          f"{first[max(0, index - 40):index + 40]!r} vs "
                          f"{second[max(0, index - 40):index + 40]!r}")
                    break
            else:
                print(f"  lengths differ: {len(first)} vs {len(second)}")
            failures += 1

    print("\nemitter determinism:", "PASS" if not failures else f"FAIL ({failures})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
