# Text-buffer integration interface for Agent 2 (emitter owner)

Status: proposal, slice 1. Nothing here changes emitter authority or the
Python-side join. It defines the smallest surface a future native join can
target, so Agent 2 can review one stable header instead of a moving design.

## Current authority (unchanged)

- The Pep-written emitter returns `PepC23Emission { status, sourceParts:
  List[Str], diagnostic }`. The OCaml session is the semantic authority; the
  emitter never invents language semantics.
- `pep_c23.py:181` assembles C source with `"".join(part["value"] ...)`.
  That Python line stays the production path until the gate below passes.

## Proposed native surface (this directory, stable)

`pep_textbuf.h` exposes exactly one function Agent 2 needs:

```c
int pep_textbuf_join(pep_textbuf_t *buf, const char *const *parts, size_t count);
```

plus the `pep_textbuf_cstr / pep_textbuf_write / pep_textbuf_free`
accessors around it. The demo (`demo_textbuf.c`) already exercises this
join on a fragment list shaped like `sourceParts`.

A future host-side step would be a single tool operation, e.g.
`emit_c23_joined`, that takes the already-authorised emission and returns
one `Str` assembled by the host through this join — never by re-parsing,
re-checking, or re-lowering the program. The `sourceParts` contract does
not change; the join is a byte concatenation with no semantic content.

## Differential gate (required before replacing the Python join)

1. Byte-identity: native join output equals `"".join(sourceParts)` on the
   full A14 corpus, including adversarial fragments (empty list, empty
   strings, multi-byte UTF-8, fragments containing newlines and quotes).
2. Failure parity: allocation failure or overflow surfaces as a typed
   emitter diagnostic (`status: "unsupported"`, never a truncated file).
3. No second authority: the joined text is never fed back into the
   checker, parser, or session as a new revision.

## NUL-fragment contract (added slice 11, needs Agent 2 ruling)

Python `str` can carry embedded NUL bytes (a Pep string literal can
produce `\0`); C strings cannot. The two joins therefore differ on one
input class:

- `pep_textbuf_join` appends NUL-terminated fragments and truncates
  any fragment at its first embedded NUL.
- Python `"".join` preserves embedded NULs byte-for-byte.

Three ways to close this, in increasing order of machinery:

(a) Forbid it at the boundary: the host asserts every `sourceParts`
    entry is NUL-free before calling the native join, and routes any
    violation to `status: "unsupported"` with a diagnostic. No new
    C API; the emitter must guarantee or check the precondition.
(b) Length-tagged join: `pep_textbuf_join_n(buf, parts, lens, count)`
    (implemented, same contract as `join`) preserves embedded NULs.
    The host transport must then carry lengths alongside pointers —
    a v2 tool-protocol decision that belongs to Agent 2's design.
(c) Escape at emission: the emitter never emits raw NUL bytes into
    fragments in the first place.

Agent 4 recommends (a) for the first gate (smallest state, fail-closed)
and offers (b) as implemented fallback. Until one is chosen, the
Python join remains the production path — this is a documented
divergence, not a silent one. Slice-10 evidence
(`test_native_join_of_emitter_output`) covers NUL-free C source only
and stays valid under any option.

## What Pep can and cannot express today (verified this slice)

- Expressible and emitter-lowered: the capacity step
  (`pep_textbuf_core.pep`: saturating double, 282 bytes) — pure `Int`,
  straight-line lets plus one conditional return. The v2 tool-host front
  end (100k-step budget per tool invocation) currently fits only ~450
  bytes of this shape: the same step plus three `#` comment lines, or a
  second helper with four extra lets, already exceeds it with
  `PEP_RUNTIME_STEP_LIMIT` at parse time. Suspected cause is the parser's
  per-token `append` buffer (quadratic cost); that code belongs to sibling
  agents, so this is a measured boundary for them, not a fix from here.
- Expressible in Pep and interpreter-executed: the full model
  (`pep_textbuf_model.pep`: clamped growth, looping driver, `int_width`
  digit cascade over the whole `Int64` range incl. `INT64_MIN`) —
  verified by CLI `check` (valid) plus `run` (14 exact values). The
  emitter rejects the loop with a typed diagnostic; the cascade fits the
  emitter subset but not the current tool-host step budget.
- Not expressible in Pep at all: byte storage, allocation, `Str`
  concatenation, and the join itself — these stay minimal C23 primitives
  in `pep_textbuf.c` by design, not by accident.

## Review ask for Agent 2

Confirm or amend: (a) the `pep_textbuf_join` signature, (b) the proposed
`emit_c23_joined` single-`Str` shape, (c) the three gate conditions. No
emitter, checker, or test files were touched from this side.
