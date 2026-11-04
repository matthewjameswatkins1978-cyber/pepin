# G-A4-1 (E8) — Smallest Useful Stdlib Closure from Compiler-A Evidence

**Campaign G, Agent 4 card 1 (PRIORITY 0).** Source: seed `57fe424` staged
sources (call-site counts measured this slice) + OCaml `describe` registry
(E1). No probes run. Labels: ESTABLISHED / INFERRED / UNKNOWN.

## 1. Measured builtin dependence (call sites, seed `57fe424`)

order: say / int_text / length / append / prepend / reverse / source_bytes /
byte_length / byte_at / byte_slice / utf8_slice / contains

| component | counts |
|---|---|
| lexer (481 lines) | 0/0/0/0/**16**/2/1/1/**19**/0/6/0 |
| parser (1802) | 0/0/13/1/24/**19**/1/1/0/0/0/0 |
| checker (2258) | 0/0/20/5/**119**/25/3/2/1/0/0/4 |
| emitter (495) | 0/**17**/1/**47**/38/1/0/0/0/0/0/0 |
| **TOTAL (~387)** | 0/17/34/53/**197**/47/5/4/20/**0**/6/4 |

## 2. Classification per area (G-A4-1 asked)

- **List[T] ops (`length/append/prepend/reverse/contains`, 335/387 calls):**
  the compiler's bloodstream — accumulator/quick-sort/scope idioms. NEEDED BY
  A: yes, heavily. Library-vs-runtime: `prepend`/`reverse` are O(1)-ish
  structural ops; a Pep-level list library over a smaller core is conceivable
  but the interpreter itself needs lists to run anything — IRREDUCIBLE
  runtime. Seed+staged support: full. Native: emitter has no lists at all
  (B3) — any native stdlib List is greenfield. Missing dependency: none for
  interpreted A; native List ABI for A2 (their lane, not prescribed).
- **Byte/source ops (`byte_at` 20, `byte_length` 4, `source_bytes` 5):**
  NEEDED: yes (lexer `byte_at` ×19). `source_bytes` is ambient authority —
  irreducible host grant (E4-T2), cannot be a library. `byte_at`/`byte_length`
  are the minimal byte interface; keep native. Seed/native: full seed; native
  emitter never touches bytes (subset excludes Str). Missing: BOUNDED BUFFER
  (see R3).
- **UTF-8 (`utf8_slice` 6, all lexer):** NEEDED: yes, exactly once (utf8_check
  path). Library-vs-runtime: demotable to a `byte_at` loop ONLY at >10× step
  cost (E2 F-C, unmeasured) — keep native, no action.
- **`byte_slice` (0 calls) + `say` (0 calls):** NOT needed by compiler A.
  `byte_slice` is dead weight for A (byte_at+length cover every use);
  candidate for E2-(c) demotion or removal from the bootstrap subset — flag,
  do not prescribe. `say` is debug/host surface, keep for humans.
- **String formatting (`int_text` 17, all emitter):** NEEDED: yes (C codegen
  embeds integer literals). Demotable to digit arithmetic (E2 softest target,
  unmeasured). Keep native for now.
- **Errors/Result:** NO Result/Option/error-value type exists — `describe`
  registry has no error types; failures are host-collected `CheckDiagnostic`
  records, never values. Classification: not a missing stdlib API but a
  missing LANGUAGE capability (user generics beyond `List[T]` do not exist).
  Any Result/Map proposal depends on a generics decision — flag as
  language-gap, out of stdlib scope.
- **Paths/file I/O:** ABSENT entirely — no path type, no read primitive.
  Compiler A reads sources through the host `open` + `source_bytes` grant.
  Needed for self-hosting Road 1 (compiler A must open its own sources), but
  requires a sandbox/authority decision first (`trustedLocal:true` today).
  Flag for Matthew, not a library to write yet.
- **Allocation:** invisible — no allocator API; lists/records just grow.
  Native side: A2 owns descriptor lifetimes (their F-slices). No stdlib item.
- **Diagnostics:** producer-side only (checker builds records; host prints).
  No formatting API needed beyond `int_text` + (missing) concat.

## 3. Ranked top-5 missing APIs (shortest testable program each)

- **R1. `str_concat(a: Str, b: Str) -> Str`.** Strongest evidence: seed
  REJECTS string `+` (`PEP_TYPE_MISMATCH`, A3 S6 TESTED) and the emitter works
  around it with 47 `append`s into `List[Str]` fragments assembled host-side.
  Concatenation is currently UNEXPRESSIBLE in Pep. Test: `concat("ab","cd")
  == "abcd"` + seed oracle + Clang/GCC run + overlong-input behavior. Native:
  trivial C. Unblocks emitter fragment assembly as first-party Pep.
- **R2. `str_join(parts: List[Str]) -> Str`.** Same evidence family; joins the
  emitter's `sourceParts` pattern natively instead of host-side. Test: join of
  `["if (", cond, ")"]` fragments. Dependency: R1 or independent C loop.
- **R3. Bounded `Bytes` buffer (`push/length/byte_at`).** Lexer does 19
  `byte_at`s + 6 `utf8_slice`s with no assembly buffer; parser models strings
  as `List[Str]` (AstString) — O(n) consing where a buffer belongs. Test:
  assemble "hello" from bytes, assert length/content. Native: malloc'd buffer
  (A2 owns lifetimes). Gives future room for a Pep-level utf8 path.
- **R4. `text_to_int` (digit-string → Int).** Parser must convert digit bytes
  today (mechanism unread this slice — UNKNOWN whether hand-rolled over
  `byte_at`); standardizing it removes a hand-rolled copy and tests the
  E2-(c) demotion path on the softest arithmetic target. Test: `"42" -> 42`,
  `"-7" -> -7`, `"4x"` refused with exact code.
- **R5. `read_source` (path → SourceBytes), DECISION-GATED.** Road-1 needs it;
  cannot be specified until the sandbox question is answered (host is
  `trustedLocal` today; a path primitive without a capability story is a
  hole, not a feature). Test sketch held until Matthew rules. Ranked fifth
  for honesty: most important long-term, least actionable now.

## 4. Status labels

INVENTORY (not a work order): 2 dead-weight findings (`byte_slice`, `say`
unused by A), 1 language-gap (`Result`/generics), 1 decision-gate (file I/O),
5 ranked APIs with tests A2 could implement. Nothing prescribed, no lane
blocked. Next: G-A4-2 (E7) — needs A1 Q1; Q4 already answered (A3-058:
forgery-first failure ranking, per-phase accounting as the only fast settler).
