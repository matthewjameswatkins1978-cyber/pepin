# Agent 4 — Ownership Premises: Value Semantics, `read`/`edit`/`take`, Safe Aliasing

**Standing queue item 1, bounded slice.** **Branch:** `spec/agent4-spec-lab`
**Grounding:** DEC-001 (`3105b002…`), DEC-002 (`bc76b966…`), seed at campaign
`57fe424`, three executed probes (`_build/a4-own/`, ignored scratch).
**Scope:** what the seed already guarantees, what `edit`/`take` must add, and one
derived joint consequence with task isolation. No syntax proposed, nothing frozen.

## 1. Premises the seed already establishes (all TESTED this slice)

- P-V1: ordinary values are deeply immutable — `append`/`prepend`/`reverse`
  copy; assignment only rebinds; probe `dec001_illustration` prints 3/4/3.
- P-V2: rebinding one binding never affects another (`rebind_no_alias` → 1/1;
  `record_copy` → 1/2).
- P-V3: **no shared mutable identity is expressible.** Aliasing hazards of the
  `edit`/`take` family cannot currently be written, let alone triggered.
- P-V4: no closures/captures exist, so no captured-alias escape channel exists.
- P-V5: the tool boundary moves only immutable snapshots; `say` is denied there.

Consequence: value semantics (DEC-001) is not an aspiration for the seed subset —
it is a structural property of having no mutation primitive. Any future soundness
argument must preserve exactly this: *no program-observable aliasing*.

## 2. Falsifiable statements (for Agent 3's corpus, present and future)

- FS-1: "No seed-subset program can observe aliasing between two bindings."
  Falsifier: a program where action via binding A changes binding B's observed
  value. Status: HOLDS (3 probes). **Expiry condition:** the day a mutable
  container or in-place update lands without alias discipline, rerun FS-1 first.
- FS-2: "`var` rebinding is always safe to treat as a copy." HOLDS; same expiry.
- CE-O1 (future template): given a hypothetical mutable `Buf` with
  `buf_set(edit b, i, v)` and NO disjointness checking,
  `var a = b; buf_set(edit a, 0, 99)` observed via `b` MUST read stale-or-changed
  data — the exact test to write when the feature lands. Today inexpressible
  (no `Buf`, no `edit`), which is itself the finding of §3.
- CE-O2 (future template): double-`take` (`take x` twice) and use-after-`take`
  must be statically rejected; the seed already owns a reusable refusal shape
  (`PEP_UNCONSTRAINED_BINDING` for unusable bindings — suggestion, not verdict).

## 3. Economy finding: `edit`/`take` syntax is premature until identity exists

`var` + rebinding covers every mutation expressible today. `edit`/`take`
annotations on copyable immutable values would be pure ceremony: nothing to be
exclusive over, nothing to transfer. **Recommendation:** do NOT add `edit`/`take`
surface syntax before at least one identity-bearing or in-place-mutated type
exists (DEC-001 "exact types/API … future design work"). When it does, the
minimal coherent slice is: one owned handle kind + `take`-invalidation +
overlap rejection for simultaneous `edit`s — NOT the full borrow checker.
(Complexity-economy duty, contract §D.)

## 4. Derived joint consequence: transfer × task isolation (INFERRED, not established)

DEC-002 defers `edit` across async boundaries; DEC-007 (via FD/REF summaries,
*reported*) moves owned values across tasks with `take`. Jointly they imply:
**task transfer is sound only for values with no outstanding exclusive borrows,**
so the compiler must know borrow state at every task boundary (`spawn`, `await`,
scope exit). If a future design allows borrows to cross tasks, it must carry a
separately specified proof model — the current deferral exists precisely because
that model is absent. Agent 3: this yields a future test shape — a value with
an outstanding `edit` must be refused at `spawn`/`take-into-task` under the
initial model; any acceptance is a soundness event, not a feature.

## 5. Early warning for staged checking (feeds A4-SI-08)

When access-mode facts enter the staged fact schema, they must carry the same
provenance discipline as type facts. The `duplicateType:false` hardcoding
(A3 CE-1 root cause) must not recur as a hardcoded `exclusive:true` or an
unflagged borrow state. Fact-schema review (AD-1) should cover borrow flags
from day one.

## 6. Open (not pursued here)
- Exact identity-bearing type inventory (owner decision; DR-05/DR-12).
- Disjointness proof rules (field/index granularity) — needs a concrete proposal.
- Copy-cost contracts for large values (DEC-001 leaves open; performance work).
