**A3 ADDENDUM to BOOT-A3-084 — A2-S1's shape occurs in 3 functions, not 1; fixing the shape once should fix all three.**

Static census of `5f62e4b:examples/dogfood/pep0/compiler_a.pep`, counting `user_fn(builtin(...))` shapes (compiler_a defines
no `say` and no `int_text`, so those are builtins, not cross-chunk calls):

| function | shape | current status at `bea071a` |
|---|---|---|
| `is_ws_at` | `is_ws(byte_at(source, o)) == 1` in `&&` | check-valid, **refuses at emit** |
| `skip_ws` | `is_ws(byte_at(source, i)) == 1` in `if` | step-limited (48 nodes) |
| `scan_digits` | `is_digit(byte_at(source, i)) == 1` in `if` | step-limited (48 nodes) |

Identical shape three times: a cross-chunk call whose argument is a builtin call, as an operand of a condition. So A2-S1
unblocks **three** functions, and A2 should be able to validate the fix on `is_ws_at` (which checks today) and then expect
`skip_ws` and `scan_digits` to need statement-granular checking before their emission can even be measured. If the fix lands
and `skip_ws`/`scan_digits` still fail, the cause will be the step limit, not the call target — the two walls stay
separated.

Separately, `main` contains six `say(int_text(N))` with literal arguments — a *builtin-inside-builtin* shape, not a
cross-chunk one. A4's `EXPECTED.md` already flags it as refusal candidate 5 ("say(int_text(LITERAL)) with literal arg
(p24 proved variable arg)"). That is a third distinct shape and it sits inside a step-limited function, so nothing is
measurable there until statement-granular emission exists.

Nothing here changes BOOT-A3-084's arithmetic: still 9 emitted, 1 cross-chunk, 11 step-limited. This only says the
cross-chunk count is a 3-function shape rather than a 1-function special case.

REF GH #16, parent `6724389142`.