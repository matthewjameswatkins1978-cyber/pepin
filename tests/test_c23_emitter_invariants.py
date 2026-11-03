"""Emitter output invariants that the bounded-input contract depends on.

The chunked-emitter contract (docs/C23_BOUNDED_EMITTER_CONTRACT.md) is accepted by
concatenating header + function units + main and requiring the result to be
byte-identical to today's one-shot output. That gate is only meaningful if the one-shot
output is itself deterministic and free of environment details, so those properties are
pinned here rather than assumed.

These are properties of the emitted *text*. They do not execute C.
"""

import pathlib
import tempfile
import unittest

from pep_c23 import emit

ROOT = pathlib.Path(__file__).resolve().parents[1]

PROGRAMS = {
    "scalars": "fn main() -> Int { return 40 + 2 }\n",
    "record": "type Point { x: Int y: Int }\n"
              "fn main() -> Int {\n"
              "  let point = Point { x: 19, y: 23 }\n"
              "  return point.x + point.y\n"
              "}\n",
    "list-int": "fn main() -> Int {\n"
                "  var xs: List[Int] = [1, 2, 3]\n"
                "  var guard = 0\n"
                "  while guard <= 0 {\n"
                "    xs = prepend(xs, 0)\n"
                "    xs = reverse(xs)\n"
                "    guard = guard + 1\n"
                "  }\n"
                "  return length(xs)\n"
                "}\n",
    "list-str": "fn main() -> Int {\n"
                "  var parts: List[Str] = []\n"
                "  var guard = 0\n"
                "  while guard <= 0 {\n"
                "    parts = prepend(parts, \"a\")\n"
                "    guard = guard + 1\n"
                "  }\n"
                "  return length(parts)\n"
                "}\n",
    "arity": "fn total(a: Int, b: Int, c: Int, d: Int) -> Int { return a + b + c + d }\n"
             "fn main() -> Int { return total(1, 2, 3, 36) }\n",
}


class PepC23EmissionInvariantTests(unittest.TestCase):
    def test_emission_is_deterministic(self):
        """Same source, same output. The chunked contract's equality gate needs this."""
        for name, source in PROGRAMS.items():
            with self.subTest(program=name):
                first = emit(source.encode("utf-8"))
                second = emit(source.encode("utf-8"))
                self.assertEqual(first, second)

    def test_emission_is_path_clean(self):
        """No host paths, usernames or absolute locations may leak into generated C."""
        absolute = str(ROOT).replace("\\", "/")
        for name, source in PROGRAMS.items():
            with self.subTest(program=name):
                generated = emit(source.encode("utf-8"))
                self.assertNotIn(absolute, generated)
                self.assertNotIn(str(ROOT), generated)
                self.assertNotIn("_build", generated)
                self.assertNotIn(tempfile.gettempdir().replace("\\", "/"), generated)
                self.assertTrue(generated.endswith("\n"))
                self.assertFalse(generated.endswith("\n\n"))

    def test_emission_has_one_definition_per_source_function(self):
        """Chunked concatenation must not duplicate or drop a function definition."""
        source = (PROGRAMS["arity"]
                  + "fn extra(value: Int) -> Int { return value }\n")
        generated = emit(source.encode("utf-8"))
        self.assertEqual(generated.count("int main(void)"), 1)
        definitions = [line for line in generated.split("\n")
                       if line.startswith("int64_t pep_fn_") and line.endswith("{")]
        prototypes = [line for line in generated.split("\n")
                      if line.startswith("int64_t pep_fn_") and line.endswith(";")]
        # one definition per source function, and a matching prototype for each
        self.assertEqual(len(definitions), len(prototypes))
        self.assertGreaterEqual(len(definitions), 3)


if __name__ == "__main__":
    unittest.main()
