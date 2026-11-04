# PEP-SN-001 — Semantic Notes: three layers, one Pep source
**Design proposal, 27 October 2026. Status: draft implementation contract. No compiler support is claimed. Not an authorised compiler milestone or master merge.**

## Purpose
Pep is an AI-first language whose compiler should expose what it actually knows. Source also contains knowledge the executable statements do not express. Keep three complementary layers in one ordinary .pep file:

1. **Program code**: executable behaviour, types, effects and expressions. The sole source of runtime semantics.
2. **Semantic Notes**: optional, short, structured source annotations interpreted by the Pep compiler, indexed by its revision-bound semantic model, and available to human and AI operators.
3. **Ordinary comments**: unconstrained rationale, history, explanation, trade-offs and warnings for the next human or AI reader. These never become compiler premises automatically.

A Semantic Note should supply useful context, state a preference, or request verification **without ever manufacturing proof, authority, correctness or permission**. A model's confidence is not compiler evidence. The proposal is additive to the existing compiler contracts and does not require a new AI runtime.

## Evidence and design precedents
- ACSL (Frama-C): source-adjacent preconditions, postconditions and invariants usable by analysers: https://frama-c.com/acsl.html
- Rust attributes and doc comments: metadata with a syntax distinct from ordinary code; compiler-defined interpretation: https://doc.rust-lang.org/stable/reference/attributes.html
- Dafny: explicit proof obligations and incomplete but sound verification: https://dafny.org/latest/DafnyRef/DafnyRef.html
- Prusti: annotated contracts on an existing language and structured verification: https://github.com/prusti/prusti
- **Failure mode to avoid:** Clang __builtin_assume can lead to undefined behaviour if the assumption is false: https://clang.llvm.org/docs/LanguageExtensions.html

Our distinctive addition is an **AI-operable, versioned, revision-bound explanation and obligation interface** over these notes. The compiler is the semantic authority; source-adjacent model-authored annotations are untrusted proposals until checked.

## Proposed surface: a tiny protocol inside comments
Canonical annotation marker: **#@** at the start of the comment payload. Pep already lexes **#** and **//** as ordinary line comments. Keep ordinary comments unchanged. A #@ line is still non-executable source trivia, but the compiler retains and parses it.

Example (future note parser; program syntax drawn from the current Pep seed):

~~~pep
# We use channel counts from the caller; zero would be invalid.
# This is a design warning for future human and AI maintainers.
#@ intent: "Audio frames contain interleaved channel data"
#@ verify: channels != 0
#@ prefer: latency

fn channel_count(channels: Int) -> Int {
    return channels
}
~~~

The existing seed sees #@ lines only as comments; this is **not evidence of implemented Semantic Notes**.

### Initial vocabulary (proposed)
| Tag | Value | Semantics | May change observable behaviour? |
| --- | --- | --- | --- |
| **intent** | Quoted UTF-8 string | Human/AI domain context, searchable metadata; NEVER a proof premise | No |
| **prefer** | One enum: latency, throughput, size, low_memory | Advisory optimisation priority, implementation may ignore it; cannot weaken safe semantics or affect permissions | No |
| **verify** | Ordinary pure Pep Bool expression | Ask verifier to establish a fact at the annotated declaration's **entry**; creates a revision-bound obligation with proof status | No, unless a separate accepted contract/check explicitly enforces it |

Prefer **one level of simple tag names** over a general embedded DSL or unrestricted macros. Require a colon, value and a complete valid line. Normal comments before/after notes are ordinary comments. Multiple #@ lines form a group.

Important: **verify is a request, not assume.** For arbitrary Int arguments, verify: channels != 0 will normally remain unresolved; this does not mean the function's caller obeys the condition, and the compiler MUST NOT optimize on it. Later formal requires/ensures/invariant contracts may make obligations enforceable once PEP-DEC-003H is specified and a verifier or explicit runtime checking contract is implemented. Do not call an unresolved verify annotation a precondition. Likewise prefer: latency does not guarantee real-time deadlines; no_alloc and no_gc must be hard separately verified effect/runtime contracts, not advisory synonyms.

## Attachment/identity rules for first slice
1. First implementation supports note groups immediately preceding a **top-level named fn or type declaration** only. No blank line between the final note and the target; ordinary adjacent # comments may appear in the group. Other placements produce an explicit unattached-note diagnostic, never silently reattach to a different symbol.
2. Notes belong to a declaration resolved by the authoritative lexer/parser, not heuristically matched by a second text parser. Parsing comments must respect quote/string boundaries and #@ text embedded in strings.
3. Use the **original UTF-8 bytes**, span and retained SHA-256 document revision. Preserve LF and CRLF without normalising, preserve ordinary comments and exact source outside edits, and never associate notes to a guessed symbol on a stale revision.
4. The annotation grammar is constrained and extensible via versioned known tags. Unknown tags, bad enum values, duplicate incompatible notes, malformed expressions and orphan notes produce structured note diagnostics, not silent acceptance.
5. The parser and checker remain deterministic. A compiler without Semantic Note support may ignore these comments, but must not claim semantic acceptance. A tool must query supported capability/version before relying on notes.
6. **No note can grant filesystem/network/process authority; alter access modes, effects, ownership or memory safety; rewrite Pep syntax; create compiler-known type abilities; or override a checked program.**
7. Standard Pep expressions reused in verify: resolve names and types in the attachment's declared scope; require a pure Bool and no unapproved calls/effects. No new expression parser or AI-authored logic evaluator. Future support must define exact entry/post/loop scope before accepting them.

## Semantic truth states
Return structured note records and never conflate:
- **informational**: intent (source author's claim; not proved);
- **advisory**: prefer (compiler may use as a tie-breaker only where allowed);
- **unsupported**: a recognised formal note whose checker is not yet available;
- **unresolved**: well-typed verify request whose proposition is not established;
- **proved**: verified under named assumptions, checker revision and verification method;
- **refuted**: an actual demonstrated counterexample with evidence;
- **invalid**: parse/type/scope error in a note.

A failed or timed-out proof is **unresolved**, never refuted. A test passing is **observed**, not a universal proof. A source edit revokes prior proof evidence unless dependency-validity has been checked; the prototype may simply re-analyse on every new revision. Keep proof confidence separate from semantic authority.

## Machine interface, AI-first
Extend the existing revision-aware compiler/session boundary, **not a new source-of-truth database**. A proposal for eventual query shape:

~~~json
{
  "notesSchemaVersion": 1,
  "document": "doc-1",
  "revision": "sha256:<actual>",
  "symbolId": "<compiler-assigned symbol identity for this revision>",
  "notes": [
    {"kind":"intent","value":"Audio frames contain interleaved channel data","status":"informational","span":{"startByte":0,"endByte":0}},
    {"kind":"verify","expression":"channels != 0","status":"unresolved","obligationId":"<revision-bound-id>"},
    {"kind":"prefer","value":"latency","status":"advisory"}
  ]
}
~~~

Placeholders above are illustrative, never fixed values or an implemented wire schema. Exact wire field names, spans, bounded response size and protocol version must be tested against session schema-v3 and Tool Protocol v2. Avoid pouring entire comment bodies into bounded extension transports; return short metadata and permit targeted revision-bound retrieval by symbol/note handle. Offer query capability discovery (supported tags, statuses, schema version, limits), source locations, explanation of why a note is unproved/ignored and permissible next actions. Preserve the distinction between compiler facts, source claims, external evidence and AI suggestions.

A future Semantic Map should be **materialised from** the compiler's immutable analysis and notes, updated or invalidated by source revision; it is a cache/index, not competing semantics. Plain comments should be accessible to AI as source-associated non-authoritative context without being parsed as proofs.

## Interaction with already accepted Pep design
- **PEP-DEC-001 value semantics** and **002 read/edit/take**: annotations cannot silently change sharing, ownership or callable access contracts.
- **003A bidirectional typing**: verify uses the existing type checker, with unresolved constraints honestly reported.
- **003B/003C generics/abilities**: no implicit trait or type ability registration from notes.
- **003E closures**: function captures remain governed by typed access; note parsing never synthesises a closure capture.
- **003F effects/host authority**: note preferences cannot grant effects or runtime permission.
- **003G Result/Option/?**: formal runtime validation, when introduced, must use explicit typed error paths, not hidden traps inserted by an advisory note.
- **003H refinement types**: proposed proof obligations can later share this channel, but refinement syntax, proof obligations and solver behaviour are NOT accepted by this proposal.
- **danger** remains explicit and strictly checked; notes are not a substitute for danger contracts.

## Bounded implementation plan (isolated branch; no merge without normal acceptance)
**Slice SN1: Lexical identity and metadata, no semantics.**
- Modify the authoritative OCaml lexer to retain Semantic Note trivia, source span and raw line while preserving the existing token stream and AST/evaluation.
- Attach only to unambiguous preceding top-level declarations; retain ordinary comment text as non-authoritative source context or retrievable spans.
- Emit versioned, bounded read-only note metadata and capability discovery via a scoped extension of the existing inspect/query/session interface. No optimisation changes.
- Verify identical prior check/run outputs for all programs without notes; with notes, runtime outputs and checked executable semantics stay equal to the version without notes.

**Slice SN2: Typed note diagnostics and advisory hints.**
- Validate tag grammar, enum values, attachment and duplicates; add negative tests and clear diagnostics.
- Parse verify predicates using existing Pep expression parser/checker as a strictly pure Bool expression; if not provable, report **unresolved**. Do not introduce a new verifier or accept unsupported expressions as proofs.
- Report prefer hints but do not claim to implement optimiser policy where none exists. If later used, keep semantics-preserving optimisation equivalence tests.

**Slice SN3: Verified obligations (separate acceptance gate).**
- Introduce a deliberately small accepted verifier for simple Bool constants, path facts or integer ranges only **after** defining proof rules and rejection/unknown cases; or delegate to an independently justified verifier with reproducible soundness checks.
- Preserve proof provenance: exact revision, expression, assumptions, verifier version, bounded fuel, status and evidence. For formal preconditions, separately specify call-site proof vs runtime checked conversion; do not silently assume an arbitrary caller satisfies a verify note.
- Expose small, targeted queries for agents: list notes, ask why unresolved, locate dependent source, propose a checked edit. Proposals are source revisions, not unreviewed semantic mutations.

SN3 can be deferred without blocking SN1/SN2. Defer modules, arbitrary expression attachment, multiline text, user-defined annotation macros, general theorem proving, persistence service and untrusted third-party extension execution.

## Acceptance tests (minimum)
- LF/CRLF/UTF-8 original-byte offsets, Unicode prose and exact stale-revision rejection.
- Ordinary # and // comments remain untouched; #@ appearing inside strings is never a note.
- Same code with and without notes has identical parse/check/run semantics and outputs, aside from additive note metadata/diagnostics.
- Note attaches to correct function/type, and fails safely for orphan/ambiguous placement.
- Unknown and duplicated tags, bad enum values, malformed/impure/non-Bool verify expressions produce structured diagnostics.
- Unproved, false, timeout or unsupported assertions **never** enter optimiser trusted facts or permissions.
- Unrelated source edits invalidate proof receipts in SN3 until rechecked.
- Tool/query responses include schema/capability, bounded sizes, UTF-8 byte spans, exact revision and actual status.
- All prior interpreter/session/tool protocols and conformance suites remain green; no changed acceptance pointers or claims that the C23 backend exists.

## Scope/status
The **three-layer design intention is accepted by Matthew**; the exact #@ grammar, three tags and phased implementation above are **this proposed engineering design** and have not yet been accepted through a compiler milestone. This document should enter review as a draft in an isolated branch. It must not change CURRENT.md, manifest.json, master or ongoing A11/A12/A13 accepted/working branches.

**Success:** a human or AI can read one .pep source file and query three clearly classified kinds of information; the compiler derives or proves only what its checked semantics justify. Removing the optional Semantic Notes changes no executable meaning.
