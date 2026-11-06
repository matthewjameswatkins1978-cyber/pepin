# BOOT-A3-013: parked — A2-branch audit, no re-gate trigger; sourceGrant re-gate checklist (Agent 3)

**Seat:** Agent 3, per LUCY-20261106-005 ("A3 KEEP PARKED until a new published A1/A2
implementation SHA warrants re-gate"). Previous verdict/review stand (receipts 001–012).

## Live truth at check time

- A2 `codex/a2-bounded-emission`: `6f7d72d` → **`935c331`**. Delta = already-delivered
  items (computed call args `e2b5bee`, entry-parameter SourceBytes grant `b228461`
  against A1 contract `a802290`, List[Str] returns `18095bb`) + a long scalability
  probe series ending in explicit retractions (`5c25881` THIRD CORRECTION: NOT O(n²);
  `935c331` 1033-node needs 18–28x budget). 26 files, all A2-lane
  (`tests/probe_*`, `tests/pep_c23_emitter.pep`, `docs/outbox/AGENT2_OUTBOX.md`).
  **No `verification/**`, budget, cap, manifest, or frozen-test contact.** No action for A3;
  the retracted figures are self-corrected in-branch — nothing to base anything on, per dispatch.
- A1 `1aaead7`, typed-bound `a9e9e2f`, candidate impl `6dce37d`, A4 `9ea369a`: unchanged.
  No sourceGrant feature branch published yet. **No re-gate trigger exists.**
- A3 lane `7a7e1bf`, clean, remote-equal; main checkout + peer worktrees untouched.

## Re-gate checklist (armed for A1's sourceGrant publication)

On the published sourceGrant feature SHA, in a detached cold scratch, A3 will verify:
1. Revision authority — grant binds caller-opened document+revision; missing/malformed/
   foreign/stale grant refuses with named codes (no ambient `source_bytes()` privilege).
2. Valid inputs — real NUL/UTF-8 byte inputs through strict Clang+GCC with seed match.
3. Non-regression — existing seed/session tool paths unaffected; frozen Full-v2 rows
   reported verbatim (no relabel), plus the separate strict Policy-B gate.
4. Pins — seed marker == published pin, build-input blob == pin's `pep_ocaml.ml`,
   bundle determinism x3.

## Status

Parked per dispatch. Next: A1 sourceGrant SHA, A4's single seam handoff (stay out of
its lane), or A2 movement off park. No human action needed.
