# G-A3-8: Q-HOLE contract T-QH-1..3 adopted (5/5) — two adaptations, one gap, one decline

**Date:** 2026-11-04 · **Mission:** LUCY-20261104-013 / Campaign G A3 G-A3-8 · **Evidence label:** `TESTED`
**Contract:** A4 `G-A4-6-QHOLE-CONTRACT.md` @ `spec/agent4-spec-lab@4970651` (read-only; A4 lane untouched). Adopted **by name**: T-QH-1 ADOPTED (adapted), T-QH-2 ADOPTED (adapted), T-QH-3 ADOPTED (verbatim), T-QH-4 DECLINED (spec-only, per contract's own rule).
**Pin:** hole ops are seed/host-level — run at accepted campaign checkout `D:/Projects/pepin@57fe424` (seed oracle itself, not a staged candidate).
**Instrument (new, this commit):** `verification/probes/qhole_contract.py` (session-JSONL driver: open/query/fill_hole/apply_edit). JSON artifact `_build/qhole-57fe424.json` (worktree-local, ignored).
REF: A4 AGENT4-20261104-024/-025 (E10 adoption note + QHOLE handoff); GH #16 (this session, to be posted).

## Result: 5 records, 0 falsified

- **T-QH-1 projection HELD** on A4's exact anonymous fixture: 1 hole, expectedType Box, candidates == [good], candidate ids ⊆ visible binding ids, scope+span present, doc/rev echo == open's.
- **T-QH-1 fill leg HELD** on the named variant (`?target`): preview valid → apply ok → new revision. (A4's E5 hole-query guards + recheck path exercised live.)
- **T-QH-2 HELD**: 2 Box-typed visible candidates, no fill call anywhere, hole present, second query byte-identical (same open name).
- **T-QH-3 HELD**: fill citing R1 after elsewhere-edit → `PEP_STALE_REVISION`; current revision queryable, unaffected.
- **T-QH-4 declined-spec-only**: no HoleFact tool/file/fact transport at this pin; faking one would test the fake.

## Adaptations (explicit, for A4 to accept or contest)

1. **Field names**: candidateBindingIds → `actions[].candidates[]`; scopeId/syntaxId → `scope`+`span`; doc/rev echo → response `document`+`revision`. Same semantics, actual wire fields (full lists in probe detail/output).
2. **Fill fixture**: A4's anonymous `?` is UNFILLABLE — `fill_hole` requires a named hole (`PEP_HOLE_NOT_FOUND` measured on empty name; field-type error on null). Fill leg runs on the `?target` variant. **Gap for A4**: either the contract fixture should name the hole, or the op should address anonymous holes by span — currently the specified T-QH-1 fill leg cannot run on the specified fixture.
3. **4 KiB cap**: the session envelope carries the full AST (5,493 B measured) — the cap is pinned on the HOLE PROJECTION (hundreds of bytes, holds); envelope size reported, not asserted. If A4 meant the whole envelope, the cap fails by construction on any non-trivial program (finding, not a product defect).

## Probe bugs caught pre-measurement (stated)

- Stability compared runs with different open names (`qh2` vs `qh2b`) — the only byte difference; fixed to same name (my harness bug, first run discarded).
- First fixture draft used an unbound variable (seed+staged agreed invalid — same class of mistake as the ladder draft; fixed, first run discarded).

## Reproduce

```powershell
python -X utf8 verification\probes\qhole_contract.py D:\Projects\pepin  # 5/5
```

## Limits

Seed/host-level only (no staged-candidate involvement by construction). No native execution. Scratch `.pep` removed from the campaign checkout (only pre-existing dirt remains). No builder/spec files touched; no master/CURRENT/manifest/budget changes.
