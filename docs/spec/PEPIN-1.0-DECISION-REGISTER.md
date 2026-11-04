# Pepin 1.0 Decision Register

- **Status:** working register of unsettled semantics. Nothing here is normative; each
  entry records the question, the existing commitments, candidate resolutions with
  trade-offs, dependencies, and a recommendation **only where the inspected evidence
  supports one**. Where the full DEC text was not directly inspected (Basic Memory
  unreachable this session), the commitment is marked **[reported]**.
- **Rule:** an entry may graduate into `PEP-LANGUAGE-SPEC-v0.1.md` only after an
  executable grammar/checker fixture and acceptance evidence exist. Closing an entry
  by prose here is forbidden.
- **Provenance shorthand:** FD = final draft (PR #14); REF = language reference
  (PR #18); R2 = Road 2 milestone; LED = full-language ledger. DEC citations are via
  FD/REF summaries.

## DR-01 Generics (DEC-003B; FD §3.2; R2-V2)

- **Commitments [reported]:** type and function declarations may take parameters
  (`Pair[A,B]`, `count[T]`, `[T: Ordered]` spellings are *proposed*); type arguments
  inferred only when unique; generic bodies checked against declared constraints,
  never merely against sample instantiations; compiler may specialise/share only
  with preserved semantics/ABI; no template-macro system.
- **Open:** declaration-site syntax; constraint spelling and where bounds are
  declared; inference algorithm and ambiguity diagnostics; cross-module
  instantiation checking; representation/monomorphisation policy and its ABI
  obligations; interaction with abilities (DR-02) and effects (DR-07).
- **Options:** (a) full Hindley–Milner-style inference with principal types —
  expressive but costly to specify and diagnose; (b) local inference + explicit
  declarations only — matches bidirectional core, smaller proof burden, more
  annotations; (c) inference with caps/annotations at module boundaries.
- **Dependencies:** DR-02 (constraints), DR-10 (closures/function types for
  higher-order generic utilities like map/filter), name resolution for
  cross-module checking.
- **Recommendation:** (b)/(c). The seed's bidirectional checker already flows
  expectations inward; extending `check` positions to generic instantiation is the
  smallest coherent step, and Road 2's acceptance (generic map/filter in Pep
  without compiler magic) tests exactly this. No new inference engine without a
  prototype and ambiguity fixtures.

## DR-02 Type abilities: Equal / Ordered / Hashable (DEC-003C; FD §3.3)

- **Commitments [reported]:** three compiler-known abilities only; structural
  equality synthesis allowed for compatible records; ordering NEVER auto-derived;
  NaN has no ordinary total order; no general operator overloading; numeric
  operations need separately specified capabilities — no invented `Numeric`
  hierarchy (a prior draft's illustrative `Numeric` was explicitly removed).
- **Open:** derivation rules and law statements (what "consistent with Equal" means
  operationally); Map's Hashable/Equal checking (static vs runtime); total-order
  policy for floats (explicit wrapper vs rejected grant); generic arithmetic
  contract shape.
- **Options:** (a) abilities as implicit constraints solved by the checker —
  ergonomic, risks invisible resolution; (b) abilities as explicit dictionary
  arguments (see DR-03) — verbose, fully inspectable; (c) hybrid: compiler-known
  solving for the three abilities with provenance in query output.
- **Dependencies:** DR-01, DR-08 (Map key laws), DR-09 (float semantics).
- **Recommendation:** (c) with machine-readable provenance, consistent with the
  AI-first queryability goal; but do not freeze until Map/Float fixtures exist.

## DR-03 Behaviour records, no global instances (DEC-003D; FD §3.4)

- **Commitments [reported]:** behaviours are ordinary generic records of typed
  functions passed explicitly (dictionary-as-value); multiple comparators for one
  type coexist; no import-dependent global resolution; inspectable like any value.
- **Open:** library shape for comparator/formatter families; how behaviour
  dictionaries compose with generic inference; whether any standard behaviour gets
  syntactic sugar (risk: sugar becomes a second resolution language).
- **Dependencies:** DR-01, DR-10.
- **Recommendation:** keep fully explicit through V2; revisit sugar only with
  demonstrated boilerplate pain from real Pep programs. No recommendation beyond
  the commitment.

## DR-04 Functions as values, closures, captures (DEC-003E; FD §3.5)

- **Commitments [reported]:** functions bindable/passable/returnable/storable;
  proposed `fn(T)->U` type shape and anonymous `fn(...) -> U { ... }` (*proposed*
  spellings); capture-by-value default with shared read-only storage allowed;
  `edit` capture exclusive + initially non-escaping; `take` capture transfers
  ownership; invocation (one-shot/mutating) respects access modes; function types
  carry effect and access contracts.
- **Open:** almost everything executable: capture-mode syntax, escaping analysis,
  one-shot enforcement, closure layout/ABI, effect-bearing function subtyping,
  async interaction (no edit across await in the initial model).
- **Options:** (a) full closure conversion with escape analysis in the checker —
  powerful, large proof surface; (b) restricted closures first (by-value capture
  of scalars/immutable values only, no escaping edit) — shippable slice that
  already enables behaviour records and callbacks.
- **Dependencies:** DR-05 (access modes), DR-06 (lifetimes), DR-11 (tasks).
- **Recommendation:** (b) as the first authorised slice; (a) stays provisional
  until the ownership story (DR-05/DR-06) has fixtures.

## DR-05 Access modes: read / edit / take (DEC-002; FD §5)

- **Commitments [reported]:** `read` default (no caller-visible mutation/transfer);
  `edit` = explicit temporary exclusive caller-owned access, rejected overlaps
  unless provably disjoint, owner resumes after synchronous edit; `take` =
  explicit transfer, source binding dead; ownership ≠ identity of referent;
  no Rust-like lifetime syntax on ordinary source; compiler derives lifetimes or
  rejects.
- **Open:** call-site spelling for `edit`/`take`; disjointness proof rules
  (field-level? index-level?); noncopyable handle kinds; use-after-take
  diagnostics; interaction with closures (DR-04), tasks (DR-11), and cleanup
  ordering on traps/cancellation.
- **Dependencies:** DR-06 (lifetime derivation), DR-12 (memory model).
- **Recommendation:** none beyond commitments — this is the highest-risk semantic
  area for compiler work (flagged in the Specification Review as must-settle
  before native/FFI work, safe to leave provisional for interpreter-only slices).

## DR-06 Lifetimes, aliasing, refinements (DEC-002, DEC-003H; FD §§3.6, 5)

- **Commitments [reported]:** compiler-inferred lifetimes, no surface syntax;
  unprovable escapes diagnosed/rejected; flow facts (e.g. `Int > 0`, valid index)
  may refine types; mutation/aliasing invalidates stale facts; proof states are
  proved / refuted / unresolved / runtime-validated; no dependent-type promises.
- **Open:** proposition grammar fragment; cost/effort model for checking;
  external-assumption policy; runtime-validation form and cost; invalidation
  precision (whole-variable vs path-sensitive).
- **Dependencies:** DR-05, DR-12.
- **Recommendation:** start with the smallest checkable fragment (non-null index
  bounds from constants/branches) as optimiser input only — never as a soundness
  claim — and keep refinement failures advisory until the access model is frozen.

## DR-07 Effects and host authority (DEC-003F; FD §6)

- **Commitments [reported]:** compiler infers internal effects; public/restricted
  contexts declare a transitive ceiling (proposed `uses`); function values carry
  effect requirements; transitive checking through helpers/generics/closures; a
  declared effect NEVER grants authority — host/runtime grants separately;
  no-effect proves nothing about termination, allocation, GC, blocking, timing.
- **Open:** effect vocabulary; `uses` grammar and transitivity rules; host-grant
  transport (capability values? ambient registry?); real-time sub-contracts
  (no-alloc/no-GC/no-block); effect polymorphism for higher-order functions.
- **Dependencies:** DR-04 (effect-carrying fn types), DR-12/DR-13 (grant
  enforcement), DR-14 (stdlib capability signatures).
- **Recommendation:** freeze the vocabulary and ceiling-checking rule before any
  host stdlib slice (R2-V4 gate); grant transport can follow as a runtime design
  with adversarial tests (revoked/denied grants).

## DR-08 Errors: Result / Option / `?` (DEC-003G; FD §6)

- **Commitments [reported]:** `Result[T,E]` expected failure, `Option[T]` absence,
  as ordinary generic families; exhaustive `match` recovery; postfix `?` propagates
  compatible errors; no silent translation between unrelated `E`; unexamined
  `Result` diagnosed unless explicitly acknowledged; no general exceptions;
  defects/traps/cancellation are separate semantics.
- **Open:** `?` vs typed-hole `?name` tokenizer disambiguation (normative grammar
  work required — see Review RX-03); error translation/wrapping mechanism;
  discard-acknowledgement syntax; how `E` compatibility is judged (nominal?
  structural?); interaction with effects (error paths and `uses` ceilings).
- **Dependencies:** DR-01 (generic families must exist first), lexer freeze.
- **Recommendation:** specify the tokenizer split (whitespace/lookahead rule with
  fixtures incl. `n??` adversarial cases from the matrix) as part of the V0
  grammar freeze; defer wrapping-operator design until real stdlib I/O exists.

## DR-09 Data families: collections, text, numerics

- **Commitments [reported]:** independent value semantics (copy-then-modify never
  leaks); `Int` checked 64-bit; `Float`/`Float32` IEEE with explicit conversions;
  `Str` valid UTF-8 (byte indexing disallowed); `Byte`/`Bytes` distinct from text;
  `List[T]` growable logical value (seeded); `Array[T,N]` fixed; `Map[K,V]` with
  observable insertion order; safe indexing with statically eliminable checks;
  `Option.get`-style access returns `Option`; Unicode version + scalar/grapheme
  APIs; Map delete/reinsert order is an explicit conformance table.
- **Open:** literal syntax for arrays/maps; conversion operators and numeric
  suffixes; NaN/signed-zero/infinity fixture table; `Str` escape set beyond the
  seed's six; grapheme segmentation version and API; `Map` equality/hash law
  enforcement; `Array[T,N]` const-size grammar; bounds-check elimination proof
  rules; value-copy/COW observability edge cases.
- **Dependencies:** DR-01 (generic families), DR-02 (key abilities), DR-06
  (bounds refinements), C23 backend semantics (no UB-based implementation).
- **Recommendation:** freeze the numeric edge table (overflow/NaN/zero/rounding)
  early — it constrains both interpreter and C23 backend; leave collection-library
  breadth (algorithms, JSON, parsing) to bottom-up stdlib work (DR-14).

## DR-10 Modules and packages (DEC-004; FD §8)

- **Commitments [reported]:** one file = one module, identity from
  project-relative path; `pub` exports, private by default, opaque types allowed;
  qualified `import` + optional `as`, no wildcards; cycles rejected; imports run
  no hidden effectful initialization; entry files may hold top-level statements,
  importable modules use declarations + pure initializers; revision-bound
  inspectable public signatures; reproducible manifests; no network fetch via
  import; path/case semantics need cross-platform tests.
- **Open:** path resolution rules (root file? search paths?); case-normalization
  and collision behaviour per OS; `pub` placement grammar; opaque-representation
  checking; what "pure initializer" permits; signature query schema; manifest/lock
  format; top-level-statement rule for entry vs library in the byte-exact parser.
- **Dependencies:** grammar freeze (V0/V1), revision identity (exists), build
  tooling (V10).
- **Recommendation:** decide path/case rules and the entry/library statement rule
  before any multi-file compiler slice (R2-V1 gate); defer manifest format until
  a second real multi-module program needs it.

## DR-11 Structured concurrency (DEC-007; FD §9)

- **Commitments [reported]:** structured-by-default: scopes own children; proposed
  `async fn` / `spawn` / `await` (*proposed*); scope exit coordinates cancellation
  and safe resource completion; values copy/share immutably, `take` moves across
  tasks, ordinary `edit` never crosses task/await silently; shared state needs
  explicit identity + isolation; typed channels/services first, locks/atomics in
  typed libraries, raw primitives only in `danger`; cooperative observable
  cancellation; data-race-freedom ≠ deadlock-freedom.
- **Open:** task scope/result spelling; supervision and error-propagation rules;
  cancellation/cleanup ordering with FFI/GPU resources; scheduler documentation
  (no deterministic-scheduling claims); closure isolation across suspension.
- **Dependencies:** DR-04, DR-05, DR-12, DR-13.
- **Recommendation:** no concurrency implementation before DR-05/DR-12 have
  adversarial-tested fixtures (R2-V6 is correctly ordered late); keep all
  concurrency spellings *proposed* until then.

## DR-12 Memory, ownership, danger, FFI (DEC-006; FD §7)

- **Commitments [reported]:** compiler-directed hybrid (stack/direct → regions →
  immutable sharing/COW → precise tracing GC as *provisional* general fallback);
  safe explicit allocation via typed noncopyable owned handles (illustrative
  `OwnedBuffer[Byte]`, `memory.free(take handle)` — design sketches, not stdlib);
  `danger` narrows to specific raw operations, never disables checkable rules;
  unprovable premises are explicit trusted obligations, never "proved";
  GC roots/pinning for foreign pointers; GPU/DMA lifetimes outlive submissions
  through completion or supervised failure; no-alloc/no-GC/no-block contexts are
  separately verified properties.
- **Open:** allocator identity in the type contract; destructor/trap/cancellation
  ordering; `danger` scope grammar; FFI layout/alignment/pinning rules; collector
  choice (GC is provisional, not selected); real-time domain contracts; safe
  wrapper verification standard.
- **Dependencies:** DR-05, DR-06, adversarial review capacity (R2-V5 gate).
- **Recommendation:** treat the GC as unselected; require an independent
  memory-safety review plus ASan/UBSan-class evidence before any native slice
  claims ownership soundness. This entry must stay open through V5.

## DR-13 Testing, evidence, Terror Bats (DEC-008T; FD §10)

- **Commitments [reported]:** compiler-discovered `test "name" {...}` (proposed);
  `std.test` helpers; `pep test` / `--json` with revision, seeds, grants, status
  schema; tests excluded from production builds; Terror Bats as an *external
  adversarial adapter* with `PROVEN` = observed falsification; hostile-test
  catalogue (stale receipts, counterfeits, prompt-injected comments, false
  containment).
- **Open:** test declaration grammar; runner privilege/isolation model; property
  testing + shrinking policy; evidence privacy schema; Bats adapter protocol.
- **Dependencies:** DR-07 (grant model for runner), DR-10 (test discovery across
  modules).
- **Recommendation:** adopt the matrix's Phase A→D ordering; never let the
  manifest-driven dev-branch runner (52a75d6) be mistaken for the specified
  compiler-discovered design — they are different mechanisms.

## DR-14 Standard library layering (DEC-008; FD §10)

- **Commitments [reported]:** layered, Pep-written as early as expressible;
  narrow native intrinsics with justification; libraries preferred over keywords;
  Group A pure (text/unicode/bytes/collections/math/parse/JSON), Group B host
  (fs/io/process/env/time/random/net/task/sync/memory), Group C dev (semantic
  queries, edits, tests); every public API exposes checker-derived contracts
  (types/effects/errors/grants/platform/examples/tests); 28-Oct priority moves
  foundational Pep-written stdlib earlier in practice.
- **Open:** module paths and naming; intrinsic inventory and its ceiling;
  platform-availability annotations; cost documentation; JSON/parse API shapes.
- **Dependencies:** DR-01, DR-07, DR-09, DR-10.
- **Recommendation:** build bottom-up driven by compiler slices (byte/buffer →
  text → collections → JSON), each with runnable examples; count and justify
  intrinsics publicly per slice.

## DR-15 Semantic model, revisions, Semantic Notes

- **Commitments [reported + supersession]:** ONE checked semantic authority serves
  compilation/tests/tools/queries/edits; responses carry exact revision +
  checker/proof identity; stale data fails closed; byte-preserving edits with
  stale/ambiguous rejection; 28-Oct priority: compiler-derived knowledge + stage
  checkpoints are the architecture — `#@` annotation-centred semantics is
  superseded as core direction (notes remain allowed as advisory/provenance-only
  comments; formal contracts need explicit typed mechanisms).
- **Open:** query/proof-validity schema; stage-checkpoint vocabulary; selective
  cross-build knowledge reuse (approved research direction, unevidenced);
  invalidation rules; note attachment/retention format (PEP-SN-001 unmerged).
- **Dependencies:** session implementation (exists in-process), DR-07 (proof vs
  grant distinction).
- **Recommendation:** hold the supersession line — no `#@` execution semantics
  without a new Matthew decision; measure (not assume) any cross-revision reuse
  against clean-rebuild equivalence.

## DR-16 Grammar and surface freeze (DEC-009; FD §§2, 14; R2-V0)

- **Commitments [reported]:** small conventional grammar; explicit named-function
  types; no classes/inheritance, no macros, no operator overloading, no wildcard
  imports, no implicit conversions, no second AI-only syntax.
- **Open (must freeze before V1):** precedence/associativity table incl. `?`
  postfix; newline continuation + optional `;`; expression/statement block
  boundary; `Unit` omission shorthand; generic/constraint syntax; named arguments
  (shown in manual-memory examples, not accepted); string escapes; numeric
  suffixes; `pub` placement; capture syntax; `test`/`async` declarations.
- **Dependencies:** every DR above contributes rows; the freeze is the V0 gate.
- **Recommendation:** produce the freeze as executable positive/negative/
  incomplete fixtures (per the matrix), not as a prose grammar — fixtures are
  the normative artefact, prose describes them.
