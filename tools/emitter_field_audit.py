"""Derive, from the emitter source, exactly which FlatAstNode fields it reads.

A1's compact projection needs an exact consumed-field list rather than an estimate: every
field the transport sends is materialised as a Pep value, and the per-invocation step budget
is consumed by that materialisation (see docs/C23_BOUNDED_EMITTER_CONTRACT.md). Sending a
field the emitter never reads is pure waste; omitting one it does read would silently
corrupt output, so this list is also a correctness boundary.

The derivation strips string literals and line comments first, because the emitter contains
large C snippets as string data whose contents look like field accesses.

Run as a script to print the audit; the accompanying test module asserts it stays true.
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
EMITTER = ROOT / "tests" / "pep_c23_emitter.pep"

# Fields declared on the parser's FlatAstNode record.
DECLARED_FIELDS = ("id", "parentId", "childIndex", "role", "kind", "text",
                   "integerValue", "booleanValue", "stringParts",
                   "startByte", "endByte", "line", "column")


def stripped_source():
    """Emitter source with string literals and line comments removed."""
    text = EMITTER.read_text(encoding="utf-8")
    text = re.sub(r'"(?:[^"\\]|\\.)*"', '""', text)
    text = re.sub(r"//[^\n]*", "", text)
    return text


def field_use_counts():
    stripped = stripped_source()
    counts = {}
    for field in DECLARED_FIELDS:
        counts[field] = len(re.findall(rf"\.{field}\b", stripped))
    return counts


def audit():
    counts = field_use_counts()
    consumed = sorted(field for field, count in counts.items() if count > 0)
    unread = sorted(field for field, count in counts.items() if count == 0)
    return counts, consumed, unread


if __name__ == "__main__":
    counts, consumed, unread = audit()
    print("field                     accesses")
    for field in DECLARED_FIELDS:
        print(f"  {field:<22} {counts[field]:>4}")
    print()
    print("consumed by the emitter :", ", ".join(consumed))
    print("never read by the emitter:", ", ".join(unread) or "(none)")
    sys.exit(0)
