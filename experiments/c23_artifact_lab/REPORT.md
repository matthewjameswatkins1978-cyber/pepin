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
declared outcomes, and all comparable Pep interpreter runs match. The accepted
ABI-04 runtime and separate-TU fixture remain the runtime authority.

## Schema and trust boundary

Schema version 1 requires exact root fields for fixture identity, source
provenance, function/binding identities, types, ownership/lifetime facts,
potential failures, supported features, and an expected outcome. Expressions
carry stable node IDs, explicit types, and byte spans. The validator rejects
missing facts, unknown bindings/functions/constructors/fields, invalid UTF-8,
bad nominal types, wrong field/constructor arity, duplicate node IDs, missing
ownership facts, incomplete match facts, revision conflicts, and unsupported
schema versions before writing C.

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
failure, executable failure, malformed receipts, and timeouts are separate
non-success classifications. It never turns a missing compiler into a pass.

The 16 native receipts comprise six successful scalar/structured values,
eight successful values including record/list/string fixtures, and four
controlled runtime errors across the full corpus. The current receipt is
written under ignored `_build/c23-artifact-05/native3`.

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
status. An independent generated-source invariant rejects a mutation that
removes `pep_list_dispose`. The ABI-04 separate-TU fixture was rerun with the
new execution/revision deadlines: Clang and GCC semantic/error receipts remain
equal, including owner mismatch `range` and owner recovery `ok`.

Clang AddressSanitizer passes on generated list, record, and string artifacts
when the LLVM 23 Windows runtime directory is explicitly present on PATH.
GCC ASan remains unavailable in the installed MinGW distribution because its
linker lacks `-lasan`; this is reported as unavailable, not passed coverage.

## Artifacts and performance

The bounded performance receipt uses two warmups and five trials per fixture
and compiler, with separate artifact/runtime object compilation and linking.
It records source/object/executable sizes, hashes, exact commands, compiler
versions, exit status, and startup samples. Eight rows per compiler passed.
On this Windows host, generated source sizes were 793--1,448 bytes, Clang
object sizes 2,134--2,716 bytes, GCC object sizes 1,222--1,672 bytes, Clang
executables 153,088 bytes, and GCC executables 61,336--61,876 bytes. Mean
process samples were approximately 9.22--15.82 ms for Clang and 9.68--12.76
ms for GCC. These are artifact startup measurements, not claims about a future
native compiler or interpreter speedup.

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
