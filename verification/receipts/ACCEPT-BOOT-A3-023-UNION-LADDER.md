# BOOT-A3-023: union-member structural ladder — where the Pep-written parser actually stops

**Seat:** A3. **Order:** LUCY-20261107-001 (A3 lane) + packet fallback item: *"Measure one
real parser >25-union-member failure plus a negative malformed variant source as A1's first
structural parser test; retain source size, tool steps and exact parser stage."*
**Measured against:** A1 `codex/a1-typed-bound-pipeline@a7d3ee1` (seed OCaml 5.5.2 +
Pep-written parser `examples/pep_parser.pep` via the JSONL session).
**Driver:** `verification/probes/union_member_ladder.py` (measured runtime 7 s).

## Headline

**The ceiling is not 25 variants. It is ~19 arms / ~540 source bytes for this shape.** The
Pep-written parser completes a valid 18-variant union (517 bytes) and **refuses a valid
19-variant union (540 bytes) with `PEP_RUNTIME_STEP_LIMIT` raised by the parser tool during a
`pep-c23-parser-step`**, while the OCaml seed reports the same source `valid`. Union-member
count is a proxy for source bytes, not the axis.

## Ladder

`type Expr = V0(Int) | ... | Vn(Int)` plus `fn describe(value: Expr) -> Int { return match
value { V0(x) => x ... } }` plus `main`.

| arms | source bytes | OCaml seed | Pep-written parser |
|---|---|---|---|
| 5 | 228 | valid | **complete**, 44 nodes |
| 15 | 448 | valid | **complete**, 104 nodes |
| 16 | 471 | valid | **complete**, 110 nodes |
| 18 | 517 | valid | **complete**, 122 nodes |
| **19** | **540** | **valid** | **REFUSED** `PEP_RUNTIME_STEP_LIMIT` (parser step) |
| 20 | 563 | valid | REFUSED `PEP_RUNTIME_STEP_LIMIT` |
| 22 | 609 | valid | REFUSED `PEP_RUNTIME_STEP_LIMIT` |
| 24 | 655 | valid | REFUSED `PEP_RUNTIME_STEP_LIMIT` |
| 25 | 678 | valid | REFUSED `PEP_RUNTIME_STEP_LIMIT` |
| 30 | 793 | valid | REFUSED `PEP_RUNTIME_STEP_LIMIT` |

Exact stage: the refusal is the return of `tool_invoke("pep-c23-parser-step")` —
`{"outcome":"error","error":{"code":"PEP_RUNTIME_STEP_LIMIT"}}` — i.e. **the Pep-written
parser function exhausted its own step budget mid-parse**, not a parse error and not the
host driver's attempt counter. (The driver bounds attempts at
`min(len(source_bytes)+2, MAX_PARSER_STEPS)`; that bound is not what fired here.)

**Mechanism is INFERRED, not measured:** a single parser step appears to re-walk the growing
variant list, so per-step cost rises with the declaration, and the per-call budget is hit
before the source is consumed. I did not instrument per-step cost for this ladder; the
receipt reports where it stops, not why.

## The malformed negative — caught, but not by the parser

Source: `type Expr = V0(Int) | V1(Int) | V2(Int) | V3(Int) | Vlast(` (94 bytes, unterminated
variant payload type).

| oracle | result |
|---|---|
| OCaml seed | `invalid` |
| Pep-written parser | **completes with 0 nodes** — it does not raise, it reports done with an empty AST |
| `analyze_chunk_typed` over that 0-node progress | **`invalid`, `PEP_PARSE_EXPECTED` at bytes 63–67** |

So the structural negative *is* refused end-to-end (fail-closed, correct span), but the
refusal comes from the **checker's parse-progress path**, not from the parser tool. The
parser tool's "complete" verdict is not a syntax oracle: completeness and correctness are
different claims, and only the checker checks.

## Corrections made before finalising (disclosed)

1. My first ladder produced `seed=invalid` for **every** rung and looked like a union-size
   mass failure. It was my grammar: the seed's match arms are `pat => expr`, so my
   `V0(x) => { return x }` blocks were `PEP_PARSE_EXPRESSION` at byte 126. Fixed to `pat =>
   expr` before any conclusion was drawn. The wrong shape is recorded here rather than
   dropped, because it is exactly the kind of self-inflicted "evidence" that reads as a
   product defect.
2. The first malformed variant was built from the 30-arm source, so it was refused for
   budget rather than malformedness. Rebuilt at 5 arms (94 bytes) so the negative is about
   syntax, not bytes.
3. `>25` came from the packet. Measured boundary is 18→19 arms; the number in the order was
   never reached, so the order's premise ("a >25-member union fails") is true but
   uninformative — it fails considerably earlier.

## What A1 can use

- **Bytes, not arms, is the axis.** Any structural parser test that plans to "grow a union
  past 25 members" will already have failed at ~540 bytes; a ladder should be expressed in
  source bytes and reported with the exact step call that refused.
- The malformed control belongs in the suite as-is: seed `invalid` + 0-node parser progress +
  `PEP_PARSE_EXPECTED` from the checker. That is a cheap, deterministic, stage-labelled
  negative and it distinguishes "parser said done" from "checker said wrong".
- This does not touch issue #20's staged composition ceiling directly; it locates one
  concrete, reproducible rung below it in bytes.

## Discipline notes

No new pinned builder SHA (`a1=a7d3ee1`), no frozen Full-v2 run, no Candidate7 relabel, no
builder/frozen/peer file touched. Seed verdicts come from `pep.ps1 check --json` on the
candidate worktree; parser results come from the session's `pep-c23-parser-*` tools. No
claim is made about runtime cost accounting beyond the step-limit code observed.

## Reproduce

```powershell
python verification/probes/union_member_ladder.py D:\Projects\wt-a1-fix
# expected: complete at 5/15/16/18 arms; PEP_RUNTIME_STEP_LIMIT at 19 and above;
#           malformed (5 arms, 94 bytes) -> 0 nodes, checker PEP_PARSE_EXPECTED
```
