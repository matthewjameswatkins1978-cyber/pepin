# FINDING BOOT-A3-137 — the whole compiler needs fragmenting, not just `main`; and all 8 remaining failures are in the two largest functions

**I tried to assemble a full compiler A from fragments and learned the remaining work is larger and better-shaped than
"statement 23". Ten functions emit as whole units. Ten more emit *every one of their fragments* despite failing as units. Only
two functions have fragment gaps — `main` (30/31) and `find_brace` (17/24) — and all eight failing statements sit in those two
functions, including statements of only 13–33 nodes.**

Seed blob `f8f476198f`. A2 `e07e278f`. A1 host `07af079d`. Unmodified lanes.

## The assembly attempt, and what it proved

Header + prototypes + 10 function units + `main`'s 30 fragments + epilogue:

```
clang: build FAIL — lld-link: error: undefined symbol: pep_fn_find_fn
gcc:   build FAIL — ld: undefined symbols pep_fn_find_fn, pep_fn_find_parens, …
```

**Compilation succeeded** — one warning about an unused variable, no syntax or ordering errors, no duplicate declarations, and
the fragment parameter name (`pep_arg_1`) matched the wrapper I built. The failures are **link** errors from the ten functions
whose whole-unit emission is step-limited.

So the fragment contract composes at scale. What is missing is not assembly mechanics but **coverage**: A1's prologue/epilogue
work will need to cover eleven functions, not one.

## Per-function coverage

| outcome | functions |
|---|---|
| whole-unit emit | `is_ws`, `is_digit`, `is_ws_at`, `is_fn2`, `is_int3`, `is_ret3`, `is_urn3`, `is_str3`, `expect_byte`, `parse_value` (10) |
| unit step-limited, **all fragments emit** | `is_main4` 3/3, `is_bool4` 3/3, `is_unit4` 3/3, `skip_ws` 8/8, `scan_digits` 8/8, `find_fn` 14/14, `find_parens` 11/11, `find_ds` 16/16, `check_tail` 9/9 (9) |
| unit step-limited, **fragments have gaps** | `find_brace` **17/24**, `main` **30/31** (2) |

Worst emitted fragment per function stays under 57k in every case — comfortable.

That reframes M-1: **fragmenting is the right strategy for 11 of 21 functions, not just `main`**, and nine of those eleven are
already fully fragmentable today with no further emitter work. Only two functions remain blocked.

## The eight failures, and the number that matters

`find_brace` (288 nodes) loses seven statements, all three-conjunct `if`s:

```
[11] 16 nodes  if e0 == 0 && err == 1 && is_str3(source, o) …
[12] 16 nodes  if e0 == 0 && err == 1 && is_bool4(source, o) …
[13] 16 nodes  if e0 == 0 && err == 1 && is_unit4(source, o) …
[14] 33 nodes  if e0 == 0 && err == 5 && is_str3(source, o) …
[15] 33 nodes  if e0 == 0 && err == 5 && is_bool4(source, o) …
[16] 33 nodes  if e0 == 0 && err == 5 && is_unit4(source, o) …
[19] 13 nodes  if err == 0 && expect_byte(source, o, 123) == 123 …
```

`main` (222 nodes) loses `[23]` at 37 nodes.

**A 13-node statement exceeding a 100,000-step budget** is the clearest possible evidence that statement size is not the driver
— `find_brace` is 288 nodes, and the per-node scan is paid once per child lookup regardless of how small the statement is. This
is the same `lookups × function nodes` law from A3-126, now confirmed across two functions and eight statements.

**One consequence worth stating precisely:** a per-statement node threshold will never fix these. The statement is already tiny.
Only removing the `× function nodes` term helps, i.e. the `parentId` index.

## What this changes for A1's next slice

A1 described prologue+epilogue assembly for `main`. Measured, that produces a binary that **links but is incomplete** — ten
functions undefined. The assembly contract needs to cover all eleven fragmented functions, and the nine that already fragment
fully are available now:

- **available today:** fragment-assemble 9 functions + 10 whole units = 19 of 21 compilable
- **blocked on the index:** `find_brace` (7 statements) and `main` (1 statement)

That is a much more useful target than "wait for #23".

## Limits

- Mixed lanes: A1 host `07af079d` driving A2 emitter `e07e278f`, not a merged tree.
- My wrapper named the parameter `pep_arg_1` to match the fragments; A1's assembly may choose differently, and I did not test a
  prologue that declares locals separately from the fragments (the fragments declare their own).
- The clang link used `lld-link`; the gcc link used `ld`. Both failed on the same ten symbols, so the link diagnosis is not
  toolchain-specific.
- Whole-unit emission failures are `PEP_RUNTIME_STEP_LIMIT`; I did not re-measure their exact overage.
- Scratch artefacts removed; A2 worktree clean.

REF GH #16. Parents: `6726084796` (A3-135), `6725694094` (A3-126), `6725863459` (A3-131).