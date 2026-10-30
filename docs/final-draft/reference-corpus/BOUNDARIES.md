# Pepin reference corpus: boundaries, conflicts, and executable-spec gates

These design fixtures exercise the **intended next specification**. They do not override the accepted 27 October language draft or current implementation authority.

## Design amendments requiring explicit reconciliation

| Topic | Accepted 27 Oct draft | 30 Oct proposal | Decision gate |
|---|---|---|---|
| Imports | import module | use module | Keyword versioning, aliases, path rules |
| Error propagation | postfix ? | prefix try | Precedence, evaluation order, diagnostics, compatibility |
| Block returns | explicit return examples, some statement/expression distinctions not fully specified | last expression produces value | Newline/semicolon handling, Never, Unit, branch joins |
| Generic behaviour | compiler-known abilities + explicit typed function records (DEC-003C/D) | user-defined ability + one canonical impl; alternative behaviours explicit | Coherence, local ownership/orphan rule, derives, shared dictionary lowering |
| Async task result | structured scope accepted, exact type unbound | await Task[T,E] -> Result[T,task.Error[E]] | cancellation, panics/traps, aggregation, nested tasks |
| Resource cleanup | owned handles and explicit free accepted, fallible cleanup order open | explicit typed close or scoped helper, preserve cleanup failure | body + close error composition, cancellation and trap |
| Refinement declarations | constrained fragments accepted, grammar provisional | type Port = Int where ... and Port.check(value) | solver bounds, overflow, runtime check vocabulary |
| Numeric literals | Int/Float/Float32/Byte design accepted; suffixes pending | contextual Byte literal in memory.write | explicit literal ranges and no implicit conversion |
| Qualified names | qualified imports accepted, exact spelling pending | http.Method.Get and call via module alias | Name grammar, constructors, type namespaces |

## Grammar gates

G1: precedence and unary \`try\`: \`try f(x)\` must apply to full postfix call; parenthesise \`try (a + b)\` when needed.

G2: newlines and final expressions: distinguish adjacent expression statements, explicit semicolon, and final tail without hidden leading-dot continuation. A block ending in let/assignment/loop produces Unit. A function returning non-Unit must have a compatible return on all completing paths.

G3: if-without-else = Unit, if-with-else compatible typed branches, Never from explicit return, exhaustive match, Bool-only condition.

G4: typed holes \`?name\` and \`try\` are lexically distinct. Source snapshots retain exact UTF-8 bytes and original line endings.

G5: typed record, tagged unions, derived abilities, function type and closure captures all have source-spanned AST and checked-tree contracts.

## Safety gates

S1: canonical ability selection never changes due to unrelated import; rejection of duplicate/orphan implementations; exact caller-visible dictionary selection where alternative strategy provided.

S2: values have independent logical semantics; edit is exclusive; take invalidates owner; region/COW/GC choices are observationally safe; lifetime inferred or rejected, not assumed.

S3: safe allocator operations preserve allocator identity; no use-after-free; fallible cleanup cannot be silently dropped, including during error/cancellation. \`danger\` trusts only explicit low-level obligations and never grants authority.

S4: tasks cannot escape structured ownership; all children joined/drained; clear failure and cancellation categories; never claim data-race freedom implies deterministic ordering or deadline freedom.

S5: exported effect ceilings are transitively checked; host authority independently enforced; refinement facts proved/refuted/unknown with bounded verification and mutation invalidation.

## AI-native acceptance gates

A1: semantic query for every public source symbol yields exact identity, revision, type, effects, ability implementation, proof status and source spans.

A2: compile-time failure gives a compact cause, affected constraint, original byte span, and checker-supported remediation (not a speculative text guess).

A3: changing parse() from Document to Result[Document,ParseError] yields a revision-bound impact query of affected callers and obligations, plus a preview that refuses stale revisions.

A4: application of a semantic edit is atomic on its preconditions, preserves untouched UTF-8 bytes, and emits evidence. A model suggestion is not evidence of correctness.

A5: independent adversarial replay and interpreter/native differential checks cover named fixtures; compiler reports which abilities exist **now**, not future design intent.

## Binding open questions

1. Should \`task.Error[E]\` be a tagged union with Job(E), Cancelled, Fault(...) and Cleanup(...), or is a separate typed aggregate report needed? Prevent lossy failure suppression.
2. Are \`ability\` implementations limited to a nominal type's owner package? If yes, what is the canonical primitive ability set and ergonomic handling for foreign types?
3. How does \`try\` bind relative to unary, function call, \`await\`, and the final block result?
4. Which operations may enter \`danger\` in a whole-module region, and what precisely is a host-granted low-level resource capability?
5. How can fallible cleanup be made both deterministic and non-blocking inside real-time/cancelled scopes?
6. Which numeric literal spellings are legal and exactly how are negative minimum signed values and floating-point NaN represented?
7. What is the exact interface and error of \`map.put\`, \`memory.free\`, \`http.serve\`, and \`task\`?
8. How do pure module constants initialise with no effectful import-time execution, and how do opaque exported types hide representation?

**Freeze criterion:** resolve this matrix with explicit normative source/type/runtime rules and valid/invalid/incomplete fixtures; do not silently accept new constructs merely because they appear in one proposed example.

**Ownership:** documents only; no active agents' compiler files, master, CURRENT.md, manifest, accepted milestone or source code changed by this suite.
