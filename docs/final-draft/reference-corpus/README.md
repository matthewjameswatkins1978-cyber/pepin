# Pepin reference corpus: proposed language vNext

**Status: DESIGN FIXTURES ONLY.** This corpus is not accepted as a frozen grammar and is not expected to compile on the current OCaml seed, Pep-written compiler, or C23 emitter. It must not be included in a production test glob until individual features are implemented, versioned and accepted.

**Base:** 27 October 2026 approved consolidated language draft at `docs/final-draft/PEP-LANG-FINAL-DRAFT-2026-10-27.md`, with subsequent 30 October discussion of `use`, `try`, implicit final-expression returns and a constrained user-definable `ability` system.

## Principles

1. **Power at the back. Beautiful at the front.**
2. **Infer what is safe. Explain what is inferred. Ask only when ambiguity matters.**
3. Test whether AI-primary programmers can obtain compiler-owned semantic answers without reconstructing entire source trees.
4. The checker and source revisions own facts, not model confidence. Every example is a proposal until acceptance.

## Positive sketches

| File | Features exercised | Proposed observable behaviour |
|---|---|---|
| `examples/01-configuration-parser.pep` | `try`, `Result`, `Option`, exhaustive `match`, implicit final return | Valid two-line config produces a record; invalid integer/flag returns typed error; missing line never indexes unsafely |
| `examples/02-data-aggregator.pep` | independent value collections, `edit`, typed map, `Option`, checked arithmetic | Empty list returns `None`; counts and total match input; overflowing signed Int traps rather than wraps |
| `examples/03-http-service.pep` | `use`, public API, pure handler, effect ceiling, host authority, `take` resource transfer | Requests route deterministically; server startup can fail as `Result`; importing HTTP does not grant network permission |
| `examples/04-concurrent-fetch.pep` | structured `task`, `spawn`, `await`, cancellation, typed task outcome | On one failure sibling is cancelled/drained; task-level errors do not silently convert to application errors |
| `examples/05-owned-memory.pep` | typed owned buffers, explicit `edit` / `take`, bounded `danger`, foreign authority | Exactly one owner releases buffer; device read needs a host-granted MMIO capability and auditable trusted obligations |

These fixtures focus on a *language contract*, not on proving that library APIs exist. Proposed stdlib signatures are assumptions to be tested and may be renamed. See `BOUNDARIES.md`.

## Provisional imported API contracts

For a fixture to become executable, the library must expose stable, checked APIs consistent with these signatures:

- `text.lines(Str) -> List[Str]` (line handling must be specified).
- `integer.parse(Str) -> Result[Int, integer.Error]`.
- `List[T].get(Int) -> Option[T]` (non-trapping).
- `map.empty[K,V]() -> Map[K,V]`, `map.get(Map[K,V], K) -> Option[V]`, `map.put(edit Map[K,V], K, V) -> Unit` (requires eligible key abilities).
- `http.listen(Str, Int) -> Result[http.Server, http.Error]`, `http.serve(take http.Server, fn(http.Request)->http.Response) -> Result[Unit, http.Error]`, and `http.get_text(Str) -> Result[Str,http.Error]`.
- `memory.allocate[T](Int) -> Result[memory.OwnedBuffer[T],memory.Error]`, `memory.write(edit memory.OwnedBuffer[Byte], Int, Byte) -> Result[Unit,memory.Error]`, `memory.free(take memory.OwnedBuffer[T]) -> Result[Unit,memory.Error]`.
- `device.read_volatile(device.MmioRegion, Int) -> Int` is restricted to a `danger` block with validated region bounds/alignment and host-authorised MMIO capability.

No signature above should silently broaden ambient IO, permissions, numeric conversion, aliasing or unsafe access.

## Acceptance path

1. Resolve listed conflicts with the older draft, recording explicit decisions before code work.
2. Produce a machine-readable grammar/AST and typing fixtures for every source example and each negative case.
3. Pin exact expected diagnostics and source byte spans (LF and CRLF), including invalid/incomplete distinctions.
4. Build stdlib signatures and effects, then compare seed checker, Pep checker, interpreter and C23 backend for all supported features.
5. Add adversarial tests for resource cleanup, orphan impls, task cancellation, alias invalidation and NaN map keys.
6. Generate revision-bound semantic query receipts and source-preserving edit previews.
7. No new language acceptance or default-branch merge without review and evidence.

**Do not claim success from mere parseability or from a missing runtime capability.**
