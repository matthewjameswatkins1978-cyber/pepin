# A4 Lane Handover — Pepin native compiler A (fallback tier + integration readiness)

Branch: `spec/agent4-spec-lab` @ `f6cf9ca` (pushed, remote-equal, worktree clean).
Source identical to gated `e4cca7a2` (`git diff e4cca7a HEAD -- compiler_a.pep` empty; only outbox prose after).
Seed check: valid, 0 diagnostics. Lane: `examples/dogfood/pep0/*`, `docs/outbox/AGENT4_OUTBOX.md`, own BM lane.

## 1. What is done and verified

Fallback tier (`err 5`, 7 contracted shapes + Str/empty/CRLF/big19 boundaries): source-complete.
Each fix independently verified (shape + full-file sectional + native runbook by A3):
- underscore guard, bare-name `Int` annotations (A13 workaround), `bytes_eq` helper,
  `match_tail` empty-then inversion, `scan_value` in-loop `var` hoist,
  loop-free single-binop `scan_value` (no loop-cost class remains), Bool-local split
  of `find_brace` 5-conjunct conditions (A3-148 shape).
- Differential model old-vs-new `scan_value`: 13,053 inputs, 0 unexpected divergences
  (`_build/r2/diff_scan.py`; lane scratch, not shipped).
- All 27 fixtures seed-executed (14 valid / 13 invalid, 0 discrepancies vs contract)
  + exact-diagnostic audit (each invalid fails in its intended rule).
- A3 runbook on e4cca7a lineage: M-1 23/23 clang+gcc, class (ii) 10/10, malformed 4/4,
  builds + native path pass. Only `identity` fails (needs committed candidate).

## 2. Exact integration steps (whoever integrates)

1. Base: `codex/a1-typed-bound-pipeline` @ `333c5805` (or successor tip).
2. Apply `verification/fixtures/a3-m1-driver-recipe.diff` (A3-170; applies cleanly).
3. Place this branch's `examples/dogfood/pep0/compiler_a.pep` as the candidate source.
4. `python pep_c23.py build-c23 examples/dogfood/pep0/compiler_a.pep --sectional --output X --emit-c X.c`
5. `python verification/probes/gate_candidate_171.py --root <tree> --contract published`
   (pins current per A3-208: 23 M-1 + full class (ii); a_plusop natively confirmed).
6. Expect: 10/10 incl. identity once the tree is a committed candidate. A3's epilogue
   posture in the measured run: `say()` diagnostics intact (gate checks stdout).

## 3. Known residuals (documented, out of contract)

Chained binop (`0-1-2` falls back to S0 error); `//` comments, `if` value-expressions,
params-ful/main-with-params, parenthesised values, `--`/`- -`, multi-`var`, doubled `fn`
(all stay at shape/literal/junk codes per PEP0_SUBSET out-list). 19-digit cap stays exit 4.

## 4. Narrowed contingency (PARKED, do not execute without workshop direction)

Full contract builds (measured 9-10/10); narrowing is dominated in all scenarios.
Recipe at `docs/outbox/AGENT4_OUTBOX.md` (2026-11-09 entries): revert `9fd6431^..HEAD`,
restore map with narrowed notice; dry-run validated (clean apply + seed-valid) in a
deleted throwaway. Turn-50 bound proposal (#6730317040) voided by the re-gate (#6730375278).

## 5. Merge state (checked turn 52 via read-only `merge-tree` vs `origin/master`)

Lane files merge cleanly (no conflicts in `examples/dogfood/pep0/*` or `docs/outbox/*`).
One pre-existing conflict in `README.md` project-description text (both sides edited the
intro; unrelated to this lane — leave for whoever owns that text at integration time).

## 6. Pointers

Outbox (full ledger): `docs/outbox/AGENT4_OUTBOX.md`. Contract/pins: `examples/dogfood/pep0/`
(EXPECTED.md, PEP0_SUBSET.md, OWN_SOURCE_MAP.md, 27 fixtures). BM lane: task `pepin-a4-fallback`
(checkpoints carry SHAs + verification notes). Board: GH #16 (A4 posts #6729972514 … #6730427438;
A3-205 handoff, A3-207/208 re-gate + pins). Model: `_build/r2/diff_scan.py` (lane-local).
