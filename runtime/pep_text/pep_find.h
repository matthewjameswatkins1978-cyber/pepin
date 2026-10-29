// Agent-4 byte-substring search: the native text primitive for finding
// a needle in a haystack without NUL termination, for the compiler
// (delimiter/keyword scanning over raw buffers) and native applications.
// Everything is explicit lengths; embedded NULs are ordinary bytes.
// Matching is a pure byte substring: no case folding, no Unicode
// normalization, no locale. When both sides are valid UTF-8 and the
// needle is non-empty, every reported match starts on a UTF-8 boundary
// by construction (a valid needle cannot begin with a continuation
// byte) — a documented property, not a checked one. Invalid UTF-8 on
// either side still searches byte-wise; offsets always count bytes.
#ifndef PEP_FIND_H
#define PEP_FIND_H

#include <stddef.h>

enum {
    PEP_FIND_OK = 0,    // found; *at holds the byte offset
    PEP_FIND_NONE = 1,  // no occurrence; *at holds hn (one past the end)
    PEP_FIND_BADARG = 2 // null pointer argument (any null, any lengths)
};

// Find the first occurrence of `needle[0..nn)` in `hay[0..hn)`.
// An empty needle is found at offset 0. A needle longer than the
// haystack is never found. Worst case O(hn*nn) byte comparisons;
// no state, no allocation, no reads outside [hay, hay+hn).
// Codes are component-local, matching the rest of runtime/pep_text.
int pep_text_find(const char *hay, size_t hn, const char *ndl, size_t nn, size_t *at);

#endif
