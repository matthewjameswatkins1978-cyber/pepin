# B4 Cycle 1 Slice 2 — Minimal Authoritative Cross-Chunk Call Contract

**Packet:** PEP-WB-A4-20261104-B, Cycle 1 Slice 2. **Branch:** `spec/agent4-spec-lab`
**Pins:** A1 `2f939a0` (`docs/CHECKED_CHUNK_CONTRACT.md` = `pep-checked-chunk-v1`,
`tests/test_chunk_cross_call_facts.py`, `tests/chunk_helper.py`); A2
`ea0bc9a` (cross-chunk emission refuses without known callee — campaign
preflight); A3 `24cd5b6`; integration `c69e15d` (unverified — no claims).
All field names below are read from A1's pinned sources, not invented.

## 1. What the contract actually carries today (IMPLEMENTED + TESTED at A1 pin)

- `CheckedFunction`: `name`, `semanticId`, `syntaxId`, `arity`, `returnType`.
  **No `params` field** (pinned by test: `assertNotIn("params", …)`).
  External declarations share placeholder ids: `semanticId` 9000,
  `syntaxId` 1000000000.
- `ResolvedSignature`: parameter name+type pairs (`ptypes`), `returnType`
  (`rtype`). The ONLY carrier of parameter facts.
- `ResolvedCall`: `callerId` (real chunk id, e.g. 100000), `calleeId`
  (**9000 placeholder — not an identifier**), `syntaxId` (chunk-remap index
  of the call node whose `text` names the callee).
- Two id spaces, must stay separate: checker synthetic `synid` (chunk-local
  lookup key, never a document id) vs contract `node` (original document node
  id of the header chunk that produced a signature — the only revision-tieable
  identity). Mixing them once silently suppressed `invalid` (regression-kept).

## 2. Rules (PROPOSED normative language)

- **B4-CALL-01 (signature-first):** a cross-chunk caller MUST be lowered from
  `ResolvedSignature` (`ptypes`/`returnType`), never from `CheckedFunction`
  alone. Rationale: parameter facts exist nowhere else.
- **B4-CALL-02 (no placeholder identity):** `semanticId` 9000 /
  `syntaxId` 1000000000 MUST be treated as "external, identity withheld", never
  as a callee address. Any consumer joining on 9000 is joining on nothing.
- **B4-CALL-03 (missing-target refusal):** a call whose callee has no supplied
  signature from this document+revision MUST be refused (A2's current refuse
  behavior is the correct fail-closed posture; it needs a declared code, not
  silent absence).
- **B4-CALL-04 (revision-bound signatures):** a signature is usable only with
  matching `(document, revision)` provenance via `chunk_signatures`; otherwise
  refuse (`CHUNK_UNSUPPLIED_SIGNATURE` family / stale-revision refusal).
- **B4-CALL-05 (binding identity):** external binding facts MUST carry scope
  identity, not bare names — A1's `utf8_check` 21/21 fix (binding-id aliasing)
  and the residual cross-chunk id collision show bare-name/synthetic-id joins
  collide. Identity shape is A1's to declare; the requirement is collision
  refusal, not a specific encoding.

## 3. The text-link gap (INFERRED weakness → precise recommendation)

Today the ONLY cross-chunk callee link is call-node `text` (the name string).
That breaks under seed-legal programs: same-name fn/type coexistence is
`valid` (A3 set-21), so text cannot disambiguate `callee` the function from
`callee` the constructor; future overloads would break it further. The
contract already owns the missing piece: signature provenance carries
contract-side `node` (original document id of the callee's header chunk).
**Recommendation to A1/A2 (R-CALL-1):** `ResolvedCall` should carry the
callee's contract-side node id (or the signature provenance must be joined on
`(document, revision, node)` before lowering), so lowering never depends on
name text. Until then, text-linked lowering MUST be restricted to chunks whose
closure proves the name unambiguous (ties to B4-CLOSURE-01), else refuse.
This is an interface recommendation, not a unilateral freeze.

## 4. Test matrix for Agent 3 (no new harness; extends cross-call + matrix style)

- T-CALL-1: callee/caller split across chunks, valid program → staged `valid`,
  calls resolve via signature (control).
- T-CALL-2: callee signature withheld → staged refuses with declared code
  (missing-target; A2 behavior pinned at emitter level).
- T-CALL-3: same-name fn + union constructor `callee` in scope → text-linking
  must NOT resolve to the wrong target (refuse or resolve-correctly; wrong
  native code = falsification of any text-only lowering).
- T-CALL-4: signature from another document/revision → refuse (provenance).
- T-CALL-5: duplicate callee names across chunks → refuse (closure interaction
  with B4-C1 F2).
- T-CALL-6: binding-id collision across chunks (A1's residual-7 shape) →
  refuse, never merge.

## 5. Interface recommendations for A1/A2 (R-CALL-1..3)

- R-CALL-1: callee contract-side node id on `ResolvedCall` (or mandatory
  `(document, revision, node)` signature join before lowering); §3.
- R-CALL-2: declared missing-callee refusal code shared by checker-staged and
  emitter paths (currently A2 refuses; code unnamed — name it).
- R-CALL-3: binding-fact identity format published in the contract doc (names
  alone insufficient per A1's own aliasing finding); A3's T-CALL-6 then has an
  oracle to test against.

## 6. Status labels

ACCEPTED: fail-closed refusal on unknown callee (direction; A2 implements).
PROPOSED: B4-CALL-01..05, R-CALL-1..3, T-CALL-1..6.
IMPLEMENTED: v1 contract + placeholder ids + signature-first shape (A1 pin).
TESTED: cross-call facts tests at A1 pin (valid caller, placeholder ids,
text-link, no-params); residual-7 collision and aliasing fix are A1-measured,
not independently re-run here.
UNKNOWN: integration `c69e15d` end-to-end; native execution of any cross-chunk
call; binding identity encoding (A1 to declare).
