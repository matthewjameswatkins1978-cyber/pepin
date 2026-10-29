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

Three numbered options close this, in increasing order of machinery:

Option 1 — forbid it at the boundary: the host asserts every
    `sourceParts` entry is NUL-free before calling the native join,
    and routes any violation to `status: "unsupported"` with a
    diagnostic. No new C API; the emitter must guarantee or check
    the precondition.
Option 2 — length-tagged join: `pep_textbuf_join_n(buf, parts, lens,
    count)` (implemented, same contract as `join`) preserves
    embedded NULs. The host transport must then carry lengths
    alongside pointers — a v2 tool-protocol decision that belongs
    to Agent 2's design.
Option 3 — escape at emission: the emitter never emits raw NUL
    bytes into fragments in the first place.

Agent 4 recommends Option 1 for the first gate (smallest state,
fail-closed) and offers Option 2 as implemented fallback. Until one
is chosen, the Python join remains the production path — this is a
documented divergence, not a silent one. Slice-10 evidence
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
`emit_c23_joined` single-`Str` shape, (c) the three gate conditions,
(d) the NUL-fragment decision above (Agent 4 recommends Option 1).
No emitter, checker, or test files were touched from this side.

## Text search primitive (Agent 4, offered, no action required)

`pep_find.h` exposes one pure function for byte-substring search:

```c
int pep_text_find(const char *hay, size_t hn, const char *ndl, size_t nn, size_t *at);
```

Contract: explicit lengths (NULs are ordinary bytes); empty needle
found at 0; needle longer than haystack never found; `*at` holds the
offset or `hn` when absent; `PEP_FIND_OK` / `PEP_FIND_NONE` /
`PEP_FIND_BADARG` (component-local codes, as elsewhere here).
No normalization, no case folding: NFC `caf\u00e9` will not match
its NFD spelling, by design. Offered for any lexer/scanner use
(delimiter and keyword search over raw buffers); the emitter is not
required to adopt it.

## Arena for Agent-2 AST nodes (Agent 4, offered, no action required)

`pep_arena.h` exposes one opaque handle plus four functions:

```c
int pep_arena_init(pep_arena_t **arena, size_t chunk_hint);
void *pep_arena_alloc(pep_arena_t *arena, size_t size, size_t align);
int pep_arena_status(const pep_arena_t *arena);
void pep_arena_free(pep_arena_t **arena);
```

Contract: chunked growth that never moves issued pointers; checked
sizes and power-of-two alignment; allocation failure and overflow
surface as sticky codes (callers must null-check every result);
one whole-arena release, no globals, single-threaded use. Arena
owns storage only — tags, arities, child counts, and every semantic
distinction stay with Pep and the checker, as today.

For illustration only (Agent 2 owns its node layout; nothing here
is required), a recursive node an Agent-2 AST could allocate from
an arena:

```c
typedef struct ast_node ast_node_t;
struct ast_node {
    int32_t tag;              /* checker-defined constructor id */
    int32_t arity;            /* number of children that follow */
    const ast_node_t *child[];/* flexible array of child pointers */
};
```

with fixed-size payload nodes (e.g. Int64 constants) as siblings.
An arena is not permission to skip ownership checks and not a
garbage-collection decision: explicit lifetime, one compilation
unit, one release. Growable *collections* of arena-owned node
references are the stated next step if a native parser needs them.
