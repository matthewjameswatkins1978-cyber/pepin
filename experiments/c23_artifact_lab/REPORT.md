# PEP-C23-ARTIFACT-05 report

This is an isolated test laboratory, not the Pep compiler and not an A14
emitter. It consumes manually authored checked-AST-shaped manifests so the
future A13 contract can be tested without importing parser topology or doing
name resolution in the generator.

## Result

The laboratory establishes deterministic C23 source generation and strict
native execution for a small explicit subset. Eight fixtures generate source
that compiles and executes under both selected Windows toolchains. Native
successes and controlled overflow/division failures match the independently
declared outcomes, and all comparable Pep interpreter runs match. Fresh R1
evidence is in `_build/c23-artifact-05/native-r1.json` and
`_build/c23-artifact-05/performance-r1.json` (ignored build outputs). The
accepted ABI-04 runtime and separate-TU fixture remain the runtime authority.

## Schema and trust boundary

Schema version 1 requires exact root fields for fixture identity, source
provenance, function/binding identities, types, ownership/lifetime facts,
potential failures, supported features, and an expected outcome. Expressions
carry stable node IDs, explicit types, and byte spans. The validator rejects
missing facts, unknown bindings/functions/constructors/fields, invalid UTF-8,
bad nominal types, wrong field/constructor arity, duplicate node IDs, incomplete
ownership coverage or values, incomplete match facts, digest mismatches,
out-of-bounds spans, revision conflicts, and unsupported schema versions before
writing C.

Validation and emission capability are separate gates. Constructor and match
facts remain validator-recognised but fail with a structured
`unsupported_emission_feature`; parameterised entry points fail with
`entry_parameters_unsupported`; union/unsupported nominal outputs fail with
`unsupported_entry_output` or `unsupported_emission_type`; and borrowed
`List[Int]` parameters fail with `borrowed_list_unsupported`. No raw assertion
or downstream C compiler error is the feature diagnostic.

A13 owns binding/type/constructor/call resolution, source validity,
exhaustiveness, holes, and semantic validity. The generator owns only schema
validation, stable C naming, emission, status propagation, and artifact
receipts. It never repairs or infers missing checked facts.

## Determinism

Stable names are SHA-256 prefixes of checked identities in separate namespaces
for functions, locals, types, fields, and temporaries. Declarations and type
fields are sorted by checked identity; generated source uses fixed formatting,
LF bytes, no timestamps, machine paths, addresses, or source spellings.
Canonical manifest bytes sort non-semantic JSON object keys. Focused tests
compare repeated renders, reordered objects, independent output directories,
and mutated generated cleanup obligations.

## Native evidence

Every build uses:

```text
-std=c23 -Wall -Wextra -Wpedantic -Werror -O2
```

| Toolchain | Installation | Result |
|---|---|---|
| Clang 23.1.4 | `C:\Users\Matmus\scoop\apps\llvm\current\bin\clang.exe` | 8/8 generated fixtures compile and execute |
| MinGW GCC 16.2.0 | `C:\Users\Matmus\scoop\apps\mingw\current\bin\gcc.exe` | 8/8 generated fixtures compile and execute |

The native runner discovers explicit `PEP_C23_CLANG`/`PEP_C23_GCC` overrides,
PATH, then known installation locations. Unavailable compilers, compilation
 failure, executable failure, malformed receipts, unrelated stdout, and
 timeouts are separate non-success classifications. Compiler identity is
 checked before compilation, and timeout stdout/stderr may be bytes or text
 without causing a secondary decoding failure. It never turns a missing
 compiler into a pass.

The fresh R1 native receipt contains 16 passed rows (eight fixtures per
compiler), including four controlled runtime errors. The receipt records the
actual compiler identity and command for every build and execution.

## Generated semantics

Verified generated cases:

- checked Int arithmetic, comparisons, function calls and parameter bindings;
- nominal immutable records and field access;
- `List[Int]` construction, checked sum, and disposal through the runtime's
  stored owner;
- validated UTF-8 byte strings containing an embedded zero and multibyte `é`;
- deterministic overflow and division-by-zero status propagation;
- Bool output and Unit-capable C representation.

The Pep source in each manifest is executed through `pep.ps1 run`; expected
values/errors are authored in the manifest and are not taken from C output.
The 16 native/interpreter comparisons all matched. A native string receipt is
canonical UTF-8 hex (`4100c3a9`) so embedded zero bytes cannot be confused with
C string termination.

## Ownership and failure evidence

List generation zero-initialises the output owner, checks constructor status,
sums with checked arithmetic, disposes before returning, and propagates the
status. Ownership maps now require exact parameter-binding and function-result
coverage, recognised borrowed/owned values, and unique lifetime facts. An
independent generated-source invariant matches every allocated list symbol to
a disposal and rejects a mismatched cleanup mutation. A borrowed `List[Int]`
parameter is deliberately rejected because the current list_sum emitter would
otherwise dispose borrowed storage. The ABI-04 separate-TU fixture was rerun
with the new execution/revision deadlines: Clang and GCC semantic/error
receipts remain equal, including owner mismatch `range` and owner recovery
`ok`.

Fresh Clang AddressSanitizer builds and executions pass on generated list,
record, and string artifacts when the LLVM 23 Windows runtime directory is
explicitly present on PATH. GCC ASan remains unavailable in the installed
MinGW distribution because its linker lacks `-lasan`; the attempted strict
link failed with that exact diagnostic, so this is reported as unavailable,
not passed coverage.

## Artifacts and performance

The fresh R1 performance receipt uses one warmup and three measured trials per
fixture and compiler, with separate artifact/runtime object compilation and
linking. It records source/object/executable sizes, hashes, exact commands,
compiler versions, exit status, stdout/stderr, and every per-run receipt.
Every warmup and measured trial was checked against the expected oracle;
unrelated stdout is rejected and stderr is retained. Sixteen rows passed.
On this Windows host, generated source sizes were 793--1,448 bytes, Clang
object sizes 2,134--2,716 bytes, GCC object sizes 1,222--1,672 bytes, Clang
executables 153,088 bytes, and GCC executables 61,336--61,876 bytes. Fresh
three-trial mean process samples were approximately 17.33--18.90 ms for
Clang and 9.14--11.36 ms for GCC. These are artifact startup measurements,
not claims about a future native compiler or interpreter speedup.

## Union boundary and A13 matrix

| Fact | Current evidence | A13 dependency |
|---|---|---|
| Stable node/source span | Manifest validator and deterministic names | Must be emitted by checked tree |
| Resolved binding/call IDs | Parameter/call fixtures | Must be semantic IDs, not A12 syntax IDs |
| Nominal record/field IDs | Generated record fixture | Must include ordered field/type facts |
| Union/constructor identity | Validator negative controls | Constructor payload and recursive identity still need review |
| Exhaustive match | Incomplete-match rejection | A13 must provide checked arms/exhaustiveness |
| Ownership/lifetime | Explicit manifest; list disposal proof | A13 must supply borrowed/owned/lifetime facts |
| Error sites | Overflow/division expected failures | A13 must enumerate checked failure sites |
| Provenance/revision | `sha256:` source commitment and conflict test | A13 output must retain authorised revision |
| Holes/incomplete programs | Rejected by missing/unsupported facts | A13 must reject or expose holes before emission |

Recursive tagged unions, pattern matching, arbitrary records with recursive
payloads, allocation-failure injection, and generated multi-translation-unit
partitioning remain unsupported in this generator. The existing ABI-04
handwritten separate-TU corpus covers those runtime properties, but it is not
evidence that Artifact-05 can generate them.

## Acceptance recommendation

The smallest sensible future A14 vertical slice is: one reviewed A13 checked
function with stable semantic IDs, `Int`/`Bool`/`Unit` and one immutable record,
one explicit checked error site, ownership facts, and source revision. A14
should emit the same canonical subset, compile/run it under strict Clang and
GCC, and compare against the checked interpreter before adding recursive unions,
lists beyond `List[Int]`, or general control flow.
