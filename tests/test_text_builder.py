"""stdlib/text_builder.pep: exact byte accounting for compiler output without joining it.

The seed cannot measure a `Str` (no length, no conversion to bytes, no concatenation), so a
fragment's width is supplied by the caller. These tests pin that contract in the interpreter.

Scope note, stated rather than implied: `text_builder_push_span` cannot run in the interpreter.
`source_bytes()` is authorised only under a host-provided v2 semantic target, and `pep.ps1 run`
refuses it with `PEP_RUNTIME_SOURCE_CONTEXT` (measured, not assumed). The span path is therefore
covered twice over: one test pins that refusal so nobody mistakes the interpreter suite for coverage,
and another runs `tests/probe_text_builder_span.py`, which registers this module against the tool host
and passes ASCII, multi-byte, embedded-NUL and combined payloads as the semantic target.

`pep.ps1 run` executes top-level statements, not `main`, so every probe ends in `say(...)`.
"""

import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
STDLIB = ROOT / "stdlib" / "text_builder.pep"
C_TEXT = ROOT / "stdlib" / "c_text.pep"
CONSUMER = ROOT / "tests" / "text_builder_consumer.pep"


def run_pep(source_bytes, name):
    path = ROOT / "_build" / f"{name}.pep"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(source_bytes)
    return subprocess.run(["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"), "run", str(path)],
                          cwd=ROOT, text=True, capture_output=True, check=False)


def lines_of(process):
    return [line for line in process.stdout.split("\n") if line != ""]


class TextBuilderTests(unittest.TestCase):
    def test_consumer_reports_exact_bytes_and_parts(self):
        """A compiler-shaped consumer's byte total must equal the joined output's real width."""
        composed = STDLIB.read_text(encoding="utf-8") + "\n" + CONSUMER.read_text(encoding="utf-8")
        expected = "typedef struct pep_record_ab { int64_t value; } pep_record_ab;\n"
        ran = run_pep(composed.encode("utf-8"), "text_builder_consumer")
        self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
        printed = lines_of(ran)
        self.assertEqual(printed[0], str(len(expected.encode("utf-8"))))
        self.assertEqual(printed[1], "7")
        # `say` prints one fragment per line, so the join is the test's job, not the program's.
        self.assertEqual(printed[2:], ["typedef struct pep_record_", "ab", " { int64_t ",
                                       "value", "; } pep_record_", "ab", ";"])

    def test_caller_supplied_width_counts_bytes_not_characters(self):
        """A multi-byte fragment must be accounted in bytes; that is what the caller's width means."""
        payload = "é\0z"
        composed = (
            STDLIB.read_text(encoding="utf-8")
            + "\nvar probe = text_builder_new()\n"
            + "probe = text_builder_push(probe, \"" + payload + "\", "
            + str(len(payload.encode("utf-8"))) + ")\n"
            + "say(int_text(text_builder_bytes(probe)))\n"
            + "say(int_text(text_builder_part_count(probe)))\n"
            + "for part in text_builder_parts(probe) { say(part) }\n")
        ran = run_pep(composed.encode("utf-8"), "text_builder_bytes")
        self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
        printed = lines_of(ran)
        self.assertEqual(printed[0], str(len(payload.encode("utf-8"))))
        self.assertNotEqual(str(len(payload)), printed[0], "characters and bytes differ for this input")
        self.assertEqual(printed[1], "1")

    def test_c_declaration_consumer_composes_a_named_field_record(self):
        """stdlib/c_text.pep is a real consumer: exact bytes, exact fragments, no width slipping.

        The expected string is a single-line record declaration in the emitter's shape but with named
        fields instead of `pep_field_<index>` members. A wrong fragment width shows up as a byte-total
        or fragment mismatch rather than as plausible C that is quietly one byte off.
        """
        module = (STDLIB.read_text(encoding="utf-8") + "\n"
                  + C_TEXT.read_text(encoding="utf-8") + "\n"
                  + "let declaration = c_two_int_record(\"ab\", 2, \"x\", 1, \"y\", 1)\n"
                  + "say(int_text(text_builder_bytes(declaration)))\n"
                  + "for part in text_builder_parts(declaration) { say(part) }\n")
        expected = "typedef struct pep_record_ab { int64_t x; int64_t y; } pep_record_ab;"
        fragments = ["typedef struct pep_record_", "ab", " { ", "int64_t", " ", "x", "; ",
                     "int64_t", " ", "y", "; ", "} pep_record_", "ab", ";"]

        ran = run_pep(module.encode("utf-8"), "c_text_consumer")
        self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
        printed = lines_of(ran)
        self.assertEqual(printed[0], str(len(expected)), "byte total must equal the real width")
        self.assertEqual(printed[1:], fragments)
        self.assertEqual("".join(fragments), expected)

    def test_negative_width_leaves_the_builder_unchanged(self):
        """A caller mistake must not move the byte count backwards silently."""
        composed = (
            STDLIB.read_text(encoding="utf-8")
            + "\nlet empty = text_builder_new()\n"
            + "let refused = text_builder_push(empty, \"abc\", 0 - 1)\n"
            + "let accepted = text_builder_push(empty, \"abc\", 3)\n"
            + "say(int_text(text_builder_part_count(refused)))\n"
            + "say(int_text(text_builder_bytes(refused)))\n"
            + "say(int_text(text_builder_bytes(accepted)))\n"
            + "say(int_text(text_builder_part_count(text_builder_new())))\n")
        ran = run_pep(composed.encode("utf-8"), "text_builder_negative")
        self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
        self.assertEqual(lines_of(ran), ["0", "0", "3", "0"])

    def test_span_entry_point_is_refused_without_host_context(self):
        """Pin the measured reason the span path needs a host probe, so nobody assumes it is covered."""
        composed = (
            STDLIB.read_text(encoding="utf-8")
            + "\nvar probe = text_builder_push_span(text_builder_new(), source_bytes(), 0, 1)\n"
            + "say(int_text(text_builder_bytes(probe)))\n")
        ran = run_pep(composed.encode("utf-8"), "text_builder_span")
        self.assertEqual(ran.returncode, 1)
        self.assertIn("PEP_RUNTIME_SOURCE_CONTEXT", ran.stdout + ran.stderr)

    def test_span_entry_point_is_covered_through_the_tool_host(self):
        """The interpreter cannot reach `source_bytes()`, so the span path is proved where it works.

        The probe registers the module against the tool host and passes each payload as the v2
        semantic target, which is the only context where `source_bytes()` is authorised.
        """
        ran = subprocess.run([sys.executable, str(ROOT / "tests" / "probe_text_builder_span.py")],
                             cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
        rows = [json.loads(line) for line in ran.stdout.splitlines() if line.strip().startswith("{")]
        self.assertEqual(len(rows), 4, rows)
        self.assertTrue(all(row["ok"] for row in rows), rows)
        self.assertTrue(all(row["roundTrip"] for row in rows), rows)
        self.assertTrue(any(row["characters"] != row["bytes"] for row in rows),
                        "at least one case must show byte width differing from character count")

    def test_native_lowering_is_classified_not_assumed(self):
        """Report which of success / refusal / step limit the C23 emitter gives this module."""
        from pep_c23 import emit

        composed = STDLIB.read_text(encoding="utf-8") + "\n" + CONSUMER.read_text(encoding="utf-8")
        try:
            emitted = emit(composed.encode("utf-8"))
        except ValueError as error:
            self.assertIn("Pep C23", str(error), f"unexpected refusal: {error}")
            return
        except RuntimeError as error:
            self.assertIn("PEP_RUNTIME_STEP_LIMIT", str(error),
                          f"native attempt failed for an unexpected reason: {str(error)[:200]}")
            return
        self.assertIn("typedef struct", emitted)
        self.assertTrue(emitted.endswith("\n"))


if __name__ == "__main__":
    unittest.main()
