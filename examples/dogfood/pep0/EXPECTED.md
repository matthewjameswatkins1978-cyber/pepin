# Pep-0 compiler A — Slice-1 expectations (A4 lane)

Canonical source: `examples/dogfood/pep0/compiler_a.pep` (this revision).
Handoff target: A2 emitter run (slice 2), then A3 independent verify.

## Subset S0 (exact)

- Exactly: `fn main() -> Int { return DECIMAL }`, DECIMAL = 1–18 ASCII digits.
- Separators: space/tab/LF/CR. Required after `fn` and after `return`;
  optional around every other joint; `->` contiguous.
- Glued forms (`fnmain`, `return42`) are REJECTED (boundary checks), never
  misread: prefix matching is safe because the following expect fails.
- Non-ASCII/NUL bytes are not whitespace and fail shape (err 1).
- Truncated inputs fail closed at runtime (bounds guards on matchers;
  unconditional skip/scan calls are guarded by err state). Never wrong C.

## Pinned inputs and exact expected results

### `a_ok.pep` — positive
Bytes: `fn  main() -> Int {\n  return 42\n}\n` (double space, LF, indent).
Expected exit **0**, stdout exactly these 9 lines:
```
int main
(
void
)
{
return
42
;
}
```
(Valid C modulo newlines; punctuation via `int_text` keeps say literals
alphanumeric+space, inside the proven F3 say shapes.)

### `a_badlit.pep` — negative, bad literal
Bytes: `fn main() -> Int { return ; }\n`.
Expected exit **2**, stdout exactly: `ERR literal`

### `a_badbrace.pep` — negative, malformed brace
Bytes: `fn main() -> Int { return 42 ]\n`.
Expected exit **1**, stdout exactly: `ERR shape`

### `a_str.pep` — negative, unsupported return type
Bytes: `fn main() -> Str { return "s" }\n` (seed-valid: returns Str; out of subset S0).
Expected exit **5**, stdout exactly: `ERR unsupported`

### `a_empty.pep` — edge, empty input
Bytes: none (0-byte file; seed-valid vacuous program).
Expected exit **0**, stdout empty (no output).

### `a_crlf.pep` — positive, CRLF line endings
Bytes: `fn main() -> Int {\r\n  return 42\r\n}\r\n` (seed-valid; stored `-text` to preserve CRLF).
Expected exit **0**, same 9-line C as `a_ok.pep`.

### `a_u8.pep` — negative, non-ASCII space
Bytes: `fn\u00a0main() -> Int { return 42 }\n` (NBSP U+00A0; seed-invalid).
Expected exit **1**, stdout exactly: `ERR shape`

### `a_nul.pep` — negative, leading NUL byte
Bytes: `\x00fn main() -> Int { return 42 }\n` (leading NUL; seed-invalid
`PEP_UNEXPECTED_CHARACTER`; stored `-text` to keep the byte exact).
Expected exit **1**, stdout exactly: `ERR shape` (hand-traced: `find_fn`
fails on byte 0; native confirmation pending S2).

### `a_big19.pep` — negative, 19-digit in-range literal
Bytes: `fn main() -> Int { return 1000000000000000000 }\n` (19 digits,
value fits Int64; seed-VALID, subset caps at 18).
Expected exit **4**, stdout exactly: `ERR longlit` (hand-traced:
`19 <= e - ds` gate; native confirmation pending S2).

### `a_foo.pep` — unsupported, no `main` entrypoint
Bytes: `fn foo()->Int{return 1}\n` (seed-VALID: defined-but-unused).
Expected exit **5**, stdout exactly: `ERR unsupported` (hand-traced:
fallback `is_unsupported_prog` matches the complete non-main def;
contract corrected per A3-153, was exit 1; native confirmation pending S2).

### `a_dup.pep` — negative, duplicate `main`
Bytes: `fn main()->Int{return 1}\nfn main()->Int{return 2}\n`
(seed-invalid: `PEP_DUPLICATE_FUNCTION`).
Expected exit **3**, stdout exactly: `ERR junk` (hand-traced: second form
is trailing bytes after `}`; native confirmation pending S2).

### `a_gfn.pep` — negative, glued `fn` keyword
Bytes: `fnmain()->Int{return 42}\n` (seed-invalid:
`PEP_PARSE_EXPRESSION`).
Expected exit **1**, stdout exactly: `ERR shape` (hand-traced: ws-after-`fn`
gate fails on `m`; native confirmation pending S2).

### `a_grt.pep` — negative, glued `return` literal
Bytes: `fn main()->Int{return42}\n` (seed-invalid:
`PEP_UNKNOWN_VARIABLE`).
Expected exit **2**, stdout exactly: `ERR literal` (hand-traced: `is_ws_at`
after `urn` fails on `4`; native confirmation pending S2).

### `a_Main.pep` — unsupported, capitalised entrypoint
Bytes: `fn Main()->Int{return 1}\n` (seed-VALID: `Main` is a different name).
Expected exit **5**, stdout exactly: `ERR unsupported` (hand-traced: generic-name
fallback path; native confirmation pending S2).

### `a_unary.pep` — unsupported, unary minus
Bytes: `fn main()->Int{return -42}\n` (seed-VALID).
Expected exit **5**, stdout exactly: `ERR unsupported` (hand-traced:
`scan_value` unary path; native confirmation pending S2).

### `a_binop.pep` — unsupported, binary minus
Bytes: `fn main()->Int{return 0-42}\n` (seed-VALID).
Expected exit **5**, stdout exactly: `ERR unsupported` (hand-traced:
`scan_value` chained-binop path; native confirmation pending S2).

### `a_plusop.pep` — unsupported, binary plus
Bytes: `fn main()->Int{return 0+42}\n` (seed-VALID).
Expected exit **5**, stdout exactly: `ERR unsupported` (hand-traced: generic
binop operator; proves the fallback is not hard-coded to `-`; native
confirmation pending S2).

### `a_var.pep` — unsupported, `var` declaration
Bytes: `fn main()->Int{var x = 1 return x}\n` (seed-VALID).
Expected exit **5**, stdout exactly: `ERR unsupported` (hand-traced:
`match_varlet_body` with declared/returned name equality; native
confirmation pending S2).

### `a_let.pep` — unsupported, `let` declaration
Bytes: `fn main()->Int{let x = 1 return x}\n` (seed-VALID).
Expected exit **5**, stdout exactly: `ERR unsupported` (hand-traced: same as
`a_var.pep`; native confirmation pending S2).

### `a_twofn.pep` — unsupported, leading non-main definition
Bytes: `fn a()->Int{return 1} fn main()->Int{return 2}\n` (seed-VALID multi-fn).
Expected exit **5**, stdout exactly: `ERR unsupported` (hand-traced: trailing
`fn`-with-different-name path; native confirmation pending S2).

### `a_mainfn.pep` — unsupported, trailing non-main definition
Bytes: `fn main()->Int{return 1} fn foo()->Int{return 2}\n` (seed-VALID multi-fn).
Expected exit **5**, stdout exactly: `ERR unsupported` (hand-traced: trailing-fn
path on a main-first program; native confirmation pending S2).

### `a_badname.pep` — negative, numeric function name
Bytes: `fn 123()->Int{return 1}\n` (seed-invalid: `PEP_PARSE_NAME`).
Expected exit **1**, stdout exactly: `ERR shape` (hand-traced: generic-name scan
finds no name; native confirmation pending S2).

### `a_dash.pep` — negative, bare unary minus
Bytes: `fn main()->Int{return -}\n` (seed-invalid: `PEP_PARSE_EXPRESSION`).
Expected exit **2**, stdout exactly: `ERR literal` (hand-traced: `scan_value`
finds no digits; native confirmation pending S2).

### `a_bintrail.pep` — negative, dangling operator
Bytes: `fn main()->Int{return 0-}\n` (seed-invalid: `PEP_PARSE_EXPRESSION`).
Expected exit **3**, stdout exactly: `ERR junk` (hand-traced: binop chain finds
no right operand; native confirmation pending S2).

### `a_varbad.pep` — negative, numeric `var` name
Bytes: `fn main()->Int{var 123 = 1 return x}\n` (seed-invalid: `PEP_PARSE_NAME`).
Expected exit **1**, stdout exactly: `ERR shape` (hand-traced: declared-name scan
fails; native confirmation pending S2).

### `a_varnox.pep` — negative, `var` without assignment
Bytes: `fn main()->Int{var x return x}\n` (seed-invalid: `PEP_PARSE_EXPECTED`).
Expected exit **1**, stdout exactly: `ERR shape` (hand-traced: `=` expected;
native confirmation pending S2).

### `a_trailfn.pep` — negative, truncated trailing definition
Bytes: `fn main()->Int{return 1} fn(\n` (seed-invalid: `PEP_PARSE_NAME`).
Expected exit **3**, stdout exactly: `ERR junk` (hand-traced: trailing `fn` has
no name; native confirmation pending S2).

## Exit-code table

| code | meaning | example |
|---|---|---|
| 0 | ok, valid C on stdout — or empty input, silent | `a_ok.pep`, `a_empty.pep` |
| 1 | bad shape (structure/brace/delimiter/unknown name) | `a_badbrace.pep`, `a_gfn.pep`, `fnmain...`, `a_nul.pep`, `a_badname.pep`, `a_varbad.pep`, `a_varnox.pep` |
| 2 | bad literal (no digits, glued `return42`, bare `-`) | `a_badlit.pep`, `a_grt.pep`, `a_dash.pep` |
| 3 | trailing junk after valid form | `...} extra`, `a_dup.pep`, `a_bintrail.pep`, `a_trailfn.pep` |
| 4 | literal longer than 18 digits (out of subset, kept distinct) | `a_big19.pep` (19 digits, seed-valid) |
| 5 | unsupported (seed-valid but out-of-subset type or form) | `a_str.pep` (`-> Str`), `a_foo.pep` (non-main), `a_Main.pep`, `a_unary.pep`, `a_binop.pep`, `a_plusop.pep`, `a_var.pep`, `a_let.pep`, `a_twofn.pep`, `a_mainfn.pep` |

## Prime emitter-refusal candidates for A2's run (most to least likely)

1. `is_main4` 5-conjunct `&&` (proven max is 3 in A1's is_fn_at).
2. `while go`-free flag loops: single `<=` condition is new vs negated form;
   call (`is_ws`/`is_digit`) inside loop-body `if`.
3. `*` in `parse_value` (checker must accept first).
4. 3-parameter functions (`expect_byte`, `parse_value`).
5. `say(int_text(LITERAL))` with literal arg (p24 proved variable arg).
6. ~14 sequential guarded `if`s in `main`/`find_*` (node budget per chunk).
7. `var neg1 = 0 - 1` / `ds == neg1` comparison shape.

Fallback ladder if refused: split long-`&&` into 3-byte atoms; split big
finders further; replace `*` with slice-echo. No new host builtins needed.

Outcome post-S1 (`7e820a7`, per A3-101): the call-position refusals
(candidates 2/6/7 and the `is_ws_at`/`skip_ws`/`scan_digits` shapes) now emit
where the step budget allows; `is_main4`/`is_bool4`/`is_unit4` + `main`
remain step-limited (S2). Per-function movement: see A1's S1 table.
