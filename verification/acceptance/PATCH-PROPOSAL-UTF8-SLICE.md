# PATCH PROPOSAL — by-name `utf8_slice` lowering (for A2; A3 does not apply it)

**Author:** A3. **Status: UNTESTED PROPOSAL.** A3 has not applied, run or verified this; it is written so
that A2 can land it in minutes and A3 can then verify it independently. Nothing here has been executed.

**Why:** BOOT-A3-054 measured that `utf8_slice` is the only missing Str path — `str_concat` works inline and
in initialisers, `utf8_slice` has **0** by-name lowering sites in `tests/pep_c23_emitter.pep` while
`str_concat` has 3. It is the single item between the campaign and input-dependent C text (BOOT-A3-055).

**Template:** the existing `str_concat` case, which pairs an expression-level lowering with a runtime helper
that allocates from a bump pool so results stay valid for the whole run.

## 1. Runtime helper — insert beside `pep_str_concat` (≈ line 5418, same `prepend` block)

```c
#define PEP_UTF8_SLICE_CAPACITY PEP_STR_CONCAT_CAPACITY
[[maybe_unused]] static pep_str pep_utf8_slice(pep_source_bytes source, int64_t start, int64_t end) {
  if (source.length != 0 && source.data == NULL) { fputs("PEP_RUNTIME_INVALID_SOURCE_BYTES\n", stderr); exit(1); }
  if (start < 0 || end < start || (uintmax_t)end > (uintmax_t)source.length) {
    fputs("PEP_RUNTIME_UTF8_SLICE_RANGE\n", stderr); exit(1);
  }
  size_t span = (size_t)(end - start);
  if (span > PEP_UTF8_SLICE_CAPACITY) { fputs("PEP_RUNTIME_UTF8_SLICE_RANGE\n", stderr); exit(1); }
  static unsigned char pep_slice_pool[PEP_UTF8_SLICE_CAPACITY];
  static size_t pep_slice_used = 0;
  unsigned char *out = pep_slice_pool + pep_slice_used;
  for (size_t i = 0; i < span; ++i) { out[i] = source.data[(size_t)(start + (int64_t)i)]; }
  pep_slice_used += span;
  return (pep_str){ .data = out, .length = span };
}
```

Notes: capacity reuses the existing constant so there is one Str budget, not two; the three range tests
mirror `pep_byte_at`'s signed-then-`uintmax_t` discipline (BOOT-A3-026); a bump pool mirrors
`pep_str_concat`'s stated rationale (every result valid for the whole run, no reuse).

## 2. Expression lowering — add a sibling of the `str_concat` case (≈ line 2766–2780)

```pep
    if node.text == "utf8_slice" {
      if !argument.found || !secondArgument.found || !thirdArgument.found || extraArgument.found {
        return pep_c23_unsupported("Pep C23 utf8_slice lowering requires a SourceBytes and two Int offsets")
      } else {}
      if thirdArgument.node.kind != "integer" && thirdArgument.node.kind != "name" && !pep_c23_is_negative_int_literal(nodes, thirdArgument.node) {
        return pep_c23_unsupported("Pep C23 utf8_slice end offset must be an integer literal or local")
      } else {}
      let loweredSource = pep_c23_expression(nodes, function, argument.node)
      let loweredStart = pep_c23_expression(nodes, function, secondArgument.node)
      let loweredEnd = pep_c23_expression(nodes, function, thirdArgument.node)
      if loweredSource.status != "emitted" { return loweredSource } else {}
      if loweredStart.status != "emitted" { return loweredStart } else {}
      if loweredEnd.status != "emitted" { return loweredEnd } else {}
      var parts: List[Str] = ["pep_utf8_slice("]
      for part in loweredSource.sourceParts { parts = append(parts, part) }
      parts = append(parts, ", ")
      for part in loweredStart.sourceParts { parts = append(parts, part) }
      parts = append(parts, ", ")
      for part in loweredEnd.sourceParts { parts = append(parts, part) }
      parts = append(parts, ")")
      return PepC23Emission { status: "emitted", sourceParts: parts, diagnostic: "" }
    } else {}
```

Notes: it must sit in the same dispatch chain and use the same `argument`/`secondArgument`/`thirdArgument`/
`extraArgument` lookups the neighbouring builtin cases use; the arity guard is explicit so a wrong-arity call
fails closed with its own text. **A2 should check the exact helper names in scope** — `pep_c23_is_negative_int_literal`
is used by the `contains` case nearby, but the SourceBytes-parameter path is whatever `byte_at`/`byte_length`
already use, and I did not trace it.

## 3. Acceptance criteria A3 will use (audit only, no authoring)

| # | check | expected after the patch |
|---|---|---|
| 1 | `verification/fixtures/str/s5_slice_local.pep` | **emits** (today: refused) |
| 2 | `verification/probes/divergence_2_042.py` | D1–D5 pass: two unseen inputs → **different C text**, both compile under strict Clang **and** GCC, run to different outputs |
| 3 | `verification/probes/emit_any_049.py` on `cursor_kind_v1/v2` | must not regress |
| 4 | `verification/probes/flatten_vs_nest_045.py`, `line_scan_gate_034.py` | no regression |
| 5 | a negative: `utf8_slice(source, 3, 1)` and `utf8_slice(source, 0, byte_length(source) + 1)` | refused at **runtime** with `PEP_RUNTIME_UTF8_SLICE_RANGE`, no value printed (my auditor's style) |

## What A3 will not do

Will not apply this, will not certify it, and will not claim it works. If A2 lands a different shape, that is
fine — the acceptance criteria above are what matter, not this code.

## Honest limits

- **Untested.** The helper names and the exact dispatch-chain position are inferred by reading
  `tests/pep_c23_emitter.pep` at A1 `86ff953`; A2 knows the file and may need to adjust.
- The capacity constant reuse is a deliberate proposal, not a measured optimum.
- Copy-vs-view is resolved as **copy**, matching `pep_str_concat`'s safety rationale; a view would dangle if
  the grant buffer were ever freed, and I have not measured either option's cost.

REF: GH #16.