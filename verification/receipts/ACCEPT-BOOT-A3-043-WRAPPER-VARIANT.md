# ACCEPT BOOT-A3-043 — wrapper variant: prediction confirmed, and the gap is two things, not one

**Verdict: STILL BLOCKED. 3/4 checks.** My pre-registered falsifier (W2) held: wrapping the builtin call
in a user function **moves** the failure, it does not remove it. The diagnosis is now sharper — and it
forces me to widen my own "one cheap seam" estimate.

## Measured (A1 `86ff953`, seed built there)

```pep
fn slice3(source: SourceBytes) -> Str { return utf8_slice(source, 0, 3) }
fn main(source: SourceBytes) -> Int { let part = slice3(source) ... say(part) ... return 0 }
```

| chunk | check status | resolved call facts |
|---|---|---|
| `slice3` | **valid** | **0** |
| `main` | **valid** | **1** |

Emission then refuses at `slice3`:

```
FIRST REFUSAL unit slice3: Pep C23 cross-chunk call has no resolved call fact
```

**Both chunks check valid.** The program is accepted by the checker; the *emitter* demands a fact the
checker never mints for a builtin call. And `main`'s `call_facts=1` proves the mechanism works
perfectly — for **user-function** calls. Builtins are simply excluded from fact minting.

So the seam is exactly: **builtin calls never get resolved-call facts; user calls do.**

## A second, separate gap found by following the same thread

I checked which builtins the emitter actually lowers by name in
`tests/pep_c23_emitter.pep`:

| builtin | quoted name-matching sites | lowered? |
|---|---|---|
| `byte_at` | 3 | yes |
| `byte_length` | 1 | yes |
| `str_concat` | 3 | yes |
| `int_text` | 0 quoted (166 occurrences, different path) | yes, via another route |
| **`utf8_slice`** | **0** | **no** |

`utf8_slice`'s single appearance in the emitter is the emitter's **own** Pep code calling it, not a
lowering case. **The one Str-producing source accessor in the language is not lowered by the C23
emitter at all.**

## Correcting my own estimate

In BOOT-A3-042 I called this "one seam away" and framed the fix as a single decision. **That was too
narrow, and I am widening it rather than leaving it standing.** Making source-dependent output possible
needs:

1. a fact (or a factless path) for **builtin** calls at initialiser/return sites — an A1/A2 seam decision;
2. a **by-name lowering for `utf8_slice`** in the emitter, like `str_concat` and `byte_at` already have;
3. almost certainly a small **C runtime helper** to slice a grant buffer into a `Str` (allocation/view),
   which is the only genuinely new native code either route needs so far.

Still far cheaper than route R's requirement to repair the quadratic traversal (**381n + 35.68n²**,
80.5% quadratic at 44 nodes; a 44-node `main` already exceeds budget). But it is three bounded items,
not one, and I said I would say so if the estimate moved.

## Predictions, scored honestly

| # | Prediction | Result |
|---|---|---|
| W1 | `main`'s chunk has a fact for the user-function call | **CONFIRMED** (`call_facts=1`) — but I emit all-or-nothing, so I never proved `main` emits *in isolation*; stated rather than glossed |
| W2 | `slice3` refuses (builtin call in return position gets no fact) | **CONFIRMED** — this was my own falsifier and it held |
| W3 | program still cannot produce input-dependent C | **CONFIRMED** |
| W4 | if W2 were wrong, input-dependent C would be demonstrable today | not triggered |

## Refined questions to peers

- **@A2:** does the fix belong in the emitter as a **factless by-name lowering for builtins** (the
  treatment `str_concat` and `byte_at` already get), rather than a new fact kind? That would keep the
  checker's invariant intact and need no A1 change — my reading of the source says yes, but you own it.
- **@A1:** is "builtins are never facts" deliberate? If minting them would change what a fact *means*, the
  emitter route is the only safe one and A1 need not change anything.

## Not established

- **No input-dependent C was produced.** The mission floor remains unproven by anyone.
- I did not attempt a `utf8_slice` lowering myself (that is A2's file, and A3 must not author what it
  later verifies).
- Whether the C runtime can express a `Str` slice without a new allocation model is **unmeasured**; it is
  my inference that a small helper suffices.

## Reproduce

```powershell
git worktree add --detach <t> 86ff953
cd <t>; pwsh -NoProfile -File ./pep.ps1 run examples/hello.pep
$env:PEPIN_GATE_ROOT = '<t>'
python verification/probes/wrapper_variant_043.py    # W2/W3 confirmed, first refusal quoted above
```

## Scope

A3 changed only `verification/**`. A1's checker/contract, A2's emitter and A4's app were read, not
modified. Cap unchanged; no `CURRENT`, manifest, frozen-gate, master or release change.

REF: GH #16 (BOOT-A3-043).