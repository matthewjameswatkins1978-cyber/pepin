# ACCEPT BOOT-A3-120 — the bindings fix WORKS when deduped by the pool's identity: main goes 18 → 28 of 31, measured

**I tested my own A3-119 proposal in a throwaway copy of A1's module. It works, and it needed one correction I had wrong: the
dedupe key must be `BindingPool._KEY_FIELDS`, not `(name, id)`. Measured result: `main` emits **28 of 31** statements, worst
fragment **57,326 steps** (under budget), with three statements left and each one now separately attributable.**

Seed blob `f8f476198f`. Emitter `651d9124` (guard restored by A2 per A3-118). Driver A1 `9bf18699`.

## Measured, not predicted

| stage | emitted | worst fragment |
|---|---|---|
| merged report as A1 produces it today (no bindings) | 18 | 36,770 |
| **+ bindings carried, deduped by `(name, syntaxId)`** | 18 | — (`assignment target is ambiguous` × 10) |
| **+ bindings carried, deduped by pool identity** | **28** | **57,326** |

The middle row is the important one: my first attempt kept **271 binding facts for 13 variable names** — `err` alone arrived
with **31 different syntaxIds** — and A2's fallback correctly refused with `Pep C23 assignment target is ambiguous in the
carried bindings`. Deduping on the pool's own source-anchored key
(`name, ownerFunctionId, scopeId, visibleFrom`) collapses 271 → **13**, one per variable, and the refusals become emissions.

So the dedupe is not incidental: it is the difference between the fix working and the fix producing a new refusal. A1's
`BindingPool` already implements exactly this key, which is why the proposal should use the pool rather than re-derive
dedupe logic.

## The exact patch that measured 28/31

Applied to a copy of `9bf18699:pep_sectional.py`, two edits plus a call-site change:

```python
# 1. signature
def merge_reports(sliced_progress, groups, full_sorted, entry_name, all_fn_facts, bindings=()):

# 2. report field
{"name": "bindings",
 "value": {"type": "List[BindingFact]", "value": [copy.deepcopy(b) for b in bindings]}},

# 3. call site — translate per group, then dedupe by the pool's identity key
rank = {str(doc): str(i) for i, doc in enumerate(full_sorted)}
carried, seen = [], set()
for cids, rep in parts:
    ordered = sorted(int(c) for c in cids)
    g2s = {str(g): rank[str(doc)] for g, doc in enumerate(ordered)}
    for b in rep["bindings"]["value"]:
        b2 = copy.deepcopy(b)
        key = str(int(_fval(b2, "syntaxId")))
        if key not in g2s:
            raise ValueError("sectional merge: binding outside slice span")
        _fset(b2, "syntaxId", g2s[key])
        identity = tuple(str(_fval(b2, f)) for f in contract.BindingPool._KEY_FIELDS)
        if identity in seen: continue
        seen.add(identity); carried.append(b2)
reports[name] = merge_reports(sl, parts, full_sorted, name, all_fn_facts, bindings=carried)
```

`21/21 chain CHECK` still passes with this in place, and `syntaxNodeCount` still reads 222 against 222 sliced nodes, so A2's
restored guard is satisfied.

## The last three statements, each separately attributable

| stmt | source | outcome |
|---|---|---|
| 17 | `if err == 0 { e = scan_digits(source, ds) } else { }` | `Pep C23 calls require a known target` |
| 20 | `if err == 0 { v = parse_value(source, ds, e) } else { }` | `Pep C23 calls require a known target` |
| 23 | `if err == 0 { say("int main") say(int_text(40)) … }` | `PEP_RUNTIME_STEP_LIMIT` |

Statements 17 and 20 are one shape: **a cross-chunk call as the assignment RHS inside an `if` body**, with carried-binding
arguments. That is the third call position, and with bindings present the diagnostic is now unambiguous — this one is
genuinely A2's. Statement 23 is the six-`say` block, which needs sub-statement splitting; everything else in `main` then
emits.

So the remaining path to a fully fragmented `main` is: **A1 carries bindings (+10 statements), A2 lowers
call-as-assignment-RHS-in-if (+2), and #23 is split further (+1).**

## Correction to my A3-119 prediction

I predicted "18 → 30 of 31". Measured: **28**, because I had assumed the 12 binding refusals were a single population. Ten
were; two (17, 20) are a separate emitter gap that was masked by the binding failures. The prediction was directionally
right and specifically wrong, which is the useful kind of wrong — it means the two gaps are now separated rather than
conflated.

## Method and hygiene

- The patched module lived at `_a3_scratch_sectional.py` in my disposable A2 worktree and has been **deleted**. Nothing was
  applied to A1's lane and nothing was pushed to their branch; the patch above is text for A1 to own.
- Mixed lane throughout: A1 driver, A2 checker and emitter, my scratch copy of A1's merge.
- Re-measure on the candidate tree once the real change lands; the numbers here are from a throwaway copy.

## Limits

- `BindingPool._KEY_FIELDS` is a private attribute; reading it is right for a proposal but A1 may prefer to expose the key
  properly.
- Dedupe keeps the *first* fact seen for an identity. The pool also refuses conflicting semantics for a seen identity; my
  scratch version does not, so A1's implementation should keep that refusal.
- One source, one emitter pin, one seed. Statement 23's budget overrun is unaffected by any of this.

REF GH #16. Supersedes the prediction in `6725358061` (A3-119). Emitter A2 `651d9124`; driver A1 `9bf18699`.