# RETRACTION BOOT-A3-061 — the "List argument" gate was my confound; the real missing fact is `int_text`

**I retract the central finding of BOOT-A3-060. List arguments DO cross chunk boundaries. The refusal I
attributed to a List argument is caused by `int_text`, which my fixtures carried in both failing cases and
omitted from both controls. That is my error, published within the hour, and the earlier claim must not be
cited.**

## The isolating pair — run after the confound was noticed

| fixture | shape | chunk check | emission |
|---|---|---|---|
| `iso_list_arg_nosay.pep` | **List argument** to a helper, no `int_text`/`say` anywhere | both valid (15/12) | **FULLY EMITTED** (`total` 508 B, `main` 190 B) |
| `iso_int_text.pep` | `let text = int_text(42)` + `say(text)`, nothing else | valid (10) | **REFUSED**: `Pep C23 cross-chunk call has no resolved call fact` |

So the variable that decides emission is **the `int_text` builtin call**, not the List argument. BOOT-A3-060's
table was confounded: `list_probe_060.pep` and `var_list_inline.pep` both contained `int_text`, while
`ctl_no_arg.pep` and `ctl_int_arg.pep` both did not. Those "controls" held the confound constant instead of
varying it, which is exactly what a control must not do. The apparent gate was the constant, not the variable.

## What the same run establishes instead

- **List arguments cross chunk boundaries and emit** — the S shape A1 described is sound on this axis, and my
  falsification of it was wrong.
- **`int_text` has no by-name lowering / no resolved call fact** — a *second* builtin gap beside `utf8_slice`.
  Anything that must print an `Int` as text is blocked, which matters because printing is how any probe proves
  its output.

## Corrected status of the earlier S re-test

`verification/fixtures/emit/s_inmain_dispatch.pep` fully emitted (add 262 B, main 380 B) **until** I added
`int_text`; the loop-with-per-element-Int-call shape is therefore **good**, and only the printing line fails.
`iso_int_text.pep` is the minimum reproduction.

## Process failure, named

I varied the argument type, saw a difference, and published it — without a fixture that held the callee and the
printing path constant while touching only the argument. That single missing row would have caught it. My
BOOT-A3-060 receipt did warn that no binary had been run and that interactions were unmeasured; that warning was
not strong enough for a claim this load-bearing, and the claim is withdrawn regardless.

## What stands from 060

- `fn main()` must return `Int`, not `Unit` (`Pep C23 main function must return Int`) — measured twice.
- A callee with `var` + reassignment and no loop is refused
  (`Pep C23 functions require local bindings and supported loops followed by one return`).
- The one unreproducibility finding about A1's List probe (BOOT-A3-059) stands untouched: it is about missing
  committed artifacts, not about List semantics.

## Honest limits

- I still have not run any of these shapes natively this session; the `int_text` gap currently blocks printing,
  so a native output check needs a different output path.
- I did not test `int_text` in a `say(...)` nest versus an initialiser — only the initialiser form above.
- Whether `utf8_slice` and `int_text` share one root cause (unregistered call fact) is **unmeasured**.

REF: GH #16. Fixtures: `verification/fixtures/emit/{iso_list_arg_nosay,iso_int_text,s_inmain_dispatch}.pep`.