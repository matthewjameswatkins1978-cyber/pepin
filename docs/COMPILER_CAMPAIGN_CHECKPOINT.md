# Pepin Compiler Campaign Checkpoint

**Date:** 2026-10-28
**Repository:** `matthewjameswatkins1978-cyber/pepin`
**Branch / verified code SHA:** `campaign/pep-v01-sustained-build-20261027` / `cf764d9888c4175b2126ae1bdaad16ab4ac098b5` (remote-equal; test-only commit after checker SHA below)
**Verification test head:** `cf764d9888c4175b2126ae1bdaad16ab4ac098b5` (remote-equal)

## Strategic development roads (planning only, 28 October 2026)

Read [roadmap index](roadmaps/ROADMAP-INDEX.md) for (1) reproducible Lucy self-hosting, (2) whole accepted Pepin 1.0, and (3) the feature/evidence ledger. These are planning documents, not current implementation/test claims or accepted phase/status changes. Maintain this checkpoint as time- and SHA-bound evidence; do not rewrite historical receipts. Both current agents keep their declared code ownership and continue through nonblocking three-slice reviews.

## Baselines and authority

- Accepted A12 parser base: `69a47fe77187666bdd045b8dc8a9f633a7dd49d7`.
- A13 review baseline: `7647ec4b6dc875745d883d82db25390b20c1c616`; PR #12 remains a separate draft review line. Lucy's review holds any claim that A13 `valid` is a complete semantic certificate.
- The campaign branch is the single active implementation line. No merge, `master`, release, `CURRENT.md`, or manifest update is authorized.
- Production truth remains the OCaml 5.5.2 seed. The project switch is `pepin-5.5.2` through `PEPIN_OPAM_ROOT`; a plain default-root opam query can select another installation.

## Verified implementation and evidence

The isolated Pep-written A13 checker resolves lexical names and function calls; checks scalar expressions, two-level primitive lists, nominal record fields and record-valued union payloads; and retains named-record payload types in constructor-pattern bindings. It checks the implemented scalar-payload pattern subset, contextual match and if-expression result types, typed holes, wrong-union patterns, duplicate constructor arms, exhaustiveness and unreachable arms after wildcard/binding catch-alls. Empty lists require a supported contextual `List[T]` type or receive OCaml-matched `PEP_EMPTY_LIST_NEEDS_TYPE`. Built-in type names cannot be redeclared, and functions cannot reuse builtin or constructor names. Deeper recursive nominal/union graphs, nested constructor patterns, broader patterns, aggregate equality, assignment and `for-in` remain unsupported or unverified. Non-Unit return validity is reported only when the current bounded block/if analysis proves coverage. The checker does not replace the OCaml production checker.

At checker code SHA `3dcd88b47fc016f9649eb5b310ed14f7bf6f38d6`, tested with the committed test source at `0346120f93aab874587612b7f935d78db3d7ce67`, `python -m unittest tests.test_a13 tests.test_a13_nested_records -q` passed **33/33** in 79.143 seconds. This is 29 A13 checker tests plus four nested-record/list tests. Ten if-expression fixtures compare status, exact diagnostic codes/spans and typed-hole expectations with OCaml across returns, annotations, function arguments, list elements, record fields and branch mismatches. Four minimal record-field match-with-hole variants still return `PEP_RUNTIME_STEP_LIMIT`; the 100,000-step budget is unchanged. The earlier 32/32 attribution to the older `7533f4c` candidate is superseded: replaying that stale checker against newer nested-list mismatch cases exposed three expected failures, while the current `3dcd88b` checker passes the exact branch suite. The existing `_build/ocaml/pep.exe` provided the OCaml CLI oracle. No clean OCaml rebuild or full repository suite was run.

### Latest fail-closed differential follow-up

At checker/test SHA `3d6484a419de2dd82aa6ca7c9047ff0c769988eb`, `python -m unittest tests.test_a13 tests.test_a13_nested_records -q` passed **33/33** in 85.415 seconds. The strengthened gate compares exact diagnostic codes and byte spans with OCaml for wrong record fields, constructor payloads, if/while conditions, builtin arity and builtin argument types. It exposed an extra `PEP_LIST_UNTYPED` after `length()` already failed arity; Pep now skips list-specific validation for wrong-arity calls, matching OCaml's single `PEP_ARGUMENT_COUNT`. Statement-if and while holes match OCaml's `Bool` expectation and byte spans; candidate and visible IDs resolve to the scoped `Bool` parameter. The four record-field match-with-hole variants still hit the unchanged 100,000-step ceiling. This run predates the current uncommitted structural type-shape edits in `tests/pep_checker_a13.pep` and `tests/test_a13_nested_records.py`; those edits are not part of SHA `3d6484a` or its evidence. `git diff --check` passed; no clean OCaml rebuild or full repository run was performed.

## Remaining risks and next action

A13 remains partial and unaccepted. Recursive nominal/union relationships, nested constructor patterns, broader patterns, complete control-flow analysis and the checked-program contract remain unfinished. Four minimized record-field match-with-hole variants still hit the unchanged 100,000-step ceiling, so their hole facts remain unverified; do not increase the budget. The reviewed fail-closed gate remains required until each rule is independently implemented and differentially tested. Verification commit `3d6484a` was remote-equal when tested. The current checkout contains uncommitted structural type-shape edits in `tests/pep_checker_a13.pep` and `tests/test_a13_nested_records.py`; preserve and review them before relying on or extending that slice.

## Latest continuation state — 2026-10-28

The latest branch head is `cf764d9888c4175b2126ae1bdaad16ab4ac098b5`, a C23 CLI test-only commit after checker SHA `ca1f5a0cfdcc30178f5cf979fe7eab765d8a6c33` (`perf(checker): reuse function result shapes`). The A13 diagnostic integration `facc4a34f1e3d60d13a0d3a66abb995d3f610f87` is an ancestor; its list-return `PEP_TYPE_MISMATCH` correction remains present.

On checker SHA `ca1f5a0cfdcc30178f5cf979fe7eab765d8a6c33`, `python -m unittest tests.test_a13 tests.test_a13_nested_records tests.test_a14_c23.A14C23EmissionTests.test_native_bool_helpers_compose_with_direct_returns -q` ran **43 tests**: the A13 and nested-record/list suites passed **42/42**, while the added A14 case failed with `PEP_RUNTIME_STEP_LIMIT` at emitter position `3804:5`. At branch head `cf764d9`, `python -m unittest tests.test_c23_cli -q` passed **4/4** in 12.444 seconds, including GCC native CLI execution. No clean OCaml rebuild or full suite is implied.

A reduced resource probe found that A13 accepts `negate(negate(false))`, a direct call to either helper, and an unused extra helper, but the valid program `identity(negate(false))` with separate `identity` and `negate` helpers returns `PEP_RUNTIME_STEP_LIMIT` at checker bundle position `2766:15` on `0d88524`. After the `ca1f5a0` function-result-shape optimization, the same A14 case still exceeds the existing limit at emitter position `3804:5`. The 100,000-step budget is unchanged. Root cause is not yet established; repeated `lookup_node` scans during type inference are a concrete candidate, not a measured attribution.

The main checkout has one uncommitted C23 regression test in `tests/test_a14_c23.py`; preserve it. `tests/test_c23_cli.py` was committed at `cf764d9` and passed 4/4. An earlier A14 suite run at pre-optimization base `fe1b24d` passed 11 tests and failed the nested-helper case with the same `PEP_RUNTIME_STEP_LIMIT`, so the failure predates the latest optimization and is not evidence of a new regression.

Next action: profile/reduce the A13 two-distinct-helper nested-call case on a stable snapshot, identify repeated work, and optimize a narrow checker path without changing semantics or budgets. Then rerun the exact reproducer and A13/nested-record regression suites. A13 remains experimental and unaccepted; no merge, master, `CURRENT.md` or manifest advancement.


## Continuation 03 — nested helper resource repair (2026-10-28)

This update supersedes the prior checkpoint's unprofiled root-cause hypothesis. The campaign branch advanced to `ec3782964629860ad0d6a24c7b007113aac2119e` while work was isolated. That commit changes `token_at` to return on the requested token rather than scanning the rest of the token list, and adds the exact nested Boolean A13 budget regression. The local implementation was rebased onto that commit before verification.

Implementation and test commit: `ab1f7f01d9511c9b49f1a55a37c775a73152fb0b`. The CLI test source `tests/test_c23_cli.py` has blob SHA-1 `a7d0b449f2771326bf5e40f7c485795b27ceb994`; the resource probe used the exact nested source SHA-256 `58c3734651c51667eb2d304ed9cdc4d08760bb11321fb2c547d0f8ae3ba3d175` (167 UTF-8 bytes). The measured compiler bundle SHA-256 was `c7d2270b726e9eb44eb76e660da632f03e54b1b70c75b74702adccfd97265ad8`.

### Resource evidence and decision

On the same nested-helper program after the parser lookup change, test-only OCaml step instrumentation recorded parser-only `59,964`, checker-only `32,803`, and the A13 combined parse/check path `98,613` steps. The prior parser-only measurement was `65,877`, a reduction of `5,913` steps. The combined A13 path now completes, but has only `1,387` steps of headroom. The monolithic A14 `emit_c23` path still reaches the unchanged `100,001` sentinel. These measurements identify accumulated parser, checker and emitter execution as the boundary; `lookup_node` scans are present but are not alone the cause.

The native CLI now passes the exact typed `ParserProgress` result into `analyze_parsed`, then passes that same parse value and the checker's exact `CheckerReport` into `emit_c23_checked`. The three isolated Pep invocations measured `59,962`, `32,800` and `19,015` steps, respectively, each under the unchanged `100,000` per-invocation ceiling. The Python driver only relays stage results; parsing, semantic checking and C23 emission remain Pep-authored. No token-by-token host round trips, hidden host lexer/checker, budget increase or protocol schema change was introduced. The older one-shot `emit_c23` entrypoint remains available and can still exceed the budget on this case; CLI compilation uses the bounded staged path.

### Verification at implementation SHA

- `python -m unittest discover -s tests -v`: **174/174 passed** in 315.410 seconds. This full-discovery count includes the 11 historical MoonBit tests; those are included once in 174.
- A13 nested-helper regression: passed in full discovery; the source is now parsed and checked under budget on the updated campaign branch.
- A14/C23 and actual `run-c23` coverage: passed in full discovery. The new native regression compares interpreter output with C23 execution under both installed Clang and GCC; both return `42`.
- Fresh OCaml 5.5.2 `ocamlopt` compile and `describe --json`: passed; the report still declares `maxSteps=100000`.
- `python -m py_compile pep_c23.py tests/test_c23_cli.py`: passed. `git diff --check`: passed before the checkpoint append.
- Test-only profile run emitted all 52/52 expected profile records. It is instrumentation evidence, not an isolated CPU or memory benchmark.

### Boundaries and next work

A13 remains experimental and unaccepted. The exact A13 combined nested case is close to the budget, larger variants such as a nested relay and two-argument helpers still reach the runtime step limit, and the monolithic A14 tool path can still fail where its individual stages pass. The practical improvement is limited to the staged native CLI route and the measured A13 case; no broad large-program guarantee is established. There are no new semantics, `CURRENT.md` or manifest changes, merges, or master updates. The main checkout's unrelated uncommitted A14 test remains untouched.

## Continuation 03 — mutable assignment typing (2026-10-28)

**Implementation and test SHA:** `cc6a6d8916b35d66f892017e95b6c65a3f4d106e` (pushed to the campaign branch). The A13 checker now resolves assignment targets through the existing lexical binding and semantic identity tables. It accepts type-correct writes to `var`, rejects writes to `let` bindings and parameters as `PEP_ASSIGN_IMMUTABLE`, reports unresolved targets as `PEP_UNKNOWN_VARIABLE`, and checks RHS type names and structural shapes. Nested-list mismatches point at the offending leaf. Assignment context supplies expected types to empty lists and holes. `for-in` remains fail-closed as unsupported.

Verification at the exact implementation/test SHA: `python -m unittest tests.test_a13 tests.test_a13_nested_records -v` passed **44/44** in 112.651 seconds; the assignment differential test compares 10 scenarios against OCaml, including byte spans and diagnostic precedence. `python -m py_compile tests/test_a13.py` and `git diff --check` passed. The full repository suite was not rerun for this checker slice. The 100,000-step budget and `CURRENT.md`/manifest are unchanged.

Limitations: assignment checking covers variable targets and the currently represented structural type subset; `for-in`, complete missing-return analysis and broad flow-sensitive semantics remain unsupported. A13 remains experimental and unaccepted. No master merge or release action occurred. The main checkout's unrelated A14 edit remains untouched.

Next slice: after rereading the coordination outboxes, implement the smallest OCaml-matched `for-in` type-checking rule, preserving lexical loop-binding scope and fail-closed behavior for any unimplemented body or flow semantics.

## Continuation 03 — for-in iterable and binding typing (2026-10-28)

**Implementation and test SHA:** `e336970cb3f1e734b5d26283c2a31c06f5fbeef1` (pushed to the sustained campaign branch; the checkpoint is a following documentation commit). A13 now derives for-in binding types from the iterable's structural list shape, including nested lists and nominal elements, and checks that a known iterable is a list. The loop binding remains immutable and scoped to the loop body. A scalar iterable yields OCaml-matched `PEP_FOR_REQUIRES_LIST` at the iterable byte span. An untyped empty list retains `PEP_EMPTY_LIST_NEEDS_TYPE`; unknown names remain invalid under the existing `PEP_UNKNOWN_BINDING` diagnostic, which differs from OCaml's `PEP_UNKNOWN_VARIABLE` and was not changed by this slice.

The OCaml differential covers seven cases: list literal, typed list, `List[Point]` element and field access, nested-list element, scalar iterable, untyped empty iterable, and assignment to the immutable loop binding. It compares status and exact diagnostic code/byte span; valid cases assert the loop binding type, immutable flag, separate scope and body-reference identity. A separate A14 guard verifies a valid for-in input is still rejected as unsupported and produces no generated C.

Verification at implementation/test SHA `e336970cb3f1e734b5d26283c2a31c06f5fbeef1`:

- `python -m unittest tests.test_a13 tests.test_a13_nested_records -v`: **45/45 passed** in 118.637 seconds.
- `python -m unittest tests.test_a14_c23 -v`: **11/11 passed** in 60.841 seconds, including the no-C-output for-in guard.
- The added for-in differential method and A14 unsupported guard each also passed in focused runs.
- `python -m py_compile tests/test_a13.py tests/test_a14_c23.py` and `git diff --check` passed.
- No runtime budget, OCaml implementation, protocol, `CURRENT.md`, manifest, master or release changes. The full repository suite and clean OCaml rebuild were not repeated.

Limitations: this adds for-in element typing and list validation only. It does not establish complete loop/control-flow semantics, count a loop as proving function return completeness, or add A14 for-in lowering. A13 remains experimental and unaccepted. The main checkout's unrelated uncommitted A14 test remains preserved; this worktree is isolated.

The diagnostic-name follow-up is recorded below; no A13 acceptance or milestone pointer change.

## Continuation 03 — unknown expression diagnostics (2026-10-28)

**Implementation and test SHA:** `f73130b50c56730e38b2824931d88f81f6061000` (pushed to the campaign branch). Unresolved expression names now report OCaml's `PEP_UNKNOWN_VARIABLE` code/message, matching the existing unresolved assignment-target diagnostic. This also makes names referenced outside for-in and match-arm scopes report the reference diagnostic. No name-resolution behavior changed for successfully resolved bindings; their semantic IDs remain unchanged.

The differential regression compares status, diagnostic code and original byte span against OCaml for three cases: a missing ordinary local, a for-in binding used after the loop, and a match-arm binding used after the match. Tests assert exactly one `PEP_UNKNOWN_VARIABLE` each.

Verification at implementation/test SHA `f73130b50c56730e38b2824931d88f81f6061000`:

- `python -m unittest tests.test_a13 tests.test_a13_nested_records -v`: **45/45 passed** in 121.296 seconds.
- `python -m unittest tests.test_a14_c23.A14C23EmissionTests.test_checker_invalid_program_is_not_emitted -v`: **1/1 passed**.
- `python -m py_compile tests/test_a13.py` and `git diff --check` passed.
- Full repository discovery, full A14 suite and clean OCaml rebuild were not repeated for this diagnostic-only change. Runtime budget, protocol, `CURRENT.md`, manifest, master and release remain unchanged.

Limitations: A13 remains a partial experimental checker. Existing expression-type and fail-closed gaps are unchanged; this repair only aligns unresolved variable diagnostics. The full worktree is isolated and main checkout changes remain preserved.

## Continuation 03 — shallow nested constructor patterns (2026-10-28)

**Implementation and test SHA:** `47ddb970006e63c97744585dc8e5fccf63c749fe` (pushed to `campaign/pep-v01-sustained-build-20261027`). The A13 checker now accepts depth-one nested constructor patterns only when the nested payload pattern is exhaustive. A nested constructor counts toward outer-union coverage only when it selects the sole inner variant and its own payloads are irrefutable. For multi-variant payload unions, `O(I(value))` alone does not cover `O`; adding `O(_)` supplies the fallback. Wrong nested union and arity produce OCaml-matched `PEP_PATTERN_TYPE_MISMATCH` and `PEP_PATTERN_ARITY` spans. Patterns deeper than this bounded slice remain invalid with `PEP_PATTERN_UNSUPPORTED`; A13 binding inference still resolves the nested value to `Int` and its use to the same binding identity.

Verification:

- `python -m unittest tests.test_a13 tests.test_a13_nested_records -v`: **46/46 passed** in 132.196 seconds. This run covered the nested-pattern differential method and surrounding A13/list/record regressions.
- `python -m unittest tests.test_a13.A13FunctionResolutionTests.test_nested_constructor_patterns_fail_closed_beyond_supported_depth -v`: **1/1 passed** in 1.781 seconds; the OCaml reference accepts the complete deeper pattern while A13 reports the explicit unsupported boundary.
- `python -m unittest tests.test_a14_c23 -v`: **11/11 passed** in 65.073 seconds.
- `python -m py_compile tests/test_a13.py` and `git diff --check`: passed.

The runtime ceiling, OCaml seed, protocols, `CURRENT.md`, manifest, `master` and release state are unchanged. Full repository discovery and a clean OCaml rebuild were not repeated. A13 remains experimental and unaccepted.

Next: reread the coordination outboxes before selecting another bounded A13 checker slice; continue against OCaml differential cases and the unchanged runtime ceiling.

## Continuation 03 — missing-return diagnostic parity (2026-10-28)

**Implementation and test SHA:** `f10d5db3fe6eeac19565e4d8db0be19720878a29` (pushed to the sustained campaign branch). For non-Unit functions whose current bounded return-flow analysis cannot establish that every path returns, the A13 checker now emits OCaml's `PEP_MISSING_RETURN` diagnostic code. Existing flow recognition and invalid status are unchanged. Four differential fixtures compare exact status, code and original function byte span for empty-body, local-fallthrough, conditional-fallthrough and nested-block-fallthrough inputs. The Pep explanatory message remains static and is not claimed to match OCaml text exactly.

Verification on this implementation/test SHA: `python -m unittest tests.test_a13 tests.test_a13_nested_records -v` passed **48/48** in 134.407 seconds; `python -m unittest tests.test_a14_c23 -v` passed **11/11** in 62.832 seconds; Python compilation and `git diff --check` passed. Full discovery and a fresh clean OCaml rebuild were not repeated. The 100,000-step ceiling, protocols, `CURRENT.md`, manifest, `master` and release state are unchanged. A13 remains experimental; complete return-flow semantics are still unfinished.

## Continuation 03 — return mismatch diagnostic parity (2026-10-28)

**Implementation and test SHA:** `1952c5ebd67bb49846bee5ed9f56557eb53d001e` (pushed to the sustained campaign branch). A13 return-expression type mismatches now use OCaml's `PEP_TYPE_MISMATCH` diagnostic code, including scalar mismatches and a value returned from a `Unit` function. The existing mismatch-node selection remains: direct scalar expressions and conditional branches point at their mismatching expression, while list returns point at the offending list element. Four OCaml differential cases compare exact status, diagnostic code and original byte span for scalar, Unit-result, conditional-branch and list-leaf mismatches.

Verification on this implementation/test SHA: focused return/hole/list tests passed **4/4** in 9.111 seconds; `python -m unittest tests.test_a13 tests.test_a13_nested_records -v` passed **49/49** in 141.140 seconds; `python -m unittest tests.test_a14_c23 -v` passed **11/11** in 63.289 seconds; Python compilation and `git diff --check` passed. Full discovery and a fresh clean OCaml rebuild were not repeated. No runtime, protocol, `CURRENT.md`, manifest, `master` or release change. A13 remains experimental.

## Continuation 03 — constructor-pattern reachability parity (2026-10-28)

**Implementation/test SHA:** `4132c5e96b85e02d61bdff1c1ecb6a3812fd32b1`, pushed to `campaign/pep-v01-sustained-build-20261027`. During the existing payload validation traversal, the checker now tracks whether a constructor arm fully covers its variant and a compact constructor-pattern key. A repeated equivalent pattern reports `PEP_DUPLICATE_MATCH_ARM` over the complete arm span; a different pattern after the variant is fully covered reports `PEP_UNREACHABLE_MATCH_ARM` over the complete arm span, matching OCaml. This does not broaden supported nested-pattern depth or change the fixed 100,000-step budget.

Verification on the implementation/test SHA:

- Focused OCaml differential: **1/1 test passed**, covering four cases (nested then broad, broad then nested, duplicate nested and duplicate top-level constructor).
- `python -m unittest tests.test_a13 tests.test_a13_nested_records -q`: **50/50 passed** in 142.052 seconds.
- `python -m py_compile tests/test_a13.py` and `git diff --check`: passed.
- `python -m unittest tests.test_a14_c23 -q`: **9/11 passed; 2 failed**. The failures are the existing C23/reference runtime expectation cases for signed overflow (reference returned `23`) and division by zero (reference returned `42`); this checker-only slice did not alter A14. Do not count these as A13 regressions or claim A14 green.
- No full repository discovery or clean OCaml rebuild was run for this slice. `CURRENT.md`, manifest, runtime budget, master and release remain unchanged. A13 remains partial and unaccepted.

## Continuation 03 — partial nested constructor diagnostics (2026-10-28; cycle review 3/3)

**Implementation/test SHA:** `96734f8b05bb2c9ea941653cc34fc1c65915a59`, pushed to `campaign/pep-v01-sustained-build-20261027`. Well-formed bounded constructor patterns are now retained for exact duplicate detection even when they cover only one variant of a nested union; such partial patterns do not count as full outer-variant coverage. When an earlier pattern fully covers an outer variant, a later well-formed partial nested pattern is reported unreachable. Malformed type/arity/pattern forms remain ineligible for this tracking. The slice does not extend supported nesting depth or attempt general pattern-matrix exhaustiveness.

Verification on the implementation/test SHA:

- The focused OCaml reachability differential passed **1/1 test**, now covering six cases: nested then broad, broad then nested, duplicate full nested, duplicate partial nested, covered outer then partial nested, and duplicate top-level.
- `python -m unittest tests.test_a13 tests.test_a13_nested_records -q`: **50/50 passed** in 140.864 seconds.
- A14 emission-boundary regressions `test_unsupported_valid_program_is_reported_without_c_output` and `test_checker_invalid_program_is_not_emitted`: **2/2 passed**.
- Python compilation and `git diff --check`: passed. No clean OCaml rebuild or full repository discovery was run.

**Nonblocking 3/3 review:** the diff is confined to A13 pattern checking and its OCaml differential. The added eligibility guard avoids registering malformed or unsupported shapes; partial patterns are recorded without claiming outer coverage, and full coverage still drives unreachable-arm detection. No runtime-budget, protocol, A14, master, `CURRENT.md`, manifest, or release changes. A13 remains experimental and partial. Continue the campaign after refreshing peer coordination notes.

## Continuation 03 — staged record-match hole analysis (2026-10-28; cycle 1/3)

**Test SHA:** `779017b858948c74e3c5c536de7c12ca9fcb91e2`, pushed to `campaign/pep-v01-sustained-build-20261027`. Added a real JSONL integration regression for a record-field `match` containing a typed hole. The Pep-written parser is invoked as `parser_parse_program`; its revision-bound `ParserProgress` is passed to the already existing `analyze_parsed` checker entry point. The staged result matches the OCaml status/diagnostics and retains the `pending: Int` hole fact, source document and revision. The existing one-shot `analyze` entry point remains unchanged.

Verification on the test SHA:

- Focused staged-path integration test: **1/1 passed** in 1.818 seconds.
- `python -m unittest tests.test_a13 tests.test_a13_nested_records -q`: **51/51 passed** in 145.388 seconds.
- A14 emission-boundary tests (`test_unsupported_valid_program_is_reported_without_c_output`, `test_checker_invalid_program_is_not_emitted`): **2/2 passed**.
- Python compilation and `git diff --check`: passed. No full repository discovery or clean OCaml rebuild was run.

**Measured boundary:** manually invoking one-shot `analyze` on this exact source still returns `PEP_RUNTIME_STEP_LIMIT` (100,000-step ceiling; runtime message location `2971:6`). The staged parser and checker each complete under their existing per-call cap. This is evidence for the existing staged protocol path, not a fix to the one-shot analyzer or a general large-source guarantee. No budgets were changed; A13 remains experimental.

## Continuation 03 — nested constructor keys across payload positions (2026-10-28; cycle 2/3)

**Implementation/test SHA:** `f314513ad955cc5a507209220b7cfcbaa3b7886f`, pushed to `campaign/pep-v01-sustained-build-20261027`. A differential probe found that two-payload patterns which differ in a later nested constructor position were incorrectly reduced to `PEP_NON_EXHAUSTIVE_MATCH` when the same partial pattern repeated; OCaml reports `PEP_DUPLICATE_MATCH_ARM` at the repeated full arm span. The checker now records each top-level payload position and its supported shallow pattern shape in the duplicate key. Distinct partial patterns such as `O(_, I())` and `O(_, J())` still do not count as exhaustive, and unsupported deeper forms remain excluded. This repairs duplicate identity only; it does not add pattern-matrix coverage.

Verification on the implementation/test SHA:

- Staged JSONL differential regression: **1/1 test passed**, covering the existing typed-hole boundary, distinct later-payload partial patterns and exact duplicate later-payload diagnostics/spans against OCaml.
- `python -m unittest tests.test_a13 tests.test_a13_nested_records -q`: **51/51 passed** in 149.575 seconds.
- A14 emitter-boundary regressions: **2/2 passed**.
- `python -m py_compile tests/test_a13.py` and `git diff --check`: passed.
- Instrumented profile for the same 132-byte target fixture: Pep parser **54,158 steps**, staged checker **35,704 steps**, one-shot analyzer still **100,001 steps** and reports `PEP_RUNTIME_STEP_LIMIT` under the unchanged cap. Before this checker change, the same fixture's staged checker measured 35,700; the observed delta is four steps. This narrow profile is not an isolated CPU or memory measurement and does not establish large-file support.

No `CURRENT.md`, manifest, master, release, protocol or budget changes. A13 remains partial and unaccepted; cycle 2/3.

## Continuation 03 — all-payload duplicate-key regressions (2026-10-28; cycle review 3/3)

**Test SHA:** `8206d0e9df325a8bcd53437cfa4e9cef94775eba`; checker implementation remains `f314513ad955cc5a507209220b7cfcbaa3b7886f`. The staged OCaml differential now checks a third/later nested payload position, both exact duplicate and distinct partial patterns, and equivalence of an irrefutable binding pattern with a wildcard. OCaml and Pep agree on exact diagnostic codes and byte spans for each fixture. No implementation semantics changed in this test-only slice.

Verification on the test SHA: the focused staged JSONL test passed **1/1** (the method exercises six source fixtures plus the known one-shot cap case); `python -m py_compile tests/test_a13.py` and `git diff --check` passed. The full A13/nested-record suite **51/51** and A14 boundary tests **2/2** were run on implementation SHA `f314513`; those source files and compiler implementation are unchanged by this test-only commit, but the newly added three fixtures were not included in that full suite run. Profile evidence is inherited from `f314513` and remains valid because only the test file changed.

**Nonblocking 3/3 review:** the implementation key covers each top-level payload position with constructor identity, payload arity and normalized irrefutable shape; eligibility still excludes malformed/deeper unsupported patterns. Full constructor coverage remains separate from duplicate identity. The expanded tests challenge both false-duplicate and missed-duplicate directions against OCaml. No budget/protocol/C23/milestone changes. A13 remains partial, experimental and unaccepted; continue the campaign.

## Continuation 03 — recursive nested constructor patterns (2026-10-28; cycle 1/3)

**Implementation/test SHA:** `7224423b3f7d3367bf7a236c01eade474a25dda3`, pushed to `campaign/pep-v01-sustained-build-20261027`. The checker now recursively validates nested constructor payloads for constructor identity, expected payload type and arity. It computes full-coverage eligibility recursively, so partial nested-union patterns remain partial. Duplicate detection keeps the compact existing key for ordinary shallow shapes and falls back to recursive AST structure comparison when constructors exceed that key's depth; binding and wildcard remain equivalent. Staged JSONL checks match OCaml on valid depth-three patterns, distinct partials, exact duplicates and diagnostics. The one-shot analyzer can still hit the unchanged 100,000-step cap on the deep fixture; the staged parser/checker path completes. This extends the checker slice's demonstrated nesting depth, not pattern-matrix exhaustiveness or a general runtime guarantee.

Verification on the implementation/test SHA:

- Focused OCaml differential and budget-boundary regressions: **3/3 passed**.
- `python -m unittest tests.test_a13 tests.test_a13_nested_records -q`: **58/58 passed**.
- `python -m unittest tests.test_a14_c23 -q`: **11/11 passed**.
- `python -m unittest tests.test_c23_cli -q`: **5/5 passed**.
- `python -m py_compile tests/test_a13.py` and `git diff --check`: passed.
- No clean OCaml rebuild, historical MoonBit suite, full test discovery or new benchmark was run. Previous performance profiles are inherited evidence, not measurements of this recursive-pattern change.

No runtime budget, protocol, A14, master, `CURRENT.md`, manifest or release changes. A13 remains partial, experimental and unaccepted; cycle 1/3.

## Continuation 03 — unreachable-statement diagnostics across control-flow bodies (2026-10-28; cycle 2/3)

**Implementation/test SHA:** `b9c7507470a606ca8e6982db4579fa1f808b21e2`, pushed to `campaign/pep-v01-sustained-build-20261027`. The checker now matches OCaml's `PEP_UNREACHABLE` diagnostic and exact statement span after direct returns, nested returning blocks, two-branch returning `if` statements, and inside `while`/`for-in` bodies. A loop body return does not make the loop itself a guaranteed return. Four new source fixtures compare ordered diagnostic codes and byte spans against the OCaml CLI, including a malformed unreachable statement whose later type error must not replace the earlier unreachable diagnostic.

Verification on the implementation/test SHA:

- Focused unreachable and nested-pattern budget regressions: **2/2 passed**.
- Combined A13, nested-record/list, A14 C23 and C23 CLI suites: **75/75 passed** in 264.974 seconds. This includes the existing deep-pattern budget stress case that exposed an over-broad first implementation.
- `python -m py_compile tests/test_a13.py` and `git diff --check`: passed.
- The fixed 100,000-step ceiling is unchanged. An over-broad scan implementation exceeded it and was discarded; the committed checker checks only return-capable statements and their following sibling. No isolated timing or memory benchmark was run.

No clean OCaml rebuild, MoonBit suite, full repository discovery, protocol, A14 implementation, master, `CURRENT.md`, manifest or release changes. A13 remains partial, experimental and unaccepted; cycle 2/3.

## Continuation 03 — fixed-budget multi-call boundary probe (2026-10-28; cycle 3/3)

**Test SHA:** `0706ef06b914340388a9937deaca7f52f88f8634`, pushed to `campaign/pep-v01-sustained-build-20261027`. Added an exact 200-byte four-caller A13 fixture and staged comparison. OCaml and the staged Pep checker agree on invalid status, ordered diagnostic identities and original byte spans. The one-shot analyzer reproducibly returns `PEP_RUNTIME_STEP_LIMIT`; a four-caller correctly typed one-shot control reaches the same ceiling, while its staged checker result is valid and a staged typed-hole control remains incomplete with expected type `Bool`. No checker implementation or budget change was made because the measurements do not isolate a safe optimization target.

Measurements on the same persistent JSONL session, with the A13 tools registered and five consecutive invocations per case (no discarded warmup), using end-to-end `JsonLineClient.send` wall time:

- 160-byte, three-mismatch one-shot: **5/5 succeeded**, median **3.565 ms**.
- 200-byte, four-mismatch one-shot: **5/5 hit `PEP_RUNTIME_STEP_LIMIT`**, median **3.077 ms**; error position `2879:238`.
- 200-byte four-mismatch staged parser: median **3.833 ms**; staged checker: median **2.344 ms**. All five parser/checker calls succeeded and the checker matched OCaml diagnostics.
- The four-call typed one-shot control also hit the fixed limit (observed position `4092:31`).

These host-visible timings include request/response and JSONL work; they are not interpreter-only CPU, step-distribution or memory measurements. The one-shot error position identifies where the counter expired, not the root cause. Parser-plus-checker composition exceeds the one-shot budget for this source while each staged operation succeeds; no claim is made about a single dominant internal traversal.

Verification:

- Focused four-call differential/budget test: **1/1 passed** on test SHA `0706ef0`.
- A13 plus nested-record/list: **60/60 passed** in 190.743 seconds immediately before final test-only cleanup (dead fallback removal and the 200-byte fixture-size assertion); final test method passed again **1/1** after those edits.
- A14 C23 **11/11** and C23 CLI **5/5** were previously verified on unchanged checker/compiler sources at `b9c7507`.
- Final `py_compile` and `git diff --check` passed. No clean standalone OCaml rebuild, historical MoonBit run or full repository discovery.

**Nonblocking 3/3 review:** the cross-stage result and capacity edge are now reproducible, the typed control rules out mismatch-diagnostic complexity as the sole explanation, and the staged hole case preserves semantic facts. Runtime output gives no phase step counts; internal attribution remains unresolved, so this test-only slice makes no speculative checker optimization. The 100,000-step ceiling is unchanged. Agent 2's native/runtime work remains separate. A13 remains partial, experimental and unaccepted; continue the campaign.

## Continuation 03 — deep structural list parity and literal-append budget edge (2026-10-28; cycle 1/3)

**Test SHA:** `76562097dd5b1b020e893fcca9eb003e35e2c1de`; checker source remains unchanged from `b9c7507470a606ca8e6982db4579fa1f808b21e2`. Added differential coverage for three- and four-level list signatures, return-context literals, reverse, append, nested call arguments, and exact leaf mismatch spans. The direct four-level append(value, item) control passes when the element is a typed name; append(value, [item]) also passes when item has depth two and the resulting list element has depth three.

Two OCaml-valid sources that pass a depth-three list literal as the depth-four collection's append element—append(value, [[[1]]]) and append(value, [[item]]) with item: List[Int]—hit the unchanged PEP_RUNTIME_STEP_LIMIT in the Pep checker. Tests record this fixed-budget boundary explicitly; they do not increase the budget or claim Pep/OCaml parity for those capped invocations. This narrows the observed boundary to list-literal elements of that nested depth, not all depth-four signatures or list operations. Runtime failure positions vary and are not treated as root-cause attribution; no isolated CPU/step-distribution or memory measurements were collected.

Verification on this slice before its commit:

- Deep structural-list differential and fixed-budget characterization: 6/6 tests passed; valid controls, exact mismatch diagnostics and the two explicit step-limit cases are separated.
- python -m py_compile tests/test_a13.py and git diff --check: passed.
- No checker implementation, budget, protocol, A14, master, CURRENT.md, manifest or release changes.

A13 remains partial, experimental and unaccepted; continue the campaign.

## Continuation 03 — staged deep-append parity and profile-guided budget investigation (2026-10-28; cycle 1/3)

**Test SHA:** `6f0718e75d2f5607bcfb4cadce13bd39488c9466`, pushed to `campaign/pep-v01-sustained-build-20261027`. Extended the two four-level append budget-boundary regressions to run the Pep-written parser and staged checker on the same authorised revision before asserting the one-shot limit. Both staged reports are valid and match OCaml status and exact diagnostics/spans; the one-shot `analyze` calls still return `PEP_RUNTIME_STEP_LIMIT`. No checker source or protocol change is in the committed slice.

Verification on the test SHA:

- `python -m unittest tests.test_a13 tests.test_a13_nested_records -q`: **66/66 passed** in 209.544 seconds.
- The five directly affected reachability, nested-list, helper-budget and staged append cases passed **5/5** in 13.627 seconds after restoring the published checker source.
- `python -m py_compile tests/test_a13.py` and `git diff --check`: passed.

A temporary, stderr-only `execute` tick profile was used and then removed; `pep_ocaml.ml` was restored byte-for-byte to the checkpoint source. For the 107-byte nested-literal append source, one-shot execution stopped at **100,001 ticks**. The successful 133-byte typed-name control used **88,546 ticks**. In the literal failure profile, the largest grouped Pep-function tick counts were `lexer_step` 21,725; `lookup_node` 10,606; `infer_expression_type` 4,609; `contextual_expected_type` 3,706; `child_at` 3,676; and `expression_type_shape` 2,444. These are interpreter tick counts grouped by active Pep function, not isolated CPU time or memory measurements.

A sorted-node early-stop and builtin constructor-scan fast path were tried locally. The constructor helper's grouped ticks fell from 2,187 to 215 in the same cap probe, but the source still hit the fixed limit and the trial introduced four new step-limit failures in the A13 suite. Both implementation edits were discarded. The final checker implementation remains unchanged; the useful result is staged parity coverage and a clearer profile of the unresolved one-shot cost.

The 100,000-step ceiling, master, `CURRENT.md`, manifest, A14/C23 ownership and release state remain unchanged. No large-file, CPU or memory guarantee is claimed. A13 remains partial, experimental and unaccepted; cycle 1/3.

## Continuation 03 — unknown for-in iterable diagnostic parity (2026-10-28; cycle 2/3)

**Test SHA:** `a89701988005ce316f86182f06dc1e378ea72883`, pushed to `campaign/pep-v01-sustained-build-20261027`. Added an unknown iterable case to the existing for-in differential. For `fn main() -> Int { for item in missing {} return 0 }`, the current Pep checker and OCaml both report invalid status with `PEP_UNKNOWN_VARIABLE` over bytes 31–38. This supersedes the older SHA-bound note above that recorded a `PEP_UNKNOWN_BINDING` discrepancy; current checker source already emits the matching code, so this slice changes tests only.

Verification: `python -m unittest tests.test_a13.A13FunctionResolutionTests.test_for_in_item_types_scope_and_list_requirement_match_ocaml -v` passed **1/1 test method**, covering eight iterable, scope, type, and diagnostic fixtures. `python -m py_compile tests/test_a13.py` and `git diff --check` passed. The prior full A13/nested-record suite remains evidence for the unchanged checker at test SHA `6f0718e`; full discovery was not repeated for this one-case test-only change.

No checker implementation, budget, protocol, master, `CURRENT.md`, manifest, A14 or release change. A13 remains partial, experimental and unaccepted; cycle 2/3.

## Continuation 03 — for-in scope and shadowing parity (2026-10-28; cycle 3/3)

**Test SHA:** `e611fdef6f4795f0e186badc844bbc22e3382cd9`, pushed to `campaign/pep-v01-sustained-build-20261027`. Added dedicated OCaml differential cases proving a loop binding is unavailable while resolving its own iterable and does not escape the loop, with exact `PEP_UNKNOWN_VARIABLE` byte spans. A valid shadowing case confirms the iterable reference resolves to the outer list binding while the loop-body reference resolves to the loop binding. No checker implementation changes.

Verification on the test SHA: the new scope method passed **1/1**; the existing for-in type/diagnostic method passed **1/1** (eight fixtures). `python -m py_compile tests/test_a13.py` and `git diff --check` passed. Full A13/nested-record suite was not rerun for this test-only slice; its last **66/66** result remains tied to test SHA `6f0718e`, with unchanged checker source.

**Nonblocking 3/3 review:** this closes the reported loop name-resolution boundary with status, spans and binding identity evidence. It does not indicate a checker defect, change the runtime ceiling, or advance A13 acceptance. Next work should target a distinct semantic parity gap or a measured checker bottleneck, keeping full-suite evidence tied to its exact source SHA. Master, `CURRENT.md`, manifest, A14 ownership, budgets and release state remain unchanged.

## Continuation 03 — four-call runtime-step attribution (2026-10-28; cycle 1/3)

**Profile source SHA:** `43c75945e3cf8097c3f26622f6a3fda7167622c9`; checker/test behavior unchanged from the published campaign head. Temporary OCaml `execute` instrumentation counted existing `tick` events by active Pep function; it did not add or remove runtime ticks and was restored byte-for-byte afterward (`pep_ocaml.ml` Git blob `c92f9cc4a36bcfe7597f7286d3b8da42f24ec0ef`). The exact `test_four_independent_call_errors_preserve_fixed_budget_boundary` passed **1/1** with profiling enabled and again **1/1** after restoration.

For the four independent mismatches, separate staged execution used **74,132 parser ticks** and **39,085 checker ticks**; together that is **113,217**, above the unchanged 100,000 cap. One-shot `analyze` stopped at **100,001**. The typed control likewise used **76,626 parser + 38,513 checker ticks = 115,139** staged and its one-shot call hit the cap. The typed-hole staged control used **30,550 parser + 13,993 checker ticks** and passed; its one-shot path was not part of this fixture. Thus the failure is consistent with the combined parser/checker budget, not a mismatch-only diagnostic path. The largest measured checker functions on the bad staged case were `type_analysis` 8,345 ticks, `child_at` 4,644, `type_shape_at` 3,288 and `lookup_node` 2,448; parser `lexer_step` alone accounted for 36,721 of 74,132 parser ticks. These counts are specific to this 200-byte fixture and are not CPU or memory measurements.

Uninstrumented warm-session JSONL observations from the same test: bad parser request/response **245/20,870 bytes, 3.786 ms**; staged checker **20,919/11,536 bytes, 3.285 ms**; failing one-shot **246/248 bytes, 3.626 ms**. Typed-control parser/checker round trips were **4.397/2.152 ms**; the one-shot limit response took **3.355 ms**. These are single warm-call observations, not medians or isolated execution times. Small requests and millisecond responses make transport an unlikely cause for this fixture; the interpreter-step ceiling is decisive. Full A13+nested suite was not repeated for this profile-only slice; no checker source, cap, protocol, `CURRENT.md`, manifest, master or A14 ownership changed. A13 remains partial and unaccepted; continue.

## Continuation 03 — list return-span and nested append contextual parity (2026-10-28; cycle 2/3)

**Implementation/test SHA:** `8896ea71be97e9857c2f05b7ec735b60a2ae476c`, pushed to `campaign/pep-v01-sustained-build-20261027`. The Pep checker now locates the offending list leaf when an `if` expression's contextual list return branch has the wrong element type. It also matches OCaml's contextual acceptance of an extra nested list literal in `append`, using a recursive list-depth predicate composed from existing shape helpers. The exception is explicitly limited to `append` and requires a list literal, inferred type text equal to the expected element type, and strictly greater actual list depth. Exact-depth mismatches remain rejected. Regression cases compare OCaml status, diagnostic codes and byte spans for the offending conditional leaf and append controls.

The OCaml reference accepts `append(xs, [[true]])` for `xs: List[List[Int]]` in this return context, as well as the integer control; the Pep checker now does too. This records reference parity, not a new guarantee that the OCaml behavior is structurally sound. The exact-depth `append(xs, [true])` remains invalid and matches the reference diagnostic. No runtime execution safety or backend support is implied by static acceptance.

Verification on this implementation/test SHA:

- Focused return-span, contextual append, deep list mismatch and four-level append checks: **4/4 passed**.
- `python -m unittest tests.test_a13 tests.test_a13_nested_records -q`: **68/68 passed** in **214.006 seconds**.
- `python -m py_compile tests/test_a13.py` and `git diff --check`: passed.
- No full repository discovery, clean standalone OCaml rebuild, MoonBit suite, A14/C23 suite or new performance measurement was run. The immediately preceding staged profiling remains valid for its recorded source SHA; this checker behavior change has not been separately profiled.

No runtime budget, protocol, A14 implementation, master, `CURRENT.md`, manifest or release change. A13 remains partial, experimental and unaccepted; cycle 2/3.

## Continuation 03 — contextual nested-list branch mismatch diagnostics (2026-10-28; cycle 3/3)

**Implementation/test SHA:** `c3adf5da8a9ce503d46367afe696a46194099480`, pushed to `campaign/pep-v01-sustained-build-20261027`. Found and fixed a contextual inference hole in `if` return checking: nested list literals could be assigned the expected outer type while a wrong leaf such as `true` remained unchecked. The checker now asks the existing structural list-leaf helper for direct list-literal branches before trusting their contextual type, reports the first offending branch/leaf in source order, and retains the whole-branch fallback for ordinary type mismatches. Tests cover wrong leaves in both then and else positions with exact OCaml code and byte spans (then: **57–61**, else: **72–76** on the two-level fixtures).

**Nonblocking independent 3/3 review:** no semantic or diagnostic-order blocker. Review flagged unnecessary branch traversals under the fixed step ceiling. Follow-up narrows leaf scans to direct list-literal branches and skips the else scan after a then-side mismatch. The full suite was rerun after this guard. The structural helper's tick savings were not instrumented separately, so no performance improvement figure is claimed.

Verification on the final implementation/test SHA:

- Focused return mismatch differential: **1/1 test method passed** after the review guard.
- `python -m unittest tests.test_a13 tests.test_a13_nested_records -q`: **68/68 passed** in **222.601 seconds**.
- `python -m py_compile tests/test_a13.py` and `git diff --check`: passed.
- No C23/A14 suite, historical MoonBit suite, clean OCaml build, full repository discovery or new benchmark was run.

No runtime-budget, protocol, A14 implementation, master, `CURRENT.md`, manifest or release change. A13 remains partial, experimental and unaccepted; the review cycle is complete and work continues.

## Continuation 03 — contextual constructor nested-list parity (2026-10-28; cycle 1/3)

**Implementation/test SHA:** `6c765f25dadc859932984fc7ab602dd5bbfd93b9`, pushed to `campaign/pep-v01-sustained-build-20261027` and verified remote-equal. A union constructor payload declared as `List[NamedRecord]` was checked through a legacy type-name conversion that cannot represent named list elements; a list containing a different record type could therefore be accepted. The checker now obtains the expected `PepTypeShape` directly from the variant payload type AST and applies the existing nested-list mismatch locator. The fix is limited to constructor payload diagnostics and does not broaden general collection support.

OCaml differential cases cover scalar and nested primitive mismatches, valid nested lists, and wrong nominal record elements. `python -m unittest tests.test_a13 tests.test_a13_nested_records -q`: **69/69 passed** in **268.593 seconds**. Focused constructor/union/nested-record selection: **3/3 test methods**. `python -m py_compile tests/test_a13.py` and `git diff --check`: passed. No isolated performance measurement; the fixed 100,000-step budget is unchanged.

Peer notes at this checkpoint: Agent 2's collection bindings and Lucy's next-slice direction concern C23 emitter/stdlib ownership and do not overlap checker files. A13 remains partial and unaccepted. No master, A14, `CURRENT.md`, manifest, budget or release change.

## Continuation 03 — constructor variable payload shape parity (2026-10-28; cycle 2/3)

**Implementation/test SHA:** `d7f4babc6a1197b021bd8a1b25595b30a6c3db16`, pushed to `campaign/pep-v01-sustained-build-20261027` and verified remote-equal. The previous constructor correction covered literal payload lists; this follow-up handles typed nonliteral payloads. A `Wrap` constructor expecting `List[P]` could accept a `List[Q]` variable because the legacy string-name conversion has no representation for named-record lists. The checker now compares the declared and actual AST-derived `PepTypeShape` when available, while retaining the exact leaf locator for list literals. Regression cases cover wrong and matching nominal list variables.

The focused constructor differential passed **1/1 method** across primitive, nested and nominal literal/variable cases, including exact OCaml diagnostics and spans. `python -m unittest tests.test_a13 tests.test_a13_nested_records -q`: **69/69 passed** in **228.821 seconds**. `python -m py_compile tests/test_a13.py` and `git diff --check`: passed. No performance measurement; 100,000-step budget unchanged.

Agent 2's latest outbox reports separate C23 collection-binding work and Lucy's direction remains on emitter profiling; no checker-file overlap. A13 remains partial and unaccepted. No master, A14, `CURRENT.md`, manifest, budget or release change.

## Continuation 03 — contextual match list diagnostic spans (2026-10-28; cycle 3/3)

**Implementation/test SHA:** `af5ebfa9d7873ff73f5e0699cb29f031f65f0e16`, pushed to `campaign/pep-v01-sustained-build-20261027` and verified remote-equal. When a match expression returns a contextual `List[Int]`, an arm `[true]` was rejected by both Pep and OCaml, but Pep reported the entire list literal while OCaml points to the first incompatible leaf. List-literal match arms now reuse `list_mismatch_node` to select that leaf and preserve the existing `PEP_MATCH_ARM_TYPE_MISMATCH` code. Scalar arm handling remains on its prior path after an initial attempt caused an existing nested-pattern fixture to hit the fixed budget; the guard was narrowed and that boundary fixture now passes.

The new OCaml differential checks exact status, code and byte spans for a mismatched leaf and a valid control. Focused match-span plus formerly failing nested-pattern tests passed **2/2**. `python -m unittest tests.test_a13 tests.test_a13_nested_records -q`: **70/70 passed** in **230.398 seconds**. `python -m py_compile tests/test_a13.py` and `git diff --check`: passed. No isolated performance measurement; the 100,000-step ceiling is unchanged.

**Nonblocking 3/3 review:** independent read-only review found no correctness or diagnostic-order blocker. The shared mismatch flag preserves source-order reporting and exact OCaml spans. It flagged that valid list-valued match arms each scan structural nodes; many arms or large literals may approach the fixed step ceiling. The current 70/70 corpus passes, but this is not a general size bound; no traversal savings were measured. A13 remains partial and unaccepted; no master, A14, `CURRENT.md`, manifest, budget or release change.

## Continuation 03 — deduplicate contextual match-list diagnostics (2026-10-28; cycle 1/3)

**Implementation/test SHA:** `a3796fb5f58ab92083bea2bdaa2a2a1bd06b573a`, pushed to `campaign/pep-v01-sustained-build-20261027` and verified remote-equal. A heterogeneous list arm such as `[1, true]` produced the correct OCaml-matching `PEP_MATCH_ARM_TYPE_MISMATCH` at `true`, but also leaked a generic `PEP_TYPE_MISMATCH` at the same span from list validation. Diagnostic selection now suppresses a generic type mismatch only when a match-arm-specific diagnostic already exists at the identical byte span. Added the heterogeneous arm to the OCaml differential matrix.

Focused match-list, constructor payload, and nested-list cases passed **3/3 methods**. `python -m unittest tests.test_a13 tests.test_a13_nested_records -q`: **70/70 passed** in **230.856 seconds**. Python compilation and `git diff --check` passed. No performance measurement; runtime budget unchanged.

A13 remains partial and unaccepted. No master, A14, `CURRENT.md`, manifest, budget or release change.
