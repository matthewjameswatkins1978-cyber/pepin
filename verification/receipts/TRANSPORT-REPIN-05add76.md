# Transport rejections re-pinned at A1 `05add76` (corpus R1/R2/R4)

**Date:** 2026-11-02 · **Lane:** Agent 3 independent verification · **Evidence label:** `TESTED`

Corpus cases `R1`/`R2`/`R4` from `verification/adversarial/cases/REVISION_AND_LIMITS.md` were originally measured at base `805062b` (2026-10-29). Probe `verification/probes/transport_repin.py` re-pins them at A1 `codex/checker-emitter-integration` @ `05add76e21d4c979d243fa1fd7cbd0eb2a9d945c` (clean pinned worktree), schema-v3 session, one process per probe. (`R3`, the 65,536-byte cap, was re-pinned earlier today by `verification/probes/open_bytes_limit.py` — see `A1-HEAD-SPOTCHECK-05add76.md`.)

Result: **exit 0, `SUMMARY cases=3 claim_falsified=0`**

| claim | observed at `05add76` |
|---|---|
| T1 stale `expected_revision` refused, current revision unchanged | `outcome=error`, `PEP_STALE_REVISION` — *"Edit expected a revision other than the document's current revision"*; `currentRevision` still rev2 afterwards ✓ |
| T2 edit range splitting a UTF-8 code point refused | `PEP_UTF8_BOUNDARY` — *"Edit range splits a UTF-8 code point"* ✓ |
| T3 forged document/revision query refused | `PEP_DOCUMENT_NOT_FOUND` — *"Document identity was not opened in this session"* ✓ |

Exact codes **and** messages match the base-pinned corpus observations — the four transport boundaries (with R3) are unchanged from `805062b` to `05add76`, i.e. **no cap/regression drift at the session layer** across ~4 days of checker/contract work.

## Honest scope

- Session-protocol layer only (OCaml seed host). The v2 `semanticTarget`/`source_bytes()` host-grant path and staged Pep checker/emitter revision checks remain builder-owned stages, `NOT_RUN` here (unchanged from the corpus file's coverage boundary).
- One head; probe is byte-offset-exact against the corpus sequences (26..27 for the `1`→`2` edit; 6..7 inside `é`).

## Reproduction

```powershell
git -C <worktree> checkout --detach 05add76e21d4c979d243fa1fd7cbd0eb2a9d945c
python verification\probes\transport_repin.py <worktree>    # expect exit 0
```

## Next action

Stand as a head-pin next to the base corpus; gate watch for A1's `d158044` fix continues.
