# B4 Cycle 2 Slice 5 — Consequence: Value Semantics + Take + Task Transfer

**Packet:** PEP-WB-A4-20261104-B, Cycle 2 Slice 5. **Branch:** `spec/agent4-spec-lab`
**Premises (all ACCEPTED design, none implemented):** DEC-001 (independent
value semantics), DEC-002 (take invalidates source; no edit across async
initially), DEC-007 via FD/REF summaries (take moves owned values across
tasks; ordinary edit never crosses task/await). Seed evidence: rebinding
independence probes (`_build/a4-own/`, 3/4/3 etc.) — transfer-by-copy today.
**Status discipline:** derivations below are INFERRED (conditional on
premises), never ESTABLISHED; missing premises are listed, not assumed.

## 1. Question

What do value semantics + `take` + structured task transfer jointly imply
about mutable aliasing across task boundaries — and what breaks if any one
premise is weakened?

## 2. Derivation

- **C-1 (isolation for pure values, INFERRED):** after `take x` into a task,
  the parent cannot observe the task's mutations through any alias, because
  (i) no alias can exist (DEC-001) and (ii) the source binding is dead
  (DEC-002). Consequence: **for ordinary values, task isolation needs no
  borrow-checking at all** — it falls out of value semantics + take.
  Falsifier: any program where parent-observable state changes via a taken
  value (would refute DEC-001 or DEC-002, not this derivation).
- **C-2 (borrow quarantine, INFERRED):** an `edit` borrow live at `spawn`
  must either end before the spawn or be rejected. From DEC-002 (no edit
  across async) + DEC-007 (no edit across task/await): the spawn point is
  both an async and a task boundary. Test shape for A3 (future):
  live-`edit` + `spawn` in scope → refuse; `edit` ended + `spawn` → accept.
- **C-3 (handle transfer gap, UNKNOWN):** for explicitly identity-bearing
  handles (future), C-1 does not apply — sharing is the point of a handle.
  Then isolation requires the handle's own contract (move vs share vs
  clone-on-transfer). Missing premise M-1: handle transfer semantics.
  Without M-1, taking a handle into a task proves nothing about aliasing.
- **C-4 (cancellation cleanup order, INFERRED):** DEC-007 requires resources
  to survive cancellation until completion/supervised failure. A task holding
  taken values that gets cancelled must still run take-destructors/scope
  cleanup in take order (LIFO). So structured concurrency + ownership jointly
  require **cancellation-safe cleanup ordering** — a real obligation on the
  future task implementation, derivable now. Test shape: cancel a task
  holding two taken values; assert cleanup ran exactly once each, in reverse
  take order, with no use-after-take observable.

## 3. Complexity tradeoff (explicit)

Full borrow-state tracking at task boundaries (flow- + path-sensitive,
alias-aware) is the precise rule; the simple rule is "no outstanding borrows
at spawn/await/scope-exit" (conservative, rejects some safe programs).
**Recommend the simple rule first** (fail-closed, matches DEC-002's deferral),
and measure rejection pain on real programs before building the precise
analysis. Cost of precision now: a borrow checker before the ownership
inventory exists (cf. A4-OWNERSHIP-PREMISES §3 economy finding).

## 4. What this changes for current work: nothing to build, one thing to protect

- No syntax, no analysis, no task implementation is requested.
- Protection: when staged fact schemas gain borrow/access flags (AD-1), the
  flags must distinguish *value* borrows (erasable by C-1) from *handle*
  borrows (load-bearing) — a single `exclusive: true` bit cannot express the
  difference. This refines the earlier borrow-flag warning with the C-1/C-3
  distinction.

## 5. Missing premises (blockers for any ESTABLISHED claim here)

- M-1: handle taxonomy + transfer semantics (owner design decision).
- M-2: take-destructor / scope-cleanup ordering rules (future DEC-006 detail).
- M-3: cancellation delivery guarantees (DEC-007 detail: what "cooperative
  and observable" promises at each suspension point).
- M-4: whether `take` of a copyable value copies or moves observably
  (performance vs semantic identity — DEC-001 permits either representation;
  the task boundary makes the choice observable through timing/identity of
  cleanup, so it must be specified).
