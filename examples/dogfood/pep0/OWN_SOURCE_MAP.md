# Own-source dependency map (A4 lane, read-only — no implementation, no grammar change)

Source: `compiler_a.pep` @ `9fd6431` (34 functions: 21 original + 13 new; counts below by the
same keyed-walk as INVENTORY.md). Question answered: what stands between
native A and compiling its own canonical source (M-2), and who owns each piece.

## 0. Baseline (measured by others, not assumed)

- M-1 15/15 achieved through the real product path on A1's candidate
  (BOOT-A3-159, pre-fallback source): chain-CHECK 21/21, 10/21 whole-unit
  emit, fragment-assembled main.
- The 7 class-(ii) misclassifications confirmed in the product-path binary
  (BOOT-A3-160) — the exact gap this revision's fallback tier closes.
- Native purity proven (BOOT-A3-161): KERNEL32 only, no interpreter markers.
- Own source is seed-valid (BOOT-A3-097, three seeds, 21 top-level forms).

## 1. Acceptance direction: what S0 must additionally accept (M-2 ladder)

First own-source input is still rejected at the first definition, exit 1
`ERR shape` — now at its parameter list, not its name (the fallback tier
accepts generic names but requires zero-param `()`). M-2 first-failure
oracle stands: input = canonical source, expected first observable =
exit 1 shape.

| rung | construct | example in own source | unblocked by | owner |
|---|---|---|---|---|
| R0 (done) | single paramless non-main Int/Str/Bool fns, plain/unary/binop/var/let bodies | `fn foo()->Int{return 1}` | this revision (S1/R1-R2) | A4 done, A3 to gate natively |
| R1 | parameters (any fn with `(params)`, incl. `main`) | `fn is_ws(b: Int)`, `fn main(source:...)` | S0 grammar decision + implementation | Matthew-level decision, then A4 slice |
| R2 | multi-`var` bodies, nested combos (var+binop, non-main+var) | `fn foo(){var x = 1 return x+1}` | same as R1 (follow-up rung) | same |
| R3 | Unit-typed non-main fns, parens values, `--` prefix, other type words, main-with-params | various | same (later rungs) | same |
| R4 | full recursive set (every construct own source uses) | whole file | R1–R3 complete | same |

Slice-3 `pos_twofn` (2-param + binop + 2-arg call) is a bounded subset of
R1, already planned. No rung is approved here; each needs its acceptance
case. Nothing in this section changes any grammar.

## 2. Emission direction: what must compile the 34 functions (S2)

Whole-chunk CHECK boundary ~47 nodes (A3-099, ~2,100 steps/node); emit
cost/node spans 1,047–2,204 (A3-100) — node counts below inform, only
measured emit steps decide. New (unmeasured) fns marked `*`.

| fn | nodes | status / need |
|---|---|---|
| is_unsupported_prog | 677* | S2 fragments (largest unit) |
| match_varlet_body | 339* | S2 fragments |
| find_brace | 284 | known step-limited; S2 fragments |
| main | 234 (incl. hook) | known step-limited; S2 fragments |
| scan_value | 207* | S2 fragments (straight-line single group, no loop) |
| match_tail | 174* | S2 fragments |
| scan_name | 125* | S2 fragments (loop; measure) |
| find_ds | 118 | known step-limited; S2 |
| find_fn | 99 | known step-limited; S2 |
| scan_string | 81* | S2 fragments or whole-unit (measure) |
| find_parens | 78 | known step-limited; S2 |
| match_return_ws | 73* | S2 or whole-unit (measure) |
| names_equal | 66* | S2 or whole-unit (measure) |
| check_tail | 62 | known step-limited; S2 |
| is_main4/is_bool4/is_unit4/is_true4/is_fals4 | 46/46/46/46/46 | boundary zone (41–48); A1 to measure |
| skip_ws/scan_digits | 45/45 | known step-limited whole-chunk; chained CHECK ok |
| is_int3/is_ret3/is_urn3/is_str3/is_var3/is_let3 | 38 | whole-unit class |
| parse_value | 30 | emits whole today |
| is_fn2/is_ws/is_ws_at/expect_byte/is_digit | 30/24/23/23/16 | emits whole today |

New code follows the proven emit-safe subset (single `==`/`<=` conditions,
`||`-only disjunctions, guarded bytes, no `!=`, no `&&`-in-`while`,
single-statement filled-then + empty-else) so that S2 fragments it without
new emitter shapes. Verification ladder: seed-validity (done, zero diags)
→ A1 chain-CHECK all 34 fns → A1 S1 movement-table rerun → A3 native gate
at S2 (13 old pins must still pass verbatim; 7 new shapes assert exit 5).

## 3. Explicit non-goals

- No S0 grammar change, no new language implementation, no A1/A2 file edits.
- No M-2 attempt until R1 is separately authorised; no S4 feature until M-1
  re-gates on a binary containing this revision.
- The epilogue echo/exit-code questions (A3-149 defects 2–3) stay with
  A1/A2; EXPECTED.md holds 9-line C until their decision lands.

## Handoffs out

- A1: please chain-CHECK the 33-function source (no emit needed) + confirm
  the S1 movement table; S2 fragment entry should cover the 8 starred fns.
- A3: the 7 shapes + 7 malformed-distinction fixtures are ready for the
  native gate once a product binary contains `9fd6431`; EXPECTED.md is the
  contract, PEP0_SUBSET.md the residual list.
