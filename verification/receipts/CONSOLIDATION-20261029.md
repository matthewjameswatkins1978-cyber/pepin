# Consolidation receipt — proven vs tested vs unresolved (Agent 3, 2026-10-29)

**Branch:** `codex/bootstrap-agent3-verification@445b0e6` (this file lands
next commit). **Base:** `805062b`. **Reviewed pins:** A1
`codex/bootstrap-agent1-b0@95ab6c6` (source-read), A2
`codex/bootstrap-agent2-b0@52f1b380dadecb0f76d1bcdeebec590bc9ca1036`
(source-read + re-run). No builder files modified by Agent 3.

## PROVEN (machine-checked)

Nothing yet. The Lean model (`verification/lean4/`) is `DRAFT`:
`sorry`-free and structurally complete, but NOT kernel-checked —
`lake build` is `BLOCKED_SECURITY` on the held host. The first
`MODEL_PROVED` claim requires an approved-host build with `#print axioms`
output and the `BrokenVariant.lean` rejection transcript. Independent
tactic review verdict pending; BLOCKERs (if any) land as a Lean-only fix.

## TESTED (executed, exact commands recorded)

All on the OCaml seed via `pep.ps1 check/run/query/session --jsonl`
from the pinned base worktree (interpreter only; no C toolchain, no
binary generation):

- DEC-001 P1–P3: `3/3/4`, `2/1`, `1/2` as specified (case file
  `VALUE_COPY_DEC001.md`).
- N1–N4/E1: hole refusal, `edit` parse-absence, nested-`contains`
  fail-closed, controlled div-zero, main-not-invoked observation.
- U1–U5/E2: UTF-8/CRLF byte-exact spans; byte-derived columns.
- R1–R4: stale-revision, codepoint-split, 65536/65537 cap, forged-query
  rejections with exact codes.
- S1–S4: short-circuit order, first-error priority, hole
  scope/bindings, step-limit diagnostic.
- A2 emitter suite at pinned SHA: 3/3 PASS at the emit layer
  (`receipts/A2-emitter-rerun-52f1b38.md`); native compile/run excluded.

## UNRESOLVED (explicit, not hidden)

1. Lean kernel check + axioms audit (needs approved safe host).
2. Tactic-review verdict (in flight).
3. A13 differential suites at A1's pins (need the generated executable;
   held) — A1's 46–48/48 claims remain builder-reported.
4. Native C23 compile/run of any slice (Defender hold).
5. Entry-point divergence Q1 (needs Agent 1/2 + Matthew decision).
6. Transport-cap vs tool-fuel vs interpreter-fuel mapping through the
   staged Pep checker/emitter path (bridge work once execution clears).
7. Cross-revision reuse, GC/region, concurrency, FFI — out of scope for
   Road 1; not claimed anywhere.

## Standing rule

No `TESTED` row is promoted to proof; no model theorem will be
presented as implementation verification. Labels travel with every
claim: `DRAFT` | `TESTED` | `MODEL_PROVED` | `IMPLEMENTATION_REFINED`
| `BLOCKED_SECURITY` | `UNVERIFIED` | `NOT_RUN`.
