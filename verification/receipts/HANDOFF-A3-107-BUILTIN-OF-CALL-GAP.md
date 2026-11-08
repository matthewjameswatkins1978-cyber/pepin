**A3 HANDOFF — one uncovered cross-chunk position, with a minimal reproducer. Not a regression, and not blocking compiler A today.**

Your A2-S1 is verified good (independent receipt `6724813393`). While using the seed as a semantic oracle (A3-105/106) I hit
one position your fix does not cover. Reporting it because it is cheap, additive, and will bite M-2/M-3.

## Minimal reproducer

```pep
fn a3_inc(n: Int) -> Int {
  return n + 1
}

fn main() -> Int {
  say(int_text(a3_inc(41)))
  return 0
}
```

→ `unit main: Pep C23 calls require a known target`

## The asymmetry, isolated

| shape | example | at `7e820a7f` |
|---|---|---|
| **user call of builtin** | `is_ws(byte_at(source, o))` in a condition | **works** (A2-S1) |
| **builtin of user call** | `say(int_text(a3_inc(41)))` | **refuses** |
| same expression hoisted | `let v = a3_inc(41)` then `say(int_text(v))` | **works**, prints `42` |

So builtin→user is lowered and user→builtin is not. A control that differs only in placement:

- `x_builtin_of_call.pep` — `say(int_text(a3_inc(41)))` → REFUSED
- `x_call_then_builtin.pep` — `let v = a3_double(21) + 1` then `say(int_text(v))` → EMITTED, prints `43`

Fixtures are committed under `verification/fixtures/emit/`.

## Two things that should reassure you

1. **It is pre-existing, not yours.** The identical refusal occurs at `1885566` (`bea071a`'s parent lineage) with the same
   message, so A2-S1 neither introduced it nor made it worse. Nothing to unwind.
2. **It does not block compiler A.** I grepped `compiler_a.pep` for every builtin followed by a user-call callee
   (`int_text`/`say`/`str_concat`/`utf8_slice`/`byte_at`/`byte_length` applied to `is_*`/`expect_*`/`skip_*`/`scan_*`/
   `parse_*`/`find_*`/`check_*`): **zero matches**. `main`'s six `say(int_text(N))` take integer literals, which is what
   `EXPECTED.md` already pins as candidate 5. So 10/21 and the A2-S2 path are unaffected.

## Why it still matters

`say(int_text(<computed Int>))` is the single most natural way to print a number in this language, and M-2 (compiler A
reading its own source) and M-3 will both reach for it. Right now every such call site must be hoisted into a `let` by hand,
which is exactly the kind of accidental constraint that becomes a false limitation later.

**Workaround that works today**, for anything you need meanwhile: bind first, then pass the binding.

## Not a request to re-prioritise

A2-S2 and the fragment contract matter more; this does not change the 21-function picture. It is here so it is recorded with a
reproducer rather than rediscovered under time pressure. Your call on sequencing.

REF GH #16. Parent receipts: `6724813393` (S1 verified), `6724935226` (A3-105, where this surfaced).