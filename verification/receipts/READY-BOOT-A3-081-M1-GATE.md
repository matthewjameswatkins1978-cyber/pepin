# READY BOOT-A3-081 — the M-1 gate for compiler A exists and is proven able to fail

**Verdict: the acceptance gate for compiler A is built and calibrated against deliberate stubs — it fails wrong exit codes
and wrong stdout, and still passes correct output. It has NOT judged a real compiler A, because none exists yet at 9/21
emission. Building it now, and proving it can fail, is the point: a gate written by the person who wants it to pass, under
time pressure at the end, is not a gate.**

## What it checks

`verification/probes/verify_m1_081.py`, contract taken from A4's `EXPECTED.md` rather than invented:

- **seven pinned cases** — `a_ok`, `a_badlit`, `a_badbrace`, `a_str`, `a_empty`, `a_crlf`, `a_u8` with A4's exact exit
  codes (0/2/1/5/0/0/1) and exact stdout (`nine_lines(42)`, `ERR literal`, `ERR shape`, `ERR unsupported`, empty, ...).
- **two UNSEEN subset-S0 forms** A4 never pinned, whose expected output I *predict* from S0's own grammar:
  - `fn main() -> Int { return 7 }\n` (single space) → exit 0, nine-line C with `7`
  - `fn  main() -> Int {\n\treturn 0\n}\n` (tab indent) → exit 0, nine-line C with `0`
- comparison is on exit code AND stdout, newline-normalised at the end only.

## The self-test, which is the actual deliverable

A gate that only ever passes proves nothing, so the gate is run against stubs that are wrong in known ways:

```
[1] stub always exiting 0 printing a_ok's C     -> 7/9 cases failed
    PASS a_ok, PASS a_crlf (it prints the right C), FAIL a_badlit 0(want 2),
    FAIL a_badbrace 0(want 1), FAIL a_str 0(want 5), FAIL a_u8 0(want 1),
    FAIL both unseen (prints 42 where 7 and 0 belong)

[2] stub exiting 0 and printing nothing         -> 6/7 cases failed
    PASS a_empty (empty stdout is CORRECT there), FAIL the other six on stdout

SELF-TEST: PASS - the gate detects both wrong exit codes and wrong stdout
```

Both halves matter. Case [1] shows the gate catches wrong exit codes **and still accepts the two cases the stub gets
right**, so it is not a blanket failure. Case [2] shows it catches wrong stdout when the exit code is right, and correctly
*accepts* `a_empty` where empty output is the contract. A gate that failed `a_empty` here would be over-strict and I would
have had to fix it before trusting it on A.

My first version of stub [2] crashed with `IndexError` instead of exiting silently, so "detects wrong stdout" was true for
the wrong reason — a crash, not a stdout mismatch. I fixed the stub and re-ran rather than bank the false green.

## Status: READY, not PASS

```
python verification/probes/verify_m1_081.py --compiler-cmd '["<path to compiler A>"]'
python verification/probes/verify_m1_081.py --selftest
```

`--compiler-cmd` takes a JSON argv prefix, so the gate does not care how A is produced (`build-c23 --sectional`, a
prebuilt exe, or a wrapper). With no compiler it exits 2 and says so: *"This gate is READY. It has not judged a real
compiler A."*

## Limits — what this does not establish

- **No compiler-A evidence exists.** Nothing here says A parses, checks, emits, or rejects anything. It is instrument
  calibration only.
- **The two unseen cases are predictions.** If A emits the nine-line C but with different spacing or a trailing newline, the
  gate will fail on formatting rather than semantics. Given A4's `say`-per-token design the form is near-certain, but
  "near-certain" is not measured, and a first real run may legitimately require reconciling the *oracle*, not the gate. If
  so, that is A4's oracle to amend, not mine.
- **The nine-line expectation itself is unverified.** `EXPECTED.md` says "stdout exactly these 9 lines" without stating
  whether the final `say` adds a trailing newline; I normalise the trailing newline and say so rather than silently picking.
- **Exit-code semantics are A4's contract, not independently derived.** The gate checks A against A4's table; whether that
  table is the *right* contract is a separate question A3-079 already partly probed at the seed-classification layer.

## Next

The moment A1 reports 21/21 emission, this gate runs unmodified against the built A. If it fails, the failure will name the
exact case and both observed and wanted values, so the earliest refusal is legible without re-instrumenting.

REF GH #16. Oracle: A4 `EXPECTED.md` @ `5f62e4b`. Gate authored and calibrated by A3, which is why it is proven on stubs
rather than trusted on assertion.