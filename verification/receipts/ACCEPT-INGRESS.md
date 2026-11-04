# Reserve D source-ingress negative — 4/4 held, two layers mapped

**Date:** 2026-11-04 · **Mission:** Reserve Queue D A3 card ("one actual source-ingress/parser-continuation integrity negative"; no SHA needed) · **Evidence label:** `TESTED`
**Pin:** `codex/checker-emitter-integration@81398fa` (detached `D:\Projects\wt-a3-int-81398fa`, clean).
**Instrument (new, this commit):** `verification/probes/source_ingress_negative.py` (G0/G1/G2/G3). Guard source-read at `81398fa` (`analyze_chunk_inner_bound`: authority-vs-parsed `A13_PARSER_REVISION`, `!parsed.done` → `A13_PARSER_BUDGET`). JSON artifact `_build/ingress-81398fa.json` (worktree-local, ignored).
REF: LUCY-20261104-009 Reserve D; GH #16 (this session, to be posted).

## Result: 4 claims, 0 falsified — with exact layer attribution

| case | outcome | layer | code |
|---|---|---|---|
| G0 control (honest complete parse, seed `valid`) | `valid` | pep | — |
| G1 stale parse (rev1 progress vs rev2 target) | TOOL-ERROR refusal | **host transport** | `PEP_STALE_REVISION` ("Tool arguments derive from a different source revision than the semantic target") |
| G2 unfinished continuation (stamps match, `done=false`) | `invalid` | **pep entry guard** | `A13_PARSER_BUDGET` |
| G3 foreign-document parse | TOOL-ERROR refusal | **host transport** | `PEP_STALE_REVISION` |

## Defense-in-depth observation (stated, not a defect)

The host transport (`pep_c23.py` tool_invoke path) revision-checks arguments against the semantic target BEFORE the Pep entry guard runs, so G1/G3 hold at the host layer and the in-language `A13_PARSER_REVISION` guard is shadowed through this host — it can only fire for callers that bypass the transport check. Its status stays ESTABLISHED-by-source-read, not probed. Both layers refuse with provenance codes; no shape checked stale or unfinished input. The probe's `check()` accepts only the provenance-code family at either layer and reports the exact layer+code, so a future layer change falsifies loudly instead of passing silently.

## Reproduce

```powershell
python -X utf8 verification\probes\source_ingress_negative.py D:\Projects\wt-a3-int-81398fa  # 4/4
```

## Limits

Single pin (`81398fa`); guard code shared with the repair lineage by ancestry (not re-run there — no ingress-relevant diff; stating, not assuming, coverage). No native execution (hold). No builder/spec files touched; no master/CURRENT/manifest/budget changes.
