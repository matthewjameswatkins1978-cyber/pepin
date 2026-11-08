**A3 HANDOFF — `verification/STATUS.md` added: one page that says what is verified, at which pins, and what is not.**

The verification lane has 273 receipts and ~90 probes across several missions. That is not navigable, and a handoff that requires
reading all of it is not a handoff. `verification/STATUS.md` on `codex/bootstrap-agent3-verification@34c3030` is now the entry point.

**What it contains**

- **Live pins**, verified against the remote just now: A1 `07af079d`, A2 `e07e278f`, A4 `e0272977` (`compiler_a` blob `ca732536`),
  campaign base `bddd3542`.
- **The two seed blobs and what differs** — `f8f476198f` knows `str_concat`, `c92f9cc4a3` does not. Every claim names its seed.
- **Ten verified claims with their method and receipt**, so nobody re-derives them: A2's lowerings byte-identical; the assignment
  fix behaving exactly as predicted; `str_contains` fixed; A1's bindings giving 30/31; fragment composition at 19/21; execution
  correctness across 19 functions; determinism; both oracles reproducing; the census exact; the M-1 gate calibrated.
- **Five honest gaps**, stated plainly: no compiler A exists and no M-1 claim is made anywhere; two functions blocked on one
  change; the child-lookup early exit cannot help a late statement; 19 functions have only a source-derived oracle because
  `source_bytes()` is host-gated; whole-function emission is impossible for 11 of 21.
- **Standing cautions**, including the ones that cost me time: mixed lanes are not an integration, three id spaces coexist, three
  optimisations each narrowed correctness silently, seven of my own conclusions are retracted and the corrections should be read
  instead of the originals, and eight instrument defects were found in my harness rather than the code under audit.
- **Probe quick reference** and the single next action: when `find_brace` and `main` assemble, build compiler A and run
  `verify_m1_081.py` — the first moment an M-1 claim becomes possible.

**State at this pin:** `python verification/run_gates.py` reports **7 gates, 0 failed, 0 skipped**. The document reports `PARTIAL`
rather than green whenever a gate is skipped, so a partial run cannot be mistaken for a full one.

Nothing in it is new measurement — it is an index over measurements already posted, checked against the live remote before
committing. Two things in it are worth acting on if you have not seen them: the `find_brace` evidence that **a 13-node statement
exceeds the budget**, which rules out any per-statement threshold as a fix; and that the input-access wall bounds *verification
exhaustiveness*, not just compiler capability — only 2 of 21 functions admit a seed differential.

REF GH #16. Lane head `34c3030`.