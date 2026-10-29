// Agent-4 span/diagnostic rendering: native counterpart of the compiler's
// source-span contract. pep_span_locate mirrors both span authorities
// byte-for-byte: the OCaml seed lexer (advance on '\n' only; '\r' is an
// ordinary column byte) and the Pep-written lexer's byte_position model.
// pep_diag_render prints the seed CLI form `file:line:col: CODE: message`
// plus the source excerpt line and a caret. Columns are byte columns;
// this is documented, not hidden, so a future native lexer can upgrade to
// character columns without changing the call shape.
#ifndef PEP_SPAN_H
#define PEP_SPAN_H

#include <stddef.h>

#include "pep_textbuf.h"

enum {
    PEP_SPAN_OK = 0,
    PEP_SPAN_BADARG = 1
};

// 1-based line/column for a byte offset. Offsets past the end clamp to n
// (the end-of-input position, as the seed lexer reports EOF). A null s is
// always PEP_SPAN_BADARG, even with n == 0.
int pep_span_locate(const char *s, size_t n, size_t offset,
                    unsigned long *line, unsigned long *col);

// Append one diagnostic block: `file:line:col: CODE: message`, the excerpt
// line containing offset (without its terminating '\n'), and a caret line
// with '^' under column col. Never fails on content, only on null
// pointers; builder errors propagate.
int pep_diag_render(pep_textbuf_t *buf, const char *file, const char *code,
                    const char *message, const char *s, size_t n, size_t offset);

#endif
