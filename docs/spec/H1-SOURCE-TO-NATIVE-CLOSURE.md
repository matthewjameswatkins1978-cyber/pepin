# H1 — Source-to-Native Closure Census, Part 1: Pins, Sample, Static Table

**Campaign H, H1 investigation.** Pins: lexer+parser @ seed `57fe424`
(byte-identical in A1 `2ad750b` and A2 `58fc9bf` — verified by empty
`git diff --stat`); staged checker @ A1 `2ad750b`
(`tests/pep_checker_a13.pep`, +1371/-513 vs seed: union facts, stamps,
chunk/signatures machinery, `str_concat` use); staged emitter @ A2
`58fc9bf` (`tests/pep_c23_emitter.pep`, +4400/-409 vs seed: lists, records,
unions, Str results, while/mutable lists, cross-chunk calls, arena,
prototypes, bounded units). Seed extended @ `2ad750b` (`pep_ocaml.ml` +65:
`str_concat` builtin added; builtin set now 13). Labels: ESTABLISHED /
INFERRED / UNKNOWN. No implementation changed; `_build/h1/` scratch only.

## ESTABLISHED file-level results (executed this slice, seed exe = 57fe424
`pep.exe` except where noted; A1-seed exe built to `_build/h1/` from the
pinned source, read-only)

- R1: lexer standalone `check` → **VALID**, exit 0 (seed exe).
- R2: parser standalone → **INVALID** `PEP_UNKNOWN_TYPE 'LexCursor'`
  (needs lexer types — cross-file dep).
- R3: checker@2ad750b standalone (seed exe) → **INVALID**
  `PEP_UNKNOWN_FUNCTION 'str_concat'` at bundle-offset — the staged checker
  outran stage-0: it CALLS `str_concat` (2 sites) and lists it in
  `known_builtin`, but seed-57fe424 has no such builtin. (Resolves below.)
- R4: emitter@58fc9bf standalone (seed exe) → **INVALID** `PEP_UNKNOWN_TYPE
  'FlatAstNode'` (needs parser types).
- R5: FULL 582,625-byte bundle (lexer+parser+checker@2ad750b+emitter@58fc9bf,
  SOURCES order) under A1-seed exe → **VALID** (12.5 MB report). No CLI size
  cap, no step-limit on the complete compiler corpus. A4's `str_concat`
  finding converged: E8-R1 exists at `2ad750b` (causation unclaimed).
- R6: A1-seed `describe` builtins = 13 (12 + `str_concat`; `utf8_slice`
  retained — earlier regex miss corrected by direct read).

Dependency chain ESTABLISHED: lexer → parser → checker → emitter (each needs
the previous file's types; bundle order = `pep_c23.py` SOURCES).

## 32-function sample (static census)

Columns: `S` = seed parses/checks the construct (corpus ESTABLISHED R1/R5;
per-fn = construct-set membership, INFERRED unless probed). `C` = staged
chunk path handles it under 100k (shape-fit INFERRED; `run` = probed).
`E` = current A2 emitter accepts its shape (guard-read INFERRED; `run` =
probed). Blocker = first refusal point (static).

### Lexer (seed 57fe424, `examples/pep_lexer.pep`)

| # | fn (line) | I/O | key deps | S | C | E | first blocker |
|---|---|---|---|---|---|---|---|
| L1 | `ascii_digit` (49) | Int→Bool | comparisons, `&&` | yes | yes-shape | lowerable-shape (Int fn, pure expr) | none structural; needs `main` harness |
| L2 | `utf8_check` (57) | (SourceBytes,Int,Int)→Utf8Check | `byte_at`, `byte_length`, while, SourceBytes | yes | yes-shape | **BLOCKED: SourceBytes param type** (no C lowering) | source-bytes ingress |
| L3 | `advance_position` (90) | (Int,Int,Int)→SourcePosition | Int arith, if | yes | yes-shape | lowerable-shape (record RESULT is the question → A2-record-opportunity, UNKNOWN) | record return |
| L4 | `make_token` (113) | (…)→LexToken | record literal, Str fields | yes | yes-shape | **record construction w/ Str fields** (A2 record support exists — opportunity, UNKNOWN) | record+Str |
| L5 | `lexer_start` (140) | ()→LexCursor | record literal | yes | yes-shape | same as L4 (smaller) | record literal |
| L6 | `lexer_step` (146) | LexCursor→LexProgress | while, mutable cursor, `byte_at`, SourceBytes | yes | yes-shape (runs in staged tool, A3-F2) | **SourceBytes + while + mutable state** (A2 has `pep_c23_loop_statement`/`while_body` — opportunity, UNKNOWN) | source bytes + loop state |

### Parser (seed 57fe424, `examples/pep_parser.pep`)

| # | fn (line) | I/O | key deps | S | C | E | first blocker |
|---|---|---|---|---|---|---|---|
| P1 | `token_at` (315) | (List[LexToken],Int)→LexToken | list indexing, records | yes | yes-shape | list-typed param (A2 has list params — opportunity, UNKNOWN) | LexToken record type |
| P2 | `stream_take` (387) | ParserStream→TokenRead | record update, Str | yes | yes-shape | record in/out | record plumbing |
| P3 | `parse_pattern` (437) | (stream,depth)→AstParse | recursion?, union match | yes | yes-shape | **AstValue union match** (A2 has `pep_c23_union_match_expression` — opportunity, UNKNOWN) | union match |
| P4 | `parse_match_expression_after` (534) | …→AstParse | recursion, union ctors | yes | yes-shape | same as P3 + recursion | union + recursion |
| P5 | `parse_expression` (1013) | (stream,prec,Bool,depth)→AstParse | precedence loop, RECURSION, depth Int | yes | yes-shape (100k-shared) | **BLOCKED (likely): direct recursion** (`parse_expression` calls itself; emitter historically refuses recursion — verify at 58fc9bf) | recursion |
| P6 | `flatten_ast` (1333) | (AstValue,Int)→List[FlatAstNode] | union match, list build | yes | yes-shape | union match + list construction | AstValue match |
| P7 | `parser_step` (1494) | ParserCursor→ParserChunk | cursor machine, frames, while? | yes | yes-shape (IS the staged tool path) | state machine + loops | control complexity |
| P8 | `flatten_top_level` (1833) | List[AstValue]→List[FlatAstNode] | list append loop | yes | yes-shape | list iteration + construction | list build |

### Checker (A1 2ad750b, `tests/pep_checker_a13.pep`)

| # | fn (line) | I/O | key deps | S | C | E | first blocker |
|---|---|---|---|---|---|---|---|
| C1 | `known_builtin` (148) | Str→Bool | `==` chain (now 13 incl. `str_concat`) | yes | yes-shape | lowerable-shape | none structural |
| C2 | `find_binding` (285) | (List[BindingFact],Int)→BindingLookup | list scan, record compare | yes | yes-shape | list+record scan | record types |
| C3 | `collect_bindings` (472) | (nodes,fns,doc,rev)→BindingCollection | loops, appends, diagnostics, stamps | yes | yes-shape (runs inside analyze) | **CheckDiagnostic construction + Str messages** | diagnostic records |
| C4 | `resolve_names` (525) | …→NameResolution | scope walk, references | yes | yes-shape | scope arithmetic + records | traversal state |
| C5 | `infer_expression_type` (753) | (nodes,id,…)→Str | recursion over exprs, `str_concat` call site (line ~687 area) | yes (A1 seed) | yes-shape | **needs `str_concat` at runtime** (now EXISTS at 2ad750b — resolved; seed-57fe424 would refuse) | stage-0 builtin sync |
| C6 | `hole_facts` (1575) | …→List[HoleFact] | scope+type filter, list build | yes | yes-shape | list of records | record lists |
| C7 | `type_analysis` (1654) | (…9 args…)→TypeAnalysis | everything (likely recursion) | yes | yes-shape (IS the budget) | **transitive closure of C3–C6** | whole-checker depth |
| C8 | `chunk_type_declarations` (2503) | ParserProgress→List[ResolvedTypeDecl] | union emission, duplicate scan | yes | yes-shape (E2b path) | union decls as data (A2 union support — opportunity, UNKNOWN) | ResolvedTypeDecl union |
| C9 | `colliding_local_function` (2727) | (nodes,names,name)→NodeLookup | list scan, Str compare | yes | yes-shape (R-ID-1 path) | list scan + Str | Str compare |
| C10 | `analyze_parsed` (2490) | ParserProgress→CheckerReport | calls C3–C7 chain | yes | yes-shape (entry) | whole-checker closure | entry breadth |

### Emitter (A2 58fc9bf, `tests/pep_c23_emitter.pep`)

| # | fn (line) | I/O | key deps | S | C | E | first blocker |
|---|---|---|---|---|---|---|---|
| E1 | `pep_c23_c_scalar_type` (749) | FlatAstNode→Str | Str `==`, record field read | yes | n/a (IS emitter) | self (probe P6) | — |
| E2 | `pep_c23_child` (24) | (nodes,id,role,idx)→Lookup | for loop, compares | yes | n/a | self (loop shape) | — |
| E3 | `pep_c23_expression` (2425) | (nodes,fn,node)→Emission | giant kind-match, binary/neg helpers | yes | n/a | self (core lowering) | — |
| E4 | `pep_c23_function_expression` (3413) | (nodes,fn,checked)→Emission | lets+return / final-if shape gate | yes | n/a | self (the subset gate) | — |
| E5 | `pep_c23_loop_statement` (3145) | (…depth,bindings…)→Emission | while lowering, depth Int | yes | n/a | self (NEW vs seed) | — |
| E6 | `pep_c23_str_expression` (1140) | (nodes,fn,value)→Lookup | Str-typed calls | yes | n/a | self (NEW Str capability) | — |
| E7 | `pep_c23_cross_chunk_call` (643) | (nodes,fn,node,…)→… | header/prototype/call assembly | yes | n/a | self (NEW seam path) | — |
| E8 | `emit_c23_checked` (4383) | (parsed,checked)→Emission | authority gate, main requirement | yes | n/a | self (entry contract) | — |

Denominators: 32 sampled of ~316 total fns (10 + 80 + ~125 + ~113); 4/4
components; easy (L1,C1,E1,E2), medium (L3–L5,P1–P2,C2,C6,C8,C9,E4,E6–E8),
hard (L2,L6,P3–P8,C3–C5,C7,C10,E3,E5). UNKNOWNs cluster at A2's NEW surface
(records/lists/unions/Str/while at 58fc9bf) — exactly what H1b probes target.

Next: H1b dynamic probes P1–P8 (disposable `_build/h1/` scratch, existing
`pep.ps1`/`pep-2ad750b.exe`/Clang/GCC only), then blocker clustering with
reachable fractions. No static claim will be called a run.

## H1b — executed probes P1–P8 (run this slice; seed exe unless noted)

- **P1** `ascii_digit` verbatim + top-level driver → output `1/0`, exit 0.
  PASS. (Also proves scratch files parse — no BOM issue.)
- **P2** `byte_at(source_bytes(),0)` → **BLOCKED-authority**:
  `PEP_RUNTIME_SOURCE_CONTEXT` (needs v2 host-granted semanticTarget;
  plain `run` does not grant). Informative, not a failure: maps E4-T2.
  Covering evidence: A3 set 13 exercises byte builtins through v2 grants
  (REPORTED). No seed-run byte path exists without a grant.
- **P3** `insert_sorted`+`quick_sort_nodes` verbatim (real staged-checker
  bodies, FlatAstNode literals) → `1,2,3` / `1,2,3,4,5`, exit 0. PASS —
  including the checker's own RECURSION under the interpreter.
- **P5** `same_type_shape` verbatim + PepTypeShape literals → `1/0/0`,
  exit 0. PASS.
- **P6** A2-58fc9bf `pep_c23_c_scalar_type` verbatim + node literals →
  `int64_t` / `_Bool` / empty / empty, exit 0. PASS (real emitter fn).
- **P7** grade bands (G-A4-4 sketch, `>=` rewritten to seed's `<=` set):
  `check` VALID; `run` → `6/10/1` exactly as predicted (seed oracle).
  Native via seed `pep.ps1 build-c23` → **BLOCKED**: `PEP_RUNTIME_STEP_LIMIT
  at 251:10` in session `tool_invoke` (parse_count 3 — the seed driver's
  bundled-emit path, not the program). Independent native evidence: A3
  adopted the bands 7x2 (REPORTED). No static native claim made here.
- **P8** existing `tests/test_a13.py` staged-checker test
  (`test_primitive_synth_check_and_type_facts` via unittest, no pytest on
  host) → **OK in 0.9s**. PASS: staged chunk path works on this host for
  small inputs — P7's block is emit-path/bundle specific, not general.
- Score: 8 probes, 6 PASS + 1 informative-authority-block (P2, covered by
  A3-set-13) + 1 path-specific block (P7-native, covered by A3-7x2).
  Probe files + raw outputs retained under ignored `_build/h1/`.

## H1b — blocker clustering (by ROOT DEPENDENCY, with denominators)

Sample: 32/316 fns (10%), 4/4 components, easy/medium/hard + control/data.

1. **Record/union value construction + match (largest share).** Affected:
   L3–L5, P1, P3–P4, P6, C2, C6, C8 (~10/32 statically; A2-58fc9bf ADDS
   record/union/list/Str lowering — reachable set EXPANDED vs E2-B3).
   Counterfactual: if A2's constructor/field/match shapes cover what these
   fns use, ~40% of the medium sample moves to reachable; next block below.
   Needs guard-reads per shape, not assumed.
2. **SourceBytes/host-grant ingress.** Affected: L2, L6 (loop state aside),
   P2-probe (BLOCKED). Gates ALL byte programs incl. the lexer core — small
   count, totalizing effect. Counterfactual: a granted-handle model unlocks
   seed-side byte programs first; native still needs while+records.
3. **Recursion + loop-state + whole-program depth.** Staged-OK vs
   native-refuse asymmetry PROVED: P3's recursive quicksort PASSES under the
   interpreter; the emitter historically refuses recursion (verify at
   58fc9bf — UNKNOWN). Affected: P5, C7, C10, E3–E5. A2's new
   `pep_c23_loop_statement`/`while_body` may narrow the loop half —
   probe-worthy, not claimed.

Reachable fraction (sampled, honest ranges): firmly lowerable today
(seed-subset shapes: L1, C1, E1, E2 + maybe L3) ≈ **3–5/32**; A2-new-surface
candidates (records/lists/unions/Str/while, guard-reads pending) ≈
**12–15/32**; firmly blocked (SourceBytes, recursion, whole-program depth)
≈ **12/32**. If A2's new lowering covers the used shapes, reachable jumps
from ~4 to ~16/32 — and the next block is SourceBytes (lexer core) +
recursion (parser/checker depth). Classification uncertainty: per-fn
construct membership INFERRED from file-VALID corpus; only probed fns are
ESTABLISHED individually.

Top-3 ranked blockers for H2: (1) record/union/list/Str lowering
completeness at 58fc9bf (biggest sample share, A2 already moving);
(2) SourceBytes/host-grant model (totalizing for byte programs);
(3) native recursion/loop-state gap (staged-proved vs native-unknown).
