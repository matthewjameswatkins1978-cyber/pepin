# Pin-verification double: A1 uniqueness 2/2 at `d64518f`, A2 G-A2-1 12/12 at `0229e60`

**Date:** 2026-11-04 · **Mission:** Campaign G fallback ("new A1/A2 SHA → review the changed interface") · **Evidence label:** `TESTED`
**Pins (both detached, clean):** A1 `codex/p1-checker-cost-fix@d64518f` (`D:\Projects\wt-a3-a1-d64518f`); A2 `codex/a2-bounded-emission@0229e60` (`D:\Projects\wt-a3-a2-0229e60`).
REF: A1 4c4064e red-pin measurement (A3); A2 G-A2-1 commit message; GH #16 (this session, to be posted).

## 1. A1 batch-uniqueness pins: RED → GREEN, helper fix independently confirmed

- At `4c4064e` (measured last turn): `test_external_signature_ids_are_unique_across_headers` FAILED `[9000,9000,9000]`.
- At `d64518f` ("batch-unique external signature IDs in fetch_all_sigs"): **2/2 OK** in 5.6s — uniqueness pin + two-external-callee end-to-end (both fact orders) pass.
- The owner-boundary repair is real and landed; A2's workaround removal (59cde2f, verified exit 0 last turn) rests on a fixed helper, confirmed from both sides. Cited phantom `9e32999` still absent locally (stated, unchanged).

## 2. A2 G-A2-1 Str-record-field: 10/11 → 12/12, stale expectation legitimately retired

- `tests/test_a14_c23.py` full file at `0229e60`: **12 tests, OK** (68s) — including the new `test_str_record_field_programs_run_natively_with_seed_parity` and the repaired second assertion.
- A2's PRE measurement (capability already emitted at baseline ea0bc9a; expectation stale, emitter not wrong) is consistent with what I verified: no them-vs-us dispute, just a retired pin + new parity coverage. The file that was baseline-red across four campaigns is now fully green.
- Note: this is the same path (`tests/test_a14_c23.py`) that's dirty in the main campaign checkout — unrelated pre-existing local modification, preserved untouched; A2's change lives on their branch only.

## Limits

Targeted suites only (2 + 12 tests); no full-suite reruns (baseline-reds elsewhere unchanged and out of scope). No builder files touched; no master/CURRENT/manifest/budget changes.
