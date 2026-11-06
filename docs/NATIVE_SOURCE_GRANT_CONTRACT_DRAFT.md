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

## 5. Non-goals

No `utf8_slice`/`byte_length`-call lowering beyond the existing parameter shape;
no ambient `source_bytes()`; no B/C-stage semantic compilation changes; no
budget, cap, or frozen-test edits.
