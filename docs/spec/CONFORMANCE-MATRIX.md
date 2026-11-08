# Pep v0.1 Conformance Matrix (core)

- **Status:** working map, not a pass/fail certificate. Each row maps a normative
  requirement in `PEP-LANGUAGE-SPEC-v0.1.md` (§) to the seed test(s) that exercise
  it at spec-branch base, names uncovered requirements, and proposes concrete
  executable cases with expected outcomes.
- **Counting convention:** "N tests" = `def test_` methods counted in the named
  file at this branch base (test_cli 45, test_a6 11, test_a7 5, test_a8 5,
  test_a10 9, test_a11 7, test_a12 22, test_a13 72 + nested-records 13, test_a14_c23
  11, test_c23_cli 5, test_lab 26, test_moonbit_cli 11, test_textbuf_native 22).
  A13/A14/C23/lab/textbuf suites exercise **development-branch** behavior; they are
  cited only where they pin core parity, never as core acceptance.
- **Evidence honesty:** test names below were read, not all re-executed here.
  Re-executed this mission: `describe --json` (live),
  `test_a6...test_list_and_binding_diagnostics` (pass). Rows marked **[proposed]**
  do not exist yet.

## M-1 Lexical and source rules (Spec §2–§3)

| Requirement | Covering test(s) | Gap / proposed case |
|---|---|---|
| Invalid UTF-8 rejected | test_cli LF/CRLF test; test_a10 UTF-8 validator tests | — |
| `#` and `//` comments | implicit in fixtures (no dedicated test found) | **[proposed]** `check` program with `#` and `//` comments incl. `#@`-looking text; expect valid + byte-identical spans |
| CRLF/LF parity + original offsets | `test_lf_and_crlf_preserve_semantics_and_original_offsets` (+ session CRLF tests, test_a10/test_a12 unicode tests) | — |
| String escapes; invalid escape / raw newline / unterminated | covered via parser tests (test_a10 invalid-escape/UTF-8 span tests) | **[proposed]** one fixture per escape `\\n \\r \\t \\0 \\\\ \\"` with exact value assertion via `run` |
| `PEP_INT_LITERAL_RANGE` on huge literal | parser tests (test_a13 literal checks) | **[proposed]** `let x = 9223372036854775808` → invalid, code `PEP_INT_LITERAL_RANGE` |
| Reserved names rejected | `test_invalid_syntax_and_reserved_builtin_names_do_not_crash` | — |
| No `<`, `>`, `%` single-char tokens | test_a6 diagnostics (implicit) | **[proposed]** `let x = 1 < 2` → `PEP_UNEXPECTED_CHARACTER`; documents the single-comparison core |

## M-2 Statements and functions (Spec §5.1–§5.3)

| Requirement | Covering test(s) | Gap / proposed case |
|---|---|---|
| Recursion + forward calls | `test_recursive_factorial_runs` | — |
| Missing return / unreachable after return | **no dedicated test found in test_cli/test_a6 names** | **[proposed]** `fn f() -> Int { let x = 1 }` → `PEP_MISSING_RETURN` with expected `Int`; `fn f() -> Int { return 1  return 2 }` → `PEP_UNREACHABLE` |
| Statement-`if` requires `else` | test_a6 `if 1 {} else {}` (type); parse rule untested by name | **[proposed]** `if true { say(\"a\") }` → `PEP_PARSE_ELSE` |
| `while` Bool condition; budget stop | `while 1 {}` type case (test_a6); `test_unbounded_while_stops_at_runtime_budget` | — |
| `for-in` requires `List[T]`; loop var scoped/immutable | `test_loop_binding_is_immutable_and_loop_return_flow_is_conservative`, `for item in [1] {} ...` unknown-after-loop case | — |
| Assignment rules (unknown/immutable/type) | four test_a6 diagnostic cases | — |
| No `break`/`continue` | none (correctly — feature absent) | **[proposed]** negative fixture `break` → parse rejection, guarding the boundary |

## M-3 Expressions and typing (Spec §6)

| Requirement | Covering test(s) | Gap / proposed case |
|---|---|---|
| `<=` Int-only; `==`/`!=` scalar-only | test_a6 diagnostics; scalar-equality + short-circuit tests (§6.2 row) | **[proposed]** `1 <= true` → `PEP_TYPE_MISMATCH`; `[1] == [1]` → `PEP_EQUALITY_UNSUPPORTED` (extends test_a13 deep-list rejection to core suite) |
| Short-circuit `&&`/`\|\|` | `test_short_circuit_and_mutable_loop_execution` | — |
| `if`-expression branch agreement + hole inference | `test_match_infers_result_type_for_earlier_holes`, `test_call_argument_hole_infers_parameter_type` | **[proposed]** `if true { ?h } else { 1 }` → hole `?h` expected `Int` |
| Empty-list needs type; nested empties; mixed literal | test_a6 diagnostics (`[]`, `[[],[]]`, `[1,true]`) | — |
| Builtin arity/type errors; `contains` scalar-only | `append(values, true)` case; Points/`contains` → `PEP_MEMBERSHIP_UNSUPPORTED` | — |
| `prepend`/`reverse` O(1)/O(n) semantics | examples `a6_collections_control.pep` run test (outputs asserted) | **[proposed]** aliasing fixture: `let b = append(a, 1)` then `length(a)` unchanged — pins value semantics executably |

## M-4 Records, unions, match (Spec §5.4, §6.4)

| Requirement | Covering test(s) |
|---|---|
| Record decl/construction/field errors | `test_records_are_checked_resolved_and_interpreted`, `test_record_declaration_and_construction_errors` |
| Recursive unions, nested patterns, match eval | `test_recursive_tagged_union_match_and_checked_evaluation`, `test_nested_patterns_and_constructor_runtime` |
| Arm-local holes; result-type inference | `test_match_holes_have_expected_types_and_arm_local_bindings`, `test_match_infers_result_type_for_earlier_holes` |
| Union/match error codes; non-exhaustive; unreachable arms | `test_union_constructor_and_match_errors` (+ test_a13's 72 differential tests for fine-grained codes) |

Gap: **same-line record-literal rule** (§5.4) has no named test. **[proposed]**
`Point\n{ x: 1 }` parses as block (invalid) vs `Point { x: 1 }` valid — the one
line-sensitive rule deserves two fixtures.

## M-5 Holes and program states (Spec §1, §8)

| Requirement | Covering test(s) |
|---|---|
| Hole contexts, expected types, bindings, actions | `test_hole_reports_expected_type_bindings_and_action`, `test_function_hole_query_reports_return_type_and_parameter_scope`, `test_function_hole_candidates_use_visible_binding_types`, `test_call_argument_hole_infers_parameter_type` |
| Unconstrained hole stays unconstrained | `test_unconstrained_hole_does_not_claim_an_expected_type`, `test_unannotated_binding_hole_is_explicitly_unconstrained` |
| Hole in unused fn still blocks `run` | `test_hole_in_unreferenced_function_prevents_any_execution` |
| `check` exit codes for incomplete/invalid | `check` paths in diagnostics tests (exit 1 asserted) |
| fill_hole preview/apply/stale/ambiguous, span preservation | 6 `test_session_fill_hole_*` tests |
| First-error-only reporting | implicit (diagnostics[0] assertions) — no test asserts *absence* of a second error | **[proposed]** fixture with two independent errors asserting exactly one diagnostic |

## M-6 Runtimes, budgets, effects (Spec §4)

| Requirement | Covering test(s) |
|---|---|
| Overflow + division-by-zero controlled | `test_integer_overflow_and_division_by_zero_are_controlled` |
| Budgets in `describe`; tool budgets enforced | `describe` live check (1M/512); `test_tool_loop_and_collection_work_obey_step_budget`, tool validation tests |
| `say` newline output; `int_text` | example-run assertions (`a6` outputs, hello) |
| `run` refuses holes; JSON vs human diagnostics | hole-prevents-execution test; structured-mismatch tests |

Gap: **truncation-toward-zero division** and `Int64.min_int / -1` overflow have no
named core fixture. **[proposed]** `run` fixtures: `-7 / 2 == -3`; `min_int / -1`
→ `PEP_RUNTIME_OVERFLOW`.

## M-7 Machine interface (Spec §10)

| Requirement | Covering test(s) |
|---|---|
| `describe` schema/types/features | `test_describe_reports_seed_and_supported_types`, `test_describe_reports_implemented_collections_and_control_flow`, plus live run this mission |
| `inspect` AST spans; `query` determinism + `--offset` | `test_inspect_returns_source_spanned_ast`, `test_query_is_deterministic_and_accepts_source_offset` |
| Session revisions, SHA-256 IDs, cache, stale-edit rejection | `test_session_revisions_queries_and_analysis_cache`, `test_session_revision_hash_matches_sha256_for_multiblock_source`, `test_session_edit_preserves_old_revision_and_rejects_stale_edit`, byte-range/UTF-8 edit tests |
| Malformed JSONL does not kill session | `test_session_malformed_json_does_not_end_process` |

## M-8 Explicitly out of core (Spec §9, §11)

SourceBytes/byte builtins, tool registry v1/v2, A10–A14 staged-compiler parity and
C23 emission are exercised by test_a10/a11/a12/a13/a14/test_c23_cli — cited here
only as *development-branch* evidence. No core requirement depends on them; the
core suite (test_cli + test_a6/a7/a8) MUST stay green without them.

## Proposed conformance-case backlog (priority order)

1. Missing-return / unreachable-return fixtures (M-2).
2. Statement-`if`-without-`else` parse fixture (M-2).
3. `<`/`>`/`%` rejection fixtures pinning the single-comparison core (M-1).
4. Same-line record-literal pair (M-4).
5. `min_int / -1`, negative-division truncation fixtures (M-6).
6. First-error singularity assertion (M-5).
7. Append-aliasing value-semantics fixture (M-3).
8. Per-escape string fixtures (M-1).
9. `break`/`continue` absence fixture (M-2).
10. `[1] == [1]` core-suite rejection (M-3).
