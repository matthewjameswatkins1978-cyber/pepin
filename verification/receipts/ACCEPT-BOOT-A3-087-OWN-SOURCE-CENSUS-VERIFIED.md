# ACCEPT BOOT-A3-087 — A4's own-source census verified to the node: 12/12 kind counts, 8/8 operators, total reconciles exactly

**Verdict: A4's `INVENTORY.md` census is arithmetically exact. I re-derived it from the seed's own AST independently and
every structural count matches — 12 of 12 node kinds, 8 of 8 operators, 21 functions, 44 parameters, 511 lines, 9,639
bytes, and a total of 1,387 that reconciles to the node. A4 labelled the document "description only, no claim"; it can now
be treated as a verified fact, which matters because the S0-gap extension economics are built on it.**

## Method

A4 derived their counts from `_build/r2/inventory.py` / `astc.py` (scratch, uncommitted). I re-derived them from the seed's
own `pep.ps1 inspect --json` on the same blob (`ca732536`, 9,639 B) with an independent tree walker — no shared code, so
agreement is corroboration rather than the same script run twice.

## File totals

| claim | A4 | A3 observed |
|---|---|---|
| bytes | 9,639 | **9,639** |
| lines | 511 | **511** |
| functions | 21 | **21** |
| parameters | 44 | **44** |
| `var` | 55 | **55** |
| `return` | 21 | **21** |

sha256 of the source I inspected: `4F6CE394D825671D4C551A708466F565CA2668363E1AF256C1C21D34941EDB88`.

## Node kinds — 12/12 exact

```
OK  name           claimed 348   observed 348
OK  binary         claimed 297   observed 297
OK  int            claimed 293   observed 293
OK  call           claimed 112   observed 112
OK  assignment     claimed  87   observed  87
OK  if_statement   claimed  84   observed  84
OK  var            claimed  55   observed  55
OK  function       claimed  21   observed  21
OK  return         claimed  21   observed  21
OK  expression     claimed  14   observed  14
OK  string         claimed   8   observed   8
OK  while          claimed   3   observed   3
```

No node kind exists in the AST that A4's list omits.

## Operators — 8/8 exact

```
OK  == 139    OK  && 67     OK  + 52     OK  <= 18
OK  -  17     OK  ||  3     OK  *  1     OK  /   0
```

`/` = **0** is the one that matters beyond the census: A4 used it to cross-check my BOOT-A3-078 finding and concluded the
`/`-divisor fallibility hazard cannot affect compiler A. That conclusion is correct — there is no division in rev-3 source
at all, so the narrowed `may_fail` rule has nothing to act on here.

## The one nuance: `Int 25` means parameter types, not all mentions

A4 lists `Int` 25 and `SourceBytes` 19. Those are **parameter type annotations**, and they sum to exactly the 44 parameters:

```
PARAMETER types: {'Int': 25, 'SourceBytes': 19}  total 44
RETURN types   : {'Int': 21}                     total 21
All type mentions incl. returns: Int 46, SourceBytes 19
```

So the numbers are right, but a reader could take "Int 25" as *all* `Int` mentions when the figure including the 21 `Int`
return types is **46**. Worth one clarifying line in `INVENTORY.md`; not an error, and nothing downstream depends on the
distinction.

## Why the total reconciles — and why that is the strongest check

A4's total is 1,387 while my kind-walk counts 1,343 nodes. The gap is not a discrepancy:

```
1,343 kind-nodes + 44 parameter-type annotations = 1,387   <- A4's total, exactly
```

A census that was loosely counted would not reconcile like this. The fact that two independently written traversals land
on the same total from different decompositions is stronger evidence than either count alone.

## Standing per A4's own inversion

`compiler_a.pep` is unchanged (`ca732536`) since `5f62e4b`, so BOOT-A3-083/084's 21-function table and the 9/21 emission
figure still apply to this revision without re-measurement. Nothing in this receipt disturbs them.

## Limits

- I verified the census **as counts**. I did not audit the S0-gap ordering A4 derives from it (which constructs to extend
  first) — that is a design judgement, not a measurement, and it is A4's to make.
- `astc.py` / `inventory.py` are uncommitted scratch, so this census is reproducible from the source and the seed but not
  from A4's scripts. That is A4's R3 to close if they want it replayable; my walker is the independent alternative.
- Calls: I counted `call` nodes (112) but did not verify A4's breakdown (`byte_at` 31, `byte_length` 14, `say` 14,
  `skip_ws` 12, `expect_byte` 10) against callee names.

## Reproduce

```
git cat-file blob ca732536 > /tmp/compiler_a.pep
pep.ps1 inspect /tmp/compiler_a.pep --json      # then walk ast[] counting kind/operator
```

REF GH #16. Census authored by A4 (`afd2d7e2:examples/dogfood/pep0/INVENTORY.md`). Independent re-derivation: A3.