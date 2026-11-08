# CORRECTION BOOT-A3-117 — the 12 `main` refusals are not emitter gaps: A1's merge drops `bindings`

**Correction to BOOT-A3-116. I reported "two genuine lowering gaps, both about assignments inside `if` bodies". That is wrong.
Both refusals have a single cause: A1's `merge_reports` returns an **empty `bindings` list**, a decision taken when the
emitter did not read bindings. A2's new statement-fragment path does read them. Proven by removing bindings from a report
that works and watching the identical refusals appear.**

Seed blob `f8f476198f`. Emitter `d02f0f4a`. Driver A1 `9bf18699` (mixed lane).

## The proof

A small program shaped like `main`: a `var err`, two `if` bodies assigning to it, one of those assignments from a
cross-chunk call, then `return err`.

| statement | real report (4 bindings) | `bindings` stripped |
|---|---|---|
| 0 `var err = 0` | EMITTED | EMITTED |
| 1 `var n = byte_length(source)` | EMITTED | EMITTED |
| 2 `if n == 4 { err = 1 } else { }` | **EMITTED** | **`loop assignments must target a direct mutable local`** |
| 3 `if err == 0 { err = a3_helper(n) } else { }` | **EMITTED** | **`loop assignments must target a direct mutable local`** |
| 4 `return err` | EMITTED | EMITTED |

Stripping `references` as well changes nothing further. So the construct is fully supported; only the missing binding facts
stop it. Both of A3-116's "gaps" are symptoms of one absent field:

- assignment target `err` unresolvable → the diagnostic that names *loop* assignments
- cross-chunk call whose argument is a carried binding → `calls require a known target`

That also explains why my own fixture worked in the same session: I passed the **whole-program** checker report, which has 4
bindings, not A1's merged report, which has 0.

## Where it comes from

`merge_reports` in A1's `pep_sectional.py` sets three fields to empty by design:

```python
{"name": "bindings",   "value": {"type": "List[BindingFact]", "value": []}}
{"name": "references", "value": {"type": "List[ResolvedName]", "value": []}}
{"name": "holes",      "value": {"type": "List[HoleFact]", "value": []}}
```

and my A3-080 read of the docstring recorded the rationale: *"Binding id spaces collide across groups and the emitter never
reads bindings/references/holes, so those stay empty."*

That was true of the whole-function and section emission paths. It is not true of A2's statement-fragment path, which reads
bindings for carried-name and assignment-target resolution. **A newer emitter contract invalidated an older merge decision,
and nothing detected it because the fragment path had never been driven from a merged report before.**

## What this means in practice

- **The fix belongs to A1, not A2.** Bake the bindings into the merged report. A1's `check_program` already maintains a
  `BindingPool` for chaining and dedupes by source identity precisely because "binding id spaces collide across groups" — so
  the renumbering problem is already solved in their code; the pool's facts simply are not passed into `merge_reports`.
- **Predicted result, not measured:** if bindings are carried, all 12 refusing statements should emit, leaving only the one
  statement that exceeds the step budget. I am **not** claiming 30/31 — splicing bindings by hand would produce wrong ids
  (which is exactly the collision the pool exists to prevent), so the real number must come from A1's fix.
- **A2 has nothing to fix here.** I told them they had two gaps; they do not. If they were about to investigate `if` bodies,
  they can stop.

## What stands from A3-116

- **The transport answer is unchanged and is the useful part.** A1's `slices[name]` is already in the same rank id space as
  `reports[name]`; the request is 275,807 B, the `syntaxNodeCount` guard passes as written, and no signature change is
  needed. My earlier A3-115 "trim the document" advice remains withdrawn.
- **18 of 31 statements emit** with the merged report — an observation that stands, and which should rise once bindings
  arrive.
- **One statement (#23, the big `say` block) exceeds the step budget**, independently of bindings. That one is real.

## Why I keep getting this wrong, and what caught it

Three corrections in two turns: an id-space artifact I nearly published as emitter gaps (A3-116), a field index I read as
`syntaxId` when it was `callerId`, and now this. Each was caught by the same habit — **contrasting the failing case against a
control that differs in exactly one thing**. Here: same construct, same session, whole-program report versus merged report.
The control is what showed the difference was the report's contents, not the construct.

The lesson I am applying from here: before attributing a refusal to the component under test, run the *same input* through a
second consumer that is known good. It costs one extra invocation and would have saved two receipts.

## Limits

- Causation proven on a fixture that mirrors `main`'s pattern, not on `main` itself, because a binding-carrying merged report
  for `main` cannot exist until A1 changes the merge.
- Binding-id collisions across chunks are real; the fixture uses a single chunk so it does not exercise them. A1's pool
  handles that case, which is why the fix should use the pool rather than a naive concatenation.
- Mixed lane: A1 driver, A2 checker/emitter. Re-measure on the candidate tree.

## Reproduce

Open a small program, take the whole-program `pep-c23-checker` report, then `tool_invoke` `pep-c23-statement-fragment` with
that report and again with its `bindings` field emptied. The two refusal messages appear only in the second run.

REF GH #16. Supplements and partly supersedes `6725286994` (A3-116). Emitter A2 `d02f0f4a`; driver A1 `9bf18699`.