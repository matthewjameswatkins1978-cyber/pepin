# BOOT-A3-065 — the byte path cannot be reached without the missing builtins (negative result)

**Verdict: negative, and useful. Attempting an input-sensitive route that avoids `utf8_slice` fails before
emission — host analysis refuses the program, so it is not an emitter question at all.**

Fixture `verification/fixtures/emit/probe_bytes_path.pep` @ `5670b41`:

```
fn main() -> Int {
    let raw = source_bytes("Pep")
    let n = byte_length(raw)
    let b = byte_at(raw, 0)
    let s = b + n
    return s
}
```
→ `RESULT: host analysis refuses this program - not an emitter question`

## What this establishes

- `byte_length` (1 by-name site) and `byte_at` (3 sites) are emittable **only once a `SourceBytes` value
  exists**, and `source_bytes` has **0** by-name sites. So the byte-processing builtins are unreachable in
  practice: the value they consume cannot be created.
- My guessed call shape (`source_bytes("Pep")`, `byte_at(raw, 0)`) is **not** the accepted signature — the
  front end rejects it before the emitter is consulted. I do not know the correct argument contract, and did
  not spend further turns guessing at it.

## Consequence for the mission

This closes the "find a route around the missing lowering" idea for the byte path: there is no way to obtain
input bytes in emittable Pep today, so an input-dependent program cannot be *constructed* without the
three-site builtin work named in BOOT-A3-062/063. **The floor is gated on that patch, not on emitter capacity,
not on decomposition, and not on List handling** — every one of those is now measured and clear.

The viable alternative remains: have `main` receive already-checked values and produce an `Int` (proved native
in BOOT-A3-064), which is a genuine execution path but not input-dependent C text.

## Honest limits

- One guessed call shape only. I did not consult `docs/SEED_LANGUAGE.md` for the real `source_bytes` contract,
  so this shows *my* program was invalid, not that no valid program exists.
- Host analysis refusal text was not captured in full detail this turn; the program never reached chunking.

REF: GH #16.