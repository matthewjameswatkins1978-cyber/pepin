# Next packet: Structured values and pattern matching (A4)

A3 added revision-bound semantic filling of one named typed hole. This packet grows Pep's ordinary language with the smallest coherent data model needed to write recursive algorithms and semantic tools in Pep itself.

## Objective

Implement monomorphic records, recursive tagged unions, and expression-level pattern matching through the existing lexer, parser, checker, checked tree, JSON inspection, hole-query model, and interpreter. The same compiler remains the only semantic authority.

## Required language forms

Records:

```pep
type Point {
    x: Int
    y: Int
}

let p = Point { x: 20, y: 22 }
say(int_text(p.x + p.y))
```

Tagged unions and recursive values:

```pep
type Expr = Number(Int) | Add(Expr, Expr)

fn evaluate(expr: Expr) -> Int {
    return match expr {
        Number(n) => n
        Add(a, b) => evaluate(a) + evaluate(b)
    }
}
```

## Semantics and limits

- Record declarations have named, explicitly typed, immutable fields. Check construction field names, duplicates, missing fields, and field value types statically.
- Tagged unions have named constructors, statically checked arity and argument types, and recursive definitions without recursive allocation.
- Match is an expression. Support constructor patterns, nested patterns, pattern-bound variables, and `_` wildcard patterns.
- Check match-arm result types, duplicate/unreachable arms, and exhaustiveness for the declared variants. Pattern `_` is distinct from Pep's expression hole syntax.
- Preserve checked declaration identities and spans through inspection and evaluation; the runtime must not repeat name resolution by string lookup.
- Holes inside arms inherit a determinable expected result type and expose only bindings in their arm's lexical scope.
- Values are immutable. Do not add field mutation, lists, maps, classes, general user-defined generics, traits, macros, reflection, or a native backend.

## Acceptance

- A record construction and field-access example evaluates to `42`.
- A recursive `Expr`/`evaluate` example with `Number(20)` and `Number(22)` evaluates to `42`.
- A match example with typed holes returns `Int` expectations and arm-local bindings (`n: Int` or `a: Expr`, `b: Expr`).
- Negative tests cover malformed declarations, missing/duplicate/unknown fields, wrong types, unknown constructors, arity and constructor argument errors, non-exhaustive and duplicate/unreachable arms, branch type mismatch, and pattern-binding scope.
- Deterministic AST and typed-tree JSON preserve Unicode, original UTF-8 offsets, LF/CRLF semantics, and existing incomplete/invalid/complete distinctions.
- Existing OCaml and MoonBit suites pass. No incomplete program executes.

## Boundary

Do not start A5 until records, recursive variants, match checking, hole queries, and interpreter evaluation pass this gate. Keep the A3 structural edit and its revision protocol intact. The A5 tool registry will expose only scalar arguments and results; records and variants remain internal until a separate message contract is designed.
