# Agent 4 Slice 3 — Conformance Mapping Update + Hole-vs-`?` Recommendation

**Packet:** PEP-A4-20261104-001, Slice 3. **Branch:** `spec/agent4-spec-lab`
**Seed probes executed this slice** (campaign `57fe424`, `_build/a4-probes/`,
ignored scratch): 10 `check --json` probes over `?` positions. All results below
are measured, not inferred.

## 1. Probe results: where `expr ?` stands today

| # | Source shape | Measured status / first code |
|---|---|---|
| P-1 | `let y = x?` (Eof after) | **incomplete**, no diagnostic — trailing `?` becomes a hole-statement |
| P-2 | `let b = a ?` (space) | **incomplete** — same split |
| P-3 | `let y = f(1)?` | **incomplete** — same split |
| P-4 | `let m = n??` | **incomplete** — two hole-statements |
| P-5 | `let y = x? + 1` | **incomplete** — splits to `x` + `(?+1)` hole expression |
| P-6 | `let y = id(x?)` (before `)`) | **invalid** `PEP_PARSE_EXPECTED` — inside parens trailing hole is an error |
| P-7 | `let y = 1 2` (no `?` at all) | **valid** — trailing `2` silently becomes a second statement |
| P-8 | `fn f() -> Int { return ? }` | **incomplete** (prefix hole, expected `Int`) — unaffected by anything below |
| P-9 | `let h = ?name` / `id(?)` | **incomplete**, prefix holes — unaffected |

Mechanism (seed parser): `parse_tail` handles only `.` and binary operators, so a
`Hole` token after a complete expression ends the expression; at statement level
the hole re-enters `parse_stmt` as a new hole-statement (P-1..P-5); inside
delimited contexts `expect_sym` rejects it (P-6). P-7 shows the generality: the
seed has NO trailing-token rejection — any juxtaposed expression silently splits.

## 2. Does the conflict actually exist? Yes — in exactly one place.

- **Exists:** at statement level (and any position where a trailing hole splits
  silently), `expr ?` already HAS a meaning: expr-statement + hole-statement,
  status incomplete. Giving it the propagation reading changes the meaning of
  currently-incomplete programs (hole count flips 1 → 0; queries/fills see a
  different tree). Incomplete programs cannot run, so no runtime changes — but
  it is a real observable change, not a free slot.
- **Does not exist:** inside `(…)`/`[…]`/argument lists the slot is a hard parse
  error today (P-6) — propagation there is pure new capability. Prefix holes
  (P-8, P-9) are untouched under every alternative. `x?y` must remain a named
  hole (lexer already so tokenizes; see §3 rule H-1).
- **Second, larger finding:** P-7 (`let y = 1 2` valid) is an independent grammar
  hazard — silent statement-splitting swallows typos. Any postfix operator
  inherits this collision class; fixing it is separable from `?` (see R-B).

## 3. Alternatives compared

- **H-0 (do nothing):** keep `expr ?` = expr + hole-statement. Cost: postfix `?`
  can never be added; DEC-003G/009 direction dies. Rejected (contradicts
  accepted decisions).
- **H-A (positional, no whitespace condition):** any `?` after a complete
  expression (same line or not) = propagation. Cost: changes P-1..P-5 readings;
  `x\n?` flips meaning. Simple grammar, nonzero migration of incomplete
  programs.
- **H-B (positional + adjacency):** `?` = propagation IFF immediately
  (no space/newline) after a complete expression AND not followed by
  identifier chars; otherwise current hole rules. Cost: `f(1) ?` stays a hole
  (mild surprise); one whitespace-sensitive rule; formatter must preserve
  adjacency. Benefit: **zero** meaning change for every program whose `?`
  tokens are all prefix-position or spaced — i.e. every program anyone would
  defend as intentional.
- **H-C (new spelling):** abandon postfix `?` for e.g. keyword/operator.
  Cost: reopens DEC-003G/009 (Matthew-level); benefits nothing H-B cannot do.
- **R-B (separate hardening, recommended regardless):** reject trailing tokens
  that form no valid continuation (kill silent splitting, P-7). Cost: turns
  currently-valid-but-suspicious programs (`let y = 1 2`, `say("a") "b"`) into
  diagnostics — an explicit compatibility break needing owner approval (AD-4).
  Benefit: removes the entire collision class for ALL future postfix syntax and
  catches typos. Independent of H-A/H-B.

## 4. Evidence-based recommendation (no freeze)

Adopt **H-B** as the candidate rule, with these exact terms for the V0 fixture
suite: `?` immediately adjacent after a complete expression, not followed by
`[A-Za-z0-9_]`, binds at call/field tightness (tightest; `(f(x)?)+1` parses as
`((f(x)?)+1)`), and applies only where the operand type-checks as
`Result[T,E]` with a compatible enclosing error contract. Keep `x?y` = named
hole, prefix `?` unchanged, spaced ` ?` = hole-statement (documents P-2 as
intentional, not accidental). Route **R-B** to Matthew/Lucy as AD-4 (it is a
compatibility break, however justified). Do NOT freeze: fixtures first, per
matrix rows below; DEC-003G's own "requires formal tests" is satisfied by
exactly this suite, not by this prose.

## 5. Conformance mapping update (adds to CONFORMANCE-MATRIX.md rows)

| New row | Requirement (from Slices 1–2) | Covering test today | Proposed fixture |
|---|---|---|---|
| M-H1 | `?`-slot taxonomy P-1..P-9 | none (probes are scratch, not suite) | commit P-1..P-9 as `test_hole_slot_taxonomy` asserting measured codes |
| M-H2 | H-B adjacency rule | none | `f(1)?` propagation-parse vs `f(1) ?` hole-parse pair (post-implementation) |
| M-H3 | `x?y` stays named hole | none | `let y = x?z` → named-hole `?z`, never propagation |
| M-S1 | A4-SI-01 duplicate rejection, all partitions | A3 matrix (dev-branch) + **missing seed anchor** | Slice-1 D-04 seed fixtures (dup type/fn) |
| M-S2 | A4-SI-03..07 closures & boundary rows | A3 13-cell matrix (dev-branch) | mirror rows against seed oracle in core suite |
| M-S3 | T-stale (CE-3) | none | staged R→R′ refusal with declared code (AD-2) |
| M-S4 | Refusal code family (AD-2) | none | decision + one fixture per code |
| M-G1 | Silent-split hazard P-7 | none (A3 noted juxtaposition-adjacent shapes) | `let y = 1 2` → currently valid; AD-4 decides its fate |

## 6. Minimum unresolved decisions (for Matthew/Lucy)
- AD-1 (Slice 2): global-consistency ownership + fact-schema duplicateType.
- AD-2 (Slice 2): staged refusal code family.
- AD-3 (Slice 2): confirm fail-closed subset gate as precondition.
- AD-4 (new): R-B trailing-token rejection — compatibility break approval.
- U-3 (carried): SourceBytes acceptance ruling (RX-01).
- U-5 (carried): remaining DEC direct reads as slices need them.

H-B itself is a RECOMMENDATION with probe evidence, not a frozen rule; freezing
belongs to the V0 grammar gate with the M-H1..H3 fixtures green.
