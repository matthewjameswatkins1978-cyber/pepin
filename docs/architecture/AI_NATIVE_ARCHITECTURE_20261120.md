# Pepin AI-Native Architecture & Specification Charter
**Date:** 20 November 2026  
**Status:** Independent Architectural Reassessment & Living Specification  
**Mission:** PEP-AG-20261120-01 (Authorised by Matthew Watkins)  
**Author:** Antigravity (Independent Architecture & Implementation Seat)  
**Base Commit:** `bddd354` | **Branch:** `ag/ai-native-architecture-20261120`

---

## 1. Executive Summary & Baseline Diagnosis

### 1.1 The Core Strength
Pepin was founded on a profoundly sound premise: an **AI-first programming language** is not an LLM embedded in a compiler, but a deterministic, introspectable compiler whose semantic authority, typed ASTs, typed holes, and immutable revisions are exposed to intelligent tools through stable versioned boundaries.

### 1.2 The Bottleneck Identified
During October and early November 2026, the project became severely constrained by an architectural trap: **premature recursive self-hosting through interpreter-hosted tool evaluation**.
Specifically, the campaign attempted to run a ~300 KB Pep-authored compiler (`pep_lexer.pep`, `pep_parser.pep`, `pep_checker_a13.pep`, `pep_c23_emitter.pep`) *inside* the OCaml seed interpreter's tool session under an immutable 100,000-step budget and 1 MiB JSONL message ceiling. This led to:
- Micro-chunking of ASTs (ChunkLedgers, 66-node ceilings, statement-group chunking) that consumed thousands of engineering hours.
- Quadratic token accumulation workarounds.
- A widening gulf between master (A8) and complex, unaccepted experimental branches (A11–A14).
- Crippling compilation latency (~600 ms for an 18 KB lexer just to lex tokens).

### 1.3 The 20 November Strategic Reset
Matthew approved a vital reprioritisation:
> **"Prioritise a small, genuinely usable general-purpose language, direct C23 native compilation via Clang/GCC, compiler-derived Semantic Maps, and bottom-up standard libraries over immediate in-interpreter self-hosting. Self-hosting remains a desirable destination, but must not gate usable language delivery."**

This document establishes the architecture for that usable, agent-native Pepin.

---

## 2. Comparative Analysis & Candidate Adoption Register

We examined eleven AI-first and relevant modern language designs (Aver, ilo, Mog, Almide, Lom, NanoLang, Tacit, X07, Astra, Lume, Toke) alongside established systems (Rust/rust-analyzer, Lean 4, Zig, Koka).

| System | Concept Examined | Decision | Rationale | Implementation Impact |
|---|---|---|---|---|
| **Aver** | Dependency-complete context packets & `verify`/`intent` blocks | **ADAPT** | Context packets give an AI worker exactly the symbols, caller facts, and requirements it needs within a token budget, eliminating context bloat. However, mandatory syntax blocks are rejected in favour of external Living Spec companion files. | Implemented as `pep_semantic_map.py context` query with token limits. |
| **ilo** | Graph-structured compiler facts & explicit diagnostic IDs | **ADOPT** | Treating symbols, calls, and tests as a compiler-derived queryable graph aligns perfectly with Pepin's Semantic Map. | Integrated into Semantic Map schema and bi-directional test links. |
| **Mog** | Single idiomatic form per concept, minimalist surface | **ADOPT** | Eliminates agent hallucination and stylistic churn. One way to write loops, one way to structure conditionals, one way to declare records. | Pep syntax remains compact; no redundant sugar added. |
| **Almide** | Semantic diagnostic explanations & repair recipes | **ADAPT** | Useful for guiding agents, but explanations must be deterministic compiler facts, not generated hallucinations. | Structured error payload includes actionable `repairHint`. |
| **Lom** | Multi-round repair benchmarks & typed repair plans | **ADOPT** | Provides reproducible benchmarks for AI repair velocity and deterministic machine-applicable patch plans. | Mechanical repair generator in Semantic Map; test repair benchmark suite. |
| **NanoLang** | Shadow tests & behavioural locality | **ADAPT** | Associating test cases directly with symbol contracts without cluttering function bodies with compulsory test boilerplate. | Behavioural Map indexes direct and indirect test contracts per symbol. |
| **Tacit / X07** | Structural editing & AST manipulation | **ADAPT** | Structural edits must preserve original source bytes, comments, and line endings. Reject X07's binary/JSON AST format as source; plaintext `.pep` remains canonical. | Retain Pep's byte-preserving typed-hole and replacement engine. |
| **Astra** | Certified safe repair transformations | **ADOPT** | Differentiates between *safe automatic* repairs (unambiguous, type-checked) and *suggested choices*. | Mechanical repairs classified by safety tier (`SAFE_AUTOMATIC`, `CHOICE`). |
| **Lume** | Token-budgeted knowledge retrieval | **ADOPT** | Limits compiler fact extraction to fit within model context windows (e.g., 2k, 4k, 8k tokens) with truncation markers. | `context_packet` supports `--max-tokens` and `--depth`. |
| **Toke** | Compact, high-density tokenisation | **REJECT** | Optimising surface syntax for a specific BPE tokenizer creates cryptic, brittle code for humans and cross-model reasoning. | Plain UTF-8 readable syntax retained. |
| **Lean 4** | Elaboration, metavariables, expected-type holes | **RETAIN** | Existing bidirectional typing with typed holes is one of Pep's strongest assets. | Deepen expected-type propagation into match arms and collection literals. |

---

## 3. Ten Architectural Pillars

### Pillar 1: Practical C23 Native Compilation
Instead of forcing the C23 generator to run inside the fuel-constrained OCaml interpreter tool protocol for every build:
- The primary OCaml compiler or a direct C23 driver translates checked Pep ASTs directly to strict ISO C23 (`-std=c23`).
- Compiles with **Clang** (primary) and cross-checks with **GCC** (conformance oracle).
- Zero dependencies on non-standard runtime libraries: produces self-contained C code with a tiny native runtime (`pep_runtime.h`).
- Pep-written self-hosting compiler development continues in parallel on its dedicated branch, but does not block language usability.

### Pillar 2: Small, Coherent Language & Bottom-Up Standard Library
Pepin eliminates artificial expressivity bottlenecks:
- **Top-Level Value Access:** Functions can directly read top-level immutable `let` constants.
- **Monomorphic Standard Library:** Rich built-in modules for string formatting, collections (`List[T]`, slice, find, filter), byte manipulation, and basic terminal I/O.
- **Fail-Closed Type Safety:** Strict static type checking with no implicit conversions.

### Pillar 3: Compiler-Directed Safe Memory Management
- **Value Semantics by Default:** Integers, booleans, and small records are passed by value and allocated on the stack.
- **Linear/Owned Containers:** Lists and records have clear ownership semantics.
- **Deterministic Lifetime & Scoped Arenas:** Native C23 runtime uses arena/region allocation for AST and compilation tasks, freeing entire arenas upon phase completion.
- **Explicit Danger Boundary:** Any unsafe FFI or raw memory pointer access requires explicit `danger` blocks.

### Pillar 4: Compiler-Derived Semantic Map
A single authoritative, revision-bound query interface that exposes:
- Symbol declarations, types, and scopes.
- Call graph edges (callers, callees, transitive reachability).
- Effects and mutation signatures.
- Context-budgeted extraction for intelligent agents.

### Pillar 5: Living Program Specifications
- Every project or non-trivial module carries a Living Specification Sheet (`.pep.spec.json` or `.spec.md`).
- Contains: Purpose, Requirements with stable IDs (`REQ-xxx`), Non-Goals, Data Contracts, Invariants, and Failure Modes.
- **Semantic Linkage:** Compiler and tooling verify that every requirement ID is bound to implementing symbols and verifying tests.

### Pillar 6: Behavioural Map & Linked Evidence
- Bi-directional test relationship:
  - `symbol -> tests`: Lists direct unit tests, integration tests, and observed coverage.
  - `test -> symbols`: Explains which contracts the test validates.
- **Affected Test Calculation:** When an agent edits a symbol, the Semantic Map computes the conservative minimal set of impacted tests.
- **Stale Evidence Invalidation:** Editing a symbol marks linked test receipts as STALE until re-executed.

### Pillar 7: Structured Diagnostics & Multi-Error Accumulation
- The checker transitions from "stop at first error" to **multi-error diagnostic accumulation**: independent errors in separate functions/statements are collected together.
- Every diagnostic provides:
  - Stable error code (`PEP_TYPE_MISMATCH`, `PEP_UNBOUND_NAME`, etc.).
  - Source span (byte offset, line, column).
  - Expected vs. actual types.
  - Deterministic **Mechanical Repair Plan** where safe.

### Pillar 8: Multi-Agent-Native Collaboration
Three supported collaboration modes over standard Git worktrees:
1. **Disjoint Tasks:** Agents work on mutually exclusive symbol sets with clean mergeability.
2. **Cooperative Candidate Edits:** Multiple agents propose candidates for a single contract, evaluated against the same living spec and test suite.
3. **Competing Implementations:** Alternative implementations competing on performance/memory budgets against identical oracles.
- **Semantic Conflict Detection:** Detects when two branches have zero Git text conflicts, but introduce conflicting type, signature, or requirement changes.

### Pillar 9: Epistemic Rigour & Provenance
Every assertion made by an agent or tool is categorized into one of four epistemic tiers:
- `ESTABLISHED`: Proven by compiler check or formal invariant.
- `TESTED`: Verified by a fresh, reproducible test execution on a named git SHA.
- `INFERRED`: Plausible deduction without fresh verification.
- `UNKNOWN / UNPROVEN`: Lacking empirical data or verification.

### Pillar 10: Human & Agent Usability Parity
No tool, API, or format should be exclusive to AI agents. What an agent queries via JSON (`pep.ps1 semantic-map`), a human programmer can view in readable markdown or CLI diagnostics. The canonical source code remains clean, readable `.pep` text.

---

## 4. Architectural Roadmap & Slice Cadence

```
[Phase 1] Architecture, Living Spec Contract & Adoption Register (Current)
   │
   ▼
[Phase 2] Semantic Map Engine, Context Packets & Behavioural Mapping Tool
   │
   ▼
[Phase 3] Usability Realignment: Top-Level Constants & Multi-Error Checker
   │
   ▼
[Phase 4] Direct C23 Native Emitter & Standard Library Slice
   │
   ▼
[Phase 5] Multi-Agent Safe Integration & Semantic Conflict Simulation
```

This roadmap directly implements Matthew's 20 November instructions and provides the foundation for an exceptional programming language.
