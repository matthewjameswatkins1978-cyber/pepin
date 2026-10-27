# C23 Artifact-05 laboratory

This directory is an isolated, test-only artifact laboratory. It accepts
explicit checked-AST-shaped JSON manifests and emits canonical C23 source.
It does not parse Pep, type-check Pep, implement A14, or define the A13
checked-tree contract.

The current supported emission subset is expression-bodied functions over
`Int`, `Bool`, `Str`, `Unit`, nominal immutable records, and `List[Int]`:
literals, checked arithmetic, comparisons, parameters, calls, record field
access, list construction/sum, and validated UTF-8 byte strings. Every
expression carries a stable identity, explicit type, and source span. The
manifest also commits source provenance, ownership facts, potential failures,
and the expected observable outcome.

Artifact-05 is capability-gated separately from validation: constructor and
match facts may be schema-valid, but they are rejected before C emission until
their emitter/runtime contract is reviewed. The current emitter also rejects
parameterised entry points, unsupported nominal outputs, and borrowed
`List[Int]` parameters rather than generating a partial or unsafe executable.

For `source.mode = comparison_source`, `source.revision` is the lowercase
SHA-256 digest of the UTF-8 `pep_source` bytes and both source and checked-node
spans are bounded by those bytes. A `synthetic` source must use an explicit
`synthetic:<label>` revision instead.

Union declarations are understood by the validator so unknown constructors
and incomplete match facts fail closed, but recursive union construction and
pattern emission remain deliberately unsupported until A13 supplies reviewed
constructor and exhaustive-match facts.

Generate with:

```text
python artifact_lab.py validate fixtures/primitive_add.json
python artifact_lab.py generate fixtures/primitive_add.json _build/primitive_add.c
```

Generated names are derived from checked identities, output uses LF and fixed
formatting, and invalid or incomplete manifests fail before output creation.

The benchmark receipt requires exactly one valid `ARTIFACT` line on stdout;
unrelated stdout is a failure, while stderr is retained as diagnostics. Every
warmup and measured trial is independently checked against the fixture oracle.
