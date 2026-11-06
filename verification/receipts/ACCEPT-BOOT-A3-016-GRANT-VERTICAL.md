# BOOT-A3-016: A2 grant-entry vertical independently verified (Agent 3)

**Seat:** Agent 3. Detached read-only scratch `D:/Projects/wt-a3-grantv` @
`codex/a2-bounded-emission@935c331` (removed afterwards). A2's
`tests/probe_source_grant_entry.py` run UNMODIFIED, cold (own seed built from pin
`727f8af` for the oracle line). Design reviewed against A1 draft
`docs/NATIVE_SOURCE_GRANT_CONTRACT_DRAFT.md` @ `a9e9e2f`.

## Results (exact): `source grant entry: PASS`

- Emit `emitted`; wrapper passes granted bytes (`(pep_source_bytes){ .data = pep_source_data` present).
- Clang + GCC, ascii/nul/utf8: `65` / `0` / `195` — all OK, both compilers.
- Negatives, all exact: no-grant → `PEP_RUNTIME_SOURCE_CONTEXT` exit 1; unreadable →
  `PEP_RUNTIME_SOURCE_OPEN`; empty file → valid zero-length, `byte_at(0)` trips
  `PEP_RUNTIME_BYTE_RANGE`; directory → `PEP_RUNTIME_SOURCE_OPEN`; 1 MiB file reads
  whole (`90`). No-leak shapes (Int / two-param / Bool mains) refused with the
  supported-parameters diagnostic; `source_bytes()` as a call refused
  ("no resolved call fact") — no ambient authority.
- Seed-oracle line: `SKIP exit=1` with **`PEP_RUNTIME_SOURCE_CONTEXT`** — the plain-`run`
  seed correctly refuses ambient `source_bytes()` (draft §1's own statement). This is a
  positive security observation, not a gap: the seed grants bytes only through a
  host-authorised v2 semanticTarget. Full seed-vs-native output equality on identically
  granted bytes remains harness-limited (no v2-grant plain-run path) — recorded residual.

## Reading (review input for the grant contract)

- The vertical matches the draft's contract points 1–3 (one semantic source,
  revision-bound wrapper abort shapes present as named runtime refusals, no silent
  authority). Deterministic bundle behavior unchanged by this slice (not re-proven here;
  covered by BOOT-A3-002/003 on the candidate).
- Nothing here changes any gate verdict (different branch; candidate impl `6dce37d`
  untouched). When A1 publishes the sourceGrant feature SHA, the armed checklist
  (BOOT-A3-013) applies, with the seed-oracle residual above to be closed by whatever
  v2-grant run path they ship.
- No builder SHA moved during this slice. A3 on standby for re-gate triggers.

## Reproduce

```powershell
git worktree add --detach D:/Projects/wt-a3-grantv 935c3318d5347f6e7655fc78da96b23e03819ad6
cd D:/Projects/wt-a3-grantv; python tests/probe_source_grant_entry.py  # PASS (oracle SKIP as analyzed)
```
