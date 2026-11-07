# ACCEPT BOOT-A3-030 — A4's EOL guard verified, and its exact remaining scope

**Purpose:** verify a peer's fix for a defect I reported (BOOT-A3-025 point 6: `core.autocrlf=true`
with no `.gitattributes` means a checkout is not the pinned revision), and delimit precisely what it
does and does not cover.

**Verdict: A4's fix WORKS and is correctly scoped to A4's own lane. The root repository is still
affected, and that is a repo-level decision A4 does not own.**

## The fix

A4 added `examples/dogfood/.gitattributes` at `b57d4bf`:

```
# Scoped checkout guard for A4's dogfood lane (A3 BOOT-A3-025 point 6).
# The byte-counting programs measure committed bytes; force LF on checkout
# so a Windows worktree matches the pinned revision byte-for-byte.
*.pep text eol=lf
```

## Verified on a fresh checkout at `b57d4bf`

| file | checkout | CRLF pairs | committed | byte-identical |
|---|---|---|---|---|
| `examples/dogfood/input_ascii.pep` | 168 B | 0 | 168 B | **yes** |
| `examples/dogfood/input_nonascii.pep` | 218 B | 0 | 218 B | **yes** |
| `examples/dogfood/pepin-source-scan.pep` | 1159 B | 0 | 1159 B | **yes** |
| `examples/dogfood/pepin-line-scan.pep` (new) | 998 B | 0 | 998 B | **yes** |

Before the fix the same files checked out at 171 / 223 / 1198 B with 3 / 5 / 39 CRLF pairs
(BOOT-A3-029). The guard does what it says.

**The frozen application is untouched by this change:** `examples/dogfood/pepin-source-scan.pep` is
still blob `4a44dd653e949258a196d247097197d7c24c1da7`, sha256 `f6e8f94240e05c2a…`, identical at
`12e143f`, `913552b` and `b57d4bf`. Freeze intact.

## Scope limit — measured, not assumed

The attribute is `*.pep` **inside `examples/dogfood/`**, so it covers only that directory:

| file (same fresh checkout) | checkout | CRLF pairs | committed | identical |
|---|---|---|---|---|
| `examples/pep_lexer.pep` | 19,425 B | 494 | 18,931 B | **no** |
| `examples/pep_parser.pep` | 96,149 B | 1,875 | 94,274 B | **no** |
| `examples/dogfood/SPEC.md` | 4,352 B | 93 | 4,259 B | **no** |

So `*.md` in the same directory is still translated, and the two large lexer/parser sources that the
seam's own probes read are still ~1–2 KB larger on checkout than at the pinned revision.

**Why this matters and whose call it is:** my gate probes are unaffected (they materialise committed
blobs via `git cat-file blob`), and the A2/A1 probes that read worktree paths happen to still produce
correct *run counts* (BOOT-A3-029 measured 23/30/0/139 identical both ways). But any probe that
hashes or length-checks an input, or any future capability that counts lines or reports spans, will
disagree with the pinned revision on a Windows checkout. A repo-wide guard (`*.pep text eol=lf` at the
repository root, plus a decision about `*.md`) is a repository-level choice — A1's lane or Matthew's,
not A4's and not A3's. **A3 does not add it.**

## What this does not change

No verdict changes. A4's application still has **no native result**: it cannot be emitted inside the
unchanged 100k budget (BOOT-A3-027/028), and semantics remain `PROVEN-ORACLE-ONLY` 25/25. A4's new
`pepin-line-scan.pep` is **not** gated by this receipt — I note its existence and its 998-byte
committed size only, and deliberately do **not** start verifying a second application while the first
gate is still red, since that would move the acceptance target mid-test.

## Reproduce

```powershell
git worktree add --detach <t> b57d4bf
# compare each file's on-disk length/CRLF count against  git cat-file -s b57d4bf:<path>
```

## Scope

A3 changed only `verification/**`. Peer tree was a read-only detached worktree; nothing pushed to any
peer branch; no change to A4's app, A1's checker/host, A2's emitter, frozen Full-v2, `CURRENT`,
manifest, budgets, master or release labels.

REF: GH #16 (BOOT-A3-030).
