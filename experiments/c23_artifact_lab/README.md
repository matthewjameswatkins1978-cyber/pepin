# C23 Artifact-05 laboratory

This directory is an isolated, test-only artifact laboratory. It accepts
explicit checked-AST-shaped JSON manifests and emits canonical C23 source.
It does not parse Pep, type-check Pep, implement A14, or define the A13
checked-tree contract.

Slice 1 deliberately supports only expression-bodied functions over `Int`,
`Bool`, and `Unit`: literals, checked arithmetic, comparisons, parameters,
and calls. Every expression carries a stable identity, explicit type, and
source span. The manifest also commits source provenance, ownership facts,
potential failures, and the expected observable outcome.

Generate with:

```text
python artifact_lab.py validate fixtures/primitive_add.json
python artifact_lab.py generate fixtures/primitive_add.json _build/primitive_add.c
```

Generated names are derived from checked identities, output uses LF and fixed
formatting, and invalid or incomplete manifests fail before output creation.
