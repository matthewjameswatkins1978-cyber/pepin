# BOOT-A4-20261106-002 — SourceBytes native blocker oracle + A2 handoff (slices 2–3)

TESTED at seed (`57fe424` campaign tree, `pep.ps1`, `_build/b4src/`, ignored
scratch). Native predictions are SOURCE-READ at A2 `123d8b3` (INFERRED where
marked). No A1/A2/verification files touched.

## Slice 2: seed oracle (TESTED)

| # | fixture | `check --json` | `run` |
|---|---|---|---|
| S1 | `let s = source_bytes()` + `say(int_text(byte_length(s)))` | valid | `PEP_RUNTIME_SOURCE_CONTEXT` exit 1 |
| S2 | `let s = source_bytes()` + `say(int_text(byte_at(s, 0)))` | valid | `PEP_RUNTIME_SOURCE_CONTEXT` exit 1 |
| S3 | `let s = source_bytes()` + `say(utf8_slice(s, 0, 3))` | valid | `PEP_RUNTIME_SOURCE_CONTEXT` exit 1 |
| S4 (neg) | `fn main() -> Int { return byte_at(0, 0) }` | invalid `PEP_TYPE_MISMATCH` "Expected SourceBytes but found Int" exit 1 | — |

S1–S3 run-refusals are CORRECT fail-closed behavior (no host-authorised v2
`semanticTarget` under standalone `run`), per dispatch — not a bug and not a
native failure. The checker gate (S4) fires on the exact shape a laundering
attempt would take. The lexer threading shape (`let source = source_bytes()`
+ `byte_at(source, …)`) checks valid, so the seed side is green end to end.

## Slice 2b: native gap (SOURCE-READ at A2 `123d8b3`, 110-fn emitter)

- G1 (INFERRED first refusal): NO `source_bytes()` lowering arm exists for
  user programs (the two `source_bytes()` hits are interpreted-side uses
  inside the emitter itself, e.g. string-literal span check). `lexer_step:152`
  `let source = source_bytes()` is therefore the first refusal of the real
  lexer vertical.
- G2 (SOURCE-READ): `byte_at`/`byte_length` lower ONLY for a name bound to a
  direct `SourceBytes` *parameter* (`pep_c23_source_bytes_parameter`);
  a let-bound local is refused with "currently requires a direct SourceBytes
  parameter". The lexer never passes SourceBytes as a parameter (E5 in
  slice-1 doc), so G2 fires immediately behind G1.
- G3 (SOURCE-READ): NO `utf8_slice` lowering arm exists at all (single
  interpreted-side use). Lexer word/symbol/string slicing (`pep_lexer.pep`
  lines 257/308/string paths) is the third refusal in line.

## Slice 3: A2 handoff (4 lines, verbatim)

Save as one file and drive through the seam probe's chunk path at the
post-re-pin A2 SHA + A1 pin, strict Clang+GCC + seed `check` oracle:

```pep
fn byte_len(source: SourceBytes) -> Int { return byte_length(source) }
fn first(source: SourceBytes) -> Int { return byte_at(source, 0) }
fn local() -> Int { let s = source_bytes(); return byte_length(s) }
fn main() -> Int { return 0 }
```

Predictions: `byte_len`/`first` lower (direct-parameter shape, runtime
`pep_byte_length`/`pep_byte_at` already emitted); `local` refuses naming
`source_bytes` (G1) or the direct-parameter constraint (G2). Any other
refusal text is a new finding — report it verbatim. If `local` lowers, G1/G2
are FALSIFIED and I retract them. No A1 fixture: the hot lexer staged work is
A1's lane and this slice found nothing that advances it beyond G1–G3.

Falsifier of THIS doc: any S1–S4 seed output above that does not reproduce, or
an A2 probe run contradicting the predictions (either routes correctly).
