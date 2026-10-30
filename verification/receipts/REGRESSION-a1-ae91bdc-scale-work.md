# URGENT REGRESSION — A1 `ae91bdc` (parser/checker scale work): heavy set 120/2 → 124/26 (2026-10-30)

A1's three scale commits (`ab79660` checker chunk streaming, `bff9dad`
UTF-8 inputs, `ae91bdc` parser flattening) landed after their last
green head. The report lane's baseline sits at `bff9dad` (276/3) —
**`ae91bdc` is unbaselined by anyone; this is the first measurement.**

## Heavy set at `ae91bdc` (clean detached, sequential, `-v`)

| metric | `46bf1c0` (old) | **`ae91bdc`** |
|---|---|---|
| tests | 120 (a13 87 + nested 13 + a14 11 + cli 8 + classifier 1) | 124 (**a13 91** — 4 added, 0 removed) |
| failures | **2** (known a14 pair) | **26** — 19 a13 + 3 nested + 2 a14 new |

## Failure modes (measured)

1. **a13 + a13_nested (22 failures): budget-class migration.**
   Dominant code **`PEP_RUNTIME_CALL_DEPTH` (21 hits)** where tests
   assert `PEP_RUNTIME_STEP_LIMIT` (3 hits) — e.g.
   `AssertionError: 'PEP_RUNTIME_CALL_DEPTH' != 'PEP_RUNTIME_STEP_LIMIT'`.
   All failing names are PRE-EXISTING deep-nesting tests
   (`test_deep_nested_list_*`, `test_four_level_append_*`,
   `test_deep_builtin_list_declaration_*`, …) that passed at
   `46bf1c0`. The parser-flattening work evidently deepens host
   recursion so call depth (128) now binds **before** the step budget
   on deep programs.
2. **a14 2 → 4 — Wall B crosses onto A1's own line.** New:
   `test_generated_c23_executes_source_backed…` and
   `test_recursive_native_calls_enforce_pep_depth` fail with emit-stage
   **`PEP_RUNTIME_STEP_LIMIT`** at tool_invoke — with A1's own
   (unchanged, `9573c227`) emitter. The countdown all-in-one path
   lost its remaining headroom to the parser/checker changes. The two
   known failures (length exemplar `'emitted' != 'unsupported'`,
   recursion wording) are unchanged.

## What is NOT broken

- The 4 added tests (`test_large_valid_utf8_source…`,
  `test_open_source_target_checks_revision_against_original_bytes`,
  `test_small_source_bytes_remain_opaque…`,
  `test_staged_functions_resolve_forward_nominal_return_across_chunks`)
  are the scale work's new coverage and are **not** in the failure set.
- cli 8/8 and classifier 1/1 passed within the heavy run.

## Assessment

The scale direction (parsing Lucy-scale sources) is the mission's
critical path, but `ae91bdc` trades one budget axis for another:
step-limit assertions across the deep suite now die at the depth axis,
and the a14 all-in-one path regresses on A1-own. Either the flattening
recursion needs bounding (depth-safe iteration), or the deep-suite
expectations and a14 contract move with the new budget shape — the
latter is the Wall B decision already on the table, now with A1-own
green-ness at stake (their line was the green reference at 272/3).

Builder-owned either way; reported before further stacking.
Replay **163/163**; corpus/base untouched.
