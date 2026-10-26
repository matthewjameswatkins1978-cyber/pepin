# A6: Typed collections and practical control flow
**Status: COMPLETED.** Accepted and published as `4d3bceff7be0f013d08310cf8e75eb5a1f365556`; see the [A6 acceptance record](archive/A6-ACCEPTANCE-RECORD.md).

## Objective
Make ordinary Pep able to traverse and construct typed sequences and implement graph algorithms. Preserve small, explicit semantics; add no user-defined generics or mutable container aliases.

## Implementation contract
1. Compiler-known **List[T]**, supporting scalar, record, variant and nested list elements; homogeneous list literals and contextual checking. Nonempty literals synthesize List[T]. Empty list requires an expected element type: an unconstrained empty literal reports a diagnostic instead of inventing T. Propagate type into ?holes in list elements.
2. **Immutable lists**: append yields a new List; original aliases unchanged. Provide checked length, append and membership primitives. Choose the smallest coherent builtin naming compatible with existing grammar; avoid a general module system merely for dotted operation names. Membership only for types with explicitly defined equality. Define observable ordering/complexity and resource accounting.
3. **var** and assignment: only var can be rebound; type stays fixed and lexical binding identity resolves in the existing checker. let remains immutable. Mutable variable binding does not imply mutable List storage. Test shadowing, nested assignment, unknown bindings and wrong types.
4. **for-in** over List, **while** with Bool condition, and multi-statement conditional blocks, preserving the existing if *expression* meaning. Collection evaluated once for for-in; while condition reevaluated. Loop variable immutable and scoped to loop. Clarify return-flow checking and termination semantics.
5. Exact scalar **==, !=, !, &&, ||** with Bool-only conditions and short-circuiting. No implicit truthiness or arbitrary equality on recursive data. Define checked evaluator operations and clear invalid diagnostics.
6. Extend source-spanned AST, checked tree, lexical resolver, interpreter, describe, JSON inspection, and hole queries coherently. Account for loop iterations, collection work and allocation under runtime limits, including tool invocation.

## Required runnable example
~~~pep
fn sum(values: List[Int]) -> Int {
    var total = 0
    for value in values {
        total = total + value
    }
    return total
}
say(int_text(sum([10, 12, 20])))
~~~
Expect 42. This spelling is a target contract; any syntax adjustment must be justified and documented with equivalent proof, not silently changed.

Additional runnable demonstrations: a List of user records; a List of recursive variants; nested List[List[Int]]; original/append immutability; annotated empty list; ?missing within List[Int] has expected Int; a scoped mutable loop accumulator; short-circuit preventing a checked division-by-zero.

## Negative / adversarial acceptance
- Mixed types, underconstrained empty list, wrong append argument, unsupported membership equality; assignment to let/unknown binding/wrong type; loop name escape; non-Bool condition; unbounded while hits interpreter budget without hanging.
- Typed holes inside loops/lists; ambiguous if grammar regression; recursion, match, records, variants and pattern scopes; UTF-8/LF/CRLF offsets; no change in existing v1 tool semantics.
- Interpreter and checker agree on resolved identities. Complete valid programs run, incomplete programs never run, invalid programs return structured errors. No runtime budget bypass through bulk builtin.

## Non-scope
User-defined generics, dynamic reflection, Map, modules, arbitrary host capabilities, native backend, incremental cross-revision analysis, general reference cells.

## Shared engineering contract
Read [founding design](../FOUNDING_DESIGN_v0.3.md), [TR001](../TECHNICAL_RESOLUTION_001.md), [TR002](../TECHNICAL_RESOLUTION_002.md), [implementation status](../DESIGN.md), [session protocol](../SESSION_PROTOCOL.md) and AGENTS.md before changing code. The latest accepted rules override speculative examples. **TR002 replaces the planned C11 generator with a Pep-written C23 generator** (Clang primary, GCC independent verification). Historical MoonBit C11 stays historical.

One compiler-owned syntax/type/scope authority. Preserve bidirectional typing, valid/incomplete/invalid, typed holes, exact original UTF-8 byte spans, LF/CRLF, immutable revisioned snapshots, checked editing and deterministic versioned JSON. The A5 tool host is **trusted local, not a security sandbox**: no ambient IO or process access, runtime budgets, transitive say denial and activation rollback must remain enforced.

Use focused checks while coding; at phase gate run clean OCaml build and full Windows CLI suite, with OCaml/MoonBit counts separate, plus real JSONL tests, negative/adversarial cases, git diff --check, secret/local-path review. Publish one coherent verified phase to public master without force-pushing or disturbing unrelated work; record public SHA, evidence, limitations and decisions. Only advance CURRENT after verified acceptance. Escalate semantic conflict, destructive work, material new dependencies or security/acceptance blockers, not routine reversible details.

## Receipt
Actual output and diagnostic examples; clean build and separately counted tests; SHA; explicit list/loop and equality rules; limitations. Once accepted and published, update CURRENT and manifest to A7.
