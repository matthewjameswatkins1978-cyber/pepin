// Agent-4 JSON values: minimal composition on top of pep_json_escape for
// the machine-readable outputs Pep promises (inspect/check/query style).
// Compact form only — `{"kind":"int","value":42}` with no spaces —
// matching the seed's emitters exactly. No pretty-printing, no DOM, no
// parsing: the writer streams into the caller's builder, so arbitrarily
// large reports never need an intermediate tree. Nesting depth is the
// caller's business; every function is O(1) besides the bytes written.
#ifndef PEP_JSONVAL_H
#define PEP_JSONVAL_H

#include <stddef.h>

#include "pep_json.h"

// Structural writers. Commas and colons are explicit calls so the caller
// — not a hidden state machine — owns document shape, exactly like the
// seed's string-concatenation emitters.
int pep_json_begin_object(pep_textbuf_t *buf);
int pep_json_end_object(pep_textbuf_t *buf);
int pep_json_begin_array(pep_textbuf_t *buf);
int pep_json_end_array(pep_textbuf_t *buf);
int pep_json_comma(pep_textbuf_t *buf);
int pep_json_colon(pep_textbuf_t *buf);

// Scalar writers.
int pep_json_str(pep_textbuf_t *buf, const char *s, size_t n);
int pep_json_int(pep_textbuf_t *buf, long long value);
int pep_json_bool(pep_textbuf_t *buf, int value);
int pep_json_null(pep_textbuf_t *buf);

// Key writer: `"name":` — an escaped string immediately followed by the
// colon, the seed's object-field shape.
int pep_json_key(pep_textbuf_t *buf, const char *s, size_t n);

#endif
