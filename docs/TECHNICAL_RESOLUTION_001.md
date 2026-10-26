# PEPIN: Technical Resolution 001

## Response to Argon's v0.3 architectural review

**Status:** Binding technical decisions for the v0.3 design direction. This resolution supplements [Founding Design v0.3](FOUNDING_DESIGN_v0.3.md). It does not claim these mechanisms are already implemented.

> **Provenance.** The original resolution writing block referenced in the design conversation was not available in the retained transcript. This record preserves the specific accepted decisions supplied for this repository and the compatible facts in its existing design notes. It is not represented as a verbatim recovery of the unavailable block or of Argon's review.

## 1. Authority and scope

This resolution makes the following architectural choices binding for future design and implementation. It does not authorize language features to be described as shipped. The OCaml seed and its tests remain the authority for current implementation facts. Where implementation detail is deliberately left open below, a later packet must specify it before code depends on it.

## 2. Typing: synthesis and checking

**Decision.** Use bidirectional typing, with distinct synthesis and checking judgments. Expressions synthesize a type where their form and context determine one. Expected types flow inward at annotated bindings, function arguments, returns, and other checking positions. The checker must not turn every expression into an unconstrained inference variable to imitate a general-purpose unifier.

**Consequence.** Context can give a hole a useful expected type; a hole without sufficient context remains explicitly unconstrained. Branches and arguments are checked against known expectations, and diagnostics identify the source span and applicable expected type. Implementation packets must state where each new expression synthesizes and where it checks.

## 3. Partial typed trees and holes

**Decision.** Preserve a partial typed tree for a syntactically valid but incomplete program. Known subexpressions keep their resolved identities and types; holes remain explicit nodes with optional names, expected types when available, scope, visible bindings, and source spans. Incomplete is a distinct program state, not success and not invalidity.

**Consequence.** Inspection and semantic queries may operate on incomplete trees. `check` reports incompleteness, and execution is refused unless the checked program is complete. A hole fill does not bypass parsing or checking; it produces a new source revision that is checked again.

## 4. Parametric containers before self-hosting

**Decision.** A bounded set of parametric containers may be implemented as built-in compiler forms before the Pep compiler is self-hosted. Their types and operations are compiler-known. This is the only permitted early route for parametric containers.

**Boundary.** This does not authorize user-defined generic declarations, a general-purpose extension type system, or arbitrary host types. Container inventory, syntax, operations, and type rules must be specified and accepted before implementation. Their representation must be expressible by the interpreter and the planned C11 backend.

## 5. Source-preserving structural edits

**Decision.** Structural edits operate against a specific immutable source snapshot and preserve untouched source bytes. They target identified syntax/semantic structure rather than rewriting the whole file as a formatting side effect.

**Consequence.** Comments, whitespace, and the existing line-ending style outside the changed region remain intact. An edit whose target is ambiguous or no longer matches its source revision is rejected. A formatter, if added, is explicit and separate from structural editing. Edit results include enough identity to establish which source revision they changed and which new revision they produced.

## 6. Revision-bound named holes

**Decision.** A named hole is identified together with its document identity and exact revision. The name alone is not a globally stable identity and does not survive edits by implication.

**Consequence.** Query results, proposed fills, and editor actions carry the revision they were derived from. Applying a fill against a different revision is rejected or requires a fresh query. After any source change, clients re-query rather than matching holes by stale byte offset or name alone.

## 7. Original UTF-8 offsets and line endings

**Decision.** Source offsets are byte offsets into the original UTF-8 file contents. The compiler does not normalize line endings before computing offsets. Both LF and CRLF are supported; each represents one logical line break for line reporting, while CRLF occupies two original bytes.

**Consequence.** JSON spans and edit positions use the same original-byte coordinate system. Tests must demonstrate correct offsets and stable line/column semantics for LF and CRLF versions of the same source. Any future edit operation must preserve original bytes outside its target.

## 8. Immutable extension message boundary

**Decision.** Extensions communicate with the compiler host through immutable messages. Extensions do not receive mutable shared references to compiler-owned ASTs, typed trees, document snapshots, or host state.

**Consequence.** Inputs and outputs are explicit values validated at the boundary. Extension errors cannot partially mutate a compiler snapshot. Message schema and protocol compatibility are versioned. Any future extension design must preserve deterministic host-owned state transitions and make failures inspectable.

## 9. Versioned JSON interface

**Decision.** Versioned JSON is the stable machine interface for compiler description, syntax/semantic inspection, diagnostics, queries, and future document or extension operations. Human-readable CLI text is not the automation contract.

**Consequence.** Each response identifies the applicable schema or protocol version and uses explicit states. Consumers reject unsupported versions rather than guessing compatibility. Additive or breaking changes follow a documented version policy and acceptance tests. The current CLI's schema version and command set describe only what the implementation actually supports.

## 10. Interpreter-first OCaml bootstrap and Pep-written C11 generator

**Decision.** Continue from the OCaml interpreter seed. Do not switch the primary semantic seed back to the historical MoonBit prototype. The intended native compilation route is a C11 generator written in Pep and compiled by a host C compiler.

**Sequence.** First keep parsing, typed representation, checking, holes, queries, and interpreter behavior explicit and testable in OCaml. Then add the language/runtime facilities required by the backend. Implement the C11 generator in Pep, validate its output and behavior against the interpreter, and use it as the path toward self-hosting. OCaml remains bootstrap implementation machinery, not the language's semantic definition.

**Boundary.** The C11 generator is a target, not a current feature. Documentation and `describe` must not claim native Pep compilation or self-hosting until the generated backend exists and passes its acceptance contract.

## 11. Extension activation and acceptance contracts

**Decision.** Extension presence does not imply activation. Activation is explicit and guarded by a declared activation contract. An extension is considered active only after it satisfies its acceptance contract.

**Contract requirement.** Before an extension implementation is authorized, its packet must define the activation preconditions, versioned immutable messages, observable active/inactive/failure states, and acceptance evidence. The host remains the authority for activation and must not expose a partially accepted extension as active. The exact registry, trust, and distribution mechanism is intentionally not fixed by this resolution.

## 12. Required acceptance evidence

Future implementation packets applying this resolution must include evidence appropriate to the changed boundary:

- typing tests that distinguish synthesis from expected-type checking;
- partial-tree tests that keep known typed structure while representing holes;
- execution refusal for incomplete checked programs;
- container typing and runtime/backend agreement for the explicitly approved built-ins;
- edit tests proving untouched bytes and line endings are preserved, plus stale and ambiguous target rejection;
- revision tests proving named-hole results cannot be applied to another revision without re-query;
- LF/CRLF differential tests with original UTF-8 byte offsets;
- protocol-version and immutable-message boundary tests before any extension is activated;
- JSON schema/version tests for each published machine command; and
- interpreter-versus-generated-C behavior checks before the C11 backend is described as accepted.

## 13. Implementation status at publication
The OCaml seed provides bidirectional synthesis/checking, explicit partial checked expressions for holes, original UTF-8 byte spans, LF/CRLF line reporting, versioned JSON responses, and an interpreter that refuses incomplete programs. These facts are documented in [SEED_LANGUAGE.md](SEED_LANGUAGE.md) and exercised by the Windows CLI suite.

Implementation packet A2 adds an in-process, ephemeral JSONL session with immutable source revisions, SHA-256 revision IDs, revision-bound hole identities, stale-checked raw byte edits, retained prior analyses, and a cache for repeated analysis of the same revision. Packet A3 adds `fill_hole` preview and application through that same parser/checker: it resolves a scope-qualified named hole at the current revision, parses one expression, splices original bytes, and validates the complete candidate before advancing the current revision. Packet A4 adds nominal records, recursive tagged unions, constructor expressions, source-resolved field access and patterns, exhaustive matching for supported patterns, and typed holes scoped to match arms. Every changed revision is fully parsed and checked; there is no cross-revision incremental reuse.

General structural refactoring beyond named typed-hole filling, parametric containers, an extension boundary or activation flow, and a Pep-written C11 generator remain unimplemented. The raw `apply_edit` operation remains a low-level byte-range edit and may create an invalid revision.
