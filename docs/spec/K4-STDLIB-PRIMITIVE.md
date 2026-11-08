# K4 — Highest-leverage stdlib primitive: function-result records

Comparison by (exists at 123d8b3) × (real call sites) × (marginal
functions). All A2-surface claims SOURCE-READ at 123d8b3; reachability
consequences INFERRED; execution owned by A3.

## Eliminated candidates

- **str_concat** — REJECTED per A2-032 (zero uses across scan/lexer/
  parser/checker sources, REPORTED). Respected; not proposed.
- **Bounded bytes builder** — EXISTS (`stdlib/text_builder.pep`:
  new/is_empty/bytes/push/push_span). Not missing.
- **SourceBytes params / byte access** — EXISTS (`scan_*_at` take
  SourceBytes; seed builtins `byte_at`/`byte_length`). The remaining
  byte blockers are host grants (`source_bytes()`) and L6 control
  flow, not a missing primitive. Ownership: host, not A2.
- **List params/construction** — EXISTS (ARENA_PROGRAM builds and
  prepends `List[Int]`; `text_builder_parts` returns `List[Str]`).
  List-as-call-arg for records (L4's `stringParts`) is the untested
  composition, not a missing primitive.

## The pick: function-result record construction

RECORD_PROGRAM (bounded suite, green both compilers) proves record
PARAMS (`total(p: Point)`), record LITERALS (`Point {x: 19, y: 23}`),
and record-carrying assemblies. NO fixture has a function RETURNING
a record. The lexer's load-bearing constructors all return records:

- L3 `advance_position` (lexer.pep:90, 3 call sites: 226/241/395):
  `(Int,Int,Int)->SourcePosition`, Int-only, conditional returns.
- L5 `lexer_start` (140): `()->LexCursor`, record literal return.
- L4 `make_token` (113, 7+ call sites): 8 params incl. Str +
  `List[Str]`, returns `LexToken` with Str fields — needs record
  return AND Str-field records AND list-literal args composed.

Marginal gain if it lowers: L3+L5 immediately (pure, tiny closures),
L4 next (composition check) — 3 real lexer functions, ~10 call
sites, unlocking the header path up to L6 (whose residual is
while+mutable-state+grants, i.e. control flow, NOT primitives).

## Program 1 (positive, L3 verbatim shape)

```pep
type SourcePosition { line: Int column: Int }
fn advance_position(line: Int, column: Int, byte: Int) -> SourcePosition {
  if byte == 10 { return SourcePosition { line: line + 1, column: 1 } } else {
    return SourcePosition { line: line, column: column + 1 }
  }
}
fn main() -> Int {
  let p = advance_position(1, 1, 10)
  return p.line * 10 + p.column
}
```

Seed oracle: `11` (line 2, column 1). NOTE the shape: conditional
RETURN of records — F3 refused conditional-return STR bodies. Either
branch of the outcome is decision-useful: lowers → the conditional
rule was Str-specific and L3/L5 are reachable; refuses with the
conditional diagnostic → the ONE rule blocking the lexer header is
named and A2 owns a precise next slice. INFERRED until A3 runs it.

## Program 2 (negative, must refuse)

```pep
type LexToken { kind: Str text: Str line: Int column: Int }
fn make_token(kind: Str, text: Str, line: Int, column: Int) -> LexToken {
  return LexToken { kind: kind, text: 0, line: line, column: column }
}
fn main() -> Int { return 0 }
```

`text: 0` against `text: Str` must refuse (PEP_TYPE_MISMATCH family),
proving a record-return path — if built — reuses the existing
field-type gate rather than laundering. A divergent-shape variant
(different record shapes per conditional branch) must likewise
refuse; that is the composition F3's rule would govern.

## Limits, falsifier, NO-CHANGE

Limits: <1 KB programs, unchanged 100k steps, Clang+GCC + seed
oracle, no baseline suite. Falsifier: A3 guard-read showing L3-shape
already lowers at 123d8b3 (record returns via existing machinery) —
then the primitive EXISTS and this card flips to NO-CHANGE, residual
L6 control-flow. Second falsifier: `str_concat`-class zero-use
finding against record returns — impossible, the 10 call sites above
are read from the lexer source, not assumed.
NO-CHANGE option, stated plainly: if record returns lower without
new code, A2 adds NOTHING and K4 closes with the L6 residual named.
The value of this card is the elimination table either way.
