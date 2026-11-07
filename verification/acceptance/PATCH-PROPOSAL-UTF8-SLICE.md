# PATCH PROPOSAL — by-name `utf8_slice` lowering (for A2; A3 does not apply it)

**Author:** A3. **Status: UNTESTED PROPOSAL.** A3 has not applied, run or verified this; it is written so
that A2 can land it in minutes and A3 can then verify it independently. Nothing here has been executed.

---

## AMENDMENT (BOOT-A3-062) — this proposal was incomplete; a lowering alone is not enough

**Read this before implementing.** The original text below describes only the *lowering* site. That is not
sufficient, and following it as written would still fail. Source inspection at `86ff953` shows a builtin is
emittable only when its name appears at **three** sites, because a builtin has no top-level function node for
`pep_c23_function` to find and produces no `ResolvedCall` fact for `pep_c23_cross_chunk_call` to resolve
(that function reads `checked.calls` by `syntaxId` only, and refuses at L655 with
`Pep C23 cross-chunk call has no resolved call fact`).

`str_concat` is the working precedent, and it appears at exactly three places:

| site | purpose | `str_concat` | `utf8_slice` |
|---|---|---|---|
| ~L1181 | classification, so `let` inits and `say()` accept the result | present | **missing** |
| ~L1252 | call-expression classification (`value.kind == "call" && value.text == …`) | present | **missing** |
| ~L2752 | the expression lowering itself | present | **missing** |

The emitter states the reason in its own comment at L1177-1180: *"str_concat is a BUILTIN … no top-level
function node exists for pep_c23_function to find … classify it directly so let-inits and say() accept its
results"*. So the three-site shape is an existing mechanical pattern, not new design.

**Amended scope: add all three sites for `utf8_slice`.** Adding only the third leaves
`let s = utf8_slice(source, a, b)` refusing before the lowering is ever reached — which is exactly the shape
`verification/probes/divergence_2_042.py` and `verification/fixtures/emit/iso_int_text.pep` exercise.

### Second builtin in the same state: `int_text`

Measured counts of quoted-name sites in the emitter: `str_concat` 3, `byte_at` 3, `contains` 2,
`byte_length` 1 — all emittable. **`int_text` 0, `utf8_slice` 0, `byte_slice` 0, `source_bytes` 0** — none
emittable.

`int_text` matters independently of the floor: it is how any emitted program prints an `Int`, so while it is
unemittable **no probe can prove its own output natively**. Minimum reproduction, 10 nodes, chunk valid:

```
fn main() -> Int {
    let text = int_text(42)
    say(text)
    return 0
}
```
→ `unit main: Pep C23 cross-chunk call has no resolved call fact`.

Landing `int_text` (same three sites) would let the whole verification suite move from "emission proven" to
"output proven", which is worth more right now than the slice itself.

### Acceptance criteria (unchanged in kind, tightened in scope)

1. `verification/fixtures/str/s5_slice_local.pep` emits (refused today).
2. `verification/fixtures/emit/iso_int_text.pep` emits, if `int_text` is included.
3. `verification/probes/divergence_2_042.py` D1-D5: two unseen inputs produce different C text, both compile
   under strict Clang **and** GCC, and run to different outputs.
4. `utf8_slice(source, 3, 1)` and `utf8_slice(source, 0, byte_length(source) + 1)` fail closed at runtime,
   printing nothing.
5. No regression in `emit_any_049.py` over `cursor_kind_v1/v2`, `flatten_vs_nest_045.py`,
   `line_scan_gate_034.py`, and the four committed S-shape fixtures under `verification/fixtures/emit/`.

A3 still does not apply this. Ownership of `tests/pep_c23_emitter.pep` is A2's, and A3 cannot certify its own
change.

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