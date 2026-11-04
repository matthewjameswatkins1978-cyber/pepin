"""Str-result functions through the C23 emitter (Campaign F F3: ONE real-lexer blocker).

BLOCKER (measured, BOOT-A2-20261104-019 item 5): the real lexer's `lex_error_code` passes
the CHECKER and then the emitter refused with the function-gate scalar-or-record message --
Str was the one missing result shape on an otherwise scalar pipeline.

WHAT THIS PINS (every shape measured at this revision, 2026-11-04):

* Straight-line `-> Str` functions lower: literal result, Str-parameter pass-through, and
  Str-returning calls bound to immutable locals then printed via `say`. Strict Clang AND GCC
  print byte-identical to the seed running the SAME calls at top level (documented
  entry-point mismatch: the seed ignores `fn main`, native runs it and echoes its return
  value as the final line -- same contract as tests/test_c23_say.py).
* The bytes behind a Str result are a STATIC-storage string literal, never a block-scope
  compound-literal array. Measured during this slice: the array form printed garbage under
  clang and GCC refused `-Wdangling-pointer` under -Werror once the value outlived the
  creating frame. Escaped literals use fixed-width three-digit octal escapes so every byte
  (including NUL and quote) round-trips unambiguously.
* Recorded boundaries, each a measured refusal rather than an assumption: conditional-return
  Str bodies, `say(<direct Str call>)` (keeps say's side-effect-free double-lowering rule),
  and a Str result built by `int_text`. Cross-chunk Str results also stay refused -- the seam
  probe's `neg-foreign-result` control pins that boundary.
* NOT claimed: this is not full Str support (no Str in conditional returns, no say of calls,
  no cross-chunk Str callee results) and not a lexer.

The harness is reused from tests.test_c23_say (emit_c / build_and_run / seed_run /
normalize); no second copy of the pipeline or seed oracle.
"""

import unittest

from tests.test_c23_say import build_and_run, emit_c, normalize, seed_run


class StrResultNativeTests(unittest.TestCase):
    def test_str_results_round_trip_on_both_compilers_with_seed_parity(self):
        """Literal result + parameter pass-through, observed through immutable locals."""
        native_source = (
            'fn tag() -> Str {\n  return "ready"\n}\n'
            'fn relay(source: Str) -> Str {\n  return source\n}\n'
            'fn main() -> Int {\n'
            '  let text = relay("ok")\n'
            '  say(text)\n'
            '  let other = tag()\n'
            '  say(other)\n'
            '  return 0\n'
            '}\n')
        c_source = emit_c(native_source)
        # Static storage: pointer cast to the string literal, not a block-scope array.
        self.assertIn("(const unsigned char *)\"ready\"", c_source)
        self.assertIn("pep_str pep_fn_tag", c_source)
        seed_source = native_source.split("fn main()")[0] + (
            'let text = relay("ok");\n'
            'say(text);\n'
            'let other = tag();\n'
            'say(other);\n')
        seed_bytes = normalize(seed_run(seed_source, "str_result_round_trip_seed"))
        for compiler in ("clang", "gcc"):
            with self.subTest(compiler=compiler):
                stdout, exit_code = build_and_run(compiler, c_source,
                                                  f"str_result_round_trip_{compiler}")
                self.assertEqual(exit_code, 0)
                self.assertEqual(normalize(stdout), seed_bytes + b"0\n",
                                 "seed say surface, then the emitter's return-value echo line")

    def test_escaped_str_result_bytes_round_trip_on_both_compilers(self):
        """The slow literal path: fixed-width octal escapes, still static storage."""
        native_source = (
            'fn esc() -> Str {\n  return "a\\nb"\n}\n'
            'fn main() -> Int {\n  let text = esc()\n  say(text)\n  return 0\n}\n')
        c_source = emit_c(native_source)
        # 97=a 10=LF 98=b -> \141 \012 \142, each escape exactly three digits.
        self.assertIn('(const unsigned char *)"\\141\\012\\142"', c_source)
        seed_source = native_source.split("fn main()")[0] + 'let text = esc();\n  say(text);\n'
        seed_bytes = normalize(seed_run(seed_source, "str_result_esc_seed"))
        for compiler in ("clang", "gcc"):
            with self.subTest(compiler=compiler):
                stdout, exit_code = build_and_run(compiler, c_source,
                                                  f"str_result_esc_{compiler}")
                self.assertEqual(exit_code, 0)
                self.assertEqual(normalize(stdout), seed_bytes + b"0\n")

    def test_str_parameter_result_passes_through_call_boundaries(self):
        """A Str parameter returned verbatim: the caller's bytes, no literal involved."""
        native_source = (
            'fn echo_text(value: Str) -> Str {\n  return value\n}\n'
            'fn main() -> Int {\n  let text = echo_text("ping")\n  say(text)\n  return 0\n}\n')
        c_source = emit_c(native_source)
        seed_source = native_source.split("fn main()")[0] + 'let text = echo_text("ping");\n  say(text);\n'
        seed_bytes = normalize(seed_run(seed_source, "str_result_param_seed"))
        for compiler in ("clang", "gcc"):
            with self.subTest(compiler=compiler):
                stdout, exit_code = build_and_run(compiler, c_source,
                                                  f"str_result_param_{compiler}")
                self.assertEqual(exit_code, 0)
                self.assertEqual(normalize(stdout), seed_bytes + b"0\n")


class StrResultBoundaries(unittest.TestCase):
    """Each refusal below was MEASURED during this slice; none is assumed."""

    def test_conditional_return_str_body_still_refuses(self):
        with self.assertRaises(ValueError) as caught:
            emit_c('fn pick(flag: Bool) -> Str {\n'
                   '  if flag { return "yes" } else { return "no" }\n'
                   '}\n'
                   'fn main() -> Int { return 0 }\n')
        self.assertIn("conditional return requires a supported scalar or record result",
                      str(caught.exception))

    def test_say_of_a_direct_str_call_still_refuses(self):
        """say re-lowers its argument twice; a call there could re-run a callee body."""
        with self.assertRaises(ValueError) as caught:
            emit_c('fn tag() -> Str {\n  return "ready"\n}\n'
                   'fn main() -> Int {\n  say(tag())\n  return 0\n}\n')
        self.assertIn("say lowers only string literals, Str parameters, Str locals and Str fields",
                      str(caught.exception))

    def test_str_result_built_by_int_text_still_refuses(self):
        with self.assertRaises(ValueError) as caught:
            emit_c('fn num() -> Str {\n  return int_text(5)\n}\n'
                   'fn main() -> Int { return 0 }\n')
        self.assertIn("cross-chunk call has no resolved call fact", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
