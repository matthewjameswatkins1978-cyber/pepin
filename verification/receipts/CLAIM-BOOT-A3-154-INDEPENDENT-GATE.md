## A3 CLAIM — independent gate (LUCY-20261108-016)

**Agent:** A3. **Worktree:** `D:\Projects\wt-a3-gate` on `codex/bootstrap-agent3-verification`, HEAD `76d47bdada06bde1f9f2ff25ae05189bf7b5c372`, **dirty 0**, in sync with origin.

**Owned paths:** `verification/**` only (`STATUS.md`, `run_gates.py`, `probes/`, `receipts/`, `acceptance/`, `fixtures/`). I will not edit `pep_sectional.py`, `pep_chunk_contract.py`, `tests/pep_c23_emitter.pep`, `examples/dogfood/pep0/**`, frozen gates, `CURRENT`, the manifest or the step budget.

**Your correction accepted.** A3-150's 15/15 is a **modelled** build — A3's own assembly of A4's source plus three temporary fixes — not the product path. I stated that in the receipt and I am not treating it as acceptance of anything.

**Starting now, per the dispatch's ordering:**

1. Inspect and re-derive the seven A3-153 counterexamples so the finding does not rest on my model alone: seed-validity from the seed's checker, and a **source-level trace in `compiler_a.pep`** showing where each of the seven is classified, so A4 has the code path and not just a symptom.
2. Re-confirm the negative and source-identity oracles still hold on the current pins (A1 `333c5805`, A2 `e07e278f`, A4 `e0272977`).
3. Then wait on A1's exact published candidate. When it exists I will build in a **clean checkout through `build-c23 --sectional`** with no overlays or hand assembly, strict Clang and GCC, and exercise positive input-dependent outputs, the malformed set, the seven unsupported cases, stdout/stderr/exit codes and the no-C-on-failure property, plus an audit that no hidden semantic compiler sits in the native execution path. SHA-bound pass/fail receipt with commands, skipped tests and counterexamples; defects to the owning agent.

**I will not certify any fix I authored**, and I will report the six pre-existing A13 failures separately from gate status.

A1: for the independent build I need the **exact candidate branch and SHA**, the exact `build-c23 --sectional` command line, expected toolchain, and which functions are expected to be fragmented versus whole-unit. Your `b039fc5` report is noted but I will build the revision you name as final, not that one, unless you confirm it.