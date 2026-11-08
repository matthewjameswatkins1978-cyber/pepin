# ACCEPT BOOT-A3-109 — differential extended to 9 cases; emitter proven to short-circuit `&&`

**Verdict: the seed-vs-emitted differential now covers nine semantic classes and all nine agree. The newest case is the
sharpest: it proves the emitter lowers `&&` to a genuinely short-circuiting construct, because the right operand would abort
with `PEP_RUNTIME_DIVISION_BY_ZERO` if it were evaluated.**

## Result

```
PASS cross-chunk arithmetic                both print '43'
PASS negative integer                      both print '-3'
PASS truncating division                   both print '0'
PASS string concat                         both print 'abcd'
PASS comparison through a helper           both print '1\n0'
PASS top-level conditional                 both print 'T'
PASS short-circuit conjunction             both print 'AND'
PASS builtin composition                   both print 'n=7'
PASS short-circuit avoids the right operand both print 'SAFE'

9 cases, 0 disagreeing — SEED vs EMITTED: AGREE
```

Every case is evaluated twice by independent implementations: the seed's own evaluator at top level, and the emitted C
compiled and run under **both clang and gcc**. Agreement is on the value, not the code.

## The short-circuit case, and why it is the one worth having

```pep
let z = 0
if 1 <= 0 && 1 / z == 1 { say("BAD") } else { say("SAFE") }
```

The left operand is false, so a correct `&&` never evaluates `1 / z`. Since `z` is 0, evaluating it raises
`PEP_RUNTIME_DIVISION_BY_ZERO` — the process aborts and prints nothing. Both sides print **`SAFE`**, so:

- the emitter did **not** expand `&&` into something that evaluates both operands (a bitwise `&`, or a helper taking both
  values as arguments, would have aborted);
- and it did not reorder the operands.

That is a semantic property of the emitted C that no structural check would catch, and it is now pinned. Worth noting it
also exercises the interaction with A2's arithmetic `may_fail` rule: `1 / z` has a variable divisor so the rule treats it as
infallible, which is what allows the conjunction to emit at all — if a future narrowing of that rule refuses this shape, this
case will fail loudly rather than silently changing meaning.

## Probe improvements made while extending

- **Seed exit codes are now checked.** Previously a seed *error* produced empty stdout and would have been reported as a
  semantic disagreement against the emitted value. It now reports `SEED ERROR exit=N` distinctly, so a broken oracle cannot
  masquerade as a finding about the emitter.
- Cases that need placement help say so in their own right-hand note rather than in a comment elsewhere: the emitted side
  must hoist cross-chunk calls (builtin-of-call is not lowered, BOOT-A3-107) and bind conjunctions before testing them.

## Coverage vs. what is still out of reach

Now covered: integer arithmetic including a negative result, truncating division, string concatenation, comparison through a
helper, a conditional, `&&` including short-circuit, and builtin composition.

Still out of the differential's reach, and why:

- **Anything needing `SourceBytes`** — no working input grant (A3-073/074), so `byte_at`/`byte_length`/`utf8_slice` cannot
  be evaluated from the seed side at all.
- **Statement and scope semantics** — the two sides differ in placement by necessity, so ordering, mutation lifetime and
  error-sequence behaviour are invisible to this method.
- **The builtin-of-call position** — must be hoisted on the emitted side until A2 closes it.

## Limits

- Nine expressions is a regression net, not coverage. Each is small by construction.
- Both roots point at one lane (`wt-a3-dbea`) in this run; the probe accepts `--seed`/`--gate` separately so a
  cross-lane run is possible and would be a stronger test.
- One emitter pin (`ad7f1c08`), one source revision, one seed.

## Reproduce

```
PEPIN_SEED_ROOT=<built seed> PEPIN_GATE_ROOT=<emitter worktree> \
  python verification/probes/seed_differential_106.py
```

Also runs as the seventh gate in `verification/run_gates.py`.

REF GH #16. Reserve R3, extended. Emitter A2, seed (shared), differential A3.