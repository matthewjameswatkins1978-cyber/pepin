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

    def test_guard_chain_str_returns_match_seed_on_both_compilers(self):
        """G-A2-3: the real lexer's guard-chain Str shape, end to end with seed parity.

        Source evidence: stdlib/scan.pep:730 `lex_error_code` returns string literals from
        statement-level `if ... { return ... } else {}` guards plus a fallthrough, and its one
        real call site (scan.pep:845) passes RECORD-FIELD ARGUMENTS (`classified.kind`,
        `classified.diagnostic`) -- so this fixture uses exactly that pattern: record fields
        into a two-parameter Str function, guard-chain returns, observed through let + say.
        MEASURED BOUNDARY (receipt, not pinned here because parser positions shift): the FULL
        five-guard function plus this record program exceeds the unchanged PARSER step budget
        (PEP_RUNTIME_STEP_LIMIT at 2451:8, parse stage, the issue #20 class -- A1's lane), so
        the proven slice uses the three-guard core; the SHAPE is what this test pins.
        """
        native_source = (
            'type Info { kind: Str, diagnostic: Str }\n'
            'fn lex_error_code(kind: Str, diagnostic: Str) -> Str {\n'
            '  if kind == "unexpected" { return "PEP_UNEXPECTED_CHARACTER" } else {}\n'
            '  if kind == "integer" { return "PEP_INT_LITERAL_RANGE" } else {}\n'
            '  return "PEP_LEXER_INPUT"\n'
            '}\n'
            'fn main() -> Int {\n'
            '  let i = Info { kind: "integer", diagnostic: "" }\n'
            '  let code = lex_error_code(i.kind, i.diagnostic)\n'
            '  say(code)\n'
            '  return 0\n'
            '}\n')
        c_source = emit_c(native_source)
        self.assertIn('(const unsigned char *)', c_source)       # static-storage literals
        self.assertIn('pep_str pep_fn_lex_error_code', c_source)  # Str result signature
        seed_source = native_source.split("fn main()")[0] + (
            'let i = Info { kind: "integer", diagnostic: "" };\n'
            '  let code = lex_error_code(i.kind, i.diagnostic);\n'
            '  say(code);\n')
        seed_bytes = normalize(seed_run(seed_source, "ga23_guard_chain_seed"))
        self.assertEqual(seed_bytes, b"PEP_INT_LITERAL_RANGE\n")  # the guard actually fired
        for compiler in ("clang", "gcc"):
            with self.subTest(compiler=compiler):
                stdout, exit_code = build_and_run(compiler, c_source,
                                                  f"ga23_guard_chain_{compiler}")
                self.assertEqual(exit_code, 0)
                self.assertEqual(normalize(stdout), seed_bytes + b"0\n")

    def test_str_lifetime_chains_match_seed_on_both_compilers(self):
        """G-A2-5: four lifetime/ownership chains actually used in Pep sources -- NO DEFECT
        found, byte parity pinned (card: prove parity or clean refusal; fix only what breaks).

        Chains: (1) embedded NUL in a RETURNED Str; (2) embedded NUL in a Str record FIELD;
        (3) field initialised from a CALLEE's returned literal (static storage must outlive
        the callee frame); (4) caller-owned Str stored into a record the callee RETURNS, then
        re-wrapped through the same pointer (alias past frame + reuse). ASan was attempted
        without install: clang built but the runtime DLL is absent on this host
        (process exit 0xC000013A, no ASan report) -- recorded NOT-APPLICABLE in the receipt,
        deliberately not pinned here so the test never depends on an uninstalled runtime.
        """
        cases = {
            "returned-nul": (
                'fn mark() -> Str {\n  return "a\\0b"\n}\n'
                'fn main() -> Int {\n  let s = mark()\n  say(s)\n  return 0\n}\n',
                'let s = mark();\n  say(s);\n',
                b'a\x00b\n'),
            "field-nul": (
                'type Info { kind: Str }\n'
                'fn main() -> Int {\n'
                '  let i = Info { kind: "x\\0y" }\n'
                '  say(i.kind)\n'
                '  return 0\n'
                '}\n',
                'let i = Info { kind: "x\\0y" };\n  say(i.kind);\n',
                b'x\x00y\n'),
            "field-from-callee": (
                'type Info { kind: Str }\n'
                'fn tag() -> Str {\n  return "from-callee\\0end"\n}\n'
                'fn main() -> Int {\n'
                '  let i = Info { kind: tag() }\n'
                '  say(i.kind)\n'
                '  return 0\n'
                '}\n',
                'let i = Info { kind: tag() };\n  say(i.kind);\n',
                b'from-callee\x00end\n'),
            "param-str-into-returned-record": (
                'type Info { kind: Str }\n'
                'fn wrap(v: Str) -> Info {\n  return Info { kind: v }\n}\n'
                'fn main() -> Int {\n'
                '  let i = wrap("caller-owned")\n'
                '  say(i.kind)\n'
                '  let again = wrap(i.kind)\n'
                '  say(again.kind)\n'
                '  return 0\n'
                '}\n',
                'let i = wrap("caller-owned");\n  say(i.kind);\n'
                '  let again = wrap(i.kind);\n  say(again.kind);\n',
                b'caller-owned\ncaller-owned\n'),
        }
        for name, (native_source, seed_body, expected_seed) in cases.items():
            with self.subTest(chain=name):
                c_source = emit_c(native_source)
                seed_source = native_source.split("fn main()")[0] + seed_body
                seed_bytes = normalize(seed_run(seed_source, f"ga25_{name}_seed"))
                self.assertEqual(seed_bytes, expected_seed)
                for compiler in ("clang", "gcc"):
                    with self.subTest(compiler=compiler):
                        stdout, exit_code = build_and_run(compiler, c_source,
                                                          f"ga25_{name}_{compiler}")
                        self.assertEqual(exit_code, 0)
                        self.assertEqual(normalize(stdout), seed_bytes + b"0\n")


class StrResultBoundaries(unittest.TestCase):
    """Each refusal below was MEASURED during this slice; none is assumed."""

    def test_conditional_return_str_body_still_refuses(self):
        """TWO-BRANCH conditional Str stays refused (the one exact negative, G-A2-3).

        Path measured after the G-A2-3 guard-chain slice: if_return_body still gates Str out,
        the fall-through straight-line analysis then requires a TOP-LEVEL return (the returns
        live inside the if/else branches), so the program refuses with the return-statement
        diagnostic instead of the old conditional one. Still fail-closed, empty sourceParts --
        only the message moved; GUARD-CHAIN Str returns (empty else + fallthrough, the real
        lex_error_code shape) are supported and pinned positive in
        test_guard_chain_str_returns_match_seed_on_both_compilers.
        """
        with self.assertRaises(ValueError) as caught:
            emit_c('fn pick(flag: Bool) -> Str {\n'
                   '  if flag { return "yes" } else { return "no" }\n'
                   '}\n'
                   'fn main() -> Int { return 0 }\n')
        self.assertIn("functions require a return statement", str(caught.exception))

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
