# Pep-0 subset — normative boundary (A4 lane, LUCY-20261108-015 A4-S1)

Status: NORMATIVE for compiler-A acceptance. Grammar changes require a
Matthew-level accepted-language decision. Implementation coverage is
rev-3 (`d78735e`); implementation pins live in `EXPECTED.md`.
Boundary evidence replayed 17/17 from prose by A3 (BOOT-A3-088).

## Class (iii) — Pep-0-valid (the subset S0, exact)

- Exactly: `fn main() -> Int { return DECIMAL }`, DECIMAL = 1–18 ASCII
  digits (leading zeros accepted: `007` seed-valid, parses to 7).
- Separators: space (32), tab (9), LF (10), CR (13); CRLF and CR-only
  line endings accepted. Required after `fn` and after `return`;
  optional around every other joint; `->` contiguous.
- Glued forms (`fnmain`, `return42`) are REJECTED, never misread.
- Keywords lowercase (`fn`, `return`); type word capitalized (`Int`);
  names case-sensitive (`Main` is a different name, see class (ii)).
- 19-digit literals: the subset caps at 18 digits (err 4) even when the
  value fits Int64 — the subset is deliberately narrower than the seed.
- Accepted-program pins: `a_ok.pep`, `a_crlf.pep` (EXPECTED.md).

## Class (ii) — seed-valid but outside Pep-0 (defined behavior, no C)

- `-> Str`, `-> Bool`, `-> Unit` returns on `main` (e.g. `a_str.pep` → exit 5).
- Non-`main` single-fn programs, zero params, Int/Str/Bool returns
  (e.g. `a_foo.pep`, `a_Main.pep` → exit 5); a trailing second `fn` def
  with a different name likewise (e.g. `a_twofn.pep`, `a_mainfn.pep` →
  exit 5; duplicate names stay exit 3).
- Empty (0-byte) input: seed-valid vacuous program → exit 0 silent.
- Unary minus (`-42`, optional space) and single binary arithmetic on Int
  literals (`0-42`, `0+42`; single leading `-` only; no parens):
  seed-valid, not in S0, no C emitted (e.g. `a_unary.pep`, `a_binop.pep`).
  Chained input (`0-1-2`) is out of contract: the fallback parses one group
  and the tail check fails, so the S0 shape error stands.
- `var`/`let` single declarations with Int values and Int returns, declared
  name equal to returned name (e.g. `a_var.pep`, `a_let.pep` → exit 5).
- 19-digit in-range literals (e.g. `1000000000000000000`, seed-valid):
  rejected by the 18-digit subset cap (exit 4), never wrapped.
- Outside the fallback tier too (stay at shape/literal/junk codes): `var`
  with non-Int values, loops, statement `if`, params-ful or `main`-with-params
  fns, parenthesised values, `--` prefix, `Unit`-typed non-`main` fns,
  other return type words, multi-`var` bodies, doubled `fn` names.
  Multi-fn (`pos_twofn`) is Slice-3 scope, not S0.

## Class (i) — seed-invalid (rejected by the seed; never reach subset)

- Lexer: NUL (`\000`), 3-byte UTF-8 BOM (`EF BB BF`; lone first byte
  untested), VTAB (`\011`), NBSP —
  all `PEP_UNEXPECTED_CHARACTER`. (My `is_ws` matches the seed set
  exactly: 32/9/10/13 only.)
- Parse: uppercase `FN` (`PEP_PARSE_EXPRESSION`), missing/mismatched
  braces (`a_badbrace.pep`), glued forms are shape errors in my
  compiler (exit 1) on seed-invalid structure.
- Check: lowercase `int` (`PEP_UNKNOWN_TYPE`), arity mismatch and
  unknown names (seed 1-diag invalids; my exit 1 shape class).
- Range: integer literal above Int64 max (`PEP_INT_LITERAL_RANGE`).

## Boundary evidence (all measured, this mission)

Seed `check --json` on 16 probes (`_build/s1/`, ignored scratch):
`i64max` valid; `i64max+1`/23-digit invalid (RANGE); `007` valid;
`1000000000000000000` valid; `-42`/`0-42` valid; `Main` valid;
CR-only/CR tab/LF valid; NUL-mid/trail, BOM, VTAB, NBSP invalid (LEX);
`FN` invalid (parse); `int` invalid (UNKNOWN_TYPE). A1's 16-shape oracle
cross-checks CRLF/NBSP/empty/`out_str` 4/4 on A4's exact bytes.

## Reserved (not decided)

- Whether S0 should ever widen (unary minus, binop, 19-digit cap relief)
  is an accepted-language decision, not an implementation convenience.
  M-2 (own-source) will force the first honest extension proposal.
