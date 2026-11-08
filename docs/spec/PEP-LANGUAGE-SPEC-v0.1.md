# Pep Language Specification v0.1 — Normative Core

- **Status:** normative for the accepted seed core only. Every rule below is grounded in
  the OCaml seed (`pep_ocaml.ml`) at campaign base `57fe424af4` and verified by reading
  that source; `describe --json` output was additionally executed live at that HEAD.
- **Scope boundary:** this document specifies *only* what the seed implements. Anything
  the seed does not implement (generics, modules, effects, `Result`/`Option`, closures,
  concurrency, `danger`, tests, user syntax extensions) is **not** part of Pep v0.1 and
  lives in `PEPIN-1.0-DECISION-REGISTER.md`. Proposed draft spellings that do not parse
  in the seed are not conforming Pep v0.1 programs.
- **Conformance language:** "MUST" states a requirement on conforming implementations;
  "rejected with `CODE`" states the observable diagnostic contract of the seed.
  Behaviour verified by executing the seed is marked **[executed]**; behaviour read from
  seed source but not executed here is marked **[source-read]**.
- **Provenance:** seed type/lexer/parser/checker/interpreter definitions in
  `pep_ocaml.ml` (2,005 lines at base); seed tests under `tests/test_*.py`;
  `docs/DESIGN.md` / `docs/SEED_LANGUAGE.md` used only as cross-references, never as
  authority where they differ from the source.

## 1. Program states

A Pep source unit is in exactly one state:

1. **Valid and complete** — parses, checks with no errors and no holes. Only such
   programs may execute.
2. **Incomplete** — parses and checks, but at least one typed hole remains. The
   checker reports the program as incomplete; `check` exits nonzero **[executed]**;
   `run` refuses execution **even when every hole is in an unused function**
   **[source-read]**.
3. **Invalid** — fails to parse or check. The checker reports the **first** error only;
   it does not accumulate multiple independent diagnostics **[source-read]**.
   Execution is refused.

## 2. Source text, comments, line endings, spans

1. Source files are plaintext; `.pep` is the canonical extension. The seed rejects
   invalid UTF-8 with `PEP_INVALID_UTF8` before lexing **[source-read]**.
2. Two comment forms begin a comment running to end of line: `#` and `//`
   **[source-read]**. Comments carry no semantic meaning in v0.1.
3. LF and CRLF both denote one line break for line/column reporting. All spans use
   **byte offsets into the original unnormalized source**: `{offset, line, column}`
   starts and an `endOffset`; CRLF occupies two bytes **[source-read]**.
4. Newlines are otherwise insignificant whitespace. There is **no** newline-sensitive
   statement separation in v0.1: statements end by grammar (`;` is optional after
   `let`/`var`/`return`/assignment/expression statements), not by line breaks
   **[source-read]**. The single line-sensitive rule is §5.4 (record literals).

## 3. Lexical rules

### 3.1 Tokens

| Token | Lexical form |
|---|---|
| Identifiers/keywords | `[A-Za-z_][A-Za-z0-9_]*`; `_` alone is an anonymous hole, not an identifier |
| Integer literals | ASCII decimal digits; out-of-`Int64` range rejected with `PEP_INT_LITERAL_RANGE` |
| String literals | `"..."`; escapes `\\n \\r \\t \\0 \\\\ \\"` only — anything else is `PEP_INVALID_ESCAPE`; a raw newline inside is `PEP_NEWLINE_IN_STRING`; unterminated is `PEP_UNTERMINATED_STRING` |
| Holes | `?name` (named, `name` = identifier chars), `?` or `_` (anonymous) |
| Multi-char symbols | `<=  ==  !=  &&  \|\|  ->  =>` |
| Single-char symbols | `( ) { } [ ] , : ; + - * / = . \| & !` |
| Keywords (reserved by position) | `fn type let var return if else match while for in true false` |

Any other character (including `<`, `>`, `%` as single characters) is rejected with
`PEP_UNEXPECTED_CHARACTER` **[source-read]**. Consequences stated normatively: v0.1 has
**no** `<`, `>`, `>=`, and **no** `%` operator; the only comparison operator is `<=`.

### 3.2 Types in source

`Int | Bool | Str | SourceBytes | Unit | Named | List[T]` where `T` is a full type.
`SourceBytes` names the opaque byte-string value produced only by the tool/session
boundary (§9); ordinary source cannot construct one. `Named` is a user-declared record
or union name. There are no type parameters, no `Option`, no `Result` in v0.1.

## 4. Values and evaluation

### 4.1 Values

`Int` is a checked signed 64-bit integer. `Bool` is true/false. `Str` is text.
`Unit` is the no-value result. Records, tagged-union values and immutable `List`
values complete the value domain. `SourceBytes` values exist at runtime but are
opaque to ordinary code (see §9).

### 4.2 Arithmetic and runtime failures

`+ - * /` take `Int` operands and yield `Int`. Unary `-x` is `0 - x`.
The following are **checked runtime failures**, reported with source span, never
silent wrap-around or signals **[source-read]**:

| Condition | Diagnostic |
|---|---|
| `+`, `-`, `*` overflow; unary negation of `Int64.min_int`; `Int64.min_int / -1` | `PEP_RUNTIME_OVERFLOW` |
| Division by zero | `PEP_RUNTIME_DIVISION_BY_ZERO` |

Integer division is `Int64.div` (truncation toward zero) **[source-read]**.

### 4.3 Execution budgets

CLI execution: at most 1,000,000 steps and 512 call depth **[executed]** (also in
`describe.runtime`). Loop iterations, list construction/traversal/copying, membership
scans and appends all consume step budget; exceeding it ends execution with a
controlled diagnostic instead of hanging (seed test: unbounded `while` stops at the
budget) **[source-read + tested]**. Tool-host execution is separately bounded at
100,000 steps / 128 call depth with `say` denied (`PEP_RUNTIME_TOOL_EFFECT`)
**[source-read]**.

### 4.4 Effects visible in v0.1

The only observable effect is `say(Str) -> Unit`, which writes the text plus a
newline to standard output **[source-read]**. `int_text(Int) -> Str` renders an
integer decimally. Both are monomorphic and reserved: no function, constructor or
type may reuse the names `say int_text length append prepend reverse contains
byte_length byte_at byte_slice utf8_slice semantic_snapshot source_bytes`
(`PEP_RESERVED_FUNCTION` / `PEP_RESERVED_CONSTRUCTOR`) **[source-read]**.

## 5. Declarations and statements

### 5.1 Functions

```pep
fn name(param: Type, ...) -> Type { statements }
```

- Parameter and result types are mandatory and explicit. Zero parameters is written
  `()`. The body MUST be a braced block (`PEP_FUNCTION_BODY` otherwise).
- Recursion and forward references resolve: signatures are collected before bodies
  are checked **[source-read + tested]**.
- A non-`Unit` function MUST return on every path; otherwise `PEP_MISSING_RETURN`
  carrying the expected type **[source-read + tested]**. Any statement after an
  unconditional `return` is rejected with `PEP_UNREACHABLE` **[source-read + tested]**.
- `return` outside a function is rejected with `PEP_RETURN_OUTSIDE_FUNCTION`.
- Duplicate function names are rejected (`PEP_DUPLICATE_FUNCTION`); duplicate
  parameter names are rejected (`PEP_DUPLICATE_PARAMETER`).

### 5.2 Bindings and assignment

- `let name [: Type] = expr` — immutable. `var name [: Type] = expr` — mutable.
- Annotations are checked (`check` direction); omitted annotations synthesize from
  the initializer. A binding whose type remains unknown (e.g. an unconstrained hole
  or an un-inferrable literal) is recorded without a type; any later use is rejected
  with `PEP_UNCONSTRAINED_BINDING`, and assignment to it is likewise rejected
  **[source-read]**.
- Duplicate names in the same scope are rejected (`PEP_DUPLICATE_BINDING`); nested
  blocks may shadow outer bindings **[source-read + tested]**.
- Assignment `name = expr` requires an existing **mutable** binding of matching
  type: unknown names give `PEP_UNKNOWN_VARIABLE`, `let` targets give
  `PEP_ASSIGN_IMMUTABLE`, type mismatches give `PEP_TYPE_MISMATCH` **[tested]**.
- The loop variable of `for` is immutable and scoped to the loop body; referencing
  it after the loop gives `PEP_UNKNOWN_VARIABLE` **[tested]**.

### 5.3 Control flow

- **Statement `if`:** `if condition { ... } else { ... }` — the `else` block is
  **mandatory** in v0.1 (`PEP_PARSE_ELSE` otherwise) **[source-read]**. There is no
  `else if` form; nesting requires explicit braces. The condition MUST be `Bool`.
- **`while`:** `while condition { ... }`, condition MUST be `Bool`
  (`PEP_TYPE_MISMATCH` otherwise) **[tested]**.
- **`for`:** `for name in expr { ... }` — `expr` MUST synthesize `List[T]`
  (`PEP_FOR_REQUIRES_LIST` otherwise, including the un-inferrable case) **[source-read]**.
  The collection expression is evaluated once on entry; the binding is immutable.
- There are **no** `break` / `continue` statements in v0.1 (no such AST constructors
  exist) **[source-read]**.

### 5.4 Records, unions, field access

- `type Name { field: Type, ... }` declares a nominal immutable record;
  `type Name = C1(...) | C2(...) | ...` declares a recursive tagged union with
  positional constructor payloads **[source-read]**.
- Construction: `Name { field: value, ... }` — and the `{` MUST be on the **same
  source line** as the constructor name, else it parses as a block
  **[source-read]**. Missing fields give `PEP_MISSING_FIELD`, duplicates give
  `PEP_DUPLICATE_FIELD`, unknown fields give `PEP_UNKNOWN_FIELD`.
- Field access `expr.field` requires a record-typed expression with a known field
  (`PEP_FIELD_ON_NON_RECORD` / `PEP_FIELD_ON_UNTYPED_VALUE` / unknown-field
  diagnostics) **[source-read]**.
- Variant construction is a call `Constructor(args)` checked for arity and payload
  types (`PEP_ARGUMENT_COUNT`) **[source-read]**.
- Type names may not collide with built-ins or each other
  (`PEP_DUPLICATE_TYPE`, `PEP_RESERVED_*`).

## 6. Expressions and typing

### 6.1 Bidirectional checking

The checker synthesizes types bottom-up and checks top-down against expected types
from annotations, arguments, return positions and `if`/`match` contexts. Incompatible
expected/found types give `PEP_TYPE_MISMATCH` with the expected type attached
**[source-read + tested]**.

### 6.2 Operators (complete v0.1 inventory)

| Operator | Operand rule | Result | Notes |
|---|---|---|---|
| `+ - * /` | both `Int` (checked) | `Int` | §4.2 failures |
| `<=` | both `Int` (checked) | `Bool` | the **only** comparison |
| `==` `!=` | left operand synthesizes a **scalar** type (`Int`/`Bool`/`Str`/`Unit`); right checked against it | `Bool` | non-scalar left: `PEP_EQUALITY_UNSUPPORTED`; untyped left: `PEP_EQUALITY_UNTYPED`. No equality on lists, records or unions **[source-read + tested]** |
| `&&` `\|\|` | both `Bool` (checked) | `Bool` | right side evaluated only if needed (short-circuit) **[source-read + tested]** |
| `!` | operand `Bool` (checked) | `Bool` | any other unary operator: `PEP_UNKNOWN_UNARY_OPERATOR` |

### 6.3 `if` expressions

`if condition { expr } else { expr }` — `else` mandatory (`PEP_PARSE_ELSE`).
Condition MUST be `Bool`. Branch types MUST agree (`PEP_TYPE_MISMATCH`). Holes in
branches participate in inference: a hole on one side takes the other side's
synthesized type; a hole on both sides stays unconstrained **[source-read]**.

### 6.4 `match` expressions

- `match subject { pattern => expr ... }` — arms need no separators; `=>`
  separates pattern from result; at least one arm is required (`PEP_EMPTY_MATCH`).
- The subject MUST synthesize a tagged-union type (`PEP_MATCH_NON_UNION`,
  `PEP_MATCH_UNTYPED`). Patterns: `_` wildcard, bare-name binding, or
  `Constructor(subpatterns...)` with exact arity (`PEP_PATTERN_ARITY`) and owning
  union (`PEP_PATTERN_TYPE_MISMATCH`).
- Pattern bindings are arm-local and immutable; duplicate bindings in one pattern
  give `PEP_DUPLICATE_PATTERN_BINDING` **[source-read + tested]**.
- Any arm after an irrefutable (wildcard/binding, or covering) pattern is rejected
  (`PEP_UNREACHABLE_MATCH_ARM`); duplicate arm shapes are rejected
  (`PEP_DUPLICATE_MATCH_ARM`). A match without an irrefutable arm MUST cover every
  constructor or `PEP_NON_EXHAUSTIVE_MATCH` names each missing constructor
  **[source-read + tested]**.
- Arm result types MUST agree with each other (and with any expected type);
  mismatches surface as `PEP_MATCH_ARM_TYPE_MISMATCH` **[source-read]**.

### 6.5 List literals and builtins

- `[a, b, ...]` with no expected element type infers the element type from the
  **first item that synthesizes a type** (holes and `[]` skipped); every item is
  then checked against it, so `[1, true]` is `PEP_TYPE_MISMATCH` **[executed]**.
- `[]` (or any literal transitively containing one) with no expected element type
  is rejected with `PEP_EMPTY_LIST_NEEDS_TYPE` **[executed]**. An annotation,
  parameter type, or builtin expectation supplies the element type (e.g.
  `let xs: List[Int] = []`).
- With a known element type `T` the literal has type `List[T]`.

| Builtin | Signature (checked) | Cost / notes |
|---|---|---|
| `length(l)` | `List[T] -> Int` | O(n) traversal; each node consumes budget |
| `append(l, x)` | `(List[T], T) -> List[T]` | O(n) copy; original unchanged (immutable lists) |
| `prepend(l, x)` | `(List[T], T) -> List[T]` | O(1) |
| `reverse(l)` | `List[T] -> List[T]` | O(n) |
| `contains(l, x)` | `(List[T], T) -> Bool` | O(n) in-order scan, stops at first equal; `T` MUST be scalar (`PEP_MEMBERSHIP_UNSUPPORTED` otherwise, e.g. records) |
| `byte_length / byte_at / byte_slice` | operate on `SourceBytes` | §9 |
| `utf8_slice(bytes, lo, hi)` | `(SourceBytes, Int, Int) -> Str` | validates UTF-8; the only `SourceBytes → Str` bridge |
| `source_bytes()` | `() -> SourceBytes` | host-gated: only inside tool protocol v2 `semanticTarget`; elsewhere `PEP_RUNTIME_SOURCE_CONTEXT` |

`length`/`append`/`contains` reject non-lists (`PEP_LIST_EXPECTED`) and
un-inferrable lists (`PEP_LIST_UNTYPED`).

## 7. Name resolution and scopes

- Lexical block scoping. Function signatures (including forward and recursive
  references) resolve in one type authority; bodies check after all signatures are
  collected **[source-read + tested]**.
- Calls to unknown functions give `PEP_UNKNOWN_FUNCTION`; capitalized unknown
  callees give `PEP_UNKNOWN_CONSTRUCTOR`. Arity mismatches give
  `PEP_ARGUMENT_COUNT` (constructors, builtins and functions alike).
- Unknown variables give `PEP_UNKNOWN_VARIABLE`. There are no nested or anonymous
  functions and no captures in v0.1 — every function is top-level; top-level
  statements execute in order at the top level **[source-read]**.

## 8. Holes

- `?name` and `?` / `_` denote typed holes with optional identity. A hole records
  its expected type (when context supplies one), visible bindings, scope and span.
- Querying (`query --holes --json`, `--offset` selects by byte offset) reports
  holes; a hole in an unannotated binding is unconstrained **[source-read]**.
- Hole fill (`fill_hole` in the session) resolves a scope-qualified named hole at
  the exact current revision, parses exactly one replacement expression, rechecks
  the whole candidate and advances the revision only on success; stale or ambiguous
  targets do not advance **[source-read]**. There is no general structural editing
  in v0.1.

## 9. SourceBytes and the tool/session boundary (development-branch status)

`SourceBytes` and its builtins (`byte_length`, `byte_at`, `byte_slice`,
`utf8_slice`, `source_bytes`, plus `open_bytes` session ingestion) are implemented
in the seed at this base but conflict with `docs/DESIGN.md`'s "A10 remains
unaccepted" (see `GAP-AND-CONTRADICTION-REPORT.md` C1). They are specified here as
**development-branch capabilities on the campaign line, not accepted core**:

- `SourceBytes` is opaque: it is not `Str`, cannot cross the v1 tool boundary, and
  only `utf8_slice` converts a byte range to `Str` (with explicit validation).
- `byte_at`/`byte_slice` reject out-of-range offsets at runtime
  (`PEP_RUNTIME_BYTE_RANGE`); raw `byte_slice` may split a UTF-8 sequence (bytewise
  scanning); offsets are original-byte offsets.
- `open_bytes` retains at most 65,536 exact bytes per ingestion, including malformed
  UTF-8; malformed input never mutates prior state **[source-read]**.
- The in-process tool registry (protocol v1 scalar messages; v2 bounded typed
  `List`/record transport + `semantic_snapshot()` of a host-granted retained
  revision) is trusted-local, not a sandbox; tools cannot reach `say`, cannot forge
  target revisions, and run under the §4.3 tool budget **[source-read]**.

## 10. Machine interface (implemented surface)

- `describe --json` — `schemaVersion: 2`, `types`, `parametricTypes: ["List[T]"]`,
  `features` (33 capabilities ending in `scalar_equality`; full list observed live),
  `runtime: {maxSteps: 1000000, maxCallDepth: 512}`, `builtins` (12 names)
  **[executed]**.
- `inspect --json` — parsed AST (`status: "parsed"`). `check --json` — checked
  status `valid | incomplete | invalid` plus diagnostics; nonzero exit unless valid.
  `query --holes --json` (+ `--offset N`) — hole contexts. `run` — executes only
  complete valid programs; prints `say` output; diagnostics go to stderr as
  `file:line:col: CODE: message`, JSON form with `--json` **[source-read]**.
- `session --jsonl` — schema v3: immutable revisions with SHA-256 IDs, revision-bound
  queries and hole identities, same-revision analysis cache; a changed revision is
  fully re-parsed and re-checked (no cross-revision incremental reuse) **[source-read]**.
- Every diagnostic carries `{code, message, span, expected?}`; unknown schema
  versions MUST be rejected by consumers, not guessed (TR001 §9).

## 11. What v0.1 deliberately leaves out

No modules/imports/visibility; no generics, abilities, or behaviour records; no
closures or capture modes; no `Option`/`Result`/`?`/error algebra; no effects,
`uses`, or host grants; no `Float`, `Byte`/`Bytes`, arrays, maps; no Unicode
grapheme API beyond §3.1 escapes; no `danger`/FFI/ownership; no tasks/channels;
no test declarations or `pep test`; no Semantic Note semantics (`#@` is an ordinary
comment); no incremental cross-revision analysis; no native backend or
self-hosting. Each item's accepted direction, if any, is tracked in
`PEPIN-1.0-DECISION-REGISTER.md` — never infer it from this core.
