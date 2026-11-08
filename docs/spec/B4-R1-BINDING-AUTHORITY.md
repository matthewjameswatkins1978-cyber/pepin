# B4 Resume-1 — Binding-Fact Authority vs Labels: Obligations, Handoff, Constraints

**Assignment:** LUCY-20261104-007 A4 THIRD, task 1. **Branch:** `spec/agent4-spec-lab`
**Pins:** A1 `f4eb231` (BindingFact shape, `BindingPool.add`, `facts()` read verbatim —
F1/F2/F3 CONFIRMED CURRENT, not historical); A3 `a4f2833` (BINDING-POOL-ATTACKS
receipt: O1c fail-open, A1/A2 conflict-drop, A4 aliasing); integration `cdbd742`
(candidate-4, independent verdict pending); seed `57fe424` (oracle).
No implementation changed; specification only.

## 1. Authority vs labels (formal distinction)

- A **label** is a claim carried on a fact (`document="d"`, `revision="r"`,
  `duplicateType=false`). Labels can be wrong, stale, or forged; nothing about
  carrying a label makes it true.
- **Authority** is a verified chain: (a) parsed source at a pinned revision →
  (b) checker-owned derivation at a pinned SHA → (c) host transport that
  re-validates identity/schema/provenance at ingress → (d) consumer checks that
  re-assert identity before use. Break any link and the fact is *untrusted*,
  however plausible its labels.
- A3's stale-BindingFact fail-open is exactly a broken link (c): type facts
  pass a `PEP_STALE_REVISION` ingress guard; binding facts cannot, because
  there is nothing to compare — no link, not a weak link.

## 2. Normative/proposed obligations

- **B4-AUTH-01 (PROPOSED, normative intent):** every staged fact kind that can
  change a verdict MUST carry source identity sufficient for ingress
  re-validation: `(document, revision)` at minimum. Today: `ResolvedTypeDecl`
  yes; `BindingFact` no; `CheckedFunction`/`ResolvedSignature` no.
  (Extends A4-SI-08 to bindings + callee facts.)
- **B4-AUTH-02 (PROPOSED):** ingress MUST apply the same staleness guard to
  bindings and callee facts as to type facts. Reuse `PEP_STALE_REVISION`;
  do not invent a parallel code family.
- **B4-AUTH-03 (PROPOSED):** pooling MUST NOT silently resolve conflicts.
  `BindingPool.add` must report `(added, conflicts)` or refuse; conflicting
  names must be surfaced, never first-wins-dropped. (A3 F2.)
- **B4-AUTH-04 (PROPOSED):** pooled-fact handles MUST NOT alias pool state.
  Deep-copy on `facts()` egress, or documented + enforced immutability.
  (A3 F3.)
- **B4-AUTH-05 (PROPOSED):** renumbered pooled ids (`BASE+n`) are transport
  keys, not provenance: no consumer may treat a renumbered id as evidence the
  fact was derived in the current revision. (Prevents a future repeat of the
  synthetic-id collision class in the contract doc.)

## 3. Counterexample conditions (when these obligations are violated)

- C-AUTH-1: a binding fact from revision R applied to R′ (same shape,
  changed type) flips a seed-`invalid` program to staged-`valid`. (A3 O1c —
  retest condition for the repair.)
- C-AUTH-2: two chunks pool conflicting facts for one identity; pool reports
  success with no conflict; consumer proceeds on first-wins data.
- C-AUTH-3: consumer mutates an egressed fact and a later chunk observes the
  mutation (pool corruption across chunk boundary).
- C-AUTH-4: self-consistent forged callee fact set validates a caller the seed
  rejects (A3 S4/O4 — same provenance hole, call side).

## 4. Test handoff to Agent 3 (no new harness; extend `binding_pool_attacks.py`)

- T-AUTH-1: re-run O1c/A1/A2/A4 cells at A1's repair SHA; assert closed.
- T-AUTH-2: cross-revision binding reuse (R facts → R′ source) → refuse with
  `PEP_STALE_REVISION` (requires B4-AUTH-01+02 implemented).
- T-AUTH-3: conflicting pool admission → conflict reported/refused (B4-AUTH-03).
- T-AUTH-4: egress-aliasing probe (B4-AUTH-04).
- T-AUTH-5: forged callee set (S4/O4 shape) with identity fields present →
  refuse (binds call side to the same fix).

## 5. Repair constraints to Agent 1 (smallest coherent change)

- Add `(document, revision)` at fact production (checker side, where the
  revision is known) or at pool admission (host side, where the target is
  known) — one place, not both; prefer production so facts are self-describing.
- Reuse the existing stale guard; no new refusal codes except the G3-style
  contradiction code if a contradictory (not merely stale) fact must be
  distinguished (see B4-C3 §2 — same rule, now extended to bindings).
- Keep renumbering; keep scope-key anchoring (ed140fb); preserve `utf8_check`
  21/21 as the no-regression gate.
- Do NOT re-derive binding types in Python to "validate" facts — that would
  make the host a semantic oracle (charter violation). Validation = identity +
  schema + closure checks only.

## 6. Status

PROPOSED: B4-AUTH-01..05. TESTED (as violations): C-AUTH-1..4 shapes at A3
`a4f2833` (O1c, A1/A2, A4, S4/O4). UNKNOWN: A1 repair SHA (does not exist yet);
integration `cdbd742` behavior under these probes (A3 gate pending). The dup-type
fix `448c689` is builder-reported only — independent verdict pending, same as
the closure obligations in B4-C1.
