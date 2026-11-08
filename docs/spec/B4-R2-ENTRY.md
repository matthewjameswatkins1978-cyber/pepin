# B4 Resume-2 — Entry-Point Divergence: Interpreter Top-Level vs Native `main`

**Assignment:** LUCY-20261104-007 A4 THIRD, task 2. **Branch:** `spec/agent4-spec-lab`
**Pins:** seed `57fe424` (behavior re-verified live this slice); A2
`review/a2-bounded-emission` = `ea0bc9a` (emitter source read: main-required
lines 4202–4237, function-only lowering).
No implementation changed; no semantics frozen.

## 1. Measured behavior (TESTED this slice, seed; source-read, A2)

| Program shape | Seed `run` | Native emitter (`ea0bc9a`) |
|---|---|---|
| Top-level statements only | Executes them, exit 0 | Functions-only lowering; top-level statement handling UNKNOWN (no evidence found — needs A3 probe, not assumed refused) |
| `fn main` only, no top-level | **Silent exit 0 — `main` never invoked** (probe `_build/a4-entry/main_top.pep`) | Whole/epilogue emission REQUIRES top-level `fn main` with zero params returning `Int` ("requires a top-level function named main"; must-return-Int enforced) |
| Top-level statements + `fn main` | Runs top-level only; `main` ignored (same probe: printed `top-level`, not `from-main`) | Presumed main-called; top-level-statement fate UNKNOWN (same gap as row 1) |
| `main` return value | Never observed by `run` (never called); process exit 0 | Presumed process exit code by C convention (not independently verified here) |

## 2. Accepted design position

- FD §8 / DEC-004 (ACCEPTED): a selected entry file MAY execute top-level
  statements; importable modules declarations/pure-initializers only. The
  seed's top-level execution is accepted-direction behavior.
- Auto-invoking `main` on `run` appears in NO accepted decision. The native
  main-requirement is an implementation-subset restriction (PROPOSED/
  IMPLEMENTED-subset), not a semantic rule.
- Therefore the divergence is: two backends with different entry contracts,
  neither fully specified, and the seed's contract (top-level runs, main
  ignored) is the only one with accepted-design backing.

## 3. Compatibility analysis (no freeze; decision for Matthew/Lucy)

- **E-1 (document both, change nothing):** run = top-level only; native =
  main only. Multi-target programs carry both shapes. Zero breakage, some
  duplication. The `main`-ignored-by-`run` case deserves at least a diagnostic
  (E-3) so it is not mistaken for execution.
- **E-2 (run invokes `main` if present):** CHANGES seed behavior — programs
  with both shapes would execute twice (top-level + main call); programs
  relying on main-not-running (including every current `fn main` test
  fixture) change meaning. Rejected as default; would need a compat gate.
- **E-3 (diagnose, don't change):** `run` warns when a `main` function exists
  but is not invoked. Zero behavior change; closes the silent-exit-0 trap.
- **Recommendation:** E-1 + E-3 now; E-2 only with an explicit versioned
  language decision. Also specify the native exit-code contract (main's Int
  return → process status) when A2's native path is next reviewed.

## 4. Test handoff to Agent 3 (entry matrix, seed oracle + native observation)

- T-ENTRY-1: main-only file under seed `run` → silent exit 0 (locks current
  behavior; any future auto-invoke must flip this test deliberately).
- T-ENTRY-2: top-level + main under seed → top-level output only.
- T-ENTRY-3: top-level-statement program under native emission → record actual
  behavior (refusal with code, silent drop, or execution) — currently UNKNOWN.
- T-ENTRY-4: main-only program natively → exit code equals main's return.
- T-ENTRY-5: top-level + main natively → which runs; assert exactly one.

## 5. Status

ESTABLISHED: seed behaviors (executed). IMPLEMENTED-subset: native main
requirement (A2 source-read). UNKNOWN: native treatment of top-level
statements; exit-code contract. PROPOSED: E-1 + E-3. No freeze; decision
with Matthew/Lucy.
