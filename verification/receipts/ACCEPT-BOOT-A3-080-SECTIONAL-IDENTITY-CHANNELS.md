# ACCEPT BOOT-A3-080 — A3-S3: A1's sectional merge fail-closed channels reproduce independently; five identity channels stay open

**Verdict: A1's five corruption channels (empty/foreign/stale/hole/out-of-span) are genuinely fail-closed — I reproduced all
six of their negatives independently. Five further *identity* channels are fail-open, none reachable through the current
driver path. The merge's stated safety property is "no stale/foreign facts", and identity is the part that is not enforced.**

## Lane state corrected first

The dispatch pins A1's owner line at `codex/a1-typed-bound-pipeline@12dbf1a`. Live remote is **`183b2fac`**, whose own commit
message is *"R3 sectional merge fail-closed on stale/foreign/empty/out-of-span (6 negatives green)"*. I audited `183b2fac`,
not the stale pin. `pep_sectional.py` is 19,056 B / 391 lines there and does not exist at all on `1885566` or `bea071a`.

## A1's six, independently executed

```
python -m unittest tests.test_a1_sectional_merge_negatives -v   # 6 tests, OK
```

and independently re-driven through my own probe rather than their test file:

| channel | A3 observed |
|---|---|
| empty group list | `ValueError: sectional merge: empty group list` |
| foreign document | `ValueError: sectional merge: foreign document in group` |
| stale revision | `ValueError: sectional merge: stale revision in group` |
| hole present | `ValueError: sectional merge hit a hole; not supported` |
| out-of-span call fact | `ValueError: sectional merge: group fact outside slice span` |
| valid control | merges, status `valid` |

Credit where due: these are real, they fire before any adoption, and they raise `ValueError` rather than a bare `KeyError`.

## Five identity channels that do not refuse

`verification/probes/sectional_negatives_080.py`, run against `183b2fac`:

| probe | expected | observed |
|---|---|---|
| forged `semanticId` on the entry function fact | refuse | **adopted** — `1 fact(s): main`, forged id carried through |
| entry name carried twice with different `semanticId`s | refuse | **adopted** — `1 fact(s): main` |
| call fact naming a callee absent from every function fact | refuse | **adopted** |
| duplicate ids inside one group (`[7, 7]`) | refuse | **adopted** — two call facts collapse onto one id |
| unsorted chunk ids | refuse | **mis-attributed** |

`merge_reports` validates `document` and `revision` and that a fact's `syntaxId` is inside the span. It never validates
`semanticId`, never checks that a `calls` fact names a function present in the merged `functions` list, and never checks
`cids` for duplicates. Dedupe is keyed on `(name, semanticId)`, so a foreign id is not a mismatch to refuse — it is a
*different function*.

## The double `break`, measured

```python
for _, rep in groups:
    for e in rep["functions"]["value"]:
        if _fval(e, "name") == entry_name:
            ...
            break
    break          # <- exits after the FIRST group, found or not
```

The outer `break` runs unconditionally, so only `groups[0]` is ever scanned for the entry fact. My second probe shows the
consequence directly: two groups each carrying `main`, and the merged report holds **one** fact — the later group's copy is
silently dropped, neither refused nor reconciled. The docstring intends *"local minted fact plus the whole-file functions
list"*; the code means *"first group's fact, if any"*. Today that is harmless because every group of one function carries
the same fact, and `all_fn_facts` supplies the list regardless — but a reordered `parts` list would silently change which
fact wins, with no test to catch it.

## The latent remap hazard

`sliced()` numbers chunk nodes **in the order given**; `merge_reports` renumbers by `sorted(cids)`. The two agree only if
the caller passes ascending ids. Demonstrated: a chunk of ids `[10, 2]` with a fact on chunk-local `0` belongs to node 10
(full-slice rank 1), and the merge re-attaches it to **rank 0 = node 2**. No refusal, no diagnostic. The driver's `groups`
path always yields `tuple(sorted(keep))`, so this is **latent, not live** — and `bounded_units`' *default* statement path
yields `keep_header + subtree(statement)`, a concatenation that is not globally sorted, so the contract is one caller away
from being violated.

## Severity, stated honestly

None of the five is reachable through `check_program` today: the `groups` path sorts ids, and every group's report comes
from the checker on the same function, so the entry fact and its `semanticId` agree by construction. I am **not** claiming a
live wrong-output bug. What is wrong is the *claim*: the docstring says the merge is fail-closed against "stale/foreign
facts", and identity is exactly the dimension it does not police. The cheap hardening is to refuse when two groups disagree
on a function's `semanticId`, and to assert `len(set(cids)) == len(cids)` before building `g2s`.

This sits with **A1** (`pep_sectional.py`, `pep_chunk_contract.py`). I have not edited either file.

## Reproduce

```
PEPIN_SECTIONAL_ROOT=<worktree at 183b2fac> python verification/probes/sectional_negatives_080.py
```

Read-only: imports A1's module, writes nothing to A1's lane. The probe initially scored the remap case as PASS by raising
when it expected `[1]` and got `[0]`; that was a dishonest pass and I corrected it, so the mis-attribution now reports as
OPEN with the node it moved to. Recorded because a verifier faking its own green is worse than the bug.

REF GH #16. Input SHA `183b2fac`. Author under audit: A1. Independent run: A3.