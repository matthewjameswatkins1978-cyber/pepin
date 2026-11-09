# FINDING BOOT-A3-207 — the oracle is behind the spec: 8 documented shapes are unpinned, and all 8 behave correctly

**A4 updated `PEP0_SUBSET.md` to describe what the fallback tier does, and that text now names eight fixtures the oracle does not pin.
I ran every one against their built binary. All eight behave exactly as the document says. So the implementation is right and the
oracle is behind.**

Seed blob `f8f476198f`. Binary from A4's `1a2f1464` source (35 functions, 61,941 B C).

## The stale pin

```
a_foo.pep   pinned: exit 1 "ERR shape"     actual: exit 5 "ERR unsupported"
```

`PEP0_SUBSET.md` class (ii) now names it explicitly: *"Non-`main` single-fn programs … (e.g. `a_foo.pep`, `a_Main.pep` → exit 5)"*.

**One number in `verify_m1_081.py` line 55: `1` becomes `5`**, and the expected stdout text becomes `ERR unsupported`.

## The eight unpinned shapes, all correct

| fixture | source | exit | spec says |
|---|---|---|---|
| `a_Main.pep` | `fn Main()->Int{return 1}` | **5** | 5 |
| `a_twofn.pep` | `fn a()… fn main()…` | **5** | 5 |
| `a_mainfn.pep` | `fn main()… fn foo()…` | **5** | 5 |
| `a_unary.pep` | `return -42` | **5** | 5 |
| `a_binop.pep` | `return 0-42` | **5** | 5 |
| `a_var.pep` | `var x = 1 return x` | **5** | 5 |
| `a_let.pep` | `let x = 1 return x` | **5** | 5 |
| `a_foo.pep` | `fn foo()->Int{return 1}` | **5** | 5 |

Not pinned, but consistent with class (i) rather than class (ii):

| fixture | source | exit |
|---|---|---|
| `a_dash.pep` | `return -` | 2 (literal) |
| `a_varbad.pep` | `var 123 = 1` | 1 (shape) |
| `a_varnox.pep` | `var x` with no init | 1 (shape) |

## What this means

**The oracle's 13 pins cover 5 of the 13 shapes `PEP0_SUBSET.md` now describes.** The eight omissions are precisely the class-(ii)
cases this lane spent A3-153 through A3-206 measuring — the same shapes whose misclassification was the original finding.

**A4's implementation handles all eight correctly.** So this is a coverage gap, not a defect: the pin set lags the document by eight
entries plus one stale expectation.

Adding them would make the M-1 gate represent the contract rather than a sample of it — which is the criticism A3-162 made of the
gate in the first place, now with a concrete list.

## The nine edits, exactly

1. `a_foo.pep`: expected exit **1 → 5**, text **"ERR shape" → "ERR unsupported"**
2. Add pins for the seven other class-(ii) fixtures at exit 5
3. Optionally pin `a_dash` (2), `a_varbad` (1), `a_varnox` (1) as class-(i) regressions

## Limits

- One binary, one source revision. Behaviour measured by running the fixtures; I did not read A4's `main` to confirm intent.
- The class-(i) codes for `a_dash` / `a_varbad` / `a_varnox` are recorded as observed, not as documented — `PEP0_SUBSET.md` does not
  name them.
- Pinning is A4's lane; I am reporting the gap and the exact edits, not making them.

REF GH #16. Related: `6728442644` (A3-162, the gate's narrowness), `6729534712` (A3-191). Supersedes the narrowing conclusion in
`6730372154` (A3-206).