# F3 adversarial callee attacks — E2b fail-open repro for A1; E1 mechanism split; E3p schema gap live

**Date:** 2026-11-04 · **Mission:** LUCY-20261104-012 / Campaign F A3-F3 · **Evidence label:** `TESTED`
**Pin:** `codex/checker-emitter-integration@46b6712` (detached `D:\Projects\wt-a3-c6-46b6712`, clean).
**Instrument (new, this commit):** `verification/probes/ext_callee_attacks.py` (E4/E1/E2a/E2b/E3p; observations never falsify). JSON artifact `_build/extcallee-46b6712.json` (worktree-local, ignored).
REF: A1 BOOT-A1-20261104-024 residual (ext-ext dup fn names); A2 BOOT-A2-20261104-021 (9000-collision); B4-CALL-02; GH #16 (this session, to be posted).

## Result: 5 records, 2 falsified — both sent to owners, neither over-claimed

| case | outcome | standing |
|---|---|---|
| E4 control (two honest externals, unique ids) | HELD `valid`, seed `valid` | non-vacuity proven |
| E1 colliding synthetic ids (type-distinct callees add_one-Int / pick-Str, both forced 9000/1000000000) | FALSIFIED `VALID`, no codes, seed `valid` | mechanism split (see §1) |
| E2a identical duplicate batch entries | observed `valid` (dedupe/first-wins, matches seed) | benign, compatible with T-ADM-2 dedupe semantics |
| E2b contradictory batch (dup Int/arity1 + forged dup Bool/arity2) | FALSIFIED `VALID`, no diagnostics | **fail-open repro for A1's disclosed residual** (§2) |
| E3p wire-field inspection | identity-free confirmed live (full field lists in detail) | schema-gap evidence for A2's ACK (§3) |

## §1 E1: ids unconsulted on THIS path — hazard is path-dependent, trap stands

The verdict matches the seed, so nothing unsound happened HERE: `analyze_chunk_typed` call resolution on this fixture is name-keyed and never consults the synthetic ids. This CONTRASTS with A2's measured mis-resolution (add_one(41) vs make_token Str → PEP_TYPE_MISMATCH) on the same id collision — so the id-keying bite is fixture/path-dependent, and verdict-level probing cannot see silent-wrong resolution, only loud mismatch or nothing. The conservative requirement (colliding identity must not validate) stays falsified as the documented discriminator; the practical consequence is unchanged: **any consumer that joins on semid/synid (A2's emitter does) can still be fed collisions, and A1's helper fix (Campaign F A1-F1) is still the owning repair.** First probe version used type-identical callees (would have hidden even a loud mismatch); caught and redesigned to type-distinct before measuring — stated so the artifact history reads clean.

## §2 E2b: executable repro of the external-vs-external gap → A1

Batch `[dup(Int,arity1), dup-forged(Bool,arity2)]` against a chunk calling `dup(41)` validates with NO diagnostics. The batch contradicts itself and the checker looks past it (presumably first-wins by name). Seed of the single-dup source is `valid`, so seed parity cannot arbitrate — the requirement is principle + precedent (A2's own ambiguous-target refusal): contradictory batches must not validate. This is A1's disclosed "not yet refused" residual with a pinned executable repro; no repair attempted (A1 lane).

## §3 E3p: foreign callee facts unstageable — for A2's schema decision

`CheckedFunction` fields: arity, endByte, name, returnShape, returnType, semanticId, startByte, syntaxId. `ResolvedSignature` fields: functionId, functionName, params, returnShape, returnType. No document/revision anywhere: a foreign-revision callee fact cannot even be CONSTRUCTED, so stale/foreign callee refusal is untestable until the schema lands. One more datum for the ACK: the binding-fact precedent (stamps + host PEP_STALE_REVISION + T-ADM-4 lock) is the tested pattern to copy.

## Reproduce

```powershell
python -X utf8 verification\probes\ext_callee_attacks.py D:\Projects\wt-a3-c6-46b6712  # E1+E2b falsified, E4 held, E2a/E3p observed
```

## Limits

Single pin; no native execution in this slice; E1 cannot see silent-wrong resolution (verdict-level instrument limit, stated); no builder/spec files touched; no master/CURRENT/manifest/budget changes.
