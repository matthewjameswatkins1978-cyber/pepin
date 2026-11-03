"""Tool-host probe for `text_builder_push_span`, the one entry the interpreter cannot reach.

`pep.ps1 run` refuses `source_bytes()` (`PEP_RUNTIME_SOURCE_CONTEXT`), so the span path needs a v2
semantic target. This probe composes `stdlib/text_builder.pep` with a span probe function, registers
it against the module document, and invokes it with payload documents as the semantic target -- so
`source_bytes()` is the payload, and the span arithmetic is exercised for real.

What this proves that the interpreter suite cannot: a multi-byte UTF-8 character and an embedded NUL
are counted in bytes, and the slice returns the payload's actual text.

    python tests/probe_text_builder_span.py
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, typed, typed_record_value  # noqa: E402

STDLIB = ROOT / "stdlib" / "text_builder.pep"

PROBE_FUNCTION = """
type PepTextSpanProbe { status: Str, diagnostic: Str, byteCount: Int, partCount: Int, fragments: List[Str] }

fn text_builder_span_probe(start: Int, finish: Int) -> PepTextSpanProbe {
  let builder = text_builder_push_span(text_builder_new(), source_bytes(), start, finish)
  return PepTextSpanProbe {
    status: "ok",
    diagnostic: "",
    byteCount: text_builder_bytes(builder),
    partCount: text_builder_part_count(builder),
    fragments: text_builder_parts(builder)
  }
}
"""

CASES = [
    ("ascii", "abc", 3),
    ("multibyte", "é", 2),
    ("embedded-nul", "a\0b", 3),
    ("multibyte-and-nul", "é\0z", 4),
]


def empty_expected():
    return typed_record_value("PepTextSpanProbe", [
        ("status", typed("Str", "ok")),
        ("diagnostic", typed("Str", "")),
        ("byteCount", typed("Int", "0")),
        ("partCount", typed("Int", "1")),
        ("fragments", {"type": "List[Str]", "value": [typed("Str", "")]}),
    ])


def fields_of(response):
    return {item["name"]: item["value"] for item in response["result"]["fields"]}


def main():
    module = STDLIB.read_text(encoding="utf-8") + PROBE_FUNCTION
    session = Session()
    results = []
    try:
        opened = session.send({"schemaVersion": 3, "op": "open", "source": module,
                               "name": "text-builder-probe", "metadataOnly": True})
        require(opened, "outcome", "ok", "open probe module")
        require(opened, "status", "valid", "check probe module")
        document, revision = opened["document"], opened["revision"]

        sample = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "validate", "bytes": []})
        require(sample, "outcome", "ok", "open validation source")
        target_spec = {"document": sample["document"], "revision": sample["revision"],
                       "entryFunctions": []}

        registered = session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_register",
                                   "tool": "text-builder-span", "document": document,
                                   "revision": revision, "function": "text_builder_span_probe"})
        require(registered, "status", "Registered", "register span probe")
        validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_validate",
                                  "tool": "text-builder-span", "document": document, "revision": revision,
                                  "testVectors": [{"arguments": [typed("Int", 0), typed("Int", 0)],
                                                   "expect": empty_expected(),
                                                   "semanticTarget": target_spec}]})
        require(validated, "status", "Validated", "validate span probe")
        activated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_activate",
                                  "tool": "text-builder-span", "document": document, "revision": revision})
        require(activated, "status", "Active", "activate span probe")

        for name, payload, expected_bytes in CASES:
            raw = payload.encode("utf-8")
            target = session.send({"schemaVersion": 3, "op": "open_bytes", "name": name,
                                   "bytes": list(raw)})
            require(target, "outcome", "ok", f"open payload {name}")
            semantic = {"document": target["document"], "revision": target["revision"],
                        "entryFunctions": []}
            invoked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                                    "tool": "text-builder-span",
                                    "arguments": [typed("Int", 0), typed("Int", len(raw))],
                                    "semanticTarget": semantic})
            require(invoked, "outcome", "ok", f"invoke span probe {name}")
            fields = fields_of(invoked)
            byte_count = int(fields["byteCount"]["value"])
            part_count = int(fields["partCount"]["value"])
            fragments = [item["value"] for item in fields["fragments"]["value"]]
            results.append({"case": name, "bytes": byte_count, "expectedBytes": expected_bytes,
                            "characters": len(payload), "parts": part_count,
                            "roundTrip": "".join(fragments) == payload,
                            "ok": byte_count == expected_bytes and "".join(fragments) == payload})
    finally:
        session.close()

    for row in results:
        print(json.dumps(row, sort_keys=True))
    if not all(row["ok"] for row in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
