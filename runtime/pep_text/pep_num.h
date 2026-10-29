// Agent-4 integer text form: parsing for the decimal Int format the seed
// owns in two places — unsigned digit runs in the lexer (overflow is
// PEP_INT_LITERAL_RANGE) and the optional-minus signed form in the tool
// protocol ("Int values must be signed 64-bit decimal strings"). This is
// the missing round-trip half of pep_textbuf_append_i64: formatting is
// exact, so parse(format(x)) must be x for every Int64, including MIN.
// No locale, no plus sign, no whitespace skipping, no UB on any input.
#ifndef PEP_NUM_H
#define PEP_NUM_H

#include <stddef.h>

enum {
    PEP_NUM_OK = 0,       // a value was parsed; *end holds bytes consumed
    PEP_NUM_NODIGITS = 1, // no digits (empty, lone "-", or non-digit first)
    PEP_NUM_OVERFLOW = 2, // digit run exceeds the Int64 range
    PEP_NUM_BADARG = 3    // null pointer argument
};

// Parse an optional "-" followed by a maximal ASCII digit run. At least
// one digit is required. "-0" parses as 0. "+5", " 12", and "" report
// NODIGITS with *end set to 0. A run past "9223372036854775807"
// ("-9223372036854775808" when negated) reports OVERFLOW with *value and
// *end left untouched. Stops at the first non-digit; that byte is not
// an error, it just ends the run.
int pep_parse_i64(const char *s, size_t n, long long *value, size_t *end);

#endif
