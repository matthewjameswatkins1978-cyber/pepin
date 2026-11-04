# E1 — Actual Compiler Closure Map (compiler A as built, not as imagined)

**Programme:** PEP-A4-RESEARCH-E-20261104, Phase I slice 1 of 3.
**Method:** read-only source inspection + counted markers. No probes run, no
implementation changed. Claims labelled ESTABLISHED / INFERRED / UNKNOWN.

## 1. Preflight pins (reverified this slice)

| Artifact | Pin | State |
|---|---|---|
| Seed checkout `D:/Projects/pepin` | `57fe424` (all counts below) | `M tests/test_a14_c23.py` preserved untouched |
| A1 repair branch | `f8ac7a8` remote-equal; local worktree has uncommitted edits (NOT read for E1) | dirty, not mine |
| A3 verification branch | `2faed39` remote (per LUCY-011); `a4f2833` named in programme doc — recheck before citing A3 state | remote only |
| Integration | `81398fa` unchanged | remote only |
| A4 own branch | `spec/agent4-spec-lab @ 489d722`, clean before this slice | mine |
| origin HEAD | `e706939` (master moved past seed pin — E1 pins to `57fe424` explicitly) | noted |

## 2. Pipeline map: what actually executes what (ESTABLISHED)

- **Driver `pep.ps1` (67 lines):** hash-guarded `ocamlopt` rebuild of
  `pep_ocaml.ml` under opam switch `pepin-5.5.2`, then forwards
  `describe/inspect/check/query/run/session`. C23 commands delegate to
  **Python `pep_c23.py` (13 KB)**. `pep_lab.py` (27 KB) is lab/session tooling.
- **Stage-0 `pep_ocaml.ml` (1930 lines, 145 KB):** lexer, parser, typed
  checker (`texpr`/`tstmt`), tree interpreter (`execute`, step-limit 1M,
  max depth 512), JSON diagnostics, `session --jsonl` host (schema v3).
  `describe` is the authoritative feature registry (quoted verbatim in §4).
- **Staged Pep programs are executed BY the OCaml interpreter** through the
  session host: `tests/test_a13.py` (168 KB) spawns
  `pep.ps1 session --jsonl`. There is no staged native execution of the
  compiler itself; `pep_c23.py` loads all four staged sources
  (lexer+parser+checker+emitter) through the OCaml session via pwsh+Python.
- **Trust chain for one staged check:** Python driver → pwsh → opam-built
  OCaml exe → session host → interpreted staged Pep. Three host languages
  (Python, PowerShell, OCaml) stand under every "Pep-written" compiler claim.
- `pep_chunk_contract.py` (BindingPool) does NOT exist at seed — it is
  A1-branch-only (`9ad7d95` lineage). Any E2/E4 reasoning that assumes it as
  stage-0 is wrong; it is staged-Python host tooling, not compiler.

## 3. Feature usage by staged component (counted at `57fe424`)

| Component (lines) | `fn` | record decls | union decls | `match` | `for_in` | `while` | `var` |
|---|---|---|---|---|---|---|---|
| checker `tests/pep_checker_a13.pep` (2258) | 103 | 25 | 0 | 34 | 10 | 7 | 148 |
| parser `examples/pep_parser.pep` (1802) | 80 | 12 | **1** | 9 | ? | ? | 67 |
| lexer `examples/pep_lexer.pep` (481) | 10 | 5 | 0 | 0 | 0 | 4 | 31 |
| emitter `tests/pep_c23_emitter.pep` (495) | 13 | 2 | 0 | 1 | 0 | 0 | 24 |

- **The single staged union is the parser's `AstValue`: 36 constructors, 243
  constructor-uses in the parser.** The AST itself is the one place compiler A
  needs a sum type; everything else is records + `List[T]`.
- **Algorithmic style is list-functional with mutable accumulators:**
  `prepend`/`reverse` idiom everywhere (checker quicksort, scope chains,
  diagnostics); `length`/`append`/`contains` as workhorses. No indexed arrays,
  no hash maps, no I/O in staged code (INFERRED from zero `say`/file uses
  outside tests — spot-checked, not exhaustively proven).
- **Emitter is a predicate-rich partial lowering** (13 fns:
  `pep_c23_expression`, `*_may_fail`, `*_call_free_*`, `emit_c23_checked`);
  its accepted subset boundary is NOT yet tabulated — E1 blocker B3.

## 4. Primitive surface (ESTABLISHED — OCaml `describe`, verbatim set)

Types: `Int Bool Str SourceBytes Unit` + `List[T]`. No floats, no maps, no
`Char`. Builtins (12): `say Str->Unit`; `int_text`; `length/append/prepend/
reverse` (documented O(n)/O(n)/O(1)/O(n)); `byte_length/byte_at/byte_slice`
(SourceBytes, checked/unsigned); `utf8_slice` (UTF-8 boundaries);
`source_bytes` (v2 semanticTarget revision authority);
`contains` (scalar-only equality). Features: recursion, lexical scopes, typed
holes + query, checked integer arithmetic, interpreter, records, tagged
unions, pattern matching, `for_in`, `while`, short-circuit booleans, scalar
equality. Session: schema v3, **`maxOpenByteInput: 65536`**,
typed transport caps (depth 16, 10k nodes, 1 MiB), tool runtime
`trustedLocal:true, sandboxed:false`, maxSteps 100k.

## 5. Four minima — first mapping (INFERRED, to be tested in E2)

1. **Subset needed to write compiler A:** records + `List[T]` + first-order
   fns + `match` + `for_in`/`while` + `var` + 12 builtins + **exactly one
   large union** (the AST). Notably NOT needed in implementation: user-declared
   unions beyond the AST, holes, tool registry, session protocol.
2. **Smallest trusted stage-0:** must implement ALL of (1) at runtime
   (interpreter executes the checker) + lex/parse/check to bootstrap + JSON +
   UTF-8 spans + 64 KiB transport. The interpreter is the irreducible core;
   the staged checker is replaceable logic, the interpreter is not.
3. **Smallest native runtime + OS glue:** UNKNOWN from source-read alone —
   depends on A2's emitter boundary (B3) and what `pep_c23.py`+Clang require.
4. **Enduring conceptual core:** records + unions + match + effects-free fns
   look essential (the AST union + checker records mirror the language);
   `SourceBytes`/tool-registry/session look like host-interface conveniences,
   not language essence. E2 must test this, not assert it.

## 6. Blockers — independently checkable (output of E1)

- **B1.** Is the parser's 36-constructor `AstValue` matched exhaustively
  everywhere it is consumed, or do wildcard arms hide missing cases?
  (Read the 9 `match` sites; one program, falsifiable.)
- **B2.** Smallest REAL end-to-end: `hello.pep` (1 line) runs through the
  seed, but no identified test composes staged lexer→parser→checker on one
  input. Does one exist, or is staged composition only exercised piecemeal?
- **B3.** Tabulate the emitter's accepted/rejected subset (which Pep forms
  lower, which `pep_c23_unsupported` refuses) — required for minima (3).
- **B4.** `maxOpenByteInput: 65536` vs 152 KB checker source: how does the
  session load staged programs larger than one transport — chunked opens?
  (Affects any "smallest host interface" claim.)
- **B5.** `source_bytes` v2-authority builtin: which staged component calls
  it, and what breaks if the host withholds it? (Trust-boundary probe for E4.)

## 7. Status labels

AUDIT slice (not a proposal): no architecture is recommended here; E2 draws
the counterfactuals, E3 the verdict. No REPORTED→TESTED upgrades. No freeze,
no master/CURRENT/manifest change. Next: E2 (three routes + falsifiers),
which needs B2/B3 answered first.
