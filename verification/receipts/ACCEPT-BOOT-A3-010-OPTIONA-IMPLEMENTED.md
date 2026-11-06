# BOOT-A3-010: Option A implementation verified additive + hostile green; Condition 2 open (Agent 3)

**Seat:** Agent 3. Detached read-only scratch `D:/Projects/wt-a3-units` @
`codex/a1-typed-bound-pipeline@3f3da65` (removed afterwards). Review input for Matthew —
not acceptance; the amendment remains unpinned and Candidate7 `6dce37d` unaffected.

## 1. Additive-only: CONFIRMED

`git diff 9eea380..3f3da65 --stat` = exactly 3 files: draft doc, NEW `pep_chunk_units.py`
(157 lines), NEW `tests/test_chunk_units.py` (164 lines). `pep_chunk_contract.py`,
checker sources, budgets, frozen tests: byte-identical. The frozen module's header rule
respected; only existing refusal codes reused (`CHUNK_COVERAGE_MISMATCH`, `CHUNK_INCOMPLETE`).

## 2. Independent test runs on the implementation SHA (cold scratch)

- `tests.test_chunk_units + tests.test_chained_bindings`: **17/17 OK** (14.2 s).
  Includes the real 21-unit utf8_check chain recording `valid`, `unitCount=21`.
- K1c pooled-forgery probe (mine, unmodified) against this SHA: group0/control `valid`;
  **F1 forged USED carried binding refused (`PEP_TYPE_MISMATCH`)**; F2 vacuous as documented.
- K1/K1b (callee-signature facts via unchanged `checker-chunk-typed` path): result transfers
  by file-identity — that path is byte-identical to the SHA where K1/K1b were measured.

## 3. Review conditions update (from BOOT-A3-007)

- **Condition 1 (adversarial green on the pooled path): SUBSTANTIALLY SATISFIED.**
  K1c F1 refuses on the implementation SHA; unit suite pins overlap/bounds refusal,
  first-refusal stickiness, terminal closure, and no-carry-from-dirty-units.
  Remaining for pinning: wire one K1-shaped hostile case into A1's own suite so the
  property is builder-owned, not just verifier-measured.
- **Condition 2 (disclose the inherited param-forgery residual): STILL OPEN.**
  The draft's §6 lists budgets/tests/matrices but says nothing about K1-A3:
  same-target forged PARAMETER types remain admitted (stamps are consistency-only),
  now also across pooled group boundaries. The module's fail-closed carry does not
  close it (it governs which units fund the pool, not fact content). One honest
  paragraph required before pinning.
- Terminality correction (structural closure + disclosed missing-return residual,
  `checker_expect_returns=False` recorded): reviewed, honest, accepted as priced.

## 4. Terminality note (verified in code)

`FunctionUnits.accept/complete`: tiling enforced, `first_refusal` sticky,
`complete()` refuses `CHUNK_INCOMPLETE` on gaps and reports `valid` only with no
refusal; `unit_ids`/`terminal_ids` route through existing `bounded_units`. Matches
the draft's corrected §2. No hidden semantics.

## Status

- Amendment implementation: verified additive, measured green, hostile-checked on the
  pooled path. **Ready for Matthew's accept/decline on Option A once Condition 2's
  paragraph lands** (Condition 1 needs only suite-wiring, already demonstrated).
- No candidate-implementation change (`6dce37d` intact; `3d41642` is outbox-only);
  all gate verdicts stand. A3 on standby for re-gate triggers.

## Reproduce

```powershell
git worktree add --detach D:/Projects/wt-a3-units 3f3da659e408ae44c4acb8719b585f7825b2fe10
cd D:/Projects/wt-a3-units; python -m unittest tests.test_chunk_units tests.test_chained_bindings  # 17 OK
python <a3-tree>/verification/probes/pooled_forgery_k1c.py D:/Projects/wt-a3-units  # F1 refused
```
