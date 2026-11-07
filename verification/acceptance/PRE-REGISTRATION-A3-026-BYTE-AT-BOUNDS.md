# PRE-REGISTRATION A3-026: does the granted SourceBytes path bounds-check `byte_at`?

**Seat:** A3. Campaign `LUCY-20261107-007`, lane item 3 (attack the next staged-checking /
native soundness gap independently). **Written and committed before any measurement of this
question.**

## Why this is the next gap

A4's application computes `byte_at(source, o - 1)` behind a guard, so it is *correct* today only
because the program happens to guard `o != 0`. Nothing in the language, the checker or the
emitted C appears to guarantee that:

- A4's guard is correct by construction; other programs will not be.
- A future "next useful Pep-native capability" (per A4's lane item 2: line/source statistics,
  lexical categories) will do offset arithmetic.
- If an out-of-range read is silently served from memory outside the granted buffer, the trust
  boundary claimed for the grant is weaker than the receipts imply.

The pinned epilogue (as observed in BOOT-A3-024/025) mallocs `length + 1` bytes and never
initialises the final byte. That strongly suggests an unchecked `data[i]`.

## Cases

Main is the only function; `X` is the offset expression.

| # | Program body | In-bounds? | **Predicted** |
|---|---|---|---|
| B0 | `return byte_at(source, 0)` on a non-empty file | yes | emits, runs, returns the true first byte |
| B1 | `return byte_at(source, 0 - 1)` | no, offset `-1` | **silent out-of-range read** — not a trap. Under two's-complement promotion `-1` becomes the largest `size_t`, so this reads far before the buffer. I predict it does not trap. |
| B2 | `return byte_at(source, byte_length(source))` | no, one past end | **silent read of the uninitialised byte** in the `length + 1` allocation; returns an arbitrary Int, no trap |
| B3 | `return byte_at(source, byte_length(source) + 1048576)` | no, far past end | **silent read far past the allocation** (heap over-read); may return garbage or crash |
| B4 | `return byte_at(source, 0)` on an **empty** file | no, empty grant | reads the uninitialised spare byte; predicted no trap |

Static refusal (checker or emitter rejecting any of B1–B4 with a diagnostic) would **falsify** the
predictions, and that would be a better outcome than what I expect.

## What counts as which verdict

- **SOUND** — an out-of-range `byte_at` traps with a non-zero exit and a `PEP_RUNTIME_*`
  diagnostic on stderr, and prints no value. Static refusal also counts as SOUND.
- **UNSOUND** — a value is printed for an out-of-range offset, or the process dies without a
  `PEP_RUNTIME_*` diagnostic.
- An emitted binary that refuses to build at all is recorded honestly as **NOT TESTED** with the
  first refusal, never as a pass.

## Evidence labels

Predictions above are mine. The measurement is native Clang (`-std=c23`) and GCC (`-std=c2x`),
strict, over a real granted file whose bytes I hash. The expected in-bounds value (B0) is verified
against an independent Python read of the same file. `byte_at` is defined in the language surface;
its out-of-range behaviour is **undefined by the spec**, so the finding is a *soundness/safety*
observation about today's implementation, not a violation of a written clause — and I will say so
in exactly those words rather than overstating it.

## Scope guard

A3 owns only `verification/**`. No edits to A4's app, A1's checker/host, A2's emitter/runtime,
frozen gates, budgets, `CURRENT`, manifest, master or release labels. No cap change. A3 does not
propose the fix; it reports the measurement so the owning lane can decide.
