// Agent-4 UTF-8 helpers: minimal C23 runtime primitives for validation,
// decoding, and encoding. Pep cannot express raw bytes, so the byte
// mechanics live here. Validation follows `invalid_utf8_offset` in the
// OCaml seed and `utf8_check` in examples/pep_lexer.pep. The strict scalar
// classification table used by decode is mirrored in pep_utf8_model.pep.
// Invalid input never produces a scalar value; every entry point reports
// the failure and changes nothing it does not own.
#ifndef PEP_UTF8_H
#define PEP_UTF8_H

#include <stddef.h>

enum {
    PEP_UTF8_OK = 0,       // valid input
    PEP_UTF8_INVALID = 1,  // malformed encoding; offset points at the byte
    PEP_UTF8_BADARG = 2,   // null pointer argument
    PEP_UTF8_RANGE = 3     // reserved for future scalar-range reporting
};

// Validate n bytes. Returns PEP_UTF8_OK, or PEP_UTF8_INVALID with
// *error_offset set using the seed's diagnostic policy: truncation or an
// invalid lead reports that lead byte; for a complete structural sequence,
// the first non-continuation reports its own byte, and otherwise overlong,
// surrogate and out-of-range scalars report their lead. On OK the offset
// is unchanged. Structural widths include C0/C1 and F5-F7 only to select
// the error offset, never to accept an invalid scalar.
// A null error_offset is allowed; the status still reports validity.
// A null s is always PEP_UTF8_BADARG, even with n == 0: pass "" or a
// real buffer for empty input.
int pep_utf8_validate(const char *s, size_t n, size_t *error_offset);

// Decode the first scalar value. Needs n >= 1. Returns the width in bytes
// (1-4) with *cp set, or 0 when the lead sequence is malformed or n holds
// only a truncation. Never reads past s + n.
size_t pep_utf8_decode(const char *s, size_t n, unsigned int *cp);

// Encode one Unicode scalar value (U+0000-U+D7FF, U+E000-U+10FFFF).
// Returns the width in bytes (1-4) with out filled, or 0 for surrogates,
// values above U+10FFFF, or a null out. No NUL terminator is written.
size_t pep_utf8_encode(unsigned int cp, char out[4]);

#endif
