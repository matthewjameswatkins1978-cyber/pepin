# Pepin Independent Qualification Receipt: Native C23 Memory & UTF-8 Integration Candidate

- **Mission ID:** `PEP-NATIVE-REVIEW-20261122-01`
- **Candidate Branch / Pinned SHA:** `codex/pepin-native-utf8-integration-20261121@5cb0fbf065f096b3826f961e4b475ab1c1f2b589`
- **Review Branch:** `review/antigravity-native-5cb0fbf`
- **Reviewing Agent:** Antigravity (Independent Inspector)
- **Review Date:** 2026-11-22
- **Verdict:** **PARTIAL** (Native memory, GC, call depth, and UTF-8 runtime pass all 63 unit/stress tests; rejected for direct acceptance due to 4 identified lowering defects resolved in PR #29)

---

## 1. Executive Summary & Recommendation

Candidate `5cb0fbf` represents the combined native runtime, shadow-frame rooting, nonmoving heap GC, stack/direct allocation optimizations, call-depth trap, and verified UTF-8 slice integration.

1. **Native Memory & GC Qualification (PASSED):** The core memory management changes—precise nonmoving shadow frame registration (`pep_heap_frame`), expression-level temporary retirement, lexical loop root clearing, nonescaping literal length elision, up to 32 scalar `for-in` stack snapshots, eager call-depth counting (512 limit), and allocator refusal handling—are verified and performant. All 63 native unit tests passed cleanly across Clang and GCC.
2. **Lowering & Compiler Authority (FAILED on 5cb0fbf, RESOLVED in PR #29):** Independent adversarial gating (`verification/lucy_native_lowering_gate.py`) revealed 30 failures and 7 errors on `5cb0fbf`:
   - Keyword identifier collisions on record field and union variant names.
   - `Unit` type lowering to C `void`, breaking variable bindings, function arguments, and struct members.
   - Driver authority bypass: `build_c23` does not enforce `check` exit status `code == 0` before emitting C.
   - Envelope validation: `C23Emitter` does not validate schemaVersion == 2 or typedTree structure.
3. **Recommendation:**
   - **Do NOT integrate `5cb0fbf` directly into master or the campaign baseline.**
   - **APPROVE integration of `5cb0fbf` with PR #29 (`9413dd55779da411298c1ee3db27f3ba4fb59196`) applied.** PR #29 retains all memory and UTF-8 invariants while converting all 30 gate failures into passes (13/13 PASS).

---

## 2. Test Environment & Execution Evidence

### Environment
- **OS:** Windows 11 Pro 64-bit (build 26100)
- **Shell:** PowerShell 7.5.4 (Core)
- **Python:** 3.15.0a4 (`pythoncore-3.15-64`)
- **Compilers:**
  - Clang 23.1.4 (Scoop LLVM)
  - GCC 16.2.0 (MinGW-w64)
- **Seed Authority:** OCaml 5.5.2 (`pep_ocaml.ml` via `pep.ps1`)
- **Safety Constraints Honored:** Issue #22 exclusions preserved (quarantined Clang empty-literal runner was neither built nor executed; no Defender exclusions added).

### Deterministic Test Evidence on Candidate `5cb0fbf`

| Test Suite | Commands Run | Tests | Result | Duration | Focus Area |
|---|---|---|---|---|---|
| **Native Memory & Roots** | `python -m unittest tests.test_c23_native_memory` | 9 | **9 PASS / 0 FAIL** | 50.36s | Shadow frames, lexical exit root clearing, transient collections, call-depth trap |
| **Runtime, Heap & UTF-8** | `python -m unittest tests.test_c23_source_bytes tests.test_c23_utf8_slice tests.test_native_heap tests.test_native_utf8_parity` | 16 | **16 PASS / 0 FAIL** | 32.03s | Heap/arena growth under Clang/GCC, ASan/UBSan, UTF-8 scalar boundaries & error offsets |
| **C23 Correctness & CLI** | `python -m unittest tests.test_c23_correctness tests.test_c23_cli` | 38 | **38 PASS / 0 FAIL** | 177.55s | String equality, globals, negative unary ints, path collisions, module boundaries |
| **Standard Candidate Total** | — | **63** | **63 PASS / 0 FAIL** | **259.94s** | Full native candidate test baseline |

### Adversarial & Independent Lowering Gate

| Target Commit | Suite | Methods | Subtests / Assertions | Result | Notes |
|---|---|---|---|---|---|
| `5cb0fbf` (Candidate) | `verification/lucy_native_lowering_gate.py` | 13 | 37 evaluated | **FAIL (30 failures, 7 errors)** | Syntax errors on keyword fields, invalid `void` bindings, unvalidated exit codes |
| `9413dd5` (PR #29) | `verification/lucy_native_lowering_gate.py` | 13 | 37 evaluated | **PASS (13 pass, 0 fail, 0 error)** | All 4 defect families closed cleanly |
| `9413dd5` (PR #29) | `tests.test_c23_source_grant` | 5 | 5 evaluated | **PASS (5 pass, 0 fail)** | Proven explicit SourceBytes entry grant |

---

## 3. Findings Ranked by Consequence

### Finding 1 [HIGH / SEVERITY 1]: C23 Keyword Collisions in Struct and Union Member Declarations
- **Symptom:** Declaring a Pep record with a field named `switch`, `bool`, `nullptr`, `case`, `default`, etc., or a union with matching variant names, produces uncompilable C code (e.g. `struct pep_rec_Box { int64_t switch; };`).
- **Mechanism:** `pep_c23_direct.py` directly emits user syntax identifiers (`field["name"]`, `variant["name"]`) as C identifier names.
- **Reproducer:**
  ```pep
  type Box { switch: Int }
  let x = Box { switch: 42 }
  say(int_text(x.switch))
  ```
- **Remediation:** Lower field and variant members by checked ID rather than syntax names: `field_member(fieldId)` (`pep_field_...`) and `variant_member(constructorId)` (`pep_variant_...`), as implemented in PR #29.

### Finding 2 [HIGH / SEVERITY 1]: `Unit` Type Lowered to C `void` Breaks Values and Bindings
- **Symptom:** Any binding of a `Unit` value (`let u: Unit = say("first")`), passing of a `Unit` parameter (`fn accept(u: Unit) -> Int`), or storing `Unit` in a record produces invalid C syntax (`[[maybe_unused]] static void pep_bind_1;`, `variable or field 'u' declared void`).
- **Mechanism:** In `5cb0fbf`, `emit_c_type("Unit")` returned `"void"`. In Pep, Unit is a valid value representing side-effect completion; in C, `void` is an incomplete type that cannot name storage or variables.
- **Reproducer:**
  ```pep
  let u: Unit = say("hello")
  say("done")
  ```
- **Remediation:** Map `Unit` to `pep_unit_t` (`typedef struct { unsigned char unused; } pep_unit_t; #define PEP_UNIT (pep_unit_t){0}`), as implemented in PR #29.

### Finding 3 [MEDIUM / SEVERITY 2]: Unchecked Compiler Exit Status & Fragile Envelope Parsing
- **Symptom:** `build_c23` parses stdout JSON from `pep.ps1 check` without asserting `returncode == 0`. If `check` exits with an error status while printing diagnostics, `build_c23` can attempt code generation. Additionally, `C23Emitter` does not validate `schemaVersion == 2` or check that `typedTree` contains required arrays.
- **Remediation:** Assert `code == 0` in `build_c23` and validate schema version and typed tree shape in `C23Emitter.__init__`.

### Finding 4 [ARCHITECTURAL]: Native Semantic Context & Source Grant Seam
- **Symptom:** `5cb0fbf` only supports borrowed byte views passed via explicit test harnesses; there is no CLI option or driver support for passing source input to a compiled binary. Full native lexer execution without ambient file access requires an explicit revision-attested source grant adapter.
- **Remediation:** Adopt `NativeSourceGrant` and design session-bound reserved `ProgramInfo`/`FunctionInfo` layouts for full tool execution (documented in `docs/NATIVE_SEMANTIC_CONTEXT_REVIEW.md`).

### Inherited Staged Failures (Non-Regressions)
- The 29 staged A13 checker failures and 1 staged A14 step limit failure present in the repository remain unchanged. These are pre-existing baseline failures from staged development and were not introduced by candidate `5cb0fbf`.

---

## 4. Next Highest-Value Core Language Gap

Following qualification of the native runtime and lowering layer:
1. **Canonical Reserved Semantic Context Layouts:** Seed-authored export of `ProgramInfo`, `FunctionInfo`, `CallEdge`, and `SemanticDiagnostic` records with negative IDs into `typedTree`, avoiding syntax re-parsing.
2. **Session-Bound Typed Tool Transport:** Bounded cursor and result transport under 128 tool call depth and 100,000-step accounting to allow the native Pep lexer to execute end-to-end within the tool protocol without ambient file reads.

---

## 5. Formal Verdict

- **Result:** **PARTIAL**
- **Tested SHA:** `5cb0fbf065f096b3826f961e4b475ab1c1f2b589`
- **Resolution Path:** Rebase / integrate candidate with PR #29 (`9413dd55779da411298c1ee3db27f3ba4fb59196`), which fully satisfies all independent acceptance gates.
