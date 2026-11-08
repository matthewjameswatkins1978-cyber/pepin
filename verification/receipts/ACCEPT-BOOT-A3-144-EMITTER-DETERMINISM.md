# ACCEPT BOOT-A3-144 — emitter determinism verified: identical across fresh processes and independent of call order

**Every comparison in receipts A3-135 through A3-143 assumes emission is deterministic and stateless. Nobody had checked. It is:
two independent sessions with fresh seed processes produce byte-identical output for all 21 functions, and a fragment's bytes do
not change when fragments are emitted in reverse or shuffled order.**

Seed blob `f8f476198f`. A2 `e07e278f`. A1 host `07af079d`. Unmodified lanes; scratch deleted after.

## What was measured

**1. Across fresh seed processes.** Emitted header + prototypes + unit *or* every statement fragment for all 21 functions, in
two completely separate sessions, and hashed each function's output:

```
functions compared: 21; differing: 0
DETERMINISM: IDENTICAL across fresh sessions
```

**2. Independent of call order.** `main`'s 31 fragments emitted forward, then reversed, then in a fixed shuffle:

```
forward == reversed : True
forward == shuffled : True
fragments differing by call order: none
fragment 23 repeated 3x: ['REFUSED','REFUSED','REFUSED'] identical: True
```

**3. Repeat calls agree.** Emitting the same fragment three times in one session yields the same result each time.

## Why this matters rather than being ceremony

Fragments are emitted as **independent tool invocations** by a host that chooses which statements to send and in what order. That
design is only sound if a fragment's C depends on nothing but its own inputs. It does not — no ordering effect, no carry-over
between calls, no dependence on prior session history.

This also retroactively validates the comparisons that came before it. A3-135's byte-identical differential, A3-138's assembled
build, and A3-139–143's executed assertions all compare outputs taken at different moments; if emission drifted between them, those
results would have been comparisons against a moving target. They were not.

It is also a property `compiler_a` itself will rely on: a compiler that produced different C on a second run of the same input
would be unusable regardless of whether the C was correct.

## Method

Two `Session()` objects, each spawning a fresh `pep.ps1 session --jsonl` seed process, driving the same `check_program` and the
same `pep-c23-section` / `pep-c23-unit` / `pep-c23-statement-fragment` invocations over the same source (`ca732536`), hashing the
concatenated emitted parts per function. The order test re-emits individual fragments of `main` in three different sequences
within one session and compares per-fragment hashes.

## Limits

- One source, one emitter pin, one driver pin, one seed. Determinism is demonstrated for `compiler_a.pep`, not proven in general.
- Only the *emitted C* is compared. Step counts differed slightly between runs in earlier receipts (e.g. A3-124's 752-step
  measurement was stable, but A3-130 noted small drift), so output determinism does not imply cost determinism.
- `find_brace` and `main` still refuse one statement each, consistently — determinism covers the refusals too, but it says nothing
  about when they will be fixed.
- Same-session reuse of a *different* document was not tested; only repeated emission of the same document.

REF GH #16. Underpins `6726084796` (A3-135) through `6726307224` (A3-143).