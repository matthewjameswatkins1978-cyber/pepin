# Pepin Final-Draft Acceptance Matrix
**Companion to:** PEP-LANG-FINAL-DRAFT-2026-10-27.md and IMPLEMENTATION-MISSION.md
**Nature:** Future conformance and release gates, NOT current test results. Accept implementation by evidence per slice, not by number of examples in documentation.

## 0. Test status classes
Every row below is a proposed requirement. **None of these rows implies implementation.**
- **Seed fact:** current behaviour documented in docs/DESIGN.md and proved by actual green test in chosen current commit.
- **Target:** user-approved desired semantic behaviour; design need not be executable yet.
- **Needs contract:** unresolved detail to decide via focused grammar/spec work.
- **Blocked:** dependent feature not shipped or missing trusted boundary.
- **Observed:** test actually run against named revision/toolchain and reported honestly.

Each acceptance receipt must carry: source commit/revision, compiler/runtime version, target platform, test mode, proof status, outcome, compared reference (if any), limitations, failures and exact files/artifacts. No fake counts or inferred CI results.

## 1. Lexing, syntax and source identity

| Gate | Positive tests | Negative/adversarial tests | Required evidence |
| --- | --- | --- | --- |
| LF/CRLF and UTF-8 original spans | Equivalent program in LF/CRLF produces same typed behaviour and correct differing byte offsets; non-ASCII identifier/comment spans | Byte edit splits a multibyte code point; stale revision; mixed newline offsets | Exact source bytes, sha256 revision, diagnostics and untouched-byte comparison |
| Top-level and semicolons | One expression per line, multiline calls/lists/records; optional ; to separate | Ambiguous line continuation and accidental merge of statements | Parser fixtures and one normative precedence/layout table |
| Control | if without else as statement, required else in expression, else-if, exhaustive match, for/while/break/continue | Non-Boolean condition, missing branch value, break outside loop, missing pattern | Checked AST shape and negative diagnostics |
| Operators and holes | ?name or _ partial expression; suffix Result ?; correct right binding | n??, collision with ?typedHole, malformed ? chain, precedence ambiguities | Lexer/token tests, ASTs, incomplete vs invalid distinction |
| Function and export grammar | fn typed signatures, fn values, pub, imports, uses/async/danger/test declarations when accepted | Invalid position, duplicate declarations, unsupported combinations | Grammar fixtures tied to specified compiler/version |
| Semantic Note trivia | Adjacent #@ note attached to intended declaration; normal # comments retained | #@ inside string; orphan/duplicate/malformed/unknown note; LF/CRLF and stale note | Source spans, bounded query response, no runtime semantics change |

## 2. Typing and type constraints

| Gate | Positive tests | Negative/adversarial tests | Required evidence |
| --- | --- | --- | --- |
| Bidirectional checking | Locals infer types; known expected type fills empty collection and hole | Empty [] without known element type; incompatible expected type; silent coercion attempt | Type judgments, source span and explanatory expected type |
| Generics | Named generic functions, records, nested inferred type arguments, recursion | Generic body assumes unbound operation on T; ambiguous instantiation; invalid cross-module instantiation | Independent generic body checking, type soundness assertions |
| Equal/Ordered/Hashable | Derived record equality when all fields valid; Map consistent hash/equality | NaN falsely claimed totally ordered, hash/equality mismatch, imported conflicting behaviour | Declared ability witnesses and honest law evidence; type checker alone cannot prove arbitrary hash law |
| Behaviour as values | Multiple Formatter[Person] dictionaries coexist, explicit selection | Implicit instance imported changes chosen behaviour | Symbol origin in compiler query and stable observable output |
| Closures | Read/default value captures; noncopyable take; local edit with exclusive access; proper call modes | Dangling edit escape, overlapping exclusive borrows, use after take, one-shot called twice | Typed access/capture/escape graph and runtime/differential tests |
| Refinements | Branch establishes Int > 0, source proof honoured; explicit Result validation | Mutation invalidates proof; Int64 overflow invalidates integer proof; unproved assumption treated as axiom | Proof/refutation/unresolved/runtime-validated distinction and checker rules |

## 3. Data, text and numeric guarantees

| Gate | Positive tests | Negative/adversarial tests | Required evidence |
| --- | --- | --- | --- |
| Independent collection values | Copy list/map, modify one, original unchanged; in-place safe optimisation equivalence | Aliased physical storage silently mutates other logical value | Differential tests across interpreter/backend and mutation patterns |
| Index and Option | In-bounds read, statically eliminated check, get missing returns Option | Out-of-bounds read, negative index, Int overflow in offset calc | Checked failure or explicit absence, no memory corruption |
| Unicode | UTF-8 round trip, scalar iteration, grapheme clusters for combining marks/emoji | Illegal UTF-8 treated as Str; byte offset confused with scalar index | Documented Unicode version and text API conformance |
| Map deterministic order | Insert/update/delete/reinsert and iteration order | Hash-map random iteration leaks into observable order | Same output on Windows/macOS/Linux and backend comparison |
| Float and conversions | Float32/Float64 correct rounding, explicit conversions | Silent lossy conversion, NaN ordering, signed zero and infinity bugs | Reference numerical cases and full specified edge table |
| Bool/Int | checked Int64 overflow and divide-by-zero reports | Overflow undetected under C23 optimisation, branch type inconsistency | Interpreter/native differential tests with strict flags |

## 4. Modules and API contracts

- File-to-module identity stable with canonical project-root resolution and cross-platform case behavior. Explicit qualified import / alias works.
- Import cycles produce a deterministic diagnostic and dependency cycle evidence.
- Private fields and internal declarations are inaccessible externally. Public opaque types expose only allowed operations; no separate manually stale interface file.
- Imported modules do not execute hidden effects. Entry-file top-level statements run only under an explicit selected entry context.
- Module query reports checked public types, parameter modes, generics, effects, errors, source revision and availability. Incremental reuse never gives stale dependent module interfaces.
- Same logical dependency manifest/lock yields reproducible selection across target platforms. External fetching requires explicit host authority.

## 5. Errors, effects, authority and runtime restrictions

- Result/Option are typed tagged unions; postfix ? returns compatible E on error, unwraps T on success, exact error translation explicit.
- Ordinary unexamined Result is diagnosed unless explicitly acknowledged. Tests show suppression cannot hide an effect or pointer safety failure.
- Public effect ceiling rejects calls introducing undeclared effects through a closure, helper or generic instantiation.
- Declaring uses fs.read never authorises an actual file read. Test with revoked host grant, denied paths, and outside-grant attempts.
- Test that compiler's claim of pure/no_external_effects does not silently imply no allocation, no blocking, total termination or deterministic scheduling.
- In a restricted real-time callback, transitive no-alloc/no-GC/no-blocking restrictions must hold; failure produces a trace to actual offending call. No blanket claim of worst-case timing proof.

## 6. Memory, danger and concurrency: must be adversarial

| Claim | Attack scenario | Expected outcome |
| --- | --- | --- |
| Manual ownership safe | Free twice, use after take, free through wrong allocator, leak after scoped exit | Statically refused if represented as safe operations; explicit runtime failure only where the contract defines it |
| Mixed memory strategies safe | GC reference stored in arena and arena pointer leaked to long-lived graph; cycles and roots across domains | Reject/retain/trace safely under proof and runtime design; no dangling references |
| Raw danger is scoped | Code performs invalid alignment/bounds/lifetime inside danger; safely callable wrapper hides unproved contract | Diagnose checkable violations and surface explicit auditable trust obligations; never quietly call unsafe proof complete |
| Foreign hardware lifetime safe | GPU command canceled after buffer submit; driver stalls, returns early or device lost | Resource remains owned/supervised through real completion or explicit failure protocol |
| RT restrictions hold | Allocator, GC trigger or destructor hidden through generic/closure/FFI call | Compile-time rejection unless declared safe and verified under supported model |
| Isolation across tasks | Transfer graph containing aliased mutable handles, nested edit closure or shared region | Reject unless isolated/synchronised contract covers entire reachable graph |
| Cancellation safe | Nested child fails while sibling owns memory or I/O; parent scope exits; unknown foreign work status | Typed observable child result, supervised closure and no premature release |
| Test outcomes honest | Crash, timeout, denied permission, missing evidence | Run status distinct from assertion/oracle verdict; no fake PASS/PROVEN |

**A Git worktree alone is not containment.** Red-team tests with untrusted code require appropriate process/OS-level restrictions and credential protection, not only a disposable source directory.

## 7. Semantic Notes and compiler query contracts

- intent appears as *untrusted descriptive text*; prefer as *advisory*; verify creates *verification request* (unresolved unless checked), not an optimiser axiom.
- Proof receipt bound to source revision/checker, exact proposition, assumptions, result and method. A modified source invalidates stale proof evidence unless a proven dependency rule justifies reuse.
- An AI editing a function may query the smallest necessary information: types, module signatures, effects, holes, caller/callee relations, invariants, test names and evidence. Responses remain bounded and revision-specific.
- No required language-server service, cloud database or LLM for the deterministic operations; capability introspection reports unsupported operations honestly.
- Structural edit preview preserves every untouched byte and refuses stale/ambiguous target; editing never implies human acceptance.

## 8. Built-in testing and Terror Bats integration

**Phase A:** compiler-registered tests and std.test assertion functions, pep test --json, test selection, execution failures with line/spans and exact source revision.

**Phase B:** stable replayable receipts: input/seed, source/compiler, environment/capabilities (requested/granted/enforced vs merely declared), execution outcome, assertion/oracle judgment, evidence links, limits and reproduction command.

**Phase C:** property testing with recorded seeds, bounded shrinking and branch/boundary generation, no inferred correctness from random samples.

**Phase D:** optional adapter to The Terror Bats framework, capable of testing a Pep program or CLI from an independent experiment runner. Its trial-specific PROVEN finding is **falsification**, NOT a proof that a program is correct. NOT OBSERVED means this attack did not find a violation. Timeout/crash generally leads to inconclusive unless deterministic oracle evidence justifies a specific claim.

**Test hostile conditions:** stale revision receipt, counterfeit result/evidence, non-reproducible random test, prompt-injected comments, hidden external effect in test runner, escaped subprocess, false containment claim, passing tests plus altered protected file, incomplete evidence file.

## 9. Standard library and self-hosting check

Build useful Pep-written facilities in evidence-backed order: generic functions / data, text and bytes, JSON, fs/path, testing, semantic inspection, memory and tasks. Every stdlib function provides inspectable accurate typed contract/effects/errors/platform and runnable examples. Instrument how much host-only compiler intrinsic code remains.

For self-hosting: Pep source compiler builds a working Pep compiler that can compile itself again without OCaml as a normal build dependency; document external C23 toolchain/runtime explicitly. Native C23 backend must pass Clang primary and GCC independent verification, with differential results under the interpreter reference. No "self-hosted" or "native supported" label before this is demonstrated.

## 10. Failure criteria and stop conditions

Do NOT accept a feature if:
- It relies on assumed evidence/handwritten mock oracle instead of executing real compiler paths.
- It silently changes meaning of existing Pep programs or the user-approved value/access/error model.
- It makes unverified AI-authored Semantic Notes usable as trust, permission or optimiser facts.
- It bypasses active/current packet authority, merges from a worker without acceptance, or overwrites another branch.
- It claims deterministic concurrency scheduling, automatic security sandboxing, data-race safety through only shallow alias checks, or sound raw-memory safety without tested trusted contracts.
- It reports generic "all tests passed" without exact revision, actual counts, tests performed and limitations.

## 11. Review and publication
- Keep scope small: targeted tests after each coherent slice, independent adversarial review after three coherent slices, full interpreter/native/memory/effects conformance at release-significant integration points.
- Feature branch commits and pushes are visibility checkpoints, never auto-merges or needless human interrupts.
- Evidence expected: repo, branch, SHA, compiler/version, actual tests and count, new feature supported vs unsupported, inspectable failures, unresolved contradictions, next gate.
- Distinguish "reviewer recommended" from "human accepted". Any new language-visible semantic decision belongs in the accepted-design record.

**This matrix defines tests to BUILD and RUN in authorised implementation slices. It is not a claim these tests already exist or pass.**
