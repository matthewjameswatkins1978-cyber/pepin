# Agent 2 — Outbox (append-only)

Receipts are appended newest-last and each is bound to a pushed commit.

**Why this file exists.** The Basic Memory A2 outbox
(`cloud|703e9fd6-…|ff4f6328-…|7b7b441e-…`) is **not reachable** from the 6 Nov Pi
session's MCP connection: the only indexed projects are
`matthew-watkins-s-workspace/{main, lantern, reusery, getting-started, agent-x}`.
Rather than drop the receipt, it is recorded here in the repo, following the
existing `runtime/pep_text/AGENT4_OUTBOX.md` convention. This is a receipt log,
not a second status board — A1 alone writes Current Status.

---

## BOOT-A2-20261106-01 — G0 re-pin published

- **Agent:** 2 (native/backend).
- **Branch:** `codex/a2-bounded-emission`. **Worktree:** `D:/Projects/wt-a2-bounded`.
- **Re-pin commit:** `1658ea9da74f3b166822ffe7fca0d69667cf9fbf`
  (remote verified: `origin/codex/a2-bounded-emission` = `1658ea9`).
- **Prior remote head:** `123d8b3` — the three-line repair was absent, as dispatched.

### Delta (exactly the three dispatched lines)

1. `A1_SHA = "727f8af4d019e6e5e235ac26077a12b166b9c080"` (was `2ad750b`).
2. `prepare()` fetches `("pep_chunk_contract.py", "pep_chunk_contract.py")` with the pin.
3. `duplicate_fact` carries `document: sem["document"], revision: sem["revision"]`.

### Why — measured, not assumed

- The A2 worktree has **no** `pep_chunk_contract.py` at all, and
  `_build/pep_chunk_contract.py` was a 4 Nov copy that **predated** the `2ad750b`
  pin marker. The probe therefore only ever ran against a stale contract; a fresh
  checkout would have raised `ImportError`.
- At `727f8af`, `chunk_helper.checked_fn_value` / `resolved_sig_value` read
  `sig["document"]` / `sig["revision"]` off the fact itself (F2: checker-stamped
  at production). The hand-built duplicate-name negative died on `KeyError`
  instead of exercising the `PEP_DUPLICATE_FUNCTION` refusal it exists to test.

### Cold start

Deleted before the run: `_build/a1_seed/`, `_build/pep_chunk_contract.py`,
`_build/a1_{lexer,parser,checker}.pep`, `_build/a1_chunk_helper.py`,
`_build/seam_*`, `_build/str_concat_seed.pep`.

Command: `python tests/probe_seam_chunked.py` → **exit 0**.

### Evidence

- `bundle_sha256 7fc7bb4ab909265eee5c125bf398a4ab73eb5faabc96f6ada692bdf3be12b846`
- Chunks valid: declaration 18 nodes, `make_token` 55, `add_one` 8, `main` 5.
- Strict Clang `-std=c23` and GCC `-std=c2x`, `-Wall -Wextra -Wpedantic -Werror -O2`:
  document order → `42`; reverse order → `42`.
- Seed oracle → `42`.
- **11** enumerated negatives all refuse (11, not 12 — matches A3's count):
  `neg-no-call-fact`, `neg-ambiguous-call`, `neg-missing-target`,
  `neg-ambiguous-target`, `neg-arity-mismatch`, `neg-foreign-result`,
  `neg-stale-revision` (`PEP_STALE_REVISION` at the transport gate),
  `neg-unit-index`, `neg-dup-external-name` (`PEP_DUPLICATE_FUNCTION`),
  `neg-unit-order-clang`, `neg-unit-order-gcc`.
- Provenance parity (`git hash-object` against the `727f8af` blobs):
  `_build/pep_chunk_contract.py` = `0751391f3a13a5637c5cafa2bdc2753d8a1b3356`;
  `_build/a1_seed/pep_ocaml.ml` = `923769a773627e804132c506be2a7a9adc665708`.
  Both byte-identical to the pin.

## BOOT-A2-20261106-02 — G-A2-7 native `str_concat` preserved and published

- **Commit:** `3f2d711e4289054c5cae577f5b71b30623a31723`.
- Pre-existing uncommitted work from the 4 Nov A2 session, re-verified cold at the
  `727f8af` pin in the same run as the re-pin, then committed rather than left dirty.
- `str_concat` is a builtin, so both the Str-result classifier and the two-argument
  dispatch classify it directly; Str-returning user functions stay refused at the
  `say(<Str call>)` boundary.
- Runtime is a per-run bump pool (no buffer reuse), capacity
  `PEP_STR_CONCAT_CAPACITY 4096`, overflow fails closed with
  `PEP_RUNTIME_STR_CONCAT_RANGE`. That is a documented divergence from the
  unbounded seed builtin, pinned by its own capacity negative and never seed-compared.
- Cold-start stages: `str-concat-check` valid, `str-concat-emit` emitted,
  `str-concat-seed` / `-clang` / `-gcc` all print
  `hello world` / `Unknown variable 'x'` / `buf-1 onebuf-2 two`,
  `str-concat-capacity` exits 1 with `PEP_RUNTIME_STR_CONCAT_RANGE`.

### Next READY

A4 `spec/agent4-spec-lab@c25fab6` `advance_position` record-result fixture
(`docs/spec/FINISH-K4-BLOCKER-TEST.md`) on the actual checker/native path; repair
only the **first** refusing native layer. If it passes, measure SourceBytes native
ingress next.

### Not claimed

No frozen Full-v2 run, no Candidate7, no acceptance, no master / `CURRENT.md` /
`manifest.json` change, no budget-cap change, no frozen-runner edit.

## BOOT-A2-20261106-03 — K4 falsifier triggered: record returns ALREADY lower natively

- **Commit:** `6e0ac7436cce8cc05b5050cc3389957521b66266`.
- **New probe:** `tests/probe_k4_record_return.py`; two cases added to
  `tests/probe_integration_case.py`.
- **A4's own falsifier** (`docs/spec/K4-STDLIB-PRIMITIVE.md`): "A3 guard-read showing
  L3-shape already lowers at 123d8b3 (record returns via existing machinery) — then the
  primitive EXISTS and this card flips to NO-CHANGE, residual L6 control-flow."
  **It already lowers.** No emitter change was needed.

Evidence — both branches of `examples/pep_lexer.pep:90`, one fixture each
(`python tests/probe_k4_record_return.py` → **exit 0**):

| branch | call | check | emit | strict Clang `-std=c23` | strict GCC `-std=c2x` | seed oracle |
|---|---|---|---|---|---|---|
| newline (`byte == 10`) | `advance_position(1, 1, 10)` | valid, 0 diags | emitted, 6537 bytes | `21` | `21` | `21` |
| ordinary | `advance_position(4, 7, 65)` | valid, 0 diags | emitted, 6537 bytes | `48` | `48` | `48` |

Both compilers with `-Wall -Wextra -Wpedantic -Werror -O2`. Negative: the L4-shape
`make_token` fixture with `text: 0` → `status=invalid`,
`PEP_TYPE_MISMATCH` "Record field value type does not match its declaration", so a
record-return path reuses the existing field-type gate rather than laundering.

**Consequence:** K4 is **NO-CHANGE** on the primitive. The residual at the lexer header
is **L6 control flow** (while + mutable state + source grants), not a missing record
primitive.

### Two incidental findings (both measured, both for A4)

1. A4's doc says the seed oracle "prints 2/1/4/8" via top-level
   `say(advance_position(...).line)`. **That does not reproduce.**
   `say` is `[Str] -> Unit` at the `727f8af` seed *and* at the campaign tree
   `57fe424` that A4 reports testing at, so `say(a.line)` is `PEP_TYPE_MISMATCH`
   at 8:5. The **values** are right; the call shape needs `int_text`. The committed
   oracle uses `say(int_text(...))` and does print `2\n1\n4\n8\n` at seed.
2. Two call sites in one `main` exceed the one-shot checker ceiling:
   `PEP_RUNTIME_STEP_LIMIT` at `2441:3`. Hence one fixture per branch.

### Not claimed

No frozen Full-v2 run, no Candidate7, no acceptance, no master / `CURRENT.md` /
`manifest.json` change, no budget-cap change, no frozen-runner edit, and no claim
that record returns were *missing* — they were never missing.

## BOOT-A2-20261106-04 — SourceBytes: byte access lowers, the grant does not

- **Commit:** `0843161ed36e8af1b0d4815a9f41503a6f6c8c88`.
- **New probe:** `tests/probe_source_bytes_runtime.py`; `sb-param` and `sb-grant`
  cases added to `tests/probe_integration_case.py`.

Two questions, kept separate because they have different owners.

### 1. Does the emitter lower SourceBytes byte access? **YES**

A function taking a `SourceBytes` parameter and reading it through `byte_length` /
`byte_at` — the shape the real lexer's `scan_*_at` helpers use — checks valid and
**emits** (6008 bytes whole program, 320 bytes unit).

The first refusal on this fixture was **not** a SourceBytes limitation: the
if/else-only body refused with *"Pep C23 functions require a return statement"*, a
shape rule. The trailing-return form emits.

### 2. Can a native program OBTAIN a SourceBytes? **NO**

`source_bytes()` refuses with *"Pep C23 cross-chunk call has no resolved call fact"* —
it is not lowered as a builtin. **That is the real ingress gap**, and it is a
host-grant boundary, not an emitter primitive (A4's K4 elimination table already
assigned it to the host).

### Runtime substrate (labelled as such, not Pep-level native execution)

Because (2) refuses, a Pep-level native program cannot yet exercise byte access end
to end. The emitted C is therefore included by a small driver with only the emitted
`main` renamed. Strict Clang `-std=c23` and GCC `-std=c2x`
(`-Wall -Wextra -Wpedantic -Werror -O2`), **both identical**:

| input | expected | observed |
|---|---|---|
| empty source | `-1` | `-1` |
| `"A"` | `65` | `65` |
| NUL first byte | `0` | `0` |
| UTF-8 U+00E9 (`0xC3 0xA9`) | `195` | `195` |

Fail-closed negatives, each its own process:

| negative | exit | stderr |
|---|---|---|
| `byte_at` past the end | 1 | `PEP_RUNTIME_BYTE_RANGE` |
| `NULL` data with length 5 | 1 | `PEP_RUNTIME_INVALID_SOURCE_BYTES` |

### Consequence

The next actual dependency for the lexer is **not** byte access and **not** record
returns. It is the **`source_bytes()` host grant** (host-owned) plus **L6 control
flow** (while + mutable state). A2 has no emitter primitive left to add for either
of the two cards it was handed.

### Not claimed

No frozen Full-v2 run, no Candidate7, no acceptance, no master / `CURRENT.md` /
`manifest.json` change, no budget-cap change, no frozen-runner edit. The runtime
table is a substrate test with a hand-written driver, not Pep-level native execution.

## BOOT-A2-20261106-05 — L6 measured: while lowers; the recursion blocker is computed call args from non-main functions

- **Commit:** `fec4806af6035599cd2e3753c80b5f65d1bf4876`.
- Cases added to `tests/probe_integration_case.py`: `while-byte`, `recursion`,
  `call-arg-expr`, `computed-arg-main`, `computed-arg-nonmain`.

The closure plan says *"measure recursion, not assume it's unsupported at current
head"*. Measured.

### while + mutable state: **LOWERS**

`while !(byte_length(source) <= offset) { offset = offset + 1 }` over a `SourceBytes`
parameter with `var` — check valid, **emits**.

Incidental: **`<` is not a Pep operator at all** (`PEP_UNEXPECTED_CHARACTER`). The
language has `<=`, `==`, `!=`, `&&`, `||`, `!`. The real lexer writes
`while !(a <= b)`, and so does the fixture. My first fixture used `<` and was
invalid Pep, not an emitter gap.

### recursion: refused — but **not because it is recursion**

The discriminating pair isolates the trigger. Same callee, same computed argument
shape; the **only** difference is the call site:

| call site | program | check | emit |
|---|---|---|---|
| `main` | `f(1 - 1)` | valid | **emitted** |
| ordinary function | `f(n - 1)` inside `g` | valid | **unsupported** — *"Pep C23 one-parameter calls require one argument and a call-free target expression"* |

Ruled out as causes, each by measurement:

- **call depth** — `main -> g -> f` emits.
- **computed arguments as such** — `add_one(20 + 21)` from `main` emits.
- **`if` before the call** — `if n <= 0 { return 0 } else {}` then `return f(n) + 1`
  emits.
- **arithmetic after the call** — `return f(n) + 1` emits.

So the real A2-owned blocker for the lexer's recursive/stateful helpers is
**computed call arguments from non-main functions**, not recursion and not `while`.

### One honest refusal that is a rule, not a gap

`f(1) + g(2)` refuses with *"Pep C23 rejects two fallible operands because C operand
evaluation order is unspecified"*. That is a deliberate safety rule and should stay.

### Not claimed

No frozen Full-v2 run, no Candidate7, no acceptance, no master / `CURRENT.md` /
`manifest.json` change, no budget-cap change, no frozen-runner edit. `while-byte`
emits but cannot be run natively yet, because it needs the `source_bytes()` grant.
