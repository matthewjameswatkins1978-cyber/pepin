# DRAFT: Native SourceBytes grant contract — entry-bound, revision-attested (A1 host boundary)

**Status:** DRAFT for A2/A3 review — 2026-11-06 (A1; Lucy's LUCY-20261106-004 item 3
"coordinate host-owned `source_bytes()` target-grant contract"). Candidate7
`6dce37d` untouched; no budgets changed.

## 1. Measured gap (A2 `495e6b1` receipt 04; A4 `409dd9a` frontier)

- Byte access on a SourceBytes **parameter** lowers natively (checks valid, emits;
  strict Clang/GCC; runtime `pep_byte_at`/`pep_byte_length` substrate present).
- `source_bytes()` — the only way a Pep program can OBTAIN bytes — has **no
  native lowering**: "Pep C23 cross-chunk call has no resolved call fact". The
  seed `run` correctly refuses it standalone (`PEP_RUNTIME_SOURCE_CONTEXT`):
  bytes are a host-granted ambient authority, not a library call.

## 2. Contract: the grant rides the entry declaration, not the call

`semanticTarget.v2` already carries `{document, revision, entryFunctions}`. The
grant is a new OPTIONAL, host-authored field **`sourceGrant`** on that value:

- `"sourceGrant": {"mode": "entry-parameter"}` — the HOST constructs the native
  `main` wrapper so the declared entry function receives the target's bytes as
  its first `SourceBytes` parameter. The bytes are exactly the `open_bytes`
  payload of `document`/`revision` (single semantic source; provenance = the
  already-attested target identity).
- With the grant present, the Pep source declares the entry as
  `fn main(source: SourceBytes) -> Int { ... }`; the emitter treats
  `source` as an ordinary parameter (the shape that already lowers).
- **`source_bytes()` as a CALL stays refused** in native lowering. No ambient
  callable is added; obtaining bytes any other way is not expressible. This
  keeps Stage-0 authority where it lives: the host grants bytes once, at the
  entry, bound to the target revision.

## 3. Invariants (fail-closed, reviewable)

1. **One semantic source:** the only bytes ever reachable natively are the
   opened target's; no second read path, no cached global.
2. **Revision-bound:** the wrapper aborts (`PEP_RUNTIME_INVALID_SOURCE_BYTES`)
   if constructed with a length mismatch vs the host-recorded payload.
3. **No silent authority:** without `sourceGrant` in the semanticTarget, native
   lowering of an entry expecting SourceBytes refuses exactly as today
   ("no resolved call fact" is then precise: no grant was declared).
4. **Deterministic:** same host grant + same target bytes ⇒ same C; the
   existing bundle determinism probes apply unchanged.
5. **Stage0 boundary:** the grant is bootstrap orchestration (host/protocol),
   to move into Pep-written Lucy later; it must not grow type/scope logic.

## 4. Concrete exit criteria (what A2/A1 implement after approval)

1. A1: host `emit()` learns the optional grant (one branch, default off);
   A2: emitter wrapper branch lowering an entry `SourceBytes` parameter from
   the granted payload — the rest already lowers.
2. Vertical: `fn main(source: SourceBytes) -> Int { return byte_at(source, 0) }`
   over a granted target ⇒ emitted ⇒ strict Clang+GCC ⇒ matches seed oracle on
   the same bytes (including NUL/UTF-8 first-byte cases A2 already measured at
   substrate level).
3. Negative: same source WITHOUT the grant ⇒ current refusal, unchanged text.
4. A3 re-gate trigger is the published candidate that carries it — the frozen
   Full-v2 rows stay untouched; hostile ingress probes re-run on the new host
   surface.

## 6. v1 wire contract — FINALISED from A2's implemented vertical (BOOT-A3-016 PASS)

A2 implemented and A3 verified (clang+gcc NUL/UTF-8, negatives exact) a simpler
shape than an explicit wire field. v1 therefore makes the grant **derived, not
declared** — no new `semanticTarget` field ships in v1:

- **Grant exists iff** the CHECKED entry function declares a parameter of type
  `SourceBytes` AND that function's name is a member of
  `semanticTarget.entryFunctions` (both fail-closed inputs that already ship).
- **Ownership/identity (REVISED 2026-11-06, A2 divergence BOOT-A2-20261106-40):**
  embedding the payload at assembly time is measured-impossible in v1 (fixed
  2-arg emitter; 1 MiB -> ~6 MiB hex through frozen transport), so v1 grants
  via **(i) argv/file**: the wrapper's ONLY byte input is ONE host-named
  operand, opened once, read fully, bound, freed (`argc<2` ->
  `PEP_RUNTIME_SOURCE_CONTEXT` before the entry runs). Revised rule: **single
  source multiplicity** - no second byte source, no cached global, no
  scanner; the host test verifies the operand's contents equal the
  `document`/`revision` payload (equality host-verified; emitter-enforced
  identity binding is v2). `source_bytes()` as a CALL stays refused.
- **Host caller requirements (from A2's merged consumption, RECEIPT 41):**
  `pep-c23-checker-sigs` must be registered AND activated before
  `emit_granted()` is called (the checked report elides entry params); typed
  refusals must be asserted via `GrantRefusal.code`, not the rendered message.
- **Fail-closed refusals (unchanged text):** an unlisted entry whose checked
  shape expects `SourceBytes` keeps today's refusal; a listed entry with no
  such parameter emits normally; no `source_bytes()` call lowering is added.
- **v2 reserved (not v1):** an explicit declared `sourceGrant` field for
  multi-entry/second-grant control (`mode`, `paramIndex` in 0..arity-1,
  strict additionalProperties=false, host-side validation before any tool
  invoke). Ships only with a new review line in this draft.
- **Host acceptance (G1, A1):** `pep_c23.py` `emit()` must pass real
  `entryFunctions` (currently `[]`) and A1's integration test asserts the
  derived-grant behaviour at the merged host+emitter SHA: granted vertical
  NUL/UTF-8/ASCII vs A2's oracle, plus the two fail-closed shapes above.

## 7. Non-goals

No `utf8_slice`/`byte_length`-call lowering beyond the existing parameter shape;
no ambient `source_bytes()`; no B/C-stage semantic compilation changes; no
budget, cap, or frozen-test edits.
