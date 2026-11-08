# GATE BOOT-A3-162 — compiler A's contract is now a mechanical gate, and the suite is honestly red

**A3's gate suite gains an eighth gate: compiler A's input classification. It fails, 7 of 14 cases, and that is the honest
state. Every previous "ALL GREEN" run was green because the suite tested only what passes.**

Seed blob `f8f476198f`. Gate builds the committed product-path C (`fixtures/a3-compilerA-productpath.c`), so it never skips.

## The suite now

```
gate                            result  detail
A4 oracle replay (13 pins)      PASS    ORACLE REPLAY: PASS
A4 normative boundary (17)      PASS    A4 BOUNDARY EVIDENCE: REPRODUCES
A1 semantic oracle (23)         PASS    A1 SEMANTIC ORACLE: REPRODUCES
A1 sectional merge (11 probes)  PASS    11 probes, 0 disagreeing
A2 DIVERGENCE-2 (16)            PASS    16 checks, 16 passed
M-1 gate calibration            PASS    SELF-TEST: PASS
Seed vs emitted differential    PASS    SEED vs EMITTED: AGREE on all
Compiler A contract (14 cases)  FAIL    CONTRACT: 7/14 match PEP0_SUBSET.md - 7 misclassified

8 gate(s) ran, 1 failed, 0 skipped — A3 GATES: 1 FAILING
```

## Why this gate had to exist

The M-1 oracle pins **one example per input class**. `-> Str`, `-> Bool` and `-> Unit` share a single code path in
`find_brace`, so three pins test one branch. The oracle therefore cannot see that every other documented class-(ii) shape is
misclassified — and it passed 15/15 while they were wrong.

That is a structural blind spot, not an oversight in any one pin. The new gate tests **the contract as published**, not a sample
of it.

## The fourteen cases

| case | want | got | |
|---|---|---|---|
| `-> Bool` | 5 | 5 | ok |
| `-> Unit` | 5 | 5 | ok |
| `-> Str` | 5 | 5 | ok |
| `fn Main()` | 5 | **1** | MISMATCH |
| non-main only | 5 | **1** | MISMATCH |
| unary minus | 5 | **2** | MISMATCH |
| binary arithmetic | 5 | **3** | MISMATCH |
| `var` | 5 | **1** | MISMATCH |
| `let` | 5 | **1** | MISMATCH |
| multi-function | 5 | **1** | MISMATCH |
| 19-digit literal | 4 | 4 | ok |
| accepted shape | 0 | 0 | ok |
| empty input | 0 | 0 | ok |
| whitespace only | 0 | 0 | ok |

## What "1 FAILING" means, precisely

It does **not** mean the language, the emitter or A1's integration is broken. Seven gates still pass, and M-1 passed 15/15 through
the product path in A3-159. It means **compiler A does not implement the contract it publishes**: `PEP0_SUBSET.md` promises nine
out-of-subset shapes exit 5, and two do.

A suite that stayed green here would be telling the next reader something false. The gate flips to PASS the moment A4 either gives
`main` enough parsing to classify properly, or narrows the published contract to the three types it can actually detect — and
updates the pins to match.

## Usage

```
python verification/run_gates.py                       # fixture build (always runs)
PEPIN_CA_EXE=<path> python verification/probes/contract_c7_162.py   # test a tracked build
```

Exit codes: 0 all match, 1 mismatches with each named, 3 no compiler or fixture.

## Limits

- The gate tests the **committed fixture C**, which is a probe artifact of A3-159, not a tracked build. When a tracked candidate
  exists, `PEPIN_CA_EXE` must be pointed at it for the gate to mean anything about the repository.
- Fourteen cases, one seed, one source revision.
- The expected codes are read from `PEP0_SUBSET.md` as it stands today. If A4 narrows the contract, **this gate's table must change
  with it** — the gate pins the promise, not the implementation.

REF GH #16. Related: `6728382343` (A3-160, the seven on the product path), `6728133368` (A3-155, the three source sites).