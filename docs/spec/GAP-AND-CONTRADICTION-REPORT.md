# Pep Specification — Gap and Contradiction Report

**Slice 1 of the Pep Language Specification v0.1 mission. Status:** audit input to the
normative draft, not a normative document itself. No language rule is settled by this report.

- **Worktree:** `D:/Projects/wt-spec-v01` (clean), **branch:** `spec/pep-spec-v01`
- **Base HEAD:** `57fe424af47e6c097b49eb26a711b3a9f0d7b980` (2026-10-31,
  `campaign/pep-v01-sustained-build-20261027`)
- **Date:** 2026-11-04. **Author role:** language specification agent.
- **Unrelated work preserved:** `tests/test_a14_c23.py` modification lives only in the
  `D:/Projects/pepin` worktree; untouched by this branch.

## Sources inspected (exact revisions)

| # | Source | Revision / location |
|---|--------|---------------------|
| S1 | Founding Design v0.3 | `docs/FOUNDING_DESIGN_v0.3.md` at base HEAD |
| S2 | Technical Resolution 001 | `docs/TECHNICAL_RESOLUTION_001.md` at base HEAD |
| S3 | Technical Resolution 002 | `docs/TECHNICAL_RESOLUTION_002.md` at base HEAD |
| S4 | 27 Oct consolidated language draft (PR #14, OPEN) | `review/pr14-head` = `97503821133ea3119f9639245b07209f68f62dee` (2026-10-28); file `docs/final-draft/PEP-LANG-FINAL-DRAFT-2026-10-27.md` (27,144 bytes) |
| S5 | Final-draft acceptance matrix (PR #14) | same ref, `docs/final-draft/ACCEPTANCE-MATRIX.md` |
| S6 | Language reference (PR #18, OPEN) | `review/pr18-head` = `845b028c2185f3a5f30d3618bc7ca9c853970389` (2026-10-28); file `docs/manual/PEP-LANGUAGE-REFERENCE.md` |
| S7 | OCaml seed implementation | `pep_ocaml.ml` (145,104 bytes) at base HEAD — read directly, not via summaries |
| S8 | Seed status docs | `docs/DESIGN.md`, `docs/SEED_LANGUAGE.md` at base HEAD |
| S9 | Release roads and ledger | `docs/roadmaps/ROAD-2-PEPIN-1.0.md`, `docs/roadmaps/FULL-LANGUAGE-LEDGER.md` at base HEAD |
| S10 | Packets and acceptance records | `docs/packets/CURRENT.md`, `A6/A7/A8` packets, `docs/packets/archive/A5,A6-ACCEPTANCE-RECORD.md` |
| S11 | Campaign CLI | `pep.ps1` at base HEAD |

**Not directly inspected (provenance gap, see G13):** full texts of Basic Memory decisions
DEC-001/002/003A–H/004–009. The live Basic Memory MCP servers were unreachable from this
session (`mcp` status: both servers not listening), and the Cloud note URLs require
authentication. This report relies on their consolidated summaries in S4/S6/S9 and treats
any detail visible only there as *reported*, not verified.

**Evidence classes used** (from S6 §1): accepted design direction ≠ proposed
syntax/contract ≠ implemented seed feature ≠ development-branch feature ≠ verified at a
revision ≠ released. Accepted master remains A8; `docs/packets/CURRENT.md` holds
`current: null` — no implementation phase is currently authorised.

## Gaps: draft promises with no seed mechanism (all verified in S7)

Seed ground truth comes from the `ty`/`expr`/`stmt`/`top` type definitions and the
reserved-builtin lists in S7 (`pep_ocaml.ml` lines 1–60, 105, 158, 396–423, 594, 753–844,
1288–1289, 1993), plus the absence of a `test` subcommand in S11.

| ID | Draft target (S4/S6) | Seed reality (S7) | Spec consequence |
|----|----------------------|-------------------|------------------|
| G1 | Generic functions/types, `[T]` parameters, inference of type arguments (FD §3.2) | No type parameters exist. `ty` = `Int\|Bool\|Str\|SourceBytes\|Unit\|Named\|List`. `List[T]` is the only parametric form and is compiler-known | Generics belong in the decision register, not the core spec |
| G2 | `Option[T]`, `Result[T,E]` as generic families; postfix `?` error propagation (FD §§4, 6) | Not expressible: nominal unions exist but cannot take parameters; no `?` postfix operator (`?name` lexes only as a typed hole) | Tokenizer collision (`?name` vs postfix `?`) is an open normative item |
| G3 | First-class functions, closures, `edit`/`take` capture modes (FD §§3.5, 5) | No lambda expressions; only top-level `fn`. No `edit`/`take` syntax | Access contracts are target-only |
| G4 | Modules: file = module, `pub`, qualified `import`, `as`, cycle rejection (FD §8) | No imports, no visibility, single-file programs | Module rules are target-only |
| G5 | `Float`/`Float32`, `Byte`/`Bytes`, `Array[T,N]`, `Map[K,V]` (FD §4) | Absent. `Int` is checked signed 64-bit; `Str` is the only text/binary-adjacent value in ordinary code | Numeric/text families are decision-register items |
| G6 | `break` / `continue` (FD §2; matrix §1) | `stmt` has `SFor`/`SWhile` but **no break/continue constructors** | Must not be presented as seed-supported |
| G7 | Effects: inferred effects, `uses` ceilings, effect-carrying function types (FD §6) | No effect syntax, inference, or ceilings anywhere in S7 | Target-only |
| G8 | `async fn` / `spawn` / `await`, channels, task supervision (FD §9) | Absent | Target-only |
| G9 | `danger` blocks, owned handles, allocators, FFI (FD §7) | No `danger` syntax; no allocator/handle types | Target-only |
| G10 | `test "name" {…}`, `pep test`, `std.test` (FD §10) | No `test` syntax in S7; **no `test` subcommand in S11**. The manifest-driven runner exists only on dev branch `52a75d6` (reported in S6 §13, not rerun here) | Test grammar is target-only |
| G11 | Refinement types / flow propositions (FD §3.6) | No refinement machinery | Target-only |
| G12 | Semantic Notes `#@ intent/verify/prefer` as compilable syntax (FD §11) | `#` and `//` both lex as ordinary comments (S7 line 105); no `#@` handling | Notes are comments to the seed; any executable role is target-only (see C2) |
| G13 | DEC-001…009 full decision texts | Noted above: unreachable this session | Every register entry sourced only from S4/S6/S9 summaries is marked *reported*; DEC re-verification is a queued follow-up, not a blocker for drafting from S7 |

### Seed-supported core (may become normative in v0.1, pending slice 2 verification)

Scalar `Int`/`Bool`/`Str`/`Unit`; monomorphic nominal records and recursive tagged unions
with constructors, field access, exhaustive `match` (nested constructor/binding/wildcard
patterns, arm-local holes); annotated/inferred `let`, `var` + assignment, lexical blocks;
recursion and forward calls; `if` expression (**requires** `else`) vs `if` statement
(`else` optional); `for-in` over `List`, `while`, statement conditionals; scalar-only
`==`/`!=`/`!`/`&&`/`||` with `Bool`-only short-circuit conditions; homogeneous `List[T]`
literals incl. contextual empty-list checking, `length`/`append`/`contains`/`prepend`/
`reverse`; monomorphic builtins `say(Str)->Unit`, `int_text(Int)->Str`; `SourceBytes`
value with `byte_at`/`byte_slice`/`utf8_slice`/`byte_length` and host-gated
`source_bytes()` (tool protocol v2 only); named/anonymous typed holes with expected types
and scope-qualified fill at the exact current revision; three program states
valid/incomplete/invalid where incomplete refuses `run` **even in unused functions**;
first-error-only diagnostics with expected-type annotation; original UTF-8 byte offsets
with LF/CRLF line reporting; immutable revisioned snapshots; `inspect`/`check`/`query`/
`run`/`describe --json` (schema v2); in-process schema-v3 `session --jsonl` with
SHA-256 revision IDs and same-revision analysis cache; budgets CLI 1,000,000 steps /
512 call depth, tool host 100,000 steps / 128 call depth, `say` denied in tools.

## Contradictions (recorded with provenance; none silently resolved)

- **C1 — SourceBytes status.** S8 (`DESIGN.md`) says the A10 review branch "adds … `SourceBytes`
  … A10 remains unaccepted", yet S7 at base HEAD already contains `SourceBytes` in `ty`,
  the full byte-builtin family (`byte_at`, `byte_slice`, `utf8_slice`, `byte_length`,
  `prepend`, `reverse`, gated `source_bytes()`), `open_bytes` session support, a `describe`
  line advertising `SourceBytes`, and `tests/test_a10.py` exists in-tree. Either the A10
  fragment was merged into the campaign branch without acceptance, or S8 is stale relative
  to the campaign branch. **Disposition for the spec:** SourceBytes/byte builtins are
  *development-branch features on the campaign line*, not accepted core, until an
  acceptance record says otherwise. Flagged for owner clarification; the normative core
  draft will mark the boundary explicitly rather than pick a winner.
- **C2 — Semantic Notes authority.** S4 §11 presents the three-layer model (code + `#@`
  notes + comments) as "accepted", while the 28 October priority correction cited in S6
  §§1/14/18 explicitly **supersedes annotation-centred semantics as the core architecture**:
  compiler-derived knowledge plus read-only stage checkpoints are the one architecture,
  and notes are not a 1.0 blocker. **Disposition:** the priority correction (later,
  owner-level) wins for spec purposes; S6 already reconciles this way. The spec will
  describe notes as advisory/provenance-only and will not normatively define `#@` tags,
  which live in the unmerged PEP-SN-001 proposal.
- **C3 — Test-count portability.** S10/S9 cite builder-reported counts at named SHAs
  (A8: 55/55 + 11/11 MoonBit; A7: 50/50; A13 checker: 48/48 + 11/11 A14 at `f10d5db`;
  native Int-list loop: 17/17 at `7bf4826`; test-runner: 12 pass + 1 skip at `52a75d6`).
  None was rerun in this session, and several SHAs live on non-campaign branches.
  **Disposition:** counts are cited only as *builder reports at stated SHAs*, never as
  current verification. The conformance matrix (slice 4) will map requirements to seed
  tests present at *this* spec branch base, by file and name.
- **C4 — Collection semantics (resolved, record only).** S1 suggested reference-like
  collection language; S4 §1 explicitly records supersession by accepted DEC-001/005
  independent value semantics. No live conflict; the spec carries the newer rule.
- **C5 — C11 vs C23 (resolved, record only).** S1/TR001-forward references name C11;
  S3 supersedes with C23 (Clang primary, GCC cross-check). No live conflict; the spec
  carries C23 and treats MoonBit A0 C11 output as historical.
- **C6 — "Functions cannot capture top-level values" (S8 `SEED_LANGUAGE.md`).**
  Ambiguous against S7: top-level statements extend the global env (line 702) and
  functions resolve against checker state, so the sentence as written is either about
  nested closures (which do not exist in S7) or is imprecise. **Disposition:** the spec
  will state only what S7 shows (no nested/lambda functions; top-level `fn` + ordered
  top-level statements) and will not repeat the uncited sentence until verified against
  checker behaviour.

## What slice 2 (normative core draft) will and will not do

- **Will:** normatively specify exactly the seed-supported core listed above, with
  observable behaviour, budgets, JSON surface, and revision/hole/tool semantics, each
  tied to S7 constructs and seed tests by file.
- **Will not:** invent rules for G1–G12, resolve C1/C6 beyond marking the boundary, or
  present S4-proposed syntax as compiling Pep. Open items move to the decision register
  (slice 3) with existing commitments, options, trade-offs, dependencies, and a
  recommendation only where the inspected evidence supports one.
- **Queued verification (non-blocking):** DEC full-text re-check when Basic Memory is
  reachable; C1 owner clarification; executable spot-checks of seed behaviour via
  `pep.ps1` before the conformance matrix claims coverage.
