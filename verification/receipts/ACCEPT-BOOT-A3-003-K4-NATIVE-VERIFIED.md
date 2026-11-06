# BOOT-A3-003: K4 record-return native vertical + published seam re-verified on Candidate7 `6dce37d` (Agent 3 slice 3/3)

**Seat:** Agent 3. `verification/**` only; no builder edits, caps, or instrument changes.
**PIN: A3 | `codex/bootstrap-agent3-verification` @ `bb258a8` (clean) → this receipt.**
**Method:** detached read-only scratch `D:/Projects/wt-a3-k4verify` @ `6dce37d` (removed afterwards);
A2's committed `tests/probe_k4_record_return.py` + `tests/probe_seam_chunked.py` run unmodified.
A4 oracle doc `docs/spec/FINISH-K4-BLOCKER-TEST.md` @ `9ea369a` (P1 return-encoded, P2 mismatch).

## 1. K4 record-return native: PASS (independent, candidate SHA)

- `[newline] advance_position(1,1,10)`: seed `21`, check `valid`, emit 6537B,
  **native-clang `21`, native-gcc `21`** — all OK.
- `[ordinary] advance_position(4,7,65)`: seed `48`, check `valid`, emit 6537B,
  **native-clang `48`, native-gcc `48`** — all OK.
- `K4 record-return native: PASS`. Real session + real emitter bundle + real A1 seed;
  entry-point difference (seed top-level `say(int_text(...))` vs native `main` return) as documented.
  The K4 primitive gap (function-result records) therefore lowers natively on the candidate;
  per A4's own falsifier language the card flips toward NO-CHANGE with control-flow residuals.

## 2. Published seam on candidate, cold: EXIT 0 (C4 dynamic, on the published SHA itself)

- `bundle_sha256 7fc7bb4a…` (x3-identical run; stage-probe bundle, distinct from seam `80c28ef5…` — both deterministic).
- Seed marker `727f8af…` (fresh exe from pinned source, no hand-supplied file, empty `_build` at start).
- 4 chunks valid (18/55/8/5), strict Clang+GCC `42` both orders + reverse, seed `42`.
- str_concat native vertical green both compilers (seed-parity output + `0` return);
  capacity case fails closed natively (`PEP_RUNTIME_STR_CONCAT_RANGE`) while the seed is
  unbounded — the KNOWN divergence Lucy flagged for a bootstrap-scope decision, not conformance.
- All 11 negatives refusing (incl. `neg-dup-external-name` via the published stamps).

## Status

- A3's packet items are now all evidenced: Full-v2 verdict (BOOT-A3-002, FAIL/1 red row),
  strict-coverage measure (FAIL w/ UNKNOWN remainder), pins/digest/adversarials (C1/C2/C4/C5 hold),
  K4 native vertical (this receipt, PASS).
- No new builder SHA since `6dce37d` affects these verdicts (candidate tip `d5a105a` is
  receipts-only; A2 `6f7d72d`, A1 `1aaead7` unchanged at check time).
- Next: A3 stands by for re-gate triggers — a new Candidate7 implementation SHA, a new A2
  native slice (computed call args), or an A1/A2 summons. No review needed for this slice.

## Reproduce

```powershell
git worktree add --detach D:/Projects/wt-a3-k4verify 6dce37da8930bdb4b0f5ba410c8042f23110545d
cd D:/Projects/wt-a3-k4verify; python tests/probe_seam_chunked.py   # EXIT 0, marker 727f8af
python tests/probe_k4_record_return.py                              # PASS (21 / 48, clang+gcc)
```
