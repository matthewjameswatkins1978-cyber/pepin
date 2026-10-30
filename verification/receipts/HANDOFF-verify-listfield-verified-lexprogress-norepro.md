# Top-blocker table verified; LexProgress mystery does NOT reproduce in natural forms (2026-10-30)

Cross-verification of the report's handoff section (`a25f520`,
`0ce0d8d`) on the combined stack (A1 `46bf1c0` + A2 emitter).

## 1. List-record-field 3-row table — VERIFIED exactly (their blocker #1)

| row | report | mine |
|---|---|---|
| `type Box { xs: List[Int] }` | checker valid, emitter unsupported, runs | check **valid**; emit **UNSUPPORTED** ✓ |
| build `Box { xs: [1, 2] }`, read `b.xs`, `length` | valid / unsupported / **runs → 2** | run rc=0 out=`2\n` ✓; emit **UNSUPPORTED** ✓ |
| (`List[Inner]` control) | valid | **valid** ✓ |

Emitter-only gap confirmed: language/checker/interpreter all accept
list record fields; only the emitter refuses. Their conversion of the
gating blocker from design question → bounded implementation task
stands.

## 2. The LexProgress mystery — does not reproduce (and my first probe was my own bug)

Their open item: *"`LexProgress` … is rejected earlier, at the
checker … remains unexplained"* while `List[Inner]` is fine.

| probe | result |
|---|---|
| A: `LexToken` + `LexProgress` only | `PEP_UNKNOWN_TYPE` — **my omission**: I forgot `LexCursor`, which `LexProgress.cursor` references. Disclosed as my 4th harness-class bug of the mission (dependencies read too late). |
| D: **all three** (`LexToken` + `LexCursor` + `LexProgress`) + trivial main | **`status=valid`** |
| E: **whole real `examples/pep_lexer.pep`** | **`status=valid`** |
| B: analogue `type Prog { tokens: List[Tok], … }` | **valid** ✓ |
| C: control `List[Inner]` | **valid** ✓ |

**The rejection does not reproduce** with dependencies complete or
with the whole real file at current pins — `List[LexToken]` inside
`LexProgress` typechecks fine. The closest way to get a rejection is
the partial-extraction probe (missing `LexCursor` → trivially
`PEP_UNKNOWN_TYPE`), i.e. the probe class my own first attempt fell
into. Their exact probe context is unknown to me (possibly a different
path — e.g. the checker-tool/`lexer_step` envelope, their blocker #5);
recorded as: **natural-form non-reproduction**, not as a refutation of
an unobserved method.

## Not verified this round

- Their census headline (types 1/4, functions 3/9 emittable) needs
  their exact extraction method — deferred, listed as pending.
- Ranked blockers #2–#5 individually already carry my own or
  double-sourced evidence (four-param ✓, family-A 9/9 ✓, budget
  walls ✓, `lexer_step` envelope = report's own).

Replay **163/163**; corpus/base untouched.
