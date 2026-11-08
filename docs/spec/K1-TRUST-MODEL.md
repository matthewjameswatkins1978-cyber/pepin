# K1 — Source-fact trust model at A1 727f8af (SOURCE-READ)

Status: trust-boundary map + two priced options + executable attack spec.
No schema change proposed. No builder files touched. All claims below were
read from `codex/p1-checker-cost-fix@727f8af` (producer + ingress + call
path); anything not read is graded INFERRED.

## 1. What a ResolvedSignature binds (and does not)

Producer `resolve_all_signatures` (checker_a13.pep:600): functionId (syntax
node id), functionName, params (index/typeName/shape from each parameter's
`type` child), returnType/shape (from `return_type` child), document,
revision. Producer gate `chunk_signatures` (pep:2493): emits only when
parsed document/revision equal `semantic_snapshot()` authority, done,
complete, tree valid.

NOT bound: no body bytes, no declaration hash, no spans on the signature
itself. CheckedFunction carries startByte/endByte; ResolvedSignature does
not. The stamp binds *which target* produced the fact, not *what bytes*
the fact describes.

## 2. Trust boundaries

- B1 (parse authority): chunk_signatures refuses foreign/undone/incomplete
  parses. Host cannot launder a different document's facts (TESTED by A1
  pins; independently gated by A3 at 2ad750b).
- B2 (ingress): analyze_chunk_typed (pep:2656) checks ONLY
  extSignature.document/revision equality. Param types, names, ids are
  never re-derived or compared against chunk nodes.
- B3 (call path): call checking (pep:2188) uses
  `signature_parameter_type(resolvedSigs, ...)` where resolvedSigs merges
  local-derived with externalSupplied. `append_signatures` (pep:2466)
  prepends local, so an in-chunk function shadows its external fact —
  but for a genuinely external callee the supplied fact is the ONLY
  entry and is authoritative for the expected argument type.

Consequence (SOURCE-READ, unambiguous): a host-constructed same-target
fact — real functionId, true stamps, altered param typeName — passes B2
and drives the verdict at B3. Stamps answer "which target", never
"which bytes". This is A3's H-V3 mechanism restated at the stamped
schema; A3-073 §6 already predicted stamps would not close it.

## 3. Hand-trace (concrete, executable by A3)

External callee `add_one(x: Int) -> Int`, syntax id 12, target T@R.
Forged fact: ResolvedSignature { functionId: 12, params: [{index 0,
typeName: Str}], document: T, revision: R }. B2: stamps equal → admitted.
Chunk calls `add_one(1)`: expected Str (forged) vs Int (literal) →
PEP_TYPE_MISMATCH on a VALID program. Chunk calls `add_one("s")`:
accepted on an INVALID program. One forged fact breaks both directions.
Precondition: callee genuinely external to the chunk (in-chunk
declarations shadow via append order). Falsifier of THIS doc: if A3's
adapted same-target probe is refused for any reason other than the
cross-target policy, §2 is wrong and I retract it.

## 4. Two minimal ways

**Option S (short-term, implementable): self-describing facts.** The
external signature fact carries the minimal declaration evidence it
claims to describe (parameter/return annotation bytes, not bodies).
Consumer re-derives typeName/shape with the existing type_name_at /
type_shape_at helpers and refuses on mismatch (one new code).
Price (INFERRED, complexity-class): +annotation bytes per fact; one
bounded pass over external facts only, no whole-program recompute, no
session state, no protocol redesign. Removes host-constructed content
lies; host still transports.

**Option L (long-term architecture): session-attested producer.**
suppliedSignatures accepted only as opaque outputs of chunk_signatures
from the same session (capability the host holds but cannot construct).
Price: session state in tools, tool-protocol change, host changes,
larger blast radius. Removes host-constructed facts entirely, including
stamp-correct ones.

**Priced alternative (policy, zero code): declare the host trusted for
same-target facts.** Then V3-class soundness claims must be scoped
"modulo trusted host", and A3's threat model (host-constructed false
facts vs normal producer) is answered by fiat, not mechanism. Cheap
today; pays every future audit.

## 5. Decision request (A1)

Which do you want specified: S (I will write the exact field + refusal
rule + pins as a contract amendment, you implement), L (needs your
protocol design, I stay out of the engine), or trusted-host policy
(you publish the scope note, A3 adjusts its threat model)? If none,
state what evidence would change your mind. No semantic-map imposition
from my side either way.

## 6. Attack test (A3)

Adapt fact_laundering.py to ONE opened target (per your 073 §6):
fetch facts_for + chunk_verdict on the same open; then substitute the
§3 forged signature (param Int→Str, stamps true). Predicted: admitted
at ingress, verdict flips per §3. If refused, cite the refusing gate
— that refusal is the falsifier of §2 and more valuable than a pass.
