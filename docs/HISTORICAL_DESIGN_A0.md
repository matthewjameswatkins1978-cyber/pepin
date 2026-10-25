# Historical design: Pep A0 and the MoonBit seed

**Status:** Historical record of the original A0 implementation slice. This document is retained for provenance; it is not the current Pep design or implementation guide. The current primary seed is OCaml. See [Founding Design v0.3](FOUNDING_DESIGN_v0.3.md), [Technical Resolution 001](TECHNICAL_RESOLUTION_001.md), and [current implementation status](DESIGN.md).

# Pep v0.2 design decisions implemented in A0

Pep is a small, statically typed language intended to become self-hosting. The
MoonBit compiler is temporary seed tooling; it does not define Pep semantics.

A0 accepts a program as zero or more `say("text")` statements. String literals
support `\n`, `\r`, `\t`, `\0`, `\\`, and `\"`. Statements may be
separated by whitespace or semicolons. Other names and constructs are rejected
with a stable diagnostic rather than silently interpreted.

The compiler uses a real character-based lexer, a token parser, and a minimal
semantic gate before C generation. Tokens and statements carry one-based source
line and column positions. LF and CRLF both count as one line break.

Generated C targets C11. The code generator emits byte arrays and calls the
small `pep_say` runtime interface. The runtime writes the exact UTF-8 bytes and
then one newline using the Windows host `WriteFile` interface. It does not embed source text in C string literals.

The initial executable has process lifetime. String values are generated as
static byte arrays; a process-lifetime arena is deferred until dynamic values
exist. Diagnostics use schema version 1 with stable codes, severity, message,
file, line, and column. `describe --json` reports only implemented features.
