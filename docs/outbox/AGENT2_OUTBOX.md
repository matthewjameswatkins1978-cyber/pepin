# Agent 2 — Outbox (append-only)

Receipts are appended newest-last and each is bound to a pushed commit.

**Why this file exists.** The Basic Memory A2 outbox
(`cloud|703e9fd6-…|ff4f6328-…|7b7b441e-…`) is **not reachable** from the 6 Nov Pi
session's MCP connection: the only indexed projects are
`matthew-watkins-s-workspace/{main, lantern, reusery, getting-started, agent-x}`.
Rather than drop the receipt, it is recorded here in the repo, following the
existing `runtime/pep_text/AGENT4_OUTBOX.md` convention. This is a receipt log,
not a second status board — A1 alone writes Current Status.

---

## BOOT-A2-20261106-01 — G0 re-pin published

- **Agent:** 2 (native/backend).
- **Branch:** `codex/a2-bounded-emission`. **Worktree:** `D:/Projects/wt-a2-bounded`.
- **Re-pin commit:** `1658ea9da74f3b166822ffe7fca0d69667cf9fbf`
  (remote verified: `origin/codex/a2-bounded-emission` = `1658ea9`).
- **Prior remote head:** `123d8b3` — the three-line repair was absent, as dispatched.

### Delta (exactly the three dispatched lines)

1. `A1_SHA = "727f8af4d019e6e5e235ac26077a12b166b9c080"` (was `2ad750b`).
2. `prepare()` fetches `("pep_chunk_contract.py", "pep_chunk_contract.py")` with the pin.
3. `duplicate_fact` carries `document: sem["document"], revision: sem["revision"]`.

### Why — measured, not assumed

- The A2 worktree has **no** `pep_chunk_contract.py` at all, and
  `_build/pep_chunk_contract.py` was a 4 Nov copy that **predated** the `2ad750b`
  pin marker. The probe therefore only ever ran against a stale contract; a fresh
  checkout would have raised `ImportError`.
- At `727f8af`, `chunk_helper.checked_fn_value` / `resolved_sig_value` read
  `sig["document"]` / `sig["revision"]` off the fact itself (F2: checker-stamped
  at production). The hand-built duplicate-name negative died on `KeyError`
  instead of exercising the `PEP_DUPLICATE_FUNCTION` refusal it exists to test.

### Cold start

Deleted before the run: `_build/a1_seed/`, `_build/pep_chunk_contract.py`,
`_build/a1_{lexer,parser,checker}.pep`, `_build/a1_chunk_helper.py`,
`_build/seam_*`, `_build/str_concat_seed.pep`.

Command: `python tests/probe_seam_chunked.py` → **exit 0**.

### Evidence

- `bundle_sha256 7fc7bb4ab909265eee5c125bf398a4ab73eb5faabc96f6ada692bdf3be12b846`
- Chunks valid: declaration 18 nodes, `make_token` 55, `add_one` 8, `main` 5.
- Strict Clang `-std=c23` and GCC `-std=c2x`, `-Wall -Wextra -Wpedantic -Werror -O2`:
  document order → `42`; reverse order → `42`.
- Seed oracle → `42`.
- **11** enumerated negatives all refuse (11, not 12 — matches A3's count):
  `neg-no-call-fact`, `neg-ambiguous-call`, `neg-missing-target`,
  `neg-ambiguous-target`, `neg-arity-mismatch`, `neg-foreign-result`,
  `neg-stale-revision` (`PEP_STALE_REVISION` at the transport gate),
  `neg-unit-index`, `neg-dup-external-name` (`PEP_DUPLICATE_FUNCTION`),
  `neg-unit-order-clang`, `neg-unit-order-gcc`.
- Provenance parity (`git hash-object` against the `727f8af` blobs):
  `_build/pep_chunk_contract.py` = `0751391f3a13a5637c5cafa2bdc2753d8a1b3356`;
  `_build/a1_seed/pep_ocaml.ml` = `923769a773627e804132c506be2a7a9adc665708`.
  Both byte-identical to the pin.

## BOOT-A2-20261106-02 — G-A2-7 native `str_concat` preserved and published

- **Commit:** `3f2d711e4289054c5cae577f5b71b30623a31723`.
- Pre-existing uncommitted work from the 4 Nov A2 session, re-verified cold at the
  `727f8af` pin in the same run as the re-pin, then committed rather than left dirty.
- `str_concat` is a builtin, so both the Str-result classifier and the two-argument
  dispatch classify it directly; Str-returning user functions stay refused at the
  `say(<Str call>)` boundary.
- Runtime is a per-run bump pool (no buffer reuse), capacity
  `PEP_STR_CONCAT_CAPACITY 4096`, overflow fails closed with
  `PEP_RUNTIME_STR_CONCAT_RANGE`. That is a documented divergence from the
  unbounded seed builtin, pinned by its own capacity negative and never seed-compared.
- Cold-start stages: `str-concat-check` valid, `str-concat-emit` emitted,
  `str-concat-seed` / `-clang` / `-gcc` all print
  `hello world` / `Unknown variable 'x'` / `buf-1 onebuf-2 two`,
  `str-concat-capacity` exits 1 with `PEP_RUNTIME_STR_CONCAT_RANGE`.

### Next READY

A4 `spec/agent4-spec-lab@c25fab6` `advance_position` record-result fixture
(`docs/spec/FINISH-K4-BLOCKER-TEST.md`) on the actual checker/native path; repair
only the **first** refusing native layer. If it passes, measure SourceBytes native
ingress next.

### Not claimed

No frozen Full-v2 run, no Candidate7, no acceptance, no master / `CURRENT.md` /
`manifest.json` change, no budget-cap change, no frozen-runner edit.
