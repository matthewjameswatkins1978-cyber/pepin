# Pepin priorities: foundations and one semantic system

**Decision date:** 28 October 2026  
**Status:** Matthew-selected project priorities. This is a planning/handoff amendment, **not** a language-grammar change, implemented feature, accepted compiler gate, approval to merge, or permission to advance `CURRENT.md` / `manifest.json`.

## Current selection (supersedes earlier four-item shortlist)

Matthew reviewed six recovered ideas, initially selected 1/2/5/6, then **explicitly deferred 6** because foundational standard-library work is far more important.

| Recovered idea | Current direction | Role |
| --- | --- | --- |
| **1. Lucy's evolving understanding of programs** | **Prioritise** | One compiler-derived, evidence-aware semantic model, with useful knowledge safely retained and queried |
| **2. Bottom-up Pep-written standard library** | **Prioritise as the main practical build focus** | Compose progressively richer libraries from a small, sound foundation |
| **5. Compiler checkpoints and continuous development** | **Prioritise with 1, NOT separately** | Read-only, source-revision-bound observations/queries into that same semantic model |
| **3. Rabbit CLI / interactive `pippin learn`** | **Defer** | Valuable user experience, not a current compiler/stdlib dependency |
| **4. Sartorial, Rust utilities and Rust-to-Pep migration** | **Defer** | Later real-world validation and migration tooling; no current porting campaign |
| **6. Paradigm freedom / semantic unity research** | **Defer** | No near-term OOP, logic-language, receiver-sugar or paradigm-framework initiative; existing Pep language decisions remain in force |

The item numbers above come from the 28 October recovered-ideas review, **not** from G1–G10, A1–A15, or the separate five-step suggested development order.

## Practical priority: build the library upwards, in Pep

**Rule:** Once existing checked Pep semantics can implement a facility safely and usefully, prefer to implement it in Pep using smaller, already-tested pieces. Add a compiler intrinsic/native helper only when a genuinely irreducible operation, bootstrap limitation, safety boundary or measured performance case justifies it. Do not force source-language purity at the expense of correctness.

Work as dependencies and evidence permit, not as an unconditional fixed list:

1. **Minimal substrate:** primitive values, checked access and memory/resource interfaces; raw bytes vs valid UTF-8 strings; bounded source bytes; typed errors; carefully scoped native/OS interfaces. Document each irreducible helper and its effects, ownership, safety and availability.
2. **Reusable foundations:** safe buffers/builders, useful generic/value containers and basic string/byte operations, including correct length/index/encoding semantics, allocation and growth contracts. Avoid treating an immutable O(n) list append as an efficient general builder. Choose structures from measured workloads.
3. **Composed libraries:** collections (lists, maps, sets, queues), iterators and algorithms (search/sort/filter), parsing and data representation (including JSON) using lower-level facilities instead of proliferating builtins.
4. **Practical systems and development services:** authorised files/paths/IO, tests, error/diagnostic support and later more demanding standard-library domains. The package/library API should be consistent, documented, typed, tested and inspectable through Lucy.

Some layers overlap; for example, compiler-written parsing and test utilities need to exist before the full general library does. Keep the initial implementations as small vertical slices used by real compiler/examples. **Do not turn this into a requirement to implement the complete Go/Python library before continuing compiler development.**

For each useful slice, record: the lower-level dependencies it reuses, the minimum compiler/runtime primitives it needs, direct tests and hostile tests, semantic/effect/memory boundaries, practical source example, performance/cost evidence where relevant, and what remains unsupported. Support ordinary multi-file examples as soon as the module/toolchain permits.

## One Lucy: compiler-derived knowledge AND checkpoints

**Unify ideas 1 and 5.** Lucy's checked semantic model remains the only compiler authority. A checkpoint is an inspectable, versioned view of an analysis stage; an evolving knowledge record is selected evidence derived from those stages and, where appropriate, linked build/test observations. **They are not separate semantic engines.**

- Begin with the existing OCaml seed's versioned source snapshots, typed holes and `semantic_snapshot()`. Introduce narrowly useful read-only stage receipts and on-demand queries before attempting cross-build persistence.
- Bind every fact to exact source/dependency revisions, compiler/backend/options, scope, and validity conditions. Distinguish proved/checked vs observed vs hypothetical vs unresolved. Never trust an old cached result for a new source revision without valid rechecking/invalidation.
- Retain selectively useful facts across compilations **only after** clean-build equivalence and measurable benefit. A cache or knowledge store must be disposable and must not determine Pep semantics.
- Eventually link source and checked program parts, compiled artefacts, tests and optional runtime observations into a coherent development view; runtime samples and agent suggestions are evidence, not proof.
- No always-on LLM at compile time, unsolicited events through current one-response-per-request JSONL protocol, second compiler server, hidden AST rewriting, global semantic registry or general theorem-prover mandate.
- Use resource limits, host authority and normal typed/effect-safe source edits. Any intervention is a later, separately reviewed revision-guarded transaction, never mutation of a running checker AST.

### Superseded research: annotation-led Semantic Notes

The old programmer-authored `#@` Semantic Notes / three-source-layer approach is **not** the selected architectural centre. Its draft [PR #13](https://github.com/matthewjameswatkins1978-cyber/pepin/pull/13) should not be adopted or merged as the current direction. Retain historical research on claims/proofs and comments, but **default to compiler-derived facts and optional ordinary explicit contracts, not a new mandatory annotation language**. This priority supersedes the older G6 Semantic Notes wording in the long campaign packet; the newer direction is recorded in Basic Memory.

## How this fits the active work

- **Accepted `master` baseline:** A8. **Development:** the authorised `campaign/pep-v01-sustained-build-20261027` branch contains experimental Pep-written lexer, parser, checker and restricted C23 generation. Their tests and actual source determine implemented truth.
- Near-term engineering still includes A13 correctness/parity, proven resource/step bottlenecks (especially nested calls), strict supported native C23 subset and test evidence. None of these should be bypassed just to declare a standard-library feature complete.
- The sustained campaign already has first-party test + Pep-written stdlib work in **G5**, with prerequisites in G4, and provenance/semantic query work in G2/G6. This document **clarifies priorities**, rather than replacing the authorised mission or requiring agents to stop other coherent independent work.
- Future multi-paradigm research (#6) is **not** a reason to introduce classes, DSLs, global method resolution or implicit semantics. Already accepted language commitments (types, values, functions, module/effect/error/safety rules) remain unchanged.
- Preserve all deferred ideas in notes. Revisit them after an actual Pep application or later maturity presents a concrete requirement.
- The 3-Slice Review Cycle remains nonblocking. Small reversible progress can continue; public `master`, accepted release tags, `CURRENT.md`, `manifest.json`, capability claims and consequence-heavy approvals require their established separate evidence/authority.

## Authority / related records

- [Sustained campaign mission](missions/PEP-SUSTAINED-IMPLEMENTATION-20261027.md) and [start pointer](missions/START-LUNA.md).
- [Compiler campaign checkpoint](COMPILER_CAMPAIGN_CHECKPOINT.md) and [implementation status](DESIGN.md).
- [Roadmap and acceptance pointer](packets/CURRENT.md).
- [Accepted final design draft PR #14](https://github.com/matthewjameswatkins1978-cyber/pepin/pull/14): historical design reference, **not** evidence that the whole language exists. Later compiler-derived-knowledge decision supersedes its `#@`-centric source-annotation wording.
- [Basic Memory: prioritisation record](https://app.basicmemory.com/notes?id=cloud%7C703e9fd6-6c96-7c2a-6f0d-4a73c11281ba%7Cfcb7313a-e158-4d76-988a-2e54978bc067%7C563c337a-eb00-4cb4-aa42-95a2ba584a73&explorer=project%3Acloud%7C703e9fd6-6c96-7c2a-6f0d-4a73c11281ba%7Cfcb7313a-e158-4d76-988a-2e54978bc067) and its specific compiler knowledge, checkpoint, stdlib and deferred multiparadigm notes.

**Precedence:** accepted language semantics and proven implementation evidence govern actual behavior; this later user selection governs project priority where an earlier design wish list or optional proposal would otherwise distract. No feature is implemented merely because it is prioritised.
