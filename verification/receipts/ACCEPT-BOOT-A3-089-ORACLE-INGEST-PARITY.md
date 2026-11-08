# ACCEPT BOOT-A3-089 — A1's oracle ingest is byte-faithful, but its corpus has no 0-byte empty-input fixture

**Verdict: A1's ingested copy of A4's six R1/R2 fixtures is byte-identical, including CRLF and NBSP — the ingest is clean.
Two gaps worth closing: A1's corpus contains no truly 0-byte input even though S0 pins empty input as a behaviour, and 7 of
22 fixtures carry a doubled trailing newline inconsistently with the other 14, so its positives are not interchangeable
with A4's.**

## Context

A1's `a15def08` (`codex/a1-integration-ledger-20261107`) added `tests/fixtures/pep0_oracle/` with 22 `.pep` fixtures and
reported "R1 fixtures absorbed, 18/18 green". A4's `2520a678` holds the canonical originals at
`examples/dogfood/pep0/`. Two copies of an acceptance oracle can silently diverge, so I compared them by blob.

`compiler_a.pep` is unchanged at every A4 revision so far (`ca732536` at `5f62e4b`, `afd2d7e2`, `2520a678`), so all my
earlier compiler-A measurements still apply.

## Ingest is byte-faithful — the six shared names

| fixture | A4 blob | A1 blob | identical |
|---|---|---|---|
| `a_nul` | `12c7cb11ed` | `12c7cb11ed` | **yes** |
| `a_big19` | `80bc7fe952` | `80bc7fe952` | **yes** |
| `a_foo` | `193f52ce76` | `193f52ce76` | **yes** |
| `a_dup` | `d63405fdad` | `d63405fdad` | **yes** |
| `a_gfn` | `f06a8286ea` | `f06a8286ea` | **yes** |
| `a_grt` | `7caf483f29` | `7caf483f29` | **yes** |

And the renamed analogues that *are* the same fixture:

| A1 | A4 | identical |
|---|---|---|
| `crlf_ok` (36 B, `0d 0a` preserved) | `a_crlf` | **yes** |
| `nbsp_fn` (32 B, `c2 a0`) | `a_u8` | **yes** |

CRLF and NBSP surviving a rename-and-copy is the part that usually breaks. It did not. Credit to A1.

## Gap 1 — no 0-byte empty input anywhere in A1's corpus

`inc_empty.pep` is **1 byte**: `0a`. It is a whitespace-only file, not an empty one.

A4's `a_empty.pep` is **0 bytes** (`e3b0c442…`, the empty blob), and `EXPECTED.md` pins empty input as its own behaviour:
*"Expected exit 0, stdout empty (no output)"*, listed separately from `a_ok` in the exit-code table. Those are two different
inputs and A1's corpus covers only the second-order one. A compiler A that mishandled a genuinely empty file — e.g. by
requiring at least one byte before `find_fn` succeeds — would not be caught by A1's set.

The name makes this easy to miss: `inc_empty` reads as "empty" but is not. Worth either adding a real 0-byte fixture or
renaming this one to say what it is.

## Gap 2 — 7 of 22 fixtures end with a doubled newline, 14 do not

| tail | count | fixtures |
|---|---|---|
| `7d 0a` / `0d 0a` (single, well-formed) | 14 | `a_*` six, `crlf_ok`, `inc_fn`, `inc_ret`, `nbsp_fn`, `neg_rettype`, `out_str`, `pos_twofn` |
| `0a 0a` (**doubled**) | **7** | `neg_badlit`, `neg_brace`, `neg_trail`, `neg_unknown`, `out_match`, `pos_42`, `pos_ws` |
| other | 1 | `inc_empty` (`0a`) |

The split does not follow the naming (both `pos_42` and `pos_twofn` are positives, only one is doubled), which suggests an
artefact of how those seven were written rather than deliberate trailing-whitespace coverage. Concretely, `pos_42` is
`fn main() -> Int { return 42 }\n\n` (32 B) while A4's `a_ok` is `fn  main() -> Int {\n  return 42\n}\n` (34 B, double space
after `fn`) — different bytes, different intent, and neither is a substitute for the other.

Practically: any cross-read of the two oracles must compare by *fixture name semantics*, not assume similar names are the
same input. If the doubled newline is deliberate, documenting it is cheaper than the next person rediscovering it; if it is
an artefact, normalising keeps the corpus honest.

## What is NOT wrong

- No divergence: there is no case of two fixtures claiming to be the same input with different bytes.
- A1's renamed fixtures are legitimately *different* tests, not corrupt copies — e.g. `neg_badlit` uses `return 4x` (bad
  digit) where A4 uses `return ;` (missing literal); `neg_rettype` uses `return true` where A4 uses `-> Str`. Both are valid
  negatives; they simply are not equivalents and should not be described as ingested copies.

## Limits

- Compared blobs and trailing-byte profiles. I did not run A1's 18-green suite, so I make no claim about whether those tests
  pass — only about what the fixtures *are*.
- A1's fixtures at `a15def08`; if A1 has since revised them the comparison must be re-run. `tests/fixtures/pep0_oracle/` is
  A1's lane and I have not touched it.

## Reproduce

```
git rev-parse <rev>:examples/dogfood/pep0/<name>.pep        # A4 canonical
git rev-parse <rev>:tests/fixtures/pep0_oracle/<name>.pep   # A1 ingested
```

REF GH #16. Fixtures authored by A1 (ingest) and A4 (canonical). Independent comparison: A3.