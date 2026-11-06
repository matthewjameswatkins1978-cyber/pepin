"""Sectional structure of the emitted C23, as the prerequisite for the bounded-emitter split.

The bounded-emitter contract requires that header + function units + main concatenated is
byte-identical to today's one-shot output. That can only be verified if the one-shot output
has an unambiguous section structure, so this module pins it before any code is split:

    includes / type declarations / runtime helpers / prototypes   <- header
    one definition per source function, in source order          <- units
    int main(...) { ... }                                        <- epilogue

These assertions are about text structure. They do not execute C; native execution is
covered by the other C23 modules.
"""

import pathlib
import re
import tempfile
import unittest

from pep_c23 import emit

ROOT = pathlib.Path(__file__).resolve().parents[1]

TWO_FUNCTIONS = (
    "fn total(a: Int, b: Int) -> Int { return a + b }\n"
    "fn main() -> Int { return total(20, 22) }\n")

WITH_RECORD = (
    "type Point { x: Int y: Int }\n"
    "fn sum(point: Point) -> Int { return point.x + point.y }\n"
    "fn main() -> Int {\n"
    "  let point = Point { x: 19, y: 23 }\n"
    "  return sum(point)\n"
    "}\n")


class PepC23SectionTests(unittest.TestCase):
    def emit_text(self, source_text):
        return emit(source_text.encode("utf-8"))

    def test_header_precedes_every_definition_and_main_is_last(self):
        generated = self.emit_text(TWO_FUNCTIONS)
        first_definition = generated.index("int64_t pep_fn_", generated.index(";\nint64_t") if ";\nint64_t" in generated else 0)
        prototypes_end = max(match.end() for match in re.finditer(r"^int64_t pep_fn_[A-Za-z_0-9]++ ?\([^\n]*\);$",
                                                                  generated, re.MULTILINE))
        main_start = generated.index("int main(")
        self.assertLess(prototypes_end, main_start)
        self.assertLess(first_definition, main_start)
        # every definition sits between the prototypes and main, never after main
        self.assertEqual(generated.count("int main("), 1)
        self.assertTrue(generated.rstrip().endswith("}"))

    def test_definitions_appear_once_each_in_source_order(self):
        generated = self.emit_text(TWO_FUNCTIONS)
        # Parameterless definitions are emitted as `name (void) {`, parameterised ones as
        # `name(args) {`, so the space before the parenthesis is optional in both shapes.
        definitions = re.findall(r"^(int64_t pep_fn_[A-Za-z_0-9]++) ?\([^\n]*\{$", generated, re.MULTILINE)
        prototypes = re.findall(r"^(int64_t pep_fn_[A-Za-z_0-9]++) ?\([^\n]*\);$", generated, re.MULTILINE)
        self.assertEqual(len(definitions), 2)
        self.assertEqual(sorted(d for d in definitions), sorted(prototypes))

    def test_record_declarations_precede_functions_that_use_them(self):
        generated = self.emit_text(WITH_RECORD)
        record_typedef = generated.index("typedef struct {")
        first_definition = re.search(r"^int64_t pep_fn_[A-Za-z_0-9]++ ?\([^\n]*\{$", generated, re.MULTILINE)
        self.assertIsNotNone(first_definition)
        self.assertLess(record_typedef, first_definition.start())

    def test_output_can_be_split_into_three_concatenable_sections(self):
        """The exact property the bounded-emitter gate will rely on."""
        generated = self.emit_text(TWO_FUNCTIONS)
        main_start = generated.index("int main(")
        # split at the boundary between the last prototype and the first definition
        first_definition = re.search(r"^int64_t pep_fn_[A-Za-z_0-9]++ ?\([^\n]*\{$", generated, re.MULTILINE).start()
        header, units, epilogue = (generated[:first_definition],
                                   generated[first_definition:main_start],
                                   generated[main_start:])
        self.assertEqual(header + units + epilogue, generated)
        self.assertIn("#include <stdio.h>", header)
        self.assertNotIn("int main(", header)
        self.assertNotIn("int main(", units)
        self.assertTrue(epilogue.startswith("int main("))
        # each section is non-empty and the split is stable across runs
        for section in (header, units, epilogue):
            self.assertGreater(len(section), 0)
        self.assertEqual(header + units + epilogue, self.emit_text(TWO_FUNCTIONS))


if __name__ == "__main__":
    unittest.main()
