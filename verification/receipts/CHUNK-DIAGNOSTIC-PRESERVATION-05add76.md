# Cross-chunk DIAGNOSTIC PRESERVATION at A1 `05add76` — codes/spans held, **messages diverge 3/3**

**Date:** 2026-11-02 · **Lane:** Agent 3 independent verification · **Evidence label:** `TESTED`
**Why:** Lucy advisory item — diagnostic preservation / cross-chunk diagnostics under the future node-ID index. This pins the *current* chunked-checker behaviour as the baseline gate.

## Method

`verification/probes/chunk_diagnostic_preservation.py` at A1 `codex/checker-emitter-integration` @ `05add76` (clean pinned worktree): whole-source session `query` (seed/OCaml checker) vs `analyze_chunk` reports (Pep-written checker through `tests/chunk_helper.py`), **one deliberate local error per fixture** so each path yields exactly one diagnostic — the seed reports only the FIRST error on multi-error sources (corpus S2), which invalidates multi-error comparisons.

**v1 of this probe was discarded before commit** (Threadmoth content-hash-guarded delete) because it compared a multi-error whole-source query against the chunked union — ill-posed by first-error semantics. Disclosure: Threadmoth `plan` refused `delete_file` with `OPERATION_UNSUPPORTED`; `mutate` applied it with the full certificate (`committed_checked_lifecycle`, budget PASS). All earlier edits in this slice were `plan`→`apply` cycles (10 certified, `unrelated_bytes_changed=false`, `lf→lf`).

Fixtures: `type Box { f: Nope }` / `let a: Zzz` in `alpha` / `return Qqq` in `beta` — each with a trivial `main`.

## Result — exit 1, `SUMMARY cases=6 claim_falsified=1` (4 claims + 2 observations)

| claim | result |
|---|---|
| VAC each fixture yields exactly one whole-source diagnostic | HELD (`{decl_only:1, alpha_only:1, beta_only:1}`) |
| CD1 **no LOSS** — every whole-source (code, span) reproduced by the chunked path | **HELD** — 11–18, 22–36, 28–31 all reproduced, by the *correct* chunk (`declaration:Box`, `alpha`, `beta`; `main` empty) |
| CD2 **no EXTRAS/duplicates** across chunks | **HELD** — chunked ⊆ whole per (code, span); no span reported twice |
| CD3 **message parity** for the same (code, span) | **FALSIFIED — 0/3 messages match** |
| O1 assignment detail | recorded (per-chunk diagnostics verbatim) |
| O2 leakage (span outside the reporting chunk's node byte intervals) | **0** across all fixtures |

### CD3 detail (verbatim, both paths, same code, same byte span)

| fixture | whole-source (seed) message | chunked (Pep-written) message | code / span |
|---|---|---|---|
| decl_only | `Unknown type 'Nope'` | `Record field type is outside the implemented checker subset` | `PEP_UNKNOWN_TYPE` 11–18 |
| alpha_only | `Unknown type 'Zzz'` | `Binding annotation is outside the implemented primitive checker subset` | `PEP_UNKNOWN_TYPE` 22–36 |
| beta_only | `Unknown variable 'Qqq'` | `No visible variable has this name` | `PEP_UNKNOWN_VARIABLE` 28–31 |

## Classification — stated fairly, decision to the owner

- **What held is the roadmap's stated A13 standard**: ROAD-1 requires parity of *“precise diagnostic codes and original UTF-8 byte spans”* — CD1/CD2/leakage show exactly that, preserved through chunking and id remapping. Credit where due; the identity half of diagnostic preservation is **green**.
- **What diverged is message text** (3/3): the seed and the Pep-written checker word the same diagnostic differently; two of the three Pep-side messages are *subset-limitation phrasings* carried under a **definite-condition code** (`PEP_UNKNOWN_TYPE`) — in these fixtures the code is provably right (the seed proves the type/variable genuinely unknown), but the wording conflates “cannot check” with “is unknown”, and the repo’s own tests do assert message text in places (the `count_between` stale-message failure was treated as a real failure).
- **Not claiming a roadmap violation** — message parity is not in ROAD-1’s A13 wording. This is a **confirmed, reproducible inconsistency with an owner decision**: either align messages (chunked consumers get seed-identical text), or document that chunk-contract messages are not part of the guarantee — in which case I will downgrade CD3 to an observation in the probe with a dated note. Until then CD3 stays a claim and doubles as the gate.

## Non-vacuity / controls

Correct chunk reports each error; `main` chunks clean; no leakage; fixture counts verified before comparison (first-error semantics confirmed empirically: a two-error source returns only the first diagnostic). Pure checker/session layer; no emission, no native build, no builder files touched.

## Reproduction

```powershell
python verification\probes\chunk_diagnostic_preservation.py <worktree-at-pin>   # exit 1 today (CD3)
```

## Next action

Report to #16 directed at A1 (checker/semantics owner) + BM; keep as baseline gate for the index work; rerun unchanged at the next pin.
