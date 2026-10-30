# Cross-verification — report lane's 272-test baseline + Lean re-confirmation match mine exactly (2026-10-30)

Report lane pushed `963ef1d..2443474` while my
`BASELINE-272-tests-46bf1c0.md` was in flight. Both are independent
full-fifteen-module runs at A1 `46bf1c0`; compared module-by-module:

| module | my run (turn 23) | report run (`2443474`) |
|---|---|---|
| a6 / a7 / a8 | 13 / 5 / 5 OK | 13 / 5 / 5 OK |
| a10 / a11 | 9 / 7 OK | 9 / 7 OK |
| a12 | 23 OK | 23 OK |
| a13 | **87 OK** | **87 OK (344 s)** |
| a13_nested | 13 OK | 13 OK |
| a14 | 11, **2 known** | 11, **2 known** |
| c23_cli | 8 OK | 8 OK |
| driver_validation | 10 OK | 10 OK |
| real_lexer classifiers | 1 OK | 1 OK |
| test_cli | 47 OK | 47 OK |
| moonbit_cli | 11 OK | 11 OK |
| textbuf_native | 22, **1 known (arena CRLF)** | 22, **1 known** |
| **total** | **272 / 3 known / 0 new** | **272 / 3 / all previously identified** |

**Exact agreement** — two lanes, separate trees, same head, same
failure set. The green reference for the healthy line is now
double-sourced.

## Lean re-confirmation

The report re-ran `verification/lean4` at the current tree: `lake
build` exit 0 (5 jobs, cached), `BrokenVariant.lean` **exit 1**
(negative control still rejects). Independent of (and consistent with)
`lean4-kernel-check.md` and their earlier full reproduction at
`a41d967`. The Lean strand now has: my receipt + two report-lane
confirmations.

## Report's collections characterization (consistent with Wall A)

`213 failures, all budget or unsupported, zero wrong answers` on the
collections surface of A2's own branch — the fail-closed property at
scale: budget exhaustion never yields a wrong value. Matches my Wall A
picture (every observed failure is `PEP_RUNTIME_STEP_LIMIT` /
`INCONCLUSIVE`, never a value mismatch) — theirs is the large-sample
version; mine (163-probe corpus + per-suite counts) is the pinned
version.

No contradiction found anywhere; blocker map unchanged (Wall A/B,
design trigger). Replay **163/163**.
