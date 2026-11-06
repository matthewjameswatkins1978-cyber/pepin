"""int_text has NO native lowering, and the emitter source is at its size limit.

Two measured findings, recorded together because the second is why the first is
not a five-minute fix.

FINDING 1 -- int_text does not lower, in any form.

  say(int_text(42))        REFUSED  "say lowers only string literals, ..."
  g(int_text(42))          REFUSED  "calls require a known target"
  let s = int_text(42)     REFUSED  "cross-chunk call has no resolved call fact"

Three different diagnostics for one missing builtin, which is why it took a direct
probe to see that the builtin had no native support at all rather than a
shape-specific gap. This matters because the emitter calls `int_text` on node ids
throughout its own source, so without it the emitter cannot emit itself.

FINDING 2 -- the emitter source cannot grow under the fixed 100k step budget.

A working implementation was written and verified: `int_text` classified as a
Str-returning builtin, lowered to a `pep_int_text` runtime helper, and proven
seed-identical on 0, 1, 42, -1, -42, INT64_MAX and INT64_MIN under strict Clang
and GCC. It was then REVERTED, because adding ~10 lines to
`tests/pep_c23_emitter.pep` breaks
`tests.test_a14_c23.A14C23EmissionTests.test_recursive_native_calls_enforce_pep_depth`
with PEP_RUNTIME_STEP_LIMIT.

The mechanism: that test drives the zero-argument `emit_c23()` entry, which calls
`parser_parse_program()` and `analyze_parsed()` and then emits -- parse, check and
emit inside ONE 100k budget. The emitter source is part of the bundle being
checked, so additions to it raise that cost.

HEADROOM, measured by bisecting the addition (each row is a real run of that test):

  16 comment lines                                  PASS
  8 new trivial top-level functions                 PASS
  1 trivial statement (`if 1 == 2`) in a tail fn    PASS
  1 statement with a field access in a small fn     FAIL  PEP_RUNTIME_STEP_LIMIT
  1 statement with a field access in a large fn     FAIL  PEP_RUNTIME_STEP_LIMIT
  the int_text branch (field access + calls)        FAIL  PEP_RUNTIME_STEP_LIMIT

So the margin is not line count and not function count: it is a handful of
TYPE-CHECKED statements. Comments are free, new uncalled functions are nearly
free, but a statement that the checker has to type is enough to tip it. The
recursive-depth test is sitting within a few checked statements of the ceiling.

The production path is unaffected: `emit_c23_checked(parsed, checked)` with
pre-parsed, pre-checked arguments emits the same program fine, because each stage
gets its own budget. So the constraint is specific to the zero-argument entry.

This probe therefore asserts the CURRENT state, so that whoever implements
`int_text` has a truthful baseline and a named obstacle.

Run: python tests/probe_int_text.py
"""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_build"))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target  # noqa: E402

# (label, source, expected diagnostic fragment)
CASES = [
    ("say-int_text",
     'fn main() -> Int {\n  say(int_text(42))\n  return 0\n}\n',
     "say lowers only string literals"),
    ("call-arg-int_text",
     'fn g(s: Str) -> Int { return 0 }\nfn main() -> Int { return g(int_text(42)) }\n',
     "calls require a known target"),
    ("let-int_text",
     'fn f(n: Int) -> Str {\n  let id = int_text(n)\n  return id\n}\nfn main() -> Int { return 0 }\n',
     "cross-chunk call has no resolved call fact"),
]


def fields_map(record):
    return {f["name"]: f["value"] for f in record.get("fields", [])}


def main():
    failures = 0
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

        for label, source, expected in CASES:
            payload = source.encode("utf-8")
            target = session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": label, "bytes": list(payload)})
            require(target, "outcome", "ok", f"open {label}")
            semantic = {"document": target["document"],
                        "revision": target["revision"], "entryFunctions": []}
            parsed = parse_target(session, payload, target, revision)
            checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                    "op": "tool_invoke", "tool": "pep-c23-checker",
                                    "arguments": [parsed], "semanticTarget": semantic})
            require(checked, "outcome", "ok", f"check {label}")
            cfields = fields_map(checked["result"])
            if cfields["status"]["value"] != "valid":
                print(f"{label:18s} CHECK-INVALID (fixture is valid Pep; probe is stale)")
                failures += 1
                continue
            emitted = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                    "op": "tool_invoke", "tool": "pep-c23-emitter",
                                    "arguments": [parsed, checked["result"]],
                                    "semanticTarget": semantic})
            require(emitted, "outcome", "ok", f"emit {label}")
            efields = fields_map(emitted["result"])
            status = efields["status"]["value"]
            detail = efields["diagnostic"]["value"]
            ok = status == "unsupported" and expected in detail
            print(f"{label:18s} {'OK' if ok else 'FAIL'} status={status} {detail[:110]}")
            if not ok:
                failures += 1
    finally:
        session.close()

    print("\nint_text gap:", "CONFIRMED (still unimplemented)"
          if not failures else f"UNEXPECTED ({failures})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
