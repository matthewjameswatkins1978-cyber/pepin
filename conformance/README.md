# Pepin language conformance laboratory

This directory owns an independent, reusable black-box laboratory for the
OCaml seed compiler at the reviewed A11 base. It does not edit the Pep parser,
checker, interpreter, or established semantics.

## Grammar-aware corpus (Conformance 02)

`conformance/generator.py` owns a small deterministic constructor library for
the implemented seed grammar. It emits paired valid and intentionally invalid
cases for arithmetic, Boolean control flow, records, recursive union matching,
lists/`for-in`, and lexical shadowing. Cases carry their seed, family, depth,
node count, exact source bytes, expected check status and (for valid programs)
independently computed output. No Pep parser or AST is reused to generate the
source.

The optional grammar tier is bounded separately from the inherited generator:

```powershell
python conformance/harness.py --seeds 20261026 1101 --count 2 `
  --grammar-count 3 --grammar-depth 2 --timeout 8 --reduce 0
```

`--grammar-count N` creates `2*N` grammar cases per seed (`N` valid and `N`
invalid); `--grammar-depth` is constrained to 0..5. Valid cases must pass the
normal check contract and then produce the exact independent output. Invalid
cases must return a completed, well-shaped diagnostic with status `invalid` or
`incomplete` and exit code 1. A valid case rejected by check is a
`confirmed-bug`; a launch/transport failure is an `infrastructure-failure`.

The same module contains a signed-64-bit reference model (`INT_MIN` and
`INT_MAX`) covering checked add/subtract/multiply/negate, truncation-toward-zero
division, divide-by-zero and the minimum-integer divide/negate overflow cases.
These vectors are recorded as model evidence; they do not silently stand in
for compiler execution. A12 parser topology remains gated and is not imported
by this tier.

## Metamorphic tier

`conformance/metamorphic.py` provides two reviewed relations for valid generated
cases: switching LF/CRLF line endings and adding lexer comments at line ends.
The runner is enabled with `--metamorphic-count N`; each selected valid case
normally yields two bounded pairs. Both checks must remain valid, both runs must
match the independent expected output, and a span/revision-insensitive semantic
signature must agree. A transformed case that differs only in source offsets is
therefore not a false finding, while a synthetic mismatch is a fatal harness
test. The relation itself is pure and deterministic, making it suitable for
future source-aware reduction without importing a Pep parser.

## Run

From the repository root:

```powershell
python conformance/harness.py --seeds 20261026 1101 1201 --count 4 --reduce 2
```

Run the fast tester self-checks separately; they do not launch Pep or consume
the comprehensive corpus budget:

```powershell
python -m unittest conformance.test_harness -v
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

The command returns non-zero when a fresh run records a confirmed bug or an
infrastructure failure.
`missing-test` entries are successful coverage observations, not correctness
claims. Every finding retains its exact corpus file, case identifier, seed in
the identifier, and replay commands in `results.json`.

Launch failures and missing or malformed process output are recorded as
`infrastructure-failure`; they still make the command fail, but are not
mislabelled as Pep compiler defects.

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
verify one response per malformed or adversarial request. Runtime failures are
accepted only when the process completes with exit code 1, a
`runtime_error` response, and the exact expected diagnostic code. Launcher
failures, malformed output, unexpected statuses and timeouts are findings.

The reducer uses a bounded deterministic byte-level ddmin loop with a
finding-specific replay oracle. It reruns the original oracle on the reduced
bytes; if the failure is unsupported or does not survive, the original input
is retained and the receipt says `reduction: unsupported`.

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
- `infrastructure-failure`: the harness could not launch or decode the bounded
  process; this is a failed run, not evidence of a compiler defect;
- `language-ambiguity`: reserved for a future reviewed finding where the
  specification and implementation disagree without a determined answer;
- `missing-test`: the case passed the current checks and is retained as a
  reusable coverage point;
- `expected-rejection`: an intentionally invalid case was rejected;
- `unsupported-feature`: the case is outside the current seed boundary.

The report also includes machine-readable classification counts and the exact
large-response fixture `session-large-response.pep` (6,000 `say("x")` lines),
which must remain reproducible as a documented `PEP_TOOL_MESSAGE_TOO_LARGE`
boundary probe.

The harness intentionally does not call agreement between two compiler paths
proof of language correctness. The OCaml parser/checker and JSONL session can
share assumptions, so the report records that limitation explicitly.
