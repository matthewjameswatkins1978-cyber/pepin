# FINDING BOOT-A3-121 — A1's merged report carries `main` twice, in two different id spaces

**A1's `merge_reports` emits a `functions` list containing **23 facts for 21 real functions**, and `main` appears **twice**
with ids from different spaces: `semanticId=100000, syntaxId=0` (chunk-local) alongside `semanticId=9020,
syntaxId=1000000020` (document space). This is the identity channel I probed in A3-080 showing up as a concrete defect rather
than a latent risk.**

Seed blob `f8f476198f`. Driver A1 `9bf18699`. Emitter `651d9124`.

## The measurement

```
merged functions: 23
names: check_tail, expect_byte, find_brace, find_ds, find_fn, find_parens, is_bool4, is_digit,
       is_fn2, is_int3, is_main4, is_ret3, is_str3, is_unit4, is_urn3, is_ws, is_ws_at,
       main, main, parse_value, scan_digits, semantic_snapshot, skip_ws

DUPLICATE 'main' x2
  main fact: semanticId=100000  syntaxId=0            arity=1 returnType=Int
  main fact: semanticId=9020    syntaxId=1000000020   arity=1 returnType=Int
```

21 compiler functions + `semantic_snapshot` = 22 expected; the 23rd is the duplicate.

## Why it happens

`merge_reports` deliberately keeps the **entry** fact from the group reports — A1's own comment says *"the merged entry keeps
the group copy (checker id-space, matching the groups' own call facts)"* — and then appends `all_fn_facts`, which comes from
the signature tool and carries **document-space** ids. The two copies are deduped by `(name, semanticId)`, and those
semanticIds differ (`100000` vs `9020`), so both survive.

So the `functions` list is **mixed-space**: the entry in chunk-local numbering, every other function in document numbering.
Every other merged fact (calls, expressionTypes, and after A3-120 bindings) is in **rank** space. That is three id spaces in
one report.

## What I have not established — stated plainly

**I do not know whether this causes the two remaining `main` refusals.** Statements 17 and 20 still refuse with
`Pep C23 calls require a known target`, but the merged `calls` facts resolve cleanly:

```
syntaxId=105 calleeId=9013 -> scan_digits
syntaxId=127 calleeId=9014 -> parse_value
```

Both callees are present in `functions` and in document space, and no call targets `main`, so the duplicate may be inert for
call resolution. I am reporting the defect on its own evidence, not as an explanation for those two statements.

## The reproducer that did *not* reproduce

I built `verification/fixtures/emit/w_call_assign_in_if.pep` — a cross-chunk call as the RHS of an assignment inside an `if`
body, which is the shape of statements 17 and 20. **Every fragment of it emits**, and the whole function emits:

```
[0,1) EMITTED   var e = 0
[1,1) EMITTED   let n = byte_length(source)
[2,1) EMITTED   if n == 4 { e = a3_take(n) } else { }
[3,1) EMITTED   return e
```

So the construct is supported and statements 17/20 are **`main`-specific**, cause not yet identified. The differences I have
not ruled out: multi-argument calls whose arguments are carried bindings; callees that are themselves step-limited
(`scan_digits` 48 nodes, `parse_value` 34); and the mixed-space `functions` list above.

## Recommended direction for A1

Pick **one** id space for `functions` and dedupe on it:

- drop the group's entry fact and rely on `all_fn_facts`, which already contains `main` in document space; or
- translate the entry fact into the same space as the rest before the `(name, semanticId)` dedupe.

The first is smaller and leaves `functions` homogeneous. It does mean the merged entry no longer matches the group's call
facts by id — but the calls are already in rank space and their `calleeId`s are document-space semanticIds (9013–9019), so
they resolve through `all_fn_facts` anyway, not through the entry copy. That is worth confirming before changing it, which is
why this is a finding and not a patch.

## Also worth noting

`main`'s `syntaxId` in the sigs-derived fact is `1000000020`, and the checker's function semanticId base is `100000` — the
same constant appearing in two roles. Any dedupe scheme that compares ids across spaces will keep tripping on it.

## Limits

- One source, one driver pin, one seed. The duplicate is structural, not data-dependent, so I expect it on any source with an
  entry function, but I measured only `compiler_a.pep`.
- I did not test whether removing the duplicate changes the 28/31 figure — that requires editing A1's merge, which is theirs.
- Mixed lane as before.

## Reproduce

`check_program` on `compiler_a.pep`, then count `functions` in `reports["main"]` and look for repeated names.

REF GH #16. Parent: `6725424101` (A3-120, where the 28/31 measurement surfaced this). Driver A1 `9bf18699`.