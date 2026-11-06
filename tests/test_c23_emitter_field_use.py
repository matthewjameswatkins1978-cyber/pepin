"""Pin the exact set of FlatAstNode fields the emitter consumes.

This is the audit A1's compact projection depends on. Two directions matter:

- a field the emitter never reads is pure cost, because every node field becomes a Pep
  value before the emitter's first statement runs and the per-invocation step budget is
  consumed by that materialisation;
- a field it does read must never be dropped, or the emitted C would change silently
  instead of failing.

The audit is derived from the emitter source with string literals and comments stripped, so
it reflects real accesses rather than C snippets embedded as data.
"""

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import emitter_field_audit as audit  # noqa: E402


class PepC23EmitterFieldUseTests(unittest.TestCase):
    def test_consumed_field_set_is_exactly_as_published(self):
        """A1 projects against this list, so changing it must be a deliberate act."""
        _, consumed, unread = audit.audit()
        self.assertEqual(consumed,
                         ["booleanValue", "childIndex", "endByte", "id", "integerValue",
                          "kind", "parentId", "role", "startByte", "text"])

    def test_unread_fields_are_the_three_that_can_be_dropped(self):
        _, _, unread = audit.audit()
        self.assertEqual(unread, ["column", "line", "stringParts"])

    def test_string_parts_are_read_from_the_source_not_from_the_node(self):
        """Literal text comes from `source_bytes()` and the node's byte span.

        If this ever changed, dropping `stringParts` from the transport would silently
        truncate every string literal, so the invariant is asserted rather than assumed.
        """
        generated = audit.stripped_source()
        self.assertNotIn(".stringParts", generated)
        for accessor in ("byte_at(", "source_bytes(", "byte_length("):
            self.assertIn(accessor, generated)


if __name__ == "__main__":
    unittest.main()
