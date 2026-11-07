# ACCEPT BOOT-A3-029 — independent three-slice review of peer claims

**Scope:** verify peers' *newest published claims* against their exact SHAs, on clean trees, rather
than re-running their lanes. This is the three-slice review required by the packet.

**Result: both claims CONFIRMED. No discrepancy found.** One hygiene recommendation for A1, and one
useful correction to an assumption nobody had checked.

## 1. A1's probe — CONFIRMED exactly at A1's own SHA

| | |
|---|---|
| Tree | clean detached worktree at `scratch/a1-dogfood-scan@9282662013ea62ff100369527ba9647d121f0134` |
| Seed | built from that tree (`./pep.ps1 run examples/hello.pep`) |
| Ran | **A1's own** `tests/probe_dogfood_scan_a1.py`, unmodified |

Output, reproduced verbatim in shape:

```
chunk ascii_letter    nodes= 24 status=valid []
chunk ascii_digit     nodes= 12 status=valid []
chunk ascii_continue  nodes= 10 status=valid []
chunk main            nodes= 44 status=valid []
FIRST REFUSAL unit main: status=unsupported Pep C23 conditional lowering requires a non-empty then branch
emitted units before the refusal: ['ascii_letter', 'ascii_digit', 'ascii_continue']
```

A1's claim ("staged check of A4 dogfood app + first emission refusal") is accurate, and it agrees with
my independent probe's first refusal and chunk node counts at the same SHA (BOOT-A3-027). Two
independently written harnesses, same numbers.

## 2. A2's new test — CONFIRMED on two trees, including A2's standalone branch

A2 `codex/a2-bounded-emission@537967e` adds `tests/test_c23_twin_byte_identity.py`.

| Tree | Result |
|---|---|
| A1's merged `9282662` | `Ran 2 tests in 2.162s — OK` |
| **A2's own standalone `537967e`** | `Ran 2 tests in 2.051s — OK` |

Both tests pass, including the **anti-vacuity guard**
(`test_statement_shapes_are_actually_supported_by_the_one_shot_path`: "both paths must really emit,
not both refuse"). That guard is the one that makes the equality claim meaningful, and it is present
and green.

**A correction to an assumption worth recording:** A2's branch does **not** carry the chunk tooling
(`tests/chunk_helper.py` and `pep_chunk_contract.py` are both absent at `537967e`), so I expected this
new test might not run standalone — the same cold-clone class of defect I hit at `123d8b3`. **It runs
fine.** The test does not need the chunk contract, so A2's branch is self-sufficient *for this test*.
Nobody had checked; now it is measured.

## 3. Fixture-provenance hazard applied to A1's probe — correctness unaffected, hygiene still wrong

BOOT-A3-025 found `core.autocrlf=true` with no `.gitattributes`: a checked-out copy differs from the
committed blob (CRLF). A1's probe reads its fixtures from the worktree
(`ROOT / "examples" / "dogfood" / …`), so it feeds the native binary **CRLF** bytes.

Whether that matters is a question I had previously only *reasoned* about ("`\r` is neither letter
nor continue, so it only acts as an extra separator"). **Now measured**, on both byte sets:

| fixture | worktree (CRLF) | runs | committed (LF) | runs | A4 claim |
|---|---|---|---|---|---|
| `input_ascii.pep` | 171 B, 3 CRLF | **23** | 168 B | **23** | 23 |
| `input_nonascii.pep` | 223 B, 5 CRLF | **30** | 218 B | **30** | 30 |
| `input_empty.pep` | 0 B | **0** | 0 B | **0** | 0 |
| `pepin-source-scan.pep` | 1198 B, 39 CRLF | **139** | 1159 B | **139** | 139 |

**Run counts are identical.** So A1's probe will report correct numbers once emission succeeds, and my
earlier reasoning is confirmed rather than merely asserted.

**Recommendation (A1 or A4's call, not A3's):** the counts are safe *for this program only*. Any
future capability that counts lines, matches `\r\n`, reports byte offsets/spans, or hashes input
provenance will silently differ between a checkout and the pinned revision. Cheapest fixes are a
`.gitattributes` (`*.pep text eol=lf`) or having the probes materialise committed blobs
(`git cat-file blob`), which is what my probes do. A3 does not change either.

## 4. What this review does NOT establish

- Confirming A1's *refusal* is not confirming a *result*: A1's probe never reached native execution,
  so there is still **no native result** for A4's application (see BOOT-A3-027/028).
- I ran A2's single new test, not A2's full suite, and not A1's full suite.
- Passing tests are not acceptance: the twin byte-identity test is about the twins matching the
  one-shot walkers, not about A4's application compiling.
- No review of A4's new `913552b` beyond confirming it changes only the outbox and leaves the app
  blob identical (BOOT-A3-027).

## Reproduce

```powershell
# A1's claim
git worktree add --detach <a1> 9282662
cd <a1>; pwsh -NoProfile -File ./pep.ps1 run examples/hello.pep
python tests/probe_dogfood_scan_a1.py            # 4 valid chunks, first refusal unit main

# A2's claim, standalone
git worktree add --detach <a2> 537967e
cd <a2>; pwsh -NoProfile -File ./pep.ps1 run examples/hello.pep
python -m unittest tests.test_c23_twin_byte_identity -v      # 2 tests OK
```

## Scope

A3 changed only `verification/**` in its own branch. All peer trees were clean detached worktrees,
read-only apart from their ignored `_build`; nothing was pushed to any peer branch. No change to
A4's app, A1's checker/host, A2's branch, frozen Full-v2, `CURRENT`, manifest, budgets, master or
release labels.

REF: GH #16 (BOOT-A3-029).
