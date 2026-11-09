# FINDING BOOT-A3-182 — the 10 sectional-built programs all work, and exit codes carry no information on this tree

**A3-181 listed "I did not check whether the 10 that built actually run" as a limit. Closed: all ten build, run, and produce
distinct plausible values. The first attempt to measure this was invalid because of a bug in my own script, which is recorded below
because the invalid result looked like a finding.**

Seed blob `f8f476198f`. Candidate `b039fc5`, each file built and run with its **own** executable.

## The result

| file | C bytes | stdout | rc |
|---|---|---|---|
| `dogfood/arity_nocall.pep` | 9,986 | `0` | 0 |
| `dogfood/arity_ok.pep` | 9,997 | `1` | 0 |
| `dogfood/pep0/a_big19.pep` | 9,821 | `1000000000000000000` | 0 |
| `dogfood/pep0/a_crlf.pep` | 9,804 | `42` | 0 |
| `dogfood/pep0/a_ok.pep` | 9,804 | `42` | 0 |
| `dogfood/pepin-line-scan.pep` | 12,195 | `3` | 0 |
| `dogfood/t2_names_probe.pep` | 13,330 | `0` | 0 |
| `dogfood/t2_valid.pep` | 9,997 | `1` | 0 |
| `lab_demo.pep` | 10,030 | `42` | 0 |
| `tests/fixtures/list_probe_native.pep` | 10,793 | `6` | 0 |

**10 of 10 build and run, and the values are distinct and plausible.** I checked two against their source: `a_ok.pep` is
`return 42` and prints `42`; `lab_demo.pep` is `double(21)` and prints `42`. The other eight I have not checked against an
expectation — "plausible" is not "verified" and I am not upgrading it.

## The bug that produced a false result first

My first version did this:

```python
exe = T / "o.exe"                 # one path, reused
...
built.append((p, exe))            # every entry holds the SAME path
...
for p, exe in built:              # so all ten "ran" the last binary written
```

All ten reported `rc=0 out=2B`. **That uniformity was the tell** — ten different programs producing byte-identical output should
have stopped me, and instead I nearly wrote "they all run and print a single digit".

This is the fifth tooling fault I have found in my own harness this mission and the second this session. It is the same class as the
`check-ok` label in A3-174: **a summary that looks like a result.** The distinguishing question is whether the pattern is *too*
uniform for the inputs, and I should ask it before believing a table.

## What the exit codes say, which is nothing

Every program exits **0**, including `a_big19` which computes `1000000000000000000` and `a_ok` which computes `42`. That is the
unpatched epilogue (A3-159 defect 3): the runtime prints the value and then `return 0`.

So on this tree **`rc` is not a signal**. Any check of the form "did it run correctly" answered by exit code is vacuous here, and
that includes the shape of test I was about to write. The value on stdout is the only observable, which is exactly why the oracle
pins stdout separately from the exit code.

## What this closes and what it does not

**Closes:** A3-181's limit. The sectional path's accepted programs are not hollow — they compute.

**Does not close:** whether the eight unverified values are *correct*, only that they are distinct and plausible. Nor whether the
programs would still work once the epilogue propagates exit codes and stops echoing — that changes observable behaviour in both
directions.

## Limits

- Ten files, one revision, sectional path only.
- Two values checked against source; eight not.
- C sizes 9.8–13.3 KB each include A2's ~4.2 KB `pep_utf8_slice` helper (A3-179), emitted even where unused at runtime.

REF GH #16. Closes the limit in `6729035984` (A3-181).