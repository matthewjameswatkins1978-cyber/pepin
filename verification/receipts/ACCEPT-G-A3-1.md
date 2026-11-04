# G-A3-1: A2 `59cde2f` zero-workaround tree — exit 0, unique ids live, Str-result 6/6

**Date:** 2026-11-04 · **Mission:** LUCY-20261104-013 / Campaign G A3 G-A3-1 (Priority 0) · **Evidence label:** `TESTED`
**Model/provider (first-receipt declaration):** muse-spark-1.3-contributor / opencode-go.
**A2 pin:** `codex/a2-bounded-emission@59cde2f` (probe re-pinned to A1 `d64518f`, renumber workaround REMOVED), detached `D:\Projects\wt-a3-a2-59cde2f` (clean before/after; ignored `_build/` only). Probe VERBATIM → **EXIT 0**. A1 `d64518f` objects verified local; seed rebuilt fresh via opam `pepin-5.5.2` in the empty worktree.
**Toolchains (live):** Clang 23.1.4, GCC 16.2.0. Full log `_build/a2-g1-run.log` (worktree-local, ignored).
REF: Campaign G A3 G-A3-1; A2 59cde2f commit message; GH #16 (this session, to be posted).

## Result: zero-workaround path verified end to end

- `sig-id-state OK raw_semids=[9000, 9001, 9002] collision=False renumber=removed` — batch-unique ids arrive from A1's owner-boundary fix live, no local renumbering.
- 4 chunks valid (18/55/8/5); header+3 units+epilogue (5,875 B); strict Clang AND GCC run → `42`; seed oracle → `42`.
- All 10 negatives OK with identical diags (stale at host transport gate).
- `tests.test_c23_str_result`: **6/6 OK** — literal + parameter pass-through round-trips on both compilers with seed parity (incl. escaped-byte round-trip, static storage), 3 boundary refusals held (conditional-return-Str, say-of-call, int_text-built Str).

## Reproducibility: contract gap stands (third run, second report)

`prepare()` still does not extract `pep_chunk_contract.py` — fresh worktree fails `ModuleNotFoundError` before any check. Supplied `d64518f:pep_chunk_contract.py` (pin-matching, 33,757 B) manually again. A2 fixed the helper extraction in e03553a but not this one; asking a third time is noise — recording instead: **any fresh-checkout rerun of either A2 probe needs this file until `prepare()` extracts it.** No builder files touched.

## Limits

A1 pin `d64518f` is builder-reported 125/125 + 72/72 (cited, not re-run — suites, not my lane). Raw-collision side unchanged since F2 (renumber deleted, helper fixed at owner boundary; historical repro pinned by A2 to df190de). No master/CURRENT/manifest/budget changes.
