# A7: Typed compiler semantics exposed to Pep
**Status: READY.** Next authorised phase in the already-scoped A6–A8 campaign, following accepted and published A6.

## Objective
Enable an authorised Pep function to inspect a target program's **compiler-resolved function declarations and call graph** without scanning source text or receiving a mutable AST.

## Architecture and work
1. Specify immutable, monomorphic semantic Pep types equivalent to **FunctionInfo** (revision-local resolved ID, name, declaration original-byte span), **CallEdge** (resolved caller/callee IDs), **ProgramInfo** (document, source revision, List[FunctionInfo], List[CallEdge], List[root IDs]). Choose exact syntax after inspecting A6. These are typed values, not untyped JSON or host pointer handles.
2. Implement read-only host-mediated **semantic.snapshot()** (or equally minimal signature) that constructs those values from the checker-owned representation. Do not add special builtins that directly calculate the linter answer. Existing parser, resolver and checker remain the only semantic authority.
3. Separate **tool implementation revision** from **target program revision**. Tool invocation must carry an explicit host-authorised target identity and exact retained revision, validated by the session. A tool cannot forge another document or mutate snapshots by stringifying a guessed ID. Reject denied, nonexistent and unauthorised access; document semantics for querying *retained historical* vs requiring current revision.
4. Root policy: actual checker-resolved top-level function calls, plus explicit host-supplied entry functions resolved by checker identity. Unknown/ambiguous roots fail. Do not infer public exports where Pep has none. Disconnected recursion is not a root. Empty roots must be labelled as a policy choice, not evidence that all functions are useless.
5. Extract edges by traversing *resolved calls* in typed function bodies and checked top-level statements; ignore constructor invocations, builtins and name lookalikes. Incomplete source can expose correctly flagged partial information but not definitive unreachable-function judgments; invalid source produces explicit diagnostics.
6. A5 tool protocol v1 accepts scalar values only. Define a **versioned v2 typed transport** for List and monomorphic record combinations, with exact signed 64-bit Int strings, checked fields/order/types, bounded nesting, elements, response bytes and host work. Preserve compatibility with scalar v1. Prevent huge semantic snapshots or serialisation from bypassing interpreter budgets or corrupting JSONL output.
7. Keep registration-derived signatures, real validation, explicit activation, no transitive say, local-host trust and rollback guarantees. A read grant is host enforced, not an annotation accepted from the tool itself.

## Test scenario
In one real session open tool source and separate target source. Target contains entry→helper and orphan_a↔orphan_b. Invoke an ordinary Pep semantic consumer tool with permission to inspect the target: it iterates List values returned by the host and returns a typed structured summary. Show correct call IDs/spans and root identities, no text-based edges. Edit the target; explicitly query both new and prior revision and prove they remain distinct. Tool source revision does not change.

## Acceptance
- Resolved call graph handles recursion, forward calls, nested expressions, shadowing, matches, constructors and top-level roots without guessed name matches.
- Wrong/forged/denied target, invalid source, stale-as-current request, malformed protocol, unsupported version, wrong structured type, oversize and overly deep value rejected with well-formed JSONL; no unintended mutation.
- v1 scalar tools remain fully operational; v2 roundtrips structured Pep values with exact integer precision and correct constraints.
- Deterministic semantic data for identical revisions, accurate original UTF-8 spans under LF/CRLF and historical snapshot stability; bounded work and read-only facts verified.

## Non-scope
Exposing arbitrary AST references, untyped host reflection, a parallel resolver, general permissions service, arbitrary IO, LSP or incremental compiler.

## Shared engineering contract
Read [founding design](../FOUNDING_DESIGN_v0.3.md), [TR001](../TECHNICAL_RESOLUTION_001.md), [TR002](../TECHNICAL_RESOLUTION_002.md), [implementation status](../DESIGN.md), [session protocol](../SESSION_PROTOCOL.md) and AGENTS.md before changing code. The latest accepted rules override speculative examples. **TR002 replaces the planned C11 generator with a Pep-written C23 generator** (Clang primary, GCC independent verification). Historical MoonBit C11 stays historical.

One compiler-owned syntax/type/scope authority. Preserve bidirectional typing, valid/incomplete/invalid, typed holes, exact original UTF-8 byte spans, LF/CRLF, immutable revisioned snapshots, checked editing and deterministic versioned JSON. The A5 tool host is **trusted local, not a security sandbox**: no ambient IO or process access, runtime budgets, transitive say denial and activation rollback must remain enforced.

Use focused checks while coding; at phase gate run clean OCaml build and full Windows CLI suite, with OCaml/MoonBit counts separate, plus real JSONL tests, negative/adversarial cases, git diff --check, secret/local-path review. Publish one coherent verified phase to public master without force-pushing or disturbing unrelated work; record public SHA, evidence, limitations and decisions. Only advance CURRENT after verified acceptance. Escalate semantic conflict, destructive work, material new dependencies or security/acceptance blockers, not routine reversible details.

## Receipt
Publish SHA, documented v2 message shape, exact Pep semantic type signatures, positive and denied sample, counts and measurable bounds. Advance CURRENT to A8 only after acceptance.
