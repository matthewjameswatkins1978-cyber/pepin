# VALUE_COPY_DEC001 — copy independence probes (V0/V1 link)

**Spec (accepted):** final-draft §4 (DEC-001): ordinary data and
collections are independent logical values; a later edit of one copy
must not mutate an earlier logical copy. Applies to `List[T]`,
records, and nested combinations.

**Model link:** `verification/lean4/Verification/ValueCopy.lean`
(`Snap`/`editOrig`, theorems `edit_takes_effect`, `copy_preserved`);
aliased violation in `AliasedCounterexample.lean`. Model status
`DRAFT`/`BLOCKED_SECURITY`; the probes below are `TESTED` on the real
interpreter and constrain the model (any model predicting other
outputs here is wrong).

**Environment:** worktree at base `805062b`,
`./pep.ps1 run <file>` (OCaml seed interpreter only — no C toolchain,
no binary output). A13/C23 columns refer to builder-owned stages and
are `NOT_RUN` by Agent 3 (ownership boundary).

## P1 — flat list: `let`-copy unaffected by derived `append`

```pep
let a = [1, 2, 3]
let b = a
let a2 = append(a, 4)
say(int_text(length(a)))   // 3
say(int_text(length(b)))   // 3
say(int_text(length(a2)))  // 4
```

| oracle | result |
|---|---|
| SPEC | `3 / 3 / 4` |
| OCAML | `TESTED` PASS — observed `3, 3, 4` |
| A13 | `NOT_RUN` (Agent 1 owned; list append already covered by `test_a13.py` list suites) |
| C23 | `BLOCKED_SECURITY` (emitter has no `List` lowering per B0 peerEvidence) |

## P2 — `var` rebinding does not alias the earlier copy

```pep
var a = [1]
let b = a
a = append(a, 2)
say(int_text(length(a)))  // 2
say(int_text(length(b)))  // 1
```

| oracle | result |
|---|---|
| SPEC | `2 / 1` (reassignment rebinds; old binding keeps its value) |
| OCAML | `TESTED` PASS — observed `2, 1` |
| A13 | `NOT_RUN` |
| C23 | `BLOCKED_SECURITY` |

## P3 — nested record list: copy unaffected by derived `append`

```pep
type Point { x: Int y: Int }
let pts = [Point { x: 1, y: 2 }]
let alias = pts
let grown = append(pts, Point { x: 9, y: 9 })
say(int_text(length(alias)))  // 1
say(int_text(length(grown)))  // 2
```

| oracle | result |
|---|---|
| SPEC | `1 / 2` |
| OCAML | `TESTED` PASS — observed `1, 2` |
| A13 | `NOT_RUN` |
| C23 | `BLOCKED_SECURITY` (no record lowering per B0 peerEvidence) |

## Coverage boundary (explicitly unresolved)

- Deep in-place element mutation does not exist in the seed surface
  (no `edit`/index-assign); independence is therefore observed across
  `append`/`var`-rebind only. A `take`/exclusive-edit rule is accepted
  design (DEC-002) but unimplemented — see `NEGATIVE_AND_EDGE.md`.
- No claim is made about C23/Clang/GCC behaviour, CoW runtimes, GC, or
  cross-task sharing. Those stay `BLOCKED_SECURITY`/`UNVERIFIED`.
