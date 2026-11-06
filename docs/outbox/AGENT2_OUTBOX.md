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

## BOOT-A2-20261106-06 — computed call arguments inside non-main functions now emit

- **Commit:** `e2b5bee1d1ff88aa6939152ee04edce46d8dcc09`.
- **New probe:** `tests/probe_computed_call_args.py`.
- **Emitter change:** `tests/pep_c23_emitter.pep` — new
  `pep_c23_parameter_value_expression`, used by the generic call branch of
  `pep_c23_parameter_expression`.

### The defect

The call-result purity gate required a call argument to be a **bare parameter
name**. So `return f(n - 1) + 1` inside an ordinary function refused with
*"Pep C23 one-parameter calls require one argument and a call-free target
expression"*, while the same shape in `main` emitted — `main` has no parameters,
so it took the zero-parameter path and a different predicate. That asymmetry is
what made the refusal look like a recursion limitation.

A computed argument over parameters and literals is just as pure as a bare name,
which is all this gate claims. The gate now accepts it.

### Deliberately NOT widened (asserted as negatives)

| negative | result |
|---|---|
| `f(1) + g(2)` — two fallible operands | still refused: *"rejects two fallible operands because C operand evaluation order is unspecified"* |
| `f(g(n))` — nested call as an argument | still refused: *"call-free target expression"* |

### Evidence — `python tests/probe_computed_call_args.py` → exit 0

| case | seed | strict Clang `-std=c23` | strict GCC `-std=c2x` |
|---|---|---|---|
| `recursion` (`countdown(3)`) | `3` | `3` | `3` |
| `computed-arg-nonmain` (`g(1)`) | `1` | `1` | `1` |

Both compilers with `-Wall -Wextra -Wpedantic -Werror -O2`.

### No regression

- `tests/probe_seam_chunked.py` → exit 0 (4 chunks, both assembly orders, 11 negatives)
- `tests/probe_k4_record_return.py` → PASS
- `tests/probe_source_bytes_runtime.py` → PASS
- `tests.test_a14_c23` → 12/12 OK
- 87 further emitter tests OK: `test_c23_emitter_invariants`, `_sections`,
  `_section_identity`, `test_c23_arity`, `test_c23_str_result`, `test_c23_say`,
  `test_c23_bounded_emission`, `test_c23_str_contains`, `test_c23_emitter_field_use`
- 5 representative `test_c23_collections` cases OK. **The full collections suite
  was not run**: 129 tests at ~33 s each is ~70 min, which exceeds a session. That
  is pre-existing slowness, not a regression from this change.

### Bundle hash moved — A1/A3 must re-pin

`c1908d06bb7752e43bb5af3f743ab3bdf8bea45d0aec25b43ee3a65805f9e9ad`
→ `0043343992e89847dde884a7c155385f83e2815c0b5d27fb855bbf197df39953`

## BOOT-A2-20261106-07 — `source_bytes()` native grant: contract proposal for A1

Not implemented. This is the coordination item the dispatch asked for, and the
host side is A1's.

### What the seed actually does (authoritative, read at the 727f8af pin)

`source_bytes()` is a **host-authorised grant**, not a language primitive. With no
grant the seed fails closed:

```
PEP_RUNTIME_SOURCE_CONTEXT: source_bytes is available only for a host-authorised v2 semanticTarget
```

(`pep_ocaml.ml:847-849`; the grant arrives as `?(source_bytes_value=None)` on
`execute`.) So a native program must not be able to mint a SourceBytes from
nothing either.

### Proposed contract

1. **Semantics preserved.** `source_bytes()` stays a grant. Ungranted → fail closed
   with `PEP_RUNTIME_SOURCE_CONTEXT`, exit 1. Same code, same meaning.
2. **Grant mechanism.** The emitted C runtime holds one
   `pep_source_bytes pep_granted_source` plus a `_Bool pep_source_granted`. The
   main wrapper initialises it once, at startup, from the host: `argv[1]` names the
   source file, the runtime reads it, sets the flag. No `argv[1]` → no grant.
3. **Ownership split.**
   - **A2 (emitter):** lower `source_bytes()` to a runtime accessor that aborts when
     ungranted, and emit the grant initialisation in the main wrapper.
   - **A1 (host):** decide and document what the host passes, and confirm the
     checker's `SourceBytes` type identity is unchanged.
4. **Fail-closed negatives to pin:** no grant → `PEP_RUNTIME_SOURCE_CONTEXT`;
   unreadable file → a distinct code; empty file → a valid zero-length SourceBytes
   (not an error); `byte_at`/`byte_length` bounds behaviour unchanged (already
   proven in receipt 04).
5. **Explicitly not in scope:** no new language feature, no checker change, no cap
   change, and no general file access — one grant, set by the host, at startup.

### Why this shape

It keeps the seed's zero-argument `source_bytes()` meaning ("the document being
compiled") without inventing a language-level file API, and it keeps the trust
boundary where the seed already puts it: the host decides, the program consumes.

## BOOT-A2-20261106-08 — entry-parameter SourceBytes grant implemented (A2 half)

- **Commit:** `b22846149c073241d969458fd0375fbcff77e9dc`.
- **New probe:** `tests/probe_source_grant_entry.py`.

A1's draft contract (`docs/NATIVE_SOURCE_GRANT_CONTRACT_DRAFT.md` @a802290, posted
to #16 as comment 6690088045) superseded my proposal: the grant rides the **entry
declaration**, and `source_bytes()` as a CALL stays refused. Adopted. My own
proposal's `argv[1]`-based `source_bytes()` lowering is withdrawn.

### What was implemented (A2's half)

1. **Entry gate.** Exactly one new shape is admitted:
   `fn main(<one SourceBytes parameter>)`. Everything else is unchanged — Int,
   Bool and two-parameter mains still refuse with the identical diagnostic.
2. **Non-arena epilogue.** A grant wrapper reads `argv[1]` once and passes it to
   the entry as `(pep_source_bytes){ .data, .length }`.

### Fail-closed behaviour, measured

| case | result |
|---|---|
| no `argv[1]` | exit 1, `PEP_RUNTIME_SOURCE_CONTEXT` — refused **before** the entry runs |
| unreadable path | exit 1, `PEP_RUNTIME_SOURCE_OPEN` |
| empty file | a **valid** zero-length SourceBytes; `byte_at(0)` then trips `PEP_RUNTIME_BYTE_RANGE` |
| Int / Bool / two-parameter main | still refused, unchanged diagnostic |
| `source_bytes()` as a call | still refused, "no resolved call fact" |

### Native evidence — strict Clang AND GCC, real files

| file bytes | first byte |
|---|---|
| `"A"` | `65` |
| `\x00A` (NUL) | `0` |
| `\xC3\xA9` (U+00E9) | `195` |

### COST DISCIPLINE — measured twice, and the first two attempts were over budget

A second traversal of `topLevelFunctions` to locate the entry pushed the
near-ceiling recursive-depth fixture over the fixed 100k budget
(`PEP_RUNTIME_STEP_LIMIT` at 4455:8). Unconditional parameter lookups in the
function gate did it again (9183:18). `grantEntry` is now computed inside the
prototype loop that already walks that list and already calls
`pep_c23_parameters`, and the gate's lookups run only for a one-parameter `main`.
No cap was raised.

### Host side is A1's and is NOT done

- `session_semantic_target` uses `session_exact_fields fields
  ["document";"revision";"entryFunctions"]`, so a `sourceGrant` field is **rejected
  today** with `PEP_SEMANTIC_TARGET_FIELDS`.
- The seed's `run` has no grant path at all (`PEP_RUNTIME_SOURCE_CONTEXT`), so the
  seed oracle for this shape cannot be produced from `run` — only through
  `semanticTarget`, whose only SourceBytes it supplies is `analysis.source`.
- So: the emitter lowers the declared shape; **authorising it remains the host's
  decision, and today the host rejects the field that would carry the authorisation.**

### Windows toolchain note

MSVC's CRT marks `fopen`/`ftell` deprecated and clang reports that under the
bundle's `-Werror` as a call-site diagnostic. `_CRT_SECURE_NO_WARNINGS` does not
suppress it; the two call sites carry `#if defined(_MSC_VER) #pragma
warning(disable: 4996) #endif` instead. Scoped to the granted wrapper only.

## BOOT-A2-20261106-09 — lexer closure measured: 4/10 native, ZERO emitter refusals

- **Commit:** `4bf597a1bc6831c90ccab288f3d4ffaf52df8165`.
- **New probe:** `tests/probe_lexer_function_closure.py`.

The A2-side closure measurement for Road 1, on the actual top-level functions of
`examples/pep_lexer.pep` rather than a synthetic feature matrix. Each function is
compiled as a real program with only the type declarations and callees it
transitively needs; when it emits, the C is built with strict Clang `-std=c23`
**and** GCC `-std=c2x` (`-Wall -Wextra -Wpedantic -Werror -O2`) and run.

| function | check | emit | native |
|---|---|---|---|
| `ascii_letter` | valid | emitted | clang ok, gcc ok |
| `ascii_digit` | valid | emitted | clang ok, gcc ok |
| `ascii_continue` | valid | emitted | clang ok, gcc ok |
| `advance_position` | valid | emitted | clang ok, gcc ok |
| `utf8_check` | `PEP_RUNTIME_STEP_LIMIT` | — | — |
| `make_cursor` | `PEP_RUNTIME_STEP_LIMIT` | — | — |
| `make_token` | `PEP_RUNTIME_STEP_LIMIT` | — | — |
| `make_progress` | `PEP_RUNTIME_STEP_LIMIT` | — | — |
| `lexer_start` | `PEP_RUNTIME_STEP_LIMIT` | — | — |
| `lexer_step` | transport 1 MiB | — | — |

### The finding that matters

**There are ZERO emitter refusals.** Every lexer function the checker can check,
the emitter lowers, and both compilers run. The remaining six are blocked by the
checker's fixed 100k step budget (5) and the 1 MiB JSONL transport limit (1) —
both A1's lane.

So **A2's emitter is not the bottleneck for the lexer.** Adding emitter features
now would be speculative: there is no measured emitter gap to close. The next real
dependency is staged checking, which A1 is already pricing.

### Two probe bugs found and fixed while measuring

Both had produced misleading rows, and both were probe defects, not emitter
defects:

1. A brace splitter that cut multi-line parameter lists at their first line, so
   `make_cursor` / `make_token` / `make_progress` reported `PEP_PARSE_EXPECTED`.
2. A missing callee closure, so `ascii_continue` reported `PEP_UNKNOWN_FUNCTION`
   for `ascii_digit`.

Recorded because the first version of this table would have sent A2 chasing two
non-existent emitter gaps.

## BOOT-A2-20261106-39 — LUCY-20261106-006 pickup: grant handoff delivered, vertical boundary measured

- **Branch:** `codex/a2-bounded-emission` @ `935c331`, pushed, remote-equal, clean.
- **#16 posts:** 6698074255 (grant handoff + ACK/counterexample), 6698115244 (vertical boundary).

### Delivered against the mission's item 4

**Both questions A1 was told to ask:**

1. **`sourceGrant` shape** — A1 has NOT posted it; `codex/a1-typed-bound-pipeline` is
   still at `a9e9e2f`. My ACK is therefore against A1's draft
   `docs/NATIVE_SOURCE_GRANT_CONTRACT_DRAFT.md` @a802290, read in full and adopted over
   my own earlier proposal.
2. **Where my native wrapper consumes the grant** — `tests/pep_c23_emitter.pep`:
   `grantEntry` computed at 4616–4626 (true iff `main` declares exactly one
   `SourceBytes` parameter); wrapper branch at 4743; fail-closed `argc < 2` at 4750;
   `fopen(argv[1])` at 4752; whole-file read at 4758–4760; passed to `pep_fn_main` at
   4765.

**Exact seed-oracle limitation** (measured): plain `run` refuses ungranted bytes with
`PEP_RUNTIME_SOURCE_CONTEXT: source_bytes is available only for a host-authorised v2
semanticTarget` at 1:22. A seed oracle for a byte-reading program therefore cannot be
produced from `run`; my probes iterate the same byte values as a literal `Int` list
instead, and label that workaround as the authority boundary.

**Test entry A1's host can invoke:** `python tests/probe_source_grant_entry.py` — exit
0 at HEAD, drives the real session, builds with strict Clang AND GCC, runs over real
files. No host change needed to run it.

### The ONE blocking interface question

**How does the emitter learn the grant is authorised?** My wrapper keys off the source
shape alone; the emitter is a pure function of `(parsed, checked)` and never sees the
host's `semanticTarget`, so it cannot distinguish "the host authorised this" from "the
source merely declares it". That is a real gap against the draft's invariant 3. Options:
(a) host-side refusal before calling the emitter, or (b) an explicit emitter grant
argument. (a) is A1's file; (b) changes the emitter's tool signature. **A2 will
implement its half once A1 chooses.**

Also factual: `session_semantic_target` uses `session_exact_fields
["document";"revision";"entryFunctions"]`, so a `sourceGrant` field is rejected today
with `PEP_SEMANTIC_TARGET_FIELDS`. That is `pep_ocaml.ml`, A1's file.

### Vertical boundary measured (mission objective 1)

| fixture | bytes | nodes | result |
|---|---|---|---|
| `main(SourceBytes) { return byte_at(source, 0) }` | 66 | 8 | valid |
| + real scan loop + `ascii_letter` | 313 | 53 | `PEP_RUNTIME_STEP_LIMIT` |
| + real scan loop + `ascii_continue` closure | 477 | 75 | `PEP_RUNTIME_STEP_LIMIT` |

A real scan loop plus even ONE lexer predicate is over the ceiling. The vertical
therefore needs the **chunked** path, with `main` checked against external signatures.
Not built: conditioned on the grant handshake above.

### Not done, deliberately

- **No scaling probes.** The global-O(n²)/55,930× claim was retracted at `5c25881`; the
  settled model is ~linear in nodes, construct-dependent, global. Not a basis for
  redesign.
- **No next closure feature**, because the mission conditions it on the grant handshake.
- **No checker edits** — read-only throughout, as the dispatch requires.
