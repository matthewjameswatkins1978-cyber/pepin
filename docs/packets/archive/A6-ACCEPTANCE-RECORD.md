# A6 acceptance record: typed collections and control flow

**Status:** accepted and published.

- Base inspected: `06e901b274d627a40256a78f4e5f5f1c8b111b94`
- A6 implementation commit: [`4d3bceff7be0f013d08310cf8e75eb5a1f365556`](https://github.com/matthewjameswatkins1978-cyber/pepin/commit/4d3bceff7be0f013d08310cf8e75eb5a1f365556)
- Published branch: `master`; remote `refs/heads/master` matched the commit exactly.
- Public files checked at the commit returned HTTP 200: `pep_ocaml.ml`, `examples/a6_collections_control.pep`, `tests/test_a6.py`, and `docs/DESIGN.md`.

## Acceptance evidence

- The Windows CLI launcher compiled the changed compiler with the Pepin OCaml 5.5.2 switch and returned valid `describe --json` output.
- `python -m unittest discover -s tests -v`: **67/67 passed**. This is 56 OCaml CLI tests (45 existing plus 11 A6 tests) and 11 historical MoonBit CLI tests. The A6 cases cover typed and nested lists, empty-list context, list holes, record and recursive-variant collections, append immutability, scalar membership and equality, short-circuiting, mutable assignment, scopes, branch return analysis, runtime budgets, and new control-flow paths in tool validation.
- The existing suite's revision-bound JSONL, exact UTF-8 byte offsets, LF/CRLF behavior, and A5 tool protocol tests all passed.
- `git diff --check` passed. Review found no machine-specific paths or credential-like strings in the published files.
- Running `examples/a6_collections_control.pep` printed, in order: `42`, `0`, `1`, `17`, `22`, `10`, `0`, `1`, `42`.

## Binding A6 behavior

- `List[T]` is compiler-known, ordered, immutable storage. Literals are homogeneous; an empty list needs a contextual element type. Expected element types flow into holes. There are no user-defined generics.
- `length`, `append`, and `contains` are O(n). `contains` visits elements in order and stops at the first equal scalar. `append` returns a new list and preserves its input. Lists do not gain recursive structural equality; membership is limited to `Int`, `Bool`, `Str`, and `Unit`.
- List construction and copying, traversal, membership comparisons, and loop iterations consume execution steps. The CLI budget is 1,000,000 steps and 512 call depth. Trusted-local tool execution remains capped at 100,000 steps and 128 call depth; the tool message boundary remains scalar-only, and call analysis now traverses A6 expressions and statements.
- `let` remains immutable. `var` can be rebound only at its checked type. `for-in` evaluates its list once and binds an immutable loop variable scoped to the loop. `while` reevaluates a Bool condition. Statement `if` requires both branches to return before the checker treats following code as unreachable; loops do not guarantee return.
- `==`, `!=`, `!`, `&&`, and `||` use exact scalar/Bool typing. `&&` and `||` short-circuit.

## Boundary and next phase

No native backend, Pep-written C23 generator, self-hosting compiler, modules, maps, or user-defined generic containers were added. Technical Resolution 002 remains authoritative: a future Pep-written C23 generator uses Clang as primary and GCC for independent verification; the OCaml interpreter remains the current semantic authority. A7 is the next already-scoped phase; A8 remains queued behind it, and A9–A15 remain provisional.