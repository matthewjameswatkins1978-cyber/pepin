# ACCEPT BOOT-A3-088 — A4's normative Pep-0 boundary reproduces 17/17, and it is now replayable from the document

**Verdict: every one of the 17 boundary claims in A4's `PEP0_SUBSET.md` reproduces against the live seed, including each
specific diagnostic code. The claims were made from ignored scratch (`_build/s1/`) and so were not replayable; they now are,
from the prose alone. This is the normative contract compiler A will be accepted against, so it was worth confirming before
A is built against it rather than after.**

## Why this specific check

`PEP0_SUBSET.md` is marked **NORMATIVE for compiler-A acceptance**. It lists a "Boundary evidence (all measured, this
mission)" section of seed verdicts across three classes — (iii) S0-valid, (ii) seed-valid but outside Pep-0, (i)
seed-invalid. A wrong verdict in that section does not fail loudly; it silently misdirects what compiler A is supposed to
accept and reject. A4 measured them on `_build/s1/`, which is ignored, so nobody could re-run them.

`verification/probes/pep0_boundary_088.py` regenerates every probe from A4's own description and re-runs the seed.

## Result: 17/17

```
PASS i64max         valid    []                        
PASS i64max+1       invalid  [PEP_INT_LITERAL_RANGE]    
PASS 23-digit       invalid  [PEP_INT_LITERAL_RANGE]    
PASS 007            valid    []                         leading zeros accepted
PASS 19-digit       valid    []                         1000000000000000000
PASS unary-minus    valid    []                         return -42
PASS binop          valid    []                         return 0-42
PASS Main           valid    []                         different name, not main
PASS cr-only        valid    []                         CR line endings
PASS cr-tab         valid    []                         CR + tab separator
PASS nul-mid        invalid  [PEP_UNEXPECTED_CHARACTER]
PASS nul-trail      invalid  [PEP_UNEXPECTED_CHARACTER]
PASS bom            invalid  [PEP_UNEXPECTED_CHARACTER]
PASS vtab           invalid  [PEP_UNEXPECTED_CHARACTER]
PASS nbsp           invalid  [PEP_UNEXPECTED_CHARACTER]
PASS uppercase-FN   invalid  [PEP_PARSE_EXPRESSION]     
PASS lowercase-int  invalid  [PEP_UNKNOWN_TYPE]         

17 probes, 0 disagreeing
A4 BOUNDARY EVIDENCE: REPRODUCES
```

The non-obvious ones all hold: `007` parses (leading zeros accepted), `Main` is a different name and therefore seed-valid,
**CR-only** line endings are accepted, and the four lexer rejections (NUL mid, NUL trailing, BOM, VTAB) are all
`PEP_UNEXPECTED_CHARACTER` exactly as A4's `is_ws` claim (32/9/10/13 only) implies.

## The claims that decide compiler A's shape

| class | claim | reproduced |
|---|---|---|
| (iii) S0 | `19-digit` is seed-**valid** but the subset caps at 18 → exit 4 | yes — seed says valid, which is precisely why the cap must be A4's, not the seed's |
| (ii) | unary minus and `0-42` are seed-**valid** yet not in S0 | yes — no C emitted, and not because the seed rejects them |
| (ii) | `Main` seed-valid | yes — S0 rejects it on `is_main4`, not on the seed |
| (i) | NUL/BOM/VTAB/NBSP are lexer rejections | yes, all `PEP_UNEXPECTED_CHARACTER` |

Together with A3-086's three deliberate seed divergences, the picture is now complete and checked from both ends: the seed
verdict is confirmed, and the subset's deliberate departures from it are confirmed.

## Construction choices I made, stated so they can be challenged

- **BOM**: A4 wrote "`\239` first byte". I used the real three-byte UTF-8 BOM `ef bb bf`, which is the stronger case. A
  lone `\239` would very likely also be `PEP_UNEXPECTED_CHARACTER`, but I did not test that specific byte alone.
- **`nul-mid` / `nul-trail`**: constructed as a NUL inside the name (`fn ma\x00in`) and a NUL before the final newline.
  A4's prose says "NUL-mid/trail" without giving bytes, so the exact position is my reading. Both are lexer rejections
  either way, so the class conclusion is robust to the position.
- **`cr-tab`**: `fn\tmain() ... \r\treturn 42\r}\r` — CR line endings with tab separators, per A4's "CR-only/CR tab/LF
  valid".

## Limits

- Verified the **seed verdicts only**. Whether S0's *implementation* honours the boundary needs compiler A to run, which it
  cannot at 9/21 — so A4's "native confirmation pending S2" remains accurate and unaddressed by this receipt.
- I did not test every possible separator/joint combination, only the documented classes. A claim like "optional around
  every other joint" remains sampled rather than exhaustively proven.
- `_build/s1/` is still ignored scratch on A4's side. My probe is the replayable substitute; A4 may prefer to commit their
  own generator, which is theirs to decide.

## Reproduce

```
PEPIN_SEED_ROOT=<worktree with built seed> python verification/probes/pep0_boundary_088.py
```

REF GH #16. Boundary authored by A4 (`afd2d7e2:examples/dogfood/pep0/PEP0_SUBSET.md`). Independent reproduction: A3.