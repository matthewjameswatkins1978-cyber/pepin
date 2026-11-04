# F2 independent A2 proof at `152f76c` — reproduced exit 0 + raw-collision failure

**Date:** 2026-11-04 · **Mission:** LUCY-20261104-012 / Campaign F A3-F2 · **Evidence label:** `TESTED`
**A2 pin:** `codex/a2-bounded-emission@152f76c` ("A2-3 negative controls"), detached `D:\Projects\wt-a3-a2-152f76c` (clean before/after; only ignored `_build/` products). A2's probe run VERBATIM, unmodified: `python -X utf8 tests/probe_seam_chunked.py` → **EXIT 0**. A1 checker SHA used by the probe: **`2f939a0`** (pinned in-probe; objects verified local).
**Toolchains (live):** Clang 23.1.4, GCC 16.2.0, opam `pepin-5.5.2` switch (seed built by the probe). Full logs: `_build/a2-f2-run.log` (exit 0), `_build/a2-raw-run.log` (raw failure) — worktree-local, ignored.
REF: A2 BOOT-A2-20261104-022; Campaign F A3-F2; GH #16 (this session, to be posted).

## 1. Positive path — independently reproduced exactly

- Bundle opens (sha `4e6f2df5…`); parse 68 nodes / 575 bytes.
- 4 separately checked chunks `valid`: declaration:LexToken 18, make_token 55, add_one 8, main 5 — matches A2's ledger node-for-node.
- Header + make_token/add_one/main units + epilogue emitted from chunk reports; assembled 5,875 B C23.
- **Strict Clang (`-std=c23 -Wall -Wextra -Wpedantic -Werror -O2`) build OK, run → `42`; strict GCC (`-std=c2x`, same warnings) build OK, run → `42`; seed oracle → `42`** (entry-point difference stated by A2 and observed: seed runs top-level, native runs `fn main`).

## 2. Raw collision vs workaround — both sides reproduced

- **With workaround (verbatim probe):** sigs renumbered 9000/9001/9002 → exit 0 as above.
- **Raw (faithful copy minus the 3-line renumber block, run from ignored `_build/`, A2 files untouched, copy deleted after):** all three externals collide at semid=9000/synid=1000000000 → `check:main FAIL status=invalid PEP_TYPE_MISMATCH "Function argument type does not match its parameter"` (caller's `add_one(41)` resolved against make_token's Str param), exit 3. **A2's transport-defect claim is independently confirmed**, including the exact mis-resolution shape.
- Status: workaround success AND raw failure both measured. This is **not an end-to-end authorised contract**: A1 pin `2f939a0` predates BindingFact stamps/union facts/R-ID-1; ids stay synthetic; A1 owns the helper fix (Campaign F A1-F1 task, still open).

## 3. Ten negatives — all reproduced with exact diags

no-call-fact / ambiguous-call / missing-target / ambiguous-target / arity-mismatch / foreign-result / **stale-revision (refused at HOST transport gate `PEP_STALE_REVISION`, emitter gate not reached — consistent with A3's ingress finding)** / unit-index / unit-order-Clang (exit 1, undeclared callee) / unit-order-GCC (same). Every emitter refusal `unsupported` + exact diagnostic + empty sourceParts.

## 4. Reproducibility gaps in A2's artifact (findings for A2, not proof defects)

Fresh worktree fails TWICE before any check, both times on `_build/` leftovers `prepare()` never creates:
1. `FileNotFoundError _build/a1_chunk_helper.py` — extraction list lacks `tests/chunk_helper.py → a1_chunk_helper.py`.
2. `ModuleNotFoundError pep_chunk_contract` — needs `2f939a0:pep_chunk_contract.py` in `_build/` (the pin-matching contract; verified present at that pin).
I supplied both byte-exact from the probe's own A1 pin and proceeded; A2's exit-0 was evidently measured in a seasoned worktree. **Fix for A2:** add both files (pinned SHA) to `prepare()`'s extraction list — one small change, no behavior impact. A2 worktree left clean (scratch copy removed; only probe-generated ignored products remain).

## Limits

A1 pin `2f939a0` is stale (latest `2e81f35`); re-pin + rerun is A2's stated next action, not mine. No native work beyond reproduction; no builder files touched (read-only + ignored scratch); no master/CURRENT/manifest/budget changes.
