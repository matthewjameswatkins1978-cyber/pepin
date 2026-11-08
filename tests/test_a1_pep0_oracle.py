"""A1 semantic oracle for the Pep-0 tiny subset (LUCY-20261107-014 Slice 2).

Executable pin of SEED-checker behavior (`pep.ps1 check --json`) that native
compiler-A must mirror within the shared subset. Each case asserts the exact
whole-file status, the first diagnostic code, and its span. Expectations were
observed from the seed on 2026-11-07 and any mismatch is a finding, not an
oracle edit.

Subset rules pinned here:
- `fn main() -> Int { return DECIMAL }`, whitespace-insensitive: valid.
- 0-byte input and whitespace-only input -> valid (vacuous programs).
  `empty_zero` (0 bytes) and `inc_ws` (lone newline) pin the two apart:
  a compiler A that requires at least one byte would pass `inc_ws`
  and fail `empty_zero`.
- Two-function declaration + call: valid (seed; forward order untested here).
- Unknown callee -> PEP_UNKNOWN_FUNCTION; arity -> PEP_ARGUMENT_COUNT;
  return-type -> PEP_TYPE_MISMATCH.
- Truncation/malformed input -> *invalid* (PEP_PARSE_EXPECTED/EXPRESSION):
  whole-file `check` does not return `incomplete`; that status belongs to the
  chunk protocol only (`empty_zero`/`inc_ws` above are the valid
  vacuous cases).
- Trailing junk after the function lexes as a following statement, hence
  PEP_UNKNOWN_VARIABLE — the seed has no dedicated trailing-junk code.
- `return 4x` parses the `4`, then flags `x` PEP_UNREACHABLE (unreachable
  statement after the return expression). Pinned as observed; odd but stable.
- `return match` with integer-literal patterns is seed-INVALID
  (PEP_PARSE_PATTERN): natively refusing it mirrors the seed, no special
  unsupported rule needed.
- `fn main() -> Str` is seed-VALID but outside the Pep-0 subset: native A
  must refuse it as *unsupported* with a distinct diagnostic, never report
  it as *invalid*. This is the unsupported-vs-invalid distinction.
"""
import json
import pathlib
import re
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "pep0_oracle"

# name -> (status, [(code, start_offset, end_offset, line, column)])
EXPECTED = {
    "pos_42": ("valid", []),
    "pos_ws": ("valid", []),
    "pos_twofn": ("valid", []),
    "neg_unknown": ("invalid", [("PEP_UNKNOWN_FUNCTION", 26, 37, 1, 27)]),
    "neg_arity": ("invalid", [("PEP_ARGUMENT_COUNT", 73, 79, 2, 27)]),
    "neg_rettype": ("invalid", [("PEP_TYPE_MISMATCH", 26, 30, 1, 27)]),
    "neg_brace": ("invalid", [("PEP_PARSE_EXPECTED", 28, 28, 2, 1)]),
    "neg_trail": ("invalid", [("PEP_UNKNOWN_VARIABLE", 30, 37, 1, 31)]),
    "neg_badlit": ("invalid", [("PEP_UNREACHABLE", 27, 28, 1, 28)]),
    # A4 reserve-3 cross-check (@78a59ee, verified identical seed behavior):
    # CRLF separators are valid whitespace; a non-breaking space is a lexer
    # error, not a parse error.
    "crlf_ok": ("valid", []),
    "nbsp_fn": ("invalid", [("PEP_UNEXPECTED_CHARACTER", 2, 3, 1, 3)]),
    "inc_ws": ("valid", []),
    "empty_zero": ("valid", []),
    "inc_fn": ("invalid", [("PEP_PARSE_EXPECTED", 19, 19, 2, 1)]),
    "inc_ret": ("invalid", [("PEP_PARSE_EXPRESSION", 26, 26, 2, 1)]),
    "out_match": ("invalid", [("PEP_PARSE_PATTERN", 42, 43, 3, 5)]),
    # Seed-valid but OUTSIDE the Pep-0 subset: native A must refuse as
    # unsupported, never as invalid. The seed side of that rule is pinned here.
    "out_str": ("valid", []),
    # A4 R1 feed (@593091e, blob-verified 27B/43B): leading NUL is a seed
    # lexer error at offset 0; 19-digit in-range is seed-valid (native A is
    # expected to refuse it separately with exit 4 longlit, outside S0).
    "a_nul": ("invalid", [("PEP_UNEXPECTED_CHARACTER", 0, 1, 1, 1)]),
    "a_big19": ("valid", []),
    # A4 R2 feed (@b555a54, blob-verified 24B/50B/25B/25B): entrypoint,
    # duplicate-function and glued-form negatives. Seed verdicts measured
    # on A4's exact bytes (a_foo is seed-valid; the native exit codes
    # 1/3/1/2 are A4-compiler-side, correctly absent from this seed oracle).
    "a_foo": ("valid", []),
    "a_dup": ("invalid", [("PEP_DUPLICATE_FUNCTION", 25, 49, 2, 1)]),
    "a_gfn": ("invalid", [("PEP_PARSE_EXPRESSION", 8, 10, 1, 9)]),
    "a_grt": ("invalid", [("PEP_UNKNOWN_VARIABLE", 15, 23, 1, 16)]),
}


def check_shape(name):
    target = FIX / (name + ".pep")
    proc = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"),
         "check", str(target), "--json"],
        cwd=ROOT, text=True, capture_output=True, check=False)
    text = proc.stdout.strip()
    text = text.lstrip("\ufeff")
    text = re.sub(r"\x1b\[[0-9;]*m", "", text)
    text = text[text.find("{"):] if "{" in text else text
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return ("DRIVER-ERROR", [(proc.stderr or proc.stdout)[:200]])
    diags = []
    for diag in data.get("diagnostics", []):
        span = diag.get("span", {})
        start = span.get("start", {})
        diags.append((diag.get("code"), start.get("offset"),
                      span.get("endOffset"), start.get("line"),
                      start.get("column")))
    return (data.get("status"), diags)


class Pep0OracleTest(unittest.TestCase):
    def test_oracle_shapes(self):
        failures = []
        for name, (want_status, want_diags) in EXPECTED.items():
            got_status, got_diags = check_shape(name)
            with self.subTest(shape=name):
                if got_status != want_status or got_diags[:1] != want_diags[:1]:
                    failures.append(
                        f"{name}: want {(want_status, want_diags[:1])} "
                        f"got {(got_status, got_diags[:1])}")
        self.assertEqual(failures, [], "oracle drift:\n" + "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
