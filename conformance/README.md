# Pepin language conformance laboratory

This directory owns an independent, reusable black-box laboratory for the
OCaml seed compiler at the reviewed A11 base. It does not edit the Pep parser,
checker, interpreter, or established semantics.

## Run

From the repository root:

```powershell
python conformance/harness.py --seeds 20261026 1101 1201 --count 4 --reduce 2
```

Add `--a11` when the inherited lexer differential suite should be included in
the receipt; it has its own 180-second process bound:

```powershell
python conformance/harness.py --a11
```

The command bounds every compiler subprocess, writes generated inputs under
ignored `_build/conformance/`, and produces:

- `_build/conformance/results.json` — machine-readable run receipt;
- `_build/conformance/report.md` — generated findings report;
- `_build/conformance/corpus/` — exact inputs used;
- `_build/conformance/counterexamples/` — reduced byte-for-byte reproducers.

The command returns non-zero only when a fresh run records a confirmed bug.
`missing-test` entries are successful coverage observations, not correctness
claims.

## Coverage

The fixed corpus is every repository `.pep` example. Each configured seed then
generates the same number of programs in four families: valid execution,
invalid/ill-typed syntax, runtime stress, and session/revision invariants.
The generator covers arithmetic, integer boundaries, lists, empty-list
context, records, recursive unions, nested matching, lexical shadowing,
recursion, loops, holes, malformed delimiters, Unicode source positions,
malformed `open_bytes` input, stale revisions, same-revision cache reuse, and
JSONL recovery after malformed requests.

The session checks compare file-oriented `check` with JSONL `open`, require
same-revision results to be stable, require cache hits, reject stale edits, and
verify one response per malformed or adversarial request. The reducer uses a
bounded deterministic byte-level ddmin loop and preserves the exact reduced
input in the result receipt.

The repository's existing A11 OCaml-lexer-vs-Pep-written-lexer differential
suite remains a separate acceptance surface. Run it independently with:

```powershell
python -m unittest tests.test_a11 -v
```

Those inherited checks are intentionally not counted as fresh laboratory
cases; this prevents the report from confusing reused builder evidence with
new harness evidence.

## Classification

- `confirmed-bug`: the public contract or an independent expected result was
  contradicted, or the bounded process failed to make a required response;
- `language-ambiguity`: reserved for a future reviewed finding where the
  specification and implementation disagree without a determined answer;
- `missing-test`: the case passed the current checks and is retained as a
  reusable coverage point;
- `expected-rejection`: an intentionally invalid case was rejected;
- `unsupported-feature`: the case is outside the current seed boundary.

The harness intentionally does not call agreement between two compiler paths
proof of language correctness. The OCaml parser/checker and JSONL session can
share assumptions, so the report records that limitation explicitly.
