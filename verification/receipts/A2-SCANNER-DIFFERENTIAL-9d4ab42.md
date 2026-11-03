# A2 scanner independent differential at `9d4ab42` — boundary/host-safety claims hold; the escaped-NUL position gap is real and already disclosed

**Date:** 2026-11-03 · **Lane:** Agent 3 independent verification (LUCY-20261103-012 "adversarially differential-test A2 scanner latest `9d4ab42` (Int64 max/MAX+1, negative offsets, escapes incl escaped-NUL position ...)") · **Evidence label:** `TESTED`
**Pin:** `codex/a2-bounded-emission` @ **`9d4ab42cf6c18180a789cee9baa39e7d579b3fcc`**, worktree `D:\Projects\wt-a2-bounded` (clean; not modified)
**Instrument:** `verification/probes/a2_scanner_differential.py` (new; no builder files touched, no Terror Bats gate)
**Method:** every claim measured on **both** sides — A2's `stdlib/scan.pep` functions invoked as registered v2 tools with the payload bytes as the host-authorised `semanticTarget`, and the **OCaml seed** (`pep.ps1 check --json`) on an equivalent Pep source. Ground truth is the seed's `status`, diagnostic codes and decoded literal bytes.

## Result — 4 claims hold, 1 disclosed gap confirmed, 1 observation

| case | claim | measured | verdict |
|---|---|---|---|
| **S1** | Int64 max accepted with the exact value | scan `status=ok value=9223372036854775807 nextOffset=19`; seed `valid` | **HELD** |
| **S2** | max+1 refused on both sides | scan `unsupported` ("Pep scan integer is too large for Int"); seed `PEP_INT_LITERAL_RANGE` | **HELD** |
| **S3** | negative offsets refuse without raising | offsets −1 / −19 → `unsupported` ("Pep scan offset is negative"); no exception, no host refusal | **HELD** |
| **S4** | escape-set parity with the seed | 6 accepted (`\n \t \\ \" \0 \r`) ok, decoded content and literal width match the seed; 2 refused (`\a`, `\x41`) refused as the seed does | **HELD** |
| **S5** | escaped-NUL **position** distinguishable | `"\0ab"` and `"ab\0"` → identical scanner output (`parts=["ab"]`, `nulCount=1`, `byteLength=6`, `nextOffset=6`); seed decoded bytes are `00 61 62` vs `61 62 00` | **DISCLOSED_GAP** (falsified) |
| **O1** | (observation, not claimed) a leading `-` is not consumed | scan `unsupported` on `-…`; seed refuses the literal `-9223372036854775808` with `PEP_INT_LITERAL_RANGE`, `-5` is a unary-minus expression over `5` | observed |

Exit code 1 (one falsified claim) with `claim_falsified=1 disclosed_gaps=1`.

## What S1/S2 close (Lucy's LUCY-20261103-005 check 2)

Lucy asked whether `scan_int_at` rejects the legal signed-64 max `9223372036854775807`. Measured on
the seed itself: **the seed accepts `9223372036854775807` as a literal and refuses
`-9223372036854775808` with `PEP_INT_LITERAL_RANGE`** — the negative bound is not a literal in this
language, it would be unary minus over an out-of-range magnitude. So an **unsigned** digit scanner
is the correct shape, and A2's `9d4ab42` repair (accept max, refuse max+1) matches the seed at both
boundaries. No signed-max special case is owed, and no grammar decision is needed from A1.

## S5 — the gap is real, and it is A2's own disclosure, stated accurately

`BOOT-A2-20261103-013` says the scanner "counts NUL without emitting it as a fragment" and asks for
either exact fragment preservation or an explicit refusal to claim semantic equivalence. Measured
consequence: **leading and trailing escaped NUL are indistinguishable in the scanner's output**
(`"\0ab"` and `"ab\0"` return the same `parts`/`nulCount`/`byteLength`/`nextOffset`), while the seed's
decoded bytes differ in position. So the disclosure is accurate and the residual gap is exactly the
one named — NUL *count* is preserved, NUL *position and fragment boundary* are not.

This is **not** a newly discovered defect and I am not claiming one: a decoder that must reconstruct
`\0` placement cannot be built on this output. Two honest closes are available to A2 — emit a
position-carrying fragment (e.g. a part index or an explicit NUL slot) or label the scanner
"token-compatible, not semantically equivalent" for NUL. Either way the claim in the probe stays
falsified until the output distinguishes the two sources.

## Discipline notes (own errors, disclosed)

Three defects in this probe were found and repaired **before** any of the above was recorded, all via
Threadmoth `edit` with `expect_count 1` certificates (`unrelated_bytes_changed=false`, `lf→lf`):
a duplicated `held =` line that left the S3 expectation malformed, escape payloads built from the
escape *letter* instead of the escape sequence (which silently turned S4 into a plain-letter test),
and an S3 expect/outcome string mismatch that reported a held claim as falsified. The escape-case
rewrite is why S4 now compares decoded bytes, literal width and `nulCount` rather than a mistaken
"decoded length" reading of `byteLength` (which is the literal's source width, quotes included).

Honest scope: pure scanner/tool-host layer; no emission, no native build, no execution beyond the
seed's checker. One pin, one pass; no bisection of when S5's shape appeared.

## Boundaries

`stdlib/scan.pep`, `tests/test_scan.py` and every other A2 path untouched. No bat, manifest, frozen
runner, budget or gate expectation changed. Write side: `verification/probes/a2_scanner_differential.py`,
this receipt, `INDEX.md`'s entry.

## Next action

Reported to A2 (and A1, as the boundary owner) on #16. Re-run is `python
verification\probes\a2_scanner_differential.py <A2-worktree>`, unchanged, at A2's next slice; the
S4 escape matrix and S1/S2 boundaries are the regression set to keep green.
