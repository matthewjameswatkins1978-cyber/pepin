# Revision identity + limit adversarial set (V0 set 3)

All observations via `./pep.ps1 session --jsonl` (schema v3, OCaml
in-process session) from base `805062b`. Each sequence runs in ONE
session process (document IDs are per-session). Raw transcripts
truncated to the decisive fields; full shapes match SESSION_PROTOCOL.md.

## R1 — stale `expected_revision` rejected, current revision preserved

Sequence: `open("fn main() -> Int { return 1 }\n")` → rev1
(`sha256:c4564bf0…`); `apply_edit(rev1, [26,27), "2")` → rev2
(`sha256:8ad64165…`, status `valid`, value now `2`); replay
`apply_edit(rev1, [26,27), "3")`.

| oracle | result |
|---|---|
| SPEC (SESSION_PROTOCOL.md) | stale revisions rejected without changing current revision |
| OCAML | `TESTED` PASS — outcome `error`, `PEP_STALE_REVISION` ("Edit expected a revision other than the document's current revision"), `currentRevision` still rev2. Forged/stale semantic facts cannot be smuggled through an old revision. |

## R2 — edit range splitting a UTF-8 code point rejected

Sequence: `open('say("hé")\n')` (é = bytes 6,7) → rev;
`apply_edit(rev, [6,7), "X")`.

| oracle | result |
|---|---|
| SPEC | byte positions inside a UTF-8 code point are rejected |
| OCAML | `TESTED` PASS — outcome `error`, `PEP_UTF8_BOUNDARY` ("Edit range splits a UTF-8 code point"). No mojibake revision is created. |

## R3 — source-byte transport cap enforced before analysis

- `open_bytes` with 65,537 space bytes → `TESTED` PASS: outcome
  `error`, `PEP_SOURCE_BYTE_LIMIT` ("exceeds 65536 bytes"),
  `parse_count: 0` (rejected before any analysis/fuel is spent).
- `open_bytes` with exactly 65,536 space bytes → `TESTED` PASS:
  outcome `ok`, retained with content revision
  (`sha256:0beca823…`), status `valid`, empty AST. The boundary is
  exactly 65,536 accepted / 65,537 rejected.

Parser-vs-transport note (from B0 peerEvidence, not re-probed here):
large *valid* Pep sources can additionally fail inside analysis with
`PEP_RUNTIME_STEP_LIMIT`. The transport cap and the tool-fuel limit are
therefore distinct, independently observed boundaries — do not conflate
"opened" with "analysable".

## R4 — forged document/revision query rejected

Sequence: `open(...)` then
`query(document: "doc-UNKNOWN", revision: "sha256:000…0")`.

| oracle | result |
|---|---|
| SPEC | unknown documents/revisions are not resolvable |
| OCAML | `TESTED` PASS — outcome `error`, `PEP_DOCUMENT_NOT_FOUND` ("Document identity was not opened in this session"). A self-hosted compiler cannot be fed forged checker facts by inventing a revision. |

## Coverage boundary

Session behaviour only (OCaml seed). The v2 `semanticTarget` /
`source_bytes()` host-grant path and the A13 Pep-written checker + A14
emitter revision checks are builder-owned stages and stay `NOT_RUN` /
`BLOCKED_SECURITY` here. Bridge question for V2/V3: demonstrate the
same four rejections through the staged Pep checker/emitter revision
plumbing once execution is cleared.
